import logging
import time
import traceback
from datetime import datetime, date, timedelta
from decimal import Decimal

import pandas as pd
from django.db import transaction
from tablib import Dataset

from bankcheck.models import Chequier, TypeChequier, DAP, Cheque
from cddaccount import TYPE_FICHIER, NATURE_COMPTE, PAYMENT_MEAN_TYPE, ETAPE_ORDRE_PAYMENT, SENS_TRX, TYPE_REGLEMENT
from cddaccount.models import CompteDepot, generate_rib, CodeAgence, AvisDeCredit, Report, ValidationCompte, \
	AnneeComptable, JourneeComptable, OrdrePayment, Nature, ReservationFond, PrisEnchageOrdrePayment, TransactionOP, \
	FichierData, AvisDeDebit, TypeCompteTrx, ReportGestion
from core.models import PosteComptable, DCP, Ministere, Direction, Secteur, ProfileDCP, CodeService, Structure
from helpers.exceptions import SigException

logger = logging.getLogger(__name__)

def chargement_items_excel_file(id):
	try:
		ob=FichierData.objects.get(id=id)
		filehandle=ob.fichier
		type=ob.type
		df = pd.read_excel(filehandle, dtype=pd.StringDtype())
		dataset = Dataset().load(df)
		datas = dataset.dict
		headers=df.columns.ravel()

		if type==TYPE_FICHIER.POSTE:
			postes_comptables_file(datas)
		if type==TYPE_FICHIER.COMPTE:
			compte_depot_file(datas)
		if type==TYPE_FICHIER.AVITCREDIT:
			avis_credit_file(type,datas)
		if type==TYPE_FICHIER.AVITDEBIT:
			avis_credit_file(type,datas)


		if type==TYPE_FICHIER.AVITCREDIT_ASTER:
			avis_credit_file_aster(type,datas)
		if type==TYPE_FICHIER.AVITDEBIT_ASTER:
			avis_credit_file_aster(type,datas)

		if type==TYPE_FICHIER.OPERATION:
			print("operaion")
			operations_file(datas)
		if type==TYPE_FICHIER.OPERATION_ASTER:
			print("operaion aster")
			operations_file_aster(datas)
		if type==TYPE_FICHIER.CHEQUIER:
			print("chequier aster")
			create_chequiers_from_file(datas)
		if type==TYPE_FICHIER.MINISTERE:
			print("minister")
			create_ministere_from_file(datas,headers)

	except :
		traceback.print_exc()


def postes_comptables_file(datas):

	for dtails in datas:
		try:
			poste = str(dtails["CODE POSTE"])
			libelle = str(dtails["LIBELLE AGENCE"])
			banque = str(dtails["N° COMPLET DU COMPTE D'OPERATIONS"])
			code_banque = str(dtails["CODE BANQUE"])
			code_agence = str(dtails["CODE AGENCE"])
			try:
				PosteComptable.objects.get(reference=poste)
			except PosteComptable.DoesNotExist:
				posteComptable=PosteComptable()
				posteComptable.reference=poste
				posteComptable.name=libelle
				posteComptable.comptebanque=banque
				posteComptable.dcp=DCP.object()
				posteComptable.type=PosteComptable.TypePoste.TG
				posteComptable.created=datetime.now()
				posteComptable.save()
		except :
			traceback.print_exc()
			ex = SigException()
			ex.message = "Erreur inconnue"
			raise ex


def compte_depot_file(datas):
	codeAgence = CodeAgence.objects.get(code="010" )
	agent=ProfileDCP.objects.last()

	for dtails in datas:
		try:

			compte_court = str(dtails["COMPTE"])

			if pd.isna(dtails["COMPTE"]) :
				continue
			poste = PosteComptable.objects.get(reference= str(dtails["POSTE"]))



			guichet="{}".format(poste.comptebanque[0:8])



			libelle = str(dtails["LIBELLE"])
			libelle_court = str(dtails["LIBCOURT"])
			nature=str(dtails["NATURE"])


			code_service = compte_court[0:3]
			compte_court = compte_court.replace(".", "")
			twelleve_format=compte_court.zfill(12)

			prefix=poste.comptebanque[0:10]
			_compte="{}{}".format(prefix,twelleve_format)
			pays=prefix[0:2]
			rib=generate_rib(pays,_compte)
			iban="{}{}{}".format(prefix,twelleve_format,rib)
			#SN17501010 00000368 50 33 91
			print(iban)


			secteur_numero = str(dtails["SECTEURS_NUMERO"])

			date_ouverture_str= str(dtails["DATE_SAISIE"])

			date_ouverture_str=date_ouverture_str.split(",")[0]



			format = "%d/%m/%y %H:%M:%S"


			date_ouverture=datetime.strptime(date_ouverture_str, format)



			#credit_fonct = Decimal(dtails["CREDITF"])
			#credit_invest = Decimal(dtails["CREDITI"])



			service,created=CodeService.objects.get_or_create(code=code_service ,defaults={"name":"service_{}".format(code_service,)})
			print(compte_court)
			try:
				compte=CompteDepot.objects.get(short_compte=compte_court)
				compte.actif=True
				compte.save()
			except CompteDepot.DoesNotExist:
				compte=CompteDepot()
				compte.poste=poste
				compte.actif = True
				compte.agent=agent
				if pd.isna(dtails["MINISTERE"]):
					secteur= Secteur.objects.last()
				else:
					secteur, created = Secteur.objects.get_or_create(code=secteur_numero, defaults={
						"name": "secteur_{}".format(secteur_numero, )})

				compte.secteur=secteur
				compte.code_service=service
				compte.compte=iban
				compte.short_compte = compte_court
				compte.banque=codeAgence.bank
				compte.rib=rib
				compte.agence=codeAgence
				compte.guichet=guichet
				compte.compteBanque = compte.compte
				compte.libelle=libelle
				compte.libelle_court=libelle_court

				if not pd.isna(dtails["MINISTERE"]):
					ministere, created = Ministere.objects.get_or_create(name=str(dtails["MINISTERE"]))
					compte.ministere = ministere
					if not pd.isna(dtails["DIRECTION"]):
						direction, created = Direction.objects.get_or_create(name=str(dtails["DIRECTION"]),defaults={"ministere": ministere})
						compte.direction=direction
				compte.open_date=date_ouverture
				#compte.balance_insvest=credit_invest
				#compte.balance_fonct = credit_fonct
				if nature == "F":
					compte.nature=NATURE_COMPTE.FONCTIONNEMENT
				else:
					compte.nature = NATURE_COMPTE.INVESTISSEMENT
				compte.created=datetime.now()
				compte.save()
			if not hasattr(compte,"validationcompte") :
				try:
					c=ValidationCompte.objects.get(compte_id=compte.id)
				except ValidationCompte.DoesNotExist:
					validationCompte = ValidationCompte()
					validationCompte.actif = True
					validationCompte.compte = compte
					validationCompte.save()


		except PosteComptable.DoesNotExist:
			continue
		except :
			traceback.print_exc()
			ex = SigException()
			ex.message = "Erreur inconnue"

			raise ex
from django.utils import timezone
from users.models import User
from djmoney.money import Money
from psycopg2.extras import DateRange
def avis_credit_file(type_,datas):
	codeAgence = CodeAgence.objects.get(code="010" )
	agent=ProfileDCP.objects.last()
	admin=User.objects.filter(is_superuser=True).last()

	current_year = AnneeComptable.active_gestion().year()
	i = int(time.time())
	is_current_year = False

	for dtails in datas:
		try:
			i += 1
			reference_aster1=str(dtails["REFERENCE"])
			reference_aster = reference_aster1.replace("/", "_")
			reference_aster = reference_aster.replace("°", "_")

			reference_aster="{}_{}".format(reference_aster,i)

			compte_court = str(dtails["COMPTE"])

			if pd.isna(dtails["COMPTE"]) :
				continue


			libelle=""
			if not pd.isna(dtails["LIBELLE_1"]):
				libelle=str(dtails["LIBELLE_1"])
				libelle = libelle.replace("/", "_")
				libelle = libelle.replace("°", "_")
			poste = PosteComptable.objects.get(reference= str(dtails["POSTE"]))

			nature=str(dtails["NATURE"])
			type_avis = str(dtails["TYPE_AVIS"])
			gestion = int(str((dtails["GESTION"])))
			if current_year == gestion:
				is_current_year = True

			#gestion=date.today().year
			date_ouverture=datetime.now()
			if not pd.isna(dtails["DATE_AVIS"]):

				date_ouverture_str = str(dtails["DATE_AVIS"])

				format = "%d/%m/%Y"  #02/27/2023
				date_ouverture = get_date_from_pattern(date_ouverture_str) #datetime.strptime(date_ouverture_str, format).date()
			try:
				date_ouverture=timezone.make_aware(date_ouverture)
				cdd=CompteDepot.objects.get(short_compte=compte_court)
				rg = DateRange(date_ouverture.date(), date_ouverture.date() + timedelta(days=1))
				annee_comptable=AnneeComptable.objects.filter(period__contains=rg).last()
				typecpte = None

				if type_avis=="COURANT":
					type_avis = str(dtails["SENS"])
					if type_avis == "C" and type_==TYPE_FICHIER.AVITCREDIT:
						try:
							AvisDeCredit.objects.get(reference=reference_aster)
							logger.debug("{} : Avit credit duplique trouve ".format(reference_aster1, ))
						except AvisDeCredit.DoesNotExist:

							avisCredit=AvisDeCredit()
							avisCredit.reference_aster=reference_aster
							avisCredit.reference = reference_aster
							avisCredit.created = date_ouverture

							avisCredit.date_avis=date_ouverture
							avisCredit.compte=cdd
							avisCredit.poste_comptable=poste
							avisCredit.amount=Decimal(dtails["MONTANT"])
							avisCredit.libelle = libelle
							jour_comptable,_created =JourneeComptable.objects.get_or_create(user=admin,annee_comptable=annee_comptable,jour=date_ouverture.date())
							avisCredit.jour_comptable = jour_comptable



							if nature == "PF":
								typecpte = TypeCompteTrx.objects.get(code="PF")
								avisCredit.nature=NATURE_COMPTE.FONCTIONNEMENT
							elif nature=="PI":
								typecpte = TypeCompteTrx.objects.get(code="PI")
								avisCredit.nature = NATURE_COMPTE.INVESTISSEMENT
							if nature == "BF":
								typecpte = TypeCompteTrx.objects.get(code="BF")
								avisCredit.nature=NATURE_COMPTE.FONCTIONNEMENT
							elif nature=="BI":
								typecpte = TypeCompteTrx.objects.get(code="BI")
								avisCredit.nature = NATURE_COMPTE.INVESTISSEMENT


							avisCredit.typecompte = typecpte
							avisCredit.save()
							avisCredit.created = date_ouverture
							avisCredit.save()
					if type_avis=="D" and type_==TYPE_FICHIER.AVITDEBIT:
						try:
							AvisDeDebit.objects.get(reference=reference_aster)
							logger.debug("{} : Avit debit duplique trouve ".format(reference_aster1, ))
						except AvisDeDebit.DoesNotExist:
							print("avit de debit trouves")

							avisCredit = AvisDeDebit()
							avisCredit.reference_aster = reference_aster
							avisCredit.reference = reference_aster
							avisCredit.created = date_ouverture

							avisCredit.date_avis = date_ouverture
							avisCredit.compte = cdd
							avisCredit.poste_comptable = poste
							avisCredit.amount = Decimal(dtails["MONTANT"])
							avisCredit.libelle = libelle
							jour_comptable, _created = JourneeComptable.objects.get_or_create(user=admin,
							                                                                  annee_comptable=annee_comptable,
							                                                                  jour=date_ouverture.date())
							avisCredit.jour_comptable = jour_comptable

							if nature == "PF":
								typecpte = TypeCompteTrx.objects.get(code="PF")
								avisCredit.disposition=NATURE_COMPTE.FONCTIONNEMENT
							elif nature=="PI":
								typecpte = TypeCompteTrx.objects.get(code="PI")
								avisCredit.disposition = NATURE_COMPTE.INVESTISSEMENT
							if nature == "BF":
								typecpte = TypeCompteTrx.objects.get(code="BF")
								avisCredit.disposition=NATURE_COMPTE.FONCTIONNEMENT
							elif nature=="BI":
								typecpte = TypeCompteTrx.objects.get(code="BI")
								avisCredit.disposition = NATURE_COMPTE.INVESTISSEMENT

							avisCredit.typecompte = typecpte
							avisCredit.save()
							avisCredit.created = date_ouverture
							print("avit de debit créé")
							avisCredit.save()


				if type_avis=="REPORT":
					anne_report = gestion - 1
					x = date(anne_report, 2, 2)

					rg_last = DateRange(x, x + timedelta(days=1))
					annee_comptable_report = AnneeComptable.objects.filter(period__contains=rg_last).last()
					amount = Decimal(dtails["MONTANT"])


					if nature == "PF":
						typecpte = TypeCompteTrx.objects.get(code="PF")
					elif nature == "PI":
						typecpte = TypeCompteTrx.objects.get(code="PI")
					if nature == "BF":
						typecpte = TypeCompteTrx.objects.get(code="BF")
					elif nature == "BI":
						typecpte = TypeCompteTrx.objects.get(code="BI")
					try:


						ReportGestion.objects.get(compte=cdd, anne_comptable=annee_comptable_report,typecompte=typecpte)
						logger.debug("{} : Report dejas  duplique  {}".format(reference_aster1, cdd))
						report.typecompte=typecpte
						report.amount=amount
						report.save()

					except ReportGestion.DoesNotExist:
						report=Report()
						report.compte=cdd
						report.creator=admin
						report.gestion_courant=annee_comptable
						report.typecompte = typecpte
						report.amount = amount

						report.anne_comptable=annee_comptable_report
						report.save()

			except CompteDepot.DoesNotExist:

				logger.debug("{} : Compte non trouve ".format(compte_court,))
				pass
		except PosteComptable.DoesNotExist:

			logger.info("{} : Poste  non trouve ".format(compte_court, ))
			continue
		except :
			traceback.print_exc()
			ex = SigException()
			ex.message = "Erreur inconnue"
			logger.info("Ligne non traite : {}".format(dtails))
			raise ex



def get_nature(nat):
	if nat=="AUTRE CHEQUE_":
		return "FACTURE"
	elif nat=="CHARGE SOCIAL_" : return "SALAIRE"
	else:return nat

def operations_file(datas):
	codeAgence = CodeAgence.objects.get(code="010" )
	agent=ProfileDCP.objects.last()
	admin=User.objects.filter(is_superuser=True).last()
	current_year=AnneeComptable.active_gestion().year()
	i=int(time.time())
	is_current_year=False
	for dtails in datas:
		try:
			i+=1

			compte_court = str(dtails["COMPTE"])
			etatOp = str(dtails["ETAT"])

			numero_cheque1 = str(dtails["NUMCHEQUE"])
			numero_cheque=numero_cheque1.replace("/","_")

			numero_cheque = "{}_{}".format(numero_cheque, i)

			observation = str(dtails["OBSERVATION"])
			mode_payment =str(dtails["MODEPAIEMENT"])
			beneficiaire=str(dtails["BENEFICIAIRE"])
			#"NUMERAIRE, VIREMENT,OPERATION ORDRE, COMPENSE"

			if pd.isna(dtails["COMPTE"]) :
				print("fsvxcxxcxcxxcc__{}".format(numero_cheque, ))
				continue

			poste = PosteComptable.objects.get(reference= str(dtails["PC_IDPOSTE"]))


			type_nature=str(dtails["TYPE_PAIEMENT"])
			print(type_nature)
			nature_name = get_nature(str(dtails["NATURE"]))


			gestion=str(dtails["GESTION"])
			if current_year==gestion:
				is_current_year=True


			date_ouverture = datetime.now()
			date_pec=datetime.now()
			date_reception=datetime.now()
			if not pd.isna(dtails["DATE_JOURNEE"]):
				date_ouverture_str = str(dtails["DATE_JOURNEE"])
				format = "%d/%m/%Y"
				date_ouverture = get_date_from_pattern(date_ouverture_str) #datetime.strptime(date_ouverture_str, format)

			if not pd.isna(dtails["DATEPEC"]):
				date_ouverture_str = str(dtails["DATEPEC"])
				format = "%d/%m/%Y"
				date_pec = get_date_from_pattern(date_ouverture_str) #datetime.strptime(date_ouverture_str, format)
			if not pd.isna(dtails["DATERECEPTION"]):
				date_ouverture_str = str(dtails["DATERECEPTION"])
				format = "%d/%m/%Y"
				date_reception = get_date_from_pattern(date_ouverture_str) #datetime.strptime(date_ouverture_str, format)


			try:
				cdd=CompteDepot.objects.get(short_compte=compte_court)
				rg = DateRange(date_ouverture.date(), date_ouverture.date() + timedelta(days=1))
				annee_comptable=AnneeComptable.objects.filter(period__contains=rg).last()

				try:
					OrdrePayment.objects.get(reference=numero_cheque)
					logger.debug("{} : Ordre de payment duplique trouve ".format(numero_cheque1, ))
				except OrdrePayment.DoesNotExist:

					ordrePayment=OrdrePayment()
					ordrePayment.created = date_reception
					ordrePayment.object=observation #libelle[0:120]
					ordrePayment.creator=admin
					ordrePayment.beneficiaire=beneficiaire
					ordrePayment.reference = numero_cheque
					ordrePayment.open_date=date_ouverture.date()
					ordrePayment.compte=cdd
					ordrePayment.observations=observation
					ordrePayment.sig_reference=numero_cheque
					ordrePayment.poste_comptable=poste
					ordrePayment.amount=Decimal(dtails["MONTANT"])
					ordrePayment.libelle = observation
					ordrePayment.secteur=Secteur.objects.last()

					##"NUMERAIRE, VIREMENT,OPERATION ORDRE, COMPENSE"

					if mode_payment=="VIREMENT":
						ordrePayment.payment_mean=PAYMENT_MEAN_TYPE.VIREMENT
					if mode_payment=="COMPENSE":
						ordrePayment.payment_mean=PAYMENT_MEAN_TYPE.CHEQUE
						ordrePayment.cheque=numero_cheque
					if mode_payment=="NUMERAIRE":
						ordrePayment.payment_mean=PAYMENT_MEAN_TYPE.CHEQUE
					if mode_payment=="OPERATION ORDRE":
						ordrePayment.payment_mean=PAYMENT_MEAN_TYPE.VIREMENT

					if nature_name:
						nature, created = Nature.objects.get_or_create(name=nature_name[0:50])
						ordrePayment.nature=nature

					jour_comptable,created =JourneeComptable.objects.get_or_create(user=admin,annee_comptable=annee_comptable,jour=date_ouverture.date())

					ordrePayment.jour_comptable = jour_comptable
					ordrePayment.gestion=annee_comptable


					if type_nature == "PF":
						ordrePayment.typecompte = TypeCompteTrx.objects.get(code="PF")
						ordrePayment.type_nature=NATURE_COMPTE.FONCTIONNEMENT
					elif type_nature=="PI":
						ordrePayment.typecompte  = TypeCompteTrx.objects.get(code="PI")
						ordrePayment.type_nature = NATURE_COMPTE.INVESTISSEMENT
					elif type_nature == "BF":
						ordrePayment.typecompte = TypeCompteTrx.objects.get(code="BF")
						ordrePayment.type_nature=NATURE_COMPTE.FONCTIONNEMENT
					elif type_nature=="BI":
						ordrePayment.typecompte  = TypeCompteTrx.objects.get(code="BI")
						ordrePayment.type_nature = NATURE_COMPTE.INVESTISSEMENT


					ordrePayment.previous_etape = ETAPE_ORDRE_PAYMENT.VALIDE
					ordrePayment.etape = ETAPE_ORDRE_PAYMENT.ACCEPTE
					ordrePayment.created = date_reception
					ordrePayment.date_reception=date_reception
					ordrePayment.save() #force la date

					if ordrePayment.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and ordrePayment.cheque:
						try:
							mark_cheque_as_use_for_op(ordrePayment)
						except SigException as e :
							#straceback.print_exc()
							pass
					try:
						reservation = ReservationFond()
						reservation.ordre = ordrePayment
						reservation.amount = ordrePayment.amount
						reservation.reliquat = ordrePayment.amount
						reservation.creator = admin
						if ordrePayment.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT:
							reservation.payment_mean = ordrePayment.payment_mean
						reservation.save()


					except SigException as e:
						print("fsffffsffsf__{}".format(numero_cheque,))
						raise e

					if etatOp=="0":
						ordrePayment.previous_etape = ETAPE_ORDRE_PAYMENT.VALIDE
						ordrePayment.etape = ETAPE_ORDRE_PAYMENT.ACCEPTE
						ordrePayment.save()
					elif etatOp=="1" or etatOp=="2":
						prise_encharge = PrisEnchageOrdrePayment()
						prise_encharge.ordre = ordrePayment
						prise_encharge.amount = ordrePayment.amount
						prise_encharge.payment_mean = ordrePayment.payment_mean
						prise_encharge.reglement = ordrePayment.reglement
						prise_encharge.creator = admin
						prise_encharge.created = date_pec
						prise_encharge.save()
						ordrePayment.date_prise_en_charge = date_pec
						ordrePayment.previous_etape = ETAPE_ORDRE_PAYMENT.ACCEPTE
						ordrePayment.etape = ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE
						ordrePayment.observations = observation
						ordrePayment.save()
						if etatOp == "2":
							try:
								with transaction.atomic():
									amount = ordrePayment.amount.amount
									ordrePayment.reservationfond.can_make_trx_with_amount(amount)
									ordrePayment.jour_comptable = jour_comptable
									trx=TransactionOP()
									trx.reservation=ordrePayment.reservationfond
									trx.amount=Money(int(amount), 'XOF')
									trx.account_depot=ordrePayment.compte.short_compte
									trx.poste_comptable=ordrePayment.compte.poste.reference
									trx.rib_cdd = ordrePayment.compte.compte
									trx.sig_reference=ordrePayment.sig_reference
									trx.origin_reference = ordrePayment.sig_reference
									trx.created=date_ouverture
									trx.account_secondaire="-"
									trx.cheque=ordrePayment.cheque
									trx.agent=admin
									trx.beneficiaire=ordrePayment.beneficiaire
									trx.jour_comptable = jour_comptable
									trx.libelle=ordrePayment.object
									trx.sens=SENS_TRX.DEBIT
									trx.payment_mean=ordrePayment.payment_mean
									trx.reglement = TYPE_REGLEMENT.GLOBAL
									trx.nature_depense=ordrePayment.nature.name
									trx.date_rlv = jour_comptable.jour
									trx.typecompte = ordrePayment.typecompte
									trx.save()
									trx.created = date_ouverture
									trx.date_rlv = jour_comptable.jour
									trx.save()

									ordrePayment.date_visa = date_ouverture
									ordrePayment.save()
							except SigException as e:
								traceback.print_exc()

			except CompteDepot.DoesNotExist:
				traceback.print_exc()
				pass
		except PosteComptable.DoesNotExist:
			traceback.print_exc()
			continue
		except :
			traceback.print_exc()
			ex = SigException()
			ex.message = "Erreur inconnue"
			raise ex



def avis_credit_file_aster(type,datas):
	codeAgence = CodeAgence.objects.get(code="010" )
	agent=ProfileDCP.objects.last()
	admin=User.objects.filter(is_superuser=True).last()

	# COMPTE LIBELLE POSTE MONTANT

	index = 0
	for dtails in datas:
		try:
			reference_aster= "{}-{}".format(time.time(),index)#str(dtails["NUMERO"])#str(dtails["REFERENCE"])
			index += 1

			compte_court = str(dtails["COMPTE"])

			if pd.isna(dtails["COMPTE"]) :
				continue

			libelle=""
			if not pd.isna(dtails["LIBELLE"]):
				libelle=str(dtails["LIBELLE"])


			poste = PosteComptable.objects.get(reference= str(dtails["POSTE"]))


			nature="1"
			report = "0"
			gestion=date.today().year
			date_ouverture = datetime.now()
			rg = DateRange(date_ouverture.date(), date_ouverture.date() + timedelta(days=1))
			annee_comptable = AnneeComptable.objects.filter(period__contains=rg).last()

			if not pd.isna(dtails["GESTION"]):
				gestion=int(dtails["GESTION"])
				if date_ouverture.date().year!=gestion:
					traceback.print_exc()
					ex = SigException()
					ex.message = "Date avis different de la gestion"
					raise ex


			try:
				cdd=CompteDepot.objects.get(short_compte=compte_court)




				if report=="0":
					type_avis = "C"
					if type_avis == "C" and type==TYPE_FICHIER.AVITCREDIT_ASTER:
						try:
							AvisDeCredit.objects.get(reference=reference_aster)
						except AvisDeCredit.DoesNotExist:

							avisCredit=AvisDeCredit()
							avisCredit.reference_aster=reference_aster
							avisCredit.reference = reference_aster
							avisCredit.created = date_ouverture

							avisCredit.date_avis=date_ouverture
							avisCredit.compte=cdd
							avisCredit.poste_comptable=poste
							avisCredit.amount=Decimal(dtails["MONTANT"])
							avisCredit.libelle = libelle
							jour_comptable,_created =JourneeComptable.objects.get_or_create(user=admin,annee_comptable=annee_comptable,jour=date_ouverture.date())
							avisCredit.jour_comptable = jour_comptable

							if nature == "1":
								avisCredit.nature=NATURE_COMPTE.FONCTIONNEMENT

								typecpte = TypeCompteTrx.objects.get(code="BF")
							else:
								avisCredit.nature = NATURE_COMPTE.INVESTISSEMENT
								typecpte = TypeCompteTrx.objects.get(code="BI")
							avisCredit.save()
							avisCredit.created = date_ouverture
							avisCredit.typecompte=typecpte
							avisCredit.save()
					if type_avis=="D" and type==TYPE_FICHIER.AVITDEBIT_ASTER:
						try:
							AvisDeDebit.objects.get(reference=reference_aster)
						except AvisDeDebit.DoesNotExist:

							avisCredit = AvisDeDebit()
							avisCredit.reference_aster = reference_aster
							avisCredit.reference = reference_aster
							avisCredit.created = date_ouverture

							avisCredit.date_avis = date_ouverture
							avisCredit.compte = cdd
							avisCredit.poste_comptable = poste
							avisCredit.amount = Decimal(dtails["MONTANT"])
							avisCredit.libelle = libelle
							jour_comptable, _created = JourneeComptable.objects.get_or_create(user=admin,
							                                                                  annee_comptable=annee_comptable,
							                                                                  jour=date_ouverture.date())
							avisCredit.jour_comptable = jour_comptable
							if nature == "1":
								avisCredit.disposition = NATURE_COMPTE.FONCTIONNEMENT
							else:
								avisCredit.disposition = NATURE_COMPTE.INVESTISSEMENT
							avisCredit.save()
							avisCredit.created = date_ouverture
							print("avit de debit créé")
							avisCredit.save()


				if report=="1":
					anne_report = gestion - 1
					x = date(anne_report, 2, 2)

					rg_last = DateRange(x, x + timedelta(days=1))
					annee_comptable_report = AnneeComptable.objects.filter(period__contains=rg_last).last()
					try:
						Report.objects.get(compte=cdd,anne_comptable=annee_comptable_report)
					except Report.DoesNotExist:
						report=Report()
						report.compte=cdd
						report.creator=admin
						report.gestion_courant=annee_comptable
						if nature == "1":
							report.amount_fonc = Decimal(dtails["MONTANT"])
						else:
							report.amount_invest = Decimal(dtails["MONTANT"])

						report.anne_comptable=annee_comptable_report
						report.save()

			except CompteDepot.DoesNotExist:
				pass
		except PosteComptable.DoesNotExist:
			continue
		except :
			traceback.print_exc()
			ex = SigException()
			ex.message = "Erreur inconnue"
			raise ex

def operations_file_aster(datas):
	codeAgence = CodeAgence.objects.get(code="010" )
	agent=ProfileDCP.objects.last()
	admin=User.objects.filter(is_superuser=True).last()

	current_year = AnneeComptable.active_gestion().year()
	i = 1
	is_current_year = False

	index=0
	for dtails in datas:
		try:

			compte_court = str(dtails["COMPTE"])
			if pd.isna(dtails["COMPTE"]) :
				continue
			numero_cheque = "{}-{}".format(time.time(), index)
			index += 1

			observation = str(dtails["LIBELLE"])
			mode_payment ="VIREMENT"#str(dtails["MODEPAIEMENT"])
			beneficiaire=str(dtails["OBSERVATION"])



			poste = PosteComptable.objects.get(reference= str(dtails["POSTE"]))


			type_nature="FONCTIONNEMENT" #str(dtails["TYPE_PAIEMENT"])

			nature_name = observation

			gestion = str(dtails["GESTION"])
			if current_year == gestion:
				is_current_year = True



			date_ouverture = datetime.now()
			try:
				cdd=CompteDepot.objects.get(short_compte=compte_court)
				rg = DateRange(date_ouverture.date(), date_ouverture.date() + timedelta(days=1))
				annee_comptable=AnneeComptable.objects.filter(period__contains=rg).last()

				try:
					OrdrePayment.objects.get(reference=numero_cheque)
				except OrdrePayment.DoesNotExist:

					ordrePayment=OrdrePayment()
					ordrePayment.created = date_ouverture
					ordrePayment.object=observation #libelle[0:120]
					ordrePayment.creator=admin
					ordrePayment.beneficiaire=beneficiaire
					ordrePayment.reference = numero_cheque
					ordrePayment.open_date=date_ouverture.date()
					ordrePayment.compte=cdd
					ordrePayment.observations=observation
					ordrePayment.sig_reference=numero_cheque
					ordrePayment.poste_comptable=poste
					ordrePayment.amount=Decimal(dtails["MONTANT"])
					ordrePayment.libelle = observation
					ordrePayment.secteur=Secteur.objects.last()

					##"NUMERAIRE, VIREMENT,OPERATION ORDRE, COMPENSE"

					if mode_payment=="VIREMENT":
						ordrePayment.payment_mean=PAYMENT_MEAN_TYPE.VIREMENT
					if mode_payment=="COMPENSE":
						ordrePayment.payment_mean=PAYMENT_MEAN_TYPE.CHEQUE
						ordrePayment.cheque=numero_cheque
					if mode_payment=="NUMERAIRE":
						ordrePayment.payment_mean=PAYMENT_MEAN_TYPE.CHEQUE
					if mode_payment=="OPERATION ORDRE":
						ordrePayment.payment_mean=PAYMENT_MEAN_TYPE.VIREMENT

					if not pd.isna(observation):
						nature, created = Nature.objects.get_or_create(name=nature_name[0:50])
						ordrePayment.nature=nature

					jour_comptable,created =JourneeComptable.objects.get_or_create(user=admin,annee_comptable=annee_comptable,jour=date_ouverture.date())

					ordrePayment.jour_comptable = jour_comptable
					if type_nature == "FONCTIONNEMENT":
						ordrePayment.typecompte = TypeCompteTrx.objects.get(code="BF")
						ordrePayment.type_nature=NATURE_COMPTE.FONCTIONNEMENT
					elif type_nature=="INVESTISSEMENT":
						ordrePayment.typecompte = TypeCompteTrx.objects.get(code="BI")
						ordrePayment.type_nature = NATURE_COMPTE.INVESTISSEMENT

					ordrePayment.etape = ETAPE_ORDRE_PAYMENT.VALIDE
					ordrePayment.previous_etape = ETAPE_ORDRE_PAYMENT.SAISIE
					ordrePayment.save()
					ordrePayment.created = date_ouverture
					ordrePayment.save() #force la date

					if ordrePayment.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and ordrePayment.cheque:
						try:
							mark_cheque_as_use_for_op(ordrePayment)
						except SigException as e :pass

					try:
						reservation = ReservationFond()
						reservation.ordre = ordrePayment
						reservation.amount = ordrePayment.amount
						reservation.creator = admin
						if ordrePayment.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT:
							reservation.payment_mean = ordrePayment.payment_mean
						reservation.save()


					except SigException as e:
						raise e

					prise_encharge = PrisEnchageOrdrePayment()
					prise_encharge.ordre = ordrePayment
					prise_encharge.amount = ordrePayment.amount
					prise_encharge.payment_mean = ordrePayment.payment_mean
					prise_encharge.reglement = ordrePayment.reglement
					prise_encharge.creator = admin
					prise_encharge.created = date_ouverture
					prise_encharge.save()
					ordrePayment.date_prise_en_charge = datetime.now()
					ordrePayment.previous_etape = ETAPE_ORDRE_PAYMENT.ACCEPTE
					ordrePayment.etape = ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE
					ordrePayment.observations = observation
					ordrePayment.save()

					try:
						with transaction.atomic():
							amount = ordrePayment.amount.amount
							ordrePayment.reservationfond.can_make_trx_with_amount(amount)
							ordrePayment.jour_comptable = jour_comptable
							trx=TransactionOP()
							trx.reservation=ordrePayment.reservationfond
							trx.amount=Money(int(amount), 'XOF')
							trx.account_depot=ordrePayment.compte.short_compte
							trx.poste_comptable=ordrePayment.compte.poste.reference
							trx.rib_cdd = ordrePayment.compte.compte
							trx.sig_reference=ordrePayment.sig_reference
							trx.origin_reference = ordrePayment.sig_reference
							trx.created=date_ouverture
							trx.account_secondaire="-"
							trx.cheque=ordrePayment.cheque
							trx.agent=admin
							trx.jour_comptable = jour_comptable
							trx.libelle=ordrePayment.object
							trx.sens=SENS_TRX.DEBIT
							trx.payment_mean=ordrePayment.payment_mean
							trx.reglement = TYPE_REGLEMENT.GLOBAL
							trx.nature_depense=ordrePayment.nature.name
							trx.save()
							trx.created = date_ouverture
							trx.save()
					except SigException as e:
						traceback.print_exc()

			except CompteDepot.DoesNotExist:
				pass
		except PosteComptable.DoesNotExist:
			continue
		except :
			traceback.print_exc()
			ex = SigException()
			ex.message = "Erreur inconnue"
			raise ex


def create_chequiers_from_file(datas):
	for dtails in datas:
		try:
			compte_court = str(dtails["COMPTE"])
			if pd.isna(dtails["COMPTE"]) :
				continue
			qte=int(dtails["QTE LIVREE"])
			seq_Deb = int(dtails["seq_Deb"])
			sep_Fin = int(dtails["sep_Fin"])  # car la colon de fin est la la col de debbit de la prochaine ligne
			q=sep_Fin-seq_Deb+1
			taille=int(q/qte)
			#print("{}-{}---{}".format(seq_Deb,sep_Fin,taille))
			typecheque,exi =TypeChequier.objects.get_or_create(nom=str(taille),taille=taille)
			cdd = CompteDepot.objects.get(short_compte=compte_court)

			for i in range(0, qte, 1):
				debut = seq_Deb+i*taille
				fin = debut +taille-1
				try:
					Chequier.objects.get(reference=str(debut))
					continue
				except Chequier.DoesNotExist:
					item = Chequier()
					item.reference = debut
					item.compte = cdd
					item.demande = debut
					item.dap = DAP.object()
					item.fin = fin
					item.debut = debut
					item.type = typecheque
					item.taille = typecheque.taille
					item.delivered=True
					item.distribue=True
					item.prise_en_charge=True
					item.activate_date=datetime.now()
					item.delivered_date=datetime.now()
					item.distribue_date=datetime.now()
					item.prise_en_charge_date=datetime.now()
					item.save()

					for i in range(item.debut, item.fin + 1, 1):
						refcheque="0{}".format(str(i),)
						try:
							Cheque.objects.get(reference=refcheque)
							#print(" trouve {}".format(i))
						except Cheque.DoesNotExist:
							#print("non trouve {}".format(i))
							cheque = Cheque()
							cheque.chequier = item
							cheque.reference = refcheque
							cheque.actif = True
							cheque.observations = ""
							cheque.save()
		except CompteDepot.DoesNotExist:
			pass
		except PosteComptable.DoesNotExist:
			continue
		except :
			logger.error("Chequier non traite : {}".format(dtails))
			traceback.print_exc()
			ex = SigException()
			ex.message = "Erreur inconnue"
			raise ex



def mark_cheque_as_use_for_op(ordrepayment):
	try:
		cheque = Cheque.objects.get(reference=ordrepayment.cheque)
		if not cheque.can_use_in_op():
			raise SigException('Réference chèque invalide : {}'.format(cheque, ))
		cheque.use=True
		cheque.amount=ordrepayment.amount
		cheque.cin_receptionnaire=ordrepayment.cin_receptionnaire
		if ordrepayment.phone_receptionnaire:
			cheque.phone_receptionnaire=ordrepayment.phone_receptionnaire.as_e164
		cheque.trx=ordrepayment.reference
		cheque.use_date=datetime.now()
		if ordrepayment.receptionnaire and ordrepayment.depositaire:
			cheque.endosser_par = ordrepayment.depositaire.full_name()
			cheque.phone_receptionnaire = ordrepayment.depositaire.phone.as_e164
			cheque.cin_receptionnaire = ordrepayment.depositaire.nin
		else : cheque.endosser_par=ordrepayment.beneficiaire
		cheque.save()

	except SigException as e: raise e

	except Cheque.DoesNotExist:
		pass
	except:
		traceback.print_exc()
		raise SigException('Réference chèque introuvable')




def get_diff_file(id):
	ob = FichierData.objects.get(id=id)
	filehandle = ob.fichier
	type = ob.type
	df = pd.read_excel(filehandle, dtype=pd.StringDtype())
	marks_list = df['NUMCHEQUE'].tolist()
	sig_list = df['sig_reference'].tolist()
	dif=[]
	for i in marks_list:
		print(i)
		i = i.replace("/", "_")
		if i not in sig_list:
			dif.append(i)
	return dif



def fix_op():
	ops=OrdrePayment.objects.filter(payment_mean=PAYMENT_MEAN_TYPE.CHEQUE)
	for op in ops:
		op.sig_reference= op.sig_reference.split("-")[0]
		op.save()


def create_ministere_from_file(datas,headers):
	set_h=set(headers)

	correct_set={"CODE SECTION","LIBELLE SECTION","CODE CHAPITRE","LIBELLE CHAPITRE","TYPE SERVICE"}
	x=correct_set.difference(set_h)
	if len(x)>0:
		traceback.print_exc()
		ex = SigException(message="Champs obligatoires{}".format(x,))
		raise ex

	for dtails in datas:
		try:
			code_ministere = str(dtails["CODE SECTION"])
			lib_ministere = str(dtails["LIBELLE SECTION"])
			code_structure = str(dtails["CODE CHAPITRE"])
			lib_structure = str(dtails["LIBELLE CHAPITRE"])
			type_stucture = str(dtails["TYPE SERVICE"])
			try:
				ministere=Ministere.objects.get(reference=code_ministere)
			except Ministere.DoesNotExist:
				ministere=Ministere()
				ministere.reference=code_ministere
				ministere.name=lib_ministere
				ministere.actif=True
				ministere.save()
			try:
				Structure.objects.get(reference=code_structure)
			except Structure.DoesNotExist:
				structure = Structure()
				structure.ministere=ministere
				structure.reference=code_structure
				structure.name=lib_structure
				structure.save()
		except :
			traceback.print_exc()
			ex = SigException()
			ex.message = "Erreur inconnue"
			raise ex

from io import BytesIO
from django.db.models import Sum, IntegerField,F, CharField,ExpressionWrapper
import collections



def generate_sitdisp(user):
	d=CompteDepot.objects.by_agent(User.objects.get(id=user))

	d = d.values("short_compte").annotate(
		balance_fonct=Sum('balance_fonct', output_field=IntegerField()),
		balance=Sum('balance', output_field=IntegerField()),
		balance_insvest=Sum('balance_insvest', output_field=IntegerField()),
		libelle=ExpressionWrapper(F("libelle"), output_field=CharField())
	)
	d = sorted(list(d), key=lambda k: k['short_compte'], reverse=False)

	my_dict = collections.Counter()

	for item in d:
		for key, value in item.items():
			if key in ["balance_fonct", "balance_insvest", "balance"]:
				my_dict[key] += value


	if len(d) > 0:
		df = pd.DataFrame(data=d)
		df.loc['Total'] = df[['balance_fonct', 'balance_insvest','balance']].sum()
		df = df.fillna('')
		df.rename(columns={"balance":"SOLDE","libelle":"LIELLE","short_compte": "COMPTE", "balance_insvest": "INVESTISSEMENT","balance_fonct":"FONCTIONNEMENT"},inplace=True)

		cols = ['COMPTE', 'LIELLE', 'FONCTIONNEMENT', 'INVESTISSEMENT','SOLDE']
		df = df[cols]
		return df
	else: return pd.DataFrame()

def generate_and_send_sitdisp(user,list_mail):
	df=generate_sitdisp(user)
	if df:
		with BytesIO() as b:
			# Use the StringIO object as the filehandle.
			writer = pd.ExcelWriter(b)
			df.to_excel(writer, sheet_name='situationdispo')
			writer.save()
			filename = 'situation_disponible_{}'.format(datetime.now())
			content_disposition = 'attachment; filename="' + filename + '.xlsx"'

			attachment = MIMEApplication(b.getvalue())
			attachment["Content-Disposition"] = content_disposition
			start_date = "{:%d-%m-%Y}".format(date.today(), )
			title="Situation de disponible à la date du {}".format(start_date)
			send_email(list_mail,title,attachment)



from django.conf import settings

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib


def send_email(send_to, subject, attachment):
	send_from = settings.EMAIL_HOST_USER
	password = settings.EMAIL_HOST_PASSWORD
	message = """\
    <p>Bonjour,&nbsp;<br> Ci joint la situation des disponibles du jour.</p>
    <p><br></p>
    <p><strong>MINISTERE DES FINANCES ET DU BUDGET&nbsp;</strong><br><strong>DIRECTION GENERALE DE LA COMPTABILITE PUBLIQUE ET DU TRESOR&nbsp;    </strong></p>
    """
	for receiver in send_to:
		multipart = MIMEMultipart()
		multipart["From"] = send_from
		multipart["To"] = receiver
		multipart["Subject"] = subject
		multipart.attach(attachment)
		multipart.attach(MIMEText(message, "html"))
		server = smtplib.SMTP("smtp.gmail.com", 587)
		server.starttls()
		server.login(multipart["From"], password)
		server.sendmail(multipart["From"], multipart["To"], multipart.as_string())
		server.quit()




import re


def get_date_from_pattern(d):
	pattern1 = r'\d{2}/\d{2}/\d{4}'
	pattern2 = r'\d{4}-\d{2}-\d{2}'
	match = re.search(pattern1, d)
	match1 = re.search(pattern2, d)
	if match: format="%d/%m/%Y"
	if match1 : format="%Y-%m-%d %H:%M:%S"
	try:
		return datetime.strptime(d, format)
	except ValueError:

		return datetime.now()


def get_date(d):
	if len(d.split("/"))>2:
		format="%d/%m/%Y"
	elif len(d.split("-"))>2: format="%Y-%m-%d %H:%M:%S"

	try:
		return datetime.strptime(d, format)
	except ValueError:

		return datetime.now()