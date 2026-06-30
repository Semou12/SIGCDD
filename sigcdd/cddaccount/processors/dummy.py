import base64
import datetime
import time
import traceback
import uuid

import six
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction, DatabaseError
from django_otp.oath import hotp

from api.process import AsterManager
from cddaccount import PAYMENT_MEAN_TYPE
from cddaccount.models import generate_trx_data, Transaction, ETAPE_ASTER, TransactionOP, AvisDeDebit, AvisDeCredit
from cddaccount.process import BaseProvider
from helpers.exceptions import SigException
from bankcheck.models import CompenseCheque, Cheque

MAX_TICKETS = 40
LIMIT_RETARD=900  # 15 minutes pour les retrard


from api.process import AsterManager
class DummyProvider(BaseProvider):
    @classmethod
    @transaction.atomic
    def create_a_compte(cls,user, compte):
        return {}

    @classmethod
    @transaction.atomic
    def send_aviscredit_trx_aster(cls, user, trx):
        return {}
    @classmethod
    @transaction.atomic
    def send_avisdebit_trx_aster(cls, user, trx):
        return {}

    @classmethod
    @transaction.atomic
    def send_cheque_trx_aster(cls, user, trx):
        return {}

    @classmethod
    @transaction.atomic
    def send_virement_trx_aster(cls, user, trx):
        return {}


    @classmethod
    @transaction.atomic
    def bulk_send_trx_aster(cls, user,rows):
        return {}

    @classmethod
    @transaction.atomic
    def retrieve_trx_aster(cls, user, **kwargs):
        return {}

    @classmethod
    @transaction.atomic
    def bulk_retrieve_trx_aster(cls, user, params):
        return {}

    @classmethod
    @transaction.atomic
    def bulk_retrieve_aviscredit_aster(cls, user, params):
        return {}

    @classmethod
    @transaction.atomic
    def bulk_retrieve_avisdebit_aster(cls, user, params):
        return {}

    @classmethod
    @transaction.atomic
    def bulk_retrieve_detailvrm_aster(cls, user, params):

        return {}

    @classmethod
    @transaction.atomic
    def bulk_delete_detailvr_aster(cls, user, trx):
        return {}

