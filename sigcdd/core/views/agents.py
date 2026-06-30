from bootstrap_modal_forms.utils import is_ajax
from django.contrib.auth.base_user import BaseUserManager
from django_tables2 import RequestConfig
from django.shortcuts import render
from django.urls import reverse_lazy
from core.models import TG,DCP,Agent,AffectationAgent,PosteComptable,ProfileDCP,ProfilePC
from users.models import User
from core.tables import Group,GroupFilter,GroupTable,TGTable,TGFilter, PosteComptableFilter,PosteComptableTable, DCPFilter,DCPTable,ProfileDCPFilter,ProfilePCFilter,AffectationAgentTable,AffectationAgentFilter,ProfilePCTable,ProfileDCPTable
from django.contrib.auth.decorators import login_required
from helpers.decorators  import user_role_required
from django.utils.decorators import method_decorator
from django.shortcuts import render,redirect,get_object_or_404
from django.utils.translation import gettext_lazy as _
from helpers.models import Role, SigRole
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from psycopg2.extras import DateRange
PAGINATION_SIZE=100

default_currency="F CFA"
# import generic UpdateView
from django.views.generic.edit import DeleteView


from core.forms import ProfilePCModelForm,ProfileDCPModelForm,AffectationAgentModelForm,GroupModelForm

# Relative import of GeeksModel
from bootstrap_modal_forms.generic import (
    BSModalLoginView,
    BSModalFormView,BSModalDeleteView,
    BSModalCreateView,BSModalUpdateView
)



@login_required
#@user_role_required("ADMIN")
def agent_pc_list_view(request):
    user=request.user
    c="profilepc"
    create_url = reverse_lazy('core:create_profilepc')
    queryset = ProfilePC.objects.by_agent(user)
    queryset_filter = ProfilePCFilter(request.GET, request=request, queryset=queryset)
    table = ProfilePCTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('core.add_{}'.format(c,))
    if user.has_perm('core.change_{}'.format(c,)) or user.has_perm('core.delete_{}'.format(c,)):
        table = ProfilePCTable(queryset_filter.qs)
    title = _("LISTE AGENT POSTE COMPTABLE")
    data_title=_("LISTE AGENT POSTE COMPTABLE")


    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'core/agent_list.html', {"can_create_agent":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc","create_url":create_url})



@login_required
#@user_role_required("ADMIN")
def agent_dcp_list_view(request):
    user=request.user
    c="profiledcp"
    create_url = reverse_lazy('core:create_profiledcp')
    queryset = ProfileDCP.objects.all()
    queryset_filter = ProfileDCPFilter(request.GET, request=request, queryset=queryset)
    table = ProfileDCPTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('core.add_{}'.format(c,))
    if user.has_perm('core.change_{}'.format(c,)) or user.has_perm('core.delete_{}'.format(c,)):
        table = ProfileDCPTable(queryset_filter.qs)
    title = _("LISTE AGENTS DCP")
    data_title=_("LISTE AGENTS DCP")

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'core/agent_list.html', {"can_create_agent":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc","create_url":create_url})



from django.contrib import messages
@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class ProfileDCPCreateView(PermissionRequiredMixin,BSModalCreateView):
    c = "profiledcp"
    template_name = 'core/add_entity.html'
    form_class = ProfileDCPModelForm
    success_message = 'Success: Création entité agent.'
    success_url = reverse_lazy('core:{}_list'.format(c,))
    permission_required = ('core.add_{}'.format(c,),)
    title="Nouveau agent"

   # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


    def form_valid(self, form):

        if not is_ajax(self.request.META):
            obj = form.save(commit=False)
            roles=form.cleaned_data["roles"]
            try:
                obj.fonction=Role.AGENT_DCP
                obj.creator=self.request.user
                obj.dcp=DCP.object()
                create_user_by_agent_infos(obj,roles)
            except Exception as ex:
                messages.error(self.request, ex.message)
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        name= self.form_class._meta.model._meta.verbose_name
        context['title'] = "Nouveau  {}".format(name,)
        sigrole = SigRole.objects.get(role=Role.AGENT_DCP)
        context['form'].fields["roles"].queryset = sigrole.groups.all()
        return context



from django.contrib import messages
@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class ProfilePCCreateView(PermissionRequiredMixin,BSModalCreateView):
    c = "profilepc"
    template_name = 'core/add_entity.html'
    form_class = ProfilePCModelForm
    success_message = 'Success: Création agent.'
    success_url = reverse_lazy('core:{}_list'.format(c,))
    permission_required = ('core.add_{}'.format(c,),)
    title="Nouveau agent"

   # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


    def form_valid(self, form):
        if not is_ajax(self.request.META):
            obj = form.save(commit=False)
            roles = form.cleaned_data["roles"]
            try:
                obj.fonction = Role.AGENT_PC
                obj.creator = self.request.user
                create_user_by_agent_infos(obj,roles)
            except Exception as ex:
                messages.error(self.request, ex.message)
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        name= self.form_class._meta.model._meta.verbose_name
        sigrole = SigRole.objects.get(role=Role.AGENT_PC)
        context['form'].fields["roles"].queryset = sigrole.groups.all()
        context['title'] = "Nouveau  {}".format(name,)
        return context


@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class ProfilePCUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    model = ProfilePC
    c = "profilepc"
    template_name = 'core/update_entity.html'
    form_class = ProfilePCModelForm
    permission_required = ('core.change_{}'.format(c,),)
    success_message = 'Success: Mise à jour  agent.'
    success_url = reverse_lazy('core:{}_list'.format(c,))
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        context['title'] = "Mise à jour de {} : {}".format(self.object._meta.verbose_name,self.object)
        sigrole = SigRole.objects.get(role=Role.AGENT_PC)
        context['form'].fields["roles"].queryset = sigrole.groups.all()
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




@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class ProfileDCPUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    model = ProfileDCP
    c = "profiledcp"
    template_name = 'core/update_entity.html'
    form_class = ProfileDCPModelForm
    permission_required = ('core.change_{}'.format(c,),)
    success_message = 'Success: Mise à jour  agent.'
    success_url = reverse_lazy('core:{}_list'.format(c,))
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour de {} : {}".format(self.object._meta.verbose_name,self.object)
        sigrole = SigRole.objects.get(role=Role.AGENT_DCP)
        context['form'].fields["roles"].queryset = sigrole.groups.all()
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


@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class ProfileDCPDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    c = "profiledcp"
    model = ProfileDCP
    permission_required = ('core.delete_{}'.format(c,),)

    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_message = 'Success: Supression  dcp'
    success_url = reverse_lazy('core:{}_list'.format(c,))

    template_name = "core/confirm_delete_entity.html"


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Suppression agent : {}".format(self.object, )
        return context


@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class ProfilePCDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    c = "profilepc"
    model = ProfilePC
    permission_required = ('core.delete_{}'.format(c,),)

    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_message = 'Success: Supression  dcp'
    success_url = reverse_lazy('core:{}_list'.format(c,))

    template_name = "core/confirm_delete_entity.html"


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Suppression agent : {}".format(self.object, )
        return context



@transaction.atomic
def create_user_by_agent_infos(agent,roles):
    try:
        User.objects.get(username=agent.matricule)
        error = "Un utilisateur ayant cet identifiant {} existe dejas".format(agent.matricule, )
        ex= Exception()
        ex.message=error
        raise ex
    except User.DoesNotExist:
        user = User()
        user.username = agent.matricule
        user.role=agent.fonction
        user.last_name = agent.lastname
        user.first_name = agent.firstname
        #user.email = agent.email
        user.force_change_pwd=True
        password1 = BaseUserManager().make_random_password(8)
        user.set_password(password1)
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.save()
        agent.user = user
        agent.save()#--->desactive le user
        user.is_active = True
        user.groups.set(roles)
        user.save()
        agent.send_sms_message(password1)




@login_required
#@user_role_required("ADMIN")
def affection_list_view(request):
    user=request.user
    queryset = AffectationAgent.objects.all()
    queryset_filter = AffectationAgentFilter(request.GET, request=request, queryset=queryset)
    table = AffectationAgentTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('core.add_affectationagent')
    if user.has_perm('core.change_affectationagent') or user.has_perm('core.delete_affectationagent'):
        table = AffectationAgentTable(queryset_filter.qs)
    title = _("LISTE AFFECTATIONS")
    data_title=_("LISTE AFFECTATIONS")


    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'core/affectation_list.html', {"can_create_entite":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})




@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class AffectationAgentCreateView(PermissionRequiredMixin,BSModalCreateView):
    model_name= "affectationagent"
    template_name = 'core/add_entity.html'
    form_class = AffectationAgentModelForm
    success_message = 'Success: Création  affectation.'
    success_url = reverse_lazy('core:affectation_list')
    permission_required = ('core.add_{}'.format(model_name),)
    title="Nouvel affectation"

   # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


    def form_valid(self, form):
        if not is_ajax(self.request.META):
            #lower,upper= form.instance.period.start,form.instance.period.stop
            #rg = DateRange(lower.date(),upper.date())
            #form.instance.period=rg

            form.instance.creator = self.request.user
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super(AffectationAgentCreateView, self).get_context_data(*args, **kwargs)
        name= self.form_class._meta.model._meta.verbose_name
        context['title'] = "Nouvel affectaion {}".format(name,)
        return context



@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class AffectationAgentUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    model_name = "affectationagent"
    model = AffectationAgent
    template_name = 'core/update_entity.html'
    form_class = AffectationAgentModelForm
    permission_required = ('core.change_{}'.format(model_name,),)
    success_message = 'Success: Mise à jour affectation.'
    success_url = reverse_lazy('core:affectation_list')
    def get_context_data(self, *args, **kwargs):
        context = super(AffectationAgentUpdateView, self).get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour affectation {} : {}".format(self.object._meta.verbose_name,self.object)
        return context



@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class AffectationAgentDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    model = AffectationAgent

    permission_required = ('core.delete_{}'.format(model._meta.model_name),)

    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_message = 'Success: Supression avec succès '
    success_url = reverse_lazy('core:affectation_list')

    template_name = "core/confirm_delete_entity.html"


    def get_context_data(self, *args, **kwargs):
        context = super(AffectationAgentDeleteView, self).get_context_data(*args, **kwargs)
        context['title'] = "Suppression affectation : {}".format(self.object.name,)
        return context





@login_required
@user_role_required("ADMIN")
def list_groups_view(request):
    user=request.user
    c="group"
    create_url = reverse_lazy('core:create_group')
    queryset = Group.objects.all()
    queryset_filter = GroupFilter(request.GET, request=request, queryset=queryset)
    table = GroupTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('auth.add_{}'.format(c,))
    if user.has_perm('auth.change_{}'.format(c,)) or user.has_perm('auth.delete_{}'.format(c,)):
        table = GroupTable(queryset_filter.qs)
    title = _("LISTE ROLES SIGCDD")
    data_title=_("LISTE ROLES SIGCDD")
    create_tilte = "Nouveau Role"


    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'core/default_list.html', {"create_tilte":create_tilte,"can_create_entite":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc","create_url":create_url})



from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class GroupCreateView(PermissionRequiredMixin,BSModalCreateView):
    model_name= "group"
    template_name = 'core/add_entity.html'
    form_class = GroupModelForm
    success_message = 'Success: Création  Role.'
    success_url = reverse_lazy('core:group_list')
    permission_required = ('auth.add_{}'.format(model_name),)
    title="Nouveau Role"

   # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


    def form_valid(self, form):
        if not is_ajax(self.request.META):
            obj = form.save(commit=False)
            types_agents=form.cleaned_data["roles"]
            form.save()
            for t in types_agents:
                ob,created=SigRole.objects.get_or_create(role=t)
                ob.groups.add(obj)
                ob.save()

        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        name= self.form_class._meta.model._meta.verbose_name

        if self.request.user.role!=Role.ADMIN:
            content_type_ids = ContentType.objects.filter(app_label__in=["group","bankcheck", "core", "cddaccount"]).values_list(
                "id", flat=True)
        else:
            content_type_ids = ContentType.objects.filter(
                app_label__in=["bankcheck", "core", "cddaccount"]).values_list(
                "id", flat=True)
        context['form'].fields["permissions"].queryset = Permission.objects.filter(content_type_id__in=content_type_ids)

        context['title'] = "Nouveau Role"
        return context



@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class GroupUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    model_name = "group"
    model = Group
    template_name = 'core/update_entity.html'
    form_class = GroupModelForm
    permission_required = ('auth.change_{}'.format(model_name,),)
    success_message = 'Success: Mise à jour.'
    success_url = reverse_lazy('core:group_list')
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        if self.request.user.role!=Role.ADMIN:
            content_type_ids = ContentType.objects.filter(app_label__in=["group","bankcheck", "core", "cddaccount"]).values_list(
                "id", flat=True)
        else:
            content_type_ids = ContentType.objects.filter(
                app_label__in=["bankcheck", "core", "cddaccount"]).values_list(
                "id", flat=True)

        context['form'].fields["permissions"].queryset = Permission.objects.filter(content_type_id__in=content_type_ids)

        context['title'] = "Mise à jour role: {}".format(self.object,)
        return context

    def get_initial(self):
        initial = super().get_initial()
        ref = self.get_object()
        sigroles =  ref.sigrole_set.all()

        a = [i.role for i in sigroles.all()]
        initial["roles"] = a
        return initial
    def form_valid(self, form):
        if not is_ajax(self.request.META):
            obj = form.save(commit=False)
            types_agents=form.cleaned_data["roles"]
            sigroles=SigRole.objects.filter(role__in=types_agents)
            self.object.sigrole_set.set(sigroles)
            form.save()

        return super().form_valid(form)


@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class GroupDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    model = Group

    permission_required = ('auth.delete_{}'.format(model._meta.model_name),)

    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_message = 'Success: Supression avec succès '
    success_url = reverse_lazy('core:group_list')

    template_name = "core/confirm_delete_entity.html"


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Suppression : {}".format(self.object.name,)
        return context