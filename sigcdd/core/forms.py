from bootstrap_modal_forms.forms import BSModalModelForm, BSModalForm
from bootstrap_modal_forms.mixins import PopRequestMixin, CreateUpdateAjaxMixin
from core.models import Structure, Direction, CodeService, DCP, Agent, AffectationAgent, PosteComptable, ProfileDCP, \
    ProfilePC, TG, PGT, RGT, TPR, ACGP, Ministere, Secteur, ConfigurationOTP
from jsignature.forms import JSignatureField
from jsignature.widgets import JSignatureWidget
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberPrefixWidget
from django import forms
from django.contrib.auth.models import Group

from helpers.models import Role
from helpers.filters import StackDateRangeField,LinkedDateWidget

from django.contrib.postgres.forms  import  DateRangeField



class GroupModelForm(BSModalModelForm):
    roles= forms.MultipleChoiceField(choices=Role.choices,label="Types agents")

    class Meta:
        model = Group
        fields='__all__'

class PosteComptableModelForm(BSModalModelForm):
    #phone = PhoneNumberField(region="SN",required=False,label="Téléphone")

    class Meta:
        model = PosteComptable
        exclude = ['created',"lat","lon","creator","zip_code","fax","dcp"]

class TGModelForm(PosteComptableModelForm):
    class Meta(PosteComptableModelForm.Meta):
        model = TG
        exclude = PosteComptableModelForm.Meta.exclude



class TPRModelForm(PosteComptableModelForm):
    class Meta(PosteComptableModelForm.Meta):
        model = TPR
        exclude = PosteComptableModelForm.Meta.exclude


class PGTModelForm(PosteComptableModelForm):
    class Meta(PosteComptableModelForm.Meta):
        model = PGT
        exclude = PosteComptableModelForm.Meta.exclude

class RGTModelForm(PosteComptableModelForm):
    class Meta(PosteComptableModelForm.Meta):
        model = RGT
        exclude = PosteComptableModelForm.Meta.exclude

class ACGPModelForm(PosteComptableModelForm):
    class Meta(PosteComptableModelForm.Meta):
        model = ACGP
        exclude = PosteComptableModelForm.Meta.exclude



class DCPModelForm(BSModalModelForm):
    #phone = PhoneNumberField(region="SN", required=False, label="Téléphone")

    class Meta:
        model = DCP
        exclude = ['created',"lat","lon","type","creator","zip_code","fax","reference","in_production","others"]




class AffectationAgentModelForm(BSModalModelForm):
    period =DateRangeField(widget=LinkedDateWidget())


    class Meta:
        model = AffectationAgent
        exclude = ['created',"creator",]


class AgentModelForm(BSModalModelForm):
    #signature_2 = signature = JSignatureField(widget=JSignatureWidget(jsignature_attrs={'background-color':"#CCC"}))
    phone = PhoneNumberField(region="SN",label='Téléphone')
    roles=forms.ModelMultipleChoiceField(queryset=Group.objects.exclude(name="ADMIN"))
    class Meta:
        model = Agent
        fields=["matricule","firstname","lastname","phone","adresse","nin","dob","lieu_dob","sexe","teaser_image","teaser_signature","email"]
        #exclude = ['created',"nin","user","father_lastname","father_firstname","mother_lastname","mother_firstname","date_delivrance","date_expiration","type_piece","piece_verso","piece_recto","fingerprint2B64","teaser_empreinte","cedeao_numero"]



class ProfileDCPModelForm(AgentModelForm):

    class Meta:
        model = ProfileDCP
        fields = ["matricule", "firstname", "lastname", "phone","email"]
        #exclude = ['created', "user", "father_lastname", "father_firstname", "mother_lastname", "mother_firstname",
        #           "date_delivrance", "date_expiration", "type_piece", "piece_verso", "piece_recto", "fingerprint2B64",
        #           "teaser_empreinte", "cedeao_numero","dcp","fonction","creator"]


class ProfilePCModelForm(AgentModelForm):
    class Meta:
        model = ProfilePC
        fields = ["poste","matricule", "firstname", "lastname", "phone","email"]

        #exclude = ['created', "user", "father_lastname", "father_firstname", "mother_lastname", "mother_firstname",
                   #"date_delivrance", "date_expiration", "type_piece", "piece_verso", "piece_recto", "fingerprint2B64",
                   #"teaser_empreinte", "cedeao_numero","fonction","creator"]


class SecteurModelForm(BSModalModelForm):

    class Meta:
        model = Secteur
        exclude = ['created',]

class MinistereModelForm(BSModalModelForm):

    class Meta:
        model = Ministere
        exclude = ['created',]


class CodeServiceModelForm(BSModalModelForm):

    class Meta:
        model = CodeService
        exclude = ['created',]



class DirectionModelForm(BSModalModelForm):

    class Meta:
        model = Direction
        exclude = ['created',]



class StructureModelForm(BSModalModelForm):

    class Meta:
        model = Structure
        exclude = ['created',"phone", "email","street","zip_code","city"]

class UpdateStructureLogoForm(PopRequestMixin,forms.Form):

    ministere = forms.ModelChoiceField(queryset=Ministere.objects.all(), required=False)
    structure = forms.ModelChoiceField(queryset=Structure.objects.all())
    logo = forms.FileField(required=True, label="Logo")



class StructureUpdateModelForm(BSModalModelForm):

    class Meta:
        model = Structure
        fields = ["name","logo"]



class ConfigurationOTPModelForm(BSModalModelForm):

    class Meta:
        model = ConfigurationOTP
        exclude = ['created',]