import traceback
from django.contrib import messages
from bootstrap_modal_forms.utils import is_ajax
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django_tables2 import RequestConfig


from cddaccount.models import  Projet, AvisDeDebit, AvisDeCredit,BlocageFond
from cddaccount.process import CddProcessManager
from helpers.decorators import user_role_required
from helpers.models import Role
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa


# import generic UpdateView
import logging

logger = logging.getLogger(__name__)
from cddaccount.forms import AvisDeDebitForm, AvisDeCreditForm

from cddaccount.tables import AvisDeCreditFilter, AvisDeDebitFilter, AvisDeCreditTable, AvisDeDebitTable
from  cddaccount.views import get_cdd_with_gerant,PAGINATION_SIZE
# Relative import of GeeksModel
from bootstrap_modal_forms.generic import (
	BSModalUpdateView,
	BSModalCreateView, BSModalDeleteView
)

from helpers.exceptions import SigException


@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def temlate_avisdebit_view(request, reference):
	template = "cddaccount/avis_template.html"
	user = request.user
	ordre = get_object_or_404(AvisDeDebit, reference=reference)
	iban_items = ordre.compte.benef_iban_items()
	journee_comptable = ordre.jour_comptable.day()
	gestion = ordre.jour_comptable.year()

	if not ordre.can_acces(user):
		raise Http404
	create_url = None
	gerant = None

	title = "AVIS DE DEBIT N° {}".format(ordre.reference_aster)

	compte = ordre.compte

	context = {"gestion": gestion, "journee_comptable": journee_comptable, "compte": compte, "ordre": ordre,
	           "agent": gerant, 'title': title, "iban_items": iban_items}
	return render(request, template, context)


@login_required
def temlate_avisdebit_view_pdf(request, reference):
	template = "cddaccount/avis_template_pdf.html"
	user = request.user
	ordre = get_object_or_404(AvisDeDebit, reference=reference)
	iban_items = ordre.compte.benef_iban_items()
	journee_comptable = ordre.jour_comptable.day()
	gestion = ordre.jour_comptable.year()

	if not ordre.can_acces(user):
		raise Http404
	create_url = None
	gerant = None

	title = "AVIS DE DEBIT N° {}".format(ordre.reference_aster)

	compte = ordre.compte

	context = {"gestion": gestion, "journee_comptable": journee_comptable, "compte": compte, "ordre": ordre,
	           "agent": gerant, 'title': title, "iban_items": iban_items}
	gettemplate = get_template(template)
	html = gettemplate.render(context)
	result = BytesIO()
	pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
	if pdf.err:
		return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
	return HttpResponse(result.getvalue(), content_type='application/pdf')


@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def template_aviscredit_view(request, reference):
	template = "cddaccount/avis_credit_template.html"
	user = request.user
	ordre = get_object_or_404(AvisDeCredit, reference=reference)
	iban_items = ordre.compte.benef_iban_items()
	journee_comptable = ordre.jour_comptable.day()
	gestion = ordre.jour_comptable.year()

	if not ordre.can_acces(user):
		raise Http404
	create_url = None
	gerant = None

	compte = ordre.compte
	title = "AVIS DE CREDIT N° {}".format(ordre.reference_aster)

	context = {"gestion": gestion, "journee_comptable": journee_comptable, "compte": compte, "ordre": ordre,
	           "agent": gerant, 'title': title.format(ordre.reference, ), "iban_items": iban_items}
	return render(request, template, context)


@login_required
def template_aviscredit_view_pdf(request, reference):
	template = "cddaccount/avis_credit_template_pdf.html"
	user = request.user
	ordre = get_object_or_404(AvisDeCredit, reference=reference)
	iban_items = ordre.compte.benef_iban_items()
	journee_comptable = ordre.jour_comptable.day()
	gestion = ordre.jour_comptable.year()

	if not ordre.can_acces(user):
		raise Http404
	create_url = None
	gerant = None

	compte = ordre.compte
	title = "AVIS DE CREDIT N° {}".format(ordre.reference_aster)

	context = {"gestion": gestion, "journee_comptable": journee_comptable, "compte": compte, "ordre": ordre,
	           "agent": gerant, 'title': title.format(ordre.reference, ), "iban_items": iban_items}
	gettemplate = get_template(template)
	html = gettemplate.render(context)
	result = BytesIO()
	pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
	if pdf.err:
		return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
	return HttpResponse(result.getvalue(), content_type='application/pdf')


@login_required
# @user_role_required("ADMIN")
def avisdedebit_list_view(request):
	user = request.user
	create_url = None
	queryset = AvisDeDebit.objects.by_agent(user)
	if hasattr(user, "gerant_cd"):
		try:
			key = request.session["select_cddacc_user_id"]
			queryset = queryset.filter(compte_id=int(key))
		except KeyError:
			pass
	queryset_filter = AvisDeDebitFilter(request.GET, request=request, queryset=queryset)
	can_create_dcp = user.has_perm('cddaccount.add_avisdedebit') and not AvisDeDebit.check_if_api_open()
	if can_create_dcp:
		create_url = reverse_lazy('cddaccount:create_avisdedebit')

	table = AvisDeDebitTable(queryset_filter.qs, request=request, exclude=("action",))
	if user.has_perm('cddaccount.add_avisdedebit') and user.has_perm('cddaccount.change_avisdedebit'):
		table = AvisDeDebitTable(queryset_filter.qs, request=request)
	title = _("Liste de Avis de débit")
	data_title = _("Liste de Avis de débit")
	create_tilte = "Nouvel Avis de débit"

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc",
	               "create_tilte": create_tilte})


@login_required
# @user_role_required("ADMIN")
def avisdecredit_list_view(request):
	user = request.user
	create_url = None
	queryset = AvisDeCredit.objects.by_agent(user)
	if hasattr(user, "gerant_cd"):
		try:
			key = request.session["select_cddacc_user_id"]
			queryset = queryset.filter(compte_id=int(key))
		except KeyError:
			pass

	queryset_filter = AvisDeCreditFilter(request.GET, request=request, queryset=queryset)
	can_create_dcp = user.has_perm('cddaccount.add_avisdecredit') and not AvisDeCredit.check_if_api_open()
	if can_create_dcp:
		create_url = reverse_lazy('cddaccount:create_avisdecredit')

	table = AvisDeCreditTable(queryset_filter.qs, request=request, exclude=("action",))
	if user.has_perm('cddaccount.add_avisdecredit') and user.has_perm('cddaccount.change_avisdecredit'):
		table = AvisDeCreditTable(queryset_filter.qs, request=request)
	title = _("Liste des Avis de crédit")
	data_title = _("Liste des Avis de crédit")
	create_tilte = "Nouvel Avis de Crédit"

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc",
	               "create_tilte": create_tilte})


@method_decorator([user_role_required(Role.AGENT_PC)], name='dispatch')
class AvisDeCreditCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'cddaccount/add_avis.html'
	form_class = AvisDeCreditForm
	model_name = form_class._meta.model._meta.model_name
	success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
	success_url = reverse_lazy('cddaccount:{}_list'.format(model_name, ))
	permission_required = ('cddaccount.add_{}'.format(model_name, ),)

	def get(self, request, *args, **kwargs):
		if AvisDeCredit.check_if_api_open():
			msg = "Api disponible pour les avis de crédit"
			messages.success(request, msg)
			return redirect(self.success_url)

		return super().get(request, *args, **kwargs)

	# @method_decorator(user_role_required("ADMIN"))
	def dispatch(self, *args, **kwargs):
		return super().dispatch(*args, **kwargs)

	def form_valid(self, form):
		if not is_ajax(self.request.META):
			# object = form.save(commit=False)
			self.object = form.save(commit=False)
			with transaction.atomic():
				self.object.jour_comptable = self.request.user.journee_comptables.filter(actif=True).last()
				self.object.createur = self.request.user
				self.object.origin_reference = self.object.reference_aster
				try:
					form.save()

					CddProcessManager.send_aviscredit_trx_aster(self.request.user, self.object)

				except SigException as e:
					traceback.print_exc()
					msg = e.message
					messages.error(self.request, msg, extra_tags="danger")
					return redirect(self.success_url)

		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		comptes = get_cdd_with_gerant(self.request)  # CompteDepot.objects.by_agent(self.request.user)
		context['form'].fields["compte"].queryset = comptes
		# context['form'].fields["provenance"].queryset = comptes
		blocages = BlocageFond.objects.by_agent(self.request.user)
		# context['form'].fields["bocagefond"].queryset = blocages
		name = self.form_class._meta.model._meta.verbose_name
		context['title'] = "Nouvel {}".format(name, )
		return context


@method_decorator([user_role_required(Role.AGENT_PC)], name='dispatch')
class AvisDeCreditDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	model = AvisDeCredit
	permission_required = ('cddaccount.delete_avisdecredit',)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression avis de credit'
	success_url = reverse_lazy('cddaccount:avisdecredit_list')

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)

		context['title'] = "Suppression  : {}".format(self.object, )
		return context


@method_decorator([user_role_required(Role.AGENT_PC)], name='dispatch')
class AvisDeDebitCreateView(PermissionRequiredMixin, BSModalCreateView):
	template_name = 'cddaccount/add_avis.html'
	form_class = AvisDeDebitForm
	model_name = form_class._meta.model._meta.model_name
	success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
	success_url = reverse_lazy('cddaccount:{}_list'.format(model_name, ))
	permission_required = ('cddaccount.add_{}'.format(model_name, ),)

	def get(self, request, *args, **kwargs):
		if AvisDeDebit.check_if_api_open():
			msg = "Api disponible pour les avis de debit"
			messages.success(request, msg)
			return redirect(self.success_url)

		return super().get(request, *args, **kwargs)

	# @method_decorator(user_role_required("ADMIN"))
	def dispatch(self, *args, **kwargs):
		a = super().dispatch(*args, **kwargs)
		return a

	def form_valid(self, form):
		if not is_ajax(self.request.META):
			self.object = form.save(commit=False)
			with transaction.atomic():
				self.object.jour_comptable = self.request.user.journee_comptables.filter(actif=True).last()
				self.object.createur = self.request.user
				self.object.origin_reference = self.object.reference_aster
				try:
					form.save()
					CddProcessManager.send_avisdebit_trx_aster(self.request.user, self.object)

				except SigException as e:
					traceback.print_exc()
					msg = e.message
					messages.error(self.request, msg, extra_tags="danger")
					return redirect(self.success_url)

		return super().form_valid(form)

	def get_context_data(self, *args, **kwargs):
		# raise Http404
		context = super().get_context_data(*args, **kwargs)
		comptes = get_cdd_with_gerant(self.request)  # CompteDepot.objects.by_agent(self.request.user)
		context['form'].fields["compte"].queryset = comptes
		blocages = Projet.objects.by_agent(self.request.user)
		context['form'].fields["projet"].queryset = blocages
		name = self.form_class._meta.model._meta.verbose_name
		context['title'] = "Nouvel  {}".format(name, )
		return context


@method_decorator([user_role_required(Role.AGENT_PC)], name='dispatch')
class AvisDeDebitDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	model = AvisDeDebit
	permission_required = ('cddaccount.delete_avisdedebit',)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression avis de debit'
	success_url = reverse_lazy('cddaccount:avisdedebit_list')

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Suppression  : {}".format(self.object, )
		return context


@method_decorator([user_role_required(Role.AGENT_PC)], name='dispatch')
class AvisDeDebitUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = AvisDeDebit
	template_name = 'core/update_entity.html'
	form_class = AvisDeDebitForm
	permission_required = ('cddaccount.change_avisdedebit',)
	success_message = 'Success: Mise à jour avis de debit.'
	success_url = reverse_lazy('cddaccount:avisdedebit_list')

	# def has_permission(self):
	#    return self.request.user.is_active and self.request.user.is_staff

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		comptes = get_cdd_with_gerant(self.request)  # CompteDepot.objects.by_agent(self.request.user)
		context['form'].fields["compte"].queryset = comptes
		context['title'] = "Mise à jour {} : {}".format(self.object._meta.verbose_name, self.object)
		return context


@method_decorator([user_role_required(Role.AGENT_PC)], name='dispatch')
class AvisDeCreditUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = AvisDeCredit
	template_name = 'core/update_entity.html'
	form_class = AvisDeCreditForm
	permission_required = ('cddaccount.change_avisdecredit',)
	success_message = 'Success: Mise à jour avis de credit.'
	success_url = reverse_lazy('cddaccount:avisdecredit_list')

	# def has_permission(self):
	#    return self.request.user.is_active and self.request.user.is_staff

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		comptes = get_cdd_with_gerant(self.request)  # CompteDepot.objects.by_agent(self.request.user)
		context['form'].fields["compte"].queryset = comptes
		# context['form'].fields["provenance"].queryset = comptes
		context['title'] = "Mise à jour {} : {}".format(self.object._meta.verbose_name, self.object)
		return context

