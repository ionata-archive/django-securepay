import sys
import datetime
import requests
import uuid
import pytz
import logging

from xml.etree import ElementTree

from django.conf import settings

from securepay.utils import remove_sensitive_info

API_VERSION = 'xml-4.2'

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)

logger = logging.getLogger(__name__)

#: Maps from <Payment.txn_type> values to SecurePay <txnType> numbers
TYPE_MAP = {
    'pay': 0,
    'refund': 4,
    'reversal': 6,
    'preauth': 10,
    'complete': 11,
    'credit': 15,
    'debit': 17,
}

def send_request(endpoint, xml):
    """
    Send an XML request to SecurePay, and return the response
    """
    xml_string = "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        ElementTree.tostring(xml),
    ])
    logger.info("Sending payment request %s", xml)


    response = requests.post(endpoint, data=xml_string)
    response_text = response.text

    response_xml = None
    try:
        response_xml = ElementTree.fromstring(response_text)
        logger.info("Got payment response %s", response_xml)
    except SyntaxError:
        logger.info("Got bad response from SecurePay: %s", response_text)

    return (response_text, response_xml)

def make_request(merchant, request_type, request_data=[]):
    """
    Make a request XML document. This is called by the make_X_request functions.
    This wraps the request_data in a `<SecurePayMessage>` element, and makes
    the required `<MessageInfo>` and `<MerchantInfo>` elements to accompany it.

    Parameters:
        merchant - The merchant credentials
        request_type - 'Payment' or 'Echo', as appropriate
        request_data - A list of extra elements to append to the request data.

    Returns:
    The root `<SecurePayMessage>` element for the whole request.
    """
    valid_request_types = ['Payment', 'Echo']
    if request_type not in valid_request_types:
        raise ValueError('Invalid request_type %s. Must be one of %s' % (
            request_type, ', '.join(valid_request_types)))

    children = [
        make_message_info(),
        make_merchant_info(merchant),
        make_element('RequestType', text=request_type),
    ]
    children += request_data

    root = make_element('SecurePayMessage', children=children)
    return root


def make_message_info(message_id=None):
    """
    Make a `<MessageInfo>` element for a request. Currently uses hardcoded
    values for timeout and api version. A UUID v4 is used for the message ID.
    """
    if message_id is None:
        message_id = uuid.uuid4()

    message_info = make_element('MessageInfo', children=[
        make_element('messageID', text=message_id),
        make_element('messageTimestamp', text=make_message_timestamp()),
        make_element('timeoutValue', text='60'),
        make_element('apiVersion', text=API_VERSION),
    ])
    return message_info


def make_message_timestamp(now=None):
    """
    Make a message timestamp, complying with the strict rules set by SecurePay.
    If passed a date, that date will be used, otherwise it will use
    <datetime.datetime.now>. Returns the timestamp as a string
    """
    if now is None:
        now = datetime.datetime.now(LOCAL_TIMEZONE)

    offset = now.utcoffset().seconds / 60

    return ''.join([
        # Note year-day-month, not year-month-day or day-month-year
        now.strftime('%Y%d%m%H%M%S'), # Timestamp
        '%03d' % int(now.microsecond / 1000), # Milliseconds
        '000', # 000 for Microsecond
        '%+04d' % (offset), # Offset in minutes from UTC
    ])


def make_merchant_info(merchant):
    """
    Make a `<MerchantInfo>` element for a given merchant
    """
    merchant_info = make_element('MerchantInfo', children=[
        make_element('merchantID', text=merchant['merchant_id']),
        make_element('password', text=merchant['password']),
    ])
    return merchant_info

def make_credit_card_info(credit_card):
    """
    Make a `<CreditCardInfo>` element for the given credit card details
    """
    expiry = '%02d/%02d' % (credit_card['expiry'][0], credit_card['expiry'][1])

    credit_card_info = make_element('CreditCardInfo', children=[
        make_element('cardNumber', text=credit_card['number']),
        make_element('cvv', text=('%03d' % credit_card['cvv'])),
        make_element('expiryDate', text=expiry),
    ])

    return credit_card_info

def make_direct_entry_info(bank_account):
    """
    Make a `<DirectEntryInfo>` element for the given credit card details
    """
    direct_entry_info = make_element('DirectEntryInfo', children=[
        make_element('bsbNumber', text=bank_account['bsb']),
        make_element('accountNumber', text=bank_account['account_number']),
        make_element('accountName', text=bank_account['name']),
    ])

    return direct_entry_info

def make_basic_txn(transaction):
    """
    Make a `<Txn>` element with the required elements. `<txnType>` is taken
    from <Transaction.txn_type>, and is what ultimately decides what type of
    transaction this is
    """
    txn = make_element('Txn', attrib={'ID': '1'}, children=[
        make_element('txnType', text=TYPE_MAP[transaction.txn_type]),
        make_element('txnSource', text='0'), # Hardcoded to 0, as per docs
        make_element('amount', text=int(transaction.amount * 100)),
        make_element('purchaseOrderNo', text=transaction.purchase_order_no),
    ])

    return txn

def wrap_txn(txn):
    """
    Wrap a `<Txn>` element in a suitable `<Payment><TxnList>` wrapper,
    and return it
    """
    txn_list = make_element('TxnList', attrib={'count': '1'}, children=[txn])
    payment = make_element('Payment', children=[txn_list])
    return payment


def make_element(name, text='', attrib={}, children=[]):
    el = ElementTree.Element(name, attrib=attrib)
    el.text = str(text)

    for child in children:
        el.append(child)

    return el


    
def _make_payment_request(merchant, transaction, credit_card):
    """
    Make an XML request for payment using a credit card
    """
    txn = make_basic_txn(transaction)
    txn.append(make_credit_card_info(credit_card))
    return make_request(merchant, 'Payment', [wrap_txn(txn)])

def _make_referenced_transaction_request(merchant, transaction):
    """
    Make an XML request that references another request
    """
    txn = make_basic_txn(transaction)

    if transaction.txn_type == 'complete':
        txn.append(make_element('preauthID', text=transaction.reference_transaction.preauth_id))
    else:
        txn.append(make_element('txnID', text=transaction.reference_transaction.txn_id))

    return make_request(merchant, 'Payment', [wrap_txn(txn)])

def _make_direct_transfer_request(merchant, transaction, bank_account):
    """
    Make a direct transfer request
    """
    txn = make_basic_txn(transaction)
    txn.append(make_direct_entry_info(bank_account))
    return make_request(merchant, 'Payment', [wrap_txn(txn)])

# Alias these functions, as they all act the same
make_preauth_request = _make_payment_request
make_pay_request = _make_payment_request

make_void_request = _make_referenced_transaction_request
make_refund_request = _make_referenced_transaction_request
make_complete_request = _make_referenced_transaction_request

make_direct_credit_request = _make_direct_transfer_request
make_direct_debit_request = _make_direct_transfer_request
