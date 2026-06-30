import datetime
import traceback

from bootstrap_modal_forms.utils import is_ajax
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django_tables2 import RequestConfig

from cddaccount import SENS_TRX, STATUT_ASTER
from cddaccount.models import ObsProjet, Projet, AvisDeDebit, AvisDeCredit, Depositaire, GestionCompteDepot, \
	TransactionOP, ReservationFond, CompteDepot, OrdrePayment, PrisEnchageOrdrePayment, VisaOrdrePayment, \
	ETAPE_ORDRE_PAYMENT, TYPE_REGLEMENT, STATUS_ORDRE_PAYMENT, get_or_create_journee_comptable, PAYMENT_MEAN_TYPE, \
	BlocageFond, AnnulationBlocageFond, VirementDetails
from helpers.decorators import user_role_required
from helpers.models import Role, SimpleOtp

PAGINATION_SIZE = 100

default_currency = "F CFA"
# import generic UpdateView

from cddaccount.forms import DemandeBlocagefondForm, AvisDeDebitForm, ProjetForm, AvisDeCreditForm, \
	PrisEnchageOrdrePaymentModalForm, DefaultSaisieOrdrePaymentModelForm, DepositaireModelForm, MakeTrxPaymentForm, \
	AcceptationOrdrePayementForm, OtpValidationOrdrePaymentForm, SaisieOrdrePaymentModelForm, VisaOrdrePaymentModelForm, \
	UpdateOrdrePaymentModelForm, PriseEnChargeOrdrePaymentModelForm, JourneeComptableForm,OrdrePaymentByBlocageFondModelForm,SimpleOPForm

from cddaccount.tables import AnnulationBlocageFondTable, AnnulationBlocageFondFilter, ProjetTable, ProjetFilter, \
	AvisDeCreditFilter, AvisDeDebitFilter, AvisDeCreditTable, AvisDeDebitTable, DepositaireTable, DepositaireFilter, \
	TransactionOPTable, OrdrePaymentFilter, OrdrePaymentTable, ASCDOrdrePaymentTable, GerantCDOrdrePaymentTable, \
	AgentPCOrdrePaymentTable, OperationViseTable, OperationViseFilter, VirementDetailsFilter, VirementDetailsTable


def get_comptes(request):
	try:
		key= request.session["select_cddacc_user_id"]
		return CompteDepot.objects.filter(id=int(key))
	except KeyError:
		return CompteDepot.objects.by_agent(request.user)




@login_required
@permission_required("cddaccount.view_ordrepayment")
def nouveaux_op_list_view(request):
	etape=ETAPE_ORDRE_PAYMENT.SAISIE
	return base_ordrepayment_list_view(request, None,etape)

@login_required
@permission_required("cddaccount.view_ordrepayment",raise_exception=True)
def valides_op_list_view(request):
	etape=ETAPE_ORDRE_PAYMENT.VALIDE
	return base_ordrepayment_list_view(request, None,etape)

@login_required
@permission_required("cddaccount.view_ordrepayment",raise_exception=True)
def accepter_op_list_view(request):
	etape=ETAPE_ORDRE_PAYMENT.ACCEPTE or ETAPE_ORDRE_PAYMENT.REJETE
	return base_ordrepayment_list_view(request, None,etape)

@login_required
@permission_required("cddaccount.view_prisenchageordrepayment",raise_exception=True)
def priseencharge_op_list_view(request):
	etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE
	return base_ordrepayment_list_view(request, None,etape)

@login_required
@permission_required("cddaccount.view_visaordrepayment",raise_exception=True)
def visa_op_list_view(request):
	etape=ETAPE_ORDRE_PAYMENT.VISA
	return base_ordrepayment_list_view(request, None,etape)




@login_required
def nouveaux_virements_list_view(request):
	paymentmean=PAYMENT_MEAN_TYPE.VIREMENT
	etape=ETAPE_ORDRE_PAYMENT.SAISIE
	return base_ordrepayment_list_view(request, paymentmean,etape)

@login_required
def valides_virements_list_view(request):
	paymentmean=PAYMENT_MEAN_TYPE.VIREMENT
	etape=ETAPE_ORDRE_PAYMENT.VALIDE
	return base_ordrepayment_list_view(request, paymentmean,etape)

@login_required
def accepter_virements_list_view(request):
	paymentmean=PAYMENT_MEAN_TYPE.VIREMENT
	etape=ETAPE_ORDRE_PAYMENT.ACCEPTE
	return base_ordrepayment_list_view(request, paymentmean,etape)

@login_required
@permission_required("cddaccount.view_prisenchageordrepayment",raise_exception=True)
def priseencharge_virements_list_view(request):
	paymentmean=PAYMENT_MEAN_TYPE.VIREMENT
	etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE
	return base_ordrepayment_list_view(request, paymentmean,etape)

@login_required
@permission_required("cddaccount.view_visaordrepayment",raise_exception=True)
def visa_virements_list_view(request):
	paymentmean=PAYMENT_MEAN_TYPE.VIREMENT
	etape=ETAPE_ORDRE_PAYMENT.VISA
	return base_ordrepayment_list_view(request, paymentmean,etape)

@login_required
def nouveaux_opcheques_list_view(request):
	paymentmean=PAYMENT_MEAN_TYPE.CHEQUE
	etape=ETAPE_ORDRE_PAYMENT.SAISIE
	return base_ordrepayment_list_view(request, paymentmean,etape)

@login_required
def valides_opcheques_list_view(request):
	paymentmean=PAYMENT_MEAN_TYPE.CHEQUE
	etape=ETAPE_ORDRE_PAYMENT.VALIDE
	return base_ordrepayment_list_view(request, paymentmean,etape)

@login_required
def accepter_opcheques_list_view(request):
	paymentmean=PAYMENT_MEAN_TYPE.CHEQUE
	etape=ETAPE_ORDRE_PAYMENT.ACCEPTE
	return base_ordrepayment_list_view(request, paymentmean,etape)

@login_required
def priseencharge_opcheques_list_view(request):
	paymentmean=PAYMENT_MEAN_TYPE.CHEQUE
	etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE
	return base_ordrepayment_list_view(request, paymentmean,etape)

@login_required
@permission_required("bankcheck.receptionner_cheque",raise_exception=True)
def visa_opcheques_list_view(request):
	paymentmean=PAYMENT_MEAN_TYPE.CHEQUE
	etape=ETAPE_ORDRE_PAYMENT.VISA
	return base_ordrepayment_list_view(request, paymentmean,etape)




def get_titles(paymentmean,etape):
	if paymentmean is  None : return get_titles_without_payment(etape)
	if paymentmean == PAYMENT_MEAN_TYPE.VIREMENT and etape == ETAPE_ORDRE_PAYMENT.SAISIE:
		title = _("LISTE DES NOUVEAUX VIREMENTS")
		data_title = _("NOUVEAUX VIREMENTS")
		action_title = "Saisir un virement"
	if paymentmean == PAYMENT_MEAN_TYPE.VIREMENT and etape == ETAPE_ORDRE_PAYMENT.VALIDE:
		title = _("VIREMENTS A RÉCEPTIONNER")
		data_title = _("VIREMENTS A RÉCEPTIONNER")
		action_title = "Saisir un virement"
	if paymentmean == PAYMENT_MEAN_TYPE.VIREMENT and etape == ETAPE_ORDRE_PAYMENT.ACCEPTE:
		title = _("VIREMENTS A PRENDRE EN CHARGE ")
		data_title = _("VIREMENTS A PRENDRE EN CHARGE")
		action_title = "Saisir un virement"

	if paymentmean == PAYMENT_MEAN_TYPE.VIREMENT and etape == ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE:
		title = _("VIREMENTS A VISER")
		data_title = _("VIREMENTS A VISER")
		action_title = "Saisir un virement"

	if paymentmean == PAYMENT_MEAN_TYPE.VIREMENT and etape == ETAPE_ORDRE_PAYMENT.VISA:
		title = _("VIREMENTS VISES")
		data_title = _("VIREMENTS VISÉS")
		action_title = "Saisir un virement"
	if paymentmean == PAYMENT_MEAN_TYPE.CHEQUE and etape == ETAPE_ORDRE_PAYMENT.SAISIE:
		title = _("LISTE DES NOUVEAUX VIREMENTS")
		data_title = _("NOUVEAUX VIREMENTS")
		action_title = "Saisir un chèque"
	if paymentmean == PAYMENT_MEAN_TYPE.CHEQUE and etape == ETAPE_ORDRE_PAYMENT.VALIDE:
		title = _("CHÈQUES A RÉCEPTIONNER ")
		data_title = _("CHÈQUES A RÉCEPTIONNER")
		action_title = "Saisir un chèque"
	if paymentmean == PAYMENT_MEAN_TYPE.CHEQUE and etape == ETAPE_ORDRE_PAYMENT.ACCEPTE:
		title = _("CHÈQUES A PRENDRE EN CHARGE")
		data_title = _("CHÈQUES A PRENDRE EN CHARGE")
		action_title = "Saisir un chèque"

	if paymentmean == PAYMENT_MEAN_TYPE.CHEQUE and etape == ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE:
		title = _("CHÈQUES A VISER")
		data_title = _("CHÈQUES A VISER")
		action_title = "Saisir un chèque"

	if paymentmean == PAYMENT_MEAN_TYPE.CHEQUE and etape == ETAPE_ORDRE_PAYMENT.VISA:
		title = _("CHÈQUES A RETIRER")
		data_title = _("CHÈQUES A RETIRER")
		action_title = "Saisir un chèque"

	return (title,data_title,action_title)


def get_titles_without_payment(etape):
	if  etape == ETAPE_ORDRE_PAYMENT.SAISIE:
		title = _("LISTE DES NOUVELLES OPÉRATIONS")
		data_title = _("NOUVELLES OPÉRATIONS")
		action_title = "Saisir une opération"
	if  etape == ETAPE_ORDRE_PAYMENT.VALIDE:
		title = _("OPÉRATIONS A RÉCEPTIONNER")
		data_title = _("OPÉRATIONS A RÉCEPTIONNER")
		action_title = "Saisir une opération"
	if etape == ETAPE_ORDRE_PAYMENT.ACCEPTE:
		title = _("OPÉRATIONS A PRENDRE EN CHARGE")
		data_title = _("OPÉRATIONS A PRENDRE EN CHARGE")
		action_title = "Saisir une opération"

	if  etape == ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE:
		title = _("OPÉRATIONS A VISER")
		data_title = _("OPÉRATIONS A VISER")
		action_title = "Saisir une opération"

	if  etape == ETAPE_ORDRE_PAYMENT.VISA:
		title = _("OPÉRATIONS VISÉES")
		data_title = _("OPÉRATIONS VISÉES")
		action_title = "Saisir une opération"


	return (title,data_title,action_title)



@login_required
# @user_role_required("ADMIN")
def base_ordrepayment_list_view(request,paymentmean,etape):
	user = request.user
	create_url=None
	template_name = "cddaccount/ordres_payements_new.html"
	if request.htmx:
		template_name = "datatables/table_only.html"

	excludes=["status","payment_mean","reliquat"]
	gen_template_vrm = reverse_lazy('cddaccount:generate_template_vrm')
	prefetchcls=("secteur","compte","nature","creator","jour_comptable","typecompte","prise_en_charge","annulation_op","prise_en_charge__visa")
	if paymentmean is None:
		queryset = OrdrePayment.objects.by_agent(user).filter(etape=etape,annulation_op=None).prefetch_related("secteur","compte","nature","creator","jour_comptable","typecompte","prise_en_charge","annulation_op","prise_en_charge__visa")
	else: queryset = OrdrePayment.objects.by_agent(user).filter(payment_mean=paymentmean,etape=etape,annulation_op=None).prefetch_related("secteur","compte","nature","creator","jour_comptable","typecompte","prise_en_charge","annulation_op","prise_en_charge__visa")

	if etape==ETAPE_ORDRE_PAYMENT.VISA:
		queryset=queryset.filter(cheque_delivred=False)
	if etape==ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE:
		excludes = ["status", "payment_mean","blocage"]

	if paymentmean==PAYMENT_MEAN_TYPE.CHEQUE:
		if etape == ETAPE_ORDRE_PAYMENT.VISA:
			queryset = queryset.filter(prise_en_charge__visa__payment_mean=PAYMENT_MEAN_TYPE.CHEQUE)
		excludes.append("template")

	queryset_filter = OrdrePaymentFilter(request.GET, request=request, queryset=queryset)
	can_create_dcp = user.has_perm('cddaccount.add_ordrepayment')
	if can_create_dcp:
		create_url = reverse_lazy('cddaccount:create_ordrepayment_default')
		if paymentmean==PAYMENT_MEAN_TYPE.VIREMENT:
			create_url="{}?type=v".format(create_url,)
		if paymentmean==PAYMENT_MEAN_TYPE.CHEQUE:
			create_url="{}?type=c".format(create_url,)
	# onajoute la selection pour les cheque a retire ou les saisie
	if etape==ETAPE_ORDRE_PAYMENT.SAISIE or (etape == ETAPE_ORDRE_PAYMENT.VISA and paymentmean==PAYMENT_MEAN_TYPE.CHEQUE):
	    pass
	else:
		excludes.append("selection")
	if etape == ETAPE_ORDRE_PAYMENT.VISA and paymentmean == PAYMENT_MEAN_TYPE.CHEQUE:
		template_name = "cddaccount/cheques_vises.html"




	if hasattr(user,Role.AGENT_SAISIE_CD.lower()):
		table=ASCDOrdrePaymentTable(queryset_filter.qs, request=request,exclude=excludes.append("creator"))
	elif hasattr(user, "gerant_cd"):

		excludes.append("matricule")
		excludes.append("gerant")
		table = GerantCDOrdrePaymentTable(queryset_filter.qs, request=request,exclude=excludes)

	elif hasattr(user, "agent_postecomptable"):
		excludes.append("matricule")
		excludes.append("creator")
		table = AgentPCOrdrePaymentTable(queryset_filter.qs.exclude(etape=ETAPE_ORDRE_PAYMENT.SAISIE), request=request, exclude=excludes)

	else:table = OrdrePaymentTable(queryset_filter.qs, request=request,exclude=excludes)
	title,data_title,action_title = get_titles(paymentmean,etape)


	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, template_name,
	              {"gen_template_vrm":gen_template_vrm,"create_url": create_url, "can_create_op": can_create_dcp, "data_title": data_title,"action_title":action_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})


def inoice_view(request):
	return render(request, 'cddaccount/recu_op.html',{})

from bootstrap_modal_forms.generic import (
    BSModalLoginView
)
from cddaccount.forms import CustomAuthenticationForm
class CustomLoginView(BSModalLoginView):
    authentication_form = CustomAuthenticationForm
    template_name = 'cddaccount/login.html'
    success_message = 'Success: You were successfully logged in.'
    success_url = reverse_lazy('index')


@login_required
# @user_role_required("ADMIN")
def default_ordrepayment_effective_list_view(request, paymentmean):
	user = request.user
	create_url = None
	excludes = ["action", "selection"]
	title = _("LISTE DES OPÉRATIONS CHÈQUES")
	data_title = _("LISTE DES OPÉRATIONS CHÈQUES")
	if paymentmean is None:
		queryset = OrdrePayment.objects.by_agent(user)
	else:
		queryset = OrdrePayment.objects.by_agent(user).filter(payment_mean=paymentmean)
	if paymentmean != PAYMENT_MEAN_TYPE.CHEQUE:
		excludes.append("cheque")
		title = _("LISTE DES OPÉRATIONS VIREMENTS ")
		data_title = _("LISTE DES OPÉRATIONS VIREMENTS ")
	queryset_filter = OrdrePaymentFilter(request.GET, request=request, queryset=queryset)
	can_create_dcp = user.has_perm('cddaccount.add_ordrepayment')
	if can_create_dcp:
		create_url = reverse_lazy('cddaccount:create_ordrepayment_default')

	if hasattr(user, Role.AGENT_SAISIE_CD.lower()):

		excludes.append("crator")
		table = ASCDOrdrePaymentTable(queryset_filter.qs, request=request, exclude=excludes)
	elif hasattr(user, "gerant_cd"):
		excludes.append("gerant")
		excludes.append("matricule")
		table = GerantCDOrdrePaymentTable(queryset_filter.qs, request=request, exclude=excludes)

	elif hasattr(user, "agent_postecomptable"):
		excludes.append("matricule")
		excludes.append("creator")
		table = AgentPCOrdrePaymentTable(queryset_filter.qs.exclude(etape=ETAPE_ORDRE_PAYMENT.SAISIE), request=request,
		                                 exclude=excludes)

	else:
		table = OrdrePaymentTable(queryset_filter.qs, request=request, exclude=excludes)



	template_name='core/default_list.html'

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, template_name,
	              {"create_url": create_url, "can_create_op": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})


@login_required
# @user_role_required("ADMIN")
def consulter_op_list_view(request):
	user = request.user
	create_url = None
	excludes = ["action", "selection","status","created","observations"]
	title = _("LISTE DES OPÉRATIONS ")
	data_title = _("LISTE DES OPÉRATIONS ")
	queryset = OrdrePayment.objects.by_agent(user).filter(annulation_op__isnull=True).prefetch_related("reservationfond","secteur","compte","nature","creator","jour_comptable","typecompte","prise_en_charge","prise_en_charge__visa").select_related("creator","gerant","compte").order_by('-created')
	if hasattr(user, "gerant_cd"):
		try:
			key= request.session["select_cddacc_user_id"]
			queryset=queryset.filter(compte_id=int(key))
		except KeyError:
			pass

	queryset_filter = OrdrePaymentFilter(request.GET, request=request, queryset=queryset)
	can_create_dcp = user.has_perm('cddaccount.add_ordrepayment')
	if can_create_dcp:
		create_url = reverse_lazy('cddaccount:create_ordrepayment_default')


	"""
	if hasattr(user, Role.AGENT_SAISIE_CD.lower()):

		excludes.append("creator")
		table = ASCDOrdrePaymentTable(queryset_filter.qs, request=request, exclude=excludes)
	elif hasattr(user, "gerant_cd"):
		excludes.append("gerant")
		excludes.append("matricule")
		table = GerantCDOrdrePaymentTable(queryset_filter.qs, request=request, exclude=excludes)

	elif hasattr(user, "agent_postecomptable"):
		excludes.append("matricule")
		excludes.append("creator")
		table = AgentPCOrdrePaymentTable(queryset_filter.qs.exclude(etape=ETAPE_ORDRE_PAYMENT.SAISIE), request=request,
		                                 exclude=excludes)

	else:
		table = OrdrePaymentTable(queryset_filter.qs, request=request, exclude=excludes)
	"""
	table = OrdrePaymentTable(queryset_filter.qs, request=request, exclude=excludes)

	template_name = "cddaccount/ordres_payements_new.html"
	if request.htmx:
		template_name = "datatables/table_only.html"

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, template_name,
	              {"create_url": create_url,  "can_create_op": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})







@login_required
# @user_role_required("ADMIN")
@permission_required("cddaccount.view_visaordrepayment",raise_exception=True)
def op_dejavises_list_view(request):
	user = request.user
	create_url=None
	template_name = 'cddaccount/list_opvises.html'
	if request.htmx:
		template_name = "datatables/table_only.html"

	gen_template_vrm = reverse_lazy('cddaccount:generate_template_vrm')
	queryset = TransactionOP.objects.by_agent(user).filter(sens=SENS_TRX.DEBIT,status_aster=STATUT_ASTER.ENCOURS,has_cancel=False).prefetch_related("typecompte")

	excludes = ["action"]

	queryset_filter = OperationViseFilter(request.GET, request=request, queryset=queryset)
	can_create_dcp = user.has_perm('cddaccount.add_ordrepayment')
	if hasattr(user, "agent_postecomptable"):
		table = OperationViseTable(queryset_filter.qs, request=request)

	else:table = OperationViseTable(queryset_filter.qs, request=request,exclude=excludes)
	title,data_title,action_title = ("OPÉRATIONS VISÉES","OPÉRATIONS VISÉES" ,"")


	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, template_name,
	              {"gen_template_vrm":gen_template_vrm,"create_url": create_url, "can_create_op": False, "data_title": data_title,"action_title":action_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})





@login_required
# @user_role_required("ADMIN")
def details_vire_list_view(request):
	user = request.user
	create_url=None
	template_name = 'core/default_list.html'
	#if request.htmx:
	#	template_name = "datatables/table_only.html"

	gen_template_vrm = reverse_lazy('cddaccount:generate_template_vrm')
	queryset = VirementDetails.objects.by_agent(user).exclude(payment_mean=PAYMENT_MEAN_TYPE.MOBILE)

	queryset_filter = VirementDetailsFilter(request.GET, request=request, queryset=queryset)
	can_create_dcp = False
	table = VirementDetailsTable(queryset_filter.qs, request=request,exclude=("wallet_provider","wallet_number","cin","dob","lieu_dob","firstname","lastname"))
	title,data_title,action_title = ("DÉTAILS VIREMENTS","DÉTAILS VIREMENTS" ,"")


	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, template_name,
	              {"gen_template_vrm":gen_template_vrm,"create_url": create_url, "can_create_op": False, "data_title": data_title,"action_title":action_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})



@login_required
# @user_role_required("ADMIN")
def mobile_details_vire_list_view(request):
	user = request.user
	create_url=None
	template_name = 'core/default_list.html'
	#if request.htmx:
	#	template_name = "datatables/table_only.html"

	gen_template_vrm = reverse_lazy('cddaccount:generate_template_vrm')
	queryset = VirementDetails.objects.by_agent(user).filter(payment_mean=PAYMENT_MEAN_TYPE.MOBILE)

	queryset_filter = VirementDetailsFilter(request.GET, request=request, queryset=queryset)
	can_create_dcp = False
	table = VirementDetailsTable(queryset_filter.qs, request=request,exclude=('beneficiaire','iban_benef'))
	title,data_title,action_title = ("DÉTAILS VIREMENTS MOBILE","DÉTAILS VIREMENTS MOBILE" ,"")


	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, template_name,
	              {"gen_template_vrm":gen_template_vrm,"create_url": create_url, "can_create_op": False, "data_title": data_title,"action_title":action_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})
