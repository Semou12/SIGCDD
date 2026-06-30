import traceback

from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.mixins import PopRequestMixin
from django import forms
from django.contrib.auth.models import Group
from django.contrib.postgres.forms import DateRangeField,IntegerRangeField
from django.core.exceptions import ValidationError
from djmoney.money import Money
from phonenumber_field.formfields import PhoneNumberField

from bankcheck.models import Cheque
from cddaccount import TYPE_REGLEMENT, PAYMENT_MEAN_TYPE, TYPE_VIREMENT, TYPE_FICHIER, NATURE_COMPTE, NATURE_FONDS
from cddaccount.models import generate_rib, Mandataire, VirementMasse, Report, JourneeComptable, AnneeComptable, \
    AvisDeDebit, \
    AvisDeCredit, Projet, BlocageFond, PrisEnchageOrdrePayment, Nature, Depositaire, ValidationCompte, CompteDepot, \
    PosteComptable, \
    Bank, CodeAgence, GerantCD, AgentSaisieCD, GestionCompteDepot, OrdrePayment, SettingsVRM, SousNature, \
    compute_all_balances_for_compte, TypeCompteTrx, ReportGestion, CompteTrx, DemandeOP
from core.models import Secteur, CodeService
from helpers.exceptions import SigException
from helpers.filters import LinkedDateWidget

import hashlib
class StackMoneyWidget(forms.TextInput):
    pass


class IbanInput(forms.TextInput):
    pass


pchoices = [(PAYMENT_MEAN_TYPE.CHEQUE, "CHEQUE"), (PAYMENT_MEAN_TYPE.VIREMENT, PAYMENT_MEAN_TYPE.VIREMENT),(PAYMENT_MEAN_TYPE.MOBILE, PAYMENT_MEAN_TYPE.MOBILE)]
#pchoices = [(PAYMENT_MEAN_TYPE.CHEQUE, "CHEQUE"), (PAYMENT_MEAN_TYPE.VIREMENT, PAYMENT_MEAN_TYPE.VIREMENT)]

class OrdrePaymentByBlocageFondModelForm(BSModalModelForm):
    phone_receptionnaire = PhoneNumberField(region="SN", label='Tel recuperateur',required=False)
    #amount = MoneyField(required=True,localize = True)
    iban=forms.CharField(max_length=150, widget=IbanInput(attrs={'class': "iban-inputmask form-control"}),required=False,label="Compte bancaire(ex:SN178 012000 1287656599899 99)")

    class Meta:
        model = OrdrePayment
        exclude = ["open_date","sig_reference","jour_comptable","compte","blocage","previous_etape","recepteur","observations","etape","initial_amount",'created',"creator","balance_after","balance_before","gerant","reference","status","date_prise_en_charge","date_visa"]

        widgets = {
             'iban': IbanInput(attrs={'class': "iban-inputmask form-control"})
         }

        #purchase-mask"

    def clean_iban(self):
        iban = self.cleaned_data['iban']
        if iban and len(iban) > 0:
            iban=iban.replace(" ", "")
            country_code=iban[:2]
            rib=iban[-2:]
            cal_rib=generate_rib(country_code,iban)
            if rib!=cal_rib:
                raise ValidationError("Compte bancaire non conforme",
                                      code='invalid',
                                      params={'value': iban},
                                      )
        return iban

    def clean_cheque(self):
        reference = self.cleaned_data['cheque']
        if reference:
            try:
                cheque=Cheque.objects.get(reference=reference)
                cheque.can_use_in_op()
            except SigException as e:
                raise ValidationError(e.message,
                    code='invalid',
                    params={'value': cheque},
                )
            except Cheque.DoesNotExist:
                raise ValidationError('Réference chèque introuvable : {}'.format(reference,),
                    code='invalid',
                    params={'value': reference},
                )
        return reference

class DepositaireModelForm(BSModalModelForm):
    phone = PhoneNumberField(region="SN", label='Téléphone')
    class Meta:
        model = Depositaire
        fields = ["firstname","lastname","phone","nin","teaser_signature","comptes"]

class SeeSoldeOrdrePaymentModelForm(PopRequestMixin,forms.Form):
    gestion=forms.ModelChoiceField(queryset=AnneeComptable.objects.all(),required=False, label="Sélectionner une gestion")
    compte=  forms.ModelChoiceField(queryset=CompteDepot.objects.none(),required=False, label="Sélectionner un compte")
    amount_fonc = forms.CharField(max_length=20, disabled=True, required=False, label="Montant fonctionnement CFA")
    amount_invest = forms.CharField(max_length=20, disabled=True, required=False, label="Montant investissement CFA")
    amount_global = forms.CharField(max_length=20, disabled=True, required=False, label="Montant global CFA")

    soldes = forms.CharField(max_length=150, widget=forms.Textarea,disabled=True, required=False,label="Details" )

    class Meta:
        widgets = {
            'type': forms.Select(attrs={"class": "select2 form-control"}),
        }

class DefaultSaisieOrdrePaymentModelForm(BSModalModelForm):
    payment_mean = forms.RadioSelect(choices=[(PAYMENT_MEAN_TYPE.CHEQUE,"COMPENSE"),(PAYMENT_MEAN_TYPE.VIREMENT,PAYMENT_MEAN_TYPE.VIREMENT)])
    phone_receptionnaire = PhoneNumberField(region="SN", label='Tel bénéficiaire',required=False)
    #amount = MoneyField(required=True,localize = True)
    amount = forms.CharField(max_length=20, widget=StackMoneyWidget(attrs={'class': "amount-inputmask form-control"}),
                             label="Montant CFA")

    #iban=forms.CharField(max_length=150, widget=IbanInput(attrs={'class': "iban-inputmask form-control"}),required=False,label="Compte bancaire(ex:SN178 012000 1287656599899 99)")

    class Meta:
        model = OrdrePayment
        exclude = ["open_date","type_gestion","sig_reference","jour_comptable","previous_etape","recepteur","observations","etape","initial_amount",'created',"creator","balance_after","balance_before","gerant","reference","status","date_prise_en_charge","date_visa"]

        widgets = {
             'iban': IbanInput(attrs={'class': "iban-inputmask form-control"})
         }

        #purchase-mask"

    def clean__(self):
        cleaned_data = super().clean()
        amount = cleaned_data['amount']
        compte = cleaned_data['compte']
        solde=compte.balance
        if solde.amount < amount:
            raise ValidationError("Solde compte {} inferieure au montant sisie{}".format(solde,Money(amount, "XOF")),code='danger')


    def clean_amount(self):
        amount = self.cleaned_data['amount']
        amount=amount.replace(" ", "")
        from decimal import Decimal

        return Decimal(amount)

    def clean_iban__(self):
        iban = self.cleaned_data['iban']
        if iban and len(iban)>0:
            iban=iban.replace(" ", "")
            country_code = iban[:2]
            rib = iban[-2:]
            cal_rib = generate_rib(country_code, iban)
            if rib != cal_rib:
                raise ValidationError("Compte bancaire non conforme",
                                      code='invalid',
                                      params={'value': iban},
                                      )
        return iban

    def clean_cheque__(self):
        reference = self.cleaned_data['cheque']
        if reference:
            try:
                cheque=Cheque.objects.get(reference=reference)
                cheque.can_use_in_op()
            except SigException as e:
                raise ValidationError(e.message,
                    code='invalid',
                    params={'value': cheque},
                )
            except Cheque.DoesNotExist:
                raise ValidationError('Réference chèque introuvable : {}'.format(reference,),
                    code='invalid',
                    params={'value': reference},
                )
        return reference



class DefaultSaisieOPChequeModelForm(DefaultSaisieOrdrePaymentModelForm):
    class Meta:
        model = OrdrePayment
        exclude = ["open_date","iban", "blocage", "payment_mean", "type_gestion", "sig_reference",
                   "jour_comptable", "previous_etape", "recepteur", "observations", "etape", "initial_amount", 'created',
                   "creator", "balance_after", "balance_before", "gerant", "reference", "status", "date_prise_en_charge",
                   "date_visa"]
class DefaultSaisieOPVirementModelForm(DefaultSaisieOrdrePaymentModelForm):

    class Meta:
        model = OrdrePayment
        exclude = ["open_date","cheque","receptionnaire","blocage","depositaire","payment_mean","type_gestion","sig_reference","jour_comptable","previous_etape","recepteur","observations","etape","initial_amount",'created',"creator","balance_after","balance_before","gerant","reference","status","date_prise_en_charge","date_visa"]

        widgets = {
             'iban': IbanInput(attrs={'class': "iban-inputmask form-control"})
         }

class SaisieOrdrePaymentModelForm(BSModalModelForm):
    phone_receptionnaire = PhoneNumberField(region="SN", label='Tel recuperateur',required=False)
    amount = forms.CharField(max_length=20, widget=StackMoneyWidget(attrs={'class': "amount-inputmask form-control"}),
                             label="Montant CFA")

    iban=forms.CharField(max_length=150, widget=IbanInput(attrs={'class': "iban-inputmask form-control"}),required=False,label="Compte bancaire(ex:SN178 012000 1287656599899 99)")

    class Meta:
        model = OrdrePayment
        exclude = ["open_date","sig_reference","jour_comptable","previous_etape","recepteur","observations","etape","initial_amount",'created',"creator","balance_after","compte","balance_before","gerant","reference","status","date_prise_en_charge","date_visa"]

        widgets = {
             'iban': IbanInput(attrs={'class': "iban-inputmask form-control"})
         }

        #purchase-mask"
    def clean_amount(self):
        amount = self.cleaned_data['amount']
        amount=amount.replace(" ", "")
        from decimal import Decimal

        return Decimal(amount)
    def clean_iban(self):
        iban = self.cleaned_data['iban']
        if iban and len(iban) > 0:
            iban=iban.replace(" ", "")

            country_code = iban[:2]
            rib = iban[-2:]
            cal_rib = generate_rib(country_code, iban)
            if rib != cal_rib:
                raise ValidationError("Compte bancaire non conforme",
                                      code='invalid',
                                      params={'value': iban},
                                      )
        return iban

    def clean_cheque(self):
        reference = self.cleaned_data['cheque']
        if reference:
            try:
                cheque=Cheque.objects.get(reference=reference)
                cheque.can_use_in_op()
            except SigException as e:
                raise ValidationError(e.message,
                    code='invalid',
                    params={'value': cheque},
                )
            except Cheque.DoesNotExist:
                raise ValidationError('Réference chèque introuvable : {}'.format(reference,),
                    code='invalid',
                    params={'value': reference},
                )
        return reference


class UpdateOrdrePaymentModelForm(BSModalModelForm):
    phone_receptionnaire = PhoneNumberField(region="SN", label='Téléphone receptionnaire ',required=False)
    amount = forms.CharField(max_length=20, widget=StackMoneyWidget(attrs={'class': "amount-inputmask form-control"}),
                             label="Montant CFA")

    class Meta:
        model = OrdrePayment
        exclude = ["open_date","sig_reference","depositaire","cin_receptionnaire","phone_receptionnaire","jour_comptable","previous_etape","recepteur","observations","etape","initial_amount",'created',"creator","balance_after","compte","balance_before","gerant","reference","status","date_prise_en_charge","date_visa"]

        # widgets = {
        #     'compte': forms.Select(attrs={'disabled': True})
        # }
    def clean_amount_(self):
        amount = self.cleaned_data['amount']
        amount=amount.replace(" ", "")
        from decimal import Decimal

        return Decimal(amount)
    def clean_cheque(self):
        reference = self.cleaned_data['cheque']
        if reference:
            try:
                cheque=Cheque.objects.get(reference=reference)
                if self.instance.cheque==reference:
                    pass
                else : cheque.can_use_in_op()
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




class UpdateOrdrePaymentPaymentModelForm(BSModalModelForm):
    payment_mean = forms.ChoiceField(choices=PAYMENT_MEAN_TYPE.CHOICES )
    class Meta:
        model = OrdrePayment
        fields = ["payment_mean"]



class UpdateOPChequeModelForm(UpdateOrdrePaymentModelForm):
    class Meta:
        model = OrdrePayment
        exclude = ["open_date","iban", "blocage", "payment_mean", "type_gestion","sig_reference", "depositaire", "cin_receptionnaire", "phone_receptionnaire", "jour_comptable",
                   "previous_etape", "recepteur", "observations", "etape", "initial_amount", 'created', "creator",
                   "balance_after", "compte", "balance_before", "gerant", "reference", "status", "date_prise_en_charge",
                   "date_visa"]

class UpdateOPVirementModelForm(UpdateOrdrePaymentModelForm):
    class Meta:
        model = OrdrePayment
        exclude = ["open_date","cheque","receptionnaire","blocage","depositaire", "payment_mean", "type_gestion","sig_reference", "depositaire", "cin_receptionnaire", "phone_receptionnaire", "jour_comptable",
                   "previous_etape", "recepteur", "observations", "etape", "initial_amount", 'created', "creator",
                   "balance_after", "compte", "balance_before", "gerant", "reference", "status", "date_prise_en_charge",
                   "date_visa"]


class PrisEnchageOrdrePaymentModalForm(BSModalModelForm):
    class Meta:
        model = PrisEnchageOrdrePayment
        fields = ["payment_mean","observations"]


class PriseEnChargeOrdrePaymentModelForm(forms.ModelForm):
    #phone_receptionnaire = PhoneNumberField(region="SN", label='Téléphone receptionnaire ',required=False)
    class Meta:
        model = OrdrePayment
        # widgets = {
        #      'secteur': forms.Select(attrs={'disabled': True}),
        #      'beneficiaire': forms.TextInput(attrs={'disabled': True})
        #  }
        exclude = ["payment_mean","reglement","sig_reference","depositaire","type_gestion","type_nature","phone_receptionnaire","receptionnaire","cin_receptionnaire","phone_receptionnaire","jour_comptable","previous_etape","amount","beneficiaire","iban","cheque","ninea","recepteur",'etape',"initial_amount",'created', "creator", "balance_after", "compte", "balance_before", "gerant", "reference", "status",
                   "date_prise_en_charge", "date_visa","blocage","depositaire","nature","open_date","object","secteur"]



class VisaOrdrePaymentModelForm(BSModalModelForm):
    class Meta:
        model = OrdrePayment
        fields = ["observations"]




class AffectationGerantCDModelForm(BSModalModelForm):
    period =DateRangeField(widget=LinkedDateWidget(),required=True,label="Période")

    class Meta:
        model = GestionCompteDepot
        exclude = ['created',"creator","agent_pc","actif","name"]

class AgentSaisieCDForm(PopRequestMixin,forms.ModelForm):
    #phone = PhoneNumberField(region="SN", label='Téléphone')

    nin = forms.CharField(max_length=150, required=True, )
    adresse = forms.CharField(max_length=150,  required=True, )

    class Meta:
        model = AgentSaisieCD
        fields = ['nin',"adresse"]


class UpdateAgentSaisieCDModelForm(BSModalModelForm):
    phone = PhoneNumberField(region="SN", label='Téléphone')
    roles = forms.ModelMultipleChoiceField(queryset=Group.objects.exclude(name="ADMIN"))

    class Meta:
        model = AgentSaisieCD
        fields = ["matricule", "firstname", "lastname", "phone","email","is_actif","comptes"]

class AgentSaisieCDModelForm(BSModalModelForm):
    phone = PhoneNumberField(region="SN", label='Téléphone')
    roles = forms.ModelMultipleChoiceField(queryset=Group.objects.exclude(name="ADMIN"))

    class Meta:
        model = AgentSaisieCD
        fields = ["matricule", "firstname", "lastname", "phone","email","comptes"]
class ValidationAgentSaisieCDForm(PopRequestMixin,forms.Form):
    compte= forms.ModelMultipleChoiceField(queryset=CompteDepot.objects.none())
    description = forms.CharField(max_length=150, widget=forms.Textarea,required=True,)



class GerantCDFormDIUserModelForm(BSModalModelForm):
    phone = PhoneNumberField(region="SN", label='Téléphone')
    compte = forms.ModelChoiceField(queryset=CompteDepot.objects.all())
    roles = forms.ModelMultipleChoiceField(queryset=Group.objects.exclude(name="ADMIN"))
    class Meta:
        model = GerantCD
        fields = ["matricule", "firstname", "lastname", "phone","email","poste","compte"]

class GerantCDModelForm(BSModalModelForm):
    phone = PhoneNumberField(region="SN", label='Téléphone')
    compte = forms.ModelChoiceField(queryset=CompteDepot.objects.all())
    roles = forms.ModelMultipleChoiceField(queryset=Group.objects.exclude(name="ADMIN"))
    class Meta:
        model = GerantCD
        fields = ["matricule", "firstname", "lastname", "phone","email","compte","roles"]


class UpdateGerantCDFormDIUserModelForm(BSModalModelForm):
    phone = PhoneNumberField(region="SN", label='Téléphone')
    compte = forms.ModelChoiceField(queryset=CompteDepot.objects.all())
    roles = forms.ModelMultipleChoiceField(queryset=Group.objects.exclude(name="ADMIN"))
    class Meta:
        model = GerantCD
        fields = ["matricule", "firstname", "lastname", "phone","poste"]


class UpdateGerantCDModelForm(BSModalModelForm):
    phone = PhoneNumberField(region="SN", label='Téléphone')
    roles = forms.ModelMultipleChoiceField(queryset=Group.objects.exclude(name="ADMIN"))
    class Meta:
        model = GerantCD
        fields = ["matricule", "firstname", "lastname", "phone","roles","structure"]

class ValidationGerantCDForm(PopRequestMixin,forms.Form):
    #compte= forms.ModelChoiceField(queryset=CompteDepot.objects.none())
    description = forms.CharField(max_length=150, widget=forms.Textarea,required=True,)
    signature = forms.FileField(required=False, label="Signature")


class ChoseCddAccountForm(PopRequestMixin,forms.Form):
    #compte= forms.ModelChoiceField(queryset=CompteDepot.objects.none(),widget=forms.Select(attrs={"class": "form-control"}))
    #description = forms.CharField(max_length=150, widget=forms.Textarea,required=False,)
    compte = forms.ModelChoiceField(queryset=CompteDepot.objects.none(),
                                    widget= forms.RadioSelect())



class CompleteGerantCDForm(PopRequestMixin,forms.ModelForm):
    justificatif = forms.FileField(required=False,label="Acte de nomination")
    teaser_signature=forms.ImageField(required=True,label="Signature")

    class Meta:
        model = GerantCD
        fields = ['acte_nomin','nin',"teaser_signature","justificatif","adresse"]

class CompteDepotModelForm(BSModalModelForm):
    compte = forms.CharField(max_length=150, widget=IbanInput(attrs={'class': "iban-inputmask form-control"}),required=False, label="Compte bancaire(ex:SN178 012000 1287656599899 99)")

    class Meta:
        model = CompteDepot
        fields=["reference_demande","ministere","direction","poste","secteur","code_service","libelle","libelle_court","compte"]
        exclude = ['created',"agent","valide","actif","balance","bank","agence","nature","typefond"]


    def clean_compte(self):
        iban = self.cleaned_data['compte']
        iban = iban.replace(" ", "")
        if iban and len(iban) > 0:
            iban=iban.replace(" ", "")
            country_code = iban[:2]
            rib = iban[-2:]
            try:
                cal_rib = generate_rib(country_code, iban)
            except:

                raise ValidationError("Compte bancaire non conforme",
                                      code='invalid',
                                      params={'value': iban},
                                      )

            if rib != cal_rib:
                raise ValidationError("Compte bancaire non conforme",
                                      code='invalid',
                                      params={'value': iban},
                                      )
        return iban



class CompteDepotNewModelForm(BSModalModelForm):
    compte = forms.CharField(max_length=8, required=False, label="Compte court")
    secteur = forms.ModelChoiceField(queryset=Secteur.objects.all(),required=False)
    code_service = forms.ModelChoiceField(queryset=CodeService.objects.all(), required=False)
    #typefond = forms.ChoiceField(choices=NATURE_FONDS.CHOICES,required=False)

    class Meta:
        model = CompteDepot
        fields=["reference_demande","ministere","poste","secteur","code_service","libelle","libelle_court","compte"]
        exclude = ['created',"agent","valide","actif","balance","bank","nature","agence"]


    def clean_compte__(self):
        iban = self.cleaned_data['compte']
        iban = iban.replace(" ", "")
        if iban and len(iban) > 0:
            iban=iban.replace(" ", "")
            country_code = iban[:2]
            rib = iban[-2:]
            try:
                cal_rib = generate_rib(country_code, iban)
            except:

                raise ValidationError("Compte bancaire non conforme",
                                      code='invalid',
                                      params={'value': iban},
                                      )

            if rib != cal_rib:
                raise ValidationError("Compte bancaire non conforme",
                                      code='invalid',
                                      params={'value': iban},
                                      )
        return iban


class UpdateDepotModelForm(BSModalModelForm):

    class Meta:
        model = CompteDepot
        fields=["actif","reference_demande","ministere","direction","poste","secteur","code_service","libelle","libelle_court"]
        exclude = ['created',"agent","valide","balance","bank","secrete","agence","typefond","nature"]



class UpdateSecretCompteDepotModelForm(BSModalModelForm):

    class Meta:
        model = CompteDepot
        fields=["actif","secrete","reference_demande","ministere","direction","poste","secteur","code_service","libelle","libelle_court"]
        exclude = ['created',"agent","valide","balance","bank","agence","typefond","nature"]

class ValidationCompteForm(PopRequestMixin,forms.ModelForm):

    class Meta:
        model = ValidationCompte
        exclude = ['created',"compte","agent","actif"]
from schwifty import BIC
class BankForm(BSModalModelForm):

    class Meta:
        model = Bank
        exclude = ['created',]

    def clean_bic(self):
        bic = self.cleaned_data['bic']
        try:
            BIC(str(bic))
        except:
            import traceback
            traceback.print_exc()
            c = traceback.format_exc(limit=0)
            raise forms.ValidationError(c)
        return bic


class CodeAgenceForm(BSModalModelForm):

    class Meta:
        model = CodeAgence
        exclude = ['created',]



class OtpValidationOrdrePaymentForm(PopRequestMixin,forms.Form):
    otp = forms.CharField(max_length=8,required=True)


class STATUS_ORDRE_PAYMENT:
    ACCEPTE = 'ACCEPTE'
    REJETE = 'REJETE'
    ANNULE = 'ANNULE'

    CHOICES = [
        (ACCEPTE, "ACCEPTE"),
        (REJETE, "REJETE"),
    ]

    CHOICES_2 = [
        (ACCEPTE, "ACCEPTE"),
        (REJETE, "REJETE"),
        (ANNULE, "ANNULER RECEPTION"),
    ]

class AcceptationOrdrePayementForm(PopRequestMixin,forms.Form):
    status=forms.ChoiceField(choices=STATUS_ORDRE_PAYMENT.CHOICES)
    description = forms.CharField(max_length=150, widget=forms.Textarea,required=False,)

    def clean(self):
        cleaned_data = super().clean()
        status =cleaned_data['status']
        desc = cleaned_data['description']

        if status==STATUS_ORDRE_PAYMENT.REJETE and not desc:
            raise ValidationError("Le champ description est obligatoire",code="success")



class AcceptationPourPriseEnChargeForm(PopRequestMixin,forms.Form):
    status=forms.ChoiceField(choices=STATUS_ORDRE_PAYMENT.CHOICES_2)
    description = forms.CharField(max_length=150, widget=forms.Textarea,required=False,)

    def clean(self):
        cleaned_data = super().clean()
        status =cleaned_data['status']
        desc = cleaned_data['description']

        if status==STATUS_ORDRE_PAYMENT.REJETE and not desc:
            raise ValidationError("Le champ description est obligatoire",code="success")




class MakeTrxPaymentForm(PopRequestMixin,forms.Form):
    max_amount = forms.CharField(widget=forms.HiddenInput())
    amount = forms.IntegerField(required=True,widget=forms.NumberInput,min_value=0,label="Montant")
    payment_mean = forms.ChoiceField(choices=PAYMENT_MEAN_TYPE.CHOICES,label="Mode de paiement")
    iban = forms.CharField(max_length=150, widget=IbanInput(attrs={'class': "iban-inputmask form-control"}),required=False, label="Compte bancaire(ex:SN178 012000 1287656599899 99)")
    def clean(self):
        cleaned_data = super().clean()
        max_amount = int(cleaned_data['max_amount'])
        amount = cleaned_data['amount']
        payment_mean = cleaned_data['payment_mean']
        #if payment_mean not in [PAYMENT_MEAN_TYPE.VIREMENT,PAYMENT_MEAN_TYPE.CHEQUE]:
        #    raise ValidationError("Moyen de paiement {} non authorisé".format(payment_mean,),code='danger')

        if payment_mean!=PAYMENT_MEAN_TYPE.VIREMENT and max_amount!=amount:
            raise ValidationError(
                "Le montant  saisie  {} est différent du montant autorisé {}".format(Money(amount, "XOF"),
                                                                                     Money(max_amount, "XOF")),
                code='danger')


    def clean_iban_(self):
        iban = self.cleaned_data['iban']
        if iban and len(iban)>0:
            iban=iban.replace(" ", "")
            country_code = iban[:2]
            rib = iban[-2:]
            cal_rib = generate_rib(country_code, iban)
            if rib != cal_rib:
                raise ValidationError("Compte bancaire non conforme",
                                      code='invalid',
                                      params={'value': iban},
                                      )
        return iban




class MakeTrxPaymentVRMForm(PopRequestMixin,forms.Form):

    amount = forms.IntegerField(required=True,widget=forms.NumberInput,min_value=0,label="Montant")
    payment_mean = forms.ChoiceField(choices=PAYMENT_MEAN_TYPE.CHOICES,label="Mode de paiement")




class NatureForm(BSModalModelForm):

    class Meta:
        model = Nature
        exclude = ['created',]

class SousNatureForm(BSModalModelForm):

    class Meta:
        model = SousNature
        exclude = ['created',]

class ProjetForm(BSModalModelForm):
    period = DateRangeField(widget=LinkedDateWidget())
    typecompte = forms.ModelChoiceField(queryset=TypeCompteTrx.objects.filter(nature=NATURE_COMPTE.INVESTISSEMENT), required=False)
    #compte_iban = forms.CharField(max_length=150, widget=IbanInput(attrs={'class': "iban-inputmask form-control"}),
    #                       required=True, label="Compte bancaire(ex:SN178 012000 1287656599899 99)")

    class Meta:
        model = Projet
        exclude = ["compte_iban",'created','creator','demande_date','acceptation_date','agent_postecomptable',"demande_blocage","accepter_blocage","status"]

    def clean_compte_iban(self):
        compte_iban = self.cleaned_data['compte_iban']
        compte_iban=compte_iban.replace(" ", "")


        iban=compte_iban
        if iban and len(iban) > 0:
            country_code = iban[:2]
            rib = iban[-2:]
            cal_rib = generate_rib(country_code, iban)
            if rib != cal_rib:
                raise ValidationError("Compte bancaire non conforme",
                                      code='invalid',
                                      params={'value': iban},
                                      )
        return compte_iban


class TYPE_PROVENANCE:
    POSTECOMPTABLE = 'POSTECOMPTABLE'
    AUTRES = 'AUTRES'

    CHOICES = [
        (POSTECOMPTABLE, "POSTE COMPTABLE"),
        (AUTRES, "AUTRES"),
    ]

class AvisDeCreditForm(BSModalModelForm):
    amount = forms.CharField(max_length=20, widget=StackMoneyWidget(attrs={'class': "amount-inputmask form-control"}),
                             label="Montant CFA")
    type_provenance = forms.ChoiceField(choices=TYPE_PROVENANCE.CHOICES,label="Type provenance")
    def clean_amount(self):
        amount = self.cleaned_data['amount']
        amount=amount.replace(" ", "")
        from decimal import Decimal
        return Decimal(amount)

    class Meta:
        model = AvisDeCredit
        fields=["libelle","amount","compte","nature","objet","type_provenance","provenance","autres"]
        #exclude = ["ligne","liod","page","bocagefond","obs_aster","status_aster","etape_compense","date_envoi","date_retour","poste_comptable","nature_depense","sens","payment_mean",'created',"date_validation","agent_validation","agent","jour_comptable"]

class AvisDeDebitForm(BSModalModelForm):
    amount = forms.CharField(max_length=20, widget=StackMoneyWidget(attrs={'class': "amount-inputmask form-control"}),label="Montant CFA")
    class Meta:
        model = AvisDeDebit
        exclude = ["ligne","liod","page","obs_aster","date_avis","reference_aster","status_aster","etape_compense","date_envoi","date_retour","poste_comptable","nature_depense","sens","payment_mean",'created',"date_validation","agent_validation","agent","jour_comptable"]

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        amount=amount.replace(" ", "")
        from decimal import Decimal

        return Decimal(amount)


class BlocageFondForm(BSModalModelForm):
    compte_iban = forms.CharField(max_length=150, widget=IbanInput(attrs={'class': "iban-inputmask form-control"}),
                           required=True, label="Compte bancaire(ex:SN178 012000 1287656599899 99)")

    class Meta:
        model = BlocageFond
        exclude = ['created',"date_validation","close","createur"]


class AnneeComptableForm(BSModalModelForm):
    period = DateRangeField(widget=LinkedDateWidget())
    class Meta:
        model = AnneeComptable
        exclude = ['created',"createur","name"]



class DemandeBlocagefondForm(PopRequestMixin,forms.Form):
    #otp = forms.CharField(max_length=8,required=True)
    description = forms.CharField(max_length=150, widget=forms.Textarea, required=True,)



class JourneeComptableForm(forms.ModelForm):

    class Meta:
        model = JourneeComptable
        fields = ['jour',]


class ActiverCompteDepotModelForm(BSModalModelForm):
    description = forms.CharField(max_length=150, widget=forms.Textarea, required=True, )

    class Meta:
        model = CompteDepot
        fields=["actif","description"]



class SimpleOPForm(PopRequestMixin,forms.Form):
    description = forms.CharField(max_length=150, widget=forms.Textarea,required=True,)

class CancelOPForm(PopRequestMixin,forms.Form):
    description = forms.CharField(max_length=150, widget=forms.Textarea,required=False,)


class TYPE_RELEVE:
    AVEC_INSTANCE = 'AVEC_INSTANCE'
    SANS_INSTANCE = 'SANS_INSTANCE'

    CHOICES = [

        (SANS_INSTANCE, "SANS INSTANCE"),

        (AVEC_INSTANCE, "AVEC INSTANCE"),
    ]
class ReleveCompteForm(PopRequestMixin,forms.Form):
    gestion = forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)
    period = DateRangeField(widget=LinkedDateWidget(),label="Période")
    #inst=forms.BooleanField( label="Avec instance",required=False)
    type = forms.ChoiceField(choices=TYPE_RELEVE.CHOICES, label="Type",widget=forms.RadioSelect, required=True,)


class BordereauOPForm(PopRequestMixin,forms.Form):
    #period = DateRangeField(widget=LinkedDateWidget(),label='Sélectionnez une periode',)
    period = forms.DateField(required=True)


class BalanceForm(PopRequestMixin,forms.Form):
    gestion = forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'), initial=0)
    jour = forms.DateField(required=True)

    def clean(self):
        cleaned_data = super().clean()
        gestion = cleaned_data['gestion']
        date = cleaned_data['jour']

        if not gestion.contains_date(date):
            raise ValidationError(
                "La date  saisie doit etre dans la periode de gestion",code='danger')

class BalanceTGForm(PopRequestMixin,forms.Form):
    gestion = forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'), initial=0)
    jour = forms.DateField(required=True)
    postes = forms.ModelChoiceField(queryset=PosteComptable.objects.all())


    def clean(self):
        cleaned_data = super().clean()
        gestion = cleaned_data['gestion']
        date = cleaned_data['jour']

        if not gestion.contains_date(date):
            raise ValidationError(
                "La date  saisie doit etre dans la periode de gestion",code='danger')



class ReportForm(BSModalModelForm):
    amount = forms.CharField(max_length=20, widget=StackMoneyWidget(attrs={'class': "amount-inputmask form-control"}),
                             label="Montant CFA")


    class Meta:
        model = ReportGestion
        exclude = ['created','creator',"sens","anne_comptable","taux","f_amount"]

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        amount = ''.join(list(map(lambda x: x.strip(), amount.split())))
        amount=amount.replace("FCFA", "")
        from decimal import Decimal
        return Decimal(amount)



from users.models import User

from django.contrib.auth.forms import AuthenticationForm
class CustomAuthenticationForm(AuthenticationForm):
    class Meta:
        model = User
        fields = ['username', 'password']



class VirementMasseForm(DefaultSaisieOrdrePaymentModelForm):

    class Meta:
        model = VirementMasse
        exclude = ["hash_file","cheque","reglement","beneficiaire","iban","ninea","receptionnaire","blocage","depositaire","payment_mean","type_gestion","sig_reference","jour_comptable","previous_etape","recepteur","observations","etape","initial_amount",'created',"creator","balance_after","balance_before","gerant","reference","status","date_prise_en_charge","date_visa"]

        widgets = {
             'iban': IbanInput(attrs={'class': "iban-inputmask form-control"}),
             "details_file":forms.FileInput(attrs={'class': "form-control","accept":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}),
         }

    def clean_details_file(self):

        IMAGE_FILE_TYPES = ['xls', 'xlsx']

        uploaded_image = self.cleaned_data.get("details_file", False)

        extension = str(uploaded_image).split('.')[-1]

        file_type = extension.lower()

        if not uploaded_image:
            raise ValidationError("Merci de charger un fichier excel")  # handle empty image

        if file_type not in IMAGE_FILE_TYPES:
            raise ValidationError("Merci de charger un fichier excel")

        return uploaded_image

#compte = forms.ModelChoiceField(queryset=CompteDepot.objects.none(),widget= forms.RadioSelect())




class BaseSaisiePaymentModelForm(BSModalModelForm):
    phone_receptionnaire = PhoneNumberField(region="SN", label='Tel bénéficiaire',required=False)
    amount = forms.CharField(max_length=20, widget=StackMoneyWidget(attrs={'class': "amount-inputmask form-control"}),
                             label="Montant CFA")
    details_file = forms.FileField(required=False, label="Fichier pour virement de masse")
    type_virement = forms.ChoiceField(choices=TYPE_VIREMENT.CHOICES, required=False, label="Type de virement")
    payment_mean = forms.ChoiceField(choices=[(PAYMENT_MEAN_TYPE.CHEQUE, "COMPENSE"),
                                              (PAYMENT_MEAN_TYPE.VIREMENT, PAYMENT_MEAN_TYPE.VIREMENT),(PAYMENT_MEAN_TYPE.RETRAIT,"RETRAIT ORDRE"),(PAYMENT_MEAN_TYPE.MOBILE,PAYMENT_MEAN_TYPE.MOBILE)], required=False,
                                     label="Mode de paiement")


    #amount_tva = forms.CharField(max_length=20, widget=StackMoneyWidget(attrs={'class': "amount-inputmask form-control"}),label="Montant HTVA")

    class Meta:
        model = OrdrePayment
        fields = ["payment_mean", "cheque", "type_nature", "amount", "type_virement", "object", "compte", "iban",
                  'details_file', "beneficiaire", "phone_receptionnaire", "ninea", "receptionnaire",
                  "cin_receptionnaire"]
        widgets = {
            'iban': IbanInput(attrs={'class': "iban-inputmask form-control"}),
            "details_file": forms.FileInput(attrs={'class': "form-control",
                                                   "accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}),
        }

    def can_debit_trx_by_type(self, amount, type,compute_disponible):
        type=type.nature
        if type == NATURE_COMPTE.FONCTIONNEMENT:
            balance = compute_disponible["fonct_balance"]["disponible"]
        elif type == NATURE_COMPTE.INVESTISSEMENT:
            balance = compute_disponible["invest_balance"]["disponible"]
        else:
            return False
        if balance >= amount :
            return True
        else:
            return False

    def get_solde_by_type(self, type, compute_disponible):
        balance = None
        if type.nature == NATURE_COMPTE.FONCTIONNEMENT:
            balance = compute_disponible["fonct_balance"]["disponible"]
        elif type.nature == NATURE_COMPTE.INVESTISSEMENT:
            balance = compute_disponible["invest_balance"]["disponible"]
        return balance
    def clean(self):
        cleaned_data = super().clean()
        
        iban = self.cleaned_data['iban']
        transfer_out_umeoa=self.cleaned_data['transfer_out_umeoa']
        if iban and len(iban) > 0 and not transfer_out_umeoa:
            iban = iban.replace(" ", "")
            country_code = iban[:2]
            rib = iban[-2:]
            try:
                cal_rib = generate_rib(country_code, iban)
                if rib != cal_rib:
                    raise ValidationError("Compte bancaire non conforme",
                                          code='invalid danger',
                                          params={'value': iban},
                                          )
            except:
                raise ValidationError("Compte bancaire non conforme",
                                      code='invalid danger',
                                      params={'value': iban},
                                      )

        amount = cleaned_data['amount']

        #type_solde=cleaned_data["type_nature"]
        type_solde = cleaned_data["typecompte"]

        if "account" in cleaned_data:
            gestion_id=AnneeComptable.current_gestion().id
            compte = CompteDepot.objects.get(id=cleaned_data['account'])
        else:
            compte = cleaned_data['compte']
            gestion_id = AnneeComptable.active_gestion().id

        if "gestion" in cleaned_data:gestion_id=cleaned_data['gestion']

        an=AnneeComptable.objects.get(id=gestion_id)
        if an.bloque:
            raise ValidationError("Operation non autorisé pour cette gestion  {}".format(an.name),code='danger')

        compute_disponible=compute_all_balances_for_compte(compte,update=False,gestion=gestion_id,for_gerant=True,type_compte=type_solde)  #solde calcule
        solde=self.get_solde_by_type(type_solde,compute_disponible)
        if not self.can_debit_trx_by_type( amount, type_solde,compute_disponible) :
            raise ValidationError("Disponible compte {} {} inférieur au montant saisie {}".format(type_solde,solde,Money(amount, "XOF")),code='danger')

        reference_cheque = cleaned_data['cheque']
        if reference_cheque:
            try:
                cheque = Cheque.objects.get(reference=reference_cheque)
                if hasattr(self,"instance") and self.instance.cheque==reference_cheque:
                    pass
                else : cheque.can_use_in_op()


                if cheque.chequier.compte != compte:
                    raise ValidationError("Réference chèque introuvable pour ce compte",
                                          code='invalid',
                                          params={'value': cheque},
                                          )

            except SigException as e:
                raise ValidationError(e.message,
                                      code='invalid',
                                      params={'value': cheque},
                                      )
            except Cheque.DoesNotExist:
                raise ValidationError('Réference chèque introuvable : {}'.format(reference_cheque, ),
                                      code='invalid',
                                      params={'value': reference_cheque},
                                      )

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if isinstance(amount,str):amount=amount.replace(" ", "")

        from decimal import Decimal
        return Decimal(amount)

    def clean_details_file(self):
        payment_mean = self.cleaned_data['payment_mean']
        amount= self.clean_amount()
        print(payment_mean)
        IMAGE_FILE_TYPES = ['xls', 'xlsx']
        uploaded_image = self.cleaned_data.get("details_file", False)
        extension = str(uploaded_image).split('.')[-1]
        file_type = extension.lower()
        if uploaded_image and file_type not in IMAGE_FILE_TYPES:
            raise ValidationError("Merci de charger un fichier excel")

        if "details_file" in self.request.FILES:
            filehandle = self.request.FILES["details_file"]

            if filehandle:
                verify_detailvirement_items_excel_file(filehandle,amount,payment_mean=payment_mean)

        return uploaded_image












class PaymentByBFModelForm(BSModalModelForm):
    blocagefond = forms.CharField(widget=forms.HiddenInput())
    phone_receptionnaire = PhoneNumberField(region="SN", label='Tel bénéficiaire',required=False)
    amount = forms.CharField(max_length=20, widget=StackMoneyWidget(attrs={'class': "amount-inputmask form-control"}),
                             label="Montant CFA")
    details_file = forms.FileField(required=False, label="Fichier pour virement de masse")
    type_virement = forms.ChoiceField(choices=TYPE_VIREMENT.CHOICES, required=False, label="Type de virement")
    payment_mean = forms.ChoiceField(choices=[(PAYMENT_MEAN_TYPE.CHEQUE, "COMPENSE"),
                                              (PAYMENT_MEAN_TYPE.VIREMENT, PAYMENT_MEAN_TYPE.VIREMENT)], required=False,
                                     label="Mode de paiement")

    class Meta:
        model = OrdrePayment
        fields = ["payment_mean", "cheque", "type_nature", "amount", "type_virement", "object", "iban",
                  'details_file', "beneficiaire", "phone_receptionnaire", "ninea", "receptionnaire",
                  "cin_receptionnaire"]
        widgets = {
            'iban': IbanInput(attrs={'class': "iban-inputmask form-control"}),
            "details_file": forms.FileInput(attrs={'class': "form-control",
                                                   "accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}),
        }


    def clean(self):
        cleaned_data = super().clean()
        iban = self.cleaned_data['iban']
        if iban and len(iban) > 0:
            iban = iban.replace(" ", "")
            country_code = iban[:2]
            rib = iban[-2:]
            cal_rib = generate_rib(country_code, iban)
            if rib != cal_rib:
                raise ValidationError("Compte bancaire non conforme",
                                      code='invalid danger',
                                      params={'value': iban},
                                      )

        amount = cleaned_data['amount']

        blocageFond = BlocageFond.objects.get(reference=cleaned_data['blocagefond'])
        compte = blocageFond.compte
        solde=blocageFond.balance


        if solde.amount < amount :
            raise ValidationError("Solde compte {} inférieur au montant saisie {}".format(solde,Money(amount, "XOF")),code='danger')

        reference_cheque = cleaned_data['cheque']
        if reference_cheque:
            try:
                cheque = Cheque.objects.get(reference=reference_cheque)
                if hasattr(self,"instance") and self.instance.cheque==reference_cheque:
                    pass
                else : cheque.can_use_in_op()


                if cheque.chequier.compte != compte:
                    raise ValidationError("Réference chèque introuvable pour ce compte",
                                          code='invalid',
                                          params={'value': cheque},
                                          )

            except SigException as e:
                raise ValidationError(e.message,
                                      code='invalid',
                                      params={'value': cheque},
                                      )
            except Cheque.DoesNotExist:
                raise ValidationError('Réference chèque introuvable : {}'.format(reference_cheque, ),
                                      code='invalid',
                                      params={'value': reference_cheque},
                                      )

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if isinstance(amount, str): amount = amount.replace(" ", "")

        from decimal import Decimal

        return Decimal(amount)

    def clean_details_file(self):
        payment_mean = self.cleaned_data['payment_mean']
        print(payment_mean)
        amount = self.clean_amount()
        IMAGE_FILE_TYPES = ['xls', 'xlsx']
        uploaded_image = self.cleaned_data.get("details_file", False)
        extension = str(uploaded_image).split('.')[-1]
        file_type = extension.lower()
        if uploaded_image and file_type not in IMAGE_FILE_TYPES:
            raise ValidationError("Merci de charger un fichier excel")

        if "details_file" in self.request.FILES:
            filehandle = self.request.FILES["details_file"]

            if filehandle:
                verify_detailvirement_items_excel_file(filehandle,amount,payment_mean=payment_mean)

        return uploaded_image


class SaisieOPWithCddAccountForm(BaseSaisiePaymentModelForm):
    account = forms.CharField(widget=forms.HiddenInput())
    gestion = forms.CharField(widget=forms.HiddenInput())
    details_file=forms.FileField(required=False,label="Fichier pour virement de masse")
    type_virement = forms.ChoiceField(choices=TYPE_VIREMENT.CHOICES, required=False,label="Type de virement")
    payment_mean = forms.ChoiceField(choices=pchoices,required=False,label="Moyen de paiement")
    #beneficiaire=forms.CharField(required=False)
    typecompte=forms.ModelChoiceField(required=True,queryset=TypeCompteTrx.objects.all())

    class Meta:
        model = OrdrePayment
        fields = ["payment_mean", "cheque", "typecompte", "amount","nature","sousnature", "type_virement","transfer_out_umeoa", "object", "iban",
                  'details_file', "beneficiaire", "phone_receptionnaire", "ninea"]


class UpdateOPWithCddAccountForm(SaisieOPWithCddAccountForm):
    pass


class SaisieOPWithPCForm(BaseSaisiePaymentModelForm):

    gestion = forms.CharField(widget=forms.HiddenInput())
    type_virement = forms.ChoiceField(choices=TYPE_VIREMENT.CHOICES, required=False, label="Type de virement")
    typecompte = forms.ModelChoiceField(required=True, queryset=TypeCompteTrx.objects.all())
    payment_mean = forms.ChoiceField(
        choices=pchoices,
        required=False, label="Mode de paiement")


    class Meta:
        model = OrdrePayment
        #exclude = ["compte","secteur","open_date","blocage","depositaire","type_gestion","sig_reference","jour_comptable","previous_etape","recepteur","observations","etape","initial_amount",'created',"creator","balance_after","balance_before","gerant","reference","status","date_prise_en_charge","date_visa"]
        fields=["payment_mean","typecompte","cheque","amount","nature","sousnature","type_virement","transfer_out_umeoa","object","compte","iban",'details_file',"beneficiaire","phone_receptionnaire","ninea"]

class UpdateOPWithPCForm(SaisieOPWithPCForm):
    pass


import pandas as pd
from tablib import Dataset


def verify_detailvirement_items_excel_file(filehandle,amount,payment_mean=None):

    if payment_mean==PAYMENT_MEAN_TYPE.MOBILE:
        return verify_mobile_detailvirement_items_excel_file(filehandle)
    df = pd.read_excel(filehandle, dtype=pd.StringDtype())
    dataset = Dataset().load(df)
    detailvirements = dataset.dict

    vrm_settings = SettingsVRM.object()
    if vrm_settings:
        plafond = vrm_settings.max_amount.amount
    else:
        raise ValidationError("Merci de faire la config pour les virements de masse")

    total = sum(float(d['MONTANT']) for d in detailvirements)
    if total!=amount:
        raise ValidationError("le montant saisie est different de celui du fichier")

    for dtails in detailvirements:
        try:
            montant = float(dtails["MONTANT"])
            beneficiaire = str(dtails["BENEFICIAIRE"])
            banque = str(dtails["BANQUE"])
            agence = str(dtails["AGENCE"])
            account = str(dtails["COMPTE"])
            rib = str(dtails["RIB"])
            rib_beneficiaire = "{}{}{}{}".format(banque, agence, account, rib)
            adrese_beneficiaire = "nonnrennseigne"  # str(dtails["ADRESSE_BENEFICIAIRE"])

            if montant > plafond:
                raise ValidationError(
                    "Le montant pour le beneficiaire {}  {} est superieur au montant plafonné {}".format(
                        beneficiaire, montant, plafond))

            iban = rib_beneficiaire
            if iban and len(iban) > 0:
                country_code = iban[:2]
                rib = iban[-2:]
                cal_rib = generate_rib(country_code, iban)
                if rib != cal_rib:
                    raise ValidationError(
                        "Le rib {} pour le beneficiaire {}  n'est pas conforme".format(iban, beneficiaire))
        except ValidationError as a:
            traceback.print_exc()
            raise a




def verify_mobile_detailvirement_items_excel_file(filehandle):
    df = pd.read_excel(filehandle, dtype=pd.StringDtype())
    dataset = Dataset().load(df)
    detailvirements = dataset.dict

    vrm_settings = SettingsVRM.object()
    if vrm_settings:
        plafond = vrm_settings.w_max_amount.amount
    else:
        raise ValidationError("Merci de faire la config pour les virements de masse")


    for dtails in detailvirements:
        try:

            phone = str(dtails["TELEPHONE"])

            if len(phone) != 9:
                ex = ValidationError("Le numéro de téléphone de la ligne est obligatoire et de 9 chiffres {}".format(
                        phone, ))
                raise ex

            prenom = str(dtails["PRENOM"])
            if len(prenom) > 100:
                ex = ValidationError("Le prénom de la ligne est obligatoire et inférieur ou égale à 100 caractères {}".format(
                        prenom, ))
                raise ex

            nom = str(dtails["NOM"])
            if len(nom) > 100:
                ex = ValidationError("Le nom de la ligne est obligatoire et inférieur ou égale à 100 caractères {}".format(
                        nom, ))
                raise ex

            wallet_provider = str(dtails["OPERATEUR"])
            if wallet_provider not in ["ORANGE", "WAVE", "FREE", "EXPRESSO"]:
                ex = ValidationError("Le nom de l'opérateur de la ligne est obligatoire et doit être une de valeurs suivantes :ORANGE,WAVE,FREE,EXPRESSO. {}".format(
                        wallet_provider, ))
                raise ex


            cin = str(dtails["CIN"])

            if len(cin) > 15:
                ex = ValidationError("Le cni de la ligne est obligatoire et inférieur ou égale à 15 caractères {}".format(
                        cin, ))
                raise ex

            montant = float(dtails["MONTANT"])

            if montant > plafond:
                raise ValidationError(
                    "Le montant pour le beneficiaire  {} est superieur au montant plafonné {}".format( montant, plafond))


        except ValidationError as a:
            traceback.print_exc()
            raise a




class ChargementFichierForm(forms.Form):
    details_file=forms.FileField(required=True,label="Fichier chargement")
    type = forms.ChoiceField(choices=TYPE_FICHIER.CHOICES, required=False,label="Type de virement")


class OpViseForm(PopRequestMixin,forms.Form):
    gestion = forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)
    comptes=  forms.ModelChoiceField(queryset=CompteDepot.objects.none(),required=False)
    #datevisa = forms.DateField(required=True,label="Date visa")

    period = DateRangeField(widget=LinkedDateWidget(), label="Période")

class OpViseWithAmountForm(PopRequestMixin,forms.Form):
    gestion = forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)
    comptes=  forms.ModelChoiceField(queryset=CompteDepot.objects.none(),required=False)
    #datevisa = forms.DateField(required=True,label="Date visa")

    period = DateRangeField(widget=LinkedDateWidget(), label="Période")
    amount = IntegerRangeField(label="Montant")



class OpViseTGForm(PopRequestMixin,forms.Form):
    gestion = forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)
    postes = forms.ModelChoiceField(queryset=PosteComptable.objects.all())
    comptes = forms.ModelChoiceField(queryset=CompteDepot.objects.all(), required=False, empty_label="--------",
                                     label="")
    #datevisa = forms.DateField(required=True,label="Date visa")
    period = DateRangeField(widget=LinkedDateWidget(), label="Période")

class AvisCreditFiltreForm(PopRequestMixin,forms.Form):
    gestion = forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)
    comptes =  forms.ModelChoiceField(queryset=CompteDepot.objects.none(),required=False)
    period = DateRangeField(widget=LinkedDateWidget(),label="Période")


class AvisCreditFiltreTGForm(PopRequestMixin,forms.Form):
    gestion = forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)
    postes = forms.ModelChoiceField(queryset=PosteComptable.objects.all())
    comptes =  forms.ModelChoiceField(queryset=CompteDepot.objects.all(),required=False,empty_label="--------",label="")
    period = DateRangeField(widget=LinkedDateWidget(),label="Période")

class AvisDebitForm(PopRequestMixin,forms.Form):
    gestion = forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)
    comptes = forms.ModelChoiceField(queryset=CompteDepot.objects.none(),required=False)
    period = DateRangeField(widget=LinkedDateWidget(),label="Période")

class AvisDebitTGForm(PopRequestMixin,forms.Form):
    gestion = forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)
    postes = forms.ModelChoiceField(queryset=PosteComptable.objects.all())
    comptes = forms.ModelChoiceField(queryset=CompteDepot.objects.all(),required=False,empty_label="--------",label="")
    period = DateRangeField(widget=LinkedDateWidget(),label="Période")

class MoyenPaiementForm(PopRequestMixin,forms.Form):
    gestion = forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)
    payment_mean = forms.ChoiceField(choices=PAYMENT_MEAN_TYPE.CHOICES,label="Moyen de paiement",required="False") 
    period = DateRangeField(widget=LinkedDateWidget(),label="Période")    
    

class DisponibleForm(PopRequestMixin,forms.Form):
    #period = DateRangeField(widget=LinkedDateWidget())
    gestion= forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)


class ChequesPartielVisesForm(PopRequestMixin,forms.Form):
    gestion= forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)
    comptes=  forms.ModelChoiceField(queryset=CompteDepot.objects.none(),required=False)
    period = DateRangeField(widget=LinkedDateWidget(),label="Période")


class ChequesPartielVisesTGForm(PopRequestMixin,forms.Form):
    gestion= forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)
    postes = forms.ModelChoiceField(queryset=PosteComptable.objects.all())
    comptes = forms.ModelChoiceField(queryset=CompteDepot.objects.all(), required=False, empty_label="--------",
                                     label="")
    period = DateRangeField(widget=LinkedDateWidget(),label="Période")


class NewDisponibleForm(PopRequestMixin,forms.Form):
    #period = DateRangeField(widget=LinkedDateWidget())
    gestion= forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)
    comptes=  forms.ModelChoiceField(queryset=CompteDepot.objects.none(),required=False)




class NewDisponibleTGForm(PopRequestMixin,forms.Form):
    #period = DateRangeField(widget=LinkedDateWidget())
    gestion= forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)

    postes = forms.ModelChoiceField(queryset=PosteComptable.objects.all())
    comptes = forms.ModelChoiceField(queryset=CompteDepot.objects.all(), required=False,empty_label="--------",label="")

class OPbyNatureForm(PopRequestMixin,forms.Form):
    gestion = forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)
    period = DateRangeField(widget=LinkedDateWidget(),label="Période")



class OPbyNatureTGForm(PopRequestMixin,forms.Form):
    gestion = forms.ModelChoiceField(queryset=AnneeComptable.objects.all().order_by('-name'),initial=0)
    postes = forms.ModelChoiceField(queryset=PosteComptable.objects.all())
    period = DateRangeField(widget=LinkedDateWidget(),label="Période")


class AnnuleVisaForm(PopRequestMixin,forms.Form):
    description = forms.CharField(max_length=150, widget=forms.Textarea,required=False,)


class MandataireModelForm(BSModalModelForm):
    phone = PhoneNumberField(region="SN", label='Téléphone')
    class Meta:
        model = Mandataire
        # fields = ["firstname","lastname","phone","nin","teaser_signature","comptes"]
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


class BulkTakeChequeVerifyPaymentForm(PopRequestMixin,forms.Form):
    type = forms.ChoiceField(choices=BENEF_CHOICES.CHOICES, required=True)
    mandataire = forms.ModelChoiceField(queryset=Mandataire.objects.none(), required=False)
    gerant = forms.ModelChoiceField(queryset=GerantCD.objects.none(), required=False)
class OtpForm(forms.Form):
    otp = forms.CharField(max_length=8,required=True)




class DeleteOPByPCForm(PopRequestMixin,forms.ModelForm):
    id = forms.HiddenInput()

    class Meta:
        model = OrdrePayment
        fields = ["id"]


class ChargementFichierIbanForm(forms.Form):
    details_file=forms.FileField(required=True,label="Fichier chargement")


class EmailForm(forms.Form):
    email = forms.EmailField(required=True)



class TypeCompteTrxModelForm(BSModalModelForm):
    class Meta:
        model = TypeCompteTrx
        # fields = ["firstname","lastname","phone","nin","teaser_signature","comptes"]
        fields = ["name","code","taux","reportable","nature", "actif"]


class CompteTrxModelForm(BSModalModelForm):
    class Meta:
        model = CompteTrx
        # fields = ["firstname","lastname","phone","nin","teaser_signature","comptes"]
        fields = ["report_valide", ]



class DemandeOPModelForm(BSModalModelForm):
    account = forms.CharField(widget=forms.HiddenInput())
    gestion = forms.CharField(widget=forms.HiddenInput())
    phone_receptionnaire = PhoneNumberField(region="SN", label='Tel bénéficiaire', required=False)
    amount = forms.CharField(max_length=20,
                             widget=StackMoneyWidget(attrs={'class': "amount-inputmask form-control"}),
                             label="Montant CFA")

    # beneficiaire=forms.CharField(required=False)

    class Meta:
        model = DemandeOP
        fields = [ "typecompte", "amount", "object",  "beneficiaire", "phone_receptionnaire", "ninea"]


    def can_debit_trx_by_type(self, amount, type, compute_disponible):
        type = type.nature
        if type == NATURE_COMPTE.FONCTIONNEMENT:
            balance = compute_disponible["fonct_balance"]["disponible"]
        elif type == NATURE_COMPTE.INVESTISSEMENT:
            balance = compute_disponible["invest_balance"]["disponible"]
        else:
            return False
        if balance >= amount:
            return True
        else:
            return False

    def get_solde_by_type(self, type, compute_disponible):
        balance = None
        if type.nature == NATURE_COMPTE.FONCTIONNEMENT:
            balance = compute_disponible["fonct_balance"]["disponible"]
        elif type.nature == NATURE_COMPTE.INVESTISSEMENT:
            balance = compute_disponible["invest_balance"]["disponible"]
        return balance

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if isinstance(amount,str):amount=amount.replace(" ", "")

        from decimal import Decimal
        return Decimal(amount)

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data['amount']

        # type_solde=cleaned_data["type_nature"]
        type_solde = cleaned_data["typecompte"]

        if "account" in cleaned_data:
            gestion_id = AnneeComptable.current_gestion().id
            compte = CompteDepot.objects.get(id=cleaned_data['account'])
        else:
            compte = cleaned_data['compte']
            gestion_id = AnneeComptable.active_gestion().id

        if "gestion" in cleaned_data: gestion_id = cleaned_data['gestion']

        an = AnneeComptable.objects.get(id=gestion_id)
        if an.bloque:
            raise ValidationError("Operation non autorisé pour cette gestion  {}".format(an.name), code='danger')

        compute_disponible = compute_all_balances_for_compte(compte, update=False, gestion=gestion_id, for_gerant=True,
                                                             type_compte=type_solde)  # solde calcule
        solde = self.get_solde_by_type(type_solde, compute_disponible)
        if not self.can_debit_trx_by_type(amount, type_solde, compute_disponible):
            raise ValidationError("Disponible compte {} {} inférieur au montant saisie {}".format(type_solde, solde,
                                                                                                  Money(amount, "XOF")),
                                  code='danger')





class CreateOPfromDemandeForm(PopRequestMixin,forms.Form):
    max_amount = forms.CharField(widget=forms.HiddenInput())
    amount = forms.IntegerField(required=True,widget=forms.NumberInput,min_value=0,label="Montant")
    payment_mean = forms.ChoiceField(choices=PAYMENT_MEAN_TYPE.CHOICES,label="Moyen paiement")
    iban = forms.CharField(max_length=150, widget=IbanInput(attrs={'class': "iban-inputmask form-control"}),required=False, label="Compte bancaire(ex:SN178 012000 1287656599899 99)")
    def clean(self):
        cleaned_data = super().clean()
        max_amount = int(cleaned_data['max_amount'])
        amount = cleaned_data['amount']
        payment_mean = cleaned_data['payment_mean']
        #if payment_mean not in [PAYMENT_MEAN_TYPE.VIREMENT,PAYMENT_MEAN_TYPE.CHEQUE]:
        #    raise ValidationError("Moyen de paiement {} non authorisé".format(payment_mean,),code='danger')

        if payment_mean!=PAYMENT_MEAN_TYPE.VIREMENT and max_amount!=amount:
            raise ValidationError(
                "Le montant  saisie  {} est différent du montant autorisé {}".format(Money(amount, "XOF"),
                                                                                     Money(max_amount, "XOF")),
                code='danger')