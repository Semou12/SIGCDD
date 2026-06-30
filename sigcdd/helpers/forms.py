from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm

from django import forms


class DefaultModelForm(forms.ModelForm):
	pass
class DefaultModalModelForm(BSModalModelForm):
	pass
class DefaultForm(forms.Form):
	pass
