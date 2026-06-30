from django_tables2 import RequestConfig
from django.shortcuts import render
from bootstrap_modal_forms.utils import is_ajax
from helpers.forms import DefaultModalModelForm
from helpers.models import FakeModel
from helpers.tables import FakeModelFilter,FakeModelTable
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import PermissionRequiredMixin

from bootstrap_modal_forms.generic import (
    BSModalDeleteView,
    BSModalCreateView,BSModalUpdateView
)

PAGINATION_SIZE=2
@login_required
def list_fakemodel_view(request):
    queryset = FakeModel.objects.all()
    queryset_filter = FakeModelFilter(request.GET, request=request, queryset=queryset)
    table = FakeModelTable(queryset_filter.qs)

    title = _("Fakemodel")
    data_title=_("Fakes models")

    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    return render(request, 'datatables/items.html', {"data_title":data_title,'table': table,"filter":queryset_filter,"title":title,"index":"0","sens":"desc"})


from django.views.decorators.cache import never_cache
from django.http import JsonResponse

from django.db.models import Sum, Avg, Count, IntegerField, F, Value, OuterRef, Subquery, Case, When, FloatField, \
    ExpressionWrapper, CharField, BooleanField

from helpers.models import Category
@never_cache
def live_unread_notification_count(request):
    user_is_authenticated = request.user.is_authenticated
    cats=list(Category.objects.values("id","name"))
    if not user_is_authenticated:
        data = {
            'unread_count': []
        }
    else:
        y=[]
        x= list(request.user.notifications.unread().values("target_content_type_id","target_object_id").annotate(count=Count('id'),  badge_class=ExpressionWrapper(F("target_object_id"), output_field=CharField())))

        for s in x:
            #print(s)
            for j in cats:
                if j['id'] == s["target_object_id"]:
                    s["badge_class"] = j["name"]
                    y.append(s)

        data = {'unread_count': y}

    return JsonResponse(data)





def trigger_sentry_error(request):
    division_by_zero = 1 / 0


class DefaultModelDeleteView(PermissionRequiredMixin,BSModalDeleteView):
    # specify the model you want to use
    model = FakeModel
    permission_required = ('core.delete_{}'.format(model._meta.model_name),)

    success_message = 'Success: Supression entité avec succès'
    success_url = reverse_lazy('core:{}_list'.format(model._meta.model_name,))

    template_name = "core/confirm_delete_entity.html"


    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Suppression  : {}".format(self.object.name,)
        return context



class DefaultModelUpdateView(PermissionRequiredMixin,BSModalUpdateView):
    model = FakeModel
    template_name = 'core/update_entity.html'
    form_class = DefaultModalModelForm
    model_name = model._meta.model_name
    permission_required = ('core.change_{}'.format(model_name,),)
    success_message = 'Success: Mise àjour {} avec succès.'.format(model._meta.verbose_name,)
    success_url = reverse_lazy('core:{}_list'.format(model_name,))
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour  {} : {}".format(self.object._meta.verbose_name,self.object)
        return context


class DefaultModelCreateView(PermissionRequiredMixin, BSModalCreateView):
    template_name = 'core/add_entity.html'
    form_class = DefaultModalModelForm
    model = FakeModel
    model_name = model._meta.model_name
    success_message = 'Success: Création {} avec succès .'.format(model._meta.verbose_name, )
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

    def get_form_class(self):
        self.form_class = DefaultModalModelForm
        return self.form_class
