
import traceback
from django.conf import settings
from django.db import transaction

from api.process import AsterManager
from bankcheck import STATUS_CHEQUE
from cddaccount.models import OrdrePayment, TransactionOP

from helpers.exceptions import SigException
from bankcheck.models import ChequeScanne, Cheque,PosteComptable

from djmoney.money import Money
import  logging
logger = logging.getLogger(__name__)
class CheckProcessManager:
    @classmethod
    @transaction.atomic
    def create_chequescannes(cls,user, params):
        rsp = AsterManager.bulk_retrieve_chequescanne_aster(user, **params)
        if rsp["status"] == settings.SUCCESS:
            # onfait la Mise à jour
            rows = rsp["data"]
            with transaction.atomic():
                for item in rows:
                    try:
                        #"TYPEOPERATION,REFERENCE1,AGENCEREMETTANTE,CODEPLACE,NOMBENEF,ADRESSEBENEF,NUMEROCHEQUE,DATECHEQUE,BANQUETIRE,AGENCETIRE,NUMEROCOMPTETIRE,CLERIBTIRE,MONTANTCHEQUE,CODECHEQUE,REJET,TRAITE,SENS,POSTE"
                        TYPEOPERATION = item[0]
                        reference = item[1]
                        AGENCEREMETTANTE = item[2]
                        CODEPLACE = item[3]
                        NOMBENEF = item[4]
                        ADRESSEBENEF = item[5]
                        NUMEROCHEQUE = item[6]
                        DATECHEQUE = item[7]
                        BANQUETIRE = item[8]
                        AGENCETIRE = item[9]
                        NUMEROCOMPTETIRE = item[10]
                        CLERIBTIRE = item[11]
                        amount = float(item[12])
                        CODECHEQUE = item[13]
                        REJET = item[14]
                        TRAITE = item[15]
                        SENS = item[16]
                        poste = item[17]
                        try:
                            ChequeScanne.objects.get(reference=reference)
                            continue
                        except ChequeScanne.DoesNotExist:

                            pass
                        chequescanne = ChequeScanne()
                        try:
                            cheque = Cheque.objects.get(reference=NUMEROCHEQUE)
                            chequescanne.cheque = cheque
                            trx=TransactionOP.objects.filter(cheque=cheque.reference).last()
                            if trx :
                                chequescanne.statut = STATUS_CHEQUE.VISE
                                if hasattr(cheque,"rejet"):
                                    chequescanne.statut = STATUS_CHEQUE.REJET
                                if hasattr(cheque,"miseop_cheque"):
                                    chequescanne.statut = STATUS_CHEQUE.MISE_EN_OPPOSITION
                            else :
                                chequescanne.statut = STATUS_CHEQUE.NON_VISE
                                if hasattr(cheque,"rejet"):
                                    chequescanne.statut = STATUS_CHEQUE.REJET
                                if hasattr(cheque,"miseop_cheque"):
                                    chequescanne.statut = STATUS_CHEQUE.MISE_EN_OPPOSITION

                        except Cheque.DoesNotExist:
                            chequescanne.statut=STATUS_CHEQUE.INCONNU

                        chequescanne.aster_date=DATECHEQUE
                        chequescanne.num_cheque=NUMEROCHEQUE
                        chequescanne.code_cheque=CODECHEQUE
                        chequescanne.traite=TRAITE
                        chequescanne.sens=SENS
                        chequescanne.rejet=REJET
                        chequescanne.adresse_benef=ADRESSEBENEF
                        chequescanne.compte=NUMEROCOMPTETIRE
                        chequescanne.code_cheque=CODECHEQUE
                        chequescanne.agence=AGENCETIRE
                        chequescanne.banque=BANQUETIRE
                        chequescanne.rib=CLERIBTIRE
                        chequescanne.typeop=TYPEOPERATION
                        chequescanne.code_place=CODEPLACE
                        chequescanne.agenceremittante=AGENCEREMETTANTE


                        chequescanne.reference=reference
                        chequescanne.amount=Money(amount, "XOF")
                        chequescanne.beneficiare=NOMBENEF
                        chequescanne.compte_aster=NUMEROCOMPTETIRE

                        try:
                            chequescanne.poste= PosteComptable.objects.get(reference=poste)
                        except PosteComptable.DoesNotExist:
                            pass
                        chequescanne.date_compense=DATECHEQUE
                        chequescanne.save()


                    except:
                        traceback.print_exc()
                        ex = SigException(message="unknow error")
                        # raise ex
                        pass
        output = {}
        return {"status": settings.SUCCESS, "data": output}