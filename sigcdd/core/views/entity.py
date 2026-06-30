import datetime
import traceback

from bootstrap_modal_forms.utils import is_ajax
from django.contrib.auth.decorators import login_required,permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Sum, Count, IntegerField, F, ExpressionWrapper, CharField
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django_tables2 import RequestConfig
from django.contrib import messages
from cddaccount import ETAPE_ORDRE_PAYMENT
from cddaccount.models import TransactionOP,AvisDeCredit,AvisDeDebit
from cddaccount.tables import AgentPCOrdrePaymentTable, OrdrePayment
from core.models import Structure, Direction, DCP, PosteComptable, ProfilePC, TG, PGT, RGT, ACGP, Secteur, Ministere, \
    CodeService, ConfigurationOTP
from core.tables import DirectionTable, DirectionFilter, CodeServiceFilter, CodeServiceTable, TGTable, TGFilter, \
    PosteComptableFilter, PosteComptableTable, DCPFilter, DCPTable, MinistereTable, SecteurTable, \
    SecteurFilter, MinistereFilter, StructureFilter, StructureTable, ConfigurationOTPTable
from helpers.decorators import user_role_required
from helpers.models import Role

PAGINATION_SIZE=100

default_currency="F CFA"
# import generic UpdateView


from core.forms import StructureModelForm, DirectionModelForm, CodeServiceModelForm, PosteComptableModelForm, \
    DCPModelForm, TGModelForm, PGTModelForm, \
    RGTModelForm, TPRModelForm, ACGPModelForm, SecteurModelForm, MinistereModelForm, UpdateStructureLogoForm, \
    ConfigurationOTPModelForm, StructureUpdateModelForm

# Relative import of GeeksModel
from bootstrap_modal_forms.generic import (
    BSModalDeleteView,
    BSModalCreateView,BSModalUpdateView
)

@login_required
#@user_role_required("ADMIN")
def postcomptabble_list_view(request):
    create_poste_url = reverse_lazy('core:create_postecomptable')
    create_tg_url = reverse_lazy('core:create_tg')
    create_tpr_url = reverse_lazy('core:create_tpr')
    create_acgp_url = reverse_lazy('core:create_acgp')
    create_rgt_url = reverse_lazy('core:create_rgt')
    create_pgt_url = reverse_lazy('core:create_pgt')
    user=request.user
    queryset = PosteComptable.objects.by_agent(user)
    queryset_filter = PosteComptableFilter(request.GET, request=request, queryset=queryset)
    table = PosteComptableTable(queryset_filter.qs,exclude=("action",))
    can_create_poste=user.has_perm('core.add_postecomptable')
    can_create_tg = user.has_perm('core.add_tg') and TG.objects.exists()==False
    can_create_tpr = user.has_perm('core.add_tpr')
    can_create_pgt = user.has_perm('core.add_pgt') and PGT.objects.exists()==False

    can_create_rgt = user.has_perm('core.add_rgt')and RGT.objects.exists()==False
    can_create_acgp = user.has_perm('core.add_acgp') and ACGP.objects.exists()==False

    q={"can_create_rgt":can_create_rgt,"can_create_acgp":can_create_acgp,"can_create_tpr":can_create_tpr,"can_create_pgt":can_create_pgt,"can_create_tg":can_create_tg}


    if user.has_perm('core.change_postecomptable') or user.has_perm('core.delete_postecomptable'):
        table = PosteComptableTable(queryset_filter.qs)
    title = _("Poste comptable")
    data_title=_("Poste comptable")

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    context =  {"create_tpr_url":create_tpr_url,"create_acgp_url":create_acgp_url,"create_rgt_url":create_rgt_url,"create_pgt_url":create_pgt_url,"create_tg_url":create_tg_url,"create_poste_url":create_poste_url,"can_create_poste":can_create_poste,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"}
    context.update(q)
    return render(request, 'core/list_postcomptable.html',context)




@login_required
#@user_role_required("ADMIN")
def tg_list_view(request):
    user=request.user
    queryset = TG.objects.all()
    queryset_filter = TGFilter(request.GET, request=request, queryset=queryset)
    table = TGTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('core.add_tg')
    if user.has_perm('core.change_tg') or user.has_perm('core.delete_tg'):
        table = TGTable(queryset_filter.qs)
    title = _("TRESOSERIE  GENENRALE")
    data_title=_("TRESOSERIE  GENENRALE")

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'core/list_tg.html', {"can_create_dcp":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})





@method_decorator([user_role_required(Role.ADMIN)], name='dispatch')
class PosteComptableCreateView(PermissionRequiredMixin, BSModalCreateView):
    template_name = 'core/add_entity.html'
    form_class = PosteComptableModelForm
    model_name = form_class._meta.model._meta.model_name
    success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
    success_url = reverse_lazy('core:{}_list'.format(model_name, ))
    permission_required = ('core.add_{}'.format(model_name, ),)

    # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        form.instance.created = datetime.datetime.now()
        if not is_ajax(self.request.META):
            self.object = form.save(commit=False)
            self.object.creator = self.request.user
            self.object.dcp=DCP.object()
            self.object.created = datetime.datetime.now()
            form.save()
        return super().form_valid(form)


    def form_invalid(self, form):
        print("invalid")
        return super().form_invalid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        name = self.form_class._meta.model._meta.verbose_name
        context['title'] = "{}".format(name, )
        return context



class TGCreateView(PosteComptableCreateView):
    form_class = TGModelForm
    model_name = form_class._meta.model._meta.model_name
    success_url = reverse_lazy('core:{}_list'.format(model_name, ))
    permission_required = ('core.add_{}'.format(model_name, ),)
    def form_valid(self, form):
        if not is_ajax(self.request.META):
            form.instance.dcp = DCP.object()
            form.instance.creator = self.request.user
            form.instance.created = datetime.datetime.now()
        return super().form_valid(form)

class TPRCreateView(PosteComptableCreateView):
    form_class = TPRModelForm
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.add_{}'.format(model_name, ),)

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            form.instance.dcp = DCP.object()
            form.instance.creator = self.request.user
            form.instance.created = datetime.datetime.now()
        return super().form_valid(form)

class ACGPCreateView(PosteComptableCreateView):
    form_class = ACGPModelForm
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.add_{}'.format(model_name, ),)

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            form.instance.dcp = DCP.object()
            form.instance.creator = self.request.user
            form.instance.created = datetime.datetime.now()
        return super().form_valid(form)

class PGTCreateView(PosteComptableCreateView):
    form_class = PGTModelForm
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.add_{}'.format(model_name, ),)

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            form.instance.dcp = DCP.object()
            form.instance.created=datetime.datetime.now()
            form.instance.creator = self.request.user
        return super().form_valid(form)

class RGTCreateView(PosteComptableCreateView):
    form_class = RGTModelForm
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.add_{}'.format(model_name, ),)

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            form.instance.dcp = DCP.object()
            form.instance.creator = self.request.user
            form.instance.created = datetime.datetime.now()
        return super().form_valid(form)

@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class PosteComptableDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    model = PosteComptable
    permission_required = ('core.delete_postecomptable',)

    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_message = 'Success: Supression entité poste comptable'
    success_url = reverse_lazy('core:postecomptable_list')

    template_name = "core/confirm_delete_entity.html"


    def get_context_data(self, *args, **kwargs):
        context = super(PosteComptableDeleteView, self).get_context_data(*args, **kwargs)
        context['title'] = "Suppression entite : {}".format(self.object.name,)
        return context

@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class PosteComptableUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    model = PosteComptable
    template_name = 'core/update_entity.html'
    form_class = PosteComptableModelForm
    #raise_exception = True
    permission_required = ('core.change_postecomptable',)
    success_message = 'Success: Mise à jour poste comptable.'
    success_url = reverse_lazy('core:postecomptable_list')
    def get_context_data(self, *args, **kwargs):
        context = super(PosteComptableUpdateView, self).get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour de {} : {}".format(self.object._meta.verbose_name,self.object)
        return context


@login_required
#@user_role_required("ADMIN")
def dcp_list_view(request):
    user=request.user
    queryset = DCP.objects.all()
    queryset_filter = DCPFilter(request.GET, request=request, queryset=queryset)
    table = DCPTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('core.add_dcp') and DCP.objects.exists()==False
    if user.has_perm('core.change_dcp') or user.has_perm('core.delete_dcp'):
        table = DCPTable(queryset_filter.qs)
    title = _("DIRECTION DE LA COMPTABILITE PUBLIQUE")
    data_title=_("DIRECTION DE LA COMPTABILITE PUBLIQUE")

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'core/dcp_list.html', {"can_create_dcp":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})




@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class DCPCreateView(PermissionRequiredMixin,BSModalCreateView):
    template_name = 'core/add_entity.html'
    form_class = DCPModelForm
    success_message = 'Success: Création entité Dcp.'
    success_url = reverse_lazy('core:dcp_list')
    permission_required = ('core.add_dcp',)
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
        context = super(DCPCreateView, self).get_context_data(*args, **kwargs)
        name= self.form_class._meta.model._meta.verbose_name
        context['title'] = "Nouvel  {}".format(name,)
        return context


@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class DCPDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    model = DCP
    permission_required = ('core.delete_dcp',)

    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_message = 'Success: Supression entité dcp'
    success_url = reverse_lazy('core:dcp_list')

    template_name = "core/confirm_delete_entity.html"

    def form_valid(self, form):
        raise Http404


    def get_context_data(self, *args, **kwargs):
        context = super(DCPDeleteView, self).get_context_data(*args, **kwargs)
        context['title'] = "Suppression entite : {}".format(self.object.name,)
        return context

@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class DCPUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    model = DCP
    template_name = 'core/update_entity.html'
    form_class = DCPModelForm
    permission_required = ('core.change_dcp',)
    success_message = 'Success: Mise à jour entité dcp.'
    success_url = reverse_lazy('core:dcp_list')
    def get_context_data(self, *args, **kwargs):
        context = super(DCPUpdateView, self).get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour de {} : {}".format(self.object._meta.verbose_name,self.object)
        return context




@login_required
@user_role_required([Role.ADMIN,Role.AGENT_PC])
def dash_postcomptable_view(request,poste_id):
    user=request.user

    create_agent_url=reverse_lazy("core:create_profilepc")
    create_gerant_url=reverse_lazy("cddaccount:create_gerantcd")
    poste = get_object_or_404(PosteComptable, id=poste_id)
    if user.role==Role.AGENT_PC and poste!= user.agent_postecomptable.poste:
        raise Http404

    create_affectationgcd_url = reverse_lazy('cddaccount:create_gestioncomptedepot')

    create_avis_credit_url=reverse_lazy('cddaccount:create_avisdecredit')
    create_avis_debit_url=reverse_lazy('cddaccount:create_avisdedebit')

    create_op_url=reverse_lazy('cddaccount:create_ordrepayment_default')
    seesolde_op_url=reverse_lazy('cddaccount:seesolde_op_view')

    agents = ProfilePC.objects.filter(poste_id=poste_id).count()
    compte_depots=poste.comptes_depots.by_agent(user).exclude(validation_cd=None).aggregate(
        solde_total=Sum('balance', output_field=IntegerField()),
        compte_depots=Count('id', output_field=IntegerField()))



    comptable_ordres = OrdrePayment.objects.by_agent(user).filter(compte__poste_id=poste_id).exclude(etape=ETAPE_ORDRE_PAYMENT.SAISIE).prefetch_related("secteur","compte","nature","creator","jour_comptable","typecompte","prise_en_charge","annulation_op","prise_en_charge__visa")
	  # .reverse()[:5]

    last_ordres = comptable_ordres.filter( created__gte=datetime.datetime.now() - datetime.timedelta(
                                                  days=7)) # .reverse()[:5]

    last_ordres=last_ordres.filter(prise_en_charge__visa=None)

    valides = comptable_ordres.filter(etape=ETAPE_ORDRE_PAYMENT.VALIDE).count()

    receptions=comptable_ordres.filter(etape = ETAPE_ORDRE_PAYMENT.ACCEPTE).count()

    #priseencharge_objs=comptable_ordres.exclude(prise_en_charge=None)


    #print(comptable_ordres.filter(etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE).values("etape","reference","sig_reference"))

    priseencharge=comptable_ordres.filter(etape= ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE).count()
    visa=comptable_ordres.filter(etape= ETAPE_ORDRE_PAYMENT.VISA).count()
    totalinstance=comptable_ordres.count()



    optable = AgentPCOrdrePaymentTable(last_ordres, request=request, exclude=("matricule", "gerant","selection","status","created","reliquat"))
    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(optable)



    blocagefondtable=None
    debittable=None
    credittable=None

    gestionnaires=poste.gestionnaires_cd.count()
    can_create_dcp = user.has_perm('core.add_affectationagent')
    title = "{} ({})".format( poste.name,poste.reference)
    context={"valides":valides,"reception":receptions,"priseencharge":priseencharge,"visa":visa,"totalinstance":totalinstance,"create_op_url":create_op_url,"seesolde_op_url":seesolde_op_url, "create_avis_credit_url":create_avis_credit_url,"create_avis_debit_url":create_avis_debit_url,"debittable":debittable,"credittable":credittable,"blocagefondtable":blocagefondtable,"optable":optable,"create_affectationgcd_url":create_affectationgcd_url,"create_agent_url":create_agent_url,"create_gerant_url":create_gerant_url,"currency":default_currency,"gestionnaires":gestionnaires,"agents":agents,"can_create_entite":can_create_dcp,"title":title,"index":"0","sens":"desc"}
    context.update(compte_depots)
    return render(request, 'core/dash_postecomptable.html', context)





@login_required
#@user_role_required("ADMIN")
def secteur_list_view(request):
    user=request.user
    c = "secteur"
    create_url = reverse_lazy('core:create_{}'.format(c,))
    queryset = Secteur.objects.all()
    queryset_filter = SecteurFilter(request.GET, request=request, queryset=queryset)
    table = SecteurTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('core.add_{}'.format(c,))
    if user.has_perm('core.change_{}'.format(c,)) or user.has_perm('core.delete_{}'.format(c,)):
        table = SecteurTable(queryset_filter.qs)
    title = _("SECTEURS")
    data_title=_("SECTEURS")
    create_tilte = "Nouveau Secteur"

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'core/default_list.html', {"create_tilte":create_tilte,"create_url":create_url,"can_create_entite":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})




def ministere_list_view(request):
    user=request.user
    c = "ministere"
    create_url = reverse_lazy('core:create_{}'.format(c,))
    queryset = Ministere.objects.all()
    queryset_filter = MinistereFilter(request.GET, request=request, queryset=queryset)
    table = MinistereTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('core.add_{}'.format(c,))
    if user.has_perm('core.change_{}'.format(c,)) or user.has_perm('core.delete_{}'.format(c,)):
        table = MinistereTable(queryset_filter.qs)
    title = _("Ministeres")
    data_title=_("Ministeres")
    create_tilte = "Nouveau Ministère"

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'core/default_list.html', {"create_tilte":create_tilte,"create_url":create_url,"can_create_entite":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})






def codeservice_list_view(request):
    user=request.user
    c = "codeservice"
    create_url = reverse_lazy('core:create_{}'.format(c,))
    queryset = CodeService.objects.all()
    queryset_filter = CodeServiceFilter(request.GET, request=request, queryset=queryset)
    table = CodeServiceTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('core.add_{}'.format(c,))
    if user.has_perm('core.change_{}'.format(c,)) or user.has_perm('core.delete_{}'.format(c,)):
        table = CodeServiceTable(queryset_filter.qs)
    title = _("Code Service")
    data_title=_("Code Service")
    create_tilte = "Nouveau Code Service"

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'core/default_list.html', {"create_tilte":create_tilte,"create_url":create_url,"can_create_entite":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})






class BaseDefaultModelCreateView(PermissionRequiredMixin, BSModalCreateView):
    template_name = 'core/add_entity.html'
    form_class = SecteurModelForm
    model_name = form_class._meta.model._meta.model_name
    success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
    success_url = reverse_lazy('core:{}_list'.format(model_name, ))
    permission_required = ('core.add_{}'.format(model_name, ),)

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
        context['title'] = "Nouvel {}".format(name, )
        return context







@method_decorator([user_role_required(Role.ADMIN)], name='dispatch')
class DefaultModelCreateView(PermissionRequiredMixin, BSModalCreateView):
    template_name = 'core/add_entity.html'
    form_class = SecteurModelForm
    model_name = form_class._meta.model._meta.model_name
    success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )
    success_url = reverse_lazy('core:{}_list'.format(model_name, ))
    permission_required = ('core.add_{}'.format(model_name, ),)

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
        context['title'] = "Nouvel {}".format(name, )
        return context



class MinistereCreateView(DefaultModelCreateView):
    form_class = MinistereModelForm
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.add_{}'.format(model_name, ),)
    success_url = reverse_lazy('core:{}_list'.format(model_name, ))
    success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )

class SecteurCreateView(DefaultModelCreateView):
    form_class = SecteurModelForm
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.add_{}'.format(model_name, ),)

    success_url = reverse_lazy('core:{}_list'.format(model_name, ))
    success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )



class CodeServiceCreateView(DefaultModelCreateView):
    form_class = CodeServiceModelForm
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.add_{}'.format(model_name, ),)

    success_url = reverse_lazy('core:{}_list'.format(model_name, ))
    success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )

@method_decorator([ user_role_required([Role.ADMIN,Role.AGENT_DCP])], name='dispatch')
class DirectionCreateView(DefaultModelCreateView):
    form_class = DirectionModelForm
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.add_{}'.format(model_name, ),)

    success_url = reverse_lazy('core:{}_list'.format(model_name, ))
    success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )



class DefaultBaseModelUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    model = Secteur
    template_name = 'core/update_entity.html'
    form_class = DCPModelForm
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.change_{}'.format(model_name,),)
    success_message = 'Success: Mise àjour {} avec succès.'.format(model._meta.verbose_name,)
    success_url = reverse_lazy('core:{}_list'.format(model_name,))
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour  {} : {}".format(self.object._meta.verbose_name,self.object)
        return context



@method_decorator([ user_role_required([Role.ADMIN])], name='dispatch')
class DefaultModelUpdateView(DefaultBaseModelUpdateView):
    pass


class SecteurUpdateView(DefaultModelUpdateView):
    form_class = SecteurModelForm
    model = Secteur
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.change_{}'.format(model_name, ),)
    success_message = 'Success: Mise àjour {} avec succès.'.format(model._meta.verbose_name, )
    success_url = reverse_lazy('core:{}_list'.format(model_name, ))

#@method_decorator([ user_role_required([Role.ADMIN,Role.AGENT_DCP])], name='dispatch')
class MinistereUpdateView(DefaultBaseModelUpdateView):
    form_class = MinistereModelForm
    model = Ministere
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.change_{}'.format(model_name, ),)
    success_message = 'Success: Mise àjour {} avec succès.'.format(model._meta.verbose_name, )
    success_url = reverse_lazy('core:{}_list'.format(model_name, ))


class CodeServiceUpdateView(DefaultModelUpdateView):
    form_class = CodeServiceModelForm
    model = CodeService
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.change_{}'.format(model_name, ),)
    success_message = 'Success: Mise àjour {} avec succès.'.format(model._meta.verbose_name, )
    success_url = reverse_lazy('core:{}_list'.format(model_name, ))

@method_decorator([ user_role_required([Role.ADMIN,Role.AGENT_DCP])], name='dispatch')
class DirectionUpdateView(DefaultModelUpdateView):
    form_class = DirectionModelForm
    model = Direction
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.change_{}'.format(model_name, ),)
    success_message = 'Success: Mise àjour {} avec succès.'.format(model._meta.verbose_name, )
    success_url = reverse_lazy('core:{}_list'.format(model_name, ))




@method_decorator([ user_role_required(Role.ADMIN)], name='dispatch')
class DefaultModelDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    model = Secteur
    permission_required = ('core.delete_{}'.format(model._meta.model_name),)

    success_message = 'Success: Supression entité avec succès'
    success_url = reverse_lazy('core:{}_list'.format(model._meta.model_name,))

    template_name = "core/confirm_delete_entity.html"


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Suppression  : {}".format(self.object.name,)
        return context



class CodeServiceDeleteView(DefaultModelDeleteView):

    model = CodeService
    permission_required = ('core.delete_{}'.format(model._meta.model_name),)
    success_url = reverse_lazy('core:{}_list'.format(model._meta.model_name, ))

class SecteurDeleteView(DefaultModelDeleteView):

    model = Secteur
    permission_required = ('core.delete_{}'.format(model._meta.model_name),)
    success_url = reverse_lazy('core:{}_list'.format(model._meta.model_name, ))


class MinistereDeleteView(DefaultModelDeleteView):
    model = Ministere
    permission_required = ('core.delete_{}'.format(model._meta.model_name),)
    success_url = reverse_lazy('core:{}_list'.format(model._meta.model_name, ))

@method_decorator([ user_role_required([Role.ADMIN,Role.AGENT_DCP])], name='dispatch')
class DirectionDeleteView(DefaultModelDeleteView):
    model = Direction
    permission_required = ('core.delete_{}'.format(model._meta.model_name),)
    success_url = reverse_lazy('core:{}_list'.format(model._meta.model_name, ))
@login_required
def direction_list_view(request):
    user=request.user
    c = "direction"
    create_url = reverse_lazy('core:create_{}'.format(c,))
    queryset = Direction.objects.all()
    queryset_filter = DirectionFilter(request.GET, request=request, queryset=queryset)
    table = DirectionTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('core.add_{}'.format(c,))
    if user.has_perm('core.change_{}'.format(c,)) or user.has_perm('core.delete_{}'.format(c,)):
        table = DirectionTable(queryset_filter.qs)
    title = _("Directions")
    data_title=_("Directions")
    create_tilte="Nouvelle Direction"


    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'core/default_list.html', {"create_tilte":create_tilte,"create_url":create_url,"can_create_entite":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})





import itertools,operator
@login_required
@user_role_required([Role.AGENT_TG])
def dash_tg_old_view(request):
    user=request.user
    create_agent_url=reverse_lazy("core:create_profilepc")
    create_gerant_url=reverse_lazy("cddaccount:create_gerantcd")

    #if user.role==Role.AGENT_PC:
    #    raise Http404
    postes= PosteComptable.objects.filter(in_production=True).order_by('priorite')

    create_affectationgcd_url = reverse_lazy('cddaccount:create_gestioncomptedepot')

    create_avis_credit_url=reverse_lazy('cddaccount:create_avisdecredit')
    create_avis_debit_url=reverse_lazy('cddaccount:create_avisdedebit')

    create_op_url=reverse_lazy('cddaccount:create_ordrepayment_default')
    comptable_ordres = OrdrePayment.objects.filter(etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE)

    datas_op= comptable_ordres.values("compte__poste_id").annotate(
        montant=Sum('amount', output_field=IntegerField()),
        nombres=Count('id', output_field=IntegerField()),
        poste_code=ExpressionWrapper(F("compte__poste__reference"), output_field=CharField()),
        poste_name=ExpressionWrapper(F("compte__poste__name"), output_field=CharField()))

    daily_trx=TransactionOP.objects.filter(created__year=datetime.date.today().year,created__month=datetime.date.today().month,created__day=datetime.date.today().day)

    datas_trx = daily_trx.values("reservation__ordre__compte__poste_id").annotate(
        montant=Sum('amount', output_field=IntegerField()),
        nombres=Count('id', output_field=IntegerField()),
        poste_code=ExpressionWrapper(F("reservation__ordre__compte__poste__reference"), output_field=CharField()),
        poste_name=ExpressionWrapper(F("reservation__ordre__compte__poste__name"), output_field=CharField()))

    datas_op = sorted(datas_op, key=lambda k: k['poste_code'], reverse=False)
    datas_trx = sorted(datas_trx, key=lambda k: k['poste_code'], reverse=False)

    postes_datas = []
    visa_total=0
    prise_en_charge_total=0
    visa_nombre = 0
    prise_en_charge_nombre = 0

    for poste in postes:
        format_data = {"poste_code": poste.reference, "poste_name": poste.name, "nombre": 0, "total": 0,
                       "virement": {"total": 0, "nombre": 0},
                       "cheque": {"total": 0, "nombre": 0, "compense": 0, "non_compense": 0},
                       "prise_en_charge": {"total": 0, "nombre": 0,
                                           "cheque": {"total": 0, "nombre": 0, "compese": 0, "non_compense": 0},
                                           "virement": {"total": 0, "nombre": 0}}, "visa": {"total": 0, "nombre": 0,
                                                                                            "cheque": {"total": 0,
                                                                                                       "nombre": 0,
                                                                                                       "compese": 0,
                                                                                                       "non_compense": 0},
                                                                                            "virement": {"total": 0,
                                                                                                         "nombre": 0}}}

        for key, items in itertools.groupby(datas_op, operator.itemgetter('poste_code')):
            item=list(items)[0]
            if key==poste.reference:
                format_data["prise_en_charge"]["total"] = item["montant"]
                format_data["prise_en_charge"]["nombre"] = item["nombres"]
                prise_en_charge_total+=item["montant"]
                prise_en_charge_nombre+=item["nombres"]

        for key, items in itertools.groupby(datas_trx, operator.itemgetter('poste_code')):
            item=list(items)[0]
            if key==poste.reference:
                format_data["visa"]["total"] = item["montant"]
                format_data["visa"]["nombre"] = item["nombres"]

                visa_total += item["montant"]
                visa_nombre += item["nombres"]

        postes_datas.append(format_data)



    #print(datas_op)
    #print(datas_trx)
    #print(postes_datas)


    blocagefondtable=None
    debittable=None
    credittable=None

    gestionnaires=0
    can_create_dcp = user.has_perm('core.add_affectationagent')
    title = "Tableau de bord"
    context={"visa_nombre":visa_nombre,"prise_en_charge_nombre":prise_en_charge_nombre,"priseencharge":prise_en_charge_total,"visa":visa_total,"create_op_url":create_op_url,"create_avis_credit_url":create_avis_credit_url,"create_avis_debit_url":create_avis_debit_url,"debittable":debittable,"credittable":credittable,"blocagefondtable":blocagefondtable,"create_affectationgcd_url":create_affectationgcd_url,"create_agent_url":create_agent_url,"create_gerant_url":create_gerant_url,"currency":default_currency,"gestionnaires":gestionnaires,"can_create_entite":can_create_dcp,"title":title,"postes":postes_datas}

    return render(request, 'core/tg_dash.html', context)




@login_required
@user_role_required([Role.AGENT_TG])
def dash_tg_view(request):
    user=request.user
    create_agent_url=reverse_lazy("core:create_profilepc")
    create_gerant_url=reverse_lazy("cddaccount:create_gerantcd")

    #if user.role==Role.AGENT_PC:
    #    raise Http404
    postes= PosteComptable.objects.filter(in_production=True).order_by('priorite')

    create_affectationgcd_url = reverse_lazy('cddaccount:create_gestioncomptedepot')

    create_avis_credit_url=reverse_lazy('cddaccount:create_avisdecredit')
    create_avis_debit_url=reverse_lazy('cddaccount:create_avisdedebit')

    create_op_url=reverse_lazy('cddaccount:create_ordrepayment_default')
    comptable_ordres = OrdrePayment.objects.by_agent(user).filter(etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE)

    datas_op= comptable_ordres.values("compte__poste_id",'payment_mean').annotate(
        montant=Sum('amount', output_field=IntegerField()),
        nombres=Count('id', output_field=IntegerField()),
        poste_code=ExpressionWrapper(F("compte__poste__reference"), output_field=CharField()),
        poste_name=ExpressionWrapper(F("compte__poste__name"), output_field=CharField()))


    daily_aviscredit=AvisDeCredit.objects.by_agent(user).filter(created__year=datetime.date.today().year)

    datas_avis = daily_aviscredit.values("compte__poste_id","payment_mean").annotate(
        montant=Sum('amount', output_field=IntegerField()),
        nombres=Count('id', output_field=IntegerField()),
        poste_code=ExpressionWrapper(F("compte__poste__reference"), output_field=CharField()),
        poste_name=ExpressionWrapper(F("compte__poste__name"), output_field=CharField()))

    daily_trx = TransactionOP.objects.by_agent(user).filter(created__year=datetime.date.today().year)

    datas_trx = daily_trx.values("reservation__ordre__compte__poste_id", "payment_mean").annotate(
        montant=Sum('amount', output_field=IntegerField()),
        nombres=Count('id', output_field=IntegerField()),
        poste_code=ExpressionWrapper(F("reservation__ordre__compte__poste__reference"), output_field=CharField()),
        poste_name=ExpressionWrapper(F("reservation__ordre__compte__poste__name"), output_field=CharField()))



    datas_avis = sorted(datas_avis, key=lambda k: k['poste_code'], reverse=False)
    datas_op = sorted(datas_op, key=lambda k: k['poste_code'], reverse=False)
    datas_trx = sorted(datas_trx, key=lambda k: k['poste_code'], reverse=False)

    postes_datas = []
    avis_nombre = 0
    avis_total = 0
    visa_total=0
    prise_en_charge_total=0
    visa_nombre = 0
    prise_en_charge_nombre = 0
    data_prise_charge={"total": 0, "nombre": 0,"cheque": {"total": 0, "nombre": 0},"virement": {"total": 0, "nombre": 0}}
    data_visa = {"total": 0, "nombre": 0, "cheque": {"total": 0, "nombre": 0},"virement": {"total": 0, "nombre": 0}}

    poste_prise_en_charge_cheque_total = 0
    poste_prise_en_charge_cheque_nombre = 0

    poste_prise_en_charge_virement_total = 0
    poste_prise_en_charge_virement_nombre = 0




    for poste in postes:
        format_data = {"poste_code": poste.reference, "poste_name": poste.name, "nombre": 0, "total": 0,
                       "virement": {"total": 0, "nombre": 0}, "aviscredit": {"total": 0, "nombre": 0},
                       "cheque": {"total": 0, "nombre": 0, "compense": 0, "non_compense": 0},
                       "prise_en_charge": {"total": 0, "nombre": 0,
                                           "cheque": {"total": 0, "nombre": 0, "compese": 0, "non_compense": 0},
                                           "virement": {"total": 0, "nombre": 0}}, "visa": {"total": 0, "nombre": 0,
                                                                                            "cheque": {"total": 0,
                                                                                                       "nombre": 0,
                                                                                                       "compese": 0,
                                                                                                       "non_compense": 0},
                                                                                            "virement": {"total": 0,
                                                                                                         "nombre": 0}}}

        for key, items in itertools.groupby(datas_op, operator.itemgetter('poste_code')):
            #item=list(items)[0]

            if key==poste.reference:

                __montant_instance=0
                __nbre_instance = 0
                __montant_instance_cheque = 0
                __nbre_instance_cheque = 0
                __montant_instance_vr = 0
                __nbre_instance_vr = 0

                for item in list(items):
                    if item["payment_mean"]== "CHEQUE":
                        __montant_instance_cheque+=item["montant"]
                        __nbre_instance_cheque += item["nombres"]

                    if item["payment_mean"]== "VIREMENT":
                        __montant_instance_vr += item["montant"]
                        __nbre_instance_vr += item["nombres"]

                    __montant_instance += item["montant"]
                    __nbre_instance += item["nombres"]




                format_data["prise_en_charge"]["total"] = __montant_instance
                format_data["prise_en_charge"]["nombre"] = __nbre_instance
                prise_en_charge_total+=__montant_instance
                prise_en_charge_nombre+=__nbre_instance

                format_data["prise_en_charge"]["virement"]["total"] = __montant_instance_vr
                format_data["prise_en_charge"]["virement"]["nombre"] = __nbre_instance_vr
                poste_prise_en_charge_virement_total += __montant_instance_vr
                poste_prise_en_charge_virement_nombre += __nbre_instance_vr

                format_data["prise_en_charge"]["cheque"]["total"] = __montant_instance_cheque
                format_data["prise_en_charge"]["cheque"]["nombre"] = __nbre_instance_cheque

                poste_prise_en_charge_cheque_total += __montant_instance_cheque
                poste_prise_en_charge_cheque_nombre +=  __nbre_instance_cheque





        for key, items in itertools.groupby(datas_trx, operator.itemgetter('poste_code')):
            #item=list(items)[0]
            poste_visa_total = 0
            poste_visa_nombre = 0
            if key==poste.reference:
                for item in list(items):
                    if item["payment_mean"]== "CHEQUE":
                        format_data["visa"]["cheque"]["total"] = item["montant"]
                        format_data["visa"]["cheque"]["nombre"] = item["nombres"]
                    if item["payment_mean"]== "VIREMENT":
                        format_data["visa"]["virement"]["total"] = item["montant"]
                        format_data["visa"]["virement"]["nombre"] = item["nombres"]

                    poste_visa_total += item["montant"]
                    poste_visa_nombre += item["nombres"]
                    visa_total += item["montant"]
                    visa_nombre += item["nombres"]
                format_data["visa"]["total"] = poste_visa_total
                format_data["visa"]["nombre"] = poste_visa_nombre

        for key, items in itertools.groupby(datas_avis, operator.itemgetter('poste_code')):
            #item=list(items)[0]
            poste_avis_total = 0
            poste_avis_nombre = 0
            if key==poste.reference:
                for item in list(items):

                    poste_avis_total += item["montant"]
                    poste_avis_nombre += item["nombres"]
                    avis_total += item["montant"]
                    avis_nombre += item["nombres"]
                format_data["aviscredit"]["total"] = poste_avis_total
                format_data["aviscredit"]["nombre"] = poste_avis_nombre

        postes_datas.append(format_data)

    data_prise_charge["total"] = prise_en_charge_total
    data_prise_charge["nombre"] = prise_en_charge_nombre
    data_prise_charge["cheque"]["total"] = poste_prise_en_charge_cheque_total
    data_prise_charge["cheque"]["nombre"] = poste_prise_en_charge_cheque_nombre
    data_prise_charge["virement"]["total"] = poste_prise_en_charge_virement_total
    data_prise_charge["virement"]["nombre"] = poste_prise_en_charge_virement_nombre



    blocagefondtable=None
    debittable=None
    credittable=None

    gestionnaires=0
    can_create_dcp = user.has_perm('core.add_affectationagent')
    title = "Tableau de bord"
    context={"avis_total":avis_total,"avis_nombre":avis_nombre,"data_prise_charge":data_prise_charge,"visa_nombre":visa_nombre,"prise_en_charge_nombre":prise_en_charge_nombre,"priseencharge":prise_en_charge_total,"visa":visa_total,"create_op_url":create_op_url,"create_avis_credit_url":create_avis_credit_url,"create_avis_debit_url":create_avis_debit_url,"debittable":debittable,"credittable":credittable,"blocagefondtable":blocagefondtable,"create_affectationgcd_url":create_affectationgcd_url,"create_agent_url":create_agent_url,"create_gerant_url":create_gerant_url,"currency":default_currency,"gestionnaires":gestionnaires,"can_create_entite":can_create_dcp,"title":title,"postes":postes_datas}

    return render(request, 'core/tg_new_dash.html', context)



@login_required
@user_role_required([Role.AGENT_DS])
def dash_ds_view(request):
    user = request.user
    create_agent_url = reverse_lazy("core:create_profilepc")
    create_gerant_url = reverse_lazy("cddaccount:create_gerantcd")

    # if user.role==Role.AGENT_PC:
    #    raise Http404
    postes = PosteComptable.objects.filter(in_production=True).order_by('priorite')

    create_affectationgcd_url = reverse_lazy('cddaccount:create_gestioncomptedepot')

    create_avis_credit_url = reverse_lazy('cddaccount:create_avisdecredit')
    create_avis_debit_url = reverse_lazy('cddaccount:create_avisdedebit')

    create_op_url = reverse_lazy('cddaccount:create_ordrepayment_default')
    comptable_ordres = OrdrePayment.objects.by_agent(user).filter(etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE)

    datas_op = comptable_ordres.values("compte__poste_id", 'payment_mean').annotate(
        montant=Sum('amount', output_field=IntegerField()),
        nombres=Count('id', output_field=IntegerField()),
        poste_code=ExpressionWrapper(F("compte__poste__reference"), output_field=CharField()),
        poste_name=ExpressionWrapper(F("compte__poste__name"), output_field=CharField()))

    daily_aviscredit = AvisDeCredit.objects.by_agent(user).filter(created__year=datetime.date.today().year)

    datas_avis = daily_aviscredit.values("compte__poste_id", "payment_mean").annotate(
        montant=Sum('amount', output_field=IntegerField()),
        nombres=Count('id', output_field=IntegerField()),
        poste_code=ExpressionWrapper(F("compte__poste__reference"), output_field=CharField()),
        poste_name=ExpressionWrapper(F("compte__poste__name"), output_field=CharField()))

    daily_trx = TransactionOP.objects.by_agent(user).filter(created__year=datetime.date.today().year)

    datas_trx = daily_trx.values("reservation__ordre__compte__poste_id", "payment_mean").annotate(
        montant=Sum('amount', output_field=IntegerField()),
        nombres=Count('id', output_field=IntegerField()),
        poste_code=ExpressionWrapper(F("reservation__ordre__compte__poste__reference"), output_field=CharField()),
        poste_name=ExpressionWrapper(F("reservation__ordre__compte__poste__name"), output_field=CharField()))

    datas_avis = sorted(datas_avis, key=lambda k: k['poste_code'], reverse=False)
    datas_op = sorted(datas_op, key=lambda k: k['poste_code'], reverse=False)
    datas_trx = sorted(datas_trx, key=lambda k: k['poste_code'], reverse=False)

    postes_datas = []
    avis_nombre = 0
    avis_total = 0
    visa_total = 0
    prise_en_charge_total = 0
    visa_nombre = 0
    prise_en_charge_nombre = 0
    data_prise_charge = {"total": 0, "nombre": 0, "cheque": {"total": 0, "nombre": 0},
                         "virement": {"total": 0, "nombre": 0}}
    data_visa = {"total": 0, "nombre": 0, "cheque": {"total": 0, "nombre": 0},
                 "virement": {"total": 0, "nombre": 0}}

    poste_prise_en_charge_cheque_total = 0
    poste_prise_en_charge_cheque_nombre = 0

    poste_prise_en_charge_virement_total = 0
    poste_prise_en_charge_virement_nombre = 0

    for poste in postes:
        format_data = {"poste_code": poste.reference, "poste_name": poste.name, "nombre": 0, "total": 0,
                       "virement": {"total": 0, "nombre": 0}, "aviscredit": {"total": 0, "nombre": 0},
                       "cheque": {"total": 0, "nombre": 0, "compense": 0, "non_compense": 0},
                       "prise_en_charge": {"total": 0, "nombre": 0,
                                           "cheque": {"total": 0, "nombre": 0, "compese": 0, "non_compense": 0},
                                           "virement": {"total": 0, "nombre": 0}}, "visa": {"total": 0, "nombre": 0,
                                                                                            "cheque": {"total": 0,
                                                                                                       "nombre": 0,
                                                                                                       "compese": 0,
                                                                                                       "non_compense": 0},
                                                                                            "virement": {"total": 0,
                                                                                                         "nombre": 0}}}

        for key, items in itertools.groupby(datas_op, operator.itemgetter('poste_code')):
            # item=list(items)[0]

            if key == poste.reference:

                __montant_instance = 0
                __nbre_instance = 0
                __montant_instance_cheque = 0
                __nbre_instance_cheque = 0
                __montant_instance_vr = 0
                __nbre_instance_vr = 0

                for item in list(items):
                    if item["payment_mean"] == "CHEQUE":
                        __montant_instance_cheque += item["montant"]
                        __nbre_instance_cheque += item["nombres"]

                    if item["payment_mean"] == "VIREMENT":
                        __montant_instance_vr += item["montant"]
                        __nbre_instance_vr += item["nombres"]

                    __montant_instance += item["montant"]
                    __nbre_instance += item["nombres"]

                format_data["prise_en_charge"]["total"] = __montant_instance
                format_data["prise_en_charge"]["nombre"] = __nbre_instance
                prise_en_charge_total += __montant_instance
                prise_en_charge_nombre += __nbre_instance

                format_data["prise_en_charge"]["virement"]["total"] = __montant_instance_vr
                format_data["prise_en_charge"]["virement"]["nombre"] = __nbre_instance_vr
                poste_prise_en_charge_virement_total += __montant_instance_vr
                poste_prise_en_charge_virement_nombre += __nbre_instance_vr

                format_data["prise_en_charge"]["cheque"]["total"] = __montant_instance_cheque
                format_data["prise_en_charge"]["cheque"]["nombre"] = __nbre_instance_cheque

                poste_prise_en_charge_cheque_total += __montant_instance_cheque
                poste_prise_en_charge_cheque_nombre += __nbre_instance_cheque

        for key, items in itertools.groupby(datas_trx, operator.itemgetter('poste_code')):
            # item=list(items)[0]
            poste_visa_total = 0
            poste_visa_nombre = 0
            if key == poste.reference:
                for item in list(items):
                    if item["payment_mean"] == "CHEQUE":
                        format_data["visa"]["cheque"]["total"] = item["montant"]
                        format_data["visa"]["cheque"]["nombre"] = item["nombres"]
                    if item["payment_mean"] == "VIREMENT":
                        format_data["visa"]["virement"]["total"] = item["montant"]
                        format_data["visa"]["virement"]["nombre"] = item["nombres"]

                    poste_visa_total += item["montant"]
                    poste_visa_nombre += item["nombres"]
                    visa_total += item["montant"]
                    visa_nombre += item["nombres"]
                format_data["visa"]["total"] = poste_visa_total
                format_data["visa"]["nombre"] = poste_visa_nombre

        for key, items in itertools.groupby(datas_avis, operator.itemgetter('poste_code')):
            # item=list(items)[0]
            poste_avis_total = 0
            poste_avis_nombre = 0
            if key == poste.reference:
                for item in list(items):
                    poste_avis_total += item["montant"]
                    poste_avis_nombre += item["nombres"]
                    avis_total += item["montant"]
                    avis_nombre += item["nombres"]
                format_data["aviscredit"]["total"] = poste_avis_total
                format_data["aviscredit"]["nombre"] = poste_avis_nombre

        postes_datas.append(format_data)

    data_prise_charge["total"] = prise_en_charge_total
    data_prise_charge["nombre"] = prise_en_charge_nombre
    data_prise_charge["cheque"]["total"] = poste_prise_en_charge_cheque_total
    data_prise_charge["cheque"]["nombre"] = poste_prise_en_charge_cheque_nombre
    data_prise_charge["virement"]["total"] = poste_prise_en_charge_virement_total
    data_prise_charge["virement"]["nombre"] = poste_prise_en_charge_virement_nombre

    blocagefondtable = None
    debittable = None
    credittable = None

    gestionnaires = 0
    can_create_dcp = user.has_perm('core.add_affectationagent')
    title = "Tableau de bord"
    context = {"avis_total": avis_total, "avis_nombre": avis_nombre, "data_prise_charge": data_prise_charge,
               "visa_nombre": visa_nombre, "prise_en_charge_nombre": prise_en_charge_nombre,
               "priseencharge": prise_en_charge_total, "visa": visa_total, "create_op_url": create_op_url,
               "create_avis_credit_url": create_avis_credit_url, "create_avis_debit_url": create_avis_debit_url,
               "debittable": debittable, "credittable": credittable, "blocagefondtable": blocagefondtable,
               "create_affectationgcd_url": create_affectationgcd_url, "create_agent_url": create_agent_url,
               "create_gerant_url": create_gerant_url, "currency": default_currency, "gestionnaires": gestionnaires,
               "can_create_entite": can_create_dcp, "title": title, "postes": postes_datas}

    return render(request, 'core/ds_dash.html', context)





class StructureDeleteView(BaseDefaultModelCreateView):
    model = Structure
    permission_required = ('core.delete_{}'.format(model._meta.model_name),)
    success_url = reverse_lazy('core:{}_list'.format(model._meta.model_name, ))


class StructureUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    form_class = StructureUpdateModelForm
    model = Structure
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.change_{}'.format(model_name, ),)
    success_message = 'Success: Mise àjour {} avec succès.'.format(model._meta.verbose_name, )
    success_url = reverse_lazy('core:{}_list'.format(model_name, ))


    template_name = 'core/update_entity.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour  {} : {}".format(self.object._meta.verbose_name,self.object)
        return context


    def form_valid(self, form):
        if not is_ajax(self.request.META):
            user=self.request.user
            self.object = form.save()
            try:
                print("dsfsdsdfsdfsdf")
                print(user.gerant_cd)
                if hasattr(user, "gerant_cd"):

                    key = self.request.session["select_cddacc_user_id"]

                    compte=user.gerant_cd.mes_compte_depots.filter(compte_id=int(key)).last().compte

                    compte.structure=self.object
                    compte.save()
                    user.gerant_cd.structure = self.object
                    user.gerant_cd.save()


            except:
                traceback.print_exc()

        return super().form_valid(form)

class StructureCreateView(BaseDefaultModelCreateView):
    form_class = StructureModelForm
    model = Structure
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.add_{}'.format(model_name, ),)
    success_url = reverse_lazy('core:{}_list'.format(model_name, ))
    success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        name = self.form_class._meta.model._meta.verbose_name
        context['title'] = "Nouvelle {}".format(name, )
        return context
    
    def form_valid(self, form):
        if not is_ajax(self.request.META):
            user=self.request.user
            self.object = form.save()
            try:
                if hasattr(user, "gerant_cd"):
                    key = self.request.session["select_cddacc_user_id"]
                    compte = user.gerant_cd.mes_compte_depots.filter(compte_id=int(key)).last().compte
                    compte.structure=self.object
                    compte.save()
                    user.gerant_cd.structure = self.object
                    user.gerant_cd.save()

            except Exception as ex:
                pass

        return super().form_valid(form)


@login_required
def structure_list_view(request):
    user=request.user
    c = "structure"
    create_url = reverse_lazy('core:create_{}'.format(c,))
    queryset = Structure.objects.all()
    queryset_filter = StructureFilter(request.GET, request=request, queryset=queryset)
    table = StructureTable(queryset_filter.qs,exclude=("action",))
    can_create_dcp=user.has_perm('core.add_{}'.format(c,))
    if user.has_perm('core.change_{}'.format(c,)) or user.has_perm('core.delete_{}'.format(c,)):
        table = StructureTable(queryset_filter.qs)
    title = _("Strucutre")
    data_title=_("Strucutre")
    create_tilte="Nouvelle Structure"
    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'core/default_list.html', {"create_tilte":create_tilte,"create_url":create_url,"can_create_entite":can_create_dcp,"data_title":data_title,'table': table,"filter_form": queryset_filter.form,"title":title,"index":"0","sens":"desc"})


@login_required
@permission_required("core.add_structure", raise_exception=True)
def link_compte_to_structure(request):
    template = "core/update_logo.html"
    success_url = reverse_lazy('core:{}_list'.format("structure", ))
    user = request.user

    if request.method == 'POST':
        form = UpdateStructureLogoForm(request.POST, request.FILES)
        if form.is_valid():
            if request and not is_ajax(request.META):
                try:
                    if hasattr(user, "gerant_cd"):
                        key = request.session["select_cddacc_user_id"]
                        structure = form.cleaned_data["structure"]
                        compte = user.gerant_cd.mes_compte_depots.filter(compte_id=int(key)).last().compte
                        url_path = user.gerant_cd.get_absolute_url()
                        if "logo" in request.FILES:
                            structure.logo=request.FILES["logo"]
                            structure.save()
                        compte.structure = structure
                        compte.save()
                        user.gerant_cd.structure = structure
                        user.gerant_cd.save()
                        return redirect(url_path)
                    # messages.add_message(request, messages.ERROR, "Aucun téléphoone disponibble pour ennvoyé l'otp")

                except Exception as ex:
                    pass
            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")

    else:
        form = UpdateStructureLogoForm()

    context = {"form": form,'title': "Ajout / Mise a jour logo"}
    return render(request, template, context)


class ConfigurationOTPDeleteView(BaseDefaultModelCreateView):
    model = ConfigurationOTP
    permission_required = ('core.delete_{}'.format(model._meta.model_name),)
    success_url = reverse_lazy('core:{}_list'.format(model._meta.model_name, ))


class ConfigurationOTPUpdateView(PermissionRequiredMixin, BSModalUpdateView):
    form_class = ConfigurationOTPModelForm
    model = ConfigurationOTP
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.change_{}'.format(model_name, ),)
    success_message = 'Success: Mise àjour {} avec succès.'.format(model._meta.verbose_name, )
    success_url = reverse_lazy('core:{}_list'.format(model_name, ))

    template_name = 'core/update_entity.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour  {} : {}".format(self.object._meta.verbose_name, self.object)
        return context




class ConfigurationOTPCreateView(BaseDefaultModelCreateView):
    form_class = ConfigurationOTPModelForm
    model = ConfigurationOTP
    model_name = form_class._meta.model._meta.model_name
    permission_required = ('core.add_{}'.format(model_name, ),)
    success_url = reverse_lazy('core:{}_list'.format(model_name, ))
    success_message = 'Success: Création {} avec succès .'.format(form_class._meta.model._meta.verbose_name, )

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        name = self.form_class._meta.model._meta.verbose_name
        context['title'] = "Nouvelle {}".format(name, )
        return context




@login_required
def configurationotp_list_view(request):
    user = request.user
    c = "configurationotp"
    create_url = reverse_lazy('core:create_{}'.format(c, ))
    queryset = ConfigurationOTP.objects.all()
    table = ConfigurationOTPTable(queryset, exclude=("action",))
    can_create_dcp = user.has_perm('core.add_{}'.format(c, )) and ConfigurationOTP.objects.exists() == False

    if user.has_perm('core.change_{}'.format(c, )) or user.has_perm('core.delete_{}'.format(c, )):
        table = ConfigurationOTPTable(queryset)
    title = _("Configuration OTP")
    data_title = _("Configuration OTP")
    create_tilte = "Configuration OTP"
    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'core/default_list.html',
                  {"create_tilte": create_tilte, "create_url": create_url, "can_create_entite": can_create_dcp,
                   "data_title": data_title, 'table': table,  "title": title,
                   "index": "0", "sens": "desc"})


