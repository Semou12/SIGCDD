import datetime
import traceback

from bootstrap_modal_forms.utils import is_ajax
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django_tables2 import RequestConfig
from decimal import Decimal
from cddaccount import STATUS_CREATION, NATURE_FONDS, PAYMENT_MEAN_TYPE, ETAPE_ORDRE_PAYMENT, SENS_TRX
from cddaccount.models import GestionCompteDepot, AgentSaisieCD, CompteDepot, Bank, CodeAgence, \
	GerantCD, create_gerant_affectation, Nature, AnneeComptable, BlocageFond, Report, SousNature, Mandataire, \
	OrdrePayment, delete_a_validate_op_initiate_by_pc, TypeCompteTrx, ReportGestion, CompteTrx, DemandeOP
from cddaccount.process import CddProcessManager
from cddaccount.tables import BlocageFondTable, BlocageFondFilter, AnneeComptableTable, AnneeComptableFilter, \
	NatureTable, NatureFilter, GestionCompteDepotTable, GestionCompteDepotFilter, AgentSaisieCDTable, \
	AgentSaisieCDFilter, GerantCDTable, GerantCDFilter, CompteDepotFilter, CompteDepotTable, BankTable, BankFilter, \
	CodeAgenceTable, CodeAgenceFilter, ReportTable, ReportFilter, SousNatureFilter, SousNatureTable, MandataireFilter, \
	MandataireTable, OrdrePaymentFilter, ASCDOrdrePaymentTable, GerantCDOrdrePaymentTable, AgentPCOrdrePaymentTable, \
	OrdrePaymentTable, TypeCompteTrxTable, ReportGestionFilter, ReportGestionTable, CompteTrxTable, CompteTrxFilter, \
	DemandeOPFilter, DemandeOPTable
from core.models import CodeService, Secteur, PosteComptable
from helpers.commons import notify_badge
from helpers.decorators import user_role_required
from helpers.exceptions import SigException
from helpers.models import Role, SigRole, TypeNotif
from users.models import User

PAGINATION_SIZE = 100

default_currency = "F CFA"
# import generic UpdateView

from cddaccount.forms import UpdateDepotModelForm, BlocageFondForm, NatureForm, UpdateAgentSaisieCDModelForm, \
	GerantCDFormDIUserModelForm, AgentSaisieCDForm, ValidationAgentSaisieCDForm, AgentSaisieCDModelForm, \
	ValidationGerantCDForm, ValidationCompteForm, CompteDepotModelForm, BankForm, CodeAgenceForm, GerantCDModelForm, \
	CompleteGerantCDForm, AffectationGerantCDModelForm, AnneeComptableForm, UpdateGerantCDModelForm, \
	UpdateGerantCDFormDIUserModelForm, ActiverCompteDepotModelForm, ReportForm, ChoseCddAccountForm, \
	CompteDepotNewModelForm, SousNatureForm, MandataireModelForm, DeleteOPByPCForm, UpdateSecretCompteDepotModelForm, \
	TypeCompteTrxModelForm, CompteTrxModelForm, DemandeOPModelForm
# Relative import of GeeksModel
from bootstrap_modal_forms.generic import (
	BSModalDeleteView,
	BSModalCreateView, BSModalUpdateView
)

def get_comptes(request):
	try:
		key= request.session["select_cddacc_user_id"]
		return CompteDepot.objects.filter(id=int(key)).prefetch_related("secteur","code_service","direction","poste","ministere","agent","validation_cd")
	except KeyError:
		return CompteDepot.objects.by_agent(request.user).prefetch_related("secteur","code_service","direction","poste","ministere","agent","validation_cd")

@login_required
# @user_role_required("ADMIN")
def comptedepot_list_view(request):
	create_url = reverse_lazy('cddaccount:create_comptedepot')

	template_name = 'cddaccount/list_comptedepots.html'
	#if request.htmx:
	#s	template_name = "datatables/table_only.html"

	user = request.user
	queryset = get_comptes(request) #CompteDepot.objects.by_agent(user)
	queryset_filter = CompteDepotFilter(request.GET, request=request, queryset=queryset)
	#table = CompteDepotTable(queryset_filter.qs, exclude=("action",), request=request)
	can_create_dcp = user.has_perm('cddaccount.add_comptedepot')
	#if user.has_perm('cddaccount.change_comptedepot') or user.has_perm('cddaccount.delete_comptedepot'):
	table = CompteDepotTable(queryset_filter.qs, request=request)
	title = _("Comptes de dépôt")
	data_title = _("Comptes de dépôt")

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request,template_name ,
	              {"create_url": create_url, "can_create_dcp": can_create_dcp, "data_title": data_title, 'table': table,
	               "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})

@login_required
# @user_role_required("ADMIN")
def new_comptedepot_list_view(request):
	create_url = reverse_lazy('cddaccount:create_comptedepot')

	template_name = 'cddaccount/list_comptedepots.html'
	#if request.htmx:
	#s	template_name = "datatables/table_only.html"

	user = request.user
	queryset = get_comptes(request).filter(validation_cd__isnull=True) #CompteDepot.objects.by_agent(user)
	queryset_filter = CompteDepotFilter(request.GET, request=request, queryset=queryset)
	#table = CompteDepotTable(queryset_filter.qs, exclude=("action",), request=request)
	can_create_dcp = user.has_perm('cddaccount.add_comptedepot')
	#if user.has_perm('cddaccount.change_comptedepot') or user.has_perm('cddaccount.delete_comptedepot'):
	table = CompteDepotTable(queryset_filter.qs, request=request)
	title = _("Nouveaux Comptes de dépôt")
	data_title = _("Nouveaux Comptes de dépôt")

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request,template_name ,
	              {"create_url": create_url, "can_create_dcp": can_create_dcp, "data_title": data_title, 'table': table,
	               "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})

from django.core.exceptions import PermissionDenied
@login_required

def secrete_comptedepot_list_view(request):
	user = request.user
	create_url = reverse_lazy('cddaccount:create_comptedepot')

	template_name = 'cddaccount/list_comptedepots.html'
	can_configure = user.has_perm('cddaccount.configure_secretecompte')
	can_use = user.has_perm('cddaccount.use_secretecompte')
	if not can_configure and not can_use : raise  PermissionDenied


	queryset = CompteDepot.objects.by_agent(request.user).filter(secrete=True)
	queryset_filter = CompteDepotFilter(request.GET, request=request, queryset=queryset)
	#table = CompteDepotTable(queryset_filter.qs, exclude=("action",), request=request)
	can_create_dcp = user.has_perm('cddaccount.add_comptedepot')
	#if user.has_perm('cddaccount.change_comptedepot') or user.has_perm('cddaccount.delete_comptedepot'):
	table = CompteDepotTable(queryset_filter.qs, request=request)
	title = _("Comptes de dépôt Secret")
	data_title = _("Comptes de dépôt Secret")

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request,template_name ,
	              {"create_url": create_url, "can_create_dcp": can_create_dcp, "data_title": data_title, 'table': table,
	               "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})


from django.contrib.contenttypes.models import ContentType
from helpers.models import Notification


def call_notify_badge_forcdd(compte):
	recepients = None
	creator = compte.agent

	category = TypeNotif.live_notify_badge_cdd
	recepients = User.objects.filter(agent_dcp__dcp_id=creator.dcp_id)

	if recepients:
		notify_badge(compte, recepients, category, "Nouveau compte")
	print("end envoie notif")


def delete_notificationcdd(compte, user):
	try:
		actortype = ContentType.objects.get_for_model(CompteDepot)
		Notification.objects.filter(actor_content_type=actortype, actor_object_id=str(compte.id)).delete()
	except:
		traceback.print_exc()
		pass


@method_decorator([user_role_required(Role.AGENT_DCP)], name='dispatch')
class CompteDepotCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'cddaccount/add_comptedepot.html'
	form_class = CompteDepotNewModelForm
	model_name = form_class._meta.model._meta.model_name
	success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
	success_url = reverse_lazy('cddaccount:{}_list'.format(model_name, ))
	permission_required = ('cddaccount.add_{}'.format(model_name, ),)

	# @method_decorator(user_role_required("ADMIN"))
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def get_initial(self):
		initial = super().get_initial()
		#cagence = CodeAgence.objects.last()
		#initial["agence"] = cagence
		return initial

	def form_valid(self, form):
		if not is_ajax(self.request.META):

			self.object = form.save(commit=False)

			self.object.agence=CodeAgence.objects.last()

			if not hasattr(self.object, "secteur"):
				self.object.secteur = Secteur.objects.last()
			if not hasattr(self.object,"code_service"):
				self.object.code_service = CodeService.objects.last()
			if "typefond" not in form.cleaned_data:
				self.object.typefond = NATURE_FONDS.FONDSDAVANCE


			self.object.agent = self.request.user.agent_dcp
			self.object.open_date = datetime.date.today()
			if "compte" in form.cleaned_data:
				iban = form.cleaned_data['compte']
				if iban and len(iban) > 0:
					self.object.set_shortiban_items(iban)

			#form.save()
			self.object.save()
			call_notify_badge_forcdd(self.object)

		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		name = self.form_class._meta.model._meta.verbose_name
		context['title'] = "Nouveau {}".format(name, )
		context['form'].fields["poste"].queryset = PosteComptable.objects.filter(in_production=True)
		return context


@method_decorator([user_role_required(Role.AGENT_DCP)], name='dispatch')
class CompteDepotDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	model = CompteDepot
	permission_required = ('cddaccount.delete_comptedepot',)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression entité poste comptable'
	success_url = reverse_lazy('cddaccount:comptedepot_list')

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Suppression entite : {}".format(self.object, )
		return context


#@method_decorator([user_role_required(Role.AGENT_DCP)], name='dispatch')
class CompteDepoteUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = CompteDepot
	template_name = 'cddaccount/update_comptedepot.html'
	#form_class = UpdateDepotModelForm
	permission_required = ('cddaccount.change_comptedepot',)
	success_message = 'Success: Mise à jour poste comptable.'
	success_url = reverse_lazy('cddaccount:comptedepot_list')

	def get_form_class(self):
		can_configure_secretcdd = self.request.user.has_perm('cddaccount.configure_secretecompte')
		self.form_class = UpdateDepotModelForm
		
		if can_configure_secretcdd:
			self.form_class = UpdateSecretCompteDepotModelForm
		return self.form_class

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['form'].fields["poste"].queryset = PosteComptable.objects.filter(in_production=True)
		context['title'] = "Mise à jour de l' entité {} : {}".format(self.object._meta.verbose_name, self.object)
		return context


@login_required
# @user_role_required("ADMIN")
def bank_list_view(request):
	create_url = reverse_lazy('cddaccount:create_bank')

	user = request.user
	queryset = Bank.objects.all()
	queryset_filter = BankFilter(request.GET, request=request, queryset=queryset)
	table = BankTable(queryset_filter.qs, exclude=("action",))
	can_create_dcp = user.has_perm('cddaccount.add_bank')
	if user.has_perm('cddaccount.change_bank') or user.has_perm('cddaccount.delete_bank'):
		table = BankTable(queryset_filter.qs)
	title = _("Banques")
	data_title = _("Banques")
	create_tilte = "Nouvelle Banque"

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_tilte":create_tilte,"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})


@method_decorator([user_role_required(Role.AGENT_DCP)], name='dispatch')
class BankCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'core/add_entity.html'
	form_class = BankForm
	model_name = form_class._meta.model._meta.model_name
	success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
	success_url = reverse_lazy('cddaccount:{}_list'.format(model_name, ))
	permission_required = ('cddaccount.add_{}'.format(model_name, ),)

	# @method_decorator(user_role_required("ADMIN"))
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def form_valid(self, form):
		if not is_ajax(self.request.META):
			form.instance.agent = self.request.user.agent_dcp
		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		name = self.form_class._meta.model._meta.verbose_name
		context['title'] = "Nouvel entité {}".format(name, )
		return context


@method_decorator([user_role_required(Role.AGENT_DCP)], name='dispatch')
class BankDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	model = Bank
	permission_required = ('cddaccount.delete_bank',)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression entité poste comptable'
	success_url = reverse_lazy('cddaccount:bank_list')

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Suppression entite : {}".format(self.object, )
		return context


@method_decorator([user_role_required(Role.AGENT_DCP)], name='dispatch')
class BankUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = Bank
	template_name = 'core/update_entity.html'
	form_class = BankForm
	permission_required = ('cddaccount.change_bank',)
	success_message = 'Success: Mise à jour banque.'
	success_url = reverse_lazy('cddaccount:bank_list')

	# def has_permission(self):
	#    return self.request.user.is_active and self.request.user.is_staff

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Mise à jour de l' entité {} : {}".format(self.object._meta.verbose_name, self.object)
		return context


@login_required
# @user_role_required("ADMIN")
def codeagence_list_view(request):
	create_url = reverse_lazy('cddaccount:create_codeagence')

	user = request.user
	queryset = CodeAgence.objects.all()
	queryset_filter = CodeAgenceFilter(request.GET, request=request, queryset=queryset)
	table = CodeAgenceTable(queryset_filter.qs, exclude=("action",))
	can_create_dcp = user.has_perm('cddaccount.add_codeagence')
	if user.has_perm('cddaccount.change_codeagence') or user.has_perm('cddaccount.delete_codeagence'):
		table = CodeAgenceTable(queryset_filter.qs)
	title = _("Code agence")
	data_title = _("Code agence")
	create_tilte="Nouveau Code agence"

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_tilte":create_tilte,"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})


@method_decorator([user_role_required([Role.AGENT_DCP,Role.ADMIN])], name='dispatch')
class CodeAgenceUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = CodeAgence
	template_name = 'core/update_entity.html'
	form_class = CodeAgenceForm
	permission_required = ('cddaccount.change_codeagence',)
	success_message = 'Success: Mise à jour code agence.'
	success_url = reverse_lazy('cddaccount:codeagence_list')

	# def has_permission(self):
	#    return self.request.user.is_active and self.request.user.is_staff

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Mise à jour de l' entité {} : {}".format(self.object._meta.verbose_name, self.object)
		return context


@method_decorator([user_role_required(Role.AGENT_DCP)], name='dispatch')
class CodeAgenceDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	model = CodeAgence
	permission_required = ('cddaccount.delete_codeagence',)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression entité avec succès'
	success_url = reverse_lazy('cddaccount:codeagence_list')

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Suppression entite : {}".format(self.object, )
		return context


@method_decorator([user_role_required(Role.AGENT_DCP)], name='dispatch')
class CodeAgenceCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'core/add_entity.html'
	form_class = CodeAgenceForm
	model_name = form_class._meta.model._meta.model_name
	success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
	success_url = reverse_lazy('cddaccount:{}_list'.format(model_name, ))
	permission_required = ('cddaccount.add_{}'.format(model_name, ),)

	# @method_decorator(user_role_required("ADMIN"))
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def form_valid(self, form):
		if not is_ajax(self.request.META):
			form.instance.agent = self.request.user.agent_dcp
		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		name = self.form_class._meta.model._meta.verbose_name
		context['title'] = "Nouvel entité {}".format(name, )
		return context


from django.contrib import messages


@login_required
@user_role_required(Role.AGENT_DCP)
@permission_required('cddaccount.add_validationcompte', raise_exception=True)
def create_validationcompte(request, id):
	template = "cddaccount/validate.html"
	user = request.user
	success_url = reverse_lazy('cddaccount:comptedepot_list')
	compte = get_object_or_404(CompteDepot, id=id)
	delete_notificationcdd(compte, user)
	if hasattr(compte, "validation_cd"):
		messages.info(request, "Compte déja validé")
		return redirect(success_url)
	if request.method == 'POST':
		form = ValidationCompteForm(request.POST)
		if form.is_valid():
			if request and not is_ajax(request.META):
				try:
					object = form.save(commit=False)
					with transaction.atomic():

						object.compte = compte
						object.agent = user.agent_dcp
						CddProcessManager.create_a_compte(user,compte)
						messages.info(request, "Compte validé avec succès")
						object.save()
				except SigException as e:
					messages.error(request, e.message,extra_tags="danger")

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		form = ValidationCompteForm()

	context = {"form": form, 'title': "Validation Compte {}".format(compte.compte, ), "compte": compte}
	return render(request, template, context)


@method_decorator([user_role_required([Role.AGENT_PC,Role.ADMIN])], name='dispatch')
#s@transaction.atomic()
class StartGerantCDCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'core/add_entity.html'
	form_class = GerantCDModelForm
	model_name = form_class._meta.model._meta.model_name
	success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
	success_url = reverse_lazy('cddaccount:{}_list'.format(model_name, ))
	permission_required = ('cddaccount.add_{}'.format(model_name, ),)

	# @method_decorator(user_role_required("ADMIN"))
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def get_form_class(self):
		"""Return the form class to use."""
		user = self.request.user
		if user.role == Role.ADMIN:
			self.form_class = GerantCDFormDIUserModelForm

		elif hasattr(user, "agent_postecomptable") == True:
			self.form_class=GerantCDModelForm
		else:
			self.form_class = GerantCDModelForm

		return self.form_class

	def form_valid(self, form):
		user = self.request.user
		if not is_ajax(self.request.META):
			obj = form.save(commit=False)
			roles = form.cleaned_data["roles"]
			try:
				obj.fonction = Role.GERANT
				if user.role == Role.ADMIN:
					pass
				else:
					obj.agent = self.request.user.agent_postecomptable
					obj.poste = self.request.user.agent_postecomptable.poste
				obj.creator = self.request.user
				create_user_by_gerantcd_infos(obj,form.cleaned_data["compte"],roles)


			except SigException as ex:
				messages.error(self.request, ex.message,extra_tags="danger")
				return redirect(self.success_url)
		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		name = self.form_class._meta.model._meta.verbose_name
		comptes = get_comptes(self.request) #CompteDepot.objects.by_agent(self.request.user)

		comptes=comptes.filter(compte_affections_gerants=None) #comptes non affectes
		context['form'].fields["compte"].queryset = comptes
		context['title'] = "Nouveau {}".format(name, )
		sigrole = SigRole.objects.get(role=Role.GERANT)
		context['form'].fields["roles"].queryset = sigrole.groups.all()
		return context


@method_decorator([user_role_required([Role.AGENT_PC,Role.ADMIN])], name='dispatch')
class GerantCDUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = GerantCD
	c = "gerantcd"
	template_name = 'core/update_entity.html'
	form_class = UpdateGerantCDModelForm
	permission_required = ('cddaccount.change_{}'.format(c, ),)
	success_message = 'Success: Mise à jour agent compte de dépôt.'
	success_url = reverse_lazy('cddaccount:{}_list'.format(c, ))

	def get_form_class(self):
		"""Return the form class to use."""
		user = self.request.user
		if user.role == Role.ADMIN:
			self.form_class = UpdateGerantCDFormDIUserModelForm

		elif hasattr(user, "agent_postecomptable") == True:
			self.form_class=UpdateGerantCDModelForm
		else:
			self.form_class = UpdateGerantCDModelForm

		return self.form_class

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		#comptes = CompteDepot.objects.by_agent(self.request.user)

		#context['form'].fields["compte"].queryset = comptes
		sigrole = SigRole.objects.get(role=Role.GERANT)
		context['form'].fields["roles"].queryset = sigrole.groups.all()
		context['title'] = "Mise à jour de {} : {}".format(self.object._meta.verbose_name, self.object)
		return context

	def form_valid(self, form):
		if not is_ajax(self.request.META):
			obj = form.save(commit=False)
			roles = form.cleaned_data["roles"]
			obj.user.groups.set(roles)
			form.save()

		return super().form_valid(form)

	def get_initial(self):
		initial = super().get_initial()
		ref = self.get_object()
		groups = ref.user.groups.all()
		a = [i.id for i in groups.all()]
		initial["roles"] = a
		return initial


@method_decorator([user_role_required([Role.AGENT_PC,Role.ADMIN])], name='dispatch')
class GerantCDDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	c = "gerantcd"
	model = GerantCD
	permission_required = ('cddaccount.delete_{}'.format(c, ),)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression gérant compte de dépôt'
	success_url = reverse_lazy('cddaccount:{}_list'.format(c, ))

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Suppression agent : {}".format(self.object, )
		return context


@login_required
# @user_role_required("ADMIN")
def gerantcd_list_view(request):
	user = request.user
	create_url = reverse_lazy('cddaccount:create_gerantcd')

	change_gerant_url =None

	can_create_affectaion = user.has_perm('cddaccount.add_gestioncomptedepot')
	if can_create_affectaion:
		change_gerant_url = reverse_lazy('cddaccount:create_gestioncomptedepot')


	queryset = GerantCD.objects.by_agent(user)
	queryset_filter = GerantCDFilter(request.GET, request=request, queryset=queryset)
	table = GerantCDTable(queryset_filter.qs, exclude=("action",))
	can_create_dcp = user.has_perm('cddaccount.add_gerantcd')

	if user.has_perm('cddaccount.change_gerantcd') or user.has_perm('cddaccount.delete_gerantcd'):
		table = GerantCDTable(queryset_filter.qs)
	title = _("GÉRANT COMPTE DE DÉPÔT")
	data_title = _("Gérant Compte Dépot")
	create_tilte = "Nouveau Gérant Compte Dépôt"

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'cddaccount/list_gerantcd.html',
	              {"can_create_affectaion":can_create_affectaion,"new_affectation_url":change_gerant_url,"create_tilte": create_tilte, "create_url": create_url, "can_create_agent": can_create_dcp,
	               "data_title": data_title, 'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0",
	               "sens": "desc"})


@transaction.atomic
def create_user_by_gerantcd_infos(agent,compte,roles):
	try:
		User.objects.get(username=agent.matricule)
		error = "Un utilisateur ayant cet identifiant {} existe déjà".format(agent.matricule, )
		ex = SigException(message=error)

		raise ex
	except User.DoesNotExist:
		user = User()
		user.username = agent.matricule
		user.role = agent.fonction
		user.last_name = agent.lastname
		user.first_name = agent.firstname
		user.force_change_pwd = True
		# user.email = agent.email
		password1 = BaseUserManager().make_random_password(8)
		user.set_password(password1)
		user.is_active = True
		user.is_staff = False
		user.is_superuser = False
		user.save()
		agent.user = user
		agent.save()  # --->desactive le user
		user.is_active = True
		user.groups.set(roles)
		user.save()
		agent.send_sms_message(password1)
		try:
			create_gerant_affectation(agent, agent.creator, compte)
		except SigException as e: raise e

@login_required
@user_role_required(Role.GERANT)
def complete_gerantcd_data(request, pk):
	template = "cddaccount/complete_gerant.html"
	user = request.user
	gerant = get_object_or_404(GerantCD, id=pk)
	success_url = reverse_lazy('cddaccount:gerantcd_profile', kwargs={"matricule": gerant.matricule})
	if gerant.user != user:
		raise Http404
	if gerant.account_is_valid() or gerant.status == STATUS_CREATION.ATTENTE:
		return redirect(success_url)
	if request.method == 'POST':
		form = CompleteGerantCDForm(request.POST, request.FILES)
		if form.is_valid():
			if request and not is_ajax(request.META):
				object = form.save(commit=False)

				gerant.acte_nomin = object.acte_nomin
				gerant.justificatif = object.justificatif
				gerant.teaser_signature = object.teaser_signature
				gerant.status = STATUS_CREATION.ATTENTE
				gerant.is_actif = False
				messages.success(request, "Votre compte est attennte de validation par le poste comptable")

				# apres changment process

				"""gerant.status = STATUS_CREATION.VALIDE
				gerant.is_actif = True
				gerant.valide = True
				gerant.date_validation = datetime.datetime.now()
				messages.success(request, "Votre compte est actif")
				"""
				gerant.save()


			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		form = CompleteGerantCDForm()

	context = {"form": form, 'title': "Compléter informations {}".format(gerant.matricule, ), "gerant": gerant}
	return render(request, template, context)


@login_required
@user_role_required([Role.AGENT_PC,Role.ADMIN])
@transaction.atomic()
def validate_gerantcd_data(request, matricule):
	template = "cddaccount/validate_gerant.html"
	user = request.user
	success_url = reverse_lazy('cddaccount:gerantcd_list')
	gerant = get_object_or_404(GerantCD, matricule=matricule)

	#if user.role == Role.ADMIN:comptes = gerant.poste.comptes_depots.filter(actif=True)

	#else:comptes = user.agent_postecomptable.poste.comptes_depots.filter(actif=True)

	if request.method == 'POST':
		form = ValidationGerantCDForm(request.POST,request.FILES)
		#form.fields['compte'].queryset = comptes
		if form.is_valid():
			if request and not is_ajax(request.META):
				#compte = form.cleaned_data["compte"]
				gerant.status = STATUS_CREATION.VALIDE
				gerant.is_actif = True
				gerant.valide = True
				gerant.date_validation = datetime.datetime.now()

				if  "signature" in form.cleaned_data:
					filehandle = form.cleaned_data["signature"]
					if  filehandle:
						gerant.teaser_signature=filehandle
				gerant.save()
				# creation affectation par defaut

				if user.role == Role.ADMIN:
					agent_pc=None
				else: agent_pc=user.agent_postecomptable
				#create_gerant_affectation(gerant, user, compte)
				messages.success(request, "Gerant valide est actif ")

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		form = ValidationGerantCDForm()
		#form.fields['compte'].queryset = comptes

	context = {"form": form, 'title': "Valider création gérant {}".format(gerant.matricule, ), "gerant": gerant}
	return render(request, template, context)



@login_required
# @user_role_required("ADMIN")
def agentsaisie_cd_list_view(request):
	create_url = reverse_lazy('cddaccount:create_agentsaisiecd')

	user = request.user
	queryset = AgentSaisieCD.objects.by_agent(user)
	queryset_filter = AgentSaisieCDFilter(request.GET, request=request, queryset=queryset)
	table = AgentSaisieCDTable(queryset_filter.qs, exclude=("action",), request=request)
	can_create_dcp = user.has_perm('cddaccount.add_agentsaisiecd')
	if user.has_perm('cddaccount.change_cagentsaisiecd') or user.has_perm('cddaccount.delete_agentsaisiecd'):
		table = AgentSaisieCDTable(queryset_filter.qs, request=request)
	title = _("Agent Saisie Comptes de dépôts")
	data_title = _("Agents Saisie Comptes de dépôts")

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'cddaccount/list_gerantcd.html',
	              {"create_url": create_url, "can_create_agent": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})


@transaction.atomic
def create_user_by_agentsaisiecd_infos(agent,roles):
	try:
		User.objects.get(username=agent.matricule)
		error = "Un utilisateur ayant cet identifiant {} existe déjà".format(agent.matricule, )
		ex = Exception()
		ex.message = error
		raise ex
	except User.DoesNotExist:
		user = User()
		user.username = agent.matricule
		user.role = agent.fonction
		user.last_name = agent.lastname
		user.first_name = agent.firstname
		user.force_change_pwd = True
		# user.email = agent.email
		password1 = BaseUserManager().make_random_password(8)
		user.set_password(password1)
		user.is_active = True
		user.is_staff = False
		user.is_superuser = False
		user.save()
		agent.user = user
		agent.save()  # --->desactive le user
		user.groups.set(roles)
		user.is_active = True
		user.save()
		agent.send_sms_message(password1)


@method_decorator([user_role_required(Role.GERANT)], name='dispatch')
class StartAgentSaisieCDCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'core/add_entity.html'
	form_class = AgentSaisieCDModelForm
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
			try:
				obj.fonction = Role.AGENT_SAISIE_CD
				obj.gerant = self.request.user.gerant_cd
				roles = form.cleaned_data["roles"]

				create_user_by_agentsaisiecd_infos(obj,roles)
			except Exception as ex:
				messages.error(self.request, ex.message)
		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		name = self.form_class._meta.model._meta.verbose_name
		comptes = CompteDepot.objects.by_agent(self.request.user)

		context['form'].fields["comptes"].queryset = comptes
		context['title'] = "Nouveau {}".format(name, )
		sigrole = SigRole.objects.get(role=Role.AGENT_SAISIE_CD)
		context['form'].fields["roles"].queryset = sigrole.groups.all()
		return context


@method_decorator([user_role_required(Role.GERANT)], name='dispatch')
class AgentSaisieCDDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	c = "agentsaisiecd"
	model = AgentSaisieCD
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


@login_required
@user_role_required(Role.GERANT)
@transaction.atomic()
def validate_agentsaisiecd_data(request, matricule):
	template = "cddaccount/validate_gerant.html"
	user = request.user
	success_url = reverse_lazy('cddaccount:agentsaisiecd_list')
	agent = get_object_or_404(AgentSaisieCD, matricule=matricule)
	comptes =get_comptes(request) #CompteDepot.objects.by_agent(user) #user.gerant_cd.comptes_depots.filter(actif=True)
	if agent.gerant != user.gerant_cd:
		raise Http404

	if request.method == 'POST':
		form = ValidationAgentSaisieCDForm(request.POST)
		form.fields['compte'].queryset = comptes
		if form.is_valid():
			if request and not is_ajax(request.META):
				compte = form.cleaned_data["compte"]
				agent.status = STATUS_CREATION.VALIDE
				agent.is_actif = True
				agent.valide = True
				agent.comptes.set(compte)
				agent.date_validation = datetime.datetime.now()
				agent.save()
				messages.success(request, "Agent saisie valide est actif ")

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		form = ValidationAgentSaisieCDForm()
		form.fields['compte'].queryset = comptes

	context = {"form": form, 'title': "Valider création agent saisie {}".format(agent.matricule, ), "gerant": agent}
	return render(request, template, context)


@method_decorator([user_role_required(Role.GERANT)], name='dispatch')
class AgentSaisieCDUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = AgentSaisieCD
	c = "agentsaisiecd"
	template_name = 'core/update_entity.html'
	form_class = UpdateAgentSaisieCDModelForm
	permission_required = ('cddaccount.change_{}'.format(c, ),)
	success_message = 'Success: Mise à jour agent de saisie compte de dépôt.'
	success_url = reverse_lazy('cddaccount:{}_list'.format(c, ))

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		comptes = CompteDepot.objects.by_agent(self.request.user)
		context['form'].fields["comptes"].queryset = comptes
		sigrole = SigRole.objects.get(role=Role.AGENT_SAISIE_CD)
		context['form'].fields["roles"].queryset = sigrole.groups.all()
		context['title'] = "Mise à jour de {} : {}".format(self.object._meta.verbose_name, self.object)
		return context

	def get_initial(self):
		initial = super().get_initial()
		ref = self.get_object()
		groups = ref.user.groups.all()
		a = [i.id for i in groups.all()]
		initial["roles"] = a
		return initial


	def form_valid(self, form):
		if not is_ajax(self.request.META):
			obj = form.save(commit=False)
			roles = form.cleaned_data["roles"]
			obj.user.groups.set(roles)
			form.save()

		return super().form_valid(form)


@login_required
@user_role_required(Role.AGENT_SAISIE_CD)
def complete_agentsaisiecd_data(request, pk):
	template = "cddaccount/complete_gerant.html"
	user = request.user
	gerant = get_object_or_404(AgentSaisieCD, id=pk)
	success_url = reverse_lazy('cddaccount:agentsaisiecd_profile_view', kwargs={"matricule": gerant.matricule})
	if gerant.user != user:
		raise Http404
	if gerant.account_is_valid() or gerant.status == STATUS_CREATION.ATTENTE:
		return redirect(success_url)
	if request.method == 'POST':
		form = AgentSaisieCDForm(request.POST, request.FILES)
		if form.is_valid():
			if request and not is_ajax(request.META):
				object = form.save(commit=False)

				gerant.nin = object.nin
				gerant.adresse = object.adresse
				gerant.is_actif = True

				gerant.status = STATUS_CREATION.VALIDE
				gerant.is_actif = True
				gerant.valide = True
				gerant.date_validation = datetime.datetime.now()

				gerant.save()
				messages.success(request, "Informations  soumises  en attente de validation")

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		form = AgentSaisieCDForm()

	context = {"form": form, 'title': "Compléter informations agent saisie {}".format(gerant.matricule, ), "gerant": gerant}
	return render(request, template, context)



@login_required
# @user_role_required("ADMIN")
def gestion_compte_depot_view(request):
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




@method_decorator([ user_role_required(Role.AGENT_PC)], name='dispatch')
class GestionCompteDepotCreateView(PermissionRequiredMixin,BSModalCreateView):
    model_name= "gestioncomptedepot"
    template_name = 'core/add_entity.html'
    form_class = AffectationGerantCDModelForm
    success_message = 'Success: Affectation avec succès.'
    success_url = reverse_lazy('cddaccount:gestioncomptedepot_list')
    permission_required = ('cddaccount.add_{}'.format(model_name,),)
    title="Nouvel affectation"

   # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


    def form_valid(self, form):
        if not is_ajax(self.request.META):
            #lower,upper= form.instance.period.start,form.instance.period.stop
            #rg = DateRange(lower.date(),upper.date())
            #form.instance.period=rg
            self.object = form.save(commit=False)
            self.object.agent_pc=self.request.user
            try:
	            form.save()
            except SigException as e:
	            messages.info(self.request,e.message)
	            return redirect(self.success_url)


            #form.instance.agent_pc = self.request.user
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        name= self.form_class._meta.model._meta.verbose_name
        comptes = get_comptes(self.request) #CompteDepot.objects.by_agent(self.request.user)

        context['form'].fields["compte"].queryset = comptes
        context['title'] = "Nouvel affectation gérant"
        return context



@method_decorator([ user_role_required(Role.AGENT_PC)], name='dispatch')
class GestionCompteDepotUpdateView(PermissionRequiredMixin,BSModalUpdateView):

    model = GestionCompteDepot
    template_name = 'core/update_entity.html'
    form_class = AffectationGerantCDModelForm
    permission_required = ('cddaccount.change_{}'.format(model._meta.model_name,),)
    success_message = 'Success: Mise à jour affectation.'
    success_url = reverse_lazy('cddaccount:gestioncomptedepot_list')
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        comptes = CompteDepot.objects.by_agent(self.request.user)

        context['form'].fields["compte"].queryset = comptes
        context['title'] = "Mise à jour affectation {} : {}".format(self.object._meta.verbose_name,self.object)
        return context



@method_decorator([ user_role_required(Role.AGENT_PC)], name='dispatch')
class GestionCompteDepotDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    model = GestionCompteDepot

    permission_required = ('cddaccount.delete_{}'.format(model._meta.model_name),)

    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_message = 'Success: Supression entité '
    success_url = reverse_lazy('cddaccount:gestioncomptedepot_list')

    template_name = "core/confirm_delete_entity.html"


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Suppression affectation : {}".format(self.object.name,)
        return context


@login_required
# @user_role_required("ADMIN")
def gestioncomptedepot_list_view(request):
	create_url = reverse_lazy('cddaccount:create_gestioncomptedepot')

	user = request.user
	queryset = GestionCompteDepot.objects.by_agent(user)
	queryset_filter = GestionCompteDepotFilter(request.GET, request=request, queryset=queryset)
	table = GestionCompteDepotTable(queryset_filter.qs, exclude=("action",), request=request)
	can_create_dcp = user.has_perm('cddaccount.add_gestioncomptedepot')
	if user.has_perm('cddaccount.change_gestioncomptedepot') or user.has_perm('cddaccount.delete_gestioncomptedepot'):
		table = GestionCompteDepotTable(queryset_filter.qs, request=request)
	title = _("Affectation gérant  Comptes de dépôts")
	data_title = _("Affectation gérant Comptes de dépôts")
	create_tilte="Nouvelle Affectation"

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'cddaccount/list_gerantcd.html',
	              {"create_tilte":create_tilte,"create_url": create_url, "can_create_agent": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})




@login_required
#@permission_required("cddaccount.sendsms_agentsaisiecd")
def send_sms(request, matricule):
	agent = get_object_or_404(AgentSaisieCD, matricule=matricule)
	agent.reset_pwd_for_agent(None)
	messages.info(request,"Mot de passe reinitialisé")

	return redirect(reverse('cddaccount:agentsaisiecd_list'))





@login_required
# @user_role_required("ADMIN")
def nature_list_view(request):
	create_url = reverse_lazy('cddaccount:create_nature')

	user = request.user
	queryset = Nature.objects.all()
	queryset_filter = NatureFilter(request.GET, request=request, queryset=queryset)
	table = NatureTable(queryset_filter.qs, exclude=("action",))
	can_create_dcp = user.has_perm('cddaccount.add_nature')
	if user.has_perm('cddaccount.change_nature') or user.has_perm('cddaccount.delete_nature'):
		table = NatureTable(queryset_filter.qs)
	title = _("Natures")
	data_title = _("Natures")
	create_tilte = "Nouvelle Nature"

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_tilte":create_tilte,"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})


@method_decorator([user_role_required(Role.ADMIN)], name='dispatch')
class NatureCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'core/add_entity.html'
	form_class = NatureForm
	model_name = form_class._meta.model._meta.model_name
	success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
	success_url = reverse_lazy('cddaccount:{}_list'.format(model_name, ))
	permission_required = ('cddaccount.add_{}'.format(model_name, ),)

	# @method_decorator(user_role_required("ADMIN"))
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def form_valid(self, form):
		if not is_ajax(self.request.META):
			pass
		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		name = self.form_class._meta.model._meta.verbose_name
		context['title'] = "Nouvelle {}".format(name, )
		return context


@method_decorator([user_role_required(Role.ADMIN)], name='dispatch')
class NatureDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	model = Nature
	permission_required = ('cddaccount.delete_nature',)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression nature'
	success_url = reverse_lazy('cddaccount:nature_list')

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Suppression entite : {}".format(self.object, )
		return context


@method_decorator([user_role_required(Role.ADMIN)], name='dispatch')
class NatureUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = Nature
	template_name = 'core/update_entity.html'
	form_class = NatureForm
	permission_required = ('cddaccount.change_nature',)
	success_message = 'Success: Mise à jour nature.'
	success_url = reverse_lazy('cddaccount:nature_list')

	# def has_permission(self):
	#    return self.request.user.is_active and self.request.user.is_staff

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Mise à jour de l' entité {} : {}".format(self.object._meta.verbose_name, self.object)
		return context






@login_required
# @user_role_required("ADMIN")
def anneecomptable_list_view(request):
	create_url = reverse_lazy('cddaccount:create_anneecomptable')

	user = request.user
	queryset = AnneeComptable.objects.all()
	queryset_filter = AnneeComptableFilter(request.GET, request=request, queryset=queryset)
	table = AnneeComptableTable(queryset_filter.qs, exclude=("action",))
	can_create_dcp = user.has_perm('cddaccount.add_anneecomptable')
	if user.has_perm('cddaccount.change_anneecomptable') or user.has_perm('cddaccount.delete_anneecomptable'):
		table = AnneeComptableTable(queryset_filter.qs)
	title = _("Années Comptables")
	data_title = _("Années Comptables")

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})


@method_decorator([user_role_required(Role.ADMIN)], name='dispatch')
class AnneeComptableCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'core/add_entity.html'
	form_class = AnneeComptableForm
	model_name = form_class._meta.model._meta.model_name
	success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
	success_url = reverse_lazy('cddaccount:{}_list'.format(model_name, ))
	permission_required = ('cddaccount.add_{}'.format(model_name, ),)

	# @method_decorator(user_role_required("ADMIN"))
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def form_valid(self, form):
		if not is_ajax(self.request.META):
			form.instance.createur=self.request.user
		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		name = self.form_class._meta.model._meta.verbose_name
		context['title'] = "Nouvelle Année Comptable"
		return context


@method_decorator([user_role_required(Role.ADMIN)], name='dispatch')
class AnneeComptableDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	model = AnneeComptable
	permission_required = ('cddaccount.delete_anneeaomptable',)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression AnneeComptable'
	success_url = reverse_lazy('cddaccount:anneeaomptable_list')

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Suppression  : {}".format(self.object, )
		return context


@method_decorator([user_role_required(Role.ADMIN)], name='dispatch')
class AnneeComptableUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model =AnneeComptable
	template_name = 'core/update_entity.html'
	form_class =AnneeComptableForm
	permission_required = ('cddaccount.change_anneecomptable',)
	success_message = 'Success: Mise à jour Année comptable.'
	success_url = reverse_lazy('cddaccount:anneecomptable_list')

	# def has_permission(self):
	#    return self.request.user.is_active and self.request.user.is_staff

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Mise à jour de l' entité {} : {}".format(self.object._meta.verbose_name, self.object)
		return context




@login_required
# @user_role_required("ADMIN")
def blocagefond_list_view(request):
	create_url = reverse_lazy('cddaccount:create_anneecomptable')

	user = request.user
	queryset = BlocageFond.objects.by_agent(user).prefetch_related("compte")
	queryset_filter = BlocageFondFilter(request.GET, request=request, queryset=queryset)
	table = BlocageFondTable(queryset_filter.qs, exclude=("action","reference"))

	if hasattr(user,"agent_postecomptable"):
		table = BlocageFondTable(queryset_filter.qs, exclude=("action",))
	can_create_dcp = user.has_perm('cddaccount.add_anneecomptable')
	if user.has_perm('cddaccount.change_anneecomptable') or user.has_perm('cddaccount.delete_anneecomptable'):
		table = BlocageFondTable(queryset_filter.qs)
	title = _("Blocage Fond")
	data_title = _("Blocage Fond")

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'cddaccount/list_blocage.html',
	              {"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})


@method_decorator([user_role_required(Role.AGENT_PC)], name='dispatch')
class BlocageFondCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'core/add_entity.html'
	form_class = BlocageFondForm
	model_name = form_class._meta.model._meta.model_name
	success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
	success_url = reverse_lazy('cddaccount:{}_list'.format(model_name, ))
	permission_required = ('cddaccount.add_{}'.format(model_name, ),)

	# @method_decorator(user_role_required("ADMIN"))
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def form_valid(self, form):
		if not is_ajax(self.request.META):
			pass
		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		name = self.form_class._meta.model._meta.verbose_name
		context['title'] = "Nouvel  {}".format(name, )
		return context


@method_decorator([user_role_required(Role.AGENT_PC)], name='dispatch')
class BlocageFondDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	model = BlocageFond
	permission_required = ('cddaccount.delete_blocagefond',)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression BlocageFond'
	success_url = reverse_lazy('cddaccount:bblocagefond_list')

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Suppression  : {}".format(self.object, )
		return context


@method_decorator([user_role_required(Role.AGENT_PC)], name='dispatch')
class BlocageFondUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = BlocageFond
	template_name = 'core/update_entity.html'
	form_class = NatureForm
	permission_required = ('cddaccount.change_blocagefond',)
	success_message = 'Success: Mise à jour BlocageFond.'
	success_url = reverse_lazy('cddaccount:blocagefond_list')

	# def has_permission(self):
	#    return self.request.user.is_active and self.request.user.is_staff

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Mise à jour de l' entité {} : {}".format(self.object._meta.verbose_name, self.object)
		return context



@login_required
@user_role_required(Role.AGENT_DCP)
@permission_required('cddaccount.add_activationcompte', raise_exception=True)
def activer_comptedepot(request, id):
	template = "cddaccount/validate.html"
	user = request.user
	success_url = reverse_lazy('cddaccount:comptedepot_list')
	compte = get_object_or_404(CompteDepot, id=id)
	delete_notificationcdd(compte, user)
	if request.method == 'POST':
		form = ActiverCompteDepotModelForm(request.POST)
		if form.is_valid():
			if request and not is_ajax(request.META):

				compte.actif = form.cleaned_data['actif']

				messages.info(request, "Operation effectuée avec succès")

				compte.save()
			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		form = ActiverCompteDepotModelForm(instance=compte)

	context = {"form": form, 'title': "Activer/Desactiver {}".format(compte.compte, ), "compte": compte}
	return render(request, template, context)






from psycopg2.extras import DateRange
#@method_decorator([user_role_required(Role.AGENT_PC)], name='dispatch')
class ReportCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'core/add_entity.html'
	form_class = ReportForm
	model_name = form_class._meta.model._meta.model_name
	success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
	success_url = reverse_lazy('cddaccount:{}_list'.format(model_name, ))
	permission_required = ('cddaccount.add_{}'.format(model_name, ),)

	# @method_decorator(user_role_required("ADMIN"))
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def form_valid(self, form):
		if not is_ajax(self.request.META):
			self.object = form.save(commit=False)
			self.object.creator = self.request.user
			self.object.gestion_courant=AnneeComptable.active_gestion()
			self.object.sens=SENS_TRX.CREDIT

			self.object.anne_comptable=self.object.gestion_courant.parent
			self.object.created = datetime.datetime.now()

			form.save()

		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		name = self.form_class._meta.model._meta.verbose_name
		context['title'] = "Nouveau  {}".format(name, )
		#context['form'].fields["anne_comptable"].queryset = AnneeComptable.objects.filter(actif=False)
		return context

	def get_initial(self):
		initial = super().get_initial()
		initial["amount"] = Decimal(0)
		return initial


#@method_decorator([user_role_required(Role.AGENT_PC)], name='dispatch')
class ReportDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	model = ReportGestion
	permission_required = ('cddaccount.delete_reportgestion',)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression repoort'
	success_url = reverse_lazy('cddaccount:reportgestion_list')

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Suppression  : {}".format(self.object, )
		return context


class ReportUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = ReportGestion
	template_name = 'core/update_entity.html'
	form_class = ReportForm
	permission_required = ('cddaccount.change_reportgestion',)
	success_message = 'Success: Mise à jour BlocageFond.'
	success_url = reverse_lazy('cddaccount:reportgestion_list')

	# def has_permission(self):
	#    return self.request.user.is_active and self.request.user.is_staff

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Mise à jour  {} : {}".format(self.object._meta.verbose_name, self.object)
		#context['form'].fields["anne_comptable"].queryset = AnneeComptable.objects.filter(actif=False)
		return context


	def get_initial(self):
		initial = super().get_initial()


		# etc...
		return initial







@login_required
# @user_role_required("ADMIN")
def report_list_view(request):
	create_url = reverse_lazy('cddaccount:create_reportgestion')

	user = request.user
	queryset = ReportGestion.objects.by_agent(user)
	queryset_filter = ReportGestionFilter(request.GET, request=request, queryset=queryset)
	table = ReportGestionTable(queryset_filter.qs, exclude=("action",))
	can_create_dcp = user.has_perm('cddaccount.add_reportgestion')
	if user.has_perm('cddaccount.change_reportgestion') or user.has_perm('cddaccount.delete_reportgestion'):
		table = ReportGestionTable(queryset_filter.qs)
	title = _("Reports")
	data_title = _("Reports")
	create_tilte="Nouveau report"

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_tilte":create_tilte,"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})



@login_required
@user_role_required([Role.GERANT,Role.AGENT_SAISIE_CD])
def select_cddaccount_for_work_view(request):
	template = "cddaccount/chose_cdd.html"
	user = request.user
	comptes=CompteDepot.objects.by_agent(user)

	if hasattr(user, "gerant_cd") == True:
		success_url = user.gerant_cd.get_absolute_url()
	elif hasattr(user, Role.AGENT_SAISIE_CD.lower()) == True:
		success_url = user.agent_saisie_cd.get_absolute_url()
	else:success_url = None

	try:
		key= request.session["select_cddacc_user_id"]
		return redirect(success_url)
	except KeyError:
		pass

	if request.method == 'POST':
		form = ChoseCddAccountForm(request.POST, request.FILES)
		form.fields['compte'].queryset = comptes
		if form.is_valid():
			if request and not is_ajax(request.META):

				compte=form.cleaned_data["compte"]

				request.session["select_cddacc_user_id"] = str(compte.id)
				messages.success(request, "Votre compte est actif")

			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		form = ChoseCddAccountForm()
		form.fields['compte'].queryset = comptes

	context = {"form": form, 'title': "Sélectionner le compte de dépôt ?"}
	return render(request, template, context)


@login_required
# @user_role_required("ADMIN")
def sousnature_list_view(request):
	create_url = reverse_lazy('cddaccount:create_sousnature')

	user = request.user
	queryset = SousNature.objects.all()
	queryset_filter = SousNatureFilter(request.GET, request=request, queryset=queryset)
	table = SousNatureTable(queryset_filter.qs, exclude=("action",))
	can_create_dcp = user.has_perm('cddaccount.add_sousnature')
	if user.has_perm('cddaccount.change_sousnature') or user.has_perm('cddaccount.delete_sousnature'):
		table = SousNatureTable(queryset_filter.qs)
	title = _("Sous Natures")
	data_title = _("Sous Natures")
	create_tilte = "Nouvelle Sous Nature"

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_tilte":create_tilte,"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})



@method_decorator([user_role_required(Role.ADMIN)], name='dispatch')
class SousNatureCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'core/add_entity.html'
	form_class = SousNatureForm
	model_name = form_class._meta.model._meta.model_name
	success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
	success_url = reverse_lazy('cddaccount:{}_list'.format(model_name, ))
	permission_required = ('cddaccount.add_{}'.format(model_name, ),)

	# @method_decorator(user_role_required("ADMIN"))
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def form_valid(self, form):
		if not is_ajax(self.request.META):
			pass
		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		name = self.form_class._meta.model._meta.verbose_name
		context['title'] = "Nouvelle {}".format(name, )
		return context


@method_decorator([user_role_required(Role.ADMIN)], name='dispatch')
class SousNatureDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	model = SousNature
	permission_required = ('cddaccount.delete_nature',)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression sous nature'
	success_url = reverse_lazy('cddaccount:sousnature_list')

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Suppression entite : {}".format(self.object, )
		return context


@method_decorator([user_role_required(Role.ADMIN)], name='dispatch')
class SousNatureUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = SousNature
	template_name = 'core/update_entity.html'
	form_class = SousNatureForm
	permission_required = ('cddaccount.change_sousnature',)
	success_message = 'Success: Mise à jour sous nature.'
	success_url = reverse_lazy('cddaccount:sousnature_list')

	# def has_permission(self):
	#    return self.request.user.is_active and self.request.user.is_staff

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Mise à jour de l' entité {} : {}".format(self.object._meta.verbose_name, self.object)
		return context



@method_decorator([user_role_required(Role.GERANT)], name='dispatch')
class MandataireCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'core/add_entity.html'
	form_class = MandataireModelForm
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
			# obj.fonction = Role.AGENT_SAISIE_CD
			obj.gerant = self.request.user.gerant_cd
		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		# context['form'].fields["comptes"].queryset= get_cdd_with_gerant(self.request)#CompteDepot.objects.by_agent(self.request.user)
		name = self.form_class._meta.model._meta.verbose_name
		context['title'] = "Nouveau mandataire"
		return context
@method_decorator([user_role_required(Role.GERANT)], name='dispatch')
class MandataireDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	c = "mandataire"
	model = Mandataire
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
class MandataireUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = Mandataire
	c = "mandataire"
	template_name = 'core/update_entity.html'
	form_class = MandataireModelForm
	permission_required = ('cddaccount.change_{}'.format(c, ),)
	success_message = 'Success: Mise à jour agent de saisie compte de dépôt.'
	success_url = reverse_lazy('cddaccount:{}_list'.format(c, ))

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		# context['form'].fields["gerant"].queryset = GerantCD.objects.by_agent(self.request.user)
		context['title'] = "Mise à jour de {} : {}".format(self.object._meta.verbose_name, self.object)
		return context
@login_required
# @user_role_required("ADMIN")
def mandataires_list_view(request):
	user =request.user
	create_url = reverse_lazy('cddaccount:create_mandataire')

	user = request.user
	queryset = Mandataire.objects.by_agent(user)
	queryset_filter = MandataireFilter(request.GET, request=request, queryset=queryset)
	table = MandataireTable(queryset_filter.qs, exclude=("action",))
	can_create_dcp = user.has_perm('cddaccount.add_mandataire')
	if user.has_perm('cddaccount.change_mandataire') or user.has_perm('cddaccount.delete_mandataire'):
		table = MandataireTable(queryset_filter.qs)
	title = _("Mandataires")
	data_title = _("Mandataires")
	create_tilte = "Nouveau Mandataire"

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_tilte":create_tilte,"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})





@login_required
@user_role_required(Role.AGENT_PC)
def delete_pc_opwith_validate_status(request, pk):
	template = "core/confirm_delete_entity.html"
	user = request.user
	ordre = get_object_or_404(OrdrePayment, id=pk)
	success_url = reverse_lazy('cddaccount:ordrepayment_list')
	if ordre.creator != user:
		raise Http404

	if request.method == 'POST':
		form = DeleteOPByPCForm(request.POST)
		if form.is_valid():
			if request and not is_ajax(request.META):
				object = form.save(commit=False)

				try:
					delete_a_validate_op_initiate_by_pc(ordre,user)
					messages.success(request,"Opération suppprimée")
				except SigException as e:
					messages.error(request, e.message)


			return redirect(success_url)
		else:
			for field in form:
				if field.errors:
					for error in field.errors:
						meg = '{}({})'.format(error, field.html_name)
						messages.error(request, meg)
	else:
		form = DeleteOPByPCForm(initial={"id":pk})

	context = {"form": form, 'title': "Suppression Opération ", "object": ordre}
	return render(request, template, context)






@login_required
# @user_role_required("ADMIN")
def opvirements_list_view(request):
	return default_ordrepayment_list_view(request, PAYMENT_MEAN_TYPE.VIREMENT)


@login_required
# @user_role_required("ADMIN")
def opcheques_list_view(request):
	return default_ordrepayment_list_view(request, PAYMENT_MEAN_TYPE.CHEQUE)


@login_required
# @user_role_required("ADMIN")
def ordrepayment_list_view(request):
	paymentmean = PAYMENT_MEAN_TYPE.CHEQUE
	return default_ordrepayment_list_view(request, None)


@login_required
# @user_role_required("ADMIN")
def default_ordrepayment_list_view(request, paymentmean):
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

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_url": create_url, "can_create_op": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})
















class TypeCompteTrxCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'core/add_entity.html'
	form_class = TypeCompteTrxModelForm
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
			# obj.fonction = Role.AGENT_SAISIE_CD
		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		# context['form'].fields["comptes"].queryset= get_cdd_with_gerant(self.request)#CompteDepot.objects.by_agent(self.request.user)
		name = self.form_class._meta.model._meta.verbose_name
		context['title'] = "Nouveau type de compte transactionnel"
		return context

class TypeCompteTrxDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	c = "typecomptetrx"
	model = Mandataire
	permission_required = ('cddaccount.delete_{}'.format(c, ),)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression agent de saisie compte de dépôt'
	success_url = reverse_lazy('cddaccount:{}_list'.format(c, ))

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Suppression  : {}".format(self.object, )
		return context

class TypeCompteTrxUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = TypeCompteTrx
	c = "typecomptetrx"
	template_name = 'core/update_entity.html'
	form_class = TypeCompteTrxModelForm
	permission_required = ('cddaccount.change_{}'.format(c, ),)
	success_message = 'Success: Mise à jour.'
	success_url = reverse_lazy('cddaccount:{}_list'.format(c, ))

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		# context['form'].fields["gerant"].queryset = GerantCD.objects.by_agent(self.request.user)
		context['title'] = "Mise à jour de {} : {}".format(self.object._meta.verbose_name, self.object)
		return context
@login_required
# @user_role_required("ADMIN")
def typecomptetrx_list_view(request):
	user =request.user
	create_url = reverse_lazy('cddaccount:create_typecomptetrx')

	user = request.user
	queryset = TypeCompteTrx.objects.all()
	table =TypeCompteTrxTable(queryset, exclude=("action",))
	can_create_dcp = user.has_perm('cddaccount.add_typecomptetrx')
	if user.has_perm('cddaccount.change_typecomptetrx') or user.has_perm('cddaccount.delete_typecomptetrx'):
		table = TypeCompteTrxTable(queryset)
	title = _("type compte transactionnel")
	data_title = _("type compte transactionnel")
	create_tilte = "Nouveau type compte transactionnel"

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_tilte":create_tilte,"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "title": title, "index": "0", "sens": "desc"})






class CompteTrxUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = CompteTrx
	template_name = 'core/update_entity.html'
	form_class = CompteTrxModelForm
	permission_required = ('cddaccount.change_comptetrx',)
	success_message = 'Success: Mise à jour BlocageFond.'
	success_url = reverse_lazy('cddaccount:comptetrx_list')

	# def has_permission(self):
	#    return self.request.user.is_active and self.request.user.is_staff

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Mise à jour  {} : {}".format(self.object._meta.verbose_name, self.object)
		#context['form'].fields["anne_comptable"].queryset = AnneeComptable.objects.filter(actif=False)
		return context


	def get_initial(self):
		initial = super().get_initial()

		# etc...
		return initial



@login_required
# @user_role_required("ADMIN")
@permission_required("cddaccount.view_comptetrx", raise_exception=True)
def comptetrx_list_view(request):
	user =request.user
	create_url = reverse_lazy('cddaccount:create_typecomptetrx')

	user = request.user
	queryset = CompteTrx.objects.all().prefetch_related("compte","type","gestion")
	queryset_filter = CompteTrxFilter(request.GET, request=request, queryset=queryset)
	table =CompteTrxTable(queryset_filter.qs, exclude=("action",))
	can_create_dcp = False
	if user.has_perm('cddaccount.change_comptetrx') :
		table = CompteTrxTable(queryset_filter.qs)
	title = _("Compte à reporter ")
	data_title = _("type compte transactionnel")
	create_tilte = "Nouveau  compte transactionnel"

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_tilte":create_tilte,"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "title": title, "index": "0", "sens": "desc","filter_form": queryset_filter.form})


@login_required
# @user_role_required("ADMIN")
@permission_required("cddaccount.view_demandeop", raise_exception=True)
def demandeop_list_view(request):
	user =request.user
	create_url = reverse_lazy('cddaccount:create_demandeop')


	user = request.user
	queryset = DemandeOP.objects.all().prefetch_related("compte","typecompte","gestion")
	queryset_filter = DemandeOPFilter(request.GET, request=request, queryset=queryset)
	table =DemandeOPTable(queryset_filter.qs, exclude=("action",))
	can_create_dcp = user.has_perm('cddaccount.add_demandeop')
	if user.has_perm('cddaccount.change_demandeop') :
		table = DemandeOPTable(queryset_filter.qs)
	title = _("Demande OP ")
	data_title = _("Demande OP ")
	create_tilte = "Nouvelle Demande OP "

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_tilte":create_tilte,"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "title": title, "index": "0", "sens": "desc","filter_form": queryset_filter.form})



class DemandeOPUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = DemandeOP
	template_name = 'core/update_entity.html'
	form_class = DemandeOPModelForm
	permission_required = ('cddaccount.change_demandeop',)
	success_message = 'Success: Mise à jour demande op.'
	success_url = reverse_lazy('cddaccount:demandeop_list')

	# def has_permission(self):
	#    return self.request.user.is_active and self.request.user.is_staff

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Mise à jour  {} : {}".format(self.object._meta.verbose_name, self.object)
		#context['form'].fields["anne_comptable"].queryset = AnneeComptable.objects.filter(actif=False)
		return context


	def get_initial(self):
		initial = super().get_initial()

		# etc...
		return initial



class DemandeOPDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	c = "demanndeop"
	model = DemandeOP
	permission_required = ('cddaccount.delete_{}'.format(c, ),)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression agent de saisie compte de dépôt'
	success_url = reverse_lazy('cddaccount:{}_list'.format(c, ))

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Suppression  : {}".format(self.object, )
		return context


class DemandeOPCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'cddaccount/add_demande_op.html'
	form_class = DemandeOPModelForm
	model_name = form_class._meta.model._meta.model_name
	success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
	success_url = reverse_lazy('cddaccount:{}_list'.format(model_name, ))
	permission_required = ('cddaccount.add_{}'.format(model_name, ),)

	# @method_decorator(user_role_required("ADMIN"))
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def form_valid(self, form):
		user = self.request.user
		if not is_ajax(self.request.META):
			context = self.get_context_data()
			self.object = form.save(commit=False)
			self.object.compte = CompteDepot.objects.get(id=int(context["account"]))
			self.object.creator = user
			# obj.fonction = Role.AGENT_SAISIE_CD
		return super().form_valid(form)




	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)

		try:
			id_compte = self.request.session["select_cddacc_user_id"]
			context["account"] = id_compte
			id_compte = self.kwargs["pk"]
			compte = get_object_or_404(CompteDepot, id=id_compte)
			context['title'] = "Nouvelle demande OP{}({})".format(compte.libelle_court, compte.short_compte)


			x = compte.get_current_gerant()

			if x: context["gerant_fullname"] = x.full_name()

			# context['form'].fields["type_nature"].choices = compte.types_account()
			context['form'].fields['amount'].min_value = 0
			context['form'].fields['amount'].max_value = int(compte.balance.amount)
		except:
			pass


		return context

	def get_initial(self):
		initial = super().get_initial()
		# Copy the dictionary so we don't accidentally change a mutable dict
		initial = initial.copy()
		try:
			key = self.request.session["select_cddacc_user_id"]
			initial['account'] = key
			initial["gestion"] = AnneeComptable.current_gestion().id

		except:
			pass

		return initial