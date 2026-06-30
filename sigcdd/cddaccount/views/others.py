import datetime
from django.contrib import messages
from bootstrap_modal_forms.utils import is_ajax
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django_tables2 import RequestConfig
from cddaccount.models import ObsProjet, Projet,Depositaire,STATUS_ORDRE_PAYMENT,BlocageFond, AnnulationBlocageFond
from helpers.decorators import user_role_required
from helpers.models import Role
from  cddaccount.views import get_cdd_with_gerant,PAGINATION_SIZE,default_currency
from cddaccount.signals import  projet_status_changed

# import generic UpdateView
import logging

logger = logging.getLogger(__name__)
from cddaccount.forms import DemandeBlocagefondForm,ProjetForm,  DepositaireModelForm, AcceptationOrdrePayementForm,  SimpleOPForm

from cddaccount.tables import AnnulationBlocageFondTable, AnnulationBlocageFondFilter, ProjetTable, ProjetFilter, DepositaireTable, DepositaireFilter

# Relative import of GeeksModel
from bootstrap_modal_forms.generic import (
	BSModalUpdateView,
	BSModalCreateView, BSModalDeleteView
)

from helpers.exceptions import SigException


@login_required
# @user_role_required("ADMIN")
def projets_list_view(request):
	user = request.user
	create_url = None
	queryset = Projet.objects.by_agent(user)
	queryset_filter = ProjetFilter(request.GET, request=request, queryset=queryset)
	can_create_dcp = user.has_perm('cddaccount.add_projet')
	if can_create_dcp:
		create_url = reverse_lazy('cddaccount:create_projet')

	table = ProjetTable(queryset_filter.qs, request=request, exclude=("action",))
	if hasattr(user, "gerant_cd") or hasattr(user, "agent_postecomptable"):
		table = ProjetTable(queryset_filter.qs, request=request)
	title = _("Liste Projets")
	data_title = _("Liste Projets")

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'cddaccount/projects_list.html',
	              {"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})


@method_decorator([user_role_required(Role.GERANT)], name='dispatch')
class ProjetCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'core/add_entity.html'
	form_class = ProjetForm
	model_name = form_class._meta.model._meta.model_name
	success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
	success_url = reverse_lazy('cddaccount:{}_list'.format(model_name, ))
	permission_required = ('cddaccount.add_{}'.format(model_name, ),)

	# @method_decorator(user_role_required("ADMIN"))
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def form_valid(self, form):
		if not is_ajax(self.request.META):
			form.instance.creator = self.request.user
		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		comptes = get_cdd_with_gerant(self.request)  # CompteDepot.objects.by_agent(self.request.user)
		context['form'].fields["compte"].queryset = comptes
		name = self.form_class._meta.model._meta.verbose_name
		context['title'] = "Nouveau {}".format(name, )
		return context


@method_decorator([user_role_required(Role.GERANT)], name='dispatch')
class ProjetDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	model = Projet
	permission_required = ('cddaccount.delete_projet',)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression projet'
	success_url = reverse_lazy('cddaccount:projet_list')

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Suppression  : {}".format(self.object, )
		return context


@method_decorator([user_role_required(Role.GERANT)], name='dispatch')
class ProjetUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = Projet
	template_name = 'core/update_entity.html'
	form_class = ProjetForm
	permission_required = ('cddaccount.change_projet',)
	success_message = 'Success: Mise à jour projet.'
	success_url = reverse_lazy('cddaccount:projet_list')

	# def has_permission(self):
	#    return self.request.user.is_active and self.request.user.is_staff

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		comptes = get_cdd_with_gerant(self.request)  # CompteDepot.objects.by_agent(self.request.user)
		context['form'].fields["compte"].queryset = comptes
		context['title'] = "Mise à jour de {} : {}".format(self.object._meta.verbose_name, self.object)
		return context



@method_decorator([user_role_required(Role.GERANT)], name='dispatch')
class DepositaireCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'core/add_entity.html'
	form_class = DepositaireModelForm
	model_name = form_class._meta.model._meta.model_name
	success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
	success_url = reverse_lazy('cddaccount:{}_list'.format(model_name, ))
	permission_required = ('cddaccount.add_{}'.format(model_name, ),)

	# @method_decorator(user_role_required("ADMIN"))
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def form_valid(self, form):
		if not is_ajax(self.request.META):
			obj = form.save(commit=False)
			obj.fonction = Role.AGENT_SAISIE_CD
			obj.gerant = self.request.user.gerant_cd
		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['form'].fields["comptes"].queryset = get_cdd_with_gerant(
			self.request)  # CompteDepot.objects.by_agent(self.request.user)
		name = self.form_class._meta.model._meta.verbose_name
		context['title'] = "Nouveau mandataire"
		return context


@method_decorator([user_role_required(Role.GERANT)], name='dispatch')
class DepositaireDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	c = "depositaire"
	model = Depositaire
	permission_required = ('cddaccount.delete_{}'.format(c, ),)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression agent de saisie compte de dépôt'
	success_url = reverse_lazy('cddaccount:{}_list'.format(c, ))

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Suppression agent : {}".format(self.object, )
		return context


@method_decorator([user_role_required(Role.GERANT)], name='dispatch')
class DepositaireUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = Depositaire
	c = "depositaire"
	template_name = 'core/update_entity.html'
	form_class = DepositaireModelForm
	permission_required = ('cddaccount.change_{}'.format(c, ),)
	success_message = 'Success: Mise à jour agent saisie compte de dépôt.'
	success_url = reverse_lazy('cddaccount:{}_list'.format(c, ))

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['form'].fields["comptes"].queryset = get_cdd_with_gerant(
			self.request)  # CompteDepot.objects.by_agent(self.request.user)
		context['title'] = "Mise à jour de {} : {}".format(self.object._meta.verbose_name, self.object)
		return context


@login_required
# @user_role_required("ADMIN")
def deposotaires_list_view(request):
	user = request.user
	create_url = reverse_lazy('cddaccount:create_depositaire')

	user = request.user
	queryset = Depositaire.objects.by_agent(user)
	queryset_filter = DepositaireFilter(request.GET, request=request, queryset=queryset)
	table = DepositaireTable(queryset_filter.qs, exclude=("action",))
	can_create_dcp = user.has_perm('cddaccount.add_depositaire')
	if user.has_perm('cddaccount.change_depositaire') or user.has_perm('cddaccount.delete_depositaire'):
		table = DepositaireTable(queryset_filter.qs)
	title = _("Mandataires")
	data_title = _("Mandataires")
	create_tilte = "Nouveau Mandataire"

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_tilte": create_tilte, "create_url": create_url, "can_create_entite": can_create_dcp,
	               "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})


@login_required
@transaction.atomic()
def details_blocagefond_view(request, pk):
	template = "cddaccount/details_blocagefond.html"
	user = request.user
	object = get_object_or_404(BlocageFond, id=pk)
	if not object.can_acces(user):
		raise Http404
	ordre_obs = object.ops_blocage.all()

	context = {"ordre_obs": ordre_obs, 'title': "Details blocage fond  {}".format(object.ref_marche, ),
	           "object": object, "compte": object.compte, }
	return render(request, template, context)


@login_required
@transaction.atomic()
@permission_required("cddaccount.demanderbf_project", raise_exception=True)
def deblocage_fond_view(request, reference):
	template = "cddaccount/add_op.html"
	user = request.user
	success_url = reverse_lazy('cddaccount:annulationblocagefond_list')
	object = get_object_or_404(BlocageFond, reference=reference)
	if not object.can_acces(user):
		raise Http404

	if request.method == 'POST':
		form = SimpleOPForm(request.POST)
		if form.is_valid():
			if request and not is_ajax(request.META):
				description = form.cleaned_data["description"]
				annulationBlocageFond = AnnulationBlocageFond()
				annulationBlocageFond.blocage = object
				annulationBlocageFond.reference = object.reference
				annulationBlocageFond.compte = object.compte
				annulationBlocageFond.amount = object.balance
				annulationBlocageFond.blocage = object
				annulationBlocageFond.demandeur = user
				annulationBlocageFond.description = description
				annulationBlocageFond.save()
				object.close
				object.save()
				messages.success(request, "Demande d'annulation des fonds bloqués avec succès")

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg, extra_tags="danger")
	else:

		form = SimpleOPForm()

	context = {"form": form, 'title': "Demande annulation fond bloqués N°{}  d'un montant  {}".format(object.ref_marche,
	                                                                                                  object.balance),
	           "object": object, "compte": object.compte}
	return render(request, template, context)


@login_required
# @user_role_required("ADMIN")
def annulationblocagefond_list_view(request):
	create_url = None
	user = request.user
	queryset = AnnulationBlocageFond.objects.by_agent(user)
	queryset_filter = AnnulationBlocageFondFilter(request.GET, request=request, queryset=queryset)
	table = AnnulationBlocageFondTable(queryset_filter.qs)
	can_create_dcp = False

	title = _("Annulation Blocage Fond")
	data_title = _("Annulation Blocage Fond")

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})


@login_required
@transaction.atomic()
@permission_required("cddaccount.approuver_annulationblocagefond", raise_exception=True)
def approuver_deblocage_fond_view(request, reference):
	template = "cddaccount/add_op.html"
	user = request.user
	success_url = reverse_lazy('cddaccount:annulationblocagefond_list')
	annulationBlocageFond = get_object_or_404(AnnulationBlocageFond, reference=reference)
	object = annulationBlocageFond.blocage
	compte = object.compte
	if not annulationBlocageFond.can_acces(user):
		raise Http404

	if request.method == 'POST':
		form = SimpleOPForm(request.POST)
		if form.is_valid():
			if request and not is_ajax(request.META):
				description = form.cleaned_data["description"]

				annulationBlocageFond.approbation_date = datetime.datetime.now()
				annulationBlocageFond.approuver = True
				annulationBlocageFond.approbateur = user
				annulationBlocageFond.description = description
				annulationBlocageFond.save()

				if compte.can_credit_trx(annulationBlocageFond.amount):
					try:
						compte.credit(annulationBlocageFond.amount)
						object.balance = 0
						object.save()
					except SigException as e:

						messages.error(request, e.message, extra_tags="danger")
						return redirect(success_url)
				else:
					messages.error(request, "Montant suupérieur au solde du compte", extra_tags="danger")
					return redirect(success_url)

				# on vide
				messages.success(request, "Validation  d'annulation des fonds bloqués avec succès")

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg, extra_tags="danger")
	else:

		form = SimpleOPForm()

	context = {"form": form,
	           'title': "Validation annulation fond bloqués N°{}  d'un montant  {}".format(object.ref_marche,
	                                                                                       object.balance),
	           "object": object, "compte": object.compte}
	return render(request, template, context)


@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def temlate_bf_view(request, reference):
	template = "cddaccount/template_bf.html"
	user = request.user
	ordre = get_object_or_404(BlocageFond, reference=reference)
	iban_items = ordre.benef_iban_items()

	if not ordre.can_acces(user):
		raise Http404
	create_url = None
	gerant = None

	compte = ordre.compte

	context = {"compte": compte, "ordre": ordre, "agent": gerant, 'title': "Template  N° {}".format(ordre.reference, ),
	           "iban_items": iban_items}
	return render(request, template, context)

@login_required
# @permission_required("cddaccount.demanderbf_projet")
def demander_bf_projet_view(request, pk):
	template = "cddaccount/demande_bf_form.html"
	user = request.user

	if not user.has_perm("cddaccount.demanderbf_project"):
		raise Http404
	success_url = reverse_lazy('cddaccount:projet_list')
	object = get_object_or_404(Projet, id=pk)
	if not object.can_acces(user):
		raise Http404

	initial = {"description": "RAS"}
	c= True

	if request.method == 'POST':
		form = DemandeBlocagefondForm(request.POST)
		if form.is_valid():
			if request and not is_ajax(request.META):
				#if object.compte.can_debit_trx(object.amount):
				if c:
					description = form.cleaned_data["description"]
					object.demande_date = datetime.datetime.today()
					object.demande_blocage = True
					object.observations = description
					object.save()
					obs = ObsProjet()
					obs.projet = object
					obs.observations = description
					obs.creator = user
					obs.save()
					messages.success(request, "Demande de blocage envoyé")

				else:
					messages.error(request, "Montant supérieur au solde du compte actuel", extra_tags="danger")
					return redirect(success_url)

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg, extra_tags="danger")
	else:
		form = DemandeBlocagefondForm(initial=initial)

	context = {"form": form, 'title': "Envoyer demande de blocage de fond {}".format(object.id, )}
	return render(request, template, context)


@login_required
@transaction.atomic()
@permission_required("cddaccount.validerbf_project")
def valider_projet_bf_view(request, pk):
	template = "cddaccount/valider_demande_bf.html"
	user = request.user
	success_url = reverse_lazy('cddaccount:projet_list')
	object = get_object_or_404(Projet, id=pk)
	if not object.can_acces(user):
		raise Http404
	gerant = object.creator.gerant_cd

	if request.method == 'POST':
		form = AcceptationOrdrePayementForm(request.POST)
		if form.is_valid():
			if request and not is_ajax(request.META):
				status = form.cleaned_data["status"]
				description = form.cleaned_data["description"]
				if status == STATUS_ORDRE_PAYMENT.ACCEPTE:

					object.accepter_blocage = True
					object.status = status
					object.acceptation_date = datetime.datetime.today()
					object.agent_postecomptable = user
					object.save()
					projet_status_changed.send(sender=type(object), instance=object)
					messages.success(request, "Blocage de fond  {}".format(status.lower()))

				else:
					object.status = status
					object.demande_blocage = True
					object.observations = description
					object.save()

					messages.info(request, "Blocage de fond {}".format(status.lower()))
				obs = ObsProjet()
				obs.projet = object
				obs.observations = description
				obs.creator = user
				obs.save()

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg, extra_tags="danger")
	else:

		form = AcceptationOrdrePayementForm()

	context = {"form": form, 'title': "Validation blocage fond du projet  {}".format(object.ref_marche, ),
	           "object": object, "compte": object.compte, "agent": gerant, }
	return render(request, template, context)


@login_required
@transaction.atomic()
def details_projet_bf_view(request, pk):
	template = "cddaccount/details_projet.html"
	user = request.user
	object = get_object_or_404(Projet, id=pk)
	if not object.can_acces(user):
		raise Http404
	gerant = object.creator.gerant_cd
	ordre_obs = object.projet_obs.all()

	context = {"ordre_obs": ordre_obs, 'title': "Details projet projet  {}".format(object.ref_marche, ),
	           "object": object, "compte": object.compte, "agent": gerant, }
	return render(request, template, context)

