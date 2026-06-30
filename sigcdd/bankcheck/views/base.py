import datetime
import time

from bankcheck.forms import RejetChequeForm, ChequierSimpleForm, ChequierForm, TypeChequierForm, DAPForm, AgentDAPForm, \
    ElementCommandeForm, CommandeForm, ChequierOtpForm, MiseEnOppositionForm, AnnulationChequeForm, CompenseChequeForm, \
    ComptableMatiereForm, EditBordereauForm, ChequierdapOtpForm
from bankcheck.models import ChequeScanne, Cheque, SettingsChequier, DAP, TypeChequier, Commande, ElementCommande, \
    Chequier, AgentDAP, \
    STATUS_COMMANDE, RejetCheque, ComptableMatiere, Bordereau
from bankcheck.tables import CompenseCheque, AnnulationCheque, MiseEnOpposition, ChequeTable, ChequierTable, \
    ChequierFilter, CommandeTable, CommandeFilter, DAPFilter, \
    DAPTable, \
    AgentDAPFilter, AgentDAPTable, TypeChequierTable, TypeChequierFilter, MiseEnOppositionTable, MiseEnOppositionFilter, \
    AnnulationChequeTable, AnnulationChequeFilter, CompenseChequeTable, CompenseChequeFilter, ChequeFullTable, \
    ChequeFilter, RejetChequeFilter, RejetChequeTable, ChequeScanneFilter, ChequeScanneTable, ComptableMatiereTable, \
    ComptableMatiereFilter, BordereauFilter, BordereauTable
from bootstrap_modal_forms.utils import is_ajax


from cddaccount.models import CompteDepot, GerantCD, OrdrePayment, cancel_op, GestionCompteDepot, Mandataire
from core.models import ProfilePC, PosteComptable
from django.contrib import messages
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django_tables2 import RequestConfig
from helpers.decorators import user_role_required
from helpers.exceptions import SigException
from helpers.models import Role, SimpleOtp, SigRole
from users.models import User

PAGINATION_SIZE=100

default_currency="F CFA"
from bootstrap_modal_forms.generic import (
    BSModalDeleteView,
	BSModalCreateView, BSModalUpdateView
)
def get_cdd_with_gerant(request):
	try:
		key= request.session["select_cddacc_user_id"]
		return CompteDepot.objects.filter(id=int(key))
	except KeyError:
		ids=GestionCompteDepot.objects.by_agent(request.user).filter(actif=True).values_list("compte_id", flat=True)
		return CompteDepot.objects.by_agent(request.user).filter(id__in=ids)




@login_required
#@user_role_required("ADMIN")
def dap_list_view(request):
    user=request.user
    queryset = DAP.objects.all()
    create_url=None
    queryset_filter = DAPFilter(request.GET, request=request, queryset=queryset)
    table = DAPTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('bankcheck.add_dap')
    if can_create_dcp:
        create_url=reverse_lazy('bankcheck:create_dap')
    if user.has_perm('bankcheck.change_dap') or user.has_perm('bankcheck.delete_dap'):
        table = DAPTable(queryset_filter.qs)
    title = _("Direction de l'Administration du Personnel")
    data_title=_("Direction de l'Administration du Personnel")

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/dap_list.html', {"create_url":create_url,"can_create_dcp":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})




@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class DAPCreateView(PermissionRequiredMixin,BSModalCreateView):
    template_name = 'core/add_entity.html'
    form_class = DAPForm
    success_message = 'Success: Création entité Dap.'
    success_url = reverse_lazy('bankcheck:dap_list')
    permission_required = ('bankcheck.add_dap',)
    title="Nouvel entite"

   # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            form.instance.created = datetime.datetime.now()
            form.instance.creator = self.request.user
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        name= self.form_class._meta.model._meta.verbose_name
        context['title'] = "Nouvel entité {}".format(name,)
        return context


@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class DAPDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    model = DAP
    permission_required = ('bankcheck.delete_dap',)

    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_message = 'Success: Supression entité dap'
    success_url = reverse_lazy('bankcheck:dap_list')

    template_name = "core/confirm_delete_entity.html"

    def form_valid(self, form):
        raise Http404


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Suppression entite : {}".format(self.object.name,)
        return context

@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class DAPUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    model = DAP
    template_name = 'core/update_entity.html'
    form_class = DAPForm
    permission_required = ('bankcheck.change_dap',)
    success_message = 'Success: Mise à jour entité dap.'
    success_url = reverse_lazy('bankcheck:dap_list')
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = " de l' entité {} : {}".format(self.object._meta.verbose_name,self.object)
        return context


@login_required
#@user_role_required("ADMIN")
def agent_dap_list_view(request):
    user=request.user
    c="agentdap"
    create_url = reverse_lazy('bankcheck:create_agentdap')
    queryset = AgentDAP.objects.all()
    queryset_filter = AgentDAPFilter(request.GET, request=request, queryset=queryset)
    table = AgentDAPTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('bankcheck.add_{}'.format(c,))
    if user.has_perm('bankcheck.change_{}'.format(c,)) or user.has_perm('bankcheck.delete_{}'.format(c,)):
        table = AgentDAPTable(queryset_filter.qs)
    title = _("LISTE AGENTS DAP")
    data_title=_("LISTE AGENTS DAP")

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/agent_dap_list.html', {"can_create_agent":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc","create_url":create_url})


@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class AgentDAPCreateView(PermissionRequiredMixin,BSModalCreateView):
    c = "agentdap"
    template_name = 'core/add_entity.html'
    form_class = AgentDAPForm
    success_message = 'Success: Création entité agent.'
    success_url = reverse_lazy('bankcheck:{}_list'.format(c,))
    permission_required = ('bankcheck.add_{}'.format(c,),)
    title="Nouveau agent"

   # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


    def form_valid(self, form):

        if not is_ajax(self.request.META):
            obj = form.save(commit=False)
            roles = form.cleaned_data["roles"]
            try:
                obj.fonction=Role.AGENT_DAP
                obj.creator=self.request.user
                obj.dap=DAP.object()

                create_user_by_agentdap_infos(obj,roles)
            except Exception as ex:
                messages.error(self.request, ex.message)
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        name= self.form_class._meta.model._meta.verbose_name
        context['title'] = "Nouveau  {}".format(name,)
        sigrole = SigRole.objects.get(role=Role.AGENT_DAP)
        context['form'].fields["roles"].queryset = sigrole.groups.all()
        return context

@transaction.atomic
def create_user_by_agentdap_infos(agent,roles):
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










@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class AgentDAPUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    model = AgentDAP
    c = "agentdap"
    template_name = 'core/update_entity.html'
    form_class = AgentDAPForm
    permission_required = ('bankcheck.change_{}'.format(c,),)
    success_message = 'Success: Mise à jour '
    success_url = reverse_lazy('bankcheck:{}_list'.format(c,))
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        sigrole = SigRole.objects.get(role=Role.AGENT_DAP)
        context['form'].fields["roles"].queryset = sigrole.groups.all()
        context['title'] = "Mise à jour de {} : {}".format(self.object._meta.verbose_name,self.object)
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
class AgentDAPDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    c = "agentdap"
    model = AgentDAP
    permission_required = ('bankcheck.delete_{}'.format(c,),)

    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_message = 'Success: Supression entité dcp'
    success_url = reverse_lazy('bankcheck:{}_list'.format(c,))

    template_name = "core/confirm_delete_entity.html"


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Suppression agent : {}".format(self.object, )
        return context








@method_decorator([user_role_required([Role.AGENT_DAP,Role.ADMIN])], name='dispatch')
class TypeChequierCreateView(PermissionRequiredMixin, BSModalCreateView):
    template_name = 'core/add_entity.html'
    form_class = TypeChequierForm
    model_name = form_class._meta.model._meta.model_name
    success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
    success_url = reverse_lazy('bankcheck:{}_list'.format(model_name, ))
    permission_required = ('bankcheck.add_{}'.format(model_name, ),)

    # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            form.instance.creator = self.request.user
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        name = self.form_class._meta.model._meta.verbose_name
        context['title'] = "Nouveau  {}".format(name, )
        return context



@method_decorator([ user_role_required([Role.AGENT_DAP,Role.ADMIN])], name='dispatch')
class TypeChequierUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    model = TypeChequier
    template_name = 'core/update_entity.html'
    form_class = TypeChequierForm
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('bankcheck.change_{}'.format(model_name,),)
    success_message = 'Success: Mise àjour {} avec succès.'.format(model._meta.verbose_name,)
    success_url = reverse_lazy('bankcheck:{}_list'.format(model_name,))
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour  {} : {}".format(self.object._meta.verbose_name,self.object)
        return context


@method_decorator([ user_role_required([Role.AGENT_DAP,Role.ADMIN])], name='dispatch')
class TypeChequierDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    model = TypeChequier
    permission_required = ('bankcheck.delete_{}'.format(model._meta.model_name),)

    success_message = 'Success: Supression  avec succès'
    success_url = reverse_lazy('bankcheck:{}_list'.format(model._meta.model_name,))

    template_name = "core/confirm_delete_entity.html"


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Suppression  : {}".format(self.object.name,)
        return context

@login_required
def typechequier_list_view(request):
    user=request.user
    c = "typechequier"
    create_url = reverse_lazy('bankcheck:create_{}'.format(c,))
    queryset = TypeChequier.objects.all()
    queryset_filter = TypeChequierFilter(request.GET, request=request, queryset=queryset)
    table = TypeChequierTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('bankcheck.add_{}'.format(c,))
    if user.has_perm('bankcheck.change_{}'.format(c,)) or user.has_perm('bankcheck.delete_{}'.format(c,)):
        table = TypeChequierTable(queryset_filter.qs)
    title = _("Type Chequier")
    data_title=_("Types Chequiers")
    create_title="Nouveau Type de chéquier"

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'core/default_list.html', {"create_tilte":create_title,"create_url":create_url,"can_create_entite":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})



from django.forms import formset_factory


ElementCommandeFormFormset = formset_factory(ElementCommandeForm,extra=1)

@login_required
@transaction.atomic
@permission_required("bankcheck.add_commande",raise_exception=True)
def commande_chequier_view(request):
    template ="bankcheck/commandechequier.html"
    user=request.user
    agent=None
    if hasattr(user,"gerant_cd"):
        agent=user.gerant_cd
    elif hasattr(user,"agent_postecomptable"):
        agent=user.agent_postecomptable

    success_url = reverse_lazy('bankcheck:commandes_list')
    comptes = CompteDepot.objects.by_agent(user)

    if request.method == 'GET':
        new_form = CommandeForm()
        new_form.fields['compte'].queryset = comptes
        ElementCommandeFormFormset = formset_factory(ElementCommandeForm, extra=1)
        formset = ElementCommandeFormFormset(request.GET or None)


    elif request.method == 'POST':
        new_form = CommandeForm(request.POST,request.FILES)
        new_form.fields['compte'].queryset = comptes

        ElementCommandeFormFormset = formset_factory(ElementCommandeForm, extra=1)
        formset = ElementCommandeFormFormset(request.POST)


        if formset.is_valid() and new_form.is_valid():

            selected_types = [form.cleaned_data for form in formset]
            try:
                commande=new_form.save(commit=False)
                if hasattr(user, "gerant_cd"):
                    commande.demandeur=agent
                commande.save()
                for _product in selected_types:
                    produit = _product["type"]
                    item = ElementCommande()
                    item.commande = commande
                    item.type = produit
                    item.nombres = int(_product["nombres"])
                    item.save()
                #url = reverse_lazy('suppliercredit:list_creditapplication_view')
                messages.info(request, "Votre commande est enregistrée. Votre comptable  vous contactera dans les plus brefs délais.")
                return HttpResponseRedirect(success_url)
            except Exception as e:
                messages.info(request, e.message)
                return HttpResponseRedirect("#")

        else:
            print(new_form.errors.as_data())
            print(formset.errors)
            print(formset.non_form_errors())
            messages.error(request, formset.non_form_errors(), extra_tags="danger")



    context= {'formset': formset,'form':new_form,"agent":agent}

    return render(request, template, context)




@login_required
#@user_role_required("ADMIN")
def commande_list_view(request):
    user=request.user
    queryset = Commande.objects.by_agent(user)
    can_valid_co = user.has_perm('bankcheck.valider_commande')
    create_url=None
    queryset_filter = CommandeFilter(request.GET, request=request, queryset=queryset)
    #table = CommandeTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('bankcheck.add_commande')
    if can_create_dcp:
        create_url=reverse_lazy('bankcheck:commande_chequier_view')
    #if user.has_perm('bankcheck.change_commande') or user.has_perm('bankcheck.delete_commande'):
    table = CommandeTable(queryset_filter.qs)
    title = _("Commandes chéquiers")
    data_title=_("Commandes chéquiers")

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/commandes_list.html', {"create_url":create_url,"can_create_dcp":can_create_dcp, 'can_valid_co':can_valid_co,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})



@login_required
def default_commande_list_view(request,status,title):
    user=request.user
    queryset = Commande.objects.by_agent(user).filter(status__in=status)
    can_valid_co = user.has_perm('bankcheck.valider_commande')
    create_url=None
    queryset_filter = CommandeFilter(request.GET, request=request, queryset=queryset)
    #table = CommandeTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('bankcheck.add_commande')
    if can_create_dcp:
        create_url=reverse_lazy('bankcheck:commande_chequier_view')
    #if user.has_perm('bankcheck.change_commande') or user.has_perm('bankcheck.delete_commande'):
    table = CommandeTable(queryset_filter.qs)

    data_title=title

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/commandes_list.html', {"create_url":create_url,"can_create_dcp":can_create_dcp, 'can_valid_co':can_valid_co,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})

def commandes_encours_list(request):
    return default_commande_list_view(request,["ACCEPTE"],"Nouvelles Commandes chéquiers")
def commandes_traite_list(request):
    return default_commande_list_view(request,['REJETE','TRAITE'],"Commandes chéquiers traitées")


@login_required
def edit_all_bordereau(request):
    import time
    user = request.user
    template="bankcheck/edit_bordereau.html"
    sequence_settings = SettingsChequier.object()
    success_url = reverse_lazy('bankcheck:commandes_list')
    if not sequence_settings:
        messages.info(request,"Merci de faire la configuration des sequences")
        return HttpResponseRedirect(success_url)

    if request.method == 'GET':
        new_form = EditBordereauForm()


    elif request.method == 'POST':
        new_form = EditBordereauForm(request.POST,request.FILES)
        if new_form.is_valid():

            commandes_a_traiter = Commande.objects.by_agent(user).filter(status=STATUS_COMMANDE.ACCEPTE, traiter=False)
            bordereau=Bordereau()
            bordereau.imprimeur=new_form.cleaned_data["imprimeur"]
            #bordereau.reference=str(int(time.time_ns()))
            bordereau.save()
            for q in commandes_a_traiter:
                generatechequier(q,bordereau,user,sequence_settings)
            url = reverse_lazy('bankcheck:commande_traiter', kwargs={"reference": bordereau.reference})
            return HttpResponseRedirect(url)
        else:
            messages.error(request, new_form.errors.as_data(), extra_tags="danger")

    context = {'form': new_form}


    return render(request, template, context)


@login_required
def all_bordereau_commande_view(request,reference):
    import time
    template = "bankcheck/all_bordereau_commande_view.html"
    user = request.user
    cheque = []
    bordereau = Bordereau.objects.get(reference=reference)

    if not hasattr(user, "agent_dap"):
        raise Http404


    context = {"imprimeur":bordereau.imprimeur, "title": "Bon de commande {}".format(bordereau.format_reference(),), "cheque_list": bordereau.chequiers.all(),"commande":bordereau}
    return render(request, template, context)


#@method_decorator([ user_role_required([Role.AGENT_DAP,Role.GERANT])], name='dispatch')
class CommandeDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    model = Commande
    permission_required = ('bankcheck.delete_{}'.format(model._meta.model_name),)

    success_message = 'Success: Supression entité avec succès'
    success_url = reverse_lazy('bankcheck:commandes_list')

    template_name = "core/confirm_delete_entity.html"


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Suppression  : {}".format(self.object,)
        return context



@login_required
@transaction.atomic
def update_commande_chequier_view(request,reference):

    template ="bankcheck/update_commande.html"
    user=request.user
    agent=user.gerant_cd
    object = get_object_or_404(Commande, reference=reference)
    if not object.can_acces(user):
        raise Http404
    success_url = reverse_lazy('bankcheck:commandes_list')
    if object.traiter:
        messages.info(request,
                      "Votre commande déjà traitée")
        return HttpResponseRedirect(success_url)


    initial = [item.as_dict() for item in object.items.all()]

    comptes = CompteDepot.objects.by_agent(user)

    if request.method == 'GET':
        new_form = CommandeForm(instance=object)
        new_form.fields['compte'].queryset = comptes
        ElementCommandeFormFormset = formset_factory(ElementCommandeForm, extra=0)
        formset = ElementCommandeFormFormset(request.GET or None,initial=initial)


    elif request.method == 'POST':
        new_form = CommandeForm(request.POST,request.FILES)
        new_form.fields['compte'].queryset = comptes

        ElementCommandeFormFormset = formset_factory(ElementCommandeForm, can_delete=True)
        formset = ElementCommandeFormFormset(request.POST)


        if formset.is_valid() and new_form.is_valid():
            try:
                for form in formset:
                    typechequier = form.cleaned_data['type']
                    try:
                        item = ElementCommande.objects.get(commande=object, type=typechequier)
                    except ElementCommande.DoesNotExist:
                        item = ElementCommande()
                        item.commande = object
                        item.type=typechequier
                    item.nombres = int(form.cleaned_data['nombres'])
                    item.save()

                #url = reverse_lazy('suppliercredit:list_creditapplication_view')
                messages.info(request, "Votre commande est mise à jour. Le service DAP vous contactera dans les plus brefs délais.")
                return HttpResponseRedirect(success_url)
            except Exception as e:
                messages.info(request, e.message)
                return HttpResponseRedirect("#")

        else:
            print(new_form.errors.as_data())
            print(formset.errors)
            print(formset.non_form_errors())
            messages.error(request, formset.non_form_errors(), extra_tags="danger")



    context= {'formset': formset,'form':new_form,"agent":agent}

    return render(request, template, context)




@login_required
@permission_required("bankcheck.accepter_commande",raise_exception=True)
@transaction.atomic

def accepter_commande_chequier_view(request,reference):

    template ="bankcheck/update_commande.html"
    user=request.user

    object = get_object_or_404(Commande, reference=reference)
    agent = object.demandeur

    if not object.can_acces(user):
        raise Http404
    success_url = reverse_lazy('bankcheck:commandes_list')
    if object.traiter:
        messages.info(request,
                      "Votre commande déjà traitée")
        return HttpResponseRedirect(success_url)

    v=object.items.all()
    initial = [item.as_dict() for item in v]

    type_chequiers= TypeChequier.objects.filter(id=v.last().type_id)

    comptes = CompteDepot.objects.by_agent(user)

    if request.method == 'GET':
        new_form = CommandeForm(instance=object)
        new_form.fields['compte'].queryset = comptes
        ElementCommandeFormFormset = formset_factory(ElementCommandeForm,extra=0)
        formset = ElementCommandeFormFormset(request.GET or None,initial=initial)
        for form in formset:
            form.fields['type'].queryset =type_chequiers


    elif request.method == 'POST':
        new_form = CommandeForm(request.POST,request.FILES)
        new_form.fields['compte'].queryset = comptes

        ElementCommandeFormFormset = formset_factory(ElementCommandeForm, can_delete=True)
        formset = ElementCommandeFormFormset(request.POST)


        if formset.is_valid() and new_form.is_valid():
            try:
                for form in formset:
                    typechequier = form.cleaned_data['type']
                    try:
                        item = ElementCommande.objects.get(commande=object, type=typechequier)
                    except ElementCommande.DoesNotExist:
                        item = ElementCommande()
                        item.commande = object
                        item.type=typechequier
                    item.nombres = int(form.cleaned_data['nombres'])
                    item.save()
                object.agent_pc=user.agent_postecomptable
                object.status=STATUS_COMMANDE.ACCEPTE
                object.accepter=True
                object.acceptation_date=datetime.datetime.now()
                object.save()

                #url = reverse_lazy('suppliercredit:list_creditapplication_view')
                messages.info(request, "Votre commande est mise à jour. Le service DAP vous contactera dans les plus brefs délais.")
                return HttpResponseRedirect(success_url)
            except Exception as e:
                messages.info(request, e.message)
                return HttpResponseRedirect("#")

        else:
            print(new_form.errors.as_data())
            print(formset.errors)
            print(formset.non_form_errors())
            messages.error(request, formset.non_form_errors(), extra_tags="danger")



    context= {'formset': formset,'form':new_form,"agent":agent}

    return render(request, template, context)







@login_required
@permission_required("bankcheck.valider_commande",raise_exception=True)
@transaction.atomic

def valider_commande_chequier_view(request,reference):

    template ="bankcheck/valider_commande.html"
    user=request.user
    success_url = reverse_lazy('bankcheck:commandes_list')

    sequence_settings =SettingsChequier.object()
    if not sequence_settings:
        messages.info(request,"Merci de faire la configuration des sequences")
        return HttpResponseRedirect(success_url)


    object = get_object_or_404(Commande, reference=reference)
    if not object.can_acces(user):
        raise Http404

    if object.traiter:
        messages.info(request,"Votre commande déjà traitée")
        return HttpResponseRedirect(success_url)


    initial = []
    start_sequence=sequence_settings.last_sequence
    object.first_sequence=start_sequence+1

    v = object.items.all()
    #initial = [item.as_dict() for item in v]

    type_chequiers = TypeChequier.objects.filter(id=v.last().type_id)

    for item in v:
        for i in range(item.nombres):
            a=item.as_dict()
            last_sequence=start_sequence+item.type.taille
            a["debut"]=start_sequence+1
            a["fin"]=last_sequence
            initial.append(a)
            start_sequence=last_sequence
            object.last_sequence=last_sequence

    if request.method == 'GET':
        #new_form = CommandeForm(instance=object)
        #new_form.fields['compte'].queryset = comptes
        ChequierFormFormset = formset_factory(ChequierForm,extra=0,max_num=1)
        formset = ChequierFormFormset(request.GET or None,initial=initial)
        for form in formset:
            form.fields['type'].queryset =type_chequiers


    elif request.method == 'POST':
        #new_form = CommandeForm(request.POST,request.FILES)
        #new_form.fields['compte'].queryset = comptes

        ChequierFormFormset = formset_factory(ChequierForm, can_delete=False)
        formset = ChequierFormFormset(request.POST)
        if formset.is_valid() :
            try:
                for form in formset:
                    type = form.cleaned_data['type']
                    debut = form.cleaned_data['debut']
                    fin = form.cleaned_data['fin']
                    item = Chequier()
                    item.reference=debut
                    item.compte=object.compte
                    item.demande=object.reference
                    item.dap=user.agent_dap.dap
                    item.editeur=user.agent_dap
                    item.fin = fin
                    item.debut = debut
                    item.type=type
                    item.taille=type.taille
                    if object.demandeur:
                        item.phone_gerant=object.demandeur.phone.as_e164
                        item.gerant=object.demandeur.matricule
                    if object.agent_pc:
                        item.phone_postecomptable=object.agent_pc.phone.as_e164
                        item.agent_pc = object.agent_pc.matricule
                    item.save()
                object.agent_dap=user.agent_dap
                object.status=STATUS_COMMANDE.TRAITE
                object.traiter=True
                object.process_date_date=datetime.datetime.now()
                object.save()
                sequence_settings.last_sequence=object.last_sequence
                sequence_settings.save()

                url = reverse_lazy('bankcheck:bordereau_commande_view',kwargs={"reference":reference})
                messages.info(request, "Votre commande est en cours de traitement.")
                return HttpResponseRedirect(url)
            except Exception as e:
                print(e)
                messages.error(request, e, extra_tags="danger")
                return HttpResponseRedirect("#")

        else:
            print(formset.errors)
            print(formset.non_form_errors())
            messages.error(request, formset.non_form_errors(), extra_tags="danger")



    context= {'formset': formset,"object":object}

    return render(request, template, context)



@login_required
#@user_role_required("ADMIN")
def chequier_list_view(request):
    user=request.user
    if hasattr(user,"agent_postecomptable"):
        url = reverse_lazy('bankcheck:aff_chequiers_list',)
        return HttpResponseRedirect(url)
    elif hasattr(user, "gerant_cd"):
        queryset = Chequier.objects.by_agent(user).filter(prise_en_charge=True,distribue=True,delivered=True)

    else:
        queryset = Chequier.objects.by_agent(user)
    create_url=None
    queryset_filter = ChequierFilter(request.GET, request=request, queryset=queryset)
    #table = CommandeTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('bankcheck.add_chequier')
    if can_create_dcp:
        create_url=reverse_lazy('bankcheck:commande_chequier_view')
    #if user.has_perm('bankcheck.change_commande') or user.has_perm('bankcheck.delete_commande'):
    table = ChequierTable(queryset_filter.qs,exclude=("selection","action"))
    if hasattr(user,"agent_dap") or hasattr(user,"agent_postecomptable"):
        table = ChequierTable(queryset_filter.qs)
    title = _("Liste chéquiers")
    data_title=_("Liste chéquiers")

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/list_chequier.html', {"create_url":create_url,"can_create_dcp":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})



@login_required
@transaction.atomic()
@permission_required("bankcheck.bloquer_chequier", raise_exception=True)
def bloquer_chequier_view(request, reference):
    template = "bankcheck/simpleform.html"
    user = request.user
    success_url = reverse_lazy('bankcheck:chequiers_list')
    object = get_object_or_404(Chequier, reference=reference)
    if not object.can_acces(user):
        raise Http404
    gerant = object.creator.gerant_cd

    if request.method == 'POST':
        form = ChequierSimpleForm(request.POST)
        if form.is_valid():
            if request and not is_ajax(request.META):
                # description = form.cleaned_data["description"]

                object.bloquer = True
                # object.observations = description
                # object.creator = user
                object.save()

            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")
    else:

        form = ChequierSimpleForm()

    context = {"form": form, 'title': "Validation blocage fond du projet  {}".format(object.ref_marche, ),
               "object": object, "compte": object.compte, "agent": gerant, }
    return render(request, template, context)

from bankcheck.signals import chequier_status_changed
@login_required
@transaction.atomic()
@permission_required("bankcheck.delivrer_chequier", raise_exception=True)
def depreciate_delivrer_chequier_view(request, reference):
    template = "bankcheck/simpleform.html"
    user = request.user
    success_url = reverse_lazy('bankcheck:chequiers_list')
    object = get_object_or_404(Chequier, reference=reference)
    if not object.can_acces(user):
        raise Http404
    if request.method == 'POST':
        form = ChequierOtpForm(request.POST)
        if form.is_valid():
            if request and not is_ajax(request.META):
                token = form.cleaned_data["otp"]
                origin_otp=SimpleOtp.objects.filter(otp=token).last()
                if origin_otp and origin_otp.verify(token):
                    object.delivered = True
                    object.delivered_date=datetime.datetime.now()
                    # object.observations = description
                    # object.creator = user
                    object.save()
                    try:
                        chequier_status_changed.send(sender=type(object), instance=object)
                    except SigException as e:
                        messages.error(request,e.message,extra_tags="danger")
                        return redirect(success_url)
                    messages.success(request, "Chequier delevré avec succès")
                else:messages.error(request, "Token invalide",extra_tags="danger")

            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")
    else:
        if object.phone_gerant:
            otp = SimpleOtp()
            otp.phone = object.phone_gerant
            otp.generate_otp()
            otp.message = object.get_otp_retrait(otp.otp)
            otp.save()
            otp.send_otp()
        form = ChequierOtpForm()

    context = {"form": form, 'title': "Delivrer la chequier n° {}".format(object.reference, ),
               "object": object,  }
    return render(request, template, context)










@login_required
@transaction.atomic()
def details_chequier_view(request, reference):
    template = "bankcheck/details_chequier.html"
    user = request.user
    object = get_object_or_404(Chequier, reference=reference)
    if not object.can_acces(user):
        raise Http404
    cheques = object.cheques.all()
    table = ChequeTable(cheques,exclude=("compte","action"))

    taille=object.taille

    agent_comptable=None
    if object.agent_pc is not None:
        try:
            agent_comptable=ProfilePC.objects.get(matricule=object.agent_pc).full_name()
        except ProfilePC.DoesNotExist:
            pass
    gerant = None
    if object.gerant is not None:
        try:
            gerant=GerantCD.objects.get(matricule=object.gerant).full_name()
        except GerantCD.DoesNotExist:
            pass

    RequestConfig(request, paginate={"per_page": taille}).configure(table)

    context = {"table": table, 'title': "Détails chéquier  {}".format(object.reference, ), "object": object,
               "compte": object.compte,"index":"0","sens":"desc","gerant":gerant,"agentcomptable":agent_comptable}
    return render(request, template, context)




@login_required
@transaction.atomic()
@permission_required("bankcheck.priseencharge_chequier", raise_exception=True)
def priseencharge_chequier_view(request, reference):
    template = "bankcheck/simpleform.html"
    user = request.user
    success_url = reverse_lazy('bankcheck:chequiers_list')
    object = get_object_or_404(Chequier, reference=reference)
    if not object.can_acces(user):
        raise Http404


    if request.method == 'POST':
        form = ChequierSimpleForm(request.POST)
        if form.is_valid():
            if request and not is_ajax(request.META):
                formdata=form.cleaned_data
                if not "description" in formdata :
                    object.observations="non renseigne"

                # description = form.cleaned_data["description"]
                object.prise_en_charge = True
                object.prise_en_charge_date=datetime.datetime.now()
                # object.observations = description
                # object.creator = user
                object.save()

                messages.success(request, "Chequier delevré avec succès")

            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")
    else:

        form = ChequierSimpleForm()

    context = {"form": form, 'title': "Delivrer la chequier n° {}".format(object.reference, ),
               "object": object,  }
    return render(request, template, context)





@login_required
def bulk_action(request):
    action=request.POST["bulk_action"]
    if action=="priseencharge":
        return bulk_prise_en_charge(request)
    elif action=="livrerapc":
        return bulk_livraison_postecomptable(request)

    elif action=="livrergdc":
        return bulk_livraison_gerant(request)
    else: raise Http404





@login_required
@permission_required("bankcheck.priseencharge_chequier", raise_exception=True)
@transaction.atomic
def bulk_prise_en_charge(request):
    user=request.user
    success_url = reverse_lazy('bankcheck:chequiers_list')
    selected_licences_id = request.POST.getlist("selection")
    total = len(selected_licences_id)
    regs= Chequier.objects.filter(id__in=selected_licences_id)
    b=0
    for cheque in regs:
        try:
            cheque.prise_en_charge = True
            cheque.prise_en_charge_date = datetime.datetime.now()
            cheque.save()
            b+=1
        except Chequier.DoesNotExist:
            #create renewline from licene
            pass


    messages.add_message(request, messages.SUCCESS,"Prise en charge cheque {}/{}  fait avec succès".format(b,total))

    return redirect(success_url)






@login_required
@permission_required("bankcheck.delivrer_chequier", raise_exception=True)
@transaction.atomic
def bulk_livraison_gerant(request):
    user=request.user

    import time

    # current timestamp
    tpc = int(time.time())


    selected_licences_id = request.POST.getlist("selection")
    total = len(selected_licences_id)


    if total==0:
        message = "Merci de chosir au moins un  chéquier"
        messages.add_message(request, messages.ERROR, message)
        success_url = reverse_lazy('bankcheck:delivred_chequier_list')
        return redirect(success_url)

    regs= Chequier.objects.filter(id__in=selected_licences_id)

    c = regs.values_list("compte_id", flat=True).distinct().order_by()

    if len(c)>1 :
        message ="Merci de chosir des chéquiers destiné au meme compte de depot"
        messages.add_message(request, messages.ERROR,message)
        success_url = reverse_lazy('bankcheck:delivred_chequier_list')
        return redirect(success_url)
    b=0
    chequier=regs.last()
    if not hasattr(chequier,"gerant") or len(chequier.gerant)==0:
        message = "Gerant no trouve pour le chiquuier compte de depot"
        messages.add_message(request, messages.ERROR, message)
        success_url = reverse_lazy('bankcheck:delivred_chequier_list')
        return redirect(success_url)

    agent=chequier.gerant
    success_url = reverse_lazy('bankcheck:bulk_otp_en_charge', kwargs={"reference": str(tpc),"matricule":agent})


    for cheque in regs:
        try:
            cheque.otp_gerant = tpc
            cheque.save()

        except Chequier.DoesNotExist:
            #create renewline from licene
            pass


    #messages.add_message(request, messages.SUCCESS,"Prise en charge cheque {}/{} licences fait avec succès".format(b,total))

    return redirect(success_url)




@login_required
@permission_required("bankcheck.priseencharge_chequier", raise_exception=True)
@transaction.atomic
def bulk_livraison_postecomptable(request):
    user=request.user
    import time
    # current timestamp
    tpc = int(time.time())
    selected_licences_id = request.POST.getlist("selection")
    if len(selected_licences_id)==0:
        message = "Merci de chosir au moins un  chéquier"
        messages.add_message(request, messages.ERROR, message)
        success_url = reverse_lazy('bankcheck:dist_chequiers_list')
        return redirect(success_url)

    regs= Chequier.objects.filter(id__in=selected_licences_id)

    c = regs.values_list("compte__poste_id", flat=True).distinct().order_by()

    if len(c)>1 :
        message ="Merci de chosir des chéquiers destiné au meme poste comptable"
        messages.add_message(request, messages.ERROR,message)
        success_url = reverse_lazy('bankcheck:dist_chequiers_list')
        return redirect(success_url)

    chequier=regs.last()
    poste= chequier.compte.poste_id
    #success_url = reverse_lazy('bankcheck:bulk_otp_en_charge', kwargs={"reference": str(tpc),"matricule":agent})

    success_url = reverse_lazy('bankcheck:bulk_otp_en_charge_pc', kwargs={"reference": str(tpc), "matricule": poste})


    for cheque in regs:
        try:
            cheque.otp_apc = tpc
            cheque.save()
        except Chequier.DoesNotExist:
            #create renewline from licene
            pass
    #messages.add_message(request, messages.SUCCESS,"Prise en charge cheque {}/{} licences fait avec succès".format(b,total))
    return redirect(success_url)


@login_required()
def bulk_otp_en_charge(request,reference,matricule):
    user=request.user
    template = "bankcheck/bulk_confirm.html"
    success_url = reverse_lazy('bankcheck:chequiers_list')

    regs=None
    user= get_object_or_404(User,username=matricule)
    if hasattr(user,"gerant_cd"):
        agent=user.gerant_cd
        type_agent="Gerant Compte "
        regs = Chequier.objects.filter(otp_gerant=int(reference),gerant=matricule)
    elif hasattr(user,"agent_postecomptable"):
        agent=user.agent_postecomptable
        type_agent = "Agent Poste Comptable "
        regs = Chequier.objects.filter(otp_apc=int(reference),agent_pc=matricule)
    else: raise Http404

    chequier=regs.last()

    table = ChequierTable(regs, exclude=("selection", "action", "blocked", "created", "vide"))


    RequestConfig(request, paginate={"per_page": 20}).configure(table)

    b=0

    if request.method == 'POST':
        form = ChequierOtpForm(request.POST)
        if form.is_valid():

            if request and not is_ajax(request.META):
                token = form.cleaned_data["otp"]
                origin_otp=SimpleOtp.objects.filter(otp=token).last()
                if origin_otp and origin_otp.verify(token):
                    for chq in regs:
                        if hasattr(user, "gerant_cd"):
                            chq.delivered = True
                            chq.delivered_date=datetime.datetime.now()
                        if hasattr(user, "agent_postecomptable"):
                            chq.distribue = True
                            chq.distribue_date = datetime.datetime.now()
                        chq.save()
                        try:
                            chequier_status_changed.send(sender=type(chq), instance=chq)
                        except SigException as e:
                            messages.error(request,e.message,extra_tags="danger")
                            return redirect(success_url)
                    messages.success(request, "Chequiers distribués avec succès")
                else:messages.error(request, "Token invalide",extra_tags="danger")

            return redirect(success_url)
            messages.add_message(request, messages.SUCCESS,"Prise en charge cheque {}/{} licences fait avec succès".format(b,20))
            return redirect(success_url)
    else:
        otp = SimpleOtp()
        otp.phone = agent.phone.as_e164
        otp.generate_otp()
        otp.message = chequier.get_otp_retrait(otp.otp)
        otp.save()
        otp.send_otp()
        form = ChequierOtpForm()

    context = {"form": form, 'title': "Merci de renseigner L'OTP reçu".format(reference, ), "table":table,"agent":agent,"type_agent":type_agent}
    return render(request, template, context)




@login_required
#@user_role_required("ADMIN")
def compensecheques_list_view(request):
    user=request.user
    queryset = CompenseCheque.objects.by_agent(user)
    create_url=None
    queryset_filter = CompenseChequeFilter(request.GET, request=request, queryset=queryset)

    can_create_dcp=user.has_perm('bankcheck.add_compensecheque') and not CompenseCheque.check_if_api_open()
    if can_create_dcp:
        create_url=reverse_lazy('bankcheck:create_compensecheque')
    #if user.has_perm('bankcheck.change_commande') or user.has_perm('bankcheck.delete_commande'):
    table = CompenseChequeTable(queryset_filter.qs)
    title = _("Liste Compenses chèques")
    data_title=_("Liste Compenses chèques")
    create_title="Nouvelle Compense Chèque"

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/default_list.html', {"create_title":create_title,"create_url":create_url,"can_create_dcp":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})


@login_required
#@user_role_required("ADMIN")
def miseenoppositions_list_view(request):
    user=request.user
    queryset = MiseEnOpposition.objects.by_agent(user)
    create_url=None
    queryset_filter = MiseEnOppositionFilter(request.GET, request=request, queryset=queryset)

    can_create_dcp=user.has_perm('bankcheck.add_miseenopposition')
    if can_create_dcp:
        create_url=reverse_lazy('bankcheck:create_miseenopposition')
    #if user.has_perm('bankcheck.change_commande') or user.has_perm('bankcheck.delete_commande'):
    table = MiseEnOppositionTable(queryset_filter.qs)
    title = _("LISTE DES CHÈQUES EN OPPOSITON ")
    data_title=_("LISTE DES CHÈQUES EN OPPOSITON")
    create_title="Nouvelle Mise en opposition Chèque"

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/default_list.html', {"create_title":create_title,"create_url":create_url,"can_create_dcp":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})





@login_required
#@user_role_required("ADMIN")
def annulationcheques_list_view(request):
    user=request.user
    queryset = AnnulationCheque.objects.by_agent(user)
    create_url=None
    queryset_filter = AnnulationChequeFilter(request.GET, request=request, queryset=queryset)

    can_create_dcp=user.has_perm('bankcheck.add_annulationcheque')
    if can_create_dcp:
        create_url=reverse_lazy('bankcheck:create_annulationcheque')
    #if user.has_perm('bankcheck.change_commande') or user.has_perm('bankcheck.delete_commande'):
    table = AnnulationChequeTable(queryset_filter.qs)
    title = _("LISTE DES CHEQUES ANNULES")
    data_title=_("LISTE DES CHEQUES ANNULES")
    create_title="Nouvelle Annulation Chèque"

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/default_list.html', {"create_title":create_title,"create_url":create_url,"can_create_dcp":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})






@method_decorator([user_role_required([Role.AGENT_DAP,Role.GERANT,Role.AGENT_PC])], name='dispatch')
class CompenseChequeCreateView(PermissionRequiredMixin, BSModalCreateView):
    template_name = 'core/add_entity.html'
    form_class = CompenseChequeForm
    model_name = form_class._meta.model._meta.model_name
    success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
    success_url = reverse_lazy('bankcheck:{}_list'.format(model_name, ))
    permission_required = ('bankcheck.add_{}'.format(model_name, ),)

    def get(self, request, *args, **kwargs):
        if CompenseCheque.check_if_api_open():
            msg = "Api disponible pour les compense"
            messages.success(request, msg)
            return redirect(self.success_url)

        return super().get(request, *args, **kwargs)

    # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            self.object = form.save(commit=False)
            cheque=Cheque.objects.get(reference=self.object.reference)
            if not cheque.can_acces(self.request.user):
                messages.error(self.request, "Chèque introuvable",extra_tags="danger")
                return redirect(self.success_url)
            self.object.cheque = cheque
            self.object.amount=cheque.amount
            self.object.trx=cheque.trx
            self.object.creator = self.request.user
            form.save()
            self.object.cheque.en_compense = True

            self.object.cheque.compense_date = datetime.datetime.now()
            self.object.cheque.save()
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        name = self.form_class._meta.model._meta.verbose_name
        context['title'] = "Nouvelle  {}".format(name, )
        return context


@method_decorator([user_role_required([Role.AGENT_DAP,Role.GERANT,Role.AGENT_PC])], name='dispatch')
class MiseEnOppositionCreateView(PermissionRequiredMixin, BSModalCreateView):
    template_name = 'core/add_entity.html'
    form_class = MiseEnOppositionForm
    model_name = form_class._meta.model._meta.model_name
    success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
    success_url = reverse_lazy('bankcheck:{}_list'.format(model_name, ))
    permission_required = ('bankcheck.add_{}'.format(model_name, ),)

    # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        user=self.request.user
        if not is_ajax(self.request.META):
            self.object = form.save(commit=False)
            cheque=Cheque.objects.get(reference=self.object.reference)
            if not cheque.can_acces(self.request.user):
                messages.error(self.request, "Chèque introuvable",extra_tags="danger")
                return redirect(self.success_url)
            self.object.cheque = cheque
            self.object.amount=cheque.amount
            self.object.trx=cheque.trx
            self.object.demandeur = self.request.user
            if hasattr(user,"agent_postecomptable"):
                self.object.acceptation_date=datetime.datetime.now()
                self.object.accepter=True
                self.object.accepteur=user
            if hasattr(user,"agent_dap"):
                self.object.acceptation_date=datetime.datetime.now()
                self.object.accepter=True
                self.object.accepteur=user

            form.save()
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        name = self.form_class._meta.model._meta.verbose_name
        context['title'] = "Nouvelle  {}".format(name, )
        return context



@method_decorator([user_role_required([Role.AGENT_DAP,Role.GERANT,Role.AGENT_PC])], name='dispatch')
class AnnulationChequeCreateView(PermissionRequiredMixin, BSModalCreateView):
    template_name = 'core/add_entity.html'
    form_class = AnnulationChequeForm
    model_name = form_class._meta.model._meta.model_name
    success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
    success_url = reverse_lazy('bankcheck:{}_list'.format(model_name, ))
    permission_required = ('bankcheck.add_{}'.format(model_name, ),)

    # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        user=self.request.user

        if not is_ajax(self.request.META):
            self.object = form.save(commit=False)
            cheque=Cheque.objects.get(reference=self.object.reference)
            if not cheque.can_acces(self.request.user):
                messages.error(self.request, "Chèque introuvable",extra_tags="danger")
                return redirect(self.success_url)
            can_update_cheque=False
            if hasattr(user, "gerant_cd"):
                try:
                    if cheque.can_use_in_op():
                        self.object.acceptation_date = datetime.datetime.now()
                        self.object.accepter = True
                        self.object.accepteur = user
                        self.object.observations = "Annulation effective"
                        self.object.approuver = True
                        self.object.approbation_date = datetime.datetime.now()
                        self. object.approbateur = user
                except SigException as e:
                    messages.error(self.request, e.message, extra_tags="danger")
                    return redirect(self.success_url)

            if hasattr(user,"agent_postecomptable"):
                self.object.acceptation_date=datetime.datetime.now()
                self.object.accepter=True
                self.object.accepteur=user
            if hasattr(user,"agent_dap"):
                self.object.acceptation_date=datetime.datetime.now()
                self.object.accepter=True
                self.object.accepteur=user
            self.object.cheque = cheque
            self.object.amount = cheque.amount
            self.object.trx = cheque.trx
            self.object.demandeur = self.request.user
            form.save()

            if can_update_cheque:
                self.object.cheque.en_annulation = True
                self.object.cheque.annulation_date = datetime.datetime.now()
                self.object.cheque.save()

        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        name = self.form_class._meta.model._meta.verbose_name
        context['title'] = "Nouvelle  {}".format(name, )
        return context




@method_decorator([user_role_required([Role.AGENT_DAP,Role.GERANT,Role.AGENT_PC])], name='dispatch')
class CompenseChequeUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    model = CompenseCheque
    template_name = 'core/update_entity.html'
    form_class = CompenseChequeForm
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('bankcheck.change_{}'.format(model_name,),)
    success_message = 'Success: Mise àjour {} avec succès.'.format(model._meta.verbose_name,)
    success_url = reverse_lazy('bankcheck:{}_list'.format(model_name,))
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour  {} : {}".format(self.object._meta.verbose_name,self.object)
        return context


@method_decorator([user_role_required([Role.AGENT_DAP,Role.GERANT,Role.AGENT_PC])], name='dispatch')
class CompenseChequeDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    model = CompenseCheque
    permission_required = ('bankcheck.delete_{}'.format(model._meta.model_name),)

    success_message = 'Success: Supression  avec succès'
    success_url = reverse_lazy('bankcheck:{}_list'.format(model._meta.model_name,))

    template_name = "core/confirm_delete_entity.html"


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Suppression  : {}".format(self.object.name,)
        return context



@method_decorator([user_role_required([Role.AGENT_DAP,Role.GERANT,Role.AGENT_PC])], name='dispatch')
class AnnulationChequeUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    model = AnnulationCheque
    template_name = 'core/update_entity.html'
    form_class = AnnulationChequeForm
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('bankcheck.change_{}'.format(model_name,),)
    success_message = 'Success: Mise àjour {} avec succès.'.format(model._meta.verbose_name,)
    success_url = reverse_lazy('bankcheck:{}_list'.format(model_name,))
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour  {} : {}".format(self.object._meta.verbose_name,self.object)
        return context


@method_decorator([user_role_required([Role.AGENT_DAP,Role.GERANT,Role.AGENT_PC])], name='dispatch')
class AnnulationChequeDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    model = AnnulationCheque
    permission_required = ('bankcheck.delete_{}'.format(model._meta.model_name),)

    success_message = 'Success: Supression  avec succès'
    success_url = reverse_lazy('bankcheck:{}_list'.format(model._meta.model_name,))

    template_name = "core/confirm_delete_entity.html"


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Suppression  : {}".format(self.object.cheque.reference,)
        return context



@method_decorator([user_role_required([Role.AGENT_DAP,Role.GERANT,Role.AGENT_PC])], name='dispatch')
class MiseEnOppositionUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    model = MiseEnOpposition
    template_name = 'core/update_entity.html'
    form_class = MiseEnOppositionForm
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('bankcheck.change_{}'.format(model_name,),)
    success_message = 'Success: Mise àjour {} avec succès.'.format(model._meta.verbose_name,)
    success_url = reverse_lazy('bankcheck:{}_list'.format(model_name,))
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour  {} : {}".format(self.object._meta.verbose_name,self.object)
        return context


@method_decorator([user_role_required([Role.AGENT_DAP,Role.GERANT,Role.AGENT_PC])], name='dispatch')
class MiseEnOppositionDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    model = MiseEnOpposition
    permission_required = ('bankcheck.delete_{}'.format(model._meta.model_name),)

    success_message = 'Success: Supression  avec succès'
    success_url = reverse_lazy('bankcheck:{}_list'.format(model._meta.model_name,))

    template_name = "core/confirm_delete_entity.html"


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Suppression  : {}".format(self.object.name,)
        return context


@login_required
@transaction.atomic()
@permission_required("bankcheck.accepter_annulationcheque", raise_exception=True)
def accepter_annulationcheque_view(request, reference):
    template = "cddaccount/validate_ordrepayment.html"
    user = request.user
    success_url = reverse_lazy('bankcheck:annulationcheque_list')
    object = get_object_or_404(AnnulationCheque, reference=reference)

    if not object.can_acces(user):
        raise Http404

    if request.method == 'POST':
        form = ChequierSimpleForm(request.POST)
        if form.is_valid():
            if request and not is_ajax(request.META):
                description = form.cleaned_data["description"]
                object.description = description
                object.accepter = True
                object.acceptation_date = datetime.datetime.now()
                object.accepteur = user
                object.approuver = True
                object.approbation_date = datetime.datetime.now()
                object.approbateur = user
                object.save()
                object.cheque.en_annulation = True

                object.cheque.annulation_date = datetime.datetime.now()
                object.cheque.save()
            messages.success(request, "Demande d'annulation de chèque accepter et en attente d'approbation ")

            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")

    else:
        form = ChequierSimpleForm()

    context = {"form": form, 'title': "Accepter la demande d'annulation de cheque {}".format(object.reference, )}
    return render(request, template, context)


@login_required
@transaction.atomic()
@permission_required("bankcheck.approuver_annulationcheque", raise_exception=True)
def approuver_annulationcheque_view(request, reference):
    template = "cddaccount/validate_ordrepayment.html"
    user = request.user
    success_url = reverse_lazy('bankcheck:annulationcheque_list')
    object = get_object_or_404(AnnulationCheque, reference=reference)

    if not object.can_acces(user):
        raise Http404

    if request.method == 'POST':
        form = ChequierSimpleForm(request.POST)
        if form.is_valid():
            if request and not is_ajax(request.META):
                description = form.cleaned_data["description"]
                object.description = description
                object.approuver = True
                object.approbation_date = datetime.datetime.now()
                object.approbateur = user
                object.save()
                object.cheque.en_annulation = True
                object.cheque.annulation_date = datetime.datetime.now()
                object.cheque.save()
            messages.success(request, "Annulation de chèque approuvée  ")

            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")

    else:
        form = ChequierSimpleForm()

    context = {"form": form, 'title': "Approuver d'annulation de cheque {}".format(object.reference, )}
    return render(request, template, context)


@login_required
@transaction.atomic()
@permission_required("bankcheck.accepter_miseenopposition", raise_exception=True)
def accepter_miseenopposition_view(request, reference):
    template = "cddaccount/validate_ordrepayment.html"
    user = request.user
    success_url = reverse_lazy('bankcheck:miseenopposition_list')
    object = get_object_or_404(MiseEnOpposition, reference=reference)

    if not object.can_acces(user):
        raise Http404

    if request.method == 'POST':
        form = ChequierSimpleForm(request.POST)
        if form.is_valid():
            if request and not is_ajax(request.META):
                description = form.cleaned_data["description"]
                object.description = description
                object.accepter = True
                object.acceptation_date = datetime.datetime.now()
                object.accepteur = user
                object.approuver = True
                object.approbation_date = datetime.datetime.now()
                object.approbateur = user

                object.save()
                object.cheque.en_mis_op = True
                object.cheque.mis_op_date = datetime.datetime.now()
                object.cheque.save()
            messages.success(request, "Demande mise en opposition de chèque accepter et en attente d'approbation ")

            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")

    else:
        form = ChequierSimpleForm()

    context = {"form": form, 'title': "Accepter la demande de mise en opposition de cheque {}".format(object.reference, )}
    return render(request, template, context)



@login_required
@transaction.atomic()
@permission_required("bankcheck.approuver_miseenopposition", raise_exception=True)
def approuver_miseenopposition_view(request, reference):
    template = "cddaccount/validate_ordrepayment.html"
    user = request.user
    success_url = reverse_lazy('bankcheck:miseenopposition_list')
    object = get_object_or_404(MiseEnOpposition, reference=reference)

    if not object.can_acces(user):
        raise Http404

    if request.method == 'POST':
        form = ChequierSimpleForm(request.POST)
        if form.is_valid():
            if request and not is_ajax(request.META):
                description = form.cleaned_data["description"]
                object.description = description
                object.approuver = True
                object.approbation_date = datetime.datetime.now()
                object.approbateur = user
                object.save()
                object.cheque.en_mis_op=True
                object.cheque.mis_op_date=datetime.datetime.now()
                object.cheque.save()

            messages.success(request, "Mise en opposition de chèque approuvée  ")

            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")

    else:
        form = ChequierSimpleForm()

    context = {"form": form, 'title': "Approuver la mise en opposition de cheque {}".format(object.reference, )}
    return render(request, template, context)






@login_required
#@user_role_required("ADMIN")
def cheques_list_view(request):
    user=request.user
    queryset = Cheque.objects.by_agent(user).filter(delivred=True)
    create_url=None
    queryset_filter = ChequeFilter(request.GET, request=request, queryset=queryset)

    can_create_dcp=False
    if can_create_dcp:
        create_url=reverse_lazy('bankcheck:create_annulationcheque')
    #if user.has_perm('bankcheck.change_commande') or user.has_perm('bankcheck.delete_commande'):
    table = ChequeFullTable(queryset_filter.qs)
    title = _("Liste des Chèques récupérés")
    data_title=_("Chèques récupérés")
    create_title="Nouvelle  Chèque"

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/default_list.html', {"create_title":create_title,"create_url":create_url,"can_create_dcp":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})




@login_required
@transaction.atomic()
@permission_required("bankcheck.accepter_rejetcheque", raise_exception=True)
def accepter_rejetcheque_view(request, reference):
    template = "cddaccount/validate_ordrepayment.html"
    user = request.user
    success_url = reverse_lazy('bankcheck:rejetcheque_list')
    object = get_object_or_404(RejetCheque, reference=reference)

    if not object.can_acces(user):
        raise Http404

    if request.method == 'POST':
        form = ChequierSimpleForm(request.POST)
        if form.is_valid():
            if request and not is_ajax(request.META):
                description = form.cleaned_data["description"]
                object.observations = description
                object.accepter = True
                object.acceptation_date = datetime.datetime.now()
                object.accepteur = user
                object.approuver = True
                object.approbation_date = datetime.datetime.now()
                object.approbateur = user
                object.save()
                object.cheque.en_annulation = True
                object.cheque.annulation_date = datetime.datetime.now()
                object.cheque.save()
                #on annulle lop lié
                op=OrdrePayment.objects.filter(sig_reference=object.cheque.reference).last()
                if op:
                    print("je passe")
                    cancel_op(op,user,description)
            messages.success(request, "Demande de rejet de chèque accepter")

            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")

    else:
        form = ChequierSimpleForm()

    context = {"form": form, 'title': "Accepter la demande de rejet de cheque {}".format(object.reference, )}
    return render(request, template, context)


@method_decorator([user_role_required([Role.GERANT,Role.AGENT_PC])], name='dispatch')
class RejetChequeUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    model = RejetCheque
    template_name = 'core/update_entity.html'
    form_class = RejetChequeForm
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('bankcheck.change_{}'.format(model_name,),)
    success_message = 'Success: Mise àjour {} avec succès.'.format(model._meta.verbose_name,)
    success_url = reverse_lazy('bankcheck:{}_list'.format(model_name,))
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour  {} : {}".format(self.object._meta.verbose_name,self.object)
        return context


@method_decorator([user_role_required([Role.GERANT,Role.AGENT_PC])], name='dispatch')
class RejetChequeDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    model = RejetCheque
    permission_required = ('bankcheck.delete_{}'.format(model._meta.model_name),)

    success_message = 'Success: Supression  avec succès'
    success_url = reverse_lazy('bankcheck:{}_list'.format(model._meta.model_name,))

    template_name = "core/confirm_delete_entity.html"


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Suppression  : {}".format(self.object.cheque.reference,)
        return context





@method_decorator([user_role_required([Role.GERANT,Role.AGENT_PC])], name='dispatch')
class RejetChequeCreateView(PermissionRequiredMixin, BSModalCreateView):
    template_name = 'core/add_entity.html'
    form_class = RejetChequeForm
    model_name = form_class._meta.model._meta.model_name
    success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
    success_url = reverse_lazy('bankcheck:{}_list'.format(model_name, ))
    permission_required = ('bankcheck.add_{}'.format(model_name, ),)

    # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            self.object = form.save(commit=False)
            cheque=Cheque.objects.get(reference=self.object.reference)
            if not cheque.can_acces(self.request.user):
                messages.error(self.request, "Chèque introuvable",extra_tags="danger")
                return redirect(self.success_url)

            op = OrdrePayment.objects.filter(sig_reference=cheque.reference).last()
            if not op:
                messages.error(self.request, "Aucun odre de payement n'est lié à ce chèque", extra_tags="danger")
                return redirect(self.success_url)

            if op and op.cheque_delivred and cheque.delivred:
                messages.error(self.request, "Chèque déjà réceptionné. Il faut faire une mise en opposition.", extra_tags="danger")
                return redirect(self.success_url)
            self.object.cheque = cheque
            self.object.amount = cheque.amount
            self.object.op = cheque.trx
            self.object.demandeur = self.request.user

            form.save()



        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        name = self.form_class._meta.model._meta.verbose_name
        context['title'] = "Nouveau  {}".format(name, )
        return context




@login_required
#@user_role_required("ADMIN")
def rejetcheques_list_view(request):
    user=request.user
    queryset = RejetCheque.objects.by_agent(user)
    create_url=None
    queryset_filter = RejetChequeFilter(request.GET, request=request, queryset=queryset)

    can_create_dcp=user.has_perm('bankcheck.add_rejetcheque')
    if can_create_dcp:
        create_url=reverse_lazy('bankcheck:create_rejetcheque')
    #if user.has_perm('bankcheck.change_commande') or user.has_perm('bankcheck.delete_commande'):
    table = RejetChequeTable(queryset_filter.qs)
    title = _("LISTE DES CHEQUES REJETES")
    data_title=_("LISTE DES CHEQUES REJETES")
    create_title="Nouvel Rejet Chèque"

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/default_list.html', {"create_title":create_title,"create_url":create_url,"can_create_dcp":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})






@login_required
#@user_role_required("ADMIN")
def chequescannes_list_view(request):
    user=request.user
    queryset = ChequeScanne.objects.by_agent(user)
    create_url=None
    queryset_filter = ChequeScanneFilter(request.GET, request=request, queryset=queryset)

    can_create_dcp = False
    if can_create_dcp:
        create_url=reverse_lazy('bankcheck:create_compensecheque')
    #if user.has_perm('bankcheck.change_commande') or user.has_perm('bankcheck.delete_commande'):
    table = ChequeScanneTable(queryset_filter.qs)
    title = _("Liste des chèques suspects")
    data_title=_("Liste des chèques suspects")
    create_title="Nouveau chèque suspect"

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/default_list.html', {"create_title":create_title,"create_url":create_url,"can_create_dcp":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})


@login_required
def bordereau_commande_view(request, reference):
    template = "bankcheck/bordereau.html"
    user = request.user
    object = get_object_or_404(Commande, reference=reference)
    chequiers=Chequier.objects.filter(demande=reference).reverse()
    if not hasattr(user,"agent_dap"):  raise Http404

    compte = object.compte
    if not object.can_acces(user):
        raise Http404
    context = {"commande": object, 'title': "Bon de commande N° {}".format(reference, ), "compte": compte,"chequiers":chequiers}
    return render(request, template, context)



@login_required
#@user_role_required("ADMIN")
def recep_chequier_list_view(request):
    user=request.user
    queryset = Chequier.objects.by_agent(user).filter(prise_en_charge=False)
    create_url=None
    queryset_filter = ChequierFilter(request.GET, request=request, queryset=queryset)
    #table = CommandeTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('bankcheck.add_chequier')
    if can_create_dcp:
        create_url=reverse_lazy('bankcheck:commande_chequier_view')
    #if user.has_perm('bankcheck.change_commande') or user.has_perm('bankcheck.delete_commande'):
    table = ChequierTable(queryset_filter.qs,exclude=("selection","action"))
    if hasattr(user,"agent_dap") or hasattr(user,"agent_postecomptable"):
        table = ChequierTable(queryset_filter.qs)
    title = _("Liste chéquiers")
    data_title=_("Liste chéquiers")
    action_reception=True

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/list_chequier.html', {"action_reception":action_reception,"create_url":create_url,"can_create_dcp":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})




@login_required
#@user_role_required("ADMIN")
def dist_chequier_list_view(request):
    user=request.user
    queryset = Chequier.objects.by_agent(user).filter(prise_en_charge=True,distribue=False)
    create_url=None
    queryset_filter = ChequierFilter(request.GET, request=request, queryset=queryset)
    #table = CommandeTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('bankcheck.add_chequier')
    if can_create_dcp:
        create_url=reverse_lazy('bankcheck:commande_chequier_view')
    #if user.has_perm('bankcheck.change_commande') or user.has_perm('bankcheck.delete_commande'):
    table = ChequierTable(queryset_filter.qs,exclude=("selection","action"))
    if hasattr(user,"agent_dap") or hasattr(user,"agent_postecomptable"):
        table = ChequierTable(queryset_filter.qs)
    title = _("Liste chéquiers")
    data_title=_("Liste chéquiers")
    action_dist=True

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/list_chequier.html', {"action_dist":action_dist,"create_url":create_url,"can_create_dcp":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})



@login_required
#@user_role_required("ADMIN")
def affecter_chequier_list_view(request):
    user=request.user
    queryset = Chequier.objects.by_agent(user).filter(prise_en_charge=True,distribue=True)
    create_url=None
    queryset_filter = ChequierFilter(request.GET, request=request, queryset=queryset)
    #table = CommandeTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('bankcheck.add_chequier')
    if can_create_dcp:
        create_url=reverse_lazy('bankcheck:commande_chequier_view')
    #if user.has_perm('bankcheck.change_commande') or user.has_perm('bankcheck.delete_commande'):
    table = ChequierTable(queryset_filter.qs,exclude=("selection","action"))
    if hasattr(user,"agent_dap") or hasattr(user,"agent_postecomptable"):
        table = ChequierTable(queryset_filter.qs)
    title = _("Liste chéquiers")
    data_title=_("Liste chéquiers")
    action_reception=True

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/list_chequier.html', {"action_reception":action_reception,"create_url":create_url,"can_create_dcp":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})


# @method_decorator([user_role_required(Role.GERANT)], name='dispatch')
class ComptableMatiereCreateView(PermissionRequiredMixin, BSModalCreateView):
    template_name = 'core/add_entity.html'
    form_class = ComptableMatiereForm
    model_name = form_class._meta.model._meta.model_name
    success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
    success_url = reverse_lazy('bankcheck:{}_list'.format(model_name, ))
    permission_required = ('bankcheck.add_{}'.format(model_name, ),)


    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


    def form_valid(self, form):
        if not is_ajax(self.request.META):
            obj = form.save(commit=False)
            obj.poste = self.request.user.agent_postecomptable.poste
            obj.save()
        return super().form_valid(form)

        def get_context_data(self, *args, **kwargs):
            context = super().get_context_data(*args, **kwargs)
            name = self.form_class._meta.model._meta.verbose_name
            context['title'] = "Nouveau comptable matière"
            return context


#@method_decorator([user_role_required(Role.GERANT)], name='dispatch')
class ComptableMatiereDeleteView(PermissionRequiredMixin, BSModalDeleteView):
	# specify the model you want to use
	c = "comptablematiere"
	model = ComptableMatiere
	permission_required = ('bankcheck.delete_{}'.format(c, ),)

	# can specify success url
	# url to redirect after successfully
	# deleting object
	success_message = 'Success: Supression agent saisie compte de dépôt'
	success_url = reverse_lazy('bankcheck:{}_list'.format(c, ))

	template_name = "core/confirm_delete_entity.html"

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Suppression agent : {}".format(self.object, )
		return context



class ComptableMatiereUpdateView(PermissionRequiredMixin, BSModalUpdateView):
	model = ComptableMatiere
	c = "comptablematiere"
	template_name = 'core/update_entity.html'
	form_class = ComptableMatiereForm
	permission_required = ('bankcheck.change_{}'.format(c, ),)
	success_message = 'Success: Mise à jour agent saisie compte de dépôt.'
	success_url = reverse_lazy('bankcheck:{}_list'.format(c, ))

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(*args, **kwargs)
		context['title'] = "Mise à jour de {} : {}".format(self.object._meta.verbose_name, self.object)
		return context



@login_required
# @user_role_required("ADMIN")
def comptablematiere_list_view(request):
	user =request.user
	create_url = reverse_lazy('bankcheck:create_comptablematiere')

	user = request.user
	queryset = ComptableMatiere.objects.by_agent(user)
	queryset_filter = ComptableMatiereFilter(request.GET, request=request, queryset=queryset)
	table = ComptableMatiereTable(queryset_filter.qs, exclude=("action",))
	can_create_dcp = user.has_perm('bankcheck.add_comptablematiere')
	if user.has_perm('bankcheck.change_comptablematiere') or user.has_perm('bankcheck.delete_comptablematiere'):
		table = ComptableMatiereTable(queryset_filter.qs)
	title = _("Comptable matière")
	data_title = _("Comptable matière")
	create_tilte = "Nouveau Comptable matière"

	RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
	return render(request, 'core/default_list.html',
	              {"create_tilte":create_tilte,"create_url": create_url, "can_create_entite": can_create_dcp, "data_title": data_title,
	               'table': table, "filter_form": queryset_filter.form, "title": title, "index": "0", "sens": "desc"})





def generatechequier(commande,bordereau,user,sequence_settings):
    start_sequence = sequence_settings.last_sequence
    commande.first_sequence = start_sequence + 1

    v = commande.items.all()
    initial = []


    for item in v:
        for i in range(item.nombres):
            a = item.as_dict()
            last_sequence = start_sequence + item.type.taille
            a["debut"] = start_sequence + 1
            a["fin"] = last_sequence
            initial.append(a)
            start_sequence = last_sequence
            commande.last_sequence = last_sequence

    for form in initial:
        type = form['type']
        debut = form['debut']
        fin = form['fin']
        item = Chequier()
        item.reference = debut
        item.compte = commande.compte
        item.demande = commande.reference
        item.dap = user.agent_dap.dap
        item.editeur = user.agent_dap
        item.fin = fin
        item.debut = debut
        item.type = type
        item.is_printed=True
        item.taille = type.taille
        if commande.demandeur:
            item.phone_gerant = commande.demandeur.phone.as_e164
            item.gerant = commande.demandeur.matricule
        if commande.agent_pc:
            item.phone_postecomptable = commande.agent_pc.phone.as_e164
            item.agent_pc = commande.agent_pc.matricule
        item.save()
        bordereau.chequiers.add(item)
    commande.agent_dap = user.agent_dap
    commande.status = STATUS_COMMANDE.TRAITE
    commande.traiter = True
    commande.process_date_date = datetime.datetime.now()
    commande.save()
    bordereau.save()
    sequence_settings.last_sequence = commande.last_sequence
    sequence_settings.save()




@login_required
#@user_role_required("ADMIN")
def bordereau_list_view(request):
    user=request.user
    queryset = Bordereau.objects.all()
    create_url=None
    queryset_filter = BordereauFilter(request.GET, request=request, queryset=queryset)
    can_create_dcp=user.has_perm('bankcheck.add_chequier')

    table = BordereauTable(queryset_filter.qs,exclude=("selection","action"))

    title = _("Liste Bordereaux")
    data_title=_("Liste Bordereaux")
    action_reception=True

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/default_list.html', {"action_reception":action_reception,"create_url":create_url,"can_create_dcp":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})




@login_required
#@user_role_required("ADMIN")
def delivred_chequier_list_view(request):
    user=request.user
    queryset = Chequier.objects.by_agent(user).filter(prise_en_charge=True,distribue=True,delivered=False)
    create_url=None
    queryset_filter = ChequierFilter(request.GET, request=request, queryset=queryset)
    #table = CommandeTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('bankcheck.add_chequier')
    if can_create_dcp:
        create_url=reverse_lazy('bankcheck:commande_chequier_view')
    #if user.has_perm('bankcheck.change_commande') or user.has_perm('bankcheck.delete_commande'):
    table = ChequierTable(queryset_filter.qs,exclude=("selection","action"))
    if hasattr(user,"agent_dap") or hasattr(user,"agent_postecomptable"):
        table = ChequierTable(queryset_filter.qs)
    title = _("Liste chéquiers non délivrés")
    data_title=_("Liste chéquiers non délivrés")
    action_reception=True

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'bankcheck/list_chequier.html', {"action_reception":action_reception,"create_url":create_url,"can_create_dcp":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})






@login_required()
def bulk_otp_en_charge_pc(request,reference,matricule):
    user=request.user
    template = "bankcheck/bulk_confirm_pc.html"
    success_url = reverse_lazy('bankcheck:chequiers_list')


    poste= get_object_or_404(PosteComptable,id=matricule)
    mdt = ProfilePC.objects.filter(poste=poste)
    matieres=ComptableMatiere.objects.filter(poste=poste)

    regs = Chequier.objects.filter(otp_apc=int(reference))

    table = ChequierTable(regs, exclude=("selection", "action", "blocked", "created", "vide"))

    RequestConfig(request, paginate={"per_page": 20}).configure(table)


    if request.method == 'POST':
        form = ChequierdapOtpForm(request.POST)
        form.fields["agent"].queryset = mdt
        form.fields["matiere"].queryset = matieres

        if form.is_valid():

            if request and not is_ajax(request.META):
                token = form.cleaned_data["otp"]
                origin_otp=SimpleOtp.objects.filter(otp=token).last()
                if origin_otp and origin_otp.verify(token):
                    for chq in regs:
                        if hasattr(user, "gerant_cd"):
                            chq.delivered = True
                            chq.delivered_date=datetime.datetime.now()
                        if hasattr(user, "agent_postecomptable"):
                            chq.distribue = True
                            chq.distribue_date = datetime.datetime.now()
                        chq.save()
                        try:
                            chequier_status_changed.send(sender=type(chq), instance=chq)
                        except SigException as e:
                            messages.error(request,e.message,extra_tags="danger")
                            return redirect(success_url)
                    messages.success(request, "Chequiers distribués avec succès")
                else:messages.error(request, "Token invalide",extra_tags="danger")

            return redirect(success_url)
            messages.add_message(request, messages.SUCCESS,"Prise en charge cheque {}/{} licences fait avec succès".format(b,20))
            return redirect(success_url)
    else:

        form = ChequierdapOtpForm()
        form.fields["agent"].queryset = mdt
        form.fields["matiere"].queryset = matieres

    context = {"table":table,"form": form, 'title': "Merci de renseigner L'OTP reçu".format(reference, ), "poste":poste.id,"bulkreference":reference,"send_otp":False}
    return render(request, template, context)









from bankcheck.forms import BENEF_CHOICES,TakeChequeVerifyPaymentForm
@login_required
@transaction.atomic()
@permission_required("bankcheck.delivrer_chequier", raise_exception=True)
def delivrer_chequier_view(request, reference):
	template = "bankcheck/delivrer_chequier.html"
	user = request.user

	success_url =  reverse_lazy('bankcheck:chequiers_list')
	chequier = get_object_or_404(Chequier, reference=reference)
	gerant = chequier.compte.get_current_gerant()
	phone = None


	if not chequier.can_acces(user):
		raise Http404

	if gerant:
		mdt = gerant.mandataires.all()
		phone = gerant.phone.as_e164
	else:
		mdt = Mandataire.objects.none()

	if request.method == 'POST':
		form = TakeChequeVerifyPaymentForm(request.POST)
		form.fields["mandataire"].queryset = mdt
		if form.is_valid():
			# if type==BENEF_CHOICES.BENEFICIAIRE and object.phone_receptionnaire :
			#	phone=object.phone_receptionnaire.as_e164

			if type == BENEF_CHOICES.MANDATAIRE:
				mandataire = form.cleaned_data["mandataire"]
				phone = mandataire.phone.as_e164
			if phone:
				chequier.phone_gerant = phone
				chequier.generate_otp_and_save()
				chequier.send_cheque_otp(phone)
				success_url = success_url
				messages.add_message(request, messages.SUCCESS,
				                     "Code otp envoyé avec succès")

			else:
				messages.add_message(request, messages.ERROR,
				                     "Aucun téléphoone disponibble pour ennvoyé l'otp")
			return redirect(success_url)

	else:
		form = TakeChequeVerifyPaymentForm()
		form.fields["mandataire"].queryset = mdt

	context = {"chequier": chequier.reference,  'mandataire': mdt, "form": form,
	           "object": chequier, "compte": chequier.compte,
	           'title': "choisir le type de beneficiaire ".format(chequier.reference, ), "send_otp": False}
	return render(request, template, context)


import  traceback

@login_required
@transaction.atomic()
@permission_required("bankcheck.delivrer_chequier", raise_exception=True)
def send_otp_sms_for_chequier(request):
    # request should be ajax and method should be GET.
    obj=None
    phone=None
    otp_reference=None
    send_otp = False
    if request.method == "POST":
        try:
            querydict_data = request.POST.dict()

            _type = querydict_data.get("type")


            cheque_ref = querydict_data.get("chequier")
            chequier = Chequier.objects.get(reference=cheque_ref)
            gerant = chequier.compte.get_current_gerant()

            if _type == BENEF_CHOICES.MANDATAIRE:
                mandataire_id = querydict_data.get("mandataire")
                mandataire = Mandataire.objects.get(id=mandataire_id)
                phone = mandataire.phone.as_e164
            elif _type == BENEF_CHOICES.GERANT:
                phone=gerant.phone.as_e164
            if phone:
                otp = SimpleOtp()
                otp.phone = phone
                otp.generate_otp()
                otp.message = chequier.get_otp_retrait(otp.otp)
                otp.save()
                otp.send_otp()
                send_otp = True


        except:
            traceback.print_exc()
            pass
    context={"send_otp":send_otp,"chequier":cheque_ref,"otp_reference":otp_reference}
    return render(request, 'bankcheck/component.html', context)


from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
import datetime
@login_required()
def verify_otp_sms_for_chequier(request):
    # request should be ajax and method should be GET.
    obj=None
    send_otp=True
    if request.method == "POST":
        try:
            print(request.POST)
            token = request.POST.get("otp")
            ordre_ref = request.POST.get("chequier")
            otp_reference = request.POST.get("otp_reference")

            chequier = Chequier.objects.get(reference=ordre_ref)

            origin_otp = SimpleOtp.objects.filter(otp=token).last()
            if origin_otp and origin_otp.verify(token):
                chequier.delivered = True
                chequier.delivered_date = datetime.datetime.now()
                # object.observations = description
                # object.creator = user
                chequier.save()
                try:
                    chequier_status_changed.send(sender=type(chequier), instance=chequier)
                    messages.success(request, "Chequier delevré avec succès")
                except SigException as e:
                    messages.error(request, e.message, extra_tags="danger")

                v =  reverse_lazy('bankcheck:chequiers_list')
                response = HttpResponse()
                response["HX-Redirect"] = v
                return response

            else:
                messages.error(request, "Token invalide", extra_tags="danger")
                send_otp = True
                messages.error(request, "Token invalide", extra_tags="danger")
        except:
            traceback.print_exc()
            pass
    context={"obj":obj,"send_otp":send_otp,"chequier":ordre_ref}
    return render(request, 'bankcheck/component.html', context)






@login_required
@transaction.atomic()
@permission_required("bankcheck.search_cheque", raise_exception=True)
def get_infos_cheque_view(request):
    template = "bankcheck/infos_cheque.html"
    user = request.user
    q_search = request.GET.get('q_search', "")
    cheque=None
    ordre=None
    compte=None
    agent=None
    context={}
    has_visa=False
    msg=None
    if q_search:

        try:
            cheque = Cheque.objects.get(reference=q_search.strip())
            msg=cheque.get_status_cheque()
            ordre=  OrdrePayment.objects.filter(cheque=cheque.reference).last()
            #if msg is None:
            #    msg="Chèque {} est au stade de {}".format(q_search,ordre.etape)

            compte=cheque.chequier.compte
            agent=compte.get_current_gerant()
            if msg is not None:
                alerte_msg = "le chèque {} n'est pas visé".format(q_search)
                messages.error(request, msg)
            else:
                if ordre:
                    if hasattr(ordre, "reservationfond"):
                        msg = "le chèque {} est en attente de prise en charge chez le comptable ".format(q_search)
                        if hasattr(ordre, "prise_en_charge"):
                            msg = "le chèque {} est en attente de visa chez le comptable ".format(q_search)
                            if hasattr(ordre.prise_en_charge, "visa"):
                                has_visa = True
                                msg = "le chèque {} est visé ".format(q_search)
                    else:
                        msg = "Le chèque {} est lié à l'opération {} qui est en validation chez le comptable ".format(q_search,ordre.sig_reference)

                else:
                    msg = "le chèque {}  n'est lié à aucune operation de paiement".format(q_search)


                if not has_visa:
                    alerte_msg = "le chèque {} n'est pas  visé".format(q_search)
                    messages.error(request,alerte_msg)



        except Cheque.DoesNotExist:
            messages.error(request,
                          "Chèque numero {} est inconnu de SIGCDD".format(q_search))
            #url = reverse("bankcheck:get_infos_cheque_view")
            #return HttpResponseRedirect(url)
    context = {"cheque": cheque, "compte": compte, "ordre": ordre, "agent": agent,"has_visa":has_visa,"msg":msg,"q_search":q_search}


    return render(request, template, context)
