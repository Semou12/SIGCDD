from __future__ import unicode_literals

from django_tables2.views import SingleTableMixin
from django_filters import views, FilterSet
from django.utils.html import format_html
from django_tables2.utils import A
import django_tables2 as tables
from django_tables2 import RequestConfig
from django.urls import reverse, reverse_lazy
from django.contrib.humanize.templatetags.humanize import intcomma
from django_filters import views, fields, widgets, FilterSet, TypedChoiceFilter, CharFilter, BooleanFilter, ChoiceFilter, \
    ModelChoiceFilter,Filter,DateTimeFilter

import traceback
from datetime import datetime


from django.utils import datetime_safe, formats
from core.models import Structure, Direction, DCP, ProfileDCP, ProfilePC, AffectationAgent, PosteComptable, TG, \
    Ministere, Secteur, CodeService, ConfigurationOTP

from helpers.filters import StackDateTimeFromToRangeFilter,StackDateFromToRangeFilter



class TGFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter()
    #date = StackDateFromToRangeFilter()

    class Meta:
        model = TG
        fields = ['name', "in_production","created","modified","dcp"]



class PosteComptableFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter(label="Date création")
    #date = StackDateFromToRangeFilter()

    class Meta:
        model = PosteComptable
        fields = ['name', "in_production","created","modified","type"]


class AffectationAgentFilter(FilterSet):
    start_date = StackDateTimeFromToRangeFilter()
    end_date = StackDateTimeFromToRangeFilter()
    #date = StackDateFromToRangeFilter()

    class Meta:
        model = AffectationAgent
        fields = ['agent', "poste","actif","start_date","end_date"]


class DCPFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter()
    #date = StackDateFromToRangeFilter()

    class Meta:
        model = DCP
        fields = ['name', "in_production","created","modified"]



class DefaultTable(tables.Table):
    class Meta:
        template_name = 'datatables/templateB4.html'
        attrs = {'class': 'table table-striped table-bordered  responsive dataex-res-rowcontrol'}

class PosteComptableTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")
    info = tables.Column(verbose_name='Détails', accessor="id")

    class Meta(DefaultTable.Meta):
        model = PosteComptable
        order_by = ("-pk")
        fields = ('id',"reference", "name","priorite", "phone", "email","action","info", "in_production")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M:%S}".format(value)) if value else "---"

    def render_in_production(self, value):
        if value:
            _str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)

    def render_action(self, value):
        delete_url = reverse('core:delete_postecomptable', kwargs={'pk': value})
        update_url = reverse('core:update_postecomptable', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)

    def render_info(self, value):
        info_url = reverse('core:dash_postcomptable_view', kwargs={'poste_id': value})

        str = """
        <a href = "{}" class=" btn btn-sm btn-info" >
          <span class="fa fa-info"></span>
        </a>
        """.format(info_url,)
        return format_html(str)


class DCPTable(DefaultTable):
    action = tables.Column(verbose_name='Actions',accessor="id")
    class Meta(DefaultTable.Meta):
        model = DCP
        order_by=("-pk")
        fields = ('id', "name", "phone", "email","action","created")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M:%S}".format(value)) if value else "---"
    def render_in_production(self, value):
        if value:
            _str="""<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)

    def render_action(self,value):
        #delete_url = reverse('core:delete_dcp', kwargs={'pk': value})
        update_url = reverse('core:update_dcp', kwargs={'pk': value})
        str="""
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>
        
        
        """.format(update_url,)
        return format_html(str)




class ProfileDCPFilter(FilterSet):
    #date = StackDateFromToRangeFilter()

    class Meta:
        model = ProfileDCP
        fields = ['phone', "lastname","firstname","is_actif"]


class ProfileDCPTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")
    roles = tables.Column(verbose_name='Rôles', accessor="format_roles")
    #img = tables.Column(verbose_name='Photo', accessor=A('get_thumbnail_url'))
    #signature = tables.Column(verbose_name='Signature', accessor=A('get_thumbnail_signature_url'))

    class Meta(DefaultTable.Meta):
        model = ProfileDCP
        order_by="-created"
        fields = ("matricule","firstname", "lastname","is_actif", "action","roles","phone")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M:%S}".format(value)) if value else "---"

    def render_is_actif(self, value):
        if value:
            _str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)

    def render_action(self, value):
        delete_url = reverse('core:delete_profiledcp', kwargs={'pk': value})
        update_url = reverse('core:update_profiledcp', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)


    def render_img(self,value):
        img_path=""
        s="<p>--</p>"
        if value:
            s=f"""
            <div class="d-block flex-shrink-0">
                                                <img src="{value}" class="img-fluid img-thumbnail" alt="">
                                            </div>
            """
        return format_html(s)

    def render_signature(self,value):
        img_path=""
        s="<p>--</p>"
        if value:
            s=f"""
            <div class="d-block flex-shrink-0">
                                                <img src="{value}" class="img-fluid img-thumbnail" alt="">
                                            </div>
            """
        return format_html(s)



class AffectationAgentTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")

    firstname = tables.Column(verbose_name="Prénom",accessor='agent__firstname')
    lastname = tables.Column(verbose_name="Nom",accessor='agent__lastname')
    poste = tables.Column(verbose_name="Poste",accessor='poste__name')
    phone = tables.Column(accessor='agent__phone',verbose_name="Tel")
    period =tables.Column(accessor=A('format_period'))
    img = tables.Column(verbose_name='Photo', accessor=A('agent.get_thumbnail_url'))

    class Meta(DefaultTable.Meta):
        model = AffectationAgent
        order_by="-created"

        fields = ['id',"firstname", "lastname","phone","img","poste","created","period","actif", "action"]




    def render_start_date(self, value):
        return format_html("{:%d-%m-%Y %H:%M:%S}".format(value)) if value else "---"




    def render_end_date(self, value):
        return format_html("{:%d-%m-%Y %H:%M:%S}".format(value)) if value else "---"

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M:%S}".format(value)) if value else "---"

    def render_actif(self, value):
        if value:
            _str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)

    def render_action(self, value):
        delete_url = reverse('core:delete_affectation', kwargs={'pk': value})
        update_url = reverse('core:update_affectation', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)


    def render_img(self,value):
        img_path=""
        s="<p>--</p>"
        if value:
            s=f"""
            <div class="d-block flex-shrink-0">
                                                <img src="{value}" class="img-fluid img-thumbnail" alt="">
                                            </div>
            """
        return format_html(s)





class TGTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")

    class Meta(DefaultTable.Meta):
        model = TG
        order_by = ("-pk")
        fields = ("id","reference", "name", "phone","email",  "street", "action")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M:%S}".format(value)) if value else "---"

    def render_in_production(self, value):
        if value:
            _str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)

    def render_action(self, value):
        delete_url = reverse('core:delete_postecomptable', kwargs={'pk': value})
        update_url = reverse('core:update_postecomptable', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)




class ProfilePCFilter(FilterSet):
    #date = StackDateFromToRangeFilter()

    class Meta:
        model = ProfilePC
        fields = ['phone', "lastname","firstname","is_actif"]


class ProfilePCTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")
    roles = tables.Column(verbose_name='Rôles', accessor="format_roles")
    #img = tables.Column(verbose_name='Photo', accessor=A('get_thumbnail_url'))
    #signature = tables.Column(verbose_name='Signature', accessor=A('get_thumbnail_signature_url'))
    poste = tables.Column(verbose_name="Poste", accessor='poste__name')

    class Meta(DefaultTable.Meta):
        model = ProfilePC
        order_by="-created"
        fields = ("id","matricule","firstname", "lastname","is_actif","poste", "action","roles","phone")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_is_actif(self, value):
        if value:
            _str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)

    def render_action(self, value):
        delete_url = reverse('core:delete_profilepc', kwargs={'pk': value})
        update_url = reverse('core:update_profilepc', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)


    def render_img(self,value):
        img_path=""
        s="<p>--</p>"
        if value:
            s=f"""
            <div class="d-block flex-shrink-0">
                                                <img src="{value}" class="img-fluid img-thumbnail" alt="">
                                            </div>
            """
        return format_html(s)

    def render_signature(self,value):
        img_path=""
        s="<p>--</p>"
        if value:
            s=f"""
            <div class="d-block flex-shrink-0">
                                                <img src="{value}" class="img-fluid img-thumbnail" alt="">
                                            </div>
            """
        return format_html(s)





class MinistereFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter()
    class Meta:
        model = Ministere
        fields = ['name']

class MinistereTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")

    class Meta(DefaultTable.Meta):
        model = Ministere
        order_by = ("-id")
        fields = ("id", "name",  "action","created")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_action(self, value):
        delete_url = reverse('core:delete_ministere', kwargs={'pk': value})
        update_url = reverse('core:update_ministere', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)





class SecteurFilter(FilterSet):
    #created = StackDateTimeFromToRangeFilter()
    class Meta:
        model = Secteur
        fields = ['name',"code"]

class SecteurTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")

    class Meta(DefaultTable.Meta):
        model = Secteur
        order_by = ("-id")
        fields = ("id","code" ,"name", "action" )

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_action(self, value):
        delete_url = reverse('core:delete_secteur', kwargs={'pk': value})
        update_url = reverse('core:update_secteur', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)

class CodeServiceFilter(FilterSet):
    #created = StackDateTimeFromToRangeFilter()
    class Meta:
        model = CodeService
        fields = ['code',"name"]

class CodeServiceTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")

    class Meta(DefaultTable.Meta):
        model = CodeService
        order_by = ("-id")
        fields = ("id","code" ,"name", "action")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_action(self, value):
        delete_url = reverse('core:delete_codeservice', kwargs={'pk': value})
        update_url = reverse('core:update_codeservice', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)



class DirectionFilter(FilterSet):
    #created = StackDateTimeFromToRangeFilter()
    class Meta:
        model = Direction
        fields = ['name',"ministere"]

class DirectionTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")

    class Meta(DefaultTable.Meta):
        model = Direction
        order_by = ("-id")
        fields = ("id", "name",  "action","ministere","created")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_action(self, value):
        delete_url = reverse('core:delete_direction', kwargs={'pk': value})
        update_url = reverse('core:update_direction', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)



from django.contrib.auth.models import Group

class GroupFilter(FilterSet):

    class Meta:
        model = Group
        fields = ['name', ]


class GroupTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")

    class Meta(DefaultTable.Meta):
        model = Group
        order_by="-pk"
        fields = ("id", "action","name","permissions","id")



    def render_action(self, value):
        delete_url = reverse('core:delete_group', kwargs={'pk': value})
        update_url = reverse('core:update_group', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)





class StructureFilter(FilterSet):
    #created = StackDateTimeFromToRangeFilter()
    class Meta:
        model = Structure
        fields = ['name']

class StructureTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")

    class Meta(DefaultTable.Meta):
        model = Structure
        order_by = ("-id")
        fields = ("id", "name",  "action","created")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_action(self, value):
        delete_url = reverse('core:delete_structure', kwargs={'pk': value})
        update_url = reverse('core:update_structure', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)


class ConfigurationOTPTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")

    class Meta(DefaultTable.Meta):
        model = ConfigurationOTP
        order_by = ("-id")
        fields = ("id", "validation_op",  "action","created")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_action(self, value):
        delete_url = reverse('core:delete_configurationotp', kwargs={'pk': value})
        update_url = reverse('core:update_configurationotp', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)