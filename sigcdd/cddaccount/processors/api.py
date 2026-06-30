import base64

import time
import traceback
import uuid

import six
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction, DatabaseError
from django_otp.oath import hotp
from datetime import datetime,date ,timedelta
from api.process import AsterManager
from cddaccount import PAYMENT_MEAN_TYPE, STATUT_ASTER, NATURE_COMPTE
from cddaccount.models import generate_trx_data, Transaction, ETAPE_ASTER, TransactionOP, AvisDeDebit, AvisDeCredit, \
    VirementDetails, CompteDepot, JourneeComptable, AnneeComptable, TypeCompteTrx
from cddaccount.process import BaseProvider
from helpers.exceptions import SigException
from bankcheck.models import CompenseCheque, Cheque
from psycopg2.extras import DateRange
MAX_TICKETS = 40
LIMIT_RETARD=900  # 15 minutes pour les retrard
from users.models import User

from api.process import AsterManager
class ApiProvider(BaseProvider):
    @classmethod
    @transaction.atomic
    def create_a_compte(cls,user, compte):
        try:
            x = compte.sql_bind_dict()
            d=AsterManager.create_a_compte(user, **x)
            return d
        except SigException as ex:
            raise ex

    @classmethod
    @transaction.atomic
    def send_aviscredit_trx_aster(cls, user, trx):
        try:
            rsp=AsterManager.send_aviscredit_aster(user,**trx.as_dict())
            if rsp["status"]==settings.SUCCESS:
                trx.etape_compense=ETAPE_ASTER.ENVOYE
                trx.date_envoi=datetime.now()
                trx.save()

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
    def send_avisdebit_trx_aster(cls, user, trx):
        try:
            rsp=AsterManager.send_avisdebit_aster(user,**trx.as_dict())
            if rsp["status"]==settings.SUCCESS:
                trx.etape_compense=ETAPE_ASTER.ENVOYE
                trx.date_envoi=datetime.now()
                trx.save()

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
    def send_cheque_trx_aster(cls, user, trx):
        try:
            rsp=AsterManager.send_cheque_aster(user,**trx.as_dict())
            if rsp["status"]==settings.SUCCESS:
                trx.etape_compense=ETAPE_ASTER.ENVOYE
                trx.date_envoi=datetime.now()
                trx.save()

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
    def send_virement_trx_aster(cls, user, trx):
        try:
            rsp=AsterManager.send_virement_aster(user,**trx.as_dict())
            if rsp["status"]==settings.SUCCESS:
                trx.etape_compense=ETAPE_ASTER.ENVOYE
                trx.date_envoi=datetime.now()
                trx.save()
                #envoie les details du virement
                dtails=trx.trx_detailvirements.exclude(payment_mean=PAYMENT_MEAN_TYPE.MOBILE)

                if dtails.exists():
                    d = [detail.as_dict() for detail in dtails]
                    rsp_detail = AsterManager.bulk_detailvirement_aster(user, d)
                    if rsp_detail["status"] == settings.SUCCESS:
                        for f in dtails:
                            f.etape_compense = ETAPE_ASTER.ENVOYE
                            f.date_envoi = datetime.now()
                            f.save()
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
    def bulk_send_trx_aster(cls, user,input_dtas):
        try:
            rsp=AsterManager.bulk_send_trx_aster(None,input_dtas)
            if rsp["status"]==settings.SUCCESS:
                #onfait la Mise à jour
                for item in input_dtas:
                    try:
                        trx=Transaction.objects.get(reference=item["reference"])
                        trx.etape_compense=ETAPE_ASTER.ENVOYE
                        trx.date_envoi=datetime.now()
                        trx.save()
                    except Transaction.DoesNotExist:
                        pass
                output={}
                return {"status": settings.SUCCESS, "data": output}

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
    def retrieve_trx_aster(cls, user, params):
        try:
            rsp=AsterManager.retrieve_trx_aster(user,**params)
            if rsp["status"]==settings.SUCCESS:
                #onfait la Mise à jour
                d=rsp["data"]
                with transaction.atomic():
                    for item in d:
                        try:
                            cls.update_trx_from_aster_item(item)
                        except Transaction.DoesNotExist:
                            pass
                        except :
                            traceback.print_exc()
                            ex = SigException(message="unknow error")
                            #raise ex
                            pass
                output={}
                return {"status": settings.SUCCESS, "data": output}

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
    def bulk_retrieve_trx_aster(cls, user, params):
        try:
            rsp=AsterManager.bulk_retrieve_trx_aster(user,**params)
            if rsp["status"]==settings.SUCCESS:
                #onfait la Mise à jour
                d=rsp["data"]
                with transaction.atomic():
                    for item in d:
                        try:
                            cls.update_trx_from_aster_item(item)
                        except Transaction.DoesNotExist:
                            pass
                        except :
                            traceback.print_exc()
                            ex = SigException(message="unknow error")
                            #raise ex
                            pass
                output={}
                return {"status": settings.SUCCESS, "data": output}

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
    def bulk_delete_detailvr_aster(cls, user, trx):
        try:
            dtails = trx.trx_detailvirements.all().values_list("reference_aster",flat=True)
            params={"date_payment":trx.jour_comptable.jour,"numeros":list(dtails)}
            rsp=AsterManager.bulk_delete_detailvr_aster(user,**params)
            if rsp["status"]==settings.SUCCESS:
                return {"status": settings.SUCCESS }
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
    def bulk_retrieve_detailvrm_aster(cls, user, params):
        try:
            rsp=AsterManager.bulk_retrieve_detailvrm_aster(user,**params)

            if rsp["status"]==settings.SUCCESS:
                #onfait la Mise à jour
                d=rsp["data"]
                with transaction.atomic():
                    for item in d:
                        try:
                            reference=item[0]
                            traite=str(item[1])
                            cpt_aster = item[3]
                            date_pay=item[2]
                            if traite and traite!="0":
                                trx=VirementDetails.objects.filter(reference_aster=reference,date_payement=date_pay.date(),virement__compte__short_compte=cpt_aster).last()
                                if trx:
                                    trx.etape_compense=ETAPE_ASTER.RETOURNE
                                    trx.status_aster=traite #get_status_vrdetail(traite)
                                    #trx.date_retour=date_retour
                                    trx.save()

                        except VirementDetails.DoesNotExist:
                            pass
                        except :
                            traceback.print_exc()
                            ex = SigException(message="unknow error")
                            #raise ex
                            pass
                output={}
                return {"status": settings.SUCCESS, "data": output}

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
    def bulk_retrieve_aviscredit_aster(cls, user, params):
        try:
            rsp = AsterManager.bulk_retrieve_aviscredit_aster(user, **params)
            admin = User.objects.filter(is_superuser=True).last()


            if rsp["status"] == settings.SUCCESS:
                # onfait la Mise à jour
                d = rsp["data"]
                format = "%d/%m/%y"
                with transaction.atomic():
                    for item in d:
                        try:

                            origin_reference = item[0]
                            compte = item[1]
                            amount = int(item[2])
                            date_pec_str = item[3]


                            datas = {}

                            date_pec = datetime.strptime(date_pec_str, format)

                            rg = DateRange(date_pec.date(), date_pec.date() + timedelta(days=1))

                            annee_comptable = AnneeComptable.objects.filter(period__contains=rg).last()
                            jour_comptable, _created = JourneeComptable.objects.get_or_create(user=admin,
                                                                                              annee_comptable=annee_comptable,
                                                                                              jour=date_pec.date())

                            type_op=item[4]
                            mode = item[5]


                            date_avis = item[10]
                            obs_aster = item[6]

                            if type_op == "AVIS_CRED_FONC":
                                nature= NATURE_COMPTE.FONCTIONNEMENT
                            elif type_op == "AVIS_CRED_INV" : nature=NATURE_COMPTE.INVESTISSEMENT

                            try:
                                AvisDeCredit.objects.get(reference_aster=origin_reference)
                            except AvisDeCredit.DoesNotExist:
                                avis=AvisDeCredit()
                                try:
                                    compte_cdd=CompteDepot.objects.get(compte=compte)
                                    avis.compte = compte_cdd
                                    avis.amount = amount
                                    avis.nature = nature
                                    avis.date_avis = date_pec  # date_avis
                                    avis.rib_cdd = compte_cdd
                                    avis.jour_comptable=jour_comptable
                                    avis.reference_aster = origin_reference
                                    y = str(date_pec.year)
                                    avis.reference = "AC{}{}".format(y[2:], origin_reference)
                                    avis.libelle = obs_aster
                                    avis.nature_depense = obs_aster
                                    avis.poste_comptable = compte_cdd.poste.reference
                                    try:
                                        type_solde_code = item[13]
                                        avis.typecompte=TypeCompteTrx.objects.get(code=type_solde_code)
                                        avis.nature = avis.typecompte.nature
                                    except TypeCompteTrx.DoesNotExist:
                                        pass
                                    avis.save()
                                except CompteDepot.DoesNotExist:
                                    continue
                        except:
                            traceback.print_exc()
                            ex = SigException(message="unknow error")
                            # raise ex
                            pass
                output = {}
                return {"status": settings.SUCCESS, "data": output}

            else:
                c = rsp["message"]
                ex = SigException(message=c)
                ex.message = c
                raise ex
        except:
            traceback.print_exc()
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = SigException(message=c)
            ex.message = c
            raise ex


    @classmethod
    @transaction.atomic
    def bulk_retrieve_avisdebit_aster(cls, user, params):
        try:
            rsp = AsterManager.bulk_retrieve_avisdebit_aster(user, **params)
            admin = User.objects.filter(is_superuser=True).last()

            if rsp["status"] == settings.SUCCESS:
                # onfait la Mise à jour
                d = rsp["data"]
                format = "%d/%m/%y"

                with transaction.atomic():
                    for item in d:
                        try:

                            origin_reference = item[0]
                            compte = item[1]
                            amount = int(item[2])
                            date_pec_str = item[3]
                            date_pec = datetime.strptime(date_pec_str, format)


                            datas = {}
                            rg = DateRange(date_pec.date(), date_pec.date() + timedelta(days=1))

                            date_pec = datetime.strptime(date_pec_str, format)
                            annee_comptable = AnneeComptable.objects.filter(period__contains=rg).last()
                            jour_comptable, _created = JourneeComptable.objects.get_or_create(user=admin,
                                                                                              annee_comptable=annee_comptable,
                                                                                              jour=date_pec.date())

                            type_op=item[4]
                            mode = item[5]


                            date_avis = item[10]
                            obs_aster = item[6]



                            if type_op == "AVIS_DEBIT_FONC":
                                nature= NATURE_COMPTE.FONCTIONNEMENT
                            elif type_op == "AVIS_DEBIT_INV" : nature=NATURE_COMPTE.INVESTISSEMENT


                            try:
                                AvisDeDebit.objects.get(reference_aster=origin_reference)
                            except AvisDeDebit.DoesNotExist:
                                avis=AvisDeDebit()
                                try:
                                    compte_cdd=CompteDepot.objects.get(compte=compte)
                                    avis.compte = compte_cdd
                                    avis.amount = amount
                                    avis.disposition = nature
                                    avis.date_avis = date_pec  # date_avis
                                    avis.rib_cdd = compte_cdd
                                    avis.reference_aster = origin_reference
                                    avis.jour_comptable = jour_comptable
                                    y = str(date_pec.year)
                                    avis.reference = "AD{}{}".format(y[:2], origin_reference)
                                    avis.libelle = obs_aster
                                    avis.nature_depense = obs_aster
                                    avis.poste_comptable = compte_cdd.poste.reference

                                    try:
                                        type_solde_code = item[13]
                                        avis.typecompte=TypeCompteTrx.objects.get(code=type_solde_code)
                                        avis.disposition   = avis.typecompte.nature
                                    except TypeCompteTrx.DoesNotExist:
                                        pass

                                    avis.save()
                                except CompteDepot.DoesNotExist:
                                    continue
                        except:
                            traceback.print_exc()
                            ex = SigException(message="unknow error")
                            # raise ex
                            pass
                output = {}
                return {"status": settings.SUCCESS, "data": output}

            else:
                c = rsp["message"]
                ex = SigException(message=c)
                ex.message = c
                raise ex
        except:
            traceback.print_exc()
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = SigException(message=c)
            ex.message = c
            raise ex


    @classmethod
    @transaction.atomic
    def update_trx_from_aster_item(cls, item):

        try:
            reference_trx=item[0]
            origin_reference = item[1]
            status_compence=item[9]
            obs_aster=item[7]
            if status_compence and status_compence!="0":
                trx=Transaction.objects.get(reference=reference_trx)
                trx.etape_compense=ETAPE_ASTER.RETOURNE
                trx.status_aster=status_compence
                trx.obs_aster=obs_aster
                trx.save()
                if status_compence=="COMPENSE" and trx.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE:
                    compense_cheque=CompenseCheque()
                    cheque = Cheque.objects.get(reference=origin_reference)
                    cheque.is_usable()
                    compense_cheque.cheque=cheque
                    compense_cheque.reference=cheque.reference
                    compense_cheque.trx=trx.reference
                    compense_cheque.observations=obs_aster
                    compense_cheque.amount=trx.amount
                    compense_cheque.compte=trx.account_depot
                    #compense_cheque.date_compense=date_retour
                    #compense_cheque.aster_date=date_retour
                    compense_cheque.banque=""
                    compense_cheque.beneficiare=""
                    compense_cheque.save()
                #si le cheque est compsé:

        except Transaction.DoesNotExist:
            pass
        except :
            traceback.print_exc()
            ex = SigException(message="unknow error")
            raise ex






def get_status_vrdetail(traite):
    if traite==1:
        return STATUT_ASTER.COMPENSE
    elif traite==2:
        return STATUT_ASTER.ECHEC
    else :return STATUT_ASTER.ENCOURS
