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

from cddaccount.models import ObsProjet, Projet, AvisDeDebit, AvisDeCredit, Depositaire, GestionCompteDepot, \
	TransactionOP, ReservationFond, CompteDepot, OrdrePayment, PrisEnchageOrdrePayment, VisaOrdrePayment, \
	ETAPE_ORDRE_PAYMENT, TYPE_REGLEMENT, STATUS_ORDRE_PAYMENT, get_or_create_journee_comptable, PAYMENT_MEAN_TYPE, \
	BlocageFond, AnnulationBlocageFond, VirementMasse
from helpers.decorators import user_role_required
from helpers.models import Role, SimpleOtp

PAGINATION_SIZE = 5

default_currency = "F CFA"
# import generic UpdateView

from cddaccount.forms import DemandeBlocagefondForm, AvisDeDebitForm, ProjetForm, AvisDeCreditForm, \
	PrisEnchageOrdrePaymentModalForm, DefaultSaisieOrdrePaymentModelForm, DepositaireModelForm, MakeTrxPaymentForm, \
	AcceptationOrdrePayementForm, OtpValidationOrdrePaymentForm, SaisieOrdrePaymentModelForm, VisaOrdrePaymentModelForm, \
	UpdateOrdrePaymentModelForm, PriseEnChargeOrdrePaymentModelForm, JourneeComptableForm,OrdrePaymentByBlocageFondModelForm,SimpleOPForm

from cddaccount.tables import AnnulationBlocageFondTable,AnnulationBlocageFondFilter, ProjetTable,ProjetFilter, AvisDeCreditFilter,AvisDeDebitFilter,AvisDeCreditTable,AvisDeDebitTable, DepositaireTable,DepositaireFilter,TransactionOPTable,OrdrePaymentFilter,OrdrePaymentTable,ASCDOrdrePaymentTable,GerantCDOrdrePaymentTable,AgentPCOrdrePaymentTable


@login_required
def nouveaux_virmasse_list_view(request):
	etape=ETAPE_ORDRE_PAYMENT.SAISIE
	return base_virementmasse_view(request,etape)

@login_required
def valides_virmasse_list_view(request):
	etape=ETAPE_ORDRE_PAYMENT.VALIDE
	return base_virementmasse_view(request,etape)

@login_required
def accepter_virmasse_list_view(request):
	etape=ETAPE_ORDRE_PAYMENT.ACCEPTE
	return base_virementmasse_view(request,etape)

@login_required
def priseencharge_virmasse_list_view(request):
	etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE
	return base_virementmasse_view(request,etape)

@login_required
def visa_virmasse_list_view(request):
	etape=ETAPE_ORDRE_PAYMENT.VISA
	return base_virementmasse_view(request,etape)



def get_titles(etape):
	if  etape == ETAPE_ORDRE_PAYMENT.SAISIE:
		title = _("LISTE DES NOUVEAUX VIREMENTS MASSE")
		data_title = _("NOUVEAUX VIREMENTS MASSE")
		action_title = "Saisie Virement Masse"
	if etape == ETAPE_ORDRE_PAYMENT.VALIDE:
		title = _("VIREMENTS MASSE A RECEPTIONNER")
		data_title = _("VIREMENTS MASSE A RECEPTIONNER")
		action_title = "Saisie Virement Masse"
	if  etape == ETAPE_ORDRE_PAYMENT.ACCEPTE:
		title = _("VIREMENTS MASSE A PRENDRE EN CHARGE ")
		data_title = _("VIREMENTS MASSE A PRENDRE EN CHARGE")
		action_title = "Saisie Virement Masse"

	if  etape == ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE:
		title = _("VIREMENTS MASSE A VISER")
		data_title = _("VIREMENTS MASSE A VISER")
		action_title = "Saisie Virement Masse"

	if  etape == ETAPE_ORDRE_PAYMENT.VISA:
		title = _("VIREMENTS MASSE VISES")
		data_title = _("VIREMENTS MASSE VISES")
		action_title = "Saisie Virement Masse"


	return (title,data_title,action_title)





@login_required
# @user_role_required("ADMIN")
def base_virementmasse_view(request,etape):
	user = request.user
	create_url=None
	template_name = "cddaccount/ordres_payements_new.html"
	if request.htmx:
		template_name = "datatables/table_only.html"

	excludes=["status","payment_mean"]
	queryset = VirementMasse.objects.by_agent(user).filter(etape=etape,annulation_op=None)

	if etape==ETAPE_ORDRE_PAYMENT.VISA:
		queryset=queryset.filter(cheque_delivred=False)

	queryset_filter = OrdrePaymentFilter(request.GET, request=request, queryset=queryset)
	can_create_dcp = user.has_perm('cddaccount.add_virementmasse')
	gen_template_vrm=reverse_lazy('cddaccount:generate_template_vrm')
	if can_create_dcp:
		create_url = reverse_lazy('cddaccount:create_virementmasse_default')

	if etape!=ETAPE_ORDRE_PAYMENT.SAISIE:
	    excludes.append("selection")

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
	title,data_title,action_title = get_titles(etape)


	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, template_name,
	              {"gen_template_vrm":gen_template_vrm,"create_url": create_url, "can_create_op": can_create_dcp, "data_title": data_title,"action_title":action_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})





