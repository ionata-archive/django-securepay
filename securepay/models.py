import datetime

from django.db import models
from django.conf import settings
from picklefield.fields import PickledObjectField

from securepay import utils
from securepay import client

URL_TEMPLATE = 'https://%s.securepay.com.au/xmlapi/%s'
URL_TYPE_MAP = {
    'pay': 'payment',
    'refund': 'payment',
    'reversal': 'payment',
    'preauth': 'payment',
    'complete': 'payment',
    'credit': 'directentry',
    'debit': 'directentry',
}

merchant = {
    'merchant_id': settings.SECUREPAY_MERCHANT_ID,
    'password': settings.SECUREPAY_PASSWORD,
}

def _send(transaction, request):
    transaction.status = 'sending'
    transaction.save()

    endpoint = URL_TEMPLATE % (
        'test' if settings.SECUREPAY_DEBUG else 'api',
        URL_TYPE_MAP[transaction.txn_type],
    )

    (response_text, response_xml) = client.send_request(endpoint, request)

    transaction.status = 'receiving'
    transaction.response_text = response_text
    transaction.save()

    transaction_response = response_xml.find('Payment/TxnList/Txn')
    # The docs say that this is always 'Yes'. They lie. Sometimes it is 'YES'.
    transaction.success = transaction_response.find('approved').text.lower() == 'yes'
    transaction.response_code = transaction_response.findtext('responseCode')
    transaction.bank_message = transaction_response.findtext('responseText')

    transaction.txn_id = transaction_response.findtext('txnID')
    transaction.preauth_id = transaction_response.findtext('preauthID')

    transaction.status = 'completed'
    transaction.save()

    return response_xml

class TransactionManager(models.Manager):
    """
    Model manager for Transactions
    """


    def pay(self, amount, credit_card, purchase_order_no='Transaction-%d', data={}):
        """
        Make a payment through SecurePay

        Parameters:
            amount - The amount to pay, in dollars.
            credit_card - A dict of credit card details, usually generated by
                <securepay.forms.CreditCardForm>.
            data - Any extra data to store with this transaction

        Returns:
        A Transaction
        """
        transaction = Transaction(amount=amount,
            txn_type='pay',
            card_name=credit_card['name'],
            description=data.get('description', ''),
            extra_data=data)
        transaction.save()

        transaction.purchase_order_no=purchase_order_no % transaction.id
        transaction.save()

        request = client.make_pay_request(merchant, transaction, credit_card)
        response = _send(transaction, request)

        return transaction

    def reversal(self, amount=None, data={}):
        """
        Void a previous transaction in SecurePay

        Parameters:
            reference_transaction - The transaction to void.
            amount - The amount to void. Defaults to the amount of the
                reference_transaction
            data - Any extra data to store with this transaction

        Returns:
        A Transaction
        """
        if amount is None:
            amount = reference_transaction.amount

        transaction = Transaction(amount=amount,
            txn_type='reversal',
            card_name=reference_transaction.card_name,
            description=data.get('description', ''),
            reference_transaction=reference_transaction,
            purchase_order_no=reference_transaction.purchase_order_no,
            extra_data=data)
        transaction.save()

        request = client.make_void_request(merchant, transaction)
        response = _send(transaction, request)

        return transaction


    def refund(self, reference_transaction, amount=None, data={}):
        """
        Refund a previous transaction in SecurePay

        Parameters:
            reference_transaction - The transaction to refund.
            amount - The amount to refund. Defaults to the amount of the
                reference_transaction
            data - Any extra data to store with this transaction

        Returns:
        A Transaction
        """
        if amount is None:
            amount = reference_transaction.amount

        transaction = Transaction(amount=amount,
            txn_type='refund',
            card_name=reference_transaction.card_name,
            description=data.get('description', ''),
            reference_transaction=reference_transaction,
            purchase_order_no=reference_transaction.purchase_order_no,
            extra_data=data)
        transaction.save()

        request = client.make_refund_request(merchant, transaction)
        response = _send(transaction, request)

        return transaction

    def preauth(self, amount, credit_card, purchase_order_no='Transaction-%d', data={}):
        """
        Preauthorise a payment on a credit card, but do not actually take any
        money. Money is taken in the <complete> method, below

        Parameters:
            amount - The amount to pay, in dollars.
            credit_card - A dict of credit card details, usually generated by
                <securepay.forms.CreditCardForm>.
            data - Any extra data to store with this transaction

        Returns:
        A Transaction
        """
        transaction = Transaction(amount=amount,
            txn_type='preauth',
            card_name=credit_card['name'],
            description=data.get('description', ''),
            extra_data=data)
        transaction.save()

        transaction.purchase_order_no=purchase_order_no % transaction.id
        transaction.save()

        request = client.make_preauth_request(merchant, transaction, credit_card)
        response = _send(transaction, request)

        return transaction

    def complete(self, reference_transaction, amount=None, data={}):
        """
        Complete a previous preauthorize transaction, taking the reserved money

        Parameters:
            reference_transaction - The preauthorize transaction to complete
            amount - The amount to take. The amount can be less than or equal
                to the preauthorised amount. If the amount taken is less than
                the amount reserverd via the preauth, the remainder is returned
                to the customers card.  Defaults to the amount of the
                reference_transaction.
            data - Any extra data to store with this transaction

        Returns:
        A Transaction
        """
        if amount is None:
            amount = reference_transaction.amount

        transaction = Transaction(amount=amount,
            txn_type='complete',
            card_name=reference_transaction.card_name,
            description=data.get('description', ''),
            reference_transaction=reference_transaction,
            purchase_order_no=reference_transaction.purchase_order_no,
            extra_data=data)
        transaction.save()

        request = client.make_complete_request(merchant, transaction)
        response = _send(transaction, request)

        return transaction


    def direct_credit(self, amount, bank_details, data={},
        purchase_order_no='Transfer %s'):
        """
        Credit another bank account, transferring money directly out of our
        linked account.

        Parameters:
            amount - The amount to transfer, in dollars.
            bank_details - A dict of bank account details, usually generated by
                <securepay.forms.BankAccountForm> or <BankAccount>.
            data - Any extra data to store with this direct transfer

        Returns:
        A Transaction
        """
        transaction = Transaction(amount=amount,
            txn_type='credit',
            card_name=bank_details['name'],
            description=data.get('description', ''),
            extra_data=data)
        transaction.save()

        transaction.purchase_order_no=purchase_order_no % transaction.id
        transaction.save()

        request = client.make_direct_credit_request(merchant, transaction,
            bank_details)
        response = _send(transaction, request)

        return transaction

    def direct_debit(self, amount, bank_details, data={},
        purchase_order_no='Transfer %s'):
        """
        Take money from another bank account, transferring the money directly in
        to out linked account.

        Parameters:
            amount - The amount to transfer, in dollars.
            bank_details - A dict of bank account details, usually generated by
                <securepay.forms.BankAccountForm> or <BankAccount>.
            data - Any extra data to store with this direct transfer

        Returns:
        A Transaction
        """
        transaction = Transaction(amount=amount,
            txn_type='debit',
            card_name=bank_details['name'],
            description=data.get('description', ''),
            extra_data=data)
        transaction.save()

        transaction.purchase_order_no=purchase_order_no % transaction.id
        transaction.save()

        request = client.make_direct_debit_request(merchant, transaction,
            bank_details)
        response = _send(transaction, request)

        return transaction


class Transaction(models.Model):
    """
    A transaction with SecurePay

    Fields:
        created - The datetime the transaction was initiated.
        modified - The datetime the transaction was last modified.

        card_name - The name on the credit card used for the transaction.

        txn_type - The type of transaction. 

        amount - The amount of money charged, in dollars.

        description - The description of the transaction as it appears on a bank
            statement.

        extra_data - Any extra data associated with the transaction.

        status - Current status of the transaction. This is only used while a
            transaction is currently being processed. All transactions which
            have been completed should have the value `'completed'`.

        processed - If the action associated with the transaction has completed
            successfully.  If a transaction was successful, but `processed` is
            false, then someone has paid for something which then failed to
            complete!

        success - If the SecurePay indicated that the transaction was
            successful.

        response_code - The response code from the bank. See the documentation
            for possible values.

        bank_message - Any messages (e.g. error messages) from the bank.
        
        reference_transaction - The transaction that refund, void or complete
            transactions refer to. Not used by pay and preauth transactions.

        txn_id - The transaction ID from the bank.

        preauth_id - The preauth ID from the bank, used in complete
            transactions. Only used in preauth transactions.
    """

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    purchase_order_no = models.CharField(max_length=60, db_index=True)

    card_name = models.CharField(max_length=255)

    txn_type = models.CharField(max_length=10, choices=[
        ('pay', 'Payment'),
        ('refund', 'Refund'),
        ('reversal', 'Reversal'),
        ('preauth', 'Preauthenticate'),
        ('complete', 'Complete'),
        ('credit', 'Direct Credit'),
        ('debit', 'Direct Debit'),
    ])

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=25)

    extra_data = PickledObjectField()

    status = models.CharField(max_length=10, choices=[
        ('init', 'Initializing'),
        ('sending', 'Sending request to SecurePay'),
        ('receiving', 'Receiving transaction information from SecurePay'),
        ('completed', 'Transaction has completed'),
    ])
    processed = models.NullBooleanField()
    success = models.NullBooleanField()

    response_text = models.TextField(blank=True)
    response_code = models.CharField(max_length=3, blank=True)
    bank_message = models.CharField(max_length=255, blank=True)

    reference_transaction = models.ForeignKey('self', related_name='referenced_by', blank=True, null=True, on_delete=models.SET_NULL)
    txn_id = models.CharField(max_length=10, blank=True, null=True)
    preauth_id = models.CharField(max_length=10, blank=True, null=True)

    debug = models.BooleanField(default=settings.SECUREPAY_DEBUG)

    objects = TransactionManager()

    class Meta:
        ordering = ['-created']

    def __unicode__(self):
        return "%s %s for $%0.2f on %s by %s" % (
            {True: 'Successful', False:'Unsuccessful', None: 'Unfinished'}[self.success],
            self.get_txn_type_display(),
            self.amount,
            self.created.strftime("%d/%m/%Y"),
            self.card_name,
        );


class BankAccount(models.Model):
    name = models.CharField(max_length=32)
    bsb = models.CharField(max_length=6)
    account_number = models.CharField(max_length=9)

    class Meta:
        ordering = ['name', 'bsb', 'account_number']

    def __unicode__(self):
        return "%s %s %s" % (self.name, self.bsb, self.account_number)
