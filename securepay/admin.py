from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered

from adminextensions.admin import ExtendedModelAdmin
from adminextensions.shortcuts import model_search, model_link

from securepay.models import Transaction, BankAccount

class TransactionAdmin(ExtendedModelAdmin):
    date_hierarchy = 'created'

    list_display = ('txn_type', 'amount', 'bank_message', 'success',
        'card_name', 'created', 'processed', 'status')
    list_filter = ('txn_type', 'success', 'status', 'processed')

    search_fields = ['amount', 'card_name']

    object_tools = {
        'change': [
            # Link to the reference_transaction, if it exists
            model_link('View reference transaction', Transaction,
                lambda obj: getattr(obj.reference_transaction, 'pk', None)),

            # Search for dependent transactions
            model_search('Find dependent transactions', Transaction,
                lambda obj: {'reference_transaction__id': obj.pk}),
        ],
    }

    fieldsets = (
        ('Transaction', {'fields': (
            'txn_type',
            'amount',
            'card_name',
            'description',
        )}),

        ('Details', {'fields': (
            'purchase_order_no',
            'success',
            'reference_transaction'
        )}),

        ('Diagnostics', {'fields': (
            'txn_id',
            'preauth_id',
            'status',
            'processed',
            'bank_message',
            'response_code',
            'response_text',
        )}),
    )

    readonly_fields = [
        'txn_type',
        'amount',
        'card_name',
        'description',
        'purchase_order_no',
        'success',
        'reference_transaction',
        'txn_id',
        'preauth_id',
        'status',
        'processed',
        'bank_message',
        'response_code',
        'response_text',
    ]

    def has_add_permission(self, request):
        return False



try:
    admin.site.register(Transaction, TransactionAdmin)
except AlreadyRegistered:
    pass

try:
    admin.site.register(BankAccount)
except AlreadyRegistered:
    pass
