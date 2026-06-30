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
from users.models import User
from api.process import AsterManager
from cddaccount import PAYMENT_MEAN_TYPE, STATUS_PROVIDER, SENS_TRX, TYPE_REGLEMENT
from cddaccount.models import generate_trx_data, Transaction, ETAPE_ASTER, TransactionOP, AvisDeDebit, AvisDeCredit, \
    SettingsOP
from cddaccount.processors.epaiment import EpaiementManager
from helpers.exceptions import SigException
from bankcheck.models import CompenseCheque, Cheque

MAX_TICKETS = 40
LIMIT_RETARD=900  # 15 minutes pour les retrard
import  logging
logger = logging.getLogger(__name__)

ASTER_ACTIVE_VARIANT=settings.ASTER_VARIANT_ACTIVE
class CddProcessManager:
    @classmethod
    @transaction.atomic
    def create_a_compte(cls,user, compte):
        provider=provider_factory()
        return provider.create_a_compte(user, compte)


    @classmethod
    @transaction.atomic
    def send_aviscredit_trx_aster(cls, user, trx):
        provider = provider_factory()
        return provider.send_aviscredit_trx_aster(user, trx)


    @classmethod
    @transaction.atomic
    def send_avisdebit_trx_aster(cls, user, trx):
        provider = provider_factory()
        return provider.send_avisdebit_trx_aster(user, trx)


    @classmethod
    @transaction.atomic
    def send_cheque_trx_aster(cls, user, trx):
        logger.info(" Evoie cheque a aster : {} par {} ".format(trx.reference, user.username))
        provider = provider_factory()
        return provider.send_cheque_trx_aster(user, trx)


    @classmethod
    @transaction.atomic
    def send_virement_trx_aster(cls, user, trx):
        logger.info(" Evoie virement a aster : {} par {} ".format(trx.reference, user.username))
        provider = provider_factory()
        return provider.send_virement_trx_aster(user, trx)

    @classmethod
    @transaction.atomic
    def send_mobile_virement_trx_provider(cls, user, trx):
        provider = provider_factory()
        return provider.send_mobile_virement_trx_provider(user, trx)


    @classmethod
    @transaction.atomic
    def bulk_send_trx_aster(cls, user,payload):
        provider = provider_factory()
        rows= generate_trx_data(payload)
        return provider.bulk_send_trx_aster(user,rows)

    @classmethod
    @transaction.atomic
    def retrieve_trx_aster(cls, user, **kwargs):
        provider = provider_factory()
        return provider.retrieve_trx_aster(user, **kwargs)


    @classmethod
    @transaction.atomic
    def bulk_retrieve_trx_aster(cls, user, params):
        provider = provider_factory()
        return provider.bulk_retrieve_trx_aster(user, params)

    @classmethod
    @transaction.atomic
    def bulk_retrieve_aviscredit_aster(cls, user, params):
        provider = provider_factory()
        return provider.bulk_retrieve_aviscredit_aster(user, params)

    @classmethod
    @transaction.atomic
    def bulk_retrieve_avisdebit_aster(cls, user, params):
        provider = provider_factory()
        return provider.bulk_retrieve_avisdebit_aster(user, params)

    @classmethod
    @transaction.atomic
    def bulk_retrieve_trx_aster(cls, user, params):
        provider = provider_factory()
        return provider.bulk_retrieve(user, params)

    @classmethod
    @transaction.atomic
    def bulk_send_detailsvirement_trx_aster(cls, user, trx):
        provider = provider_factory()
        rows = None#generate_trx_data(payload)
        return provider.send_detailsvirement_trx_aster(user, rows)

    @classmethod
    @transaction.atomic
    def bulk_retrieve_detailvrm_aster(cls, user, params):
        provider = provider_factory()
        return provider.bulk_retrieve_detailvrm_aster(user, params)

    @classmethod
    @transaction.atomic
    def bulk_delete_detailvr_aster(cls, user, trx):
        provider = provider_factory()
        return provider.bulk_delete_detailvr_aster(user, trx)

    @classmethod
    @transaction.atomic
    def create_trx_from_rsp_and_ordre(cls, user, ordre,rsp):
        provider = provider_factory()
        return provider.create_trx_from_rsp_and_ordre(user, ordre,rsp)



class BaseProvider:
    @classmethod
    @transaction.atomic
    def create_a_compte(cls,user, compte):
        raise SigException(message="Not implemented")

    @classmethod
    @transaction.atomic
    def send_aviscredit_trx_aster(cls, user, trx):
        raise SigException(message="Not implemented")
    @classmethod
    @transaction.atomic
    def send_avisdebit_trx_aster(cls, user, trx):
        raise SigException(message="Not implemented")


    @classmethod
    @transaction.atomic
    def send_cheque_trx_aster(cls, user, trx):
        raise SigException(message="Not implemented")

    @classmethod
    @transaction.atomic
    def send_virement_trx_aster(cls, user, trx):
        raise SigException(message="Not implemented")

    @classmethod
    @transaction.atomic
    def send_mobile_virement_trx_provider(cls, user, ordre):
        try:
            data=ordre.virementmasse.mobile_as_dict()
            rsp=EpaiementManager.create_op(**data)
            if rsp["retourType"]=="FONCTIONNAL":
                ordre.status_provider=STATUS_PROVIDER.ENCOURS
                ordre.rsp_provider = rsp
                ordre.id_sender_rq=user.id
                ordre.save()
                return rsp
            else:
                c=rsp["message"]
                ex = SigException(message=c)
                ex.message = c
                raise ex
        except:
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = SigException(message=c)
            ex.message = c
            raise ex

    @classmethod
    @transaction.atomic
    def lookup_and_update_trx_provider(cls, user, ordre):
        try:
            data = ordre.mobile_as_dict()
            rsp = EpaiementManager.get_trx_op(user, **data)
            cls.create_trx_from_rsp_and_ordre(user,ordre, rsp)
        except:
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = SigException(message=c)
            ex.message = c
            raise ex

    @classmethod
    @transaction.atomic
    def create_trx_from_rsp_and_ordre(cls,user, ordre,rsp):
        try:
            if rsp["status"]=="RECU":
                ordre.status_provider = STATUS_PROVIDER.ENCOURS
                ordre.rsp_provider = rsp
                ordre.provider_trx=rsp["ordrePaiementId"]
                trx = TransactionOP()
                trx.reservation = ordre.reservationfond
                trx.amount = ordre.amount
                trx.account_depot = ordre.compte.short_compte
                trx.poste_comptable = ordre.compte.poste.reference
                trx.rib_cdd = ordre.compte.compte
                trx.sig_reference = ordre.sig_reference
                trx.origin_reference = ordre.sig_reference
                trx.account_secondaire = "-"
                trx.cheque = ordre.cheque
                trx.agent = User.objects.get(id=int(ordre.id_sender_rq))
                trx.jour_comptable = ordre.jour_comptable
                trx.libelle = ordre.object
                trx.sens = SENS_TRX.DEBIT
                trx.payment_mean = PAYMENT_MEAN_TYPE.MOBILE
                trx.reglement = TYPE_REGLEMENT.GLOBAL
                trx.beneficiaire = ordre.beneficiaire
                trx.nature_depense = ordre.nature.name
                trx.save()
                CddProcessManager.send_virement_trx_aster(user, trx)
                ordre.status_provider = STATUS_PROVIDER.DELIVRE

                ordre.save()
                # update balance
                from cddaccount.models import compute_all_balances_for_compte
                compute_all_balances_for_compte(ordre.compte,gestion=trx.jour_comptable.annee_comptable_id)

                return rsp
            else:
                c = rsp["message"]
                ex = SigException(message=c)
                ex.message = c
                raise ex
        except:
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = SigException(message=c)
            ex.message = c
            raise ex

    @classmethod
    @transaction.atomic
    def bulk_send_trx_aster(cls, user,rows):
        raise SigException(message="Not implemented")

    @classmethod
    @transaction.atomic
    def retrieve_trx_aster(cls, user, **kwargs):
        raise SigException(message="Not implemented")

    @classmethod
    @transaction.atomic
    def bulk_retrieve_trx_aster(cls, user, params):
        raise SigException(message="Not implemented")

    @classmethod
    @transaction.atomic
    def send_detailsvirement_trx_aster(cls, user, rows):
        raise SigException(message="Not implemented")

    @classmethod
    @transaction.atomic
    def bulk_retrieve_detailvrm_aster(cls, user, params):
        raise SigException(message="Not implemented")

    @classmethod
    @transaction.atomic
    def bulk_retrieve_aviscredit_aster(cls, user, params):
        raise SigException(message="Not implemented")

    @classmethod
    @transaction.atomic
    def bulk_retrieve_avisdebit_aster(cls, user, params):
        raise SigException(message="Not implemented")

    @classmethod
    @transaction.atomic
    def bulk_delete_detailvr_aster(cls, user, trx):
        raise SigException(message="Not implemented")




from typing import Dict
from typing import Tuple
ASTER_VARIANTS: Dict[str, Tuple[str, Dict]] = {
    'default': ('cddaccount.processors.Dummy.DummyProcessManager', {})}

PROVIDER_CACHE = {}

def provider_factory():
    '''
    Return the provider instance based on variant
    '''
    variant=None
    opsettings=SettingsOP.object()
    if opsettings and opsettings.aster_variant:
        variant=opsettings.aster_variant
    variants = getattr(settings, 'ASTER_VARIANTS', ASTER_VARIANTS)
    handler, config = variants.get(variant, (None, None))
    if not handler:
        raise ValueError('aster variant does not exist: %s' %
                         (variant,))
    if variant not in PROVIDER_CACHE:
        module_path, class_name = handler.rsplit('.', 1)
        module = __import__(
            str(module_path), globals(), locals(), [str(class_name)])
        class_ = getattr(module, class_name)
        PROVIDER_CACHE[variant] = class_#(**config)
    return PROVIDER_CACHE[variant]
