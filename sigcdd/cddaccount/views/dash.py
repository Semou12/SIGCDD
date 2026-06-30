import datetime

from bootstrap_modal_forms.utils import is_ajax
from django.contrib.auth.base_user import BaseUserManager
from django_tables2 import RequestConfig
from django.shortcuts import render
from django.urls import reverse_lazy

from bankcheck.models import Chequier
from cddaccount.models import GestionCompteDepot, AgentSaisieCD, ValidationCompte, CompteDepot, Bank, CodeAgence, \
	GerantCD, create_gerant_affectation, OrdrePayment, BlocageFond, AvisDeCredit, AvisDeDebit, Report, AnneeComptable, \
	compute_all_balances_for_compte, ReportGestion
from users.models import User
from cddaccount.tables import GerantCDOrdrePaymentTable, ASCDOrdrePaymentTable,OrdrePaymentFilter,OrdrePaymentTable,GestionCompteDepotTable, GestionCompteDepotFilter, AgentSaisieCDTable, \
	AgentSaisieCDFilter, GerantCDTable, GerantCDFilter, CompteDepotFilter, CompteDepotTable, BankTable, BankFilter, \
	CodeAgenceTable, CodeAgenceFilter
from django.contrib.auth.decorators import login_required, permission_required
from helpers.decorators import user_role_required, user_change_pwd_required
from django.utils.decorators import method_decorator
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _
from helpers.models import Role
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse, Http404
from psycopg2.extras import DateRange
from cddaccount import NATURE_COMPTE, NATURE_FONDS, STATUS_CREATION
from django.db.models import Sum, Avg, Count, IntegerField,F, Value,ExpressionWrapper,CharField
from django.contrib import messages

from django.db.models.functions import Coalesce

PAGINATION_SIZE = 100

default_currency = "F CFA"
# import generic UpdateView
from django.views.generic.edit import DeleteView

from cddaccount.forms import AgentSaisieCDForm, ValidationAgentSaisieCDForm, AgentSaisieCDModelForm, \
	ValidationGerantCDForm, ValidationCompteForm, CompteDepotModelForm, BankForm, CodeAgenceForm, GerantCDModelForm, \
	CompleteGerantCDForm
# Relative import of GeeksModel
from bootstrap_modal_forms.generic import (
	BSModalLoginView,
	BSModalFormView, BSModalDeleteView,
	BSModalCreateView, BSModalUpdateView
)

def get_comptes(request):
	try:
		key= request.session["select_cddacc_user_id"]
		return CompteDepot.objects.filter(id=int(key))
	except KeyError:
		return CompteDepot.objects.by_agent(request.user)



@login_required
# @user_role_required("ADMIN")
def comptedepot_dash_view(request, pk):
	user=request.user
	compte = get_object_or_404(CompteDepot, id=pk)
	if not compte.can_acces(user):
		raise Http404

	make_saisie_url=reverse_lazy('cddaccount:create_ordrepayment',kwargs={"pk":pk})
	can_make_saisie=user.has_perm('cddaccount.add_ordrepayment') and compte.balance.amount>=0
	gerant=None
	gestion_compte = GestionCompteDepot.objects.filter(actif=True,compte=compte).last()

	can_create_structure=user.has_perm('core.add_structure')
	create_structure_url=None
	if can_create_structure:
		if compte.structure :
			create_structure_url = reverse_lazy('core:update_structure',kwargs={"pk":compte.structure.pk})
		else:create_structure_url = reverse_lazy('core:create_structure')

	gestionEnCours = AnneeComptable.current_gestion()
	if not gestionEnCours:
		messages.info(request, "Annee comptable non encore ouvert")
		return Http404

	date_du_jour = datetime.datetime.now()

	details__solde = compute_all_balances_for_compte(compte, gestion=gestionEnCours.id,update=False)

	balance= details__solde["balance"]
	balance_invest = details__solde["invest_balance"]["solde"]
	balance_fonct = details__solde["fonct_balance"]["solde"]

	blocages=BlocageFond.objects.filter(compte_id=pk).aggregate(
		solde=Sum('balance', output_field=IntegerField()),
		amount=Sum('amount', output_field=IntegerField()),
		items=Count('id', output_field=IntegerField()))
	ordres_debit = AvisDeDebit.objects.filter(compte_id=pk,date_avis__year=gestionEnCours.year()).aggregate(
		amount=Sum('amount', output_field=IntegerField()),
		items=Count('id', output_field=IntegerField()))
	ordres_credit = AvisDeCredit.objects.filter(compte_id=pk,date_avis__year=gestionEnCours.year()).aggregate(
		amount=Sum('amount', output_field=IntegerField()),
		items=Count('id', output_field=IntegerField()))
	fonds_bloque=blocages
	#ordres_debit={"amount":0,"items":0}
	#ordres_credit = {"amount": 0, "items": 0}
	change_gerant_url= None  #reverse_lazy('cddaccount:update_gestioncomptedepot',kwargs={"pk":gestion_compte.pk})
	url_rb=reverse_lazy('cddaccount:genere_releve_compte',kwargs={"reference":compte.short_compte})
	url_rb_detaille=reverse_lazy('cddaccount:genere_relevedetaille_compte_view',kwargs={"reference":compte.short_compte})
	if gestion_compte:
		change_gerant_url = reverse_lazy('cddaccount:update_gestioncomptedepot', kwargs={"pk": gestion_compte.pk})
		gerant=gestion_compte.gerant
	title = "Compte Dépot {} ({})".format(compte.short_compte,compte.libelle_court)

	context = {"url_rb_detaille":url_rb_detaille,"can_create_structure":can_create_structure,"create_structure_url":create_structure_url,"balance_invest":balance_invest,"balance_fonct":balance_fonct,"change_gerant_url":change_gerant_url,"url_rb":url_rb,"can_make_saisie":can_make_saisie,"make_saisie_url":make_saisie_url,"balance":balance,"fonds_bloques":fonds_bloque,"currency": default_currency, "compte":compte,"title":title,"agent":gerant,"ordres_credit":ordres_credit,"ordres_debit":ordres_debit}
	return render(request, 'cddaccount/comptedepot_dash.html', context)






@login_required
#@user_role_required(Role.GERANT)
# @user_role_required("ADMIN")
def simple_gerantcd_profile_view(request, matricule):
	user = request.user
	gerant = GerantCD.objects.get(matricule=matricule)
	if not gerant.can_acces(user):raise Http404
	if gerant.status == STATUS_CREATION.NOUVEAU:
		messages.success(request, "Ce gérant n'est pas encore actif car le propriétaire n'a pas encore renseigné les infos")
		return redirect(reverse_lazy("users:home_view"))
		#raise Http404
	if gerant.user==user:
		success_url = reverse_lazy('cddaccount:gerantcd_profile', kwargs={"matricule": matricule})
		return redirect(success_url)
	comptes_ids= gerant.mes_compte_depots.values_list("compte_id",flat=True) ## affectationns
	comptes =  CompteDepot.objects.filter(id__in=comptes_ids)#get_comptes(request).filter(actif=True)
	#comptes_ids=comptes.values_list("id", flat=True)
	agents_saisie=AgentSaisieCD.objects.filter(gerant_id=gerant.id).count()

	chequiers=Chequier.objects.filter(compte_id__in=comptes_ids).count()

	compte_depots_datas = comptes.aggregate(
		solde=Sum('balance', output_field=IntegerField()),
		nombre=Count('id', output_field=IntegerField()))
	gerant_ordres = OrdrePayment.objects.by_agent(gerant.user)
	can_make_saisie = user.has_perm('cddaccount.add_ordrepayment')
	create_op_url = reverse_lazy('cddaccount:create_ordrepayment_default')

	ordres_datas=gerant_ordres.exclude(reservationfond=None).aggregate(amount = Coalesce(Sum((F("amount")), output_field=IntegerField()), Value(0)),
	                                                     nombre = Count("id", output_field=IntegerField()))

	blocages = BlocageFond.objects.filter(compte_id__in=comptes_ids).aggregate(
		solde=Sum('balance', output_field=IntegerField()),
		amount=Sum('amount', output_field=IntegerField()),
		items=Count('id', output_field=IntegerField()))
	ordres_debit = AvisDeDebit.objects.filter(compte_id__in=comptes_ids).aggregate(
		amount=Sum('amount', output_field=IntegerField()),
		items=Count('id', output_field=IntegerField()))
	ordres_credit = AvisDeCredit.objects.filter(compte_id__in=comptes_ids).aggregate(
		amount=Sum('amount', output_field=IntegerField()),
		items=Count('id', output_field=IntegerField()))
	fonds_bloque = blocages


	last_ordres= gerant_ordres.filter( created__gte=datetime.datetime.now() - datetime.timedelta(
                                                  days=7))#.reverse()[:5]
	table = OrdrePaymentTable(last_ordres, request=request, exclude=("matricule", "gerant","selection"))
	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)


	#context = {"url_rb":url_rb,"can_make_saisie":can_make_saisie,"make_saisie_url":make_saisie_url,"balance":balance,"fonds_bloques":fonds_bloque,"currency": default_currency, "compte":compte,"title":title,"agent":gerant,"ordres_credit":ordres_credit,"ordres_debit":ordres_debit}



	return render(request, 'cddaccount/simple_dash_gerant.html', {"create_op_url":create_op_url,"chequiers":chequiers,"can_make_saisie":can_make_saisie,"table":table,"ordres":ordres_datas,"currency":default_currency,"compte_depots_datas":compte_depots_datas,"agent": gerant, "index": "0", "sens": "desc", "comptes": comptes,'agents_saisie':agents_saisie,"ordres_credit":ordres_credit,"ordres_debit":ordres_debit,"fonds_bloques":fonds_bloque})





@login_required
#@user_role_required(Role.GERANT)
# @user_role_required("ADMIN")
def gerantcd_profile_view(request, matricule):
	user = request.user
	gerant = GerantCD.objects.get(matricule=matricule)
	if gerant.status == STATUS_CREATION.NOUVEAU:
		messages.info(request, "Merci de completer les informations")
		success_url = reverse_lazy('cddaccount:complete_gerant', kwargs={"pk": gerant.id})
		return redirect(success_url)
	if gerant.user!=user:
		success_url = reverse_lazy('cddaccount:simple_gerantcd_profile', kwargs={"matricule": matricule})
		return redirect(success_url)
	compte = None
	can_create_structure = user.has_perm('core.add_structure')
	create_structure_url = None
	try:
		key= request.session["select_cddacc_user_id"]
		compte = CompteDepot.objects.get(id=int(key))

		if can_create_structure:
			create_structure_url = reverse_lazy('core:link_compte_to_structure')

	except KeyError:
		raise Http404

	gestionEnCours = AnneeComptable.current_gestion()
	if not gestionEnCours:
		#messages.info(request, "Annee comptable non encore ouvert")
		raise Http404


	date_du_jour = datetime.datetime.now()



	agents_saisie=AgentSaisieCD.objects.filter(gerant_id=gerant.id).count()

	chequiers=Chequier.objects.filter(compte_id=compte.id,is_use=False).count()


	compte_depots_datas={"solde":int(compte.balance.amount),"nombre":1,"solde_invest":int(compte.balance_insvest.amount),"solde_fonct":int(compte.balance_fonct.amount)}
	gerant_ordres = OrdrePayment.objects.filter(compte_id=compte.id)
	can_make_saisie = user.has_perm('cddaccount.add_ordrepayment')
	create_op_url = reverse_lazy('cddaccount:create_ordrepayment_default')

	ordres_datas=gerant_ordres.filter(created__year = gestionEnCours.year(),reservationfond__isnull=True).aggregate(amount = Coalesce(Sum((F("amount")), output_field=IntegerField()), Value(0)),
	                                                     nombre = Count("id", output_field=IntegerField()))



	blocages = BlocageFond.objects.filter(compte_id=compte.id).aggregate(
		solde=Sum('balance', output_field=IntegerField()),
		amount=Sum('amount', output_field=IntegerField()),
		items=Count('id', output_field=IntegerField()))
	ordres_debitFonct = AvisDeDebit.objects.filter(compte_id=compte.id,  date_avis__year = date_du_jour.year).values("typecompte_id").annotate(
		amount=Sum('amount', output_field=IntegerField()),
		items=Count('id', output_field=IntegerField()),
		nature=ExpressionWrapper(F("typecompte__nature"), output_field=CharField()),
		name=ExpressionWrapper(F("typecompte__name"), output_field=CharField()
		                       )
	)
	ordres_creditFonct = AvisDeCredit.objects.filter(compte_id=compte.id, date_avis__year = date_du_jour.year).values("typecompte_id").annotate(
		amount=Sum('amount', output_field=IntegerField()),
		items=Count('id', output_field=IntegerField()),
		nature=ExpressionWrapper(F("typecompte__nature"), output_field=CharField()),
		name=ExpressionWrapper(F("typecompte__name"), output_field=CharField()
		                       ))
	

	
	fonds_bloque = blocages
	

	reportCredit = ReportGestion.objects.filter(compte_id=compte.id, gestion_courant_id=gestionEnCours.id).values("typecompte_id").annotate(

		amount=Sum('amount', output_field=IntegerField()),

		nature=ExpressionWrapper(F("typecompte__nature"), output_field=CharField()),
		name=ExpressionWrapper(F("typecompte__name"), output_field=CharField()
		                       )
	)

	
	last_ordres= gerant_ordres.filter( created__gte=datetime.datetime.now() - datetime.timedelta(
                                                  days=7))
	table = GerantCDOrdrePaymentTable(last_ordres, request=request, exclude=("matricule", "gerant","selection"))
	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)

	details__solde= compute_all_balances_for_compte(compte,gestion=gestionEnCours.id,for_gerant=True,update=False)





	#context = {"url_rb":url_rb,"can_make_saisie":can_make_saisie,"make_saisie_url":make_saisie_url,"balance":balance,"fonds_bloques":fonds_bloque,"currency": default_currency, "compte":compte,"title":title,"agent":gerant,"ordres_credit":ordres_credit,"ordres_debit":ordres_debit}



	return render(request, 'cddaccount/dash_gerant.html', {"details__solde":details__solde,"can_create_structure":can_create_structure,"create_structure_url":create_structure_url,"create_op_url":create_op_url,"chequiers":chequiers,"can_make_saisie":can_make_saisie,"table":table,"ordres":ordres_datas,"currency":default_currency,"compte_depots_datas":compte_depots_datas,"agent": gerant, "index": "0", "sens": "desc", "compte": compte,'agents_saisie':agents_saisie,"ordres_creditFonct":ordres_creditFonct,  "ordres_debitFonct":ordres_debitFonct,"fonds_bloques":fonds_bloque, "reportCredit":reportCredit})



@login_required
@user_role_required(Role.AGENT_SAISIE_CD)

def agentsaisiecd_profile_view(request, matricule):
	user = request.user

	gerant = get_object_or_404(AgentSaisieCD, matricule=matricule)

	if gerant.status == STATUS_CREATION.NOUVEAU:
		messages.info(request, "Merci de completer les informations")
		success_url = reverse_lazy('cddaccount:complete_agentsaisiecd', kwargs={"pk": gerant.id})
		return redirect(success_url)
	if gerant.user!=user:
		raise Http404


	comptes = gerant.comptes.all()

	queryset = OrdrePayment.objects.by_agent(user)
	queryset_filter = OrdrePaymentFilter(request.GET, request=request, queryset=queryset)


	table = ASCDOrdrePaymentTable(queryset_filter.qs, request=request,exclude=("agent",))


	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)


	can_make_saisie = user.has_perm('cddaccount.add_ordrepayment')

	make_saisie_url = reverse_lazy('cddaccount:create_ordrepayment', kwargs={"pk": gerant.pk})

	return render(request, 'cddaccount/agentsaisie_dash.html', {'table': table, "filter_form": queryset_filter.form,"can_make_saisie":can_make_saisie,"make_saisie_url":make_saisie_url,"agent": gerant, "index": "0", "sens": "desc","comptes":comptes})


@login_required
# @user_role_required("ADMIN")
def gestion_ccompte_depot_view(request):
	create_url = reverse_lazy('cddaccount:create_comptedepot')

	user = request.user
	queryset = GestionCompteDepot.objects.by_agent(user)
	queryset_filter = GestionCompteDepotFilter(request.GET, request=request, queryset=queryset)
	table = GestionCompteDepotTable(queryset_filter.qs, exclude=("action",), request=request)
	can_create_dcp = user.has_perm('cddaccount.add_gestioncomptedepot')
	if user.has_perm('cddaccount.change_gestioncomptedepot') or user.has_perm('cddaccount.delete_gestioncomptedepot'):
		table = CompteDepotTable(queryset_filter.qs, request=request)
	title = _("Comptes de dépôts")
	data_title = _("Comptes de dépôts")

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'cddaccount/list_gestioncomptedepot.html',
	              {"create_url": create_url, "can_create_dcp": can_create_dcp, "data_title": data_title, 'table': table,
	               "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})




