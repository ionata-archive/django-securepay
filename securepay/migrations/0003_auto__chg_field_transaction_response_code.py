# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Transaction.response_code'
        db.alter_column('securepay_transaction', 'response_code', self.gf('django.db.models.fields.CharField')(max_length=3))

    def backwards(self, orm):

        # Changing field 'Transaction.response_code'
        db.alter_column('securepay_transaction', 'response_code', self.gf('django.db.models.fields.CharField')(max_length=2))

    models = {
        'securepay.bankaccount': {
            'Meta': {'ordering': "['name', 'bsb', 'account_number']", 'object_name': 'BankAccount'},
            'account_number': ('django.db.models.fields.CharField', [], {'max_length': '9'}),
            'bsb': ('django.db.models.fields.CharField', [], {'max_length': '6'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'securepay.transaction': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Transaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '10', 'decimal_places': '2'}),
            'bank_message': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'card_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'debug': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'extra_data': ('picklefield.fields.PickledObjectField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'preauth_id': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'processed': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'purchase_order_no': ('django.db.models.fields.CharField', [], {'max_length': '60', 'db_index': 'True'}),
            'reference_transaction': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'referenced_by'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': "orm['securepay.Transaction']"}),
            'response_code': ('django.db.models.fields.CharField', [], {'max_length': '3', 'blank': 'True'}),
            'response_text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'success': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'txn_id': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'txn_type': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        }
    }

    complete_apps = ['securepay']