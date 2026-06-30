from __future__ import unicode_literals
from django_filters import fields, widgets,Filter
from django import forms
from django.http import QueryDict
from datetime import datetime, time
from django_filters.utils import handle_timezone
from django.utils import formats
from django.core.exceptions import ValidationError



class LinkedDateTimeWidget(widgets.RangeWidget):
    pass

class LinkedDateWidget(widgets.RangeWidget):
    pass


class StackDefaultFromToRangeFilter(Filter):
    pass
class StackDateRangeWidget(forms.TextInput):
    pass

class StackDateRangeField(forms.CharField):
    widget=StackDateRangeWidget
    def to_python(self, value):
        value = super().to_python(value)
        if value in self.empty_values:
            return ""
        if self.localize:
            value = formats.sanitize_separators(value)
        if not '-' in value:
            raise ValidationError("format range date invalide ", code="invalid")
        return value

class StackDateFromToRangeFilter(StackDefaultFromToRangeFilter):
    def filter(self, qs, value):
        format = '%d/%m/%Y'
        if value:
            if not '-' in value: raise ValidationError("format range date invalide ", code="invalid")
            if len(value) > 3:
                start, stop = value.split(" - ")
                value=(datetime.strptime(start, format).date(), datetime.strptime(stop, format).date())

                self.lookup_expr = 'range'

        return super().filter(qs, value)


class StackDateTimeRangeWidget(forms.TextInput):
    pass
class StackDateTimeRangeField(forms.CharField):
    widget=StackDateTimeRangeWidget

    def to_python(self, value):
        value = super().to_python(value)
        if value in self.empty_values:
            return ""
        if self.localize:
            value = formats.sanitize_separators(value)
        if not '-' in value:
            raise ValidationError("format range date invalide ", code="invalid")
        return value
class StackDateTimeFromToRangeFilter(StackDefaultFromToRangeFilter):
    field_class = StackDateTimeRangeField
    def filter(self, qs, value):
        format = '%d/%m/%Y %H:%M:%S'
        if value:
            if "-" in value:
                pass
            else:
                raise ValidationError("format range date invalide ", code="invalid")
            if len(value) > 3:
                start, stop = value.split(" - ")
                value=(datetime.strptime(start, format), datetime.strptime(stop, format))

                self.lookup_expr = 'range'

        return super().filter(qs, value)



