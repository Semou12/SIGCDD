from datetime import datetime,date ,timedelta
import hashlib
import traceback

import pandas as pd
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render,redirect
from tablib import Dataset

from cddaccount.forms import ChargementFichierForm, ChargementFichierIbanForm, EmailForm, DeleteOPByPCForm
from cddaccount.models import CompteDepot, generate_rib, Bank, CodeAgence, AvisDeCredit, Report, ValidationCompte, \
	AnneeComptable, JourneeComptable, OrdrePayment, Nature, FichierData, TransactionOP, AvisDeDebit
from core.models import PosteComptable

from helpers.exceptions import SigException

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required


from helpers.models import Role


@login_required
def chargement_view(request):
	template = "cddaccount/chargement_view.html"
	user = request.user
	if user.role!=Role.ADMIN:
		raise Http404

	if request.method == 'POST':
		form = ChargementFichierForm(request.POST,request.FILES)#PriseEnChargeOrdrePaymentModelForm(request.POST, request.FILES,instance=ordre_payment)
		if form.is_valid():

			type = form.cleaned_data["type"]
			filehandle = request.FILES["details_file"]
			try:
				fichier_data=FichierData()
				fichier_data.fichier=filehandle
				fichier_data.type=type
				fichier_data.name="{}--{}".format(type,datetime.now())
				fichier_data.save()
				chargement_items_excel_file(fichier_data.id)
				messages.success(request, "chargement effectif avec succès" )
			except SigException as e:
				messages.error(request, e.message,extra_tags="danger")
			return HttpResponseRedirect("#")
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg,extra_tags="danger")
	else:
		form = ChargementFichierForm()#PriseEnChargeOrdrePaymentModelForm(instance=ordre_payment)

	context = {"form": form, 'title': "Chargement fichier"}
	return render(request, template, context)


def chargement_items_excel_file(id):
	from cddaccount.tasks import async_loading_data
	async_loading_data.delay(id)



import xlwt
from io import BytesIO
from django.http import HttpResponse
@login_required
def verify_iban(request):
	template = "cddaccount/verify_iban_view.html"
	user = request.user


	if request.method == 'POST':
		form = ChargementFichierIbanForm(request.POST,request.FILES)#PriseEnChargeOrdrePaymentModelForm(request.POST, request.FILES,instance=ordre_payment)
		if form.is_valid():
			filehandle = request.FILES["details_file"]
			try:
				c=verify_ibans_excel_file(filehandle)
				if len(c)>0:
					df = pd.DataFrame(data=c)

					with BytesIO() as b:
						# Use the StringIO object as the filehandle.
						writer = pd.ExcelWriter(b)
						df.to_excel(writer, sheet_name='iban')
						writer.save()
						filename = 'virementmasse_mauvais_iban_{}'.format(datetime.now())
						content_type = 'application/vnd.ms-excel'
						response = HttpResponse(b.getvalue(), content_type=content_type)
						response['Content-Disposition'] = 'attachment; filename="' + filename + '.xlsx"'
						return response

				else:

					messages.success(request, "Le fichier est correct" )
			except SigException as e:
				messages.error(request, e.message,extra_tags="danger")
			return HttpResponseRedirect("#")
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg,extra_tags="danger")
	else:
		form = ChargementFichierIbanForm()#PriseEnChargeOrdrePaymentModelForm(instance=ordre_payment)

	context = {"form": form, 'title': "Chargement fichier"}
	return render(request, template, context)





def verify_ibans_excel_file(filehandle):
	df = pd.read_excel(filehandle, dtype=pd.StringDtype())
	dataset = Dataset().load(df)
	detailvirements = dataset.dict
	invalide_ribs=[]
	for dtails in detailvirements:
		try:
			phone=None
			banque = str(dtails["BANQUE"])
			agence = str(dtails["AGENCE"])
			account = str(dtails["COMPTE"])
			rib = str(dtails["RIB"])
			rib_beneficiaire = "{}{}{}{}".format(banque,agence,account,rib)
			iban = rib_beneficiaire
			if iban and len(iban) > 0:
				country_code = iban[:2]
				rib = iban[-2:]
				cal_rib = generate_rib(country_code, iban)
				if rib != cal_rib:
					invalide_ribs.append(dtails)
		except:
			pass
	return invalide_ribs




from django.urls import reverse_lazy, reverse
@login_required
def generate_and_send_sitdisponible_in_excel(request):
	template = "core/add_entity.html"
	user = request.user
	success_url = reverse_lazy('cddaccount:disponible_situation_view')

	if request.method == 'POST':
		form = EmailForm(request.POST)
		if form.is_valid():
			email = form.cleaned_data["email"]
			try:
				from cddaccount.tasks import async_generate_and_send_sitdisp
				async_generate_and_send_sitdisp.delay(user.id,[email])
				messages.success(request, "Fichier envoyé par email " )
			except SigException as e:
				messages.error(request, e.message,extra_tags="danger")
			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg,extra_tags="danger")
	else:
		form = EmailForm()

	context = {"form": form, 'title': "Chargement fichier"}
	return render(request, template, context)



@login_required
def generate_sitdisponible_in_excel(request):
	template = "core/add_entity.html"
	user = request.user
	success_url = reverse_lazy('cddaccount:disponible_situation_view')

	try:
		from cddaccount.chargement_process import generate_sitdisp
		df = generate_sitdisp(user.id)
		if not df.empty:
			messages.success(request, "Fichier généré avec succès")
			with BytesIO() as b:
				print("sdfsdsd")
				# Use the StringIO object as the filehandle.
				#writer = pd.ExcelWriter(b)
				#writer = pd.ExcelWriter(b, engine='xlsxwriter')
				with pd.ExcelWriter(b) as writer:
					df.to_excel(writer, sheet_name="Data", index=False)
				#df.to_excel(writer, sheet_name='iban')
				#writer.save()
				filename = 'situation_disponible_{}'.format(datetime.now())
				content_type = 'application/vnd.ms-excel'
				response = HttpResponse(b.getvalue(), content_type=content_type)
				response['Content-Disposition'] = 'attachment; filename="' + filename + '.xlsx"'
				print("fss")
				return response
		else:
			messages.error(request, "Fichier non généré ")


	except SigException as e:
		messages.error(request, e.message,extra_tags="danger")
	except:
		traceback.print_exc()
	return redirect(success_url)


from django.db.models import Sum, Count, IntegerField, F, Value, ExpressionWrapper, CharField, Func,DateField
from django.contrib import messages

from django.db.models.functions import Coalesce
import collections, operator,itertools

@login_required
def generate_opvise_in_excel(request):
	template = "core/add_entity.html"
	user = request.user
	success_url = reverse_lazy('cddaccount:repport_op_vise_view')

	try:

		if hasattr(user, "agent_postecomptable"):
			poste = user.agent_postecomptable.poste
		else:
			poste_comptable = request.GET.get('poste', None)
			if poste_comptable is None:
				poste = PosteComptable.defaultobject()
			else:
				poste = PosteComptable.objects.get(reference=poste_comptable)
		poste_comptable = poste.reference
		poste_comptable_name = poste.name

		gestion_v = request.GET.get('gestion', None)
		if gestion_v is None:
			gestionO = AnneeComptable.active_gestion()
			gestion_v = gestionO.id

		else:
			gestionO = AnneeComptable.objects.get(id=gestion_v)

		qdatevisa = request.GET.get('qstartdate', None)
		if qdatevisa is None:
			datevisa = datetime.now()
		else:
			format = "%Y-%m-%d"
			datevisa = datetime.strptime(qdatevisa, format)



		qdatevisa2 = request.GET.get('qenddate', None)
		if qdatevisa2 is None:
			datevisa2 = date.today()
		else:
			format = "%Y-%m-%d"
			datevisa2 = datetime.strptime(qdatevisa2, format)

		compte_v = request.GET.get('compte', None)

		vd = "{:%Y-%m-%d}".format(datevisa, )

		last_rg = (datevisa, datevisa2 + timedelta(days=1))

		print(last_rg)

		s = "{:%Y-%m-%d}".format(datevisa, )
		end = "{:%Y-%m-%d}".format(datevisa2, )

		vd = "{:%Y-%m-%d}".format(datevisa, )
		# url_report_pdf = "{}?qdatevisa={}&gestion={}".format(reverse_lazy('cddaccount:repport_op_vise_pdf_view'), vd,gestionO.id)

		if compte_v:
			# url_report_pdf="{}&compte={}".format(url_report_pdf,compte_v)
			objs = TransactionOP.objects.by_agent(user).filter(jour_comptable__annee_comptable__id=gestion_v,
			                                                   jour_comptable__jour__range=last_rg,
			                                                   poste_comptable=poste_comptable,
			                                                   reservation__ordre__compte_id=compte_v)
		else:
			objs = TransactionOP.objects.by_agent(user).filter(jour_comptable__annee_comptable__id=gestion_v,
			                                                   jour_comptable__jour__range=last_rg,
			                                                   poste_comptable=poste_comptable)

		# d= objs.values("account_depot","reference","reservation__ordre__beneficiaire","libelle","amount")

		d = objs.values("reservation__ordre__sig_reference").annotate(
			amount=Sum('amount', output_field=IntegerField()),
			reservation__ordre__beneficiaire=ExpressionWrapper(F("reservation__ordre__beneficiaire"),
			                                                   output_field=CharField()),
			account_depot=ExpressionWrapper(F("reservation__ordre__compte__short_compte"), output_field=CharField()),
			reference=ExpressionWrapper(F("reservation__ordre__sig_reference"), output_field=CharField()),
			libelle=ExpressionWrapper(F("reservation__ordre__object"), output_field=CharField()),
			nature=ExpressionWrapper(F("payment_mean"), output_field=CharField()))


		datas_r = sorted(list(d), key=lambda k: k['nature'], reverse=False)
		z = {"amount": 0}
		x = []
		total_general = 0
		ligne_general = 0
		for key, cpts in itertools.groupby(datas_r, operator.itemgetter('nature')):
			c = list(cpts)
			my_dict = collections.Counter()
			ligne = 0
			for item in c:
				ligne += 1
				for _key, value in item.items():
					if _key in ["amount"]:
						my_dict[_key] += value
						total_general += value
			ligne_general += ligne
			x.append({"NATURE": key,  "MONTANT": my_dict["amount"]})

		str_date = "{:%d/%m/%Y}".format(datetime.now())
		# visa_date = "{:%d/%m/%Y}".format(datevisa)
		visa_date = "{:%d/%m/%Y} - {:%d/%m/%Y}".format(datevisa, datevisa2)

		if len(d) > 0:
			df = pd.DataFrame(data=d)
			#df.loc['Total'] = df[['balance_fonct', 'balance_insvest', 'balance']].sum()
			df = df.fillna('')
			df.rename(columns={"nature":"NATURE","amount": "MONTANT", "libelle": "LIELLE", "account_depot": "N° COMPTE","reservation__ordre__beneficiaire": "BÉNÉFICIAIRE", "reference": "N° OPÉRATION"}, inplace=True)

			cols = ['N° COMPTE', 'N° OPÉRATION', 'NATURE', 'BÉNÉFICIAIRE', 'MONTANT']
			df = df[cols]

		else:
			df= pd.DataFrame()

		if len(x) > 0:
			df1 = pd.DataFrame(data=x)

		else:df1 = pd.DataFrame()



		#df = generate_sitdisp(user.id)
		if not df.empty:
			messages.success(request, "Fichier généré avec succès")
			with BytesIO() as b:
				with pd.ExcelWriter(b) as writer:
					df.to_excel(writer, sheet_name="OPERATIONS VISES", index=False)
					if not df1.empty:
						df1.to_excel(writer, sheet_name="RECAPITULATION", index=False)

				filename = 'operation_vise_{}'.format(visa_date,)
				content_type = 'application/vnd.ms-excel'
				response = HttpResponse(b.getvalue(), content_type=content_type)
				response['Content-Disposition'] = 'attachment; filename="' + filename + '.xlsx"'

				return response
		else:
			messages.error(request, "Fichier non généré ")


	except SigException as e:
		messages.error(request, e.message,extra_tags="danger")
	except:
		traceback.print_exc()
	return redirect(success_url)









@login_required
def generate_report_aviscredit_in_excel(request):
	template = "core/add_entity.html"
	user = request.user
	success_url = reverse_lazy('cddaccount:report_aviscredit_compte_view')

	try:

		if hasattr(user, "agent_postecomptable"):
			poste = user.agent_postecomptable.poste
		else:
			poste_comptable = request.GET.get('poste', None)
			if poste_comptable is None:
				poste = PosteComptable.defaultobject()
			else:
				poste = PosteComptable.objects.get(reference=poste_comptable)
		poste_comptable = poste.reference

		gestion_v = request.GET.get('gestion', None)
		if gestion_v is None:
			gestionO = AnneeComptable.active_gestion()
			gestion_v = gestionO.id
		else:
			gestionO = AnneeComptable.objects.get(id=gestion_v)

		compte = request.GET.get('compte', None)

		qenddate = request.GET.get('qenddate', None)
		if qenddate is None:
			enddate = datetime.now()
		else:
			format = "%Y-%m-%d"
			enddate = datetime.strptime(qenddate, format)
		qstartdate = request.GET.get('qstartdate', None)
		if qstartdate is None:
			startdate = datetime.now()
		else:
			format = "%Y-%m-%d"
			startdate = datetime.strptime(qstartdate, format)


		visa_date = "{:%d/%m/%Y} - {:%d/%m/%Y}".format(startdate, enddate)

		if qstartdate is None:
			qstartdate = date.today().strftime('%Y-%m-%d')
		datedebut = datetime.strptime(qstartdate, '%Y-%m-%d')
		if qenddate is None:
			qenddate = date.today().strftime('%Y-%m-%d')
		datefin = datetime.strptime(qenddate, '%Y-%m-%d')
		gestion = gestionO.year()

		mylist = []
		listCompte = []
		totalDesAvis = 0
		if compte is None:
			listCompte = CompteDepot.objects.by_agent(user).filter(poste__reference=poste_comptable).values(
				"short_compte", "libelle")
			list_avis_credit = AvisDeCredit.objects.by_agent(user).filter(date_avis__year=gestion,jour_comptable__annee_comptable_id=gestionO.id,
			                                                              date_avis__range=(datedebut, datefin))
		else:
			compteSelect = CompteDepot.objects.get(short_compte=compte)
			list_avis_credit = AvisDeCredit.objects.by_agent(user).filter(compte__short_compte=compte,
			                                                              date_avis__year=gestion,jour_comptable__annee_comptable_id=gestionO.id,
			                                                              date_avis__range=(datedebut, datefin))



		#d=list_avis_credit.values("amount","compte__short_compte","date_avis","libelle","reference_aster","nature")
		d = list_avis_credit.values("id").annotate(
			reference_aster=ExpressionWrapper(F("reference_aster"), output_field=CharField()),
			libelle=ExpressionWrapper(F("libelle"), output_field=CharField()),
			date_avis=ExpressionWrapper(F("date_avis"), output_field=DateField()),
			amount=ExpressionWrapper(F("amount"), output_field=IntegerField()),
			nature=ExpressionWrapper(F("nature"), output_field=CharField()),
			short_compte=ExpressionWrapper(F("compte__short_compte"), output_field=CharField())
		)


		if len(d) > 0:
			df = pd.DataFrame(data=d)
			#df.loc['Total'] = df[['balance_fonct', 'balance_insvest', 'balance']].sum()
			df = df.fillna('')
			df.rename(columns={"date_avis":"DATE","reference_aster":"N° AVIS","amount": "MONTANT", "libelle": "LIBELLE", "short_compte": "N° COMPTE","nature": "NATURE"}, inplace=True)

			cols = ["N° AVIS" ,"N° COMPTE","NATURE" ,"MONTANT" ,"DATE" ,"LIBELLE"]
			df = df[cols]

		else:
			df= pd.DataFrame()




		#df = generate_sitdisp(user.id)
		if not df.empty:
			messages.success(request, "Fichier généré avec succès")
			with BytesIO() as b:
				with pd.ExcelWriter(b) as writer:
					df.to_excel(writer, sheet_name="OPERATIONS VISES", index=False)


				filename = 'avis_credits_{}'.format(visa_date,)
				content_type = 'application/vnd.ms-excel'
				response = HttpResponse(b.getvalue(), content_type=content_type)
				response['Content-Disposition'] = 'attachment; filename="' + filename + '.xlsx"'

				return response
		else:
			messages.error(request, "Fichier non généré ")


	except SigException as e:
		messages.error(request, e.message,extra_tags="danger")
	except:
		traceback.print_exc()
	return redirect(success_url)


@login_required
def generate_report_avisdebit_in_excel(request):
	template = "core/add_entity.html"
	user = request.user
	success_url = reverse_lazy('cddaccount:avisdedebit_report_view')

	try:

		if hasattr(user, "agent_postecomptable"):
			poste = user.agent_postecomptable.poste
		else:
			poste_comptable = request.GET.get('poste', None)
			if poste_comptable is None:
				poste = PosteComptable.defaultobject()
			else:
				poste = PosteComptable.objects.get(reference=poste_comptable)
		poste_comptable = poste.reference

		gestion_v = request.GET.get('gestion', None)
		if gestion_v is None:
			gestionO = AnneeComptable.active_gestion()
			gestion_v = gestionO.id
		else:
			gestionO = AnneeComptable.objects.get(id=gestion_v)

		compte = request.GET.get('compte', None)

		qenddate = request.GET.get('qenddate', None)
		if qenddate is None:
			enddate = datetime.now()
		else:
			format = "%Y-%m-%d"
			enddate = datetime.strptime(qenddate, format)
		qstartdate = request.GET.get('qstartdate', None)
		if qstartdate is None:
			startdate = datetime.now()
		else:
			format = "%Y-%m-%d"
			startdate = datetime.strptime(qstartdate, format)

		visa_date = "{:%d/%m/%Y} - {:%d/%m/%Y}".format(startdate, enddate)

		if qstartdate is None:
			qstartdate = date.today().strftime('%Y-%m-%d')
		datedebut = datetime.strptime(qstartdate, '%Y-%m-%d')
		if qenddate is None:
			qenddate = date.today().strftime('%Y-%m-%d')
		datefin = datetime.strptime(qenddate, '%Y-%m-%d')
		gestion = gestionO.year()


		if compte is None:
			listCompte = CompteDepot.objects.by_agent(user).filter(poste__reference=poste_comptable).values(
				"short_compte", "libelle")
			list_avis_credit = AvisDeDebit.objects.by_agent(user).filter(date_avis__year=gestion,jour_comptable__annee_comptable_id=gestionO.id,
			                                                              date_avis__range=(datedebut, datefin))
		else:
			list_avis_credit = AvisDeDebit.objects.by_agent(user).filter(compte__short_compte=compte,jour_comptable__annee_comptable_id=gestionO.id,
			                                                              date_avis__year=gestion,
			                                                              date_avis__range=(datedebut, datefin))

		#d = list_avis_credit.values("amount", "compte__short_compte", "date_avis", "libelle", "reference_aster","disposition")
		d = list_avis_credit.values("id").annotate(
			reference_aster=ExpressionWrapper(F("reference_aster"), output_field=CharField()),
			libelle=ExpressionWrapper(F("libelle"), output_field=CharField()),
			date_avis=ExpressionWrapper(F("date_avis"), output_field=DateField()),
			amount=ExpressionWrapper(F("amount"), output_field=IntegerField()),
			disposition=ExpressionWrapper(F("disposition"), output_field=CharField()),
			short_compte=ExpressionWrapper(F("compte__short_compte"), output_field=CharField())
		)

		if len(d) > 0:
			df = pd.DataFrame(data=d)
			# df.loc['Total'] = df[['balance_fonct', 'balance_insvest', 'balance']].sum()
			df = df.fillna('')
			df.rename(
				columns={"date_avis": "DATE", "reference_aster": "N° AVIS", "amount": "MONTANT", "libelle": "LIBELLE",
				         "short_compte": "N° COMPTE", "disposition": "NATURE"}, inplace=True)

			cols = ["N° AVIS", "N° COMPTE", "NATURE", "MONTANT", "DATE", "LIBELLE"]
			df = df[cols]

		else:
			df = pd.DataFrame()

		# df = generate_sitdisp(user.id)
		if not df.empty:
			messages.success(request, "Fichier généré avec succès")
			with BytesIO() as b:
				with pd.ExcelWriter(b) as writer:
					df.to_excel(writer, sheet_name="OPERATIONS VISES", index=False)

				filename = 'avis_debit_{}'.format(visa_date, )
				content_type = 'application/vnd.ms-excel'
				response = HttpResponse(b.getvalue(), content_type=content_type)
				response['Content-Disposition'] = 'attachment; filename="' + filename + '.xlsx"'

				return response
		else:
			messages.error(request, "Fichier non généré ")


	except SigException as e:
		messages.error(request, e.message, extra_tags="danger")
	except:
		traceback.print_exc()
	return redirect(success_url)