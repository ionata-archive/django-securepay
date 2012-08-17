from logging import Filter
from xml.etree import ElementTree

from django.conf import settings

# On 2.6.6, <ElementTree.Element> is function which constructs an 
# <ElementTree._ElementInterface> instance. On 2.7.7, it is a class.
# This makes it annoying to do `isinstance` calls about a potential element,
# so we extract the class here for later use
ELEMENT_CLASS = ElementTree.Element('dummy').__class__

class Merchant:
    def __init__(self, merchant_id, password):
        self.merchant_id = merchant_id
        self.password = password


def remove_sensitive_info(xml):
    for cc_info in xml.findall('Payment/TxnList/Txn/CreditCardInfo'):
        for child in ['cardNumber', 'pan', 'expiryDate', 'cardType', 'cvv']:
            remove_text_if_exists(cc_info, child)

    merchant_info = xml.find('MerchantInfo')
    remove_text_if_exists(merchant_info, 'password')

    return xml

def remove_text_if_exists(root, child_name):
    if root is None:
        return

    child = root.find(child_name)
    if child is not None:
        child.text = ''

sample_credit_card_data = {
    'number': '4444333322221111',
    'name': 'Tim Heap',
    'card_type': 'VI',
    'expiry': (12, 12,),
    'cvv': 123,
}


class SecurePayFilter(Filter):
    def filter(self, record):
        # Do not obfuscate things in debug mode
        if not settings.DEBUG:
            return True

        # Escape the message and its args, if any of them are XML
        record.msg = self.filter_value(record.msg)
        record.args = tuple([self.filter_value(x) for x in record.args])
        return True

    def filter_value(self, value):
        if not isinstance(value, ELEMENT_CLASS):
            return value

        xml = value
        remove_sensitive_info(xml)
        return ElementTree.tostring(xml)
