
import datetime
import traceback
from django.contrib import messages
from bootstrap_modal_forms.utils import is_ajax
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from psycopg2.extras import DateRange
from django_tables2 import RequestConfig

from cddaccount import  SENS_TRX, NATURE_COMPTE
from cddaccount.forms import ReleveCompteForm, TYPE_RELEVE
from cddaccount.models import ReservationFond, CompteDepot, ETAPE_ORDRE_PAYMENT, PAYMENT_MEAN_TYPE, Transaction, \
	AnneeComptable, Report, ReportGestion, TypeCompteTrx, compute_all_balances_for_compte
from cddaccount.tables import TransactionOPTable

from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.db.models import Sum, Count, IntegerField, Value
from django.db.models.functions import Coalesce
from django.contrib import messages
from django.http import HttpResponse

# import generic UpdateView
import logging
@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def releve_compte_view_old(request, reference, startdate, enddate):
	template = "cddaccount/releve_compte_new.html"
	user = request.user
	format = '%d-%m-%Y'
	compte = get_object_or_404(CompteDepot, short_compte=reference)
	last_balance = 0

	if not compte.can_acces(user):
		raise Http404
	print_date = datetime.date.today()
	rg = DateRange(startdate.date(), startdate.date() + datetime.timedelta(days=1))
	an = AnneeComptable.objects.filter(period__contains=rg).last()

	start_january = datetime.datetime(print_date.year, 1, 1)
	last_january = datetime.datetime(print_date.year - 1, 1, 1)

	last_rg = DateRange(last_january.date(), last_january.date() + datetime.timedelta(days=1))

	previous_anne_comptable = AnneeComptable.objects.filter(period__contains=last_rg).last()

	if previous_anne_comptable:
		try:
			report = Report.objects.get(compte=compte, anne_comptable=previous_anne_comptable)
			last_balance = report.amount_fonc.amount + report.amount_invest.amount

		except Report.DoesNotExist:
			pass

	if an:
		annee_comptable = startdate.year
	else:
		annee_comptable = print_date.year

	all_trx = Transaction.objects.filter(account_depot=reference, created__range=(start_january, enddate))

	trx = all_trx.filter(created__range=(startdate, enddate))
	cheques = trx.filter(payment_mean=PAYMENT_MEAN_TYPE.CHEQUE).count()
	lignes = trx.count()
	ordres_debit = trx.values("sens").annotate(amount=Sum('amount', output_field=IntegerField()))

	last_credit = 0
	last_debit = 0

	if startdate > start_january:
		reporttrx = all_trx.filter(created__range=(start_january, startdate - datetime.timedelta(days=1)))
		report_ordres_debit = reporttrx.values("sens").annotate(amount=Sum('amount', output_field=IntegerField()))

		last_credit = 0
		last_debit = 0
		if report_ordres_debit:
			for i in report_ordres_debit:
				if i["sens"] == SENS_TRX.CREDIT: last_credit = i["amount"]
				if i["sens"] == SENS_TRX.DEBIT: last_debit = i["amount"]
	else:
		pass

	last_balance = last_balance + last_credit - last_debit

	credit = 0
	debit = 0
	if ordres_debit:
		for i in ordres_debit:
			if i["sens"] == SENS_TRX.CREDIT: credit = i["amount"]
			if i["sens"] == SENS_TRX.DEBIT: debit = i["amount"]

	solde = credit - debit

	start_date = "{:%d/%m/%Y}".format(startdate, )
	end_date = "{:%d/%m/%Y}".format(enddate, )

	table = TransactionOPTable(trx, request=request)
	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	context = {"lignes": lignes, "last_balance": last_balance, "cheques": cheques, "solde": solde, "debit": debit,
	           "credit": credit, "start_date": start_date, "end_date": end_date, "table": table,
	           'title': "Détails ordre de paiement N° {}".format(reference, ), "compte": compte, "trxs": trx,
	           "print_date": print_date, "annee_comptable": annee_comptable}
	return render(request, template, context)


# ReleveCompteForm
from datetime import timedelta


@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def genere_releve_compte_view(request, reference):
	template = "core/add_entity.html"
	user = request.user
	compte = get_object_or_404(CompteDepot, short_compte=reference)
	success_url = reverse_lazy('cddaccount:comptedepot_dash_view', kwargs={"pk": compte.id})

	upper_date = datetime.date.today()
	date_str = '01/01/2023'

	date_object = datetime.datetime.strptime(date_str, '%d/%m/%Y').date()
	lower_date = date_object  # datetime.datetime(upper_date.year, 1,1).date()

	rg = DateRange(lower_date, upper_date)

	if request.method == 'POST':
		form = ReleveCompteForm(request.POST)
		if form.is_valid():
			if request and not is_ajax(request.META):

				date_rg = form.cleaned_data['period']
				gestion = form.cleaned_data['gestion']
				typeinstance = form.cleaned_data['type']
				eninstance = False
				if typeinstance == TYPE_RELEVE.AVEC_INSTANCE: eninstance = True
				startdate, enddate = date_rg.lower, date_rg.upper
				success_url = reverse_lazy('cddaccount:releve_compte_view',
				                           kwargs={"reference": reference, "startdate": startdate, "enddate": enddate,
				                                   "gestion": gestion.id, "inst": eninstance.real
				                                   })

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		form = ReleveCompteForm(initial={"period": rg, "type": TYPE_RELEVE.SANS_INSTANCE})

	context = {"form": form, 'title': "Choisir la période", "compte": compte}
	return render(request, template, context)

@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def releve_compte_view(request, reference, startdate, enddate, gestion, inst):
	template = "cddaccount/releveinst_compte_new.html"
	user = request.user

	compte = get_object_or_404(CompteDepot, short_compte=reference)
	last_balance = 0

	if not compte.can_acces(user):
		raise Http404
	print_date = datetime.date.today()
	rg = DateRange(startdate.date(), startdate.date() + datetime.timedelta(days=1))

	an = AnneeComptable.objects.filter(period__contains=rg).last()
	if an:
		annee_comptable = startdate.year
	else:
		annee_comptable = print_date.year
	if an and an.id != gestion:
		messages.error(request, "Période n'est pas dans la gestion")
		success_url = reverse_lazy('cddaccount:comptedepot_list')
		return redirect(success_url)
	pcharges, trx, soldes = compute_all_balances_for_compte(compte, startdate=startdate, enddate=enddate,
	                                                        gestion=gestion, update=False, with_trx=True,for_releve=True)
	lignes = trx.count()
	lignes_inst = pcharges.count()


	cheques = trx.filter(payment_mean=PAYMENT_MEAN_TYPE.CHEQUE).count()


	previous__date = startdate - datetime.timedelta(days=1)
	previous__date = "{:%d/%m/%Y}".format(previous__date, )



	start_date = "{:%d/%m/%Y}".format(startdate, )
	end_date = "{:%d/%m/%Y}".format(enddate, )


	url_rb = reverse_lazy('cddaccount:genere_releve_compte', kwargs={"reference": compte.short_compte})

	date_imp = "{:%d/%m/%Y}".format(datetime.date.today(), )

	url_report_pdf = reverse_lazy('cddaccount:releve_compte_pdf_view',
	                              kwargs={"reference": compte.short_compte, "startdate": startdate, "enddate": enddate,
	                                      "gestion": gestion, "inst": inst})

	context = {"url_report_pdf": url_report_pdf, "date": date_imp, "previous__date": previous__date, "url_rb": url_rb,
	           "eninstance": inst, "pcharges": pcharges,
	           "lignes": lignes, "last_balance": int(last_balance), "cheques": cheques,  "start_date": start_date, "end_date": end_date,
	           'title': "Détails ordre de paiement N° {}".format(reference, ), "compte": compte, "trxs": trx,
	           "print_date": print_date, "annee_comptable": annee_comptable,"account_balance":soldes,"lignes_inst":lignes_inst}
	return render(request, template, context)






@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def releve_compte_view_deprecate(request, reference, startdate, enddate, gestion, inst):
	template = "cddaccount/releveinst_compte_new.html"
	user = request.user
	format = '%d-%m-%Y'
	compte = get_object_or_404(CompteDepot, short_compte=reference)
	last_balance = 0

	if not compte.can_acces(user):
		raise Http404
	print_date = datetime.date.today()
	# enddate= enddate+ datetime.timedelta(days=1)
	rg = DateRange(startdate.date(), startdate.date() + datetime.timedelta(days=1))
	rg = DateRange(startdate.date(), startdate.date() + datetime.timedelta(days=1))

	an = AnneeComptable.objects.filter(period__contains=rg).last()
	if an and an.id != gestion:
		messages.error(request, "Période n'est pas dans la gestion")
		success_url = reverse_lazy('cddaccount:comptedepot_list')
		return redirect(success_url)
	# an=AnneeComptable.objects.get(id=gestion)
	print_date_1 = an.period.lower

	start_january = datetime.datetime(print_date_1.year, 1, 1)
	end_decembre = datetime.datetime(print_date_1.year, 12, 31)
	last_january = datetime.datetime(print_date_1.year - 1, 1, 1)

	last_rg = DateRange(last_january.date(), last_january.date() + datetime.timedelta(days=1))

	previous_anne_comptable = AnneeComptable.objects.filter(period__contains=last_rg).last()

	if previous_anne_comptable:
		try:
			report = Report.objects.get(compte=compte, anne_comptable=previous_anne_comptable)
			last_balance = report.amount_fonc.amount + report.amount_invest.amount

		except Report.DoesNotExist:
			pass
	if an:
		annee_comptable = startdate.year
	else:
		annee_comptable = print_date.year

	# include_endate=enddate+datetime.timedelta(days=1)
	include_endate = enddate + datetime.timedelta(days=0)

	all_trx = Transaction.objects.filter(account_depot=reference, jour_comptable__annee_comptable__id=gestion,
	                                     jour_comptable__jour__range=(start_january, include_endate))

	trx = all_trx.filter(jour_comptable__jour__range=(startdate, include_endate))

	trx = trx.order_by('jour_comptable__jour', 'id')

	cheques = trx.filter(payment_mean=PAYMENT_MEAN_TYPE.CHEQUE).count()
	lignes = trx.count()
	canceleds_trx = trx.filter(transactionop__is_cancel_trx=True)
	none_canceleds_trx = trx.exclude(transactionop__is_cancel_trx=True)

	# ordres_debit = trx.values("sens").annotate(amount=Sum('amount', output_field=IntegerField()))

	canceleds_trx_debit = canceleds_trx.values("sens").annotate(amount=Sum('amount', output_field=IntegerField()))

	none_canceleds_trx_debit = none_canceleds_trx.values("sens").annotate(
		amount=Sum('amount', output_field=IntegerField()))

	last_credit = 0
	last_debit = 0
	previous__date = startdate - datetime.timedelta(days=1)
	previous__date = "{:%d/%m/%Y}".format(previous__date, )

	if startdate > start_january:
		reporttrx = all_trx.filter(jour_comptable__jour__range=(start_january, startdate - datetime.timedelta(days=1)))
		report_ordre_sens = reporttrx.values("sens").annotate(
			amount=Sum('amount', output_field=IntegerField()))
		last_credit = 0
		last_debit = 0
		if report_ordre_sens:
			for i in report_ordre_sens:
				if i["sens"] == SENS_TRX.CREDIT: last_credit = i["amount"]
				if i["sens"] == SENS_TRX.DEBIT: last_debit = i["amount"]

		'''  cats correction solde les annulations doivent être prises en compte sur les soldes
				report_canceleds_trx = reporttrx.filter(transactionop__is_cancel_trx=True)
				report_none_canceleds_trx = reporttrx.exclude(transactionop__is_cancel_trx=True)

				# report_ordres_debit = reporttrx.values("sens").annotate(amount=Sum('amount', output_field=IntegerField()))

				report_canceleds_debit = report_canceleds_trx.values("sens").annotate(
					amount=Sum('amount', output_field=IntegerField()))
				report_none_canceleds_debit = report_none_canceleds_trx.values("sens").annotate(
					amount=Sum('amount', output_field=IntegerField()))

				last_credit = 0
				last_debit = 0
				if report_none_canceleds_debit:
					for i in report_none_canceleds_debit:
						if i["sens"] == SENS_TRX.CREDIT: last_credit = i["amount"]
						if i["sens"] == SENS_TRX.DEBIT: last_debit = i["amount"]

				if report_canceleds_debit:
					rapport_c_debit = 0
					rapport_c_credit = 0
					for i in report_canceleds_debit:
						if i["sens"] == SENS_TRX.CREDIT: rapport_c_debit = i["amount"]
						if i["sens"] == SENS_TRX.DEBIT: rapport_c_credit = i["amount"]
					last_debit = last_debit - rapport_c_credit
			'''
	else:
		pass

	last_balance = last_balance + last_credit - last_debit

	credit = 0
	debit = 0
	if none_canceleds_trx_debit:
		for i in none_canceleds_trx_debit:
			if i["sens"] == SENS_TRX.CREDIT: credit = credit + i["amount"]
			if i["sens"] == SENS_TRX.DEBIT: debit = debit + i["amount"]

	if canceleds_trx_debit:
		c_debit = 0
		c_credit = 0
		for i in canceleds_trx_debit:
			if i["sens"] == SENS_TRX.CREDIT: c_credit = c_credit + i["amount"]
			if i["sens"] == SENS_TRX.DEBIT: c_debit = c_debit + i["amount"]

		debit = debit - c_credit

	credit = last_balance + credit

	solde = credit - debit

	start_date = "{:%d/%m/%Y}".format(startdate, )
	end_date = "{:%d/%m/%Y}".format(enddate, )
	disponible = 0
	t_pcharges = None
	pcharges = None
	url_rb = reverse_lazy('cddaccount:genere_releve_compte', kwargs={"reference": compte.short_compte})

	if inst == 1:
		objs = ReservationFond.objects.filter(ordre__compte__short_compte=reference, close=False,
		                                      ordre__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE,
		                                      created__range=(start_january, end_decembre)).select_related("ordre")

		t_pcharges = objs.aggregate(amount=Coalesce(Sum('reliquat', output_field=IntegerField()), Value(0)),
		                            nombre=Count('id', output_field=IntegerField()))
		pcharges = objs  # PrisEnchageOrdrePayment.objects.filter(ordre__compte__short_compte=reference,ordre__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE,created__range=(start_january, enddate)).select_related("ordre")#.values("compte__short_compte","reference","amount","created","object","sig_reference","nature__name")
		# t_pcharges=pcharges.aggregate(amount=Coalesce(Sum('amount', output_field=IntegerField()),Value(0)),nombre=Count('id', output_field=IntegerField()))
		if t_pcharges:
			disponible = solde - t_pcharges["amount"]
	date_imp = "{:%d/%m/%Y}".format(datetime.date.today(), )

	url_report_pdf = reverse_lazy('cddaccount:releve_compte_pdf_view',
	                              kwargs={"reference": compte.short_compte, "startdate": startdate, "enddate": enddate,
	                                      "gestion": gestion, "inst": inst})

	# url_rb=reverse_lazy('cddaccount:show_sit_instance_op_hs_form_view')

	context = {"url_report_pdf": url_report_pdf, "date": date_imp, "previous__date": previous__date, "url_rb": url_rb,
	           "eninstance": inst, "disponible": int(disponible), "t_pcharges": t_pcharges, "pcharges": pcharges,
	           "lignes": lignes, "last_balance": int(last_balance), "cheques": cheques, "solde": int(solde),
	           "debit": int(debit), "credit": int(credit), "start_date": start_date, "end_date": end_date,
	           'title': "Détails ordre de paiement N° {}".format(reference, ), "compte": compte, "trxs": trx,
	           "print_date": print_date, "annee_comptable": annee_comptable}
	return render(request, template, context)


@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def releve_compte_pdf_view(request, reference, startdate, enddate, gestion, inst):
	template = "cddaccount/releveinst_compte_new_pdf.html"
	user = request.user
	format = '%d-%m-%Y'
	compte = get_object_or_404(CompteDepot, short_compte=reference)
	last_balance = 0

	if not compte.can_acces(user):
		raise Http404
	print_date = datetime.date.today()
	rg = DateRange(startdate.date(), startdate.date() + datetime.timedelta(days=1))

	an = AnneeComptable.objects.filter(period__contains=rg).last()
	if an:
		annee_comptable = startdate.year
	else:
		annee_comptable = print_date.year
	if an and an.id != gestion:
		messages.error(request, "Période n'est pas dans la gestion")
		success_url = reverse_lazy('cddaccount:comptedepot_list')
		return redirect(success_url)
	# an=AnneeComptable.objects.get(id=gestion)
	print_date_1 = an.period.lower

	pcharges, trx, soldes = compute_all_balances_for_compte(compte, startdate=startdate, enddate=enddate,
	                                                        gestion=gestion, update=False, with_trx=True,with_cancel_trx=False,for_releve=True)
	lignes = trx.count()
	lignes_inst = pcharges.count()

	cheques = trx.filter(payment_mean=PAYMENT_MEAN_TYPE.CHEQUE).count()


	previous__date = startdate - datetime.timedelta(days=1)
	previous__date = "{:%d/%m/%Y}".format(previous__date, )



	start_date = "{:%d/%m/%Y}".format(startdate, )
	end_date = "{:%d/%m/%Y}".format(enddate, )
	url_rb = reverse_lazy('cddaccount:genere_releve_compte', kwargs={"reference": compte.short_compte})


	date_imp = "{:%d/%m/%Y}".format(datetime.date.today(), )

	context = {"user": user, "pagesize": "A4", "date": date_imp, "previous__date": previous__date, "url_rb": url_rb,
	           "eninstance": inst, "pcharges": pcharges,
	           "lignes": lignes, "last_balance": int(last_balance), "cheques": cheques,  "start_date": start_date, "end_date": end_date,
	           'title': "Détails ordre de paiement N° {}".format(reference, ), "compte": compte, "trxs": trx,
	           "print_date": print_date, "annee_comptable": annee_comptable,"account_balance":soldes,"lignes_inst":lignes_inst}
	gettemplate = get_template(template)
	html = gettemplate.render(context)
	result = BytesIO()
	from xhtml2pdf.config.httpconfig import httpConfig
	#httpConfig.save_keys('nosslcheck', True)

	pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
	if pdf.err:
		return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
	return HttpResponse(result.getvalue(), content_type='application/pdf')


@login_required()
def gerant_curent_releve(request):
	try:
		key = request.session["select_cddacc_user_id"]

		compte = CompteDepot.objects.get(id=key)
		return redirect(compte.get_current_month_releve())
	except:
		url_path = request.user.gerant_cd.get_absolute_url()
		return redirect(url_path)


@login_required()
def gerant_curent_detaillereleve(request):
	try:
		key = request.session["select_cddacc_user_id"]

		compte = CompteDepot.objects.get(id=key)
		return redirect(compte.get_current_full_releve())
	except:
		url_path = request.user.gerant_cd.get_absolute_url()
		return redirect(url_path)


@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def releve_compte_detaille_view(request, reference, startdate, enddate, gestion, inst):
	template = "cddaccount/relevedetaille_compte_new.html"
	user = request.user
	compte = get_object_or_404(CompteDepot, short_compte=reference)


	#enddate = enddate + datetime.timedelta(days=1)

	if not compte.can_acces(user):
		raise Http404
	print_date = datetime.date.today()
	an = AnneeComptable.objects.get(id=gestion)


	if an:
		annee_comptable = startdate.year
	else:
		annee_comptable = print_date.year
	last_year = annee_comptable - 1

	previous__date = startdate - datetime.timedelta(days=1)
	previous__date = "{:%d/%m/%Y}".format(previous__date, )



	start_date = "{:%d/%m/%Y}".format(startdate, )
	end_date = "{:%d/%m/%Y}".format(enddate, )
	disponible = None
	url_rb = reverse_lazy('cddaccount:genere_relevedetaille_compte_view', kwargs={"reference": compte.short_compte})



	pcharges,trx,soldes = compute_all_balances_for_compte(compte,startdate=startdate,enddate=enddate, gestion=gestion, update=False,with_trx=True,for_releve=True)
	lignes = trx.count()
	lignes_inst=pcharges.count()

	date_imp = "{:%d/%m/%Y}".format(datetime.date.today(), )

	context = {"previous__date": previous__date,
	           "last_year": last_year, "date": date_imp, "url_rb": url_rb, "eninstance": inst, "disponible": disponible, "pcharges": pcharges, "lignes": lignes,
	             "start_date": start_date,"lignes_inst":lignes_inst,
	           "end_date": end_date, 'title': "Détails ordre de paiement N° {}".format(reference, ), "compte": compte,
	           "trxs": trx, "print_date": print_date, "annee_comptable": annee_comptable,"account_balance":soldes}
	return render(request, template, context)






@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def releve_compte_detaille_view_deprecate(request, reference, startdate, enddate, gestion, inst):
	template = "cddaccount/relevedetaille_compte_new.html"
	user = request.user
	format = '%d-%m-%Y'
	compte = get_object_or_404(CompteDepot, short_compte=reference)
	last_balance = 0
	last_year = None
	fonct_anterieur = 0
	fonct_courant = 0
	invest_anterieur = 0
	invest_courant = 0
	last_balance_fonct = 0

	last_balance_invest = 0
	enddate = enddate + datetime.timedelta(days=1)

	if not compte.can_acces(user):
		raise Http404
	print_date = datetime.date.today()
	rg = DateRange(startdate.date(), startdate.date() + datetime.timedelta(days=1))
	an = AnneeComptable.objects.get(id=gestion)

	start_january = datetime.datetime(print_date.year, 1, 1)
	last_january = datetime.datetime(print_date.year - 1, 1, 1)

	last_rg = DateRange(last_january.date(), last_january.date() + datetime.timedelta(days=1))

	previous_anne_comptable = AnneeComptable.objects.filter(period__contains=last_rg).last()

	if previous_anne_comptable:
		try:
			report = ReportGestion.objects.get(compte=compte, anne_comptable=previous_anne_comptable)
			last_balance = report.amount_fonc.amount + report.amount_invest.amount
			last_balance_fonct = report.amount_fonc.amount
			last_balance_invest = report.amount_invest.amount

		except Report.DoesNotExist:
			pass

	if an:
		annee_comptable = startdate.year
	else:
		annee_comptable = print_date.year
	last_year = annee_comptable - 1

	all_trx = Transaction.objects.filter(account_depot=reference, created__range=(start_january, enddate))

	trx = all_trx.filter(created__range=(startdate, enddate))
	cheques = trx.filter(payment_mean=PAYMENT_MEAN_TYPE.CHEQUE).count()
	lignes = trx.count()
	ordres_debit = trx.values("sens", "type_nature").annotate(amount=Sum('amount', output_field=IntegerField()))

	last_credit = 0
	last_debit = 0
	last_credit_fonct = 0
	last_credit_invest = 0
	last_debit_fonct = 0
	last_debit_invest = 0

	previous__date = startdate - datetime.timedelta(days=1)
	previous__date = "{:%d/%m/%Y}".format(previous__date, )

	if startdate > start_january:
		reporttrx = all_trx.filter(created__range=(start_january, startdate - datetime.timedelta(days=1)))
		report_ordres_debit = reporttrx.values("sens", "type_nature").annotate(
			amount=Sum('amount', output_field=IntegerField()))

		if report_ordres_debit:
			for i in report_ordres_debit:
				if i["type_nature"] == NATURE_COMPTE.FONCTIONNEMENT:
					if i["sens"] == SENS_TRX.CREDIT: last_credit_fonct = i["amount"]
					if i["sens"] == SENS_TRX.DEBIT: last_debit_fonct = i["amount"]
				if i["type_nature"] == NATURE_COMPTE.INVESTISSEMENT:
					if i["sens"] == SENS_TRX.CREDIT: last_credit_invest = i["amount"]
					if i["sens"] == SENS_TRX.DEBIT: last_debit_invest = i["amount"]
	else:
		pass

	# slast_balance = last_balance + last_credit - last_debit

	last_balance_invest = last_balance_invest + last_credit_invest - last_debit_invest
	last_balance_fonct = last_balance_fonct + last_credit_fonct - last_debit_fonct

	last_balance = last_balance_invest + last_balance_fonct

	credit = 0
	debit = 0

	credit_invest = 0
	debit_invest = 0

	debit_fonct = 0
	credit_fonct = 0
	if ordres_debit:
		for i in ordres_debit:
			if i["type_nature"] == NATURE_COMPTE.FONCTIONNEMENT:
				if i["sens"] == SENS_TRX.CREDIT: credit_fonct = i["amount"]
				if i["sens"] == SENS_TRX.DEBIT: debit_fonct = i["amount"]
			if i["type_nature"] == NATURE_COMPTE.INVESTISSEMENT:
				if i["sens"] == SENS_TRX.CREDIT: credit_invest = i["amount"]
				if i["sens"] == SENS_TRX.DEBIT: debit_invest = i["amount"]

	credit_fonct = last_balance_fonct + credit_fonct
	credit_invest = last_balance_invest + credit_invest
	# debit=debit_fonct+debit_invest
	# sdebit = debit_fonct + debit_invest

	solde_fonct = credit_fonct - debit_fonct
	solde_invest = credit_invest - debit_invest

	solde = solde_fonct - solde_invest

	start_date = "{:%d/%m/%Y}".format(startdate, )
	end_date = "{:%d/%m/%Y}".format(enddate, )
	disponible = None
	t_pcharges = None
	pcharges = None
	url_rb = reverse_lazy('cddaccount:genere_relevedetaille_compte_view', kwargs={"reference": compte.short_compte})

	if inst == 1:
		objs = ReservationFond.objects.filter(ordre__compte__short_compte=reference, close=False,
		                                      ordre__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE,
		                                      ordre__date_prise_en_charge__range=(
		                                      start_january, enddate)).select_related("ordre")
		t_pcharges = objs.aggregate(amount=Coalesce(Sum('reliquat', output_field=IntegerField()), Value(0)),
		                            nombre=Count('id', output_field=IntegerField()))

		# objs=PrisEnchageOrdrePayment.objects.filter(ordre__compte__short_compte=reference,ordre__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE,created__range=(start_january, enddate)).select_related("ordre")
		# .values("compte__short_compte","reference","amount","created","object","sig_reference","nature__name")
		# t_pcharges=objs.aggregate(amount=Coalesce(Sum('amount', output_field=IntegerField()),Value(0)),nombre=Count('id', output_field=IntegerField()))
		if t_pcharges:
			disponible = solde - t_pcharges["amount"]

	date_imp = "{:%d/%m/%Y}".format(datetime.date.today(), )

	context = {"last_balance_fonct": last_balance_fonct, "last_balance_invest": last_balance_invest,
	           "solde_fonct": solde_fonct, "solde_invest": solde_invest, "debit_invest": debit_invest,
	           "credit_invest": credit_invest, "debit_fonct": debit_fonct, "credit_fonct": credit_fonct,
	           "previous__date": previous__date, "invest_anterieur": invest_anterieur, "invest_courant": invest_courant,
	           "fonct_courant": fonct_courant, "fonct_anterieur": fonct_anterieur,
	           "last_year": last_year, "date": date_imp, "url_rb": url_rb, "eninstance": inst, "disponible": disponible,
	           "t_pcharges": t_pcharges, "pcharges": pcharges, "lignes": lignes, "last_balance": last_balance,
	           "cheques": cheques, "solde": solde, "debit": debit, "credit": credit, "start_date": start_date,
	           "end_date": end_date, 'title': "Détails ordre de paiement N° {}".format(reference, ), "compte": compte,
	           "trxs": trx, "print_date": print_date, "annee_comptable": annee_comptable}
	return render(request, template, context)


# ReleveCompteForm
from datetime import timedelta


@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def genere_relevedetaille_compte_view(request, reference):
	template = "core/add_entity.html"
	user = request.user
	compte = get_object_or_404(CompteDepot, short_compte=reference)
	success_url = reverse_lazy('cddaccount:comptedepot_dash_view', kwargs={"pk": compte.id})

	upper_date = datetime.date.today()
	date_str = '01/01/2023'

	date_object = datetime.datetime.strptime(date_str, '%d/%m/%Y').date()
	lower_date = date_object  # datetime.datetime(upper_date.year, 1,1).date()

	rg = DateRange(lower_date, upper_date)

	if request.method == 'POST':
		form = ReleveCompteForm(request.POST)
		if form.is_valid():
			if request and not is_ajax(request.META):

				date_rg = form.cleaned_data['period']
				gestion = form.cleaned_data['gestion']
				# eninstance=form.cleaned_data['inst']
				typeinstance = form.cleaned_data['type']
				eninstance = False
				if typeinstance == TYPE_RELEVE.AVEC_INSTANCE: eninstance = True
				startdate, enddate = date_rg.lower, date_rg.upper
				success_url = reverse_lazy('cddaccount:releve_compte_detaille_view',
				                           kwargs={"reference": reference, "startdate": startdate, "enddate": enddate,
				                                   "gestion": gestion.id, "inst": eninstance.real
				                                   })

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		form = ReleveCompteForm(initial={"period": rg, "type": TYPE_RELEVE.SANS_INSTANCE})

	context = {"form": form, 'title': "Choisir la période", "compte": compte}
	return render(request, template, context)

