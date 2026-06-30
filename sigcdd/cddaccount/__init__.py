
from django.utils.translation import pgettext_lazy


class STATUS_CREATION:
    NOUVEAU = 'NOUVEAU'
    VALIDE = 'VALIDE'
    ATTENTE = 'ATTENTE'

    CHOICES = [
        (NOUVEAU, pgettext_lazy("NOUVEAU", "NOUVEAU")),
        (ATTENTE, pgettext_lazy("ATTENTE VALIDATION", "ATTENTE VALIDATION")),
        (VALIDE, pgettext_lazy("VALIDE", "VALIDE")),
    ]


class NATURE_COMPTE:
    FONCTIONNEMENT = 'FONCTIONNEMENT'
    INVESTISSEMENT = 'INVESTISSEMENT'

    CHOICES = [
        (INVESTISSEMENT, pgettext_lazy('INVESTISSEMENT', 'INVESTISSEMENT')),
        (FONCTIONNEMENT, pgettext_lazy('FONCTIONNEMENT', 'FONCTIONNEMENT'))

    ]

class PROVENANCE_FOND:
    BUDGET = 'B'
    FONDPROPRE = 'F'

    CHOICES = [
        (BUDGET, pgettext_lazy('BUDGET', 'BUDGET')),
        (FONDPROPRE, pgettext_lazy('FOND PROPRE', 'FOND PROPRE'))

    ]

class NATURE_FONDS:
    FONDSDAVANCE = 'FONDDAVANCE'
    CAISSEDAVANCE = 'CAISSEDAVANCE'

    CHOICES = [
        (CAISSEDAVANCE, pgettext_lazy("CAISSE D'AVANCE", "CAISSE D'AVANCE")),
        (FONDSDAVANCE, pgettext_lazy("FONDS D'AVANCE", "FONDS D'AVANCE")),
    ]

class STATUS_ORDRE_PAYMENT:
    NOUVEAU = 'NOUVEAU'
    ACCEPTE = 'ACCEPTE'
    REJETE = 'REJETE'

    CHOICES = [
        (NOUVEAU, pgettext_lazy("NOUVEAU", "NOUVEAU")),
        (ACCEPTE, pgettext_lazy("ACCEPTE", "ACCEPTE")),
        (REJETE, pgettext_lazy("REJETE", "REJETE")),
    ]

    CHOICES_1 = [
        (ACCEPTE, "ACCEPTE"),
        (REJETE, "REJETE"),
    ]



class ETAPE_ORDRE_PAYMENT:
    SAISIE = 'SAISIE'
    VALIDE = 'VALIDE'
    ACCEPTE = 'ACCEPTE'
    REJETE = 'REJETE'
    PRISE_EN_CHARGE = 'PRISE_EN_CHARGE'
    VISA = 'VISA'

    CHOICES = [
        (SAISIE, pgettext_lazy("SAISIE", "SAISIE")),
        (VALIDE, pgettext_lazy("VALIDE", "VALIDE")),
        (ACCEPTE, pgettext_lazy("ACCEPTE", "ACCEPTE")),
        (REJETE, pgettext_lazy("REJETE", "REJETE")),
        (PRISE_EN_CHARGE, pgettext_lazy("PRISE_EN_CHARGE", "PRISE EN CHARGE")),
        (VISA, pgettext_lazy("VISA", "VISA")),
    ]



class TYPE_REGLEMENT:
    ACOMPTE  = 'ACOMPTE '
    GLOBAL = 'GLOBAL'

    CHOICES = [
        (GLOBAL, pgettext_lazy("GLOBAL", "GLOBAL")),
        (ACOMPTE, pgettext_lazy("ACOMPTE ", "ACOMPTE "))
    ]



class TYPE_VIREMENT:
    SIMPLE  = 'UNITAIRE'
    MASSE = 'MASSE'

    CHOICES = [
        (SIMPLE, pgettext_lazy("UNITAIRE", "UNITAIRE")),
        (MASSE, pgettext_lazy("MASSE ", "MASSE"))
    ]



class PAYMENT_MEAN_TYPE:
    CHEQUE = 'CHEQUE'
    VIREMENT = 'VIREMENT'
    NUMERAIRE = 'NUMERAIRE'
    OPERATION_ORDRE = 'OD'
    MOBILE = 'MOBILE'
    RETRAIT = 'ODRE_DE_PAIEMENT'

    CHOICES = [
        (CHEQUE, pgettext_lazy("CHEQUE", "COMPENSE")),
        (VIREMENT, pgettext_lazy("VIREMENT", "VIREMENT")),
        (NUMERAIRE, pgettext_lazy("NUMERAIRE", "NUMERAIRE")),
        (OPERATION_ORDRE, pgettext_lazy("OPERATION ORDRE", "OPERATION ORDRE")),
        (RETRAIT, pgettext_lazy("ODRE PAIEMENT", "ODRE PAIEMENT")),
        (MOBILE, pgettext_lazy("MOBILE", "MOBILE")),
    ]



class DISPOSITION_TYPE:
    COURANT = 'COURANT'
    INVESTISSEMENT = 'INVESTISSEMENT'
    ANTERIEUR = 'ANTERIEUR'
    FONCTIONNEMENT = 'FONCTIONNEMENT'

    CHOICES = [
        (COURANT, pgettext_lazy("COURANT", "COURANT")),
        (INVESTISSEMENT, pgettext_lazy("INVESTISSEMENT", "INVESTISSEMENT")),
        (FONCTIONNEMENT, pgettext_lazy("FONCTIONNEMENT", "FONCTIONNEMENT")),
        (ANTERIEUR, pgettext_lazy("ANTERIEUR", "ANTERIEUR"))
    ]



class TYPE_GESTION:
    COURANT = 'COURANT'
    ANTERIEUR = 'ANTERIEUR'

    CHOICES = [
        (COURANT, pgettext_lazy("GESTION COURANTE", "GESTION COURANTE")),
        (ANTERIEUR, pgettext_lazy("GESTION ANTERIEURE", "GESTION ANTERIEURE"))
    ]


class TYPE_RECEPTIONNAIRE:
    GERANT = 'GERANT'
    MANDATAIRE = 'MANDATAIRE'
    BENEFICIAIRE = 'BENEFICIAIRE'

    CHOICES = [
        (GERANT, pgettext_lazy("GERANT", "GERANT")),
        (MANDATAIRE, pgettext_lazy("MANDATAIRE", "MANDATAIRE")),
    ]




class SENS_TRX:
    CREDIT = 'CREDIT'
    DEBIT = 'DEBIT'

    CHOICES = [
        (CREDIT, pgettext_lazy("CREDIT", "CREDIT")),
        (DEBIT, pgettext_lazy("DEBIT", "DEBIT")),
    ]


class ETAPE_ASTER:
    NOUVEAU = 'NOUVEAU'
    ENVOYE = 'ENVOYE'
    RETOURNE="RETOURNE"

    CHOICES = [
        (NOUVEAU, pgettext_lazy("NOUVEAU", "NOUVEAU")),
        (ENVOYE, pgettext_lazy("ENVOYE", "ENVOYE")),
        (RETOURNE, pgettext_lazy("RETOURNE", "RETOURNE")),
    ]



class STATUT_ASTER:
    COMPENSE = '4'
    CHEZ_TG = '1'
    REJET="5"
    ENVOIE_SICA="8"
    ENCOURS="0"

    CHOICES = [
        (ENCOURS, pgettext_lazy("ENCOURS", "ENCOURS")),
        (REJET, pgettext_lazy("REJET", "REJET VERS PC")),
        (CHEZ_TG, pgettext_lazy("CHEZ_TG", "CHEZ TG")),
        (ENVOIE_SICA, pgettext_lazy("ENVOIE_SICA", "ENCOURS ENVOIE SICA")),
        (COMPENSE, pgettext_lazy("COMPENSE", "PAYE SICA")),
    ]



class TYPE_OBJECT:
    TRANSFERT_COURANT = 'TRANSFERT COURANT'
    TPT = 'TPT'
    LATURE = 'LA TURE'

    AMENDEFORTAITAIRE = 'AMENDE FORTAITAIRE'
    DROITSDETIMBRE = 'DROITS DE TIMBRE'
    REVERSEMENTCAISSEDEDEPOT="REVERSEMENT CAISSE DEDEPOT"

    CHOICES = [
        (TRANSFERT_COURANT, pgettext_lazy('TRANSFERT_COURANT', 'TRANSFERT COURANT')),
        (TPT, pgettext_lazy('TPT', 'TPT')),
        (LATURE, pgettext_lazy('LATURE', 'LA TURE')),
        (AMENDEFORTAITAIRE, pgettext_lazy('AMENDEFORTAITAIRE', 'AMENDE FORTAITAIRE')),
        (DROITSDETIMBRE, pgettext_lazy('DROITSDETIMBRE', 'DROITS DETIMBRE')),
        (REVERSEMENTCAISSEDEDEPOT, pgettext_lazy('HYBRIDE', 'REVERSEMENT CAISSE DE DEPOT')),
    ]



class TYPE_FICHIER:
    POSTE  = 'POSTE'
    COMPTE = 'COMPTE'
    AVITCREDIT="AVITCREDIT"
    AVITDEBIT = "AVITDEBIT"
    OPERATION="OPERATION"

    AVITCREDIT_ASTER = "AVITCREDIT_ASTER"
    AVITDEBIT_ASTER = "AVITDEBIT_ASTER"
    OPERATION_ASTER="OPERATION_ASTER"
    CHEQUIER = "CHEQUIER"

    MINISTERE = "MINISTERE"

    CHOICES = [
        (POSTE, pgettext_lazy("POSTE", "POSTE")),
        (COMPTE, pgettext_lazy("COMPTE ", "COMPTE")),
        (AVITCREDIT, pgettext_lazy("AVITCREDIT ", "AVITCREDIT")),
        (AVITDEBIT, pgettext_lazy("AVITDEBIT ", "AVITDEBIT")),

        (OPERATION,pgettext_lazy("OPERATION ", "OPERATION")),

        (AVITCREDIT_ASTER, pgettext_lazy("AVITCREDIT_ASTER ", "AVITCREDIT_ASTER")),
        (AVITDEBIT_ASTER, pgettext_lazy("AVITDEBIT_ASTER", "AVITDEBIT_ASTER")),
        (OPERATION_ASTER, pgettext_lazy("OPERATION_ASTER ", "OPERATION_ASTER")),

        (CHEQUIER, pgettext_lazy("CHEQUIER ", "CHEQUIER")),
        (MINISTERE,pgettext_lazy("MINISTERE","MINISTERE"))
    ]



def update(output, f):
	if f["moyen"] == PAYMENT_MEAN_TYPE.VIREMENT:
		if f["typenature"] == NATURE_COMPTE.FONCTIONNEMENT:
			output["VIREMENT"]["fonct"] = output["VIREMENT"]["fonct"] + f["montant"]
		if f["typenature"] == NATURE_COMPTE.INVESTISSEMENT:
			output["VIREMENT"]["invest"] = output["VIREMENT"]["invest"] + f["montant"]
		output["VIREMENT"]["total"] = output["VIREMENT"]["total"] + f["montant"]
	if f["moyen"] == PAYMENT_MEAN_TYPE.OPERATION_ORDRE:
		if f["typenature"] == NATURE_COMPTE.FONCTIONNEMENT:
			output["OPERATION"]["fonct"] = output["OPERATION"]["fonct"] + f["montant"]
		if f["typenature"] == NATURE_COMPTE.INVESTISSEMENT:
			output["OPERATION"]["invest"] = output["OPERATION"]["invest"] + f["montant"]
		output["OPERATION"]["total"] = output["OPERATION"]["total"] + f["montant"]
	if f["moyen"] == PAYMENT_MEAN_TYPE.NUMERAIRE:
		if f["typenature"] == NATURE_COMPTE.FONCTIONNEMENT:
			output["NUMERAIRE"]["fonct"] = output["NUMERAIRE"]["fonct"] + f["montant"]
		if f["typenature"] == NATURE_COMPTE.INVESTISSEMENT:
			output["NUMERAIRE"]["invest"] = output["NUMERAIRE"]["invest"] + f["montant"]
		output["NUMERAIRE"]["total"] = output["NUMERAIRE"]["total"] + f["montant"]
	if f["moyen"] == PAYMENT_MEAN_TYPE.CHEQUE:
		if f["typenature"] == NATURE_COMPTE.FONCTIONNEMENT:
			output["COMPENSE"]["fonct"] = output["COMPENSE"]["fonct"] + f["montant"]
		if f["typenature"] == NATURE_COMPTE.INVESTISSEMENT:
			output["COMPENSE"]["invest"] = output["COMPENSE"]["invest"] + f["montant"]
		output["COMPENSE"]["total"] = output["COMPENSE"]["total"] + f["montant"]
	output["total"] = output["total"] + f["montant"]

	return output




class STATUS_PROVIDER:
    INIT = 'INIT'
    ENCOURS = 'ENCOURS'
    DELIVRE = 'DELIVRE'

    CHOICES = [
        (INIT, pgettext_lazy("INIT", "INIT")),
        (ENCOURS, pgettext_lazy("ENCOURS", "ENCOURS")),
        (DELIVRE, pgettext_lazy("DELIVRE", "DELIVRE")),
    ]




class MonthType:
    #January, February, March, April, May, June, July, August, September, October, November, December.
    JANUARY = 'Janvier'
    FEBRUARY = 'Fevrier'
    MARCH = 'Mars'
    APRIL = 'Avril'
    MAY = 'Mai'
    JUNE = 'Juin'
    JULY = 'Juillet'
    AUGUST = 'Aout'
    SEPTEMBER = 'Septembre'
    OCTOBER = 'Octobre'
    NOVEMBER ='Novembre'
    DECEMBER ='Decembre'

    CHOICES = [
        (JANUARY, pgettext_lazy('Mutal type', "Janvier")),
        (FEBRUARY, pgettext_lazy('Health cover', 'Fevrier')),
        (MARCH, pgettext_lazy('Health cover type', "Mars")),
        (APRIL, pgettext_lazy('Health cover', 'Avril')),
        (MAY, pgettext_lazy('Mutal type', "Mai")),
        (JUNE, pgettext_lazy('Health cover', 'Juin')),
        (JULY, pgettext_lazy('Health cover type', "Juillet")),
        (AUGUST, pgettext_lazy('Health cover', 'Aout')),
        (SEPTEMBER, pgettext_lazy('Mutal type', "Septembre")),
        (OCTOBER, pgettext_lazy('Health cover', 'Octobre')),
        (NOVEMBER, pgettext_lazy('Health cover type', "Novembre")),
        (DECEMBER, pgettext_lazy('Health cover', 'Decembre'))
    ]
    DICT_NUMBER_TO_MONTHS= {"1":"JANVIER","2":"FEVRIER","3":"MARS","4":"AVRIL","5":"MAI","6":"JUIN","7":"JUILLET","8":"AOUT","9":"SEPTEMBRE","10":"OCTOBRE","11":"NOVEMBRE","12":"DECEMBRE"}


