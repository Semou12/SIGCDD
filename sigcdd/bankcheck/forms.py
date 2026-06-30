from bankcheck.models import Imprimeur, ComptableMatiere, DAP, TypeChequier, Commande, ElementCommande, Chequier, Cheque, AgentDAP, CompenseCheque, \
    AnnulationCheque, MiseEnOpposition, RejetCheque
from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.mixins import PopRequestMixin
from django import forms
from phonenumber_field.formfields import PhoneNumberField
from django.contrib.auth.models import Group

from cddaccount.models import Mandataire
from helpers.exceptions import SigException
from helpers.filters import StackDateRangeField,LinkedDateWidget
from core.models import ProfilePC
from django.contrib.postgres.forms  import  DateRangeField
from django.core.exceptions import ValidationError
class ChequierOtpForm(PopRequestMixin,forms.Form):
    otp = forms.CharField(max_length=8, required=True)



class TYPE_PC_CHOICES:
    COMPTABLE = 'COMPTABLE'
    MATIERE = 'MATIERE'


    CHOICES = [
    ("COMPTABLE", "AGENT COMPTABLE"),
        ("MATIERE", "COMPTABLE MATIERE"),
     ]

class ChequierdapOtpForm(PopRequestMixin,forms.Form):
    #otp = forms.CharField(max_length=8, required=True)
    type = forms.ChoiceField(choices=TYPE_PC_CHOICES.CHOICES, required=True)
    agent=forms.ModelChoiceField(queryset=ProfilePC.objects.none())
    matiere = forms.ModelChoiceField(queryset=ComptableMatiere.objects.none())

class ChequierSimpleForm(PopRequestMixin,forms.Form):
    description = forms.CharField(max_length=150, widget=forms.Textarea,required=False,)


class EditBordereauForm(PopRequestMixin,forms.Form):
    imprimeur = forms.ModelChoiceField(queryset=Imprimeur.objects.all())




class CommandeChequierForm(forms.Form):
    pass

class TypeChequierForm(BSModalModelForm):

    class Meta:
        model = TypeChequier
        exclude = ['created',]


class DAPForm(BSModalModelForm):

    class Meta:
        model = DAP
        exclude = ['created', "lat", "lon", "type", "creator", "zip_code", "fax", "reference", "in_production",
                   "others"]

class AgentDAPForm(BSModalModelForm):
    phone = PhoneNumberField(region="SN", label='Téléphone')
    roles = forms.ModelMultipleChoiceField(queryset=Group.objects.exclude(name="ADMIN"))

    class Meta:
        model = AgentDAP
        fields = ["matricule", "firstname", "lastname", "phone","email","roles"]

class ElementCommandeForm(forms.ModelForm):

    class Meta:
        model = ElementCommande
        exclude = ['created','commande']
        widgets = {
            'type': forms.Select(attrs={"class": "select2 form-control"}),
        }


class CommandeForm(forms.ModelForm):

    class Meta:
        model = Commande
        exclude = ['first_sequence','last_sequence','created',"demandeur","agent_pc","reference","agent_dap","status","acceptation_date","process_date","traiter","accepter"]



class ChequierForm(forms.ModelForm):

    class Meta:
        model = Chequier
        exclude = ['created','commande',"compte","demande","taille","reference","dap",'first_sequence','last_sequence']
        widgets = {
            'type': forms.Select(attrs={"class": "select2 form-control"}),
        }



class CompenseChequeForm(BSModalModelForm):
    date_compense = forms.DateField(label="Date Compense",
                          widget=forms.DateTimeInput(format='%d/%m/%Y %H:%M:%S', attrs={'class': 'datetimepicker'}),
                          input_formats=('%d/%m/%Y %H:%M:%S',))

    class Meta:
        model = CompenseCheque
        exclude = ['created','cheque','creator',"trx","amount","aster_date","aster","compte"]

    def clean_reference(self):
        reference = self.cleaned_data['reference']
        if reference:
            try:
                cheque=Cheque.objects.get(reference=reference)
                cheque.can_use_for_compense()
            except SigException as e:
                raise ValidationError(e.message,
                    code='invalid',
                    params={'value': reference},
                )
            except Cheque.DoesNotExist:
                raise ValidationError('Réference chèque introuvable : {}'.format(reference,),
                    code='invalid',
                    params={'value': reference},
                )
        return reference


class MiseEnOppositionForm(BSModalModelForm):

    class Meta:
        model = MiseEnOpposition
        exclude = ['created','cheque',"accepter","acceptation_date","demandeur","approbation_date","approuver","approbateur","accepteur","amount"]

    def clean_reference(self):
        reference = self.cleaned_data['reference']
        if reference:
            try:
                cheque=Cheque.objects.get(reference=reference)
                #cheque.can_use_for_miseop()
            except SigException as e:
                raise ValidationError(e.message,
                    code='invalid',
                    params={'value': reference},
                )
            except Cheque.DoesNotExist:
                raise ValidationError('Réference chèque introuvable : {}'.format(reference,),
                    code='invalid',
                    params={'value': reference},
                )
        return reference

class AnnulationChequeForm(BSModalModelForm):

    class Meta:
        model = AnnulationCheque
        exclude = ['created','cheque',"accepter","acceptation_date","demandeur","approbation_date","approuver","approbateur","accepteur","amount"]


    def clean_reference(self):
        reference = self.cleaned_data['reference']
        if reference:
            try:
                cheque=Cheque.objects.get(reference=reference)
                cheque.can_use_for_annulation()
            except SigException as e:
                raise ValidationError(e.message,
                    code='invalid',
                    params={'value': reference},
                )
            except Cheque.DoesNotExist:
                raise ValidationError('Réference chèque introuvable : {}'.format(reference,),
                    code='invalid',
                    params={'value': reference},
                )
        return reference


class RejetChequeForm(BSModalModelForm):

    class Meta:
        model = RejetCheque
        exclude = ['created',"op",'cheque',"accepter","acceptation_date","demandeur","approbation_date","approuver","approbateur","accepteur","amount"]


    def clean_reference(self):
        reference = self.cleaned_data['reference']
        if reference:
            try:
                cheque=Cheque.objects.get(reference=reference)
                cheque.can_use_for_annulation()
            except SigException as e:
                raise ValidationError(e.message,
                    code='invalid',
                    params={'value': reference},
                )
            except Cheque.DoesNotExist:
                raise ValidationError('Réference chèque introuvable : {}'.format(reference,),
                    code='invalid',
                    params={'value': reference},
                )
        return reference





class ComptableMatiereForm(BSModalModelForm):
    phone = PhoneNumberField(region="SN", label='Téléphone')

    class Meta:
        model = ComptableMatiere
        fields = ["firstname", "lastname", "phone", "nin"]

class BENEF_CHOICES:
    GERANT = 'GERANT'
    MANDATAIRE = 'MANDATAIRE'


    CHOICES = [
    ("GERANT", "GERANT"),
        ("MANDATAIRE", "MANDATAIRE"),
     ]
class TakeChequeVerifyPaymentForm(PopRequestMixin,forms.Form):
    type = forms.ChoiceField(choices=BENEF_CHOICES.CHOICES, required=True)
    mandataire = forms.ModelChoiceField(queryset=Mandataire.objects.none(), required=False)
    #tel_benef =  forms.CharField(label='Tel bénéficiaire',required=False)
