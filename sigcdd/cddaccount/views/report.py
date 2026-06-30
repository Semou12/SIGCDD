
import datetime
import traceback ,logging
from bootstrap_modal_forms.utils import is_ajax
from django.contrib.auth.decorators import login_required
from django.db.models.functions import Coalesce
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
import collections, operator, itertools
from django.http import HttpResponse
from cddaccount.models import Report,ReportGestion, BlocageFond,  AvisDeDebit, AvisDeCredit,TransactionOP, ReservationFond, CompteDepot, OrdrePayment, PrisEnchageOrdrePayment,ETAPE_ORDRE_PAYMENT, Transaction, AnneeComptable,  update_newbalance_by_date
from core.models import  PosteComptable
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa
from cddaccount import update, NATURE_COMPTE, PAYMENT_MEAN_TYPE

logger = logging.getLogger(__name__)
from cddaccount.forms import BalanceForm, OpViseForm, OPbyNatureForm, NewDisponibleForm, AvisDebitForm, \
	AvisCreditFiltreForm, MoyenPaiementForm, ChequesPartielVisesForm, SeeSoldeOrdrePaymentModelForm, \
	AvisCreditFiltreTGForm, AvisDebitTGForm, OPbyNatureTGForm, \
	NewDisponibleTGForm, OpViseTGForm, ChequesPartielVisesTGForm, BalanceTGForm, OpViseWithAmountForm

from django.db.models import Case, When,Sum, Count, IntegerField, F, ExpressionWrapper, CharField, DateField,Value,DurationField
from django.contrib import messages


PAGINATION_SIZE = 50
@login_required
def genere_repport_avisdebit_view(request):
	template = "cddaccount/report_form.html"
	user = request.user
	success_url = reverse_lazy('cddaccount:genere_repport_avisdebit_view')

	if request.method == 'POST':

		if hasattr(user, "agent_postecomptable"):
			form = AvisDebitForm(request.POST)
			lisComptesUser = CompteDepot.objects.by_agent(user)
			poste = user.agent_postecomptable.poste
			form.fields["comptes"].queryset = lisComptesUser
		else:
			form = AvisDebitTGForm(request.POST)

		if form.is_valid():
			if request and not is_ajax(request.META):
				date_rg = form.cleaned_data['period']
				gestion = form.cleaned_data['gestion']
				compte = form.cleaned_data['comptes']

				startdate, enddate = date_rg.lower, date_rg.upper

				str_date = "{:%Y-%m-%d}".format(startdate)
				end_date = "{:%Y-%m-%d}".format(enddate)

				if compte is None:
					if "postes" in form.cleaned_data:
						poste = form.cleaned_data['postes']
					success_url = "{}?qstartdate={}&qenddate={}&gestion={}&poste={}".format(
						reverse_lazy('cddaccount:avisdedebit_report_view'), str_date, end_date, gestion.id,
						poste.reference)
				else:
					success_url = "{}?qstartdate={}&qenddate={}&gestion={}&compte={}&poste={}".format(
						reverse_lazy('cddaccount:avisdedebit_report_view'), str_date, end_date, gestion.id,
						compte.short_compte, compte.poste.reference)

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		form = AvisDebitForm()
		if hasattr(user, "agent_postecomptable"):
			form = AvisDebitForm()
			lisComptesUser = CompteDepot.objects.by_agent(user)
			form.fields["comptes"].queryset = lisComptesUser
		else:
			form = AvisDebitTGForm()

	context = {"form": form, 'title': "Indiquer les critères de recherche", }
	return render(request, template, context)


@login_required
def genere_repport_op_paye_view(request):
	template = "core/add_entity.html"

	success_url = reverse_lazy('cddaccount:genere_repport_op_paye_view')

	if request.method == 'POST':
		form = MoyenPaiementForm(request.POST)

		if form.is_valid():
			if request and not is_ajax(request.META):
				date_rg = form.cleaned_data['period']
				gestion = form.cleaned_data['gestion']
				moyenpay = form.cleaned_data['payment_mean']
				startdate, enddate = date_rg.lower, date_rg.upper

				str_date = "{:%Y-%m-%d}".format(startdate)
				end_date = "{:%Y-%m-%d}".format(enddate)

				if moyenpay is None:
					success_url = "{}?qstartdate={}&qenddate={}&gestion={}".format(
						reverse_lazy('cddaccount:repport_op_paye_view'), str_date, end_date, gestion.id)
				else:
					success_url = "{}?qstartdate={}&qenddate={}&gestion={}&payment_mean={}".format(
						reverse_lazy('cddaccount:repport_op_paye_view'), str_date, end_date, gestion.id, moyenpay)

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		form = MoyenPaiementForm()

	context = {"form": form, 'title': "Indiquer les critères de recherche", }
	return render(request, template, context)


@login_required
def avisdedebit_report_view(request):
	template = "cddaccount/repport_avis_debit.html"
	# gestion= AnneeComptable.active_gestion().id
	user = request.user
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
	else:
		gestionO = AnneeComptable.objects.get(id=gestion_v)

	qenddate = request.GET.get('qenddate', None)
	if qenddate is None:
		enddate = datetime.datetime.now()
	else:
		format = "%Y-%m-%d"
		enddate = datetime.datetime.strptime(qenddate, format)
	qstartdate = request.GET.get('qstartdate', None)
	if qstartdate is None:
		startdate = datetime.datetime.now()
	else:
		format = "%Y-%m-%d"
		startdate = datetime.datetime.strptime(qstartdate, format)

	last_rg = (startdate, enddate)

	compte_v = request.GET.get('compte', None)

	if compte_v:

		objs = AvisDeDebit.objects.by_agent(user).filter(jour_comptable__annee_comptable_id=gestion_v,
		                                                 created__range=last_rg, compte__short_compte=compte_v)
	else:
		objs = AvisDeDebit.objects.by_agent(user).filter(jour_comptable__annee_comptable_id=gestion_v,
		                                                 created__range=last_rg, poste_comptable=poste_comptable)

	d = objs.values("compte_id").annotate(
		total=Sum('amount', output_field=IntegerField()),
		reference=ExpressionWrapper(F("reference"), output_field=CharField()),
		libelle=ExpressionWrapper(F("libelle"), output_field=CharField()),
		date_avis=ExpressionWrapper(F("date_avis"), output_field=DateField()),
		amount=ExpressionWrapper(F("amount"), output_field=IntegerField()),
		disposition=ExpressionWrapper(F("disposition"), output_field=CharField()),
		short_compte=ExpressionWrapper(F("compte__short_compte"), output_field=CharField()),
		libelle_court=ExpressionWrapper(F("compte__libelle"), output_field=CharField())
	)

	# d = objs.values("reference","libelle","date_avis","disposition","amount","compte__short_compte", "compte__libelle")

	datas_r = sorted(list(d), key=lambda k: k['short_compte'], reverse=False)
	z = {"short_compte": 0}
	x = []
	total_general = 0
	ligne_general = 0

	for key, cpts in itertools.groupby(datas_r, operator.itemgetter('short_compte')):
		c = list(cpts)
		ligne_general += len(c)
		total = 0

		libelle_court = c[0]["libelle_court"]
		shortcompte = c[0]["short_compte"]
		for item in c:

			# recap=update(recap,item)
			for _key, value in item.items():
				if _key in ["amount"]:
					total += int(value)

		x.append(
			{"compte_v": key, "shortcompte": shortcompte, "libelle_court": libelle_court, "items": c, "total": total, })

		total_general += int(total)

	str_date = "{:%d/%m/%Y}".format(enddate)
	start_date = "{:%d/%m/%Y}".format(startdate)
	end_date = "{:%d/%m/%Y}".format(enddate)
	gestion = gestionO.year()
	url_rb = reverse_lazy('cddaccount:genere_repport_avisdebit_view')
	Title = 'AVIS DE DÉBIT'

	v_str1 = str(startdate.strftime("%Y-%m-%d"));
	v_str2 = str(enddate.strftime("%Y-%m-%d"))
	vstr3 = str(gestionO.id)

	url_excel_rb = reverse_lazy('cddaccount:generate_report_avisdebit_in_excel')
	if compte_v:
		url_excel_rb = url_excel_rb + "?qstartdate=" + v_str1 + "&qenddate=" + v_str2 + "&gestion=" + vstr3 + "&poste=" + poste_comptable + "&compte=" + compte_v
		url_report_pdf = "pdf/?format=pdf&qstartdate=" + v_str1 + "&qenddate=" + v_str2 + "&gestion=" + vstr3 + "&poste=" + poste_comptable + "&compte=" + compte_v
	else:
		url_report_pdf = "pdf/?format=pdf&qstartdate=" + v_str1 + "&qenddate=" + v_str2 + "&gestion=" + vstr3 + "&poste=" + poste_comptable + "&compte="
		url_excel_rb = url_excel_rb + "?qstartdate=" + v_str1 + "&qenddate=" + v_str2 + "&gestion=" + vstr3 + "&poste=" + poste_comptable + "&compte="

	context = {"url_excel_rb": url_excel_rb, "url_report_pdf": url_report_pdf, "title": Title, "start_date": start_date,
	           "end_date": end_date, "listavis": x, "poste": poste_comptable_name, "date": str_date, "gestion": gestion,
	           "url_rb": url_rb, "compte": compte_v, "total_general": total_general}
	format_output = request.GET.get('format', "html")
	if format_output == "pdf":
		context.update({"pagesize": "A4"})
		template = "cddaccount/report_avis_debit_pdf.html"
		gettemplate = get_template(template)
		html = gettemplate.render(context)
		result = BytesIO()
		pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
		if pdf.err:
			return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
		return HttpResponse(result.getvalue(), content_type='application/pdf')
	else:
		return render(request, template, context)


@login_required
def repport_op_paye_view(request):
	template = "cddaccount/repport_op_paye.html"
	# gestion= AnneeComptable.active_gestion().id
	user = request.user

	gestion_v = request.GET.get('gestion', None)
	if gestion_v is None:
		gestionO = AnneeComptable.active_gestion()
		gestion_v = gestionO.id
	else:
		gestionO = AnneeComptable.objects.get(id=gestion_v)

	qenddate = request.GET.get('qenddate', None)
	if qenddate is None:
		enddate = datetime.datetime.now()
	else:
		format = "%Y-%m-%d"
		enddate = datetime.datetime.strptime(qenddate, format)
	qstartdate = request.GET.get('qstartdate', None)
	if qstartdate is None:
		startdate = datetime.datetime.now()
	else:
		format = "%Y-%m-%d"
		startdate = datetime.datetime.strptime(qstartdate, format)

	last_rg = (startdate, enddate + datetime.timedelta(days=1))

	moyenpaye_v = request.GET.get('payment_mean', None)

	s = "{:%Y-%m-%d}".format(startdate, )
	d = "{:%Y-%m-%d}".format(enddate, )

	url_report_pdf = "{}?format=pdf&qstartdate={}&qenddate={}&gestion={}".format(
		reverse_lazy('cddaccount:repport_op_paye_view'), s, d, gestionO.id)

	if moyenpaye_v:
		url_report_pdf = "{}&payment_mean={}".format(url_report_pdf, moyenpaye_v)
		objs = TransactionOP.objects.by_agent(user).filter(jour_comptable__annee_comptable__id=gestion_v,
		                                                   jour_comptable__jour__range=last_rg,
		                                                   poste_comptable=user.agent_postecomptable.poste.reference,
		                                                   payment_mean=moyenpaye_v)
	else:
		objs = TransactionOP.objects.by_agent(user).filter(jour_comptable__annee_comptable__id=gestion_v,
		                                                   jour_comptable__jour__range=last_rg,
		                                                   poste_comptable=user.agent_postecomptable.poste.reference)

	objs = objs.exclude(is_cancel_trx=True).filter(has_cancel=False)

	d = objs.values("reservation__ordre__compte_id").annotate(
		total=Sum('amount', output_field=IntegerField()),
		reference=ExpressionWrapper(F("reference"), output_field=CharField()),
		beneficiaire=ExpressionWrapper(F("reservation__ordre__beneficiaire"), output_field=CharField()),
		date_visa=ExpressionWrapper(F("reservation__ordre__date_visa"), output_field=DateField()),
		amount=ExpressionWrapper(F("amount"), output_field=IntegerField()),
		short_compte=ExpressionWrapper(F("reservation__ordre__compte__short_compte"), output_field=CharField()),
		libelle_court=ExpressionWrapper(F("reservation__ordre__compte__libelle"), output_field=CharField())

	)

	datas_r = sorted(list(d), key=lambda k: k['short_compte'], reverse=False)
	z = {"short_compte": 0}
	x = []
	total_general = 0
	ligne_general = 0

	for key, cpts in itertools.groupby(datas_r, operator.itemgetter('short_compte')):
		c = list(cpts)
		ligne_general += len(c)
		total = 0

		libelle_court = c[0]["libelle_court"]
		shortcompte = c[0]["short_compte"]
		for item in c:

			# recap=update(recap,item)
			for _key, value in item.items():
				if _key in ["amount"]:
					total += int(value)

		x.append({"moyenpaye_v": key, "shortcompte": shortcompte, "libelle_court": libelle_court, "items": c,
		          "total": total, })

		total_general += int(total)

	str_date = "{:%d/%m/%Y}".format(enddate)
	start_date = "{:%d/%m/%Y}".format(startdate)
	end_date = "{:%d/%m/%Y}".format(enddate)
	gestion = gestionO.year()
	url_rb = reverse_lazy('cddaccount:genere_repport_op_paye_view')
	Title = 'OPÉRATIONS PAR MOYEN DE PAIEMENT'
	context = {"url_report_pdf": url_report_pdf, "title": Title, "start_date": start_date, "end_date": end_date,
	           "listavis": x, "poste": user.agent_postecomptable.poste.name, "date": str_date, "gestion": gestion,
	           "url_rb": url_rb, "moyenpay": moyenpaye_v, "total_general": total_general}

	format_output = request.GET.get('format', "html")
	if format_output == "pdf":
		context.update({"pagesize": "A4"})
		template = "cddaccount/repport_op_paye_pdf.html"
		gettemplate = get_template(template)
		html = gettemplate.render(context)
		result = BytesIO()
		pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
		if pdf.err:
			return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
		return HttpResponse(result.getvalue(), content_type='application/pdf')
	else:
		return render(request, template, context)




@login_required
def genere_repport_opvise_view(request):
	template = "cddaccount/report_form.html"

	success_url = reverse_lazy('cddaccount:genere_repport_opvise_view')
	user = request.user
	show_delai = request.GET.get('delai', "0")

	amt_rg=None

	if request.method == 'POST':
		if hasattr(user, "agent_postecomptable"):
			form = OpViseForm(request.POST)
			if show_delai:form =OpViseWithAmountForm(request.POST)

			poste = user.agent_postecomptable.poste
			form.fields["comptes"].queryset = CompteDepot.objects.by_agent(user)
		else:
			form = OpViseTGForm(request.POST)
		if form.is_valid():
			if request and not is_ajax(request.META):
				gestion = form.cleaned_data['gestion']
				compte = form.cleaned_data['comptes']

				date_rg = form.cleaned_data['period']


				startdate, enddate = date_rg.lower, date_rg.upper

				str_date = "{:%Y-%m-%d}".format(startdate)
				end_date = "{:%Y-%m-%d}".format(enddate)

				# if moyenpay is None:success_url = "{}&qstartdate={}&qenddate={}

				if "postes" in form.cleaned_data:
					poste = form.cleaned_data['postes']

				success_url = "{}?gestion={}&poste={}&qstartdate={}&qenddate={}&delai={}".format(
					reverse_lazy('cddaccount:repport_op_vise_view'), gestion.id, poste.reference, str_date, end_date,show_delai)

				if compte:
					success_url = "{}?gestion={}&compte={}&poste={}&qstartdate={}&qenddate={}&delai={}".format(
						reverse_lazy('cddaccount:repport_op_vise_view'), gestion.id, compte.id, poste.reference,
						str_date, end_date,show_delai)

				if show_delai:
					amount_rg=form.cleaned_data['amount']
					if amount_rg:
						min_amount, max_amount = amount_rg.lower, amount_rg.upper+1
						amt_rg="&minamount={}&maxamount={}".format(min_amount,max_amount)
						success_url="{}{}".format(success_url,amt_rg)


			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:

		if hasattr(user, "agent_postecomptable"):
			form = OpViseForm()
			if show_delai: form = OpViseWithAmountForm()
			poste = user.agent_postecomptable.poste
			form.fields["comptes"].queryset = CompteDepot.objects.by_agent(user)
		else:
			form = OpViseTGForm()

	context = {"form": form, 'title': "Choisir la date", }
	return render(request, template, context)

from django.db.models.functions import ExtractDay
@login_required
def repport_op_vise_view(request):
	template = "cddaccount/repport_op_vise.html"
	# gestion= AnneeComptable.active_gestion().id
	user = request.user
	minamt=0
	maxamt = 0

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
	format_output=request.GET.get('format', "html")
	show_delai = request.GET.get('delai', "0")
	if show_delai=="1":
		minamt=int(request.GET.get('minamount', "0"))
		maxamt =int( request.GET.get('maxamount', "0"))
		template = "cddaccount/repport_op_vise_with_delai.html"
	amount_rg = (minamt, maxamt)

	gestion_v = request.GET.get('gestion', None)
	if gestion_v is None:
		gestionO = AnneeComptable.active_gestion()
		gestion_v = gestionO.id

	else:
		gestionO = AnneeComptable.objects.get(id=gestion_v)

	qdatevisa = request.GET.get('qstartdate', None)
	if qdatevisa is None:
		datevisa = datetime.date.today()
	else:
		format = "%Y-%m-%d"
		datevisa = datetime.datetime.strptime(qdatevisa, format)

	qdatevisa2 = request.GET.get('qenddate', None)
	if qdatevisa2 is None:
		datevisa2 = datetime.date.today()
	else:
		format = "%Y-%m-%d"
		datevisa2 = datetime.datetime.strptime(qdatevisa2, format)

	compte_v = request.GET.get('compte', None)

	vd = "{:%Y-%m-%d}".format(datevisa, )

	last_rg = (datevisa, datevisa2 + datetime.timedelta(days=1))

	s = "{:%Y-%m-%d}".format(datevisa, )
	end = "{:%Y-%m-%d}".format(datevisa2, )

	if compte_v:
		# url_report_pdf="{}&compte={}".format(url_report_pdf,compte_v)
		objs = TransactionOP.objects.by_agent(user).filter(jour_comptable__annee_comptable__id=gestion_v,
		                                                   jour_comptable__jour__range=last_rg,
		                                                   reservation__ordre__compte_id=compte_v)
	else:
		objs = TransactionOP.objects.by_agent(user).filter(jour_comptable__annee_comptable__id=gestion_v,
		                                                   jour_comptable__jour__range=last_rg,
		                                                   poste_comptable=poste_comptable)
	objs=objs.exclude(is_cancel_trx=True).filter(has_cancel=False)

	if show_delai and maxamt>0 and minamt<=maxamt:
		objs=objs.filter(amount__gte=minamt,amount__lte=maxamt)

	# d= objs.values("account_depot","reference","reservation__ordre__beneficiaire","libelle","amount")

	wi=ExtractDay(F('reservation__ordre__date_visa') - F('reservation__ordre__date_reception'))
	wd=ExtractDay(F('datevisa') - F('daterecep'))

	d = objs.values("reservation__ordre__sig_reference").annotate(
		amount=Sum('amount', output_field=IntegerField()),
		reservation__ordre__beneficiaire=ExpressionWrapper(F("reservation__ordre__beneficiaire"),
		                                                   output_field=CharField()),
		account_depot=ExpressionWrapper(F("reservation__ordre__compte__short_compte"), output_field=CharField()),
		reference=ExpressionWrapper(F("reservation__ordre__sig_reference"), output_field=CharField()),
		libelle=ExpressionWrapper(F("reservation__ordre__object"), output_field=CharField()),
		daterecep=ExpressionWrapper(F("reservation__ordre__date_reception"), output_field=DateField()),
		datepec=ExpressionWrapper(F("reservation__ordre__date_prise_en_charge"), output_field=DateField()),
		creation=ExpressionWrapper(F("created"), output_field=DateField()),


		datevisa=Case(When(reservation__ordre__date_visa__isnull=True, then=F("created")), default=F("reservation__ordre__date_visa")),

		duree=wd,
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
		x.append({"nature": key, "items": c, "total": my_dict, 'ligne': ligne})

	str_date = "{:%d/%m/%Y}".format(datevisa)
	visa_date = "{:%d/%m/%Y} - {:%d/%m/%Y}".format(datevisa, datevisa2)
	gestion = gestionO.year()
	url_rb = reverse_lazy('cddaccount:genere_repport_opvise_view')
	if show_delai == "1":
		url_rb=url_rb+"?delai=1"

	url_excel_rb = reverse_lazy('cddaccount:generate_opvise_in_excel')

	if compte_v:
		url_excel_rb = "{}?gestion={}&compte={}&poste={}&qstartdate={}&qenddate={}".format(url_excel_rb, gestion_v,
		                                                                                   compte_v, poste_comptable, s,
		                                                                                   end)

		url_report_pdf = "{}?gestion={}&compte={}&poste={}&qstartdate={}&qenddate={}&format=pdf&delai={}".format(
			reverse_lazy('cddaccount:repport_op_vise_view'), gestion_v, compte_v, poste_comptable, s, end,show_delai)
	else:
		url_excel_rb = "{}?gestion={}&poste={}&qstartdate={}&qenddate={}".format(url_excel_rb, gestion_v,
		                                                                         poste_comptable, s, end)
		url_report_pdf = "{}?gestion={}&poste={}&qstartdate={}&qenddate={}&format=pdf&delai={}".format(
			reverse_lazy('cddaccount:repport_op_vise_view'), gestion_v, poste_comptable, s, end,show_delai)

	context = {"show_delai":show_delai,"url_excel_rb": url_excel_rb, "url_report_pdf": url_report_pdf, "visa_date": visa_date, "balances": d,
	           "poste": poste_comptable_name, "Datas": x, "date": str_date, "gestion": gestion, "url_rb": url_rb}

	format_output = request.GET.get('format', "html")
	if format_output=="pdf":
		context.update({"pagesize":"A4"})
		template = "cddaccount/repport_op_vise_pdf.html"
		if show_delai == "1":
			template = "cddaccount/repport_op_vise_pdf_with_delai.html"
		gettemplate = get_template(template)
		html = gettemplate.render(context)
		result = BytesIO()
		pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
		if pdf.err:
			return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
		return HttpResponse(result.getvalue(), content_type='application/pdf')
	else :
		return render(request, template, context)



@login_required
def show_genere_rapport_cheques_partiellement_visees_view(request):
	template = "cddaccount/report_form.html"
	success_url = reverse_lazy('cddaccount:show_genere_rapport_cheques_partiellement_visees_view')
	user = request.user
	if request.method == 'POST':

		if hasattr(user, "agent_postecomptable"):
			form = ChequesPartielVisesForm(request.POST)
			poste = user.agent_postecomptable.poste
			form.fields["comptes"].queryset = CompteDepot.objects.by_agent(user)
		else:
			form = ChequesPartielVisesTGForm(request.POST)

		if form.is_valid():
			if request and not is_ajax(request.META):
				date_rg = form.cleaned_data['period']
				gestion = form.cleaned_data['gestion']
				compte = form.cleaned_data['comptes']
				startdate, enddate = date_rg.lower, date_rg.upper

				str_date = "{:%Y-%m-%d}".format(startdate)
				end_date = "{:%Y-%m-%d}".format(enddate)
				if "postes" in form.cleaned_data:
					poste = form.cleaned_data['postes']

				query_string = "?qstartdate={}&qenddate={}&gestion={}&poste={}".format(str_date, end_date, gestion.id,
				                                                                       poste.reference)

				if compte:
					query_string = "{}&compte={}".format(query_string, compte.id)

				success_url = "{}{}".format(reverse_lazy('cddaccount:rapport_cheques_partiellement_visees_view'),
				                            query_string)

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		if hasattr(user, "agent_postecomptable"):
			form = ChequesPartielVisesForm()
			poste = user.agent_postecomptable.poste
			form.fields["comptes"].queryset = CompteDepot.objects.by_agent(user)
		else:
			form = ChequesPartielVisesTGForm()

	context = {"form": form, 'title': "Choisir ", }
	return render(request, template, context)


@login_required
def rapport_cheques_partiellement_visees_view(request):
	template = "cddaccount/rapport_cheques_partiellement_visees.html"
	# gestion= AnneeComptable.active_gestion().id
	user = request.user
	user = request.user
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
	compte_v = request.GET.get('compte', None)
	if gestion_v is None:
		gestionO = AnneeComptable.active_gestion()
		gestion_v = gestionO.id
	else:
		gestionO = AnneeComptable.objects.get(id=gestion_v)

	qenddate = request.GET.get('qenddate', None)

	if qenddate is None:
		enddate = datetime.datetime.now()
	else:
		format = "%Y-%m-%d"
		enddate = datetime.datetime.strptime(qenddate, format)
	qstartdate = request.GET.get('qstartdate', None)
	if qstartdate is None:
		startdate = datetime.datetime.now()
	else:
		format = "%Y-%m-%d"
		startdate = datetime.datetime.strptime(qstartdate, format)

	last_rg = (startdate, enddate + datetime.timedelta(days=1))

	s = "{:%Y-%m-%d}".format(startdate, )
	d = "{:%Y-%m-%d}".format(enddate, )
	url_report_pdf = "{}?format=pdf&qstartdate={}&qenddate={}&gestion={}&poste={}".format(
		reverse_lazy('cddaccount:rapport_cheques_partiellement_visees_view'), s, d,
		gestionO.id, poste_comptable)

	# str_date="{:%d/%m/%Y}".format(enddate)
	# start_date = "{:%d/%m/%Y}".format(startdate)
	# end_date = "{:%d/%m/%Y}".format(enddate)
	# gestion=gestionO.year()
	# url_rb=reverse_lazy('cddaccount:genere_report_aviscredit_view')
	# title="SITUATION DES AVIS DE CREDIT"

	if qstartdate is None:
		qstartdate = datetime.date.today().strftime('%Y-%m-%d')
	datedebut = datetime.datetime.strptime(qstartdate, '%Y-%m-%d')
	if qenddate is None:
		qenddate = datetime.date.today().strftime('%Y-%m-%d')
	datefin = datetime.datetime.strptime(qenddate, '%Y-%m-%d')

	lecompte = None
	if compte_v:

		objs = ReservationFond.objects.by_agent(user).filter(close=False, amount__gt=F("reliquat"),
		                                                     created__range=last_rg, ordre__compte_id=compte_v)
		lecompte = CompteDepot.objects.get(id=int(compte_v)).short_compte
		url_report_pdf = "{}&compte={}".format(url_report_pdf, compte_v)
	else:
		objs = ReservationFond.objects.by_agent(user).filter(ordre__compte__poste__reference=poste_comptable,
		                                                     close=False, amount__gt=F("reliquat"),
		                                                     created__range=last_rg)

	d = objs.values("ordre__compte_id").annotate(
		total=Sum('amount', output_field=IntegerField()),
		montant=ExpressionWrapper(F("amount"), output_field=IntegerField()),
		reliquat=ExpressionWrapper(F("reliquat"), output_field=IntegerField()),
		dejapaye=ExpressionWrapper(F("montant") - F("reliquat"), output_field=IntegerField()),
		compte=ExpressionWrapper(F("ordre__compte__short_compte"), output_field=CharField()),
		moyen=ExpressionWrapper(F("payment_mean"), output_field=CharField()),
		typenature=ExpressionWrapper(F("ordre__type_nature"), output_field=CharField()),
		libelle_court=ExpressionWrapper(F("ordre__compte__libelle_court"), output_field=CharField()),
		beneficiaire=ExpressionWrapper(F("ordre__beneficiaire"), output_field=CharField()),
		nature=ExpressionWrapper(F("ordre__object"), output_field=CharField()),
		date_depot=ExpressionWrapper(F("created"), output_field=DateField()),
		sig_reference=ExpressionWrapper(F("ordre__sig_reference"), output_field=CharField()),
		date_pec=ExpressionWrapper(F("ordre__date_prise_en_charge"), output_field=DateField())
	)

	datas_r = sorted(list(d), key=lambda k: k['compte'], reverse=False)
	z = {"amount": 0}
	x = []
	total_general = 0
	ligne_general = 0
	recap = {"COMPENSE": {"fonct": 0, "invest": 0, 'total': 0}, "NUMERAIRE": {"fonct": 0, "invest": 0, 'total': 0},
	         "VIREMENT": {"fonct": 0, "invest": 0, 'total': 0}, "OPERATION": {"fonct": 0, "invest": 0, 'total': 0},
	         'total': 0}
	for key, cpts in itertools.groupby(datas_r, operator.itemgetter('compte')):
		c = list(cpts)
		ligne_general += len(c)
		total = 0
		libelle_court = c[0]["libelle_court"]
		for item in c:
			recap = update(recap, item)
			for _key, value in item.copy().items():
				if _key in ["montant"]:
					total += value

				if _key in ["sig_reference"]:
					t = Transaction.objects.filter(origin_reference=value)
					dt = t.values("reference", "account_depot", "amount", "created")
					item['transactions'] = dt

		x.append({"compte": key, "items": c, "total": total, 'libelle_court': libelle_court})

		total_general += total

	gestion = gestionO.year()

	start_date = "{:%d/%m/%Y}".format(datetime.date.today(), )
	url_rb = reverse_lazy('cddaccount:show_genere_rapport_cheques_partiellement_visees_view')
	title = "SITUATION DES CHÈQUES PARTIELLEMENT VISES"
	context = {"url_report_pdf": url_report_pdf, "recap": recap, "total": total_general, "lignes": ligne_general,
	           "title": title, "date": start_date, "situations": x, "poste": poste_comptable_name, "gestion": gestion,
	           "lecompte": lecompte, "url_rb": url_rb}
	format_output = request.GET.get('format', "html")
	if format_output == "pdf":
		context.update({"pagesize": "A4"})
		template = "cddaccount/rapport_cheques_partiellement_visees_pdf.html"
		gettemplate = get_template(template)
		html = gettemplate.render(context)
		result = BytesIO()
		pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
		if pdf.err:
			return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
		return HttpResponse(result.getvalue(), content_type='application/pdf')
	else:
		return render(request, template, context)


@login_required
def genere_report_aviscredit_view(request):
	template = "cddaccount/report_form.html"
	success_url = reverse_lazy('cddaccount:genere_report_aviscredit_view')
	user = request.user
	if request.method == 'POST':
		if hasattr(user, "agent_postecomptable"):
			form = AvisCreditFiltreForm(request.POST)
			poste = user.agent_postecomptable.poste
		# lisComptesUser = CompteDepot.objects.filter(poste=poste.id)
		# form.fields["comptes"].queryset = lisComptesUser

		else:
			form = AvisCreditFiltreTGForm(request.POST)
		# lisComptesUser = CompteDepot.objects.filter(poste=request.user.agent_postecomptable.poste.id)
		# form.fields["comptes"].queryset = lisComptesUser
		if form.is_valid():
			if request and not is_ajax(request.META):
				date_rg = form.cleaned_data['period']

				gestion = form.cleaned_data['gestion']
				comptes = form.cleaned_data['comptes']
				startdate, enddate = date_rg.lower, date_rg.upper

				str_date = "{:%Y-%m-%d}".format(startdate)
				end_date = "{:%Y-%m-%d}".format(enddate)
				if comptes is None:
					if "postes" in form.cleaned_data:
						poste = form.cleaned_data['postes']
					success_url = "{}?qstartdate={}&qenddate={}&gestion={}&poste={}".format(
						reverse_lazy('cddaccount:report_aviscredit_compte_view'), str_date, end_date, gestion.id,
						poste.reference)
				else:
					success_url = "{}?qstartdate={}&qenddate={}&gestion={}&compte={}&poste={}".format(
						reverse_lazy('cddaccount:report_aviscredit_compte_view'), str_date, end_date, gestion.id,
						comptes.short_compte, comptes.poste.reference)

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)

						messages.error(request, meg)
	else:
		if hasattr(user, "agent_postecomptable"):
			form = AvisCreditFiltreForm()
			lisComptesUser = CompteDepot.objects.filter(poste=request.user.agent_postecomptable.poste.id)
			form.fields["comptes"].queryset = lisComptesUser
		else:
			form = AvisCreditFiltreTGForm()
			lisComptesUser = CompteDepot.objects.none()
	# form.fields["comptes"].queryset = lisComptesUser
	context = {"form": form, 'title': "Indiquer les critères de recherche"}
	return render(request, template, context)


@login_required
def report_aviscredit_compte_view(request):
	template = "cddaccount/report_avis_credit.html"
	user = request.user
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
	format_output = request.GET.get('format', "html")

	gestion_v = request.GET.get('gestion', None)
	if gestion_v is None:
		gestionO = AnneeComptable.active_gestion()
		gestion_v = gestionO.id
	else:
		gestionO = AnneeComptable.objects.get(id=gestion_v)

	compte = request.GET.get('compte', None)

	qenddate = request.GET.get('qenddate', None)
	if qenddate is None:
		enddate = datetime.datetime.now()
	else:
		format = "%Y-%m-%d"
		enddate = datetime.datetime.strptime(qenddate, format)
	qstartdate = request.GET.get('qstartdate', None)
	if qstartdate is None:
		startdate = datetime.datetime.now()
	else:
		format = "%Y-%m-%d"
		startdate = datetime.datetime.strptime(qstartdate, format)

	last_rg = (startdate, enddate)

	str_date = "{:%d/%m/%Y}".format(enddate)
	start_date = "{:%d/%m/%Y}".format(startdate)
	end_date = "{:%d/%m/%Y}".format(enddate)
	gestion = gestionO.year()
	url_rb = reverse_lazy('cddaccount:genere_report_aviscredit_view')
	title = "SITUATION DES AVIS DE CREDIT"

	if qstartdate is None:
		qstartdate = datetime.date.today().strftime('%Y-%m-%d')
	datedebut = datetime.datetime.strptime(qstartdate, '%Y-%m-%d')
	if qenddate is None:
		qenddate = datetime.date.today().strftime('%Y-%m-%d')
	datefin = datetime.datetime.strptime(qenddate, '%Y-%m-%d')

	mylist = []
	listCompte = []
	totalDesAvis = 0
	if compte is None:
		listCompte = CompteDepot.objects.by_agent(user).filter(poste__reference=poste_comptable).values("short_compte",
		                                                                                                "libelle")
		for item in listCompte:
			list_avis_credit = AvisDeCredit.objects.by_agent(user).filter(
				jour_comptable__annee_comptable_id=gestionO.id, compte__short_compte=item["short_compte"],
				date_avis__year=gestion, date_avis__range=(datedebut, datefin))
			total = 0
			for x in list_avis_credit:
				total = total + x.amount
			totalDesAvis = totalDesAvis + total
			if len(list_avis_credit) > 0:
				dict = {'total': total, 'titre': item["short_compte"] + ' ' + item["libelle"],
				        'tableau': list_avis_credit}
				mylist.append(dict)
	else:
		compteSelect = CompteDepot.objects.get(short_compte=compte)
		list_avis_credit = AvisDeCredit.objects.by_agent(user).filter(jour_comptable__annee_comptable_id=gestionO.id,
		                                                              compte__short_compte=compte,
		                                                              date_avis__year=gestion,
		                                                              date_avis__range=(datedebut, datefin))
		total = 0
		for x in list_avis_credit:
			total = total + x.amount
		totalDesAvis = totalDesAvis + total
		mylist = [{'total': total, 'titre': compteSelect.short_compte + ' ' + compteSelect.libelle,
		           'tableau': list_avis_credit}]

	v_str1 = str(startdate.strftime("%Y-%m-%d"))
	v_str2 = str(enddate.strftime("%Y-%m-%d"))
	vstr3 = str(gestion_v)

	url_excel_rb = reverse_lazy('cddaccount:generate_report_aviscredit_in_excel')
	if compte is None:
		url_excel_rb = url_excel_rb + "?qstartdate=" + v_str1 + "&qenddate=" + v_str2 + "&gestion=" + vstr3 + "&poste=" + poste_comptable
		url_report_pdf = "pdf/?format=pdf&qstartdate=" + v_str1 + "&qenddate=" + v_str2 + "&gestion=" + vstr3 + "&poste=" + poste_comptable
	else:
		url_excel_rb = url_excel_rb + "?qstartdate=" + v_str1 + "&qenddate=" + v_str2 + "&gestion=" + vstr3 + "&poste=" + poste_comptable + "&compte=" + compte

		url_report_pdf = "pdf/?format=pdf&qstartdate=" + v_str1 + "&qenddate=" + v_str2 + "&gestion=" + vstr3 + "&poste=" + poste_comptable + "&compte=" + compte

	context = {"url_excel_rb": url_excel_rb, "url_report_pdf": url_report_pdf, "title": title, "start_date": start_date,
	           "end_date": end_date, "balances": mylist, "poste": poste_comptable_name, "date": str_date,
	           "gestion": gestion, "compte": compte, "url_rb": url_rb, "totalDesAvis": totalDesAvis}


	if format_output=="pdf":
		context.update({"pagesize":"A4"})
		template = "cddaccount/report_avis_credit_pdf.html"
		gettemplate = get_template(template)
		html = gettemplate.render(context)
		result = BytesIO()
		pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
		if pdf.err:
			return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
		return HttpResponse(result.getvalue(), content_type='application/pdf')
	else:return render(request, template, context)



@login_required
def situation_op_hs_view(request):
	template = "cddaccount/sit_instance_op_hs.html"
	# gestion= AnneeComptable.active_gestion().id

	user = request.user
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
	compte = request.GET.get('compte', None)
	if gestion_v is None:
		gestionO = AnneeComptable.active_gestion()
	else:
		gestionO = AnneeComptable.objects.get(id=gestion_v)

	url_report_pdf = "{}?gestion={}&poste={}".format(reverse_lazy('cddaccount:situation_op_hs_pdf_view'), gestionO.id,
	                                                 poste_comptable)
	lecompte = None
	if compte:
		objs = ReservationFond.objects.by_agent(user).filter(close=False, reliquat__gt=0, ordre__compte_id=compte,
		                                                     ordre__annulation_op=None,
		                                                     ordre__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE).exclude(
			ordre__nature__name="SALAIRES")
		lecompte = asc = CompteDepot.objects.get(id=int(compte)).short_compte
		url_report_pdf = "{}&compte={}".format(url_report_pdf, compte)
	else:
		objs = ReservationFond.objects.by_agent(user).filter(ordre__compte__poste__reference=poste_comptable,
		                                                     close=False, reliquat__gt=0, ordre__annulation_op=None,
		                                                     ordre__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE).exclude(
			ordre__nature__name="SALAIRES")

	d = objs.values("ordre__compte_id").annotate(
		total=Sum('amount', output_field=IntegerField()),
		reliquat=ExpressionWrapper(F("reliquat"), output_field=IntegerField()),
		montant=ExpressionWrapper(F("amount"), output_field=IntegerField()),
		compte=ExpressionWrapper(F("ordre__compte__short_compte"), output_field=CharField()),
		moyen=ExpressionWrapper(F("payment_mean"), output_field=CharField()),
		typenature=ExpressionWrapper(F("ordre__type_nature"), output_field=CharField()),
		libelle_court=ExpressionWrapper(F("ordre__compte__libelle_court"), output_field=CharField()),
		beneficiaire=ExpressionWrapper(F("ordre__beneficiaire"), output_field=CharField()),
		nature=ExpressionWrapper(F("ordre__object"), output_field=CharField()),
		date_depot=ExpressionWrapper(F("created"), output_field=DateField()),
		sig_reference=ExpressionWrapper(F("ordre__sig_reference"), output_field=CharField()),

		date_pec=ExpressionWrapper(F("ordre__date_prise_en_charge"), output_field=DateField())
	)

	datas_r = sorted(list(d), key=lambda k: k['compte'], reverse=False)
	z = {"amount": 0}
	x = []
	total_general = 0
	ligne_general = 0
	recap = {"COMPENSE": {"fonct": 0, "invest": 0, 'total': 0}, "NUMERAIRE": {"fonct": 0, "invest": 0, 'total': 0},
	         "VIREMENT": {"fonct": 0, "invest": 0, 'total': 0}, "OPERATION": {"fonct": 0, "invest": 0, 'total': 0},
	         'total': 0}
	for key, cpts in itertools.groupby(datas_r, operator.itemgetter('compte')):
		c = list(cpts)
		ligne_general += len(c)
		total = 0
		libelle_court = c[0]["libelle_court"]

		for item in c:

			recap = update(recap, item)
			for _key, value in item.items():
				if _key in ["reliquat"]:
					total += value

		x.append({"compte": key, "items": c, "total": total, 'libelle_court': libelle_court})

		total_general += total

	gestion = gestionO.year()
	start_date = "{:%d/%m/%Y}".format(datetime.date.today(), )
	url_rb = reverse_lazy('cddaccount:show_sit_instance_op_hs_form_view')
	title = "Situation des Instances Hors Salaires"
	context = {"url_report_pdf": url_report_pdf, "recap": recap, "total": total_general, "lignes": ligne_general,
	           "title": title, "date": start_date, "situations": x, "poste": poste_comptable_name, "gestion": gestion,
	           "lecompte": lecompte, "url_rb": url_rb}
	return render(request, template, context)


@login_required
def situation_op_s_view(request):
	template = "cddaccount/sit_instance_op_s.html"
	# gestion= AnneeComptable.active_gestion().id
	user = request.user
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
	compte = request.GET.get('compte', None)
	if gestion_v is None:
		gestionO = AnneeComptable.active_gestion()
	else:
		gestionO = AnneeComptable.objects.get(id=gestion_v)
	url_report_pdf = "{}?gestion={}&poste".format(reverse_lazy('cddaccount:situation_op_s_pdf_view'), gestionO.id,
	                                              poste_comptable)
	lecompte = None
	if compte:
		objs = ReservationFond.objects.by_agent(user).filter(close=False, reliquat__gt=0,
		                                                     ordre__nature__name="SALAIRES", ordre__compte_id=compte,
		                                                     ordre__annulation_op=None,
		                                                     ordre__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE)
		lecompte = CompteDepot.objects.get(id=int(compte)).short_compte
		url_report_pdf = "{}&compte={}".format(url_report_pdf, compte)

	else:
		objs = ReservationFond.objects.by_agent(user).filter(ordre__compte__poste__reference=poste_comptable,
		                                                     close=False, reliquat__gt=0,
		                                                     ordre__nature__name="SALAIRES", ordre__annulation_op=None,
		                                                     ordre__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE)

	d = objs.values("ordre__compte_id").annotate(
		total=Sum('amount', output_field=IntegerField()),
		reliquat=ExpressionWrapper(F("reliquat"), output_field=IntegerField()),
		montant=ExpressionWrapper(F("amount"), output_field=IntegerField()),
		compte=ExpressionWrapper(F("ordre__compte__short_compte"), output_field=CharField()),
		moyen=ExpressionWrapper(F("payment_mean"), output_field=CharField()),
		typenature=ExpressionWrapper(F("ordre__type_nature"), output_field=CharField()),
		libelle_court=ExpressionWrapper(F("ordre__compte__libelle_court"), output_field=CharField()),
		beneficiaire=ExpressionWrapper(F("ordre__beneficiaire"), output_field=CharField()),
		nature=ExpressionWrapper(F("ordre__object"), output_field=CharField()),
		date_depot=ExpressionWrapper(F("created"), output_field=DateField()),
		sig_reference=ExpressionWrapper(F("ordre__sig_reference"), output_field=CharField()),

		date_pec=ExpressionWrapper(F("ordre__date_prise_en_charge"), output_field=DateField())
	)

	datas_r = sorted(list(d), key=lambda k: k['compte'], reverse=False)
	z = {"amount": 0}
	x = []
	total_general = 0
	ligne_general = 0
	recap = {"COMPENSE": {"fonct": 0, "invest": 0, 'total': 0}, "NUMERAIRE": {"fonct": 0, "invest": 0, 'total': 0},
	         "VIREMENT": {"fonct": 0, "invest": 0, 'total': 0}, "OPERATION": {"fonct": 0, "invest": 0, 'total': 0},
	         'total': 0}
	for key, cpts in itertools.groupby(datas_r, operator.itemgetter('compte')):
		c = list(cpts)
		ligne_general += len(c)
		total = 0
		libelle_court = c[0]["libelle_court"]
		for item in c:

			recap = update(recap, item)
			for _key, value in item.items():
				if _key in ["reliquat"]:
					total += value

		x.append({"compte": key, "items": c, "total": total, 'libelle_court': libelle_court})

		total_general += total

	gestion = gestionO.year()
	start_date = "{:%d/%m/%Y}".format(datetime.date.today(), )
	url_rb = reverse_lazy('cddaccount:show_sit_instance_op_s_form_view')
	title = "Situation des Instances Salaires"
	context = {"url_report_pdf": url_report_pdf, "recap": recap, "total": total_general, "lignes": ligne_general,
	           "title": title, "date": start_date, "situations": x, "poste": poste_comptable_name, "gestion": gestion,
	           "lecompte": lecompte, "url_rb": url_rb}
	return render(request, template, context)


@login_required
def situation_op_all_view(request):
	template = "cddaccount/sit_instance_op_all.html"
	# gestion= AnneeComptable.active_gestion().id
	user = request.user
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
	compte_v = request.GET.get('compte', None)
	qstartdate = request.GET.get('qstartdate', None)
	if qstartdate is None:
		startdate = datetime.datetime.now()
	else:
		format = "%Y-%m-%d"
		startdate = datetime.datetime.strptime(qstartdate, format)
	if gestion_v is None:
		gestionO = AnneeComptable.active_gestion()
	else:
		gestionO = AnneeComptable.objects.get(id=gestion_v)
	lecompte = None
	if compte_v:
		objs = ReservationFond.objects.by_agent(user).filter(ordre__gestion_id=gestionO.id, close=False, reliquat__gt=0,
		                                                     ordre__compte_id=compte_v, ordre__annulation_op=None,
		                                                     ordre__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE)
		lecompte = CompteDepot.objects.get(id=int(compte_v)).short_compte
	else:
		objs = ReservationFond.objects.by_agent(user).filter(ordre__compte__poste__reference=poste_comptable,
		                                                     ordre__gestion_id=gestionO.id, close=False, reliquat__gt=0,
		                                                     ordre__annulation_op=None,
		                                                     ordre__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE)

	d = objs.values("ordre__compte_id").annotate(
		total=Sum('amount', output_field=IntegerField()),
		reliquat=ExpressionWrapper(F("reliquat"), output_field=IntegerField()),
		montant=ExpressionWrapper(F("amount"), output_field=IntegerField()),
		compte=ExpressionWrapper(F("ordre__compte__short_compte"), output_field=CharField()),
		moyen=ExpressionWrapper(F("payment_mean"), output_field=CharField()),
		typenature=ExpressionWrapper(F("ordre__type_nature"), output_field=CharField()),
		libelle_court=ExpressionWrapper(F("ordre__compte__libelle_court"), output_field=CharField()),
		beneficiaire=ExpressionWrapper(F("ordre__beneficiaire"), output_field=CharField()),
		nature=ExpressionWrapper(F("ordre__object"), output_field=CharField()),
		date_depot=ExpressionWrapper(F("created"), output_field=DateField()),
		sig_reference=ExpressionWrapper(F("ordre__sig_reference"), output_field=CharField()),

		date_pec=ExpressionWrapper(F("ordre__date_prise_en_charge"), output_field=DateField())
	)

	datas_r = sorted(list(d), key=lambda k: k['compte'], reverse=False)
	z = {"amount": 0}
	x = []
	total_general = 0
	ligne_general = 0
	recap = {"COMPENSE": {"fonct": 0, "invest": 0, 'total': 0}, "NUMERAIRE": {"fonct": 0, "invest": 0, 'total': 0},
	         "VIREMENT": {"fonct": 0, "invest": 0, 'total': 0}, "OPERATION": {"fonct": 0, "invest": 0, 'total': 0},
	         'total': 0}
	for key, cpts in itertools.groupby(datas_r, operator.itemgetter('compte')):
		c = list(cpts)
		ligne_general += len(c)
		total = 0
		libelle_court = c[0]["libelle_court"]
		for item in c:
			recap = update(recap, item)

			for _key, value in item.items():

				if _key in ["reliquat"]:  # prendre le reliquat si paiement partiel
					total += value

		x.append({"compte": key, "items": c, "total": total, 'libelle_court': libelle_court})

		total_general += total

	gestion = gestionO.year()
	# start_date = "{:%d/%m/%Y}".format(datetime.date.today(), )
	start_date = "{:%d/%m/%Y}".format(startdate)
	vstr1 = str(startdate.strftime("%Y-%m-%d"));
	vstr3 = str(gestion_v)
	url_rb = reverse_lazy('cddaccount:show_situation_cdd_form_view')
	title = "SITUATION DES INSTANCES DÉTAILLEES PAR CDD"
	if compte_v:
		url_report_pdf = "pdf/?format=pdf&qstartdate=" + vstr1 + "&gestion=" + vstr3 + "&compte=" + compte_v
	else:
		url_report_pdf = "pdf/?format=pdf&qstartdate=" + vstr1 + "&gestion=" + vstr3 + "&poste=" + poste_comptable + "&compte="

	context = {"url_report_pdf": url_report_pdf, "recap": recap, "total": total_general, "lignes": ligne_general,
	           "title": title, "date": start_date, "situations": x, "poste": poste_comptable_name, "gestion": gestion,
	           "lecompte": lecompte, "url_rb": url_rb}
	format_output = request.GET.get('format', "html")
	if format_output == "pdf":
		context.update({"pagesize": "A4"})
		template = "cddaccount/sit_instance_op_all_pdf.html"
		gettemplate = get_template(template)
		html = gettemplate.render(context)
		result = BytesIO()
		pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
		if pdf.err:
			return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
		return HttpResponse(result.getvalue(), content_type='application/pdf')
	else:
		return render(request, template, context)


@login_required
def situation_op_hs_view(request):
	template = "cddaccount/sit_instance_op_hs.html"
	# gestion= AnneeComptable.active_gestion().id

	user = request.user
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
	compte = request.GET.get('compte', None)
	if gestion_v is None:
		gestionO = AnneeComptable.active_gestion()
	else:
		gestionO = AnneeComptable.objects.get(id=gestion_v)

	url_report_pdf = "{}?format=pdf&gestion={}&poste={}".format(reverse_lazy('cddaccount:situation_op_hs_view'), gestionO.id,
	                                                 poste_comptable)
	lecompte = None
	if compte:
		objs = ReservationFond.objects.by_agent(user).filter(close=False, reliquat__gt=0, ordre__compte_id=compte,
		                                                     ordre__annulation_op=None,
		                                                     ordre__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE).exclude(
			ordre__nature__name="SALAIRES")
		lecompte = asc = CompteDepot.objects.get(id=int(compte)).short_compte
		url_report_pdf = "{}&compte={}".format(url_report_pdf, compte)
	else:
		objs = ReservationFond.objects.by_agent(user).filter(ordre__compte__poste__reference=poste_comptable,
		                                                     close=False, reliquat__gt=0, ordre__annulation_op=None,
		                                                     ordre__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE).exclude(
			ordre__nature__name="SALAIRES")

	d = objs.values("ordre__compte_id").annotate(
		total=Sum('amount', output_field=IntegerField()),
		reliquat=ExpressionWrapper(F("reliquat"), output_field=IntegerField()),
		montant=ExpressionWrapper(F("amount"), output_field=IntegerField()),
		compte=ExpressionWrapper(F("ordre__compte__short_compte"), output_field=CharField()),
		moyen=ExpressionWrapper(F("payment_mean"), output_field=CharField()),
		typenature=ExpressionWrapper(F("ordre__type_nature"), output_field=CharField()),
		libelle_court=ExpressionWrapper(F("ordre__compte__libelle_court"), output_field=CharField()),
		beneficiaire=ExpressionWrapper(F("ordre__beneficiaire"), output_field=CharField()),
		nature=ExpressionWrapper(F("ordre__object"), output_field=CharField()),
		date_depot=ExpressionWrapper(F("created"), output_field=DateField()),
		sig_reference=ExpressionWrapper(F("ordre__sig_reference"), output_field=CharField()),

		date_pec=ExpressionWrapper(F("ordre__date_prise_en_charge"), output_field=DateField())
	)

	datas_r = sorted(list(d), key=lambda k: k['compte'], reverse=False)
	z = {"amount": 0}
	x = []
	total_general = 0
	ligne_general = 0
	recap = {"COMPENSE": {"fonct": 0, "invest": 0, 'total': 0}, "NUMERAIRE": {"fonct": 0, "invest": 0, 'total': 0},
	         "VIREMENT": {"fonct": 0, "invest": 0, 'total': 0}, "OPERATION": {"fonct": 0, "invest": 0, 'total': 0},
	         'total': 0}
	for key, cpts in itertools.groupby(datas_r, operator.itemgetter('compte')):
		c = list(cpts)
		ligne_general += len(c)
		total = 0
		libelle_court = c[0]["libelle_court"]

		for item in c:

			recap = update(recap, item)
			for _key, value in item.items():
				if _key in ["reliquat"]:
					total += value

		x.append({"compte": key, "items": c, "total": total, 'libelle_court': libelle_court})

		total_general += total

	gestion = gestionO.year()
	start_date = "{:%d/%m/%Y}".format(datetime.date.today(), )
	url_rb = reverse_lazy('cddaccount:show_sit_instance_op_hs_form_view')
	title = "Situation des Instances Hors Salaires"
	context = {"url_report_pdf": url_report_pdf, "recap": recap, "total": total_general, "lignes": ligne_general,
	           "title": title, "date": start_date, "situations": x, "poste": poste_comptable_name, "gestion": gestion,
	           "lecompte": lecompte, "url_rb": url_rb}

	format_output = request.GET.get('format', "html")
	if format_output == "pdf":
		context.update({"pagesize": "A4"})
		template = "cddaccount/sit_instance_op_hs_pdf.html"
		gettemplate = get_template(template)
		html = gettemplate.render(context)
		result = BytesIO()
		pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
		if pdf.err:
			return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
		return HttpResponse(result.getvalue(), content_type='application/pdf')
	else:
		return render(request, template, context)


@login_required
def situation_op_s_view(request):
	template = "cddaccount/sit_instance_op_s.html"
	# gestion= AnneeComptable.active_gestion().id
	user = request.user
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
	compte = request.GET.get('compte', None)
	if gestion_v is None:
		gestionO = AnneeComptable.active_gestion()
	else:
		gestionO = AnneeComptable.objects.get(id=gestion_v)
	url_report_pdf = "{}?format=pdf&gestion={}&poste".format(reverse_lazy('cddaccount:situation_op_s_view'), gestionO.id,
	                                              poste_comptable)
	lecompte = None
	if compte:
		objs = ReservationFond.objects.by_agent(user).filter(close=False, reliquat__gt=0,
		                                                     ordre__nature__name="SALAIRES", ordre__compte_id=compte,
		                                                     ordre__annulation_op=None,
		                                                     ordre__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE)
		lecompte = CompteDepot.objects.get(id=int(compte)).short_compte
		url_report_pdf = "{}&compte={}".format(url_report_pdf, compte)

	else:
		objs = ReservationFond.objects.by_agent(user).filter(ordre__compte__poste__reference=poste_comptable,
		                                                     close=False, reliquat__gt=0,
		                                                     ordre__nature__name="SALAIRES", ordre__annulation_op=None,
		                                                     ordre__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE)

	d = objs.values("ordre__compte_id").annotate(
		total=Sum('amount', output_field=IntegerField()),
		reliquat=ExpressionWrapper(F("reliquat"), output_field=IntegerField()),
		montant=ExpressionWrapper(F("amount"), output_field=IntegerField()),
		compte=ExpressionWrapper(F("ordre__compte__short_compte"), output_field=CharField()),
		moyen=ExpressionWrapper(F("payment_mean"), output_field=CharField()),
		typenature=ExpressionWrapper(F("ordre__type_nature"), output_field=CharField()),
		libelle_court=ExpressionWrapper(F("ordre__compte__libelle_court"), output_field=CharField()),
		beneficiaire=ExpressionWrapper(F("ordre__beneficiaire"), output_field=CharField()),
		nature=ExpressionWrapper(F("ordre__object"), output_field=CharField()),
		date_depot=ExpressionWrapper(F("created"), output_field=DateField()),
		sig_reference=ExpressionWrapper(F("ordre__sig_reference"), output_field=CharField()),

		date_pec=ExpressionWrapper(F("ordre__date_prise_en_charge"), output_field=DateField())
	)

	datas_r = sorted(list(d), key=lambda k: k['compte'], reverse=False)
	z = {"amount": 0}
	x = []
	total_general = 0
	ligne_general = 0
	recap = {"COMPENSE": {"fonct": 0, "invest": 0, 'total': 0}, "NUMERAIRE": {"fonct": 0, "invest": 0, 'total': 0},
	         "VIREMENT": {"fonct": 0, "invest": 0, 'total': 0}, "OPERATION": {"fonct": 0, "invest": 0, 'total': 0},
	         'total': 0}
	for key, cpts in itertools.groupby(datas_r, operator.itemgetter('compte')):
		c = list(cpts)
		ligne_general += len(c)
		total = 0
		libelle_court = c[0]["libelle_court"]
		for item in c:

			recap = update(recap, item)
			for _key, value in item.items():
				if _key in ["reliquat"]:
					total += value

		x.append({"compte": key, "items": c, "total": total, 'libelle_court': libelle_court})

		total_general += total

	gestion = gestionO.year()
	start_date = "{:%d/%m/%Y}".format(datetime.date.today(), )
	url_rb = reverse_lazy('cddaccount:show_sit_instance_op_s_form_view')
	title = "Situation des Instances Salaires"
	context = {"url_report_pdf": url_report_pdf, "recap": recap, "total": total_general, "lignes": ligne_general,
	           "title": title, "date": start_date, "situations": x, "poste": poste_comptable_name, "gestion": gestion,
	           "lecompte": lecompte, "url_rb": url_rb}

	format_output = request.GET.get('format', "html")
	if format_output == "pdf":
		context.update({"pagesize": "A4"})
		template = "cddaccount/sit_instance_op_s_pdf.html"
		gettemplate = get_template(template)
		html = gettemplate.render(context)
		result = BytesIO()
		pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
		if pdf.err:
			return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
		return HttpResponse(result.getvalue(), content_type='application/pdf')
	else:
		return render(request, template, context)


@login_required
def situation_op_all_by_format(request,type="simple"):
	template = "cddaccount/sit_instance_op_all.html"
	# gestion= AnneeComptable.active_gestion().id
	user = request.user
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
	compte_v = request.GET.get('compte', None)
	qstartdate = request.GET.get('qstartdate', None)
	if qstartdate is None:
		startdate = datetime.datetime.now()
	else:
		format = "%Y-%m-%d"
		startdate = datetime.datetime.strptime(qstartdate, format)
	if gestion_v is None:
		gestionO = AnneeComptable.active_gestion()
	else:
		gestionO = AnneeComptable.objects.get(id=gestion_v)
	lecompte = None
	#etapes = [ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE,ETAPE_ORDRE_PAYMENT.VALIDE, ETAPE_ORDRE_PAYMENT.ACCEPTE ]
	etapes = [ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE]
	ex_etapes=[ETAPE_ORDRE_PAYMENT.VALIDE, ETAPE_ORDRE_PAYMENT.ACCEPTE ]
	if compte_v:
		objs = ReservationFond.objects.by_agent(user).filter(ordre__gestion_id=gestionO.id, close=False, reliquat__gt=0,
		                                                     ordre__compte_id=compte_v, ordre__annulation_op=None,
		                                                     ordre__etape__in=etapes,payment_mean__isnull=False)
		lecompte = CompteDepot.objects.get(id=int(compte_v)).short_compte
	else:
		objs = ReservationFond.objects.by_agent(user).filter(ordre__compte__poste__reference=poste_comptable,
		                                                     ordre__gestion_id=gestionO.id, close=False, reliquat__gt=0,
		                                                     ordre__annulation_op=None,
		                                                     ordre__etape__in=etapes,payment_mean__isnull=False).prefetch_related("ordre__compte")

	d = objs.values("ordre__compte_id").annotate(
		total=Sum('amount', output_field=IntegerField()),
		reliquat=ExpressionWrapper(F("reliquat"), output_field=IntegerField()),
		montant=ExpressionWrapper(F("amount"), output_field=IntegerField()),
		compte=ExpressionWrapper(F("ordre__compte__short_compte"), output_field=CharField()),
		moyen=ExpressionWrapper(F("payment_mean"), output_field=CharField()),
		typenature=ExpressionWrapper(F("ordre__type_nature"), output_field=CharField()),
		libelle_court=ExpressionWrapper(F("ordre__compte__libelle_court"), output_field=CharField()),
		beneficiaire=ExpressionWrapper(F("ordre__beneficiaire"), output_field=CharField()),
		nature=ExpressionWrapper(F("ordre__object"), output_field=CharField()),
		date_depot=ExpressionWrapper(F("created"), output_field=DateField()),
		sig_reference=ExpressionWrapper(F("ordre__sig_reference"), output_field=CharField()),

		date_pec=ExpressionWrapper(F("ordre__date_prise_en_charge"), output_field=DateField())


	)

	cc = objs.values("ordre__type_nature","payment_mean").annotate(
		total=Sum('amount', output_field=IntegerField()),
		reliquat=Sum('reliquat', output_field=IntegerField()),
		moyen=ExpressionWrapper(F("payment_mean"), output_field=CharField()),
		typenature=ExpressionWrapper(F("ordre__type_nature"), output_field=CharField()),

	)
	datas_cc = sorted(list(cc), key=lambda k: k['moyen'], reverse=False)

	group_by_pamen = []
	for key, cpts in itertools.groupby(datas_cc, operator.itemgetter('moyen')):
		c = list(cpts)
		total=0
		reliquat=0
		invest=0
		fonct=0
		t=key
		for item in c:
			total+= item["reliquat"]
			reliquat += item["reliquat"]
			if item["typenature"]==NATURE_COMPTE.FONCTIONNEMENT:
				fonct+=item["reliquat"]
			if item["typenature"] == NATURE_COMPTE.INVESTISSEMENT:
				invest +=item["reliquat"]

		if key==PAYMENT_MEAN_TYPE.CHEQUE: t="COMPENSE"
		elif key==PAYMENT_MEAN_TYPE.RETRAIT: t="ORDRE DE PAIEMENT"
		group_by_pamen.append({"fonct": fonct, "invest": invest,"reliquat":reliquat, 'total': total,"moyen":t})



	datas_r = sorted(list(d), key=lambda k: k['compte'], reverse=False)
	z = {"amount": 0}
	x = []
	total_general = 0
	ligne_general = 0
	recap = {"COMPENSE": {"fonct": 0, "invest": 0, 'total': 0}, "NUMERAIRE": {"fonct": 0, "invest": 0, 'total': 0},
	         "VIREMENT": {"fonct": 0, "invest": 0, 'total': 0}, "OPERATION": {"fonct": 0, "invest": 0, 'total': 0},
	         'total': 0}
	for key, cpts in itertools.groupby(datas_r, operator.itemgetter('compte')):
		c = list(cpts)
		ligne_general += len(c)
		total = 0
		libelle_court = c[0]["libelle_court"]
		for item in c:
			recap = update(recap, item)

			for _key, value in item.items():

				if _key in ["reliquat"]:  # prendre le reliquat si paiement partiel
					total += value

		x.append({"compte": key, "items": c, "total": total, 'libelle_court': libelle_court})

		total_general += total

	gestion = gestionO.year()
	# start_date = "{:%d/%m/%Y}".format(datetime.date.today(), )
	start_date = "{:%d/%m/%Y}".format(startdate)
	vstr1 = str(startdate.strftime("%Y-%m-%d"));
	vstr3 = str(gestionO.id)
	url_rb = reverse_lazy('cddaccount:show_situation_cdd_form_view')
	title = "SITUATION DES INSTANCES DÉTAILLEES PAR CDD"
	if compte_v:
		url_report_pdf = "?format=pdf&qstartdate=" + vstr1 + "&gestion=" + vstr3 + "&compte=" + compte_v
	else:
		url_report_pdf = "?format=pdf&qstartdate=" + vstr1 + "&gestion=" + vstr3 + "&poste=" + poste_comptable + "&compte="

	context = {"url_report_pdf": url_report_pdf, "recap": recap, "total": total_general, "lignes": ligne_general,
	           "title": title, "date": start_date, "situations": x, "poste": poste_comptable_name, "gestion": gestion,
	           "lecompte": lecompte, "url_rb": url_rb,"recap1":group_by_pamen}

	return  context
	#return render(request, template, context)



@login_required
def situation_op_all_view(request):
	context= situation_op_all_by_format(request)
	template = "cddaccount/sit_instance_op_all.html"
	format_output = request.GET.get('format', "html")
	if format_output == "pdf":
		context.update({"pagesize": "A4"})
		template = "cddaccount/sit_instance_op_all_pdf.html"
		gettemplate = get_template(template)
		html = gettemplate.render(context)
		result = BytesIO()
		pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
		if pdf.err:
			return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
		return HttpResponse(result.getvalue(), content_type='application/pdf')
	else:
		return render(request, template, context)



from cddaccount.tasks import generate_pdf_task
from django.http import JsonResponse


from celery.result import AsyncResult

def check_task_status(request, task_id):
    task = AsyncResult(task_id)
    if task.state == 'SUCCESS':
        return JsonResponse({'state': task.state, 'result': task.result.url})
    else:
        return JsonResponse({'state': task.state})



@login_required
def situation_consolde_view(request):
	template = "cddaccount/sit_consolide.html"
	# gestion= AnneeComptable.active_gestion().id
	user = request.user
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
	else:
		gestionO = AnneeComptable.objects.get(id=gestion_v)

	d = PrisEnchageOrdrePayment.objects.by_agent(user).filter(ordre__compte__poste__reference=poste_comptable).values(
		"ordre__compte_id").annotate(
		total=Sum('amount', output_field=IntegerField()),
		montant=ExpressionWrapper(F("amount"), output_field=IntegerField()),
		compte=ExpressionWrapper(F("ordre__compte__short_compte"), output_field=CharField()),
		moyen=ExpressionWrapper(F("payment_mean"), output_field=CharField()),
		typenature=ExpressionWrapper(F("ordre__type_nature"), output_field=CharField()),
		libelle_court=ExpressionWrapper(F("ordre__compte__libelle_court"), output_field=CharField()),
		beneficiaire=ExpressionWrapper(F("ordre__beneficiaire"), output_field=CharField()),
		nature=ExpressionWrapper(F("ordre__nature__name"), output_field=CharField()),
		date_depot=ExpressionWrapper(F("ordre__created"), output_field=DateField()),
		sig_reference=ExpressionWrapper(F("ordre__sig_reference"), output_field=CharField()),

		date_pec=ExpressionWrapper(F("created"), output_field=DateField())
	)

	datas_r = sorted(list(d), key=lambda k: k['compte'], reverse=False)
	z = {"amount": 0}
	x = []
	total_general = 0
	ligne_general = 0
	recap = {"COMPENSE": {"fonct": 0, "invest": 0, 'total': 0}, "NUMERAIRE": {"fonct": 0, "invest": 0, 'total': 0},
	         "VIREMENT": {"fonct": 0, "invest": 0, 'total': 0}, "OPERATION": {"fonct": 0, "invest": 0, 'total': 0},
	         'total': 0}
	for key, cpts in itertools.groupby(datas_r, operator.itemgetter('compte')):
		c = list(cpts)
		ligne_general += len(c)
		total = 0
		libelle_court = c[0]["libelle_court"]
		for item in c:

			recap = update(recap, item)
			for _key, value in item.items():
				if _key in ["montant"]:
					total += value

		x.append({"compte": key, "items": c, "total": total, 'libelle_court': libelle_court})

		total_general += total

	gestion = gestionO.year()
	start_date = "{:%d/%m/%Y}".format(datetime.date.today(), )
	url_rb = reverse_lazy('cddaccount:show_disponible_form_view')
	title = "SITUATION D’EXECUTION CONSOLIDEE"
	context = {"recap": recap, "total": total_general, "lignes": ligne_general, "title": title, "date": start_date,
	           "situations": x, "poste": poste_comptable_name, "gestion": gestion, "url_rb": url_rb}
	return render(request, template, context)
from django.db import connection


def get_report_rows_sql(poste, gestion, compte=None):
	sql_str = """SELECT id_annee, sum(amount_invest) as amount_invest, sum(amount_fonc) as amount_fonc,
short_compte, libelle FROM (
SELECT ca.id as id_annee, rsv.amount_invest,rsv.amount_fonc,
			td.short_compte, td.libelle
			FROM public.cddaccount_comptedepot td,
			public.cddaccount_anneecomptable ca,
			public.cddaccount_report rsv
			where rsv.compte_id = td.id
			and rsv.gestion_courant_id = ca.id
			and ca.id = %s
			and td.poste_id=%s
			UNION 
			SELECT ca.id as id_annee, 0 as amount_invest, 0 as amount_fonc,
					td.short_compte, td.libelle
					FROM public.cddaccount_comptedepot td,
					public.cddaccount_anneecomptable ca
					WHERE ca.id = %s
					and td.poste_id=%s) as tb
			GROUP BY id_annee, short_compte, libelle;"""
	if compte:
		sql_str = """SELECT id_annee, sum(amount_invest) as amount_invest, sum(amount_fonc) as amount_fonc,
short_compte, libelle FROM (
SELECT ca.id as id_annee, rsv.amount_invest,rsv.amount_fonc,
					td.short_compte, td.libelle
					FROM public.cddaccount_comptedepot td,
					public.cddaccount_anneecomptable ca,
					public.cddaccount_report rsv
					where rsv.compte_id = td.id
					and rsv.gestion_courant_id = ca.id
					and td.short_compte = %s
					and ca.id = %s
					and td.poste_id=%s
					UNION 
			SELECT ca.id as id_annee, 0 as amount_invest, 0 as amount_fonc,
					td.short_compte, td.libelle
					FROM public.cddaccount_comptedepot td,
					public.cddaccount_anneecomptable ca
					WHERE td.short_compte = %s
					and ca.id = %s
					and td.poste_id=%s) as tb
			GROUP BY id_annee, short_compte, libelle;"""

	with connection.cursor() as cursor:
		if compte:
			cursor.execute(sql_str, [compte, gestion, poste, compte, gestion, poste])
		else:
			cursor.execute(sql_str, [gestion, poste, gestion, poste])
		# rows = cursor.fetchall()
		columns = [col[0] for col in cursor.description]
		rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

	return rows


def get_instances_rows_sql(poste, gestion, compte=None):
	sql_str = """SELECT id_annee, sum(reliquat), short_compte, libelle, type_nature
FROM (
SELECT ca.id as id_annee, sum(rsv.reliquat) as reliquat,
			td.short_compte, td.libelle, op.type_nature 
			FROM public.cddaccount_comptedepot td,
			public.cddaccount_anneecomptable ca,
			public.cddaccount_reservationfond rsv,
			public.cddaccount_ordrepayment op
			where op.compte_id = td.id
			and op.gestion_id = ca.id
			and ca.id = %s
			and td.poste_id=%s
			and rsv.ordre_id=op.id
			and op.etape='PRISE_EN_CHARGE'
			and rsv.close=false			
			group by  ca.id,  td.short_compte, td.libelle, op.type_nature
	UNION
SELECT ca.id as id_annee, 0 as reliquat,
			td.short_compte, td.libelle, 'FONCTIONNEMENT' as type_nature 
			FROM public.cddaccount_comptedepot td,
			public.cddaccount_anneecomptable ca
			WHERE ca.id = %s
			and td.poste_id=%s
	) as tb
group by  id_annee,  short_compte, libelle, type_nature
order by  id_annee,  short_compte, libelle, type_nature;"""
	if compte:
		sql_str = """SELECT id_annee, sum(reliquat), short_compte, libelle, type_nature
FROM (
SELECT ca.id as id_annee, sum(rsv.reliquat) as reliquat,
			td.short_compte, td.libelle, op.type_nature 
					FROM public.cddaccount_comptedepot td,
					public.cddaccount_anneecomptable ca,
					public.cddaccount_reservationfond rsv,
					public.cddaccount_ordrepayment op
					where op.compte_id = td.id
					and td.short_compte = %s
					and op.gestion_id = ca.id
					and ca.id = %s
					and td.poste_id=%s
					and rsv.ordre_id=op.id
					and op.etape='PRISE_EN_CHARGE'
					and rsv.close=false
					group by  ca.id,  td.short_compte, td.libelle, op.type_nature
					UNION
SELECT ca.id as id_annee, 0 as reliquat,
			td.short_compte, td.libelle, 'FONCTIONNEMENT' as type_nature 
			FROM public.cddaccount_comptedepot td,
			public.cddaccount_anneecomptable ca
			WHERE td.short_compte = %s
			and ca.id = %s
			and td.poste_id=%s
	) as tb
group by  id_annee,  short_compte, libelle, type_nature
order by  id_annee,  short_compte, libelle, type_nature;"""

	with connection.cursor() as cursor:
		if compte:
			cursor.execute(sql_str, [compte, gestion, poste, compte, gestion, poste])
		else:
			cursor.execute(sql_str, [gestion, poste, gestion, poste, ])
		# rows = cursor.fetchall()
		columns = [col[0] for col in cursor.description]
		rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

	return rows




def get_trx_rows_sql(poste, gestion, compte=None):
	sql_str = """SELECT id_annee, sum(amount_fonc) as r_fonct,sum(amount_invest) as r_insvest,
			short_compte, libelle, type_nature, sum(fc_amount) 
			FROM (
SELECT j.annee_comptable_id as id_annee, 0 as amount_fonc,0 as amount_invest,
			t.account_depot as short_compte, td.libelle, t.type_nature, sum(t.fc_amount) as fc_amount
		FROM public.cddaccount_transaction t, 
		public.cddaccount_comptedepot td,
		public.cddaccount_journeecomptable j,
		public.cddaccount_anneecomptable ca	
		where t.account_depot = td.short_compte
		and t.jour_comptable_id = j.id		--
		and j.annee_comptable_id = ca.id
		and j.annee_comptable_id = %s
		and t.poste_comptable = %s
		group by  j.annee_comptable_id,  t.account_depot, td.libelle, t.type_nature
			UNION 
SELECT ca.id as id_annee, 0 as amount_fonc,0 as amount_invest,
			td.short_compte as short_compte, td.libelle, 'FONCTIONNEMENT' as type_nature, 0 as fc_amount
			FROM public.cddaccount_comptedepot td,
			public.cddaccount_anneecomptable ca,
			public.core_postecomptable tp	
			WHERE tp.id = td.poste_id
			and ca.id = %s
			and tp.reference=%s
			UNION
			SELECT ca.id as id_annee, sum(r.amount_fonc) as amount_fonc,sum(r.amount_invest) as amount_invest,
			td.short_compte as short_compte, td.libelle, 'FONCTIONNEMENT' as type_nature, 0 as fc_amount
		FROM public.cddaccount_comptedepot td,
		public.cddaccount_anneecomptable ca,		
		public.cddaccount_report r,
		public.core_postecomptable p
		where td.poste_id = p.id 
		and r.compte_id=td.id
		and r.gestion_courant_id=ca.id
		and ca.id = %s
		and p.reference = %s
		group by  ca.id,  td.short_compte, td.libelle

			) as tb
			group by  id_annee,  short_compte, libelle, type_nature
			order by  id_annee,  short_compte, libelle, type_nature;"""
	if compte:
		sql_str = """SELECT id_annee, sum(amount_fonc) as r_fonct,sum(amount_invest) as r_insvest,
			short_compte, libelle, type_nature, sum(fc_amount) 
			FROM (
SELECT j.annee_comptable_id as id_annee, 0 as amount_fonc,0 as amount_invest,
			t.account_depot as short_compte, td.libelle, t.type_nature, sum(t.fc_amount) as fc_amount
		FROM public.cddaccount_transaction t, 
		public.cddaccount_comptedepot td,
		public.cddaccount_journeecomptable j,
		public.cddaccount_anneecomptable ca	
		where td.short_compte = %s
		and t.account_depot = td.short_compte
		and t.jour_comptable_id = j.id		--
		and j.annee_comptable_id = ca.id
		and j.annee_comptable_id = %s
		and t.poste_comptable = %s
		group by  j.annee_comptable_id,  t.account_depot, td.libelle, t.type_nature
			UNION 
SELECT ca.id as id_annee, 0 as amount_fonc,0 as amount_invest,
			td.short_compte as short_compte, td.libelle, 'FONCTIONNEMENT' as type_nature, 0 as fc_amount
			FROM public.cddaccount_comptedepot td,
			public.cddaccount_anneecomptable ca,
			public.core_postecomptable tp	
			WHERE tp.id = td.poste_id
			and td.short_compte = %s
			and ca.id = %s
			and tp.reference=%s
			UNION
			SELECT ca.id as id_annee, sum(r.amount_fonc) as amount_fonc,sum(r.amount_invest) as amount_invest,
			td.short_compte as short_compte, td.libelle, 'FONCTIONNEMENT' as type_nature, 0 as fc_amount
		FROM public.cddaccount_comptedepot td,
		public.cddaccount_anneecomptable ca,		
		public.cddaccount_report r,
		public.core_postecomptable p
		where td.short_compte = %s		
		and td.poste_id = p.id 
		and r.compte_id=td.id
		and r.gestion_courant_id=ca.id
		and ca.id = %s
		and p.reference = %s
		group by  ca.id,  td.short_compte, td.libelle

			) as tb
			group by  id_annee,  short_compte, libelle, type_nature
			order by  id_annee,  short_compte, libelle, type_nature;"""

	with connection.cursor() as cursor:
		if compte:
			cursor.execute(sql_str, [compte, gestion, poste, compte, gestion, poste, compte, gestion, poste])
		else:
			cursor.execute(sql_str, [gestion, poste, gestion, poste, gestion, poste])
		# rows = cursor.fetchall()
		columns = [col[0] for col in cursor.description]
		rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

	return rows




def get_trx_rows_sql_new(poste, gestion, compte=None):
	from django.db.models import Sum
	if compte:
		comptes = CompteDepot.objects.filter(short_compte=compte)
	else:
		comptes = CompteDepot.objects.filter(poste__reference=poste)



	rapports_rows = comptes.annotate(

		amount_fonc_fp=Sum(
			Case(
				When(
					compte_reports__typecompte__code='PF',
					compte_reports__gestion_courant_id=gestion,
					then='compte_reports__f_amount'
				),
				default=0,
				output_field=IntegerField()
			)
		),
		amount_fonc_bg=Sum(
			Case(
				When(
					compte_reports__typecompte__code='BF',
					compte_reports__gestion_courant_id=gestion,
					then='compte_reports__f_amount'
				),
				default=0,
				output_field=IntegerField()
			)
		),
		amount_invest_fp=Sum(
			Case(
				When(
					compte_reports__typecompte__code='PI',
					compte_reports__gestion_courant_id=gestion,
					then='compte_reports__f_amount'
				),
				default=0,
				output_field=IntegerField()
			)
		),
		amount_invest_bg=Sum(
			Case(
				When(
					compte_reports__typecompte__code='BI',
					compte_reports__gestion_courant_id=gestion,
					then='compte_reports__f_amount'
				),
				default=0,
				output_field=IntegerField()
			)
		),
		##amount_fonc_fp = Sum('compte_reports__amount', filter=Case(When(compte_reports__typecompte__code='PF',compte_reports__gestion_courant_id=gestion, then=True))),
		##amount_fonc_bg =Sum('compte_reports__amount', filter=Case(When(compte_reports__typecompte__code='BF',compte_reports__gestion_courant_id=gestion, then=True))),
		##amount_invest_fp=Sum('compte_reports__amount', filter=Case(When(compte_reports__typecompte__code='PI',compte_reports__gestion_courant_id=gestion, then=True))),
		##amount_invest_bg=Sum('compte_reports__amount', filter=Case(When(compte_reports__typecompte__code='BI',compte_reports__gestion_courant_id=gestion, then=True))),
	).values("id", "libelle", "amount_fonc_fp", "amount_fonc_bg", "amount_invest_fp", "amount_invest_bg", "short_compte")



	instances_rows = comptes.annotate(
		amount_fonc_fp=Sum(Case(
			When(compte_ordres__typecompte__code='PF', compte_ordres__gestion_id=gestion,
			     compte_ordres__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE, then='compte_ordres__reservationfond__amount'
			     ),
			default=0,
			output_field=IntegerField())),
		amount_fonc_bg=Sum(Case(
			When(compte_ordres__typecompte__code='BF', compte_ordres__gestion_id=gestion,
			     compte_ordres__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE, then='compte_ordres__reservationfond__amount'
			     ),
			default=0,
			output_field=IntegerField())),
		amount_invest_fp=Sum(Case(
			When(compte_ordres__typecompte__code='PI', compte_ordres__gestion_id=gestion,
			     compte_ordres__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE, then='compte_ordres__reservationfond__amount'
			     ),
			default=0,
			output_field=IntegerField())),
		amount_invest_bg=Sum(Case(
			When(compte_ordres__typecompte__code='BI', compte_ordres__gestion_id=gestion,
			     compte_ordres__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE, then='compte_ordres__reservationfond__amount'
			     ),
			default=0,
			output_field=IntegerField())),
	).values("id", "libelle", "amount_fonc_fp", "amount_fonc_bg", "amount_invest_fp", "amount_invest_bg",
	         "short_compte")



	clause="WHERE p.reference = '{}'  and (j.annee_comptable_id = {} OR j.annee_comptable_id IS NULL)".format(poste, gestion,)
	if compte:
		clause+=" and cpt.short_compte ='{}'".format(compte)
	if poste:
		clause += "AND (t.poste_comptable = '{}' OR t.poste_comptable IS NULL)".format( poste)


	sql_str="""SELECT 
    cpt.id AS id,
    cpt.libelle AS libelle,
    cpt.short_compte AS short_compte,
    COALESCE(SUM(CASE WHEN ty.code = 'BI' THEN t.fc_amount ELSE 0 END), 0) AS amount_invest_bg,
    COALESCE(SUM(CASE WHEN ty.code = 'BF' THEN t.fc_amount ELSE 0 END), 0) AS amount_fonc_bg,
    COALESCE(SUM(CASE WHEN ty.code = 'PI' THEN t.fc_amount ELSE 0 END), 0) AS amount_invest_fp,
    COALESCE(SUM(CASE WHEN ty.code = 'PF' THEN t.fc_amount ELSE 0 END), 0) AS amount_fonc_fp
	FROM public.cddaccount_comptedepot cpt
	LEFT JOIN public.cddaccount_transaction t ON cpt.short_compte = t.account_depot
	LEFT JOIN public.cddaccount_typecomptetrx ty ON t.typecompte_id = ty.id
	LEFT JOIN public.cddaccount_journeecomptable j ON t.jour_comptable_id = j.id
	LEFT JOIN public.core_postecomptable p ON cpt.poste_id = p.id
	
	{}
	GROUP BY cpt.id, cpt.libelle, cpt.short_compte
	ORDER BY cpt.id;
	""".format(clause,)

	trx_rows=[]



	with connection.cursor() as cursor:
		cursor.execute(sql_str, )
		# rows = cursor.fetchall()
		columns = [col[0] for col in cursor.description]
		trx_rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
	"""
	short_comptes=comptes.values_list("short_compte")
	xc_rows = Transaction.objects.filter(jour_comptable__annee_comptable_id=gestion,account_depot__in=short_comptes).values("account_depot").annotate(

		amount_fonc_fp=Sum(
			Case(
				When(
					typecompte__code='PF',
					then='fc_amount'
				),
				default=0,
				output_field=IntegerField()
			)
		),
		amount_fonc_bg=Sum(
			Case(
				When(
					typecompte__code='BF',
					then='fc_amount'
				),
				default=0,
				output_field=IntegerField()
			)
		),
		amount_invest_fp=Sum(
			Case(
				When(
					typecompte__code='PI',
					then='fc_amount'
				),
				default=0,
				output_field=IntegerField()
			)
		),
		amount_invest_bg=Sum(
			Case(
				When(
					typecompte__code='BI',
					then='fc_amount'
				),
				default=0,
				output_field=IntegerField()
			)
		),
		).values( "amount_fonc_fp", "amount_fonc_bg", "amount_invest_fp", "amount_invest_bg",
	         "account_depot")
	"""


	#750 005 000

	sd = sorted(list(trx_rows), key=lambda k: k['short_compte'], reverse=False)

	instances = sorted(list(instances_rows), key=lambda k: k['short_compte'], reverse=False)


	reports = sorted(list(rapports_rows), key=lambda k: k['short_compte'], reverse=False)


	return sd,instances,reports





@login_required
def disponible_situation_view(request):
	template = "cddaccount/disponibles_new.html"
	# gestion= AnneeComptable.active_gestion().id
	user = request.user
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
	compte = request.GET.get('compte', None)
	if gestion_v is None:
		gestionO = AnneeComptable.active_gestion()
		gestion_v = gestionO.id
	else:
		gestionO = AnneeComptable.objects.get(id=gestion_v)
	query_string = "?format=pdf&gestion={}&poste={}".format(gestionO.id, poste.reference)
	query_excel_string = "?format=excel&gestion={}&poste={}".format(gestionO.id, poste.reference)

	cdd = None
	if compte:
		cdd = CompteDepot.objects.get(id=compte).short_compte
		query_string = "{}&compte={}".format(query_string, compte)
		query_excel_string = "{}&compte={}".format(query_excel_string, compte)

	pdf_url = "{}{}".format(reverse_lazy('cddaccount:disponible_situation_view'), query_string)
	excel_url = "{}{}".format(reverse_lazy('cddaccount:disponible_situation_view'), query_excel_string)


	sd, instances, reports=get_trx_rows_sql_new(poste_comptable, gestion_v, compte=cdd)


	d = []
	total_dispos = {"amount_fonc_fp": 0, "amount_fonc_bg": 0,"amount_invest_fp": 0, "amount_invest_bg": 0,"total":0}
	for key, items in itertools.groupby(sd, operator.itemgetter('short_compte')):
		rsvitems = list(items)
		libelle =rsvitems[0]["libelle"]
		_r = {"short_compte":key,"libelle":libelle, "amount_fonc_fp": 0, "amount_fonc_bg": 0,"amount_invest_fp": 0, "amount_invest_bg": 0,"total":0}


		for rsv in rsvitems:
			_r["amount_fonc_fp"] += int(rsv["amount_fonc_fp"])
			_r["amount_fonc_bg"] += int(rsv["amount_fonc_bg"])
			_r["amount_invest_fp"] += int(rsv["amount_invest_fp"])
			_r["amount_invest_bg"] += int(rsv["amount_invest_bg"])

			total_dispos["amount_fonc_fp"] += int(rsv["amount_fonc_fp"])
			total_dispos["amount_fonc_bg"] += int(rsv["amount_fonc_bg"])
			total_dispos["amount_invest_fp"] += int(rsv["amount_invest_fp"])
			total_dispos["amount_invest_bg"] += int(rsv["amount_invest_bg"])



		for inst, datas in itertools.groupby(reports, operator.itemgetter('short_compte')):
			if inst == key:
				rsvitems = list(datas)
				for rsv in rsvitems:

					_r["amount_fonc_fp"] += int(rsv.get("amount_fonc_fp","0"))
					_r["amount_fonc_bg"] += int(rsv["amount_fonc_bg"])
					_r["amount_invest_fp"] += int(rsv["amount_invest_fp"])
					_r["amount_invest_bg"] += int(rsv["amount_invest_bg"])

					total_dispos["amount_fonc_fp"] += int(rsv["amount_fonc_fp"])
					total_dispos["amount_fonc_bg"] += int(rsv["amount_fonc_bg"])
					total_dispos["amount_invest_fp"] += int(rsv["amount_invest_fp"])
					total_dispos["amount_invest_bg"] += int(rsv["amount_invest_bg"])
				break

		for inst, datas in itertools.groupby(instances, operator.itemgetter('short_compte')):
			if inst == key:
				rsvitems = list(datas)
				for rsv in rsvitems:
					_r["amount_fonc_fp"] -= int(rsv["amount_fonc_fp"])
					_r["amount_fonc_bg"] -= int(rsv["amount_fonc_bg"])
					_r["amount_invest_fp"] -= int(rsv["amount_invest_fp"])
					_r["amount_invest_bg"] -= int(rsv["amount_invest_bg"])

					total_dispos["amount_fonc_fp"] -= int(rsv["amount_fonc_fp"])
					total_dispos["amount_fonc_bg"] -= int(rsv["amount_fonc_bg"])
					total_dispos["amount_invest_fp"] -= int(rsv["amount_invest_fp"])
					total_dispos["amount_invest_bg"] -= int(rsv["amount_invest_bg"])
				break
		_r["total"] =_r["amount_fonc_fp"]+_r["amount_fonc_bg"] +_r["amount_invest_fp"] +_r["amount_invest_bg"]

		d.append(_r)
	total_dispos["total"] = total_dispos["amount_fonc_fp"] + total_dispos["amount_fonc_bg"] + total_dispos["amount_invest_fp"] + total_dispos["amount_invest_bg"]
	my_dict = total_dispos

	gestion = gestionO.year()
	start_date = "{:%d/%m/%Y}".format(datetime.date.today(), )
	url_rb = reverse_lazy('cddaccount:show_disponible_form_view')
	title = "SITUATION DES DISPONIBLES"

	context = {"pdf_url": pdf_url, "url_excel_rb": excel_url, "title": title, "totaux": my_dict, "date": start_date,
	           "balances": d, "poste": poste_comptable_name, "gestion": gestion, "url_rb": url_rb}
	format_output = request.GET.get('format', "html")
	if format_output == "pdf":
		context.update({"pagesize": "A4"})
		template = "cddaccount/disponibles_pdf.html"
		gettemplate = get_template(template)
		html = gettemplate.render(context)
		result = BytesIO()
		pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
		if pdf.err:
			return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
		return HttpResponse(result.getvalue(), content_type='application/pdf')

	elif format_output =="excel":
		if len(d) > 0:
			df = pd.DataFrame(data=d)
			df = df.fillna('')
			df.rename(columns={"amount_fonc_bg": "MONTANT  FONC TRANSFERT","amount_invest_bg": "MONTANT INV TRANSFERT","amount_fonc_fp": "MONTANT FONC FOND PROPRE","amount_invest_fp": "MONTANT INV FOND PROPRE", "libelle": "LIELLE", "short_compte": "COMPTE",
			                   "balance_insvest": "INVESTISSEMENT", "balance_fonct": "FONCTIONNEMENT","total":"SOLDE"}, inplace=True)

			cols = ['COMPTE', 'LIELLE','MONTANT  FONC TRANSFERT','MONTANT INV TRANSFERT','MONTANT FONC FOND PROPRE', 'MONTANT INV FOND PROPRE', 'SOLDE']
			df = df[cols]

		else:
			df=pd.DataFrame()
		if not df.empty:
			messages.success(request, "Fichier généré avec succès")
			with BytesIO() as b:
				with pd.ExcelWriter(b) as writer:
					df.to_excel(writer, sheet_name="Data", index=False)
				filename = 'situation_disponible_{}'.format(datetime.datetime.now())
				content_type = 'application/vnd.ms-excel'
				response = HttpResponse(b.getvalue(), content_type=content_type)
				response['Content-Disposition'] = 'attachment; filename="' + filename + '.xlsx"'
				return response
		else:
			messages.error(request, "Fichier non généré ")


	else:
		return render(request, template, context)





@login_required
def disponible_situation_view_deprecate(request):
	template = "cddaccount/disponibles.html"
	# gestion= AnneeComptable.active_gestion().id
	user = request.user
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
	compte = request.GET.get('compte', None)
	if gestion_v is None:
		gestionO = AnneeComptable.active_gestion()
		gestion_v = gestionO.id
	else:
		gestionO = AnneeComptable.objects.get(id=gestion_v)
	query_string = "?format=pdf&gestion={}&poste={}".format(gestionO.id, poste.reference)

	cdd = None
	if compte:
		cdd = CompteDepot.objects.get(id=compte).short_compte
		query_string = "{}&compte={}".format(query_string, compte.id)

	pdf_url = "{}{}".format(reverse_lazy('cddaccount:disponible_situation_view'), query_string)

	l = get_trx_rows_sql(poste_comptable, gestion_v, compte=cdd)
	instances = get_instances_rows_sql(poste.id, gestion_v, compte=cdd)

	reports = get_report_rows_sql(poste.id, gestion_v, compte=cdd)

	sd = sorted(list(l), key=lambda k: k['short_compte'], reverse=False)
	instances = sorted(list(instances), key=lambda k: k['short_compte'], reverse=False)

	reports = sorted(list(reports), key=lambda k: k['short_compte'], reverse=False)

	# my_dict = collections.Counter()
	balance_fonct = 0
	balance_insvest = 0

	inst_fonct = 0
	inst_insvest = 0
	balance = 0
	total_inst = 0
	report_fonct = 0
	report_total = 0
	report_invest = 0
	d = []
	for key, items in itertools.groupby(sd, operator.itemgetter('short_compte')):

		_r = {"report_fonct": 0, "report_insvest": 0}
		for inst, datas in itertools.groupby(reports, operator.itemgetter('short_compte')):
			if inst == key:
				rsvitems = list(datas)
				for rsv in rsvitems:
					_r["report_fonct"] = int(rsv["amount_fonc"])
					_r["report_insvest"] = int(rsv["amount_invest"])

					report_fonct += int(rsv["amount_fonc"])
					report_invest += int(rsv["amount_invest"])
				break

		_y = {"instance_fonct": 0, "instance_insvest": 0}
		for inst, datas in itertools.groupby(instances, operator.itemgetter('short_compte')):
			if inst == key:
				rsvitems = list(datas)
				for rsv in rsvitems:
					if rsv["type_nature"] == "FONCTIONNEMENT":
						_y["instance_fonct"] = int(rsv["sum"])
						inst_fonct += int(rsv["sum"])
						total_inst += int(rsv["sum"])
					if rsv["type_nature"] == "INVESTISSEMENT":
						_y["instance_insvest"] = int(rsv["sum"])
						inst_insvest += int(rsv["sum"])
						total_inst += int(rsv["sum"])
				break
		_datas = list(items)
		_x = {"short_compte": key, "libelle": _datas[0]["libelle"], "balance_fonct": 0, "balance_insvest": 0,
		      "balance": 0}
		_balance = 0
		for c in _datas:
			if c["type_nature"] == "FONCTIONNEMENT":
				_x["balance_fonct"] = int(c["sum"])
				balance_fonct += int(c["sum"])
				_balance += int(c["sum"])
				balance += int(c["sum"])

			if c["type_nature"] == "INVESTISSEMENT":
				_x["balance_insvest"] = int(c["sum"])
				balance_insvest += int(c["sum"])
				_balance += int(c["sum"])
				balance += int(c["sum"])
		_x["balance"] = _balance

		_x["balance_insvest"] -= _y["instance_insvest"]
		_x["balance_fonct"] -= _y["instance_fonct"]

		_x["balance_insvest"] += _r["report_insvest"]
		_x["balance_fonct"] += _r["report_fonct"]

		_x["balance"] = _balance - _y["instance_fonct"] - _y["instance_insvest"] + _r["report_fonct"] + _r[
			"report_insvest"]
		d.append(_x)
	report_total = report_invest + report_fonct
	my_dict = {"balance_insvest": balance_insvest - inst_insvest + report_invest,
	           "balance": balance - total_inst + report_total,
	           "balance_fonct": balance_fonct - inst_fonct + report_fonct}

	gestion = gestionO.year()
	start_date = "{:%d/%m/%Y}".format(datetime.date.today(), )
	url_rb = reverse_lazy('cddaccount:show_disponible_form_view')
	url_excel_rb = reverse_lazy('cddaccount:generate_sitdisponible_in_excel')
	title = "SITUATION DES DISPONIBLES"

	context = {"pdf_url": pdf_url, "url_excel_rb": url_excel_rb, "title": title, "totaux": my_dict, "date": start_date,
	           "balances": d, "poste": poste_comptable_name, "gestion": gestion, "url_rb": url_rb}
	format_output = request.GET.get('format', "html")
	if format_output == "pdf":
		context.update({"pagesize": "A4"})
		template = "cddaccount/disponibles_pdf.html"
		gettemplate = get_template(template)
		html = gettemplate.render(context)
		result = BytesIO()
		pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
		if pdf.err:
			return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
		return HttpResponse(result.getvalue(), content_type='application/pdf')
	else:
		return render(request, template, context)



@login_required
def show_opbynature_form_view(request):
	template = "cddaccount/report_form.html"
	user = request.user

	success_url = reverse_lazy('cddaccount:show_opbynature_form_view')

	if request.method == 'POST':
		if hasattr(user, "agent_postecomptable"):
			form = OPbyNatureForm(request.POST)
			poste = user.agent_postecomptable.poste
		else:
			form = OPbyNatureTGForm(request.POST)
		if form.is_valid():
			if request and not is_ajax(request.META):

				date_rg = form.cleaned_data['period']
				gestion = form.cleaned_data['gestion']
				startdate, enddate = date_rg.lower, date_rg.upper

				str_date = "{:%Y-%m-%d}".format(startdate)
				end_date = "{:%Y-%m-%d}".format(enddate)
				if "postes" in form.cleaned_data:
					poste = form.cleaned_data['postes']

				success_url = "{}?qstartdate={}&qenddate={}&gestion={}&poste={}".format(
					reverse_lazy('cddaccount:op_by_nature_view'), str_date, end_date, gestion.id, poste.reference)

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		if hasattr(user, "agent_postecomptable"):
			form = OPbyNatureForm()
			poste = user.agent_postecomptable.poste
		else:

			form = OPbyNatureTGForm()

	context = {"form": form, 'title': "Choisir ", }
	return render(request, template, context)


@login_required
def op_by_nature_view(request):
	template = "cddaccount/op_by_nature.html"
	user = request.user
	last_balance = 0

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
		gestion = AnneeComptable.active_gestion()
	else:
		gestion = AnneeComptable.objects.get(id=gestion_v)

	qenddate = request.GET.get('qenddate', None)
	if qenddate is None:
		enddate = datetime.datetime.now()
	else:
		format = "%Y-%m-%d"
		enddate = datetime.datetime.strptime(qenddate, format)
	# enddate = enddate + datetime.timedelta(days=1)

	qstartdate = request.GET.get('qstartdate', None)
	if qstartdate is None:
		startdate = datetime.datetime.now()

	else:
		format = "%Y-%m-%d"
		startdate = datetime.datetime.strptime(qstartdate, format)

	include_enddate = enddate + datetime.timedelta(days=1)

	print_date = datetime.date.today()

	all_trx = OrdrePayment.objects.by_agent(user).filter(compte__poste__reference=poste_comptable,
	                                                     date_reception__range=(startdate, include_enddate)).values(
		"nature__name", "compte__short_compte", "compte__libelle_court", "sig_reference", "amount", "id",
		"beneficiaire", "date_reception")

	datas_r = sorted(list(all_trx), key=lambda k: k['nature__name'], reverse=False)
	z = {"amount": 0}
	x = []
	total_general = 0
	ligne_general = 0
	for key, cpts in itertools.groupby(datas_r, operator.itemgetter('nature__name')):
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
		x.append({"nature": key, "items": c, "total": my_dict, 'ligne': ligne})

	ordres_debit = all_trx.values("nature__name").annotate(amount=Sum('amount', output_field=IntegerField()),
	                                                       nombre=Count('id', output_field=IntegerField()))

	s = "{:%Y-%m-%d}".format(startdate, )
	d = "{:%Y-%m-%d}".format(enddate, )

	url_report_pdf = "{}?format=pdf&qstartdate={}&qenddate={}&gestion={}&poste={}".format(
		reverse_lazy('cddaccount:op_by_nature_view'), s, d, gestion.id, poste_comptable)

	start_date = "{:%d/%m/%Y}".format(startdate, )
	end_date = "{:%d/%m/%Y}".format(enddate, )
	print_date = "{:%d/%m/%Y}".format(print_date, )
	disponible = None
	t_pcharges = None
	pcharges = None
	url_rb = reverse_lazy('cddaccount:show_opbynature_form_view')
	title = "SITUATION DES OPÉRATIONS RECUES"

	context = {"url_report_pdf": url_report_pdf, "title": title, "ligne_general": ligne_general,
	           "total_general": total_general, "date": print_date, "gestion": gestion.year, "url_rb": url_rb,
	           "disponible": disponible, "lignes": x, "last_balance": last_balance, "start_date": start_date,
	           "end_date": end_date, "trxs": ordres_debit, "print_date": print_date, "annee_comptable": gestion.year,
	           "poste": poste_comptable_name}
	format_output = request.GET.get('format', "html")
	if format_output == "pdf":
		context.update({"pagesize": "A4"})
		template = "cddaccount/op_by_nature_pdf.html"
		gettemplate = get_template(template)
		html = gettemplate.render(context)
		result = BytesIO()
		pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
		if pdf.err:
			return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
		return HttpResponse(result.getvalue(), content_type='application/pdf')
	else:
		return render(request, template, context)


@login_required
def seesolde_op_view(request):
	template = "cddaccount/see_solde_op.html"
	success_url = reverse_lazy('cddaccount:seesolde_op_view')
	comptes = CompteDepot.objects.by_agent(request.user)

	if request.method == 'POST':
		form = SeeSoldeOrdrePaymentModelForm(request.POST)
		form.fields["compte"].queryset = comptes
		if form.is_valid():
			if request and not is_ajax(request.META):
				compte = form.cleaned_data['compte']
				gestion = form.cleaned_data['gestion']

				success_url = "{}?qstartdate={}&qenddate={}&gestion={}".format(
					reverse_lazy('cddaccount:seesolde_op_view'), "", "", gestion.id)

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		form = SeeSoldeOrdrePaymentModelForm()
		form.fields["compte"].queryset = comptes

	context = {"form": form, 'title': "Consultation du solde d'un compte", }
	return render(request, template, context)

# context = {"title":title,"ligne_general":ligne_general,"total_general":total_general,"date":print_date,"gestion":gestion.year,"url_rb":url_rb,"disponible":disponible,"lignes":x,"last_balance":last_balance,"start_date":start_date,"end_date":end_date,"trxs":ordres_debit,"print_date":print_date,"annee_comptable":gestion.year,"poste":user.agent_postecomptable.poste.name}
# return render(request, template, context)


@login_required
def show_disponible_form_view(request):
	template = "cddaccount/report_form.html"
	success_url = reverse_lazy('cddaccount:show_disponible_form_view')
	user = request.user
	if request.method == 'POST':
		if hasattr(user, "agent_postecomptable"):
			form = NewDisponibleForm(request.POST)
			comptes = CompteDepot.objects.by_agent(request.user)
			form.fields["comptes"].queryset = comptes
			poste = user.agent_postecomptable.poste
		else:
			form = NewDisponibleTGForm(request.POST)

		if form.is_valid():
			if request and not is_ajax(request.META):
				gestion = form.cleaned_data['gestion']
				compte = form.cleaned_data['comptes']
				if "postes" in form.cleaned_data:
					poste = form.cleaned_data['postes']
				query_string = "?gestion={}&poste={}".format(gestion.id, poste.reference)

				if compte:
					query_string = "{}&compte={}".format(query_string, compte.id)

				success_url = "{}{}".format(reverse_lazy('cddaccount:disponible_situation_view'), query_string)

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		if hasattr(user, "agent_postecomptable"):
			form = NewDisponibleForm()
			comptes = CompteDepot.objects.by_agent(request.user)
			form.fields["comptes"].queryset = comptes
			poste = user.agent_postecomptable.poste
		else:
			form = NewDisponibleTGForm()

	context = {"form": form, 'title': "Choisir ", }
	return render(request, template, context)


@login_required
def show_situation_cdd_form_view(request):
	template = "cddaccount/report_form.html"
	success_url = reverse_lazy('cddaccount:show_situation_cdd_form_view')  # situation_op_all_view
	# get_cdd_with_gerant(self.request)
	user = request.user

	if request.method == 'POST':

		if hasattr(user, "agent_postecomptable"):
			form = NewDisponibleForm(request.POST)
			comptes = CompteDepot.objects.by_agent(request.user)

			form.fields["comptes"].queryset = comptes
			poste = user.agent_postecomptable.poste
		else:
			form = NewDisponibleTGForm(request.POST)
		# comptes = CompteDepot.objects.by_agent(request.user)
		# form.fields["comptes"].queryset = comptes

		if form.is_valid():
			if request and not is_ajax(request.META):
				gestion = form.cleaned_data['gestion']
				compte = form.cleaned_data['comptes']
				query_string = "?gestion={}".format(gestion.id, )

				if "postes" in form.cleaned_data:
					poste = form.cleaned_data['postes']
				query_string = "{}&poste={}".format(query_string, poste.reference)
				if compte:
					query_string = "{}&compte={}".format(query_string, compte.id)
				print(form.cleaned_data)
				success_url = "{}{}".format(reverse_lazy('cddaccount:situation_op_all_view'), query_string)

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:

		if hasattr(user, "agent_postecomptable"):
			form = NewDisponibleForm()
			comptes = CompteDepot.objects.by_agent(request.user)
			form.fields["comptes"].queryset = comptes

		else:
			form = NewDisponibleTGForm()
	# form.fields["compte"].queryset = comptes

	context = {"form": form, 'title': "Choisir ", }
	return render(request, template, context)


@login_required
def show_sit_instance_op_s_form_view(request):
	template = "cddaccount/report_form.html"
	success_url = reverse_lazy('cddaccount:show_sit_instance_op_s_form_view')  # situation_op_all_view salaire
	# get_cdd_with_gerant(self.request)

	user = request.user

	if request.method == 'POST':
		if hasattr(user, "agent_postecomptable"):
			form = NewDisponibleForm(request.POST)
			comptes = CompteDepot.objects.by_agent(request.user)
			form.fields["comptes"].queryset = comptes
			poste = user.agent_postecomptable.poste
		else:
			form = NewDisponibleTGForm(request.POST)

		if form.is_valid():
			if request and not is_ajax(request.META):
				gestion = form.cleaned_data['gestion']
				compte = form.cleaned_data['comptes']
				query_string = "?gestion={}".format(gestion.id, )
				if compte:
					query_string = "{}&compte={}".format(query_string, compte.id)

				if "postes" in form.cleaned_data:
					poste = form.cleaned_data['postes']
				query_string = "{}&poste={}".format(query_string, poste.reference)

				success_url = "{}{}".format(reverse_lazy('cddaccount:situation_op_s_view'), query_string)

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:

		if hasattr(user, "agent_postecomptable"):
			form = NewDisponibleForm()
			comptes = CompteDepot.objects.by_agent(request.user)
			form.fields["comptes"].queryset = comptes
		else:
			form = NewDisponibleTGForm()

	context = {"form": form, 'title': "Choisir ", }
	return render(request, template, context)


@login_required
def show_sit_instance_op_hs_form_view(request):
	template = "cddaccount/report_form.html"
	success_url = reverse_lazy('cddaccount:show_sit_instance_op_hs_form_view')  # situation_op_all_view salaire
	user = request.user  # get_cdd_with_gerant(self.request)

	if request.method == 'POST':
		if hasattr(user, "agent_postecomptable"):
			form = NewDisponibleForm(request.POST)
			comptes = CompteDepot.objects.by_agent(request.user)
			form.fields["comptes"].queryset = comptes
			poste = user.agent_postecomptable.poste
		else:
			form = NewDisponibleTGForm(request.POST)
		if form.is_valid():
			if request and not is_ajax(request.META):
				gestion = form.cleaned_data['gestion']
				compte = form.cleaned_data['comptes']
				query_string = "?gestion={}".format(gestion.id, )
				if compte:
					query_string = "{}&compte={}".format(query_string, compte.id)
				if "postes" in form.cleaned_data:
					poste = form.cleaned_data['postes']
				query_string = "{}&poste={}".format(query_string, poste.reference)

				success_url = "{}{}".format(reverse_lazy('cddaccount:situation_op_hs_view'), query_string)

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		if hasattr(user, "agent_postecomptable"):
			form = NewDisponibleForm()
			comptes = CompteDepot.objects.by_agent(request.user)
			form.fields["comptes"].queryset = comptes
		else:
			form = NewDisponibleTGForm()

	context = {"form": form, 'title': "Choisir ", }
	return render(request, template, context)





import pandas as pd
from tablib import Dataset

@login_required
def balance_view(request):
	template = "cddaccount/balance_new.html"
	user = request.user

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
	gObj = AnneeComptable.active_gestion()

	gestion = request.GET.get('gestion', gObj.id)
	gObj = AnneeComptable.objects.get(id=gestion)
	geyear = gObj.year

	q_search = request.GET.get('qdate', None)
	if q_search is None:
		enddate = datetime.datetime.now()
	else:
		q = q_search
		format = "%Y-%m-%d"
		enddate = datetime.datetime.strptime(q, format)

	d, totaux = update_newbalance_by_date(
		CompteDepot.objects.by_agent(request.user).filter(poste__reference=poste_comptable), enddate, gestion)

	str_date = "{:%d/%m/%Y}".format(enddate)

	url_rb = reverse_lazy('cddaccount:genere_balance_view')
	if q_search is None:
		url_report_pdf ="{}?format=pdf".format(reverse_lazy('cddaccount:balance_view'))
		url_report_excel = "{}?format=excel".format(reverse_lazy('cddaccount:balance_view'))

	else:
		url_report_pdf = "{}?format=pdf&qdate={}&poste={}&gestion={}".format(reverse_lazy('cddaccount:balance_view'), q_search,
		                                                          poste_comptable, gestion)
		url_report_excel = "{}?format=excel&qdate={}&poste={}&gestion={}".format(reverse_lazy('cddaccount:balance_view'),
		                                                                     q_search,
		                                                                     poste_comptable, gestion)

	context = {"url_report_excel":url_report_excel,"url_report_pdf": url_report_pdf, "totaux": totaux, "balances": d, "poste": poste_comptable_name,
	           "date": str_date, "gestion": geyear, "url_rb": url_rb}

	format_output = request.GET.get('format', "html")
	if format_output == "pdf":
		context.update({"pagesize": "A4"})
		template = "cddaccount/balance_new_pdf.html"
		gettemplate = get_template(template)
		html = gettemplate.render(context)
		result = BytesIO()
		pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
		if pdf.err:
			return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
		return HttpResponse(result.getvalue(), content_type='application/pdf')
	elif format_output == "excel":
		if len(d) > 0:
			#print(d)
			flat_data = []
			for entry in d:
				code = entry['code']
				for balance in entry['balances']:
					balance['code'] = code
					flat_data.append(balance)
				h=entry['totaux']

				h.update({"libelle": "TOTAL COMPTE GENERIQUE {}".format(code), "compte": "", "poste": "", "code": code,"provenance":""})

				flat_data.append(h)
			totaux.update({"libelle": "TOTAL ", "compte": "", "poste": "", "code": "","provenance":""})
			flat_data.append(totaux)
			df = pd.DataFrame(data=flat_data)

			df.rename(
				columns={"be_credit_fonc": "BE CREDIT FONC",
				         "be_credit_inv": "BE CREDIT INV", "op_debit_fonc": "OP DEBIT FONC",
				         "op_debit_inv": "OP DEBIT FONC",
				         "op_credit_fonc": "OP CREDIT FONC",
				         "op_credit_inv": "OP CREDIT INV",
				         "total_debit_fonc": "TT DEBIT FONC",
				         "total_debit_inv": "TT DEBIT INV",
				         "total_credit_fonc": "TT CREDIT FONC",
				         "total_credit_inv": "TT CREDIT INV",
				         "bs_debit_fonc": "BS DEBIT FONC",
				         "bs_debit_inv": "BS DEBIT INV",
				         "bs_credit_fonc": "BS CREDIT FONC",
				         "bs_credit_inv": "BS CREDIT INV",
				         "libelle": "LIBELLE",
				         "poste": "POSTE",
				         "compte": "COMPTE",
				         "provenance": "PROVENANCE",
				         "code": "CODE"}, inplace=True)
			# df.loc['Total'] = df[['balance_fonct', 'balance_insvest', 'balance']].sum()
			df = df.fillna('')


			cols = ["CODE","POSTE","COMPTE","LIBELLE","PROVENANCE","BE CREDIT FONC",	"BE CREDIT INV","OP DEBIT FONC","OP DEBIT FONC","OP CREDIT FONC","OP CREDIT INV","TT DEBIT FONC","TT DEBIT INV","TT CREDIT FONC","TT CREDIT INV","BS DEBIT FONC","BS DEBIT INV","BS CREDIT FONC","BS CREDIT INV"]
			df = df[cols]


		else:
			df = pd.DataFrame()



		# df = generate_sitdisp(user.id)
		if not df.empty:
			messages.success(request, "Fichier généré avec succès")
			with BytesIO() as b:
				with pd.ExcelWriter(b) as writer:
					df.to_excel(writer, sheet_name="BALANCES", index=False)


				filename = 'balances_{}'.format(str_date, )
				content_type = 'application/vnd.ms-excel'
				response = HttpResponse(b.getvalue(), content_type=content_type)
				response['Content-Disposition'] = 'attachment; filename="' + filename + '.xlsx"'

				return response
		else:
			messages.error(request, "Fichier non généré ")

	else:
		return render(request, template, context)


@login_required
def genere_balance_view(request):
	template = "cddaccount/report_form.html"

	success_url = reverse_lazy('cddaccount:genere_balance_view')
	user = request.user

	if request.method == 'POST':
		if hasattr(user, "agent_postecomptable"):
			poste = user.agent_postecomptable.poste
			form = BalanceForm(request.POST)
		else:
			form = BalanceTGForm(request.POST)
		if form.is_valid():
			if request and not is_ajax(request.META):

				date_rg = form.cleaned_data['jour']
				gestion = form.cleaned_data['gestion'].id
				str_date = "{:%Y-%m-%d}".format(date_rg)
				if "postes" in form.cleaned_data:
					poste = form.cleaned_data['postes']

				success_url = "{}?qdate={}&poste={}&gestion={}".format(reverse_lazy('cddaccount:balance_view'),
				                                                       str_date, poste.reference, gestion)

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		if hasattr(user, "agent_postecomptable"):
			poste = user.agent_postecomptable.poste
			form = BalanceForm()
		else:
			form = BalanceTGForm()

	context = {"form": form, 'title': "Choisir la date", }
	return render(request, template, context)


@login_required
def balanceconso_view(request):
	user = request.user
	template = "cddaccount/balanceconso_new.html"
	gestion = AnneeComptable.active_gestion().id

	q_search = request.GET.get('qdate', None)
	if q_search is None:
		enddate = datetime.datetime.now()
	else:
		q = q_search
		format = "%Y-%m-%d"
		enddate = datetime.datetime.strptime(q, format)

	d, totaux = update_newbalance_by_date(CompteDepot.objects.by_agent(user), enddate, gestion)

	str_date = "{:%d/%m/%Y}".format(enddate)
	user = request.user
	gestion = datetime.date.today().year
	url_rb = reverse_lazy('cddaccount:genere_balance_view')
	context = {"totaux": totaux, "balances": d, "poste": user.agent_postecomptable.poste.name, "date": str_date,
	           "gestion": gestion, "url_rb": url_rb}
	return render(request, template, context)


@login_required
def genere_balanceconso_view(request):
	template = "core/add_entity.html"

	success_url = reverse_lazy('cddaccount:genere_balance_view')

	if request.method == 'POST':
		form = BalanceForm(request.POST)
		if form.is_valid():
			if request and not is_ajax(request.META):
				date_rg = form.cleaned_data['jour']
				str_date = "{:%Y-%m-%d}".format(date_rg)

				success_url = "{}?qdate={}".format(reverse_lazy('cddaccount:balance_view'), str_date)

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		form = BalanceForm()

	context = {"form": form, 'title': "Choisir la date", }
	return render(request, template, context)







from wkhtmltopdf.views import PDFTemplateView

class GeneratePDF(PDFTemplateView):
    template_name = 'cddaccount/pdftemplate.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['key'] = 'value'  # Ajouter vos variables de contexte ici
        return context








@login_required
def repport_bf_vise_view(request):
	template = "cddaccount/repport_bf_vise.html"
	# gestion= AnneeComptable.active_gestion().id
	user = request.user
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
		datevisa = datetime.date.today()
	else:
		format = "%Y-%m-%d"
		datevisa = datetime.datetime.strptime(qdatevisa, format)

	qdatevisa2 = request.GET.get('qenddate', None)
	if qdatevisa2 is None:
		datevisa2 = datetime.date.today()
	else:
		format = "%Y-%m-%d"
		datevisa2 = datetime.datetime.strptime(qdatevisa2, format)

	compte_v = request.GET.get('compte', None)

	vd = "{:%Y-%m-%d}".format(datevisa, )

	last_rg = (datevisa, datevisa2 + datetime.timedelta(days=1))

	s = "{:%Y-%m-%d}".format(datevisa, )
	end = "{:%Y-%m-%d}".format(datevisa2, )

	if compte_v:
		# url_report_pdf="{}&compte={}".format(url_report_pdf,compte_v)

		objs = BlocageFond.objects.by_agent(user).filter(jour_comptable__annee_comptable__id=gestion_v,
		                                                   jour_comptable__jour__range=last_rg,
		                                                   reservation__ordre__compte_id=compte_v)
	else:
		objs = BlocageFond.objects.by_agent(user).filter(jour_comptable__annee_comptable__id=gestion_v,
		                                                   jour_comptable__jour__range=last_rg,
		                                                   compte__poste=poste_comptable)

	# d= objs.values("account_depot","reference","reservation__ordre__beneficiaire","libelle","amount")

	d = objs.values("reference").annotate(
		amount=Sum('amount', output_field=IntegerField()),
		account_depot=ExpressionWrapper(F("compte__short_compte"), output_field=CharField()),

		libelle=ExpressionWrapper(F("projet__name"), output_field=CharField()),
		ninea=ExpressionWrapper(F("ninea"), output_field=CharField()),
		prestataire=ExpressionWrapper(F("prestataire"), output_field=CharField()))

	datas_r = sorted(list(d), key=lambda k: k['nature'], reverse=False)
	z = {"amount": 0}
	x = []
	total_general = 0
	ligne_general = 0


	str_date = "{:%d/%m/%Y}".format(datevisa)
	visa_date = "{:%d/%m/%Y} - {:%d/%m/%Y}".format(datevisa, datevisa2)
	gestion = gestionO.year()
	url_rb = reverse_lazy('cddaccount:genere_repport_bfvise_view')

	url_excel_rb = reverse_lazy('cddaccount:generate_opvise_in_excel')

	if compte_v:
		url_excel_rb = "{}?gestion={}&compte={}&poste={}&qstartdate={}&qenddate={}".format(url_excel_rb, gestion_v,
		                                                                                   compte_v, poste_comptable, s,
		                                                                                   end)

		url_report_pdf = "{}?gestion={}&compte={}&poste={}&qstartdate={}&qenddate={}".format(
			reverse_lazy('cddaccount:repport_op_vise_pdf_view'), gestion_v, compte_v, poste_comptable, s, end)
	else:
		url_excel_rb = "{}?gestion={}&poste={}&qstartdate={}&qenddate={}".format(url_excel_rb, gestion_v,
		                                                                         poste_comptable, s, end)
		url_report_pdf = "{}?gestion={}&poste={}&qstartdate={}&qenddate={}".format(
			reverse_lazy('cddaccount:repport_op_vise_pdf_view'), gestion_v, poste_comptable, s, end)

	context = {"url_excel_rb": url_excel_rb, "url_report_pdf": url_report_pdf, "visa_date": visa_date, "balances": d,
	           "poste": poste_comptable_name, "Datas": x, "date": str_date, "gestion": gestion, "url_rb": url_rb}
	return render(request, template, context)






@login_required
def genere_repport_bfvise_view(request):
	template = "cddaccount/report_form.html"

	success_url = reverse_lazy('cddaccount:genere_repport_bfvise_view')
	user = request.user

	if request.method == 'POST':
		if hasattr(user, "agent_postecomptable"):
			form = OpViseForm(request.POST)
			poste = user.agent_postecomptable.poste
			form.fields["comptes"].queryset = CompteDepot.objects.by_agent(user)
		else:
			form = OpViseTGForm(request.POST)
		if form.is_valid():
			if request and not is_ajax(request.META):
				gestion = form.cleaned_data['gestion']
				compte = form.cleaned_data['comptes']

				date_rg = form.cleaned_data['period']

				startdate, enddate = date_rg.lower, date_rg.upper

				str_date = "{:%Y-%m-%d}".format(startdate)
				end_date = "{:%Y-%m-%d}".format(enddate)

				# if moyenpay is None:success_url = "{}&qstartdate={}&qenddate={}

				if "postes" in form.cleaned_data:
					poste = form.cleaned_data['postes']

				success_url = "{}?gestion={}&poste={}&qstartdate={}&qenddate={}".format(
					reverse_lazy('cddaccount:repport_bf_vise_view'), gestion.id, poste.reference, str_date, end_date)

				if compte:
					success_url = "{}?gestion={}&compte={}&poste={}&qstartdate={}&qenddate={}".format(
						reverse_lazy('cddaccount:repport_bf_vise_view'), gestion.id, compte.id, poste.reference,
						str_date, end_date)

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:

		if hasattr(user, "agent_postecomptable"):
			form = OpViseForm()
			poste = user.agent_postecomptable.poste
			form.fields["comptes"].queryset = CompteDepot.objects.by_agent(user)
		else:
			form = OpViseTGForm()

	context = {"form": form, 'title': "Choisir la date", }
	return render(request, template, context)
