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
from helpers.models import FakeModel

from helpers.filters import StackDateTimeFromToRangeFilter,StackDateFromToRangeFilter


class FakeModelFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter()
    #date = StackDateFromToRangeFilter()

    class Meta:
        model = FakeModel
        fields = ['is_active', "user","created"]

class DefaultTable(tables.Table):
    class Meta:
        template_name = 'django_tables2/bootstrap4.html'
        attrs = {'class': 'table table-striped table-bordered dataex-res-rowcontrol'}




class FakeModelTable(DefaultTable):
    class Meta(DefaultTable.Meta):
        model = FakeModel
        fields = ("id", "user","date","created","is_active","rate","sid")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M:%S}".format(value)) if value else "---"
    def render_date(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

    def render_is_active(self, value):
        if value:
            _str="""<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)


