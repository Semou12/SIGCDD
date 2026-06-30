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

from urllib.parse import  urlencode
from django.utils import datetime_safe, formats

from cddaccount import PAYMENT_MEAN_TYPE, TYPE_REGLEMENT
from cddaccount.models import DemandeOP, TypeCompteTrx, Role, Mandataire, SousNature, VirementDetails, Report, \
    AnnulationBlocageFond, BlocageFond, AnneeComptable, AvisDeDebit, Projet, AvisDeCredit, Nature, Depositaire, \
    TransactionOP, ValidationCompte, CompteDepot, Bank, CodeAgence, GerantCD, AgentSaisieCD, GestionCompteDepot, \
    OrdrePayment, ETAPE_ORDRE_PAYMENT, ReportGestion, CompteTrx

from helpers.filters import StackDateTimeFromToRangeFilter,StackDateFromToRangeFilter
from django.utils.translation import gettext_lazy as _


choices = (
    ("unknown", "-------"),
    ("true", _("Yes")),
    ("false", _("No")),
)
from distutils.util import strtobool
class DefaultTable(tables.Table):
    class Meta:
        template_name = 'datatables/templateB4.html'
        #template_name = 'datatables/template_htmx.html'
        attrs = {'class': 'table table-striped table-bordered  table-sm responsive dataex-res-rowcontrol'}



class BankFilter(FilterSet):

    class Meta:
        model = Bank
        fields = ['code',"name"]


class BankTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")

    class Meta(DefaultTable.Meta):
        model = Bank
        #order_by = ("-pk")
        fields = ("code","name",'bic',"action")
    def render_action(self, value):
        delete_url = reverse('cddaccount:delete_bank', kwargs={'pk': value})
        update_url = reverse('cddaccount:update_bank', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)





class CompteDepotFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter(label="Date création")
    #date = StackDateFromToRangeFilter()
    libelle = CharFilter(lookup_expr='icontains',label="Libélle")
    libelle_court = CharFilter(lookup_expr='icontains', label="Libélle court")
    compte = CharFilter(lookup_expr='icontains', label="Compte")
    #valide = BooleanFilter(widget=forms.NullBooleanSelect(choices=choices), label="Est valide ?" )
    #actif = BooleanFilter(widget=widgets.BooleanWidget(), label="Est actif ?")
    actif = TypedChoiceFilter(choices=choices,coerce=strtobool)
    valide = TypedChoiceFilter(choices=choices, coerce=strtobool,label="Validé")


    class Meta:
        model = CompteDepot
        fields = ['libelle',"libelle_court","created" ,"nature","poste","actif","valide","compte"]


class CompteDepotTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor=A("actions"))
    info = tables.Column(verbose_name='Détails', accessor=A("get_absolute_url"))



    class Meta(DefaultTable.Meta):
        model = CompteDepot
        template_name = 'datatables/templateB4.html'
        #order_by = ("-pk")
        fields = ("short_compte","action","compte","libelle_court","poste","actif","ministere","direction","secteur","libelle","agent","created","open_date")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M:%S}".format(value)) if value else "---"

    def render_actif(self, value):
        if value:
            _str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)

    def render_valide(self, value):
        if value:
            _str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)



    def render_info(self, value):
        str = """
        <a href = "{}" class=" btn btn-sm btn-info" >
          <span class="fa fa-info"></span>
        </a>
        """.format(value,)
        return format_html(str)

    def render_action(self,value):
        user = self.request.user
        delete_url = reverse('cddaccount:delete_comptedepot', kwargs={'pk': value.pk})
        update_url = reverse('cddaccount:update_comptedepot', kwargs={'pk': value.pk})

        str = """<div class="form-group">"""

        if user.has_perm('cddaccount.change_comptedepot'):
            str += """
                    <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
                      <span class="fa fa-pencil"></span>
                    </button>""".format(update_url,)

        if user.has_perm('cddaccount.delete_comptedepot'):
    	         str += """<button type="button" class="delete-item btn btn-sm btn-danger btn-block" data-form-url="{}">
    	          <span class="fa fa-trash"></span>
    	        </button>
    	        """.format( delete_url)

        if user.has_perm('cddaccount.add_activationcompte'):
            validate_url = reverse('cddaccount:activer_comptedepot', kwargs={'id': value.pk})
            if value.actif: s="Désactiver"
            else:s="Activer"
            str += """<button type="button" class="activer-item btn btn-sm btn-warning btn-block"  title="Valiider" data-form-url="{}">
                  <span >{}</span>
                </button>
                """.format(validate_url,s)

        if not hasattr(value, "validation_cd"):
            if user.has_perm('cddaccount.add_validationcompte'):
                validate_url = reverse('cddaccount:create_validationcompte', kwargs={'id': value.pk})
                str += """<button type="button" class="validate-item btn btn-sm btn-purple btn-block"  title="Valiider" data-form-url="{}">
                      <span >Valider</span>
                    </button>
                    """.format(validate_url)
            else: str+="ATTENTE VALIDATION"



        url_rb = reverse_lazy('cddaccount:genere_releve_compte', kwargs={"reference": value.short_compte})

        #bloc rajouté par Assane Goumbele le 7 septembre 2023 pour corriger le bug n 84 dans mantis
        if user.role == Role.AGENT_DCP:
            

            str += "</div>"
        else:
            str += """<button  class="show-releve-item btn btn-sm btn-outline-primary btn-block" data-form-url="{}"><span >Relevé de compte </span></button>""".format(
            url_rb, )

            str += "</div>"
        #ajout btt ajout structure dans la colonne action

        if user.has_perm('core.add_structure'):
            if value.structure :
                create_structure_url = reverse_lazy('core:update_structure',kwargs={"pk":value.structure.pk})
                text_btt = "MAJ structure"
            else:
                #create_structure_url = reverse_lazy('core:create_structure')
                create_structure_url = reverse_lazy('core:link_compte_to_structure')
                text_btt = "Ajout structure"
            
            str += """<button type="button" class="activer-item btn btn-sm btn-warning btn-block"  title="Valiider" data-form-url="{}">
                  <span >{}</span>
                </button>
                """.format(create_structure_url,text_btt)


        return format_html(str)
    

class CodeAgenceFilter(FilterSet):

    class Meta:
        model = CodeAgence
        fields = ['code',"bank"]


class CodeAgenceTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")
    bank_name= tables.Column(verbose_name='Nom banque', accessor="bank__name")
    bank_bic = tables.Column(verbose_name='Bic', accessor="bank__bic")
    bank_code = tables.Column(verbose_name='Code banque', accessor="bank__code")

    class Meta(DefaultTable.Meta):
        model = CodeAgence
        order_by = ("-pk")
        fields = ("code","bank_name","bank_code","bank_bic","action")
    def render_action(self, value):
        delete_url = reverse('cddaccount:delete_codeagence', kwargs={'pk': value})
        update_url = reverse('cddaccount:update_codeagence', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)



class GerantCDFilter(FilterSet):
    #date = StackDateFromToRangeFilter()
    is_actif = TypedChoiceFilter(choices=choices, coerce=strtobool, label="Est actif")

    class Meta:
        model = GerantCD
        fields = ['phone', "lastname","firstname","is_actif"]


class GerantCDTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor=A("actions"))
    roles = tables.Column(verbose_name='Rôles', accessor="format_roles")
    comptes = tables.Column(verbose_name='Comptes', accessor="format_mes_compte_depots")

    #img = tables.Column(verbose_name='Photo', accessor=A('get_thumbnail_url'))
    signature = tables.Column(verbose_name='Signature', accessor=A('render_signature'))
    #poste = tables.Column(verbose_name="Poste", accessor='poste__name')

    class Meta(DefaultTable.Meta):
        model = GerantCD
        order_by="-created"
        fields = ("matricule","phone","firstname", "lastname","comptes","roles","action","created","status","signature","justificatif","teaser_signature")

    def render_matricule(self, value):
        url = reverse('cddaccount:simple_gerantcd_profile', kwargs={'matricule': value})
        str = """
           <a href = "{}"  >
             <span >{}</span>
           </a>
           """.format(url,value, )
        return format_html(str)


    def render_justificatif(self, value):
        url = "/media/{}".format(value)
        return format_html('<a href= {}>  <i class="fa fa-file"></i> </a>'.format(url, ))

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_is_actif(self, value):
        if value:
            _str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)



    def render_img(self,value):
        img_path=""
        s="<p>--</p>"
        if value:
            s=f"""
            <div class="d-block flex-shrink-0">
                                             <a href= "{value}">   <img src="{value}" class="img-fluid img-thumbnail" alt=""></a>
                                            </div>
            """
        return format_html(s)

    def render___signature(self,value):
        img_path=""
        s="<p>--</p>"
        if value:
            s=f"""
            <div class="d-block flex-shrink-0">
                                                <a href= "{value}"><img src="{value}" class="img-fluid img-thumbnail" alt=""></a>
                                            </div>
            """
        return format_html(s)


class AgentSaisieCDFilter(FilterSet):
    #date = StackDateFromToRangeFilter()
    is_actif = TypedChoiceFilter(choices=choices, coerce=strtobool, label="Est actif")


    class Meta:
        model = AgentSaisieCD
        fields = ['phone', "lastname","firstname","is_actif"]



class AgentSaisieCDTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor=A("actions"))
    comptes = tables.Column(verbose_name='Comptes', accessor=A("format_comptes"))

    class Meta(DefaultTable.Meta):
        model = AgentSaisieCD
        order_by="-created"
        fields = ("matricule","phone","firstname", "lastname","comptes","created","status", "action","is_actif")


    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_is_actif(self, value):
        if value:
            _str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)




class GestionCompteDepotFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter()

    #date = StackDateFromToRangeFilter()
    compte__short_compte = CharFilter(lookup_expr='icontains', label="compte de dépôt")
    compte__libelle_court = CharFilter(lookup_expr='icontains', label="Libellé")

    compte__actif = TypedChoiceFilter(choices=choices, coerce=strtobool, label="Est actif")
    compte__valide = TypedChoiceFilter(choices=choices, coerce=strtobool, label="Est validé")

    class Meta:
        model = GestionCompteDepot
        fields = ['compte__libelle_court', "compte__short_compte","compte__actif","compte__valide"]




class GestionCompteDepotTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")
    firstname = tables.Column(verbose_name="Prénom",accessor='gerant__firstname')
    lastname = tables.Column(verbose_name="Nom",accessor='gerant__lastname')
    compte = tables.Column(verbose_name="Compte",accessor='compte__short_compte')
    matricule = tables.Column(accessor='gerant__matricule',verbose_name="Matricule")
    period =tables.Column(accessor=A('format_period'), verbose_name="Période")
    signature = tables.Column(verbose_name='Signature', accessor=A('gerant.render_signature'))

    class Meta(DefaultTable.Meta):
        model = GestionCompteDepot

        order_by="-created"
        fields = ["firstname", "lastname","matricule","signature","compte","action","actif","created","period"]

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
        delete_url = reverse('cddaccount:delete_gestioncomptedepot', kwargs={'pk': value})
        update_url = reverse('cddaccount:update_gestioncomptedepot', kwargs={'pk': value})
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





def filtrecomptes(request):
    if request is None:
        return CompteDepot.objects.none()
    return CompteDepot.objects.by_agent(request.user)

from django import forms

class OrdrePaymentFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter(label="Date création")
    sig_reference = CharFilter(lookup_expr='icontains', label="Référence")
    compte = ModelChoiceFilter(queryset=filtrecomptes, empty_label=_("Selectionner Compte Depot"),
                               widget=forms.Select(attrs={'id': 'idcompte'}))

    typecompte = ModelChoiceFilter(queryset=TypeCompteTrx.objects.filter(actif=True), empty_label=_("Selectionner type solde"))

    #date = StackDateFromToRangeFilter()

    class Meta:
        model = OrdrePayment
        fields = [ "compte","typecompte","object","amount","payment_mean","open_date","created","gestion"]




class OrdrePaymentTable(DefaultTable):
    selection = tables.CheckBoxColumn(accessor='pk', attrs={"th__input": {"id": "selectAll"}})
    action = tables.Column(verbose_name='Actions autorisées', accessor=A("get_instance"), orderable=True)
    #crud =tables.Column(verbose_name='Modifier', accessor=A("get_instance"))
    gerant = tables.Column(verbose_name="Gérant",accessor=A('gerant.full_name'))
    agent = tables.Column(verbose_name="Agent de saisie", accessor=A('creator.full_name'))
    compte = tables.Column(verbose_name="Compte de dépôt",accessor='compte__short_compte')
    libelle_court = tables.Column(verbose_name="Libellé court", accessor='compte__libelle_court')
    matricule = tables.Column(accessor='gerant__username',verbose_name="Matricule Gérant")
    jour_comptable=tables.Column(accessor='jour_comptable.day',verbose_name="Journée Comptable")
    template = tables.Column(accessor='get_reference_template', verbose_name="Editer OV")

    templateop = tables.Column(accessor='get_reference_templateop', verbose_name="Editer Demannde OP")

    blocage = tables.Column(verbose_name="Projet", accessor='blocage__id')
    #reference=tables.Column(verbose_name="Reference(OV/CH)")
    reference=tables.Column(verbose_name="Référence",accessor='render_sig_reference')
    reliquat= tables.Column(verbose_name="Reste à payer",accessor='get_reliquat')
    amount=tables.Column(verbose_name="Montant",attrs={"td": {"align": "right"}})
    created = tables.Column(verbose_name="Date de saisie")
    typesolde = tables.Column(verbose_name="Type Solde", accessor='typecompte__name')

    #date_reception = tables.Column(verbose_name="Date de réception")
    #date_prise_en_charge = tables.Column(verbose_name="Date de saisie")
    #date_visa = tables.Column(verbose_name="Date de saisie")



    class Meta(DefaultTable.Meta):
        model = OrdrePayment
        #template_name = 'datatables/template_htmx.html'
        order_by="-id"
        fields = ["selection","reference","compte","libelle_court","object","amount","reliquat","etape","blocage","reglement","template","templateop","status","payment_mean","agent","gerant","matricule","jour_comptable","nature","secteur","created","date_reception","date_prise_en_charge","date_visa","typesolde"]

    def render_date_prise_en_charge(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

    def render_date_reception(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"



    def render_amount(self, value):
        v=intcomma(int(value.amount))
        return format_html("{}".format(v)) if value else 0

    def render_reliquat(self, value):
        v=intcomma(int(value.amount))
        return format_html("{}".format(v)) if value else 0


    def render_blocage(self, value):
        str="--"
        if value:
            details_url = reverse('cddaccount:details_blocagefond', kwargs={'pk': value})
            str = """<a   href="{}"><span >{} </span></a>""".format(details_url, value)
        return format_html(str)

    def render_date_visa(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

    def render_created(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

    def render_actif(self, value):
        if value:
            _str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)



class ASCDOrdrePaymentTable(OrdrePaymentTable):

    class Meta(OrdrePaymentTable.Meta):
        order_by="-created"
        #template_name = 'datatables/template_htmx.html'
        fields = ["selection","cheque","reference","object","blocage","beneficiaire","payment_mean","amount","status","action","created","date_reception","date_prise_en_charge","date_visa","etape","template","jour_comptable","reglement","gerant","compte","nature","secteur","observations","typesolde"]

    def render_created(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

    def render_date_visa(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

    def render_action(self, value):
        user=self.request.user

        visa_url = "#"  # reverse('cddaccount:validate_gerantcd_data', kwargs={'reference': self.reference})
        prise_en_charge_url = reverse('cddaccount:prise_en_charge_view', kwargs={'pk': value.pk})
        if hasattr(value, "annulation_op"):
            str = """OP ANNULLE """
        elif hasattr(value, "prise_en_charge"):
            if hasattr(value.prise_en_charge, "visa"):
                str = """VISA OK """
            else:
                str = """ATTENTE VISA"""
        else:
            str=""
            if value.etape==ETAPE_ORDRE_PAYMENT.SAISIE:
                delete_url = reverse('cddaccount:delete_ordrepayment', kwargs={'pk': value.pk})
                update_url = reverse('cddaccount:update_ordrepayment', kwargs={'pk': value.pk})

                str += """<div class="form-group">"""

                if user.has_perm('cddaccount.change_ordrepayment'):
                    str += """<button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
                                          <span class="fa fa-pencil"></span>
                                        </button>""".format(update_url,)

                if user.has_perm('cddaccount.delete_ordrepayment'):
                    str +="""<button type="button" class="delete-item btn btn-sm btn-danger btn-block" data-form-url="{}">
                                      <span class="fa fa-trash"></span>
                                    </button>
                                    """.format(delete_url, )
                str+="</div>"
            elif value.etape == ETAPE_ORDRE_PAYMENT.VALIDE:
                str = """ATTENTE ACCEPTATION"""
            elif value.etape == ETAPE_ORDRE_PAYMENT.ACCEPTE:
                str = """ATTENTE PRISE EN CHARGE"""


        return format_html(str)




class GerantCDOrdrePaymentTable(OrdrePaymentTable):

    class Meta(OrdrePaymentTable.Meta):
        order_by="-created"
        #template_name = 'datatables/template_htmx.html'
        fields = ["selection","action","reference","object","beneficiaire","amount","status","etape","blocage","payment_mean","compte","nature","created","date_reception","date_prise_en_charge","date_visa","template","templateop","reglement","jour_comptable","secteur","observations","typesolde"]

    def render_created(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

    def render_date_visa(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"


    def render_action(self, value):
        user=self.request.user

        visa_url = "#"  # reverse('cddaccount:validate_gerantcd_data', kwargs={'reference': self.reference})
        prise_en_charge_url = reverse('cddaccount:prise_en_charge_view', kwargs={'pk': value.pk})
        #valider_ordrepayment
        if hasattr(value, "annulation_op"):
            str = """OP ANNULLE """
        elif hasattr(value, "prise_en_charge"):
            if hasattr(value.prise_en_charge, "visa"):
                str = """VISA OK """
            else:
                str = """ATTENTE VISA"""
        else:
            str=""
            if value.etape==ETAPE_ORDRE_PAYMENT.SAISIE:
                delete_url = reverse('cddaccount:delete_ordrepayment', kwargs={'pk': value.pk})
                update_url = reverse('cddaccount:update_ordrepayment', kwargs={'pk': value.pk})

                validate_url = reverse('cddaccount:validate_ordre_payment', kwargs={'reference': value.reference})

                str += """<div class="form-group">"""

                if user.has_perm('cddaccount.valider_ordrepayment'):
                    str +="""<button type="button" title="Envoyer" class="valider-item btn btn-sm btn-success " data-form-url="{} ">
                                      <i class="fa fa-paper-plane" aria-hidden="true"></i>
                                    </button>
                                    """.format(validate_url, )
                    
                if user.has_perm('cddaccount.change_ordrepayment'):
                    str += """<button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}" >
                                          <span class="fa fa-pencil"></span>
                                        </button>""".format(update_url,)

                if user.has_perm('cddaccount.delete_ordrepayment'):
                    str +="""&nbsp;<button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}" >
                                      <span class="fa fa-trash"></span>
                                    </button>
                                    """.format(delete_url, )

                str+="</div>"
            elif value.etape == ETAPE_ORDRE_PAYMENT.VALIDE:
                str = """ATTENTE ACCEPTATION"""
            elif value.etape == ETAPE_ORDRE_PAYMENT.ACCEPTE:
                str = """ATTENTE PRISE EN CHARGE"""



        return format_html(str)



class AgentPCOrdrePaymentTable(OrdrePaymentTable):

    class Meta(OrdrePaymentTable.Meta):
        order_by="-created"
        #template_name = 'datatables/template_htmx.html'

        fields = ["selection","action","reference","object","compte","libelle_court","beneficiaire","amount","reliquat","payment_mean","status","template","created","date_reception","date_prise_en_charge","date_visa","blocage","etape","reglement","jour_comptable","nature","secteur","observations","typesolde"]

    def render_created(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

    def render_date_visa(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"
    def render_action(self, value):
        user=self.request.user
        #valider_ordrepayment
        str = ""
        if hasattr(value, "annulation_op"):
            str = """OP ANNULLE """
        elif hasattr(value, "prise_en_charge"):
            if hasattr(value.prise_en_charge, "visa"):
                str = """VISA OK"""
                if user.has_perm('bankcheck.receptionner_cheque') and value.prise_en_charge.visa.reglement == TYPE_REGLEMENT.GLOBAL and value.prise_en_charge.visa.payment_mean==PAYMENT_MEAN_TYPE.CHEQUE and not value.cheque_delivred:
                    str = """<div class="form-group">"""
                    prise_en_charge = reverse('cddaccount:send_otp_to_receptionnaire_new',
                                              kwargs={'reference': value.reference})


                    str += """<a title="Rejeter chèque" class="accepter-item btn btn-sm btn-block btn-success" href="{}"><span ><i class="fa fa-caret-square-o-up" aria-hidden="true"></i></span></a>""".format( prise_en_charge, )




                str += """</div>"""

            else:
                if value.etape == ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE:
                    str = """<div class="form-group form-inline">"""

                    if hasattr(value, "reservationfond") and not value.reservationfond.close:
                        if user.has_perm('cddaccount.maketrx_ordrepayment'):
                                visa_url = reverse('cddaccount:maketrx_ordre_payement', kwargs={'reference': value.reference})

                                params = {'success_url': self.request.build_absolute_uri()}
                                visa_url=visa_url+"?" + urlencode(params)

                                str += """<button title="Viser" class="payer-ordre-item btn btn-sm btn-success" data-form-url="{}"><i class="fa fa-check-square"></i></button>""".format(visa_url, )

                    if hasattr(value, "reservationfond"):# and not value.reservationfond.has_trx:

                        if user.has_perm('cddaccount.annulation_ordrepayment'):
                            prise_en_charge = reverse('cddaccount:reject_op', kwargs={'reference': value.reference})
                            str += """&nbsp;<button type="button" title="Annuler PEC" class="delete_priseencharge-item btn btn-sm btn-danger
                            " data-form-url="{}"><i class="fa fa-times" aria-hidden="true"></i></button>""".format(
                                prise_en_charge, )
                            
                        if user.has_perm('cddaccount.change_prisenchageordrepayment'):
                            prise_en_charge = reverse('cddaccount:update_priseencharge', kwargs={'pk': value.prise_en_charge.id})
                            str += """&nbsp;<button type="button" title="Modifier" class="change_priseencharge-item btn btn-sm btn-warning" data-form-url="{}"><span class="fa fa-pencil"></span></button>""".format(
                                prise_en_charge, )
                        #
                        # if user.has_perm('cddaccount.annulation_ordrepayment'):
                        #     prise_en_charge = reverse('cddaccount:annulation_op', kwargs={'reference': value.reference})
                        #     str += """<br><button type="button" class="delete_priseencharge-item btn btn-sm btn-danger
                        #      btn-block" data-form-url="{}"><span >Annuler </span></button>""".format(
                        #         prise_en_charge, )

                    
                    str += "</div>"

        else:
            str=""
            if value.etape==ETAPE_ORDRE_PAYMENT.VALIDE:
                delete_url = reverse('cddaccount:delete_ordrepayment', kwargs={'pk': value.pk})
                update_url = reverse('cddaccount:update_ordrepayment', kwargs={'pk': value.pk})

                validate_url = reverse('cddaccount:accepter_ordre_payment', kwargs={'reference': value.reference})

                str += """<div class="form-group form-inline">"""

                if user.has_perm('cddaccount.accepter_ordrepayment'):
                    str += """<a  title="Réceptionner" class="accepter-item btn btn-sm btn-success" href="{}">
                                                                                                      <i class="fa fa-cart-plus" aria-hidden="true"></i>
                                                                                                                        </a>""".format(
                        validate_url, )

                if value.creator==user:
                    if user.has_perm('cddaccount.change_ordrepayment'):
                        str += """&nbsp;<button type="button" title="Modifier" class="update-item btn btn-sm btn-warning" data-form-url="{}">
                                          <span class="fa fa-pencil"></span>
                                        </button>""".format(update_url,)
                        
                    if user.has_perm('cddaccount.delete_ordrepayment'):
                         v_url= reverse('cddaccount:delete_pc_opwith_validate_status', kwargs={'pk': value.pk})
                         str +="""&nbsp;<button type="button" title="Supprimer" class="op_pc_delete-item btn btn-sm btn-danger" data-form-url="{}" >
                                           <span class="fa fa-trash"></span>
                                         </button>
                                         """.format(v_url, )

                str+="</div>"
            elif value.etape==ETAPE_ORDRE_PAYMENT.ACCEPTE:
                prise_en_charge_url = reverse('cddaccount:prise_en_charge_view', kwargs={'pk': value.pk})

                mij_accepted_op_paymentmean_url = reverse('cddaccount:update_pm_ordrepayment', kwargs={'pk': value.pk})

                str += """<div class="form-group">"""

                if user.has_perm('cddaccount.priseencharge_ordrepayment'):

                    str += """<a title="PEC" class="priseencharge-item btn btn-sm btn-success" href="{}">
                                                                                                     <i class="fa fa-shopping-bag" aria-hidden="true"></i>
                                                                                                    </a>""".format(
                        prise_en_charge_url, )

                    str += """&nbsp;<button type="button" title="Modifier" class="mij-paymentmean-item btn btn-sm btn-warning" data-form-url="{}" >
                                                          <span class="fa fa-pencil"></span>
                                                       </button>
                                                       """.format(mij_accepted_op_paymentmean_url, )





                else: str = """ATTENTE PRISE EN CHARGE"""


                str += "</div>"
        return format_html(str)




class TransactionOPTable(DefaultTable):
    account_depot = tables.Column(verbose_name='COMPTE DEPOT' )
    account_secondaire = tables.Column(verbose_name='SECOND COMPTE')


    created = tables.Column(verbose_name='DATE', )
    libelle = tables.Column(verbose_name='LIBELLE', )


    cheque = tables.Column(verbose_name='CHÈQUE')

    amount= tables.Column(verbose_name='MONTANT')

    class Meta(DefaultTable.Meta):
        model = TransactionOP
        order_by="-created"
        fields = ["reference","amount","account_depot","cheque","sens","created","libelle"]

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_reference(self, value):
        details_url = reverse('cddaccount:recu_payement', kwargs={'reference': value})
        str = """<a   href="{}"><span >{} </span></a>""".format(details_url, value)
        return format_html(str)
    def render_amount(self, value):
        v=intcomma(int(value.amount))
        return format_html("{}".format(v)) if value else 0




class DepositaireFilter(FilterSet):

    class Meta:
        model = Depositaire
        fields = ['phone', "lastname", "firstname"]


class DepositaireTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor=A("actions"))
    comptes=tables.Column(verbose_name='Comptes', accessor=A("format_comptes"))
    signature = tables.Column(verbose_name='Signature', accessor=A('get_thumbnail_signature_url'))


    class Meta(DefaultTable.Meta):
        model = Depositaire
        order_by = "-created"
        fields = ("phone","nin", "firstname", "lastname", "action","comptes","signature", "created", "status",)


    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"


    def render_is_actif(self, value):
        if value:
            _str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)


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



class NatureFilter(FilterSet):

    class Meta:
        model = Nature
        fields = ["name"]


class NatureTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")

    class Meta(DefaultTable.Meta):
        model = Nature
        order_by = ("-id")
        fields = ("id","name","action","created")
    def render_action(self, value):
        delete_url = reverse('cddaccount:delete_nature', kwargs={'pk': value})
        update_url = reverse('cddaccount:update_nature', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)



class ProjetFilter(FilterSet):

    class Meta:
        model = Projet
        fields = ["name"]


class ProjetTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor=A("get_instance"))
    period = tables.Column(accessor=A('format_period'),verbose_name="Période")
    compte = tables.Column(verbose_name="Compte de dépôt", accessor='compte__short_compte')


    class Meta(DefaultTable.Meta):
        model = Projet
        order_by = ("-pk")
        fields = ("ref_marche","name","amount","status","compte","period","action","observations","created")

    def render_id(self, value):
        details_url = reverse('cddaccount:details_projet_bf', kwargs={'pk': value})
        str = """<a   href="{}"><span >{} </span></a>""".format(details_url, value)
        return format_html(str)
    def render_amount(self, value):
        v=intcomma(int(value.amount))
        return format_html("{}".format(v)) if value else 0

    def render_action(self, value):
        user=self.request.user
        if hasattr(value, "blocagefond"):
            str = """FOND BLOQUE"""
        else:
            str = """<div class="form-group">"""
            if value.demande_blocage:
                if user.has_perm('cddaccount.validerbf_project'):
                    prise_en_charge = reverse('cddaccount:valider_projet_bf', kwargs={'pk': value.id})
                    str += """<br><a type="button" class="valider-bf-item btn btn-sm btn-purple btn-block" href="{}"><span >Bloquer Fond </span></a>""".format(
                        prise_en_charge, )
                else : str += """ATTENTE BLOCAGE FOND"""
            else:
                delete_url = reverse('cddaccount:delete_projet', kwargs={'pk': value.pk})
                update_url = reverse('cddaccount:update_projet', kwargs={'pk': value.pk})

                if user.has_perm('cddaccount.delete_projet'):
                    str +="""<button type="button" class="delete-item btn btn-sm btn-danger btn-block" data-form-url="{}" >
                                      <span class="fa fa-trash">Supprimer</span>
                                    </button>
                                    """.format(delete_url, )
                if user.has_perm('cddaccount.change_projet'):
                    str +="""<button type="button" class="update-item btn btn-sm btn-primary btn-block" data-form-url="{}" >
                                          <span class="fa fa-pencil">Modifier</span>
                                        </button>""".format(update_url, )


                if user.has_perm('cddaccount.demanderbf_project'):
                    prise_en_charge = reverse('cddaccount:demander_bf_projet', kwargs={'pk': value.id})
                    str += """<br><button type="button" class="demander-bf-item btn btn-sm btn-purple btn-block" data-form-url="{}"><span >Demander Blocage Fond </span></button>""".format(
                        prise_en_charge, )
                else : str += """ATTENTE DEMANDE BLOCAGE FOND """

            str += "</div>"


        return format_html(str)






class AvisDeCreditFilter(FilterSet):
    jour_comptable__annee_comptable=ModelChoiceFilter(queryset=AnneeComptable.objects.all() ,label="Gestion")
    typecompte = ModelChoiceFilter(queryset=TypeCompteTrx.objects.filter(actif=True),
                                   empty_label=_("Selectionner type solde"))

    class Meta:
        model = AvisDeCredit
        fields = ["libelle","compte","date_avis","jour_comptable__annee_comptable","typecompte"]


class AvisDeDebitFilter(FilterSet):
    jour_comptable__annee_comptable = ModelChoiceFilter(queryset=AnneeComptable.objects.all(), label="Gestion")
    typecompte = ModelChoiceFilter(queryset=TypeCompteTrx.objects.filter(actif=True),
                                   empty_label=_("Selectionner type solde"))
    class Meta:
        model = AvisDeDebit
        fields = ["libelle","compte","date_avis","jour_comptable__annee_comptable","typecompte"]

class AvisDeCreditTable(DefaultTable):
    jour_comptable = tables.Column(accessor='jour_comptable.day', verbose_name="Journée Comptable")
    compte = tables.Column(verbose_name='Numéro compte', accessor="compte__short_compte")
    libelle_court = tables.Column(verbose_name='Libellé compte', accessor="compte__libelle_court")
    created = tables.Column(verbose_name='Date', )
    libelle = tables.Column(verbose_name='Libellé avis', )
    amount = tables.Column(verbose_name='Montant',
                           footer=lambda table: sum(x.amount for x in table.data if x.amount is not None))
    typesolde = tables.Column(verbose_name="Type Solde", accessor='typecompte__name')

    class Meta(DefaultTable.Meta):
        model = AvisDeCredit
        order_by="-created"
        fields = ["reference","amount","compte","typesolde","libelle_court","date_avis","created","libelle","jour_comptable"]

    def render_created(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

    def render_date_avis(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

    def render_amount(self, value):
        v=intcomma(int(value.amount))
        return format_html("{}".format(v)) if value else 0



    def render_reference(self, value):
        details_url = reverse('cddaccount:template_aviscredit', kwargs={'reference': value})
        str = """<a   href="{}" target="_blank"><span >{} </span></a>""".format(details_url, value)
        return format_html(str)



class AvisDeDebitTable(DefaultTable):
    jour_comptable = tables.Column(accessor='jour_comptable.day', verbose_name="Journée comptable")
    compte=tables.Column(verbose_name='Numéro compte',accessor="compte__short_compte")
    libelle_court = tables.Column(verbose_name='Libellé compte', accessor="compte__libelle_court")
    created = tables.Column(verbose_name='Date', )
    libelle = tables.Column(verbose_name='Libellé avis', )
    amount = tables.Column(verbose_name='Montant',
                           footer=lambda table: sum(x.amount for x in table.data if x.amount is not None))
    typesolde = tables.Column(verbose_name="Type Solde", accessor='typecompte__name')

    class Meta(DefaultTable.Meta):
        model = AvisDeDebit
        order_by="-created"
        fields = ["reference","amount","compte","typesolde","libelle_court","date_avis","created","libelle","jour_comptable"]

    def render_created(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

    def render_date_avis(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"



    def render_reference(self, value):
        details_url = reverse('cddaccount:template_avisdebit_pdf', kwargs={'reference': value})
        str = """<a   href="{}" target="_blank"><span >{} </span></a>""".format(details_url, value)
        return format_html(str)

    def render_amount(self, value):
        v=intcomma(int(value.amount))
        return format_html("{}".format(v)) if value else 0


class AnneeComptableFilter(FilterSet):

    class Meta:
        model = AnneeComptable
        fields = ["name","actif"]


class AnneeComptableTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")
    period = tables.Column(accessor=A('format_period'))

    class Meta(DefaultTable.Meta):
        model = AnneeComptable
        order_by = ("-created")
        fields = ("period","name","action","actif","created")
    def render_action(self, value):
        delete_url = reverse('cddaccount:delete_anneecomptable', kwargs={'pk': value})
        update_url = reverse('cddaccount:update_anneecomptable', kwargs={'pk': value})
        bascule_url = reverse('cddaccount:bascule_anneecomptable', kwargs={'id': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        
        <button type="button" class="bascule-item btn btn-sm btn-success" data-form-url="{}">
          <span class="fa fa-check"></span>
        </button>
        """.format(update_url, delete_url,bascule_url)
        return format_html(str)




class BlocageFondFilter(FilterSet):

    class Meta:
        model = BlocageFond
        fields = ["close","reference","ref_marche"]


class BlocageFondTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")
    compte = tables.Column(verbose_name="Compte de dépôt", accessor='compte__short_compte')

    #action = tables.Column(verbose_name='Actions', accessor="id")

    reference = tables.Column(verbose_name='Attestation')
    new_op= tables.Column(verbose_name='Actions', accessor="get_instance")




    class Meta(DefaultTable.Meta):
        model = BlocageFond
        order_by = ("-pk")
        fields = ("reference","ref_marche","amount","balance","new_op","prestataire","ninea","compte_iban","compte","open_date","end_date","close","created")
    def render_action(self, value):
        delete_url = reverse('cddaccount:delete_blocagefond', kwargs={'pk': value})
        update_url = reverse('cddaccount:update_blocagefond', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)

    def render_amount(self, value):
        v=intcomma(int(value.amount))
        return format_html("{}".format(v)) if value else 0


    def render_id(self, value):
        details_url = reverse('cddaccount:details_blocagefond', kwargs={'pk': value})
        str = """<a   href="{}"><span >{} </span></a>""".format(details_url, value)
        return format_html(str)

    def render_reference(self, value):
        details_url = reverse('cddaccount:temlate_bf', kwargs={'reference': value})
        str = """<a   href="{}"><span >{} </span></a>""".format(details_url, value)
        return format_html(str)

    def render_new_op(self, value):
        user = self.request.user
        str=""
        if hasattr(value,"annulationblocagefond"):
            if value.annulationblocagefond.approuver:
                str="FONDS ANNULES"
            else:
                str = "ANNULATION FONDS EN COURS"
        else:

            str = """<div class="form-group">"""

            if user.has_perm('cddaccount.change_bocagefond'):
                update_url = reverse('cddaccount:update_bocagefond', kwargs={'pk': value.id})
                str += """
                                <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
                                  <span class="fa fa-pencil"></span>
                                </button>
                                """.format(update_url, )

            if user.has_perm('cddaccount.delete_bocagefond'):
                delete_url = reverse('cddaccount:delete_bocagefond', kwargs={'pk': value.id})
                str += """
                                <button type="button" class="delete-item btn btn-sm btn-danger btn-block" data-form-url="{}">
                                  <span class="fa fa-trash"> </span>
                                </button>
                                """.format(delete_url, )



            if user.has_perm('cddaccount.add_ordrepayment'):
                update_url = reverse('cddaccount:create_op_blocagefond', kwargs={'reference': value.reference})
                str += """
                <button type="button" class="new-op-item btn btn-sm btn-primary btn-block" data-form-url="{}">
                  <span class="fa fa-pencil"> Nouveau ordre Paiement</span>
                </button>
                """.format(update_url, )
            if user.has_perm('cddaccount.demanderbf_project'):
                update_url = reverse('cddaccount:deblocage_fond_view', kwargs={'reference': value.reference})
                str += """
                        <button type="button" class="annuler-fd-item btn btn-sm btn-danger btn-block" data-form-url="{}">Annuler blocage fond</span>
                        </button>
                        """.format(update_url, )
            str+="</div>"
        return format_html(str)




    def render_annuler_bf(self, value):
        update_url = reverse('cddaccount:deblocage_fond_view', kwargs={'reference': value})
        str = """
        <button type="button" class="annuler-fd-item btn btn-sm btn-danger" data-form-url="{}">Annuler blocage fond</span>
        </button>
        """.format(update_url, )
        return format_html(str)


class AnnulationBlocageFondFilter(FilterSet):
    class Meta:
        model = AnnulationBlocageFond
        fields = ["reference"]


class AnnulationBlocageFondTable(DefaultTable):
    compte = tables.Column(verbose_name="Compte de dépôt", accessor='compte__short_compte')
    new_op = tables.Column(verbose_name='--', accessor="get_instance")



    class Meta(DefaultTable.Meta):
        model = AnnulationBlocageFond
        order_by = ("-created")
        fields = ( "reference", "amount","new_op", "compte", "demandeur", "approbateur", "approuver", "description", "approbation_date", "created")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_approbation_date(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

    def render_amount(self, value):
        v=intcomma(int(value.amount))
        return format_html("{}".format(v)) if value else 0


    def render_new_op(self, value):
        user = self.request.user

        if value.approuver:
            str="FONDS ANNULES"
        else:
            str = "ANNULATION FONDS EN COURS"

            if user.has_perm('cddaccount.approuver_annulationblocagefond'):
                str = """<div class="form-group">"""
                update_url = reverse('cddaccount:approuver_deblocage_fond', kwargs={'reference': value.reference})
                str += """
                            <button type="button" class="valider-annulation-item btn btn-sm btn-danger btn-block" data-form-url="{}">
                              <span class="fa fa-pencil"> Approuver annulation</span>
                            </button>
                            """.format(update_url, )

                str += "</div>"

        return format_html(str)


#list_display = ("id","compte","taux_fonc","taux_invest","amount_fonc","amount_fonc","gestion","anne_comptable")


class ReportGestionFilter(FilterSet):
    class Meta:
        model = ReportGestion
        fields = ["compte__short_compte","typecompte","gestion_courant","sens"]



class ReportGestionTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")
    jour_comptable = tables.Column(accessor='anne_comptable.year', verbose_name="Gestion")
    compte = tables.Column(verbose_name='Compte de dépôt', accessor="compte__short_compte")

    class Meta(DefaultTable.Meta):
        model = ReportGestion
        order_by="-created"
        fields = ["id","compte","jour_comptable","typecompte","amount","sens","action","created"]



    def render_amount(self, value):
        v=intcomma(int(value.amount))
        return format_html("{}".format(v)) if value else 0

    def render_created(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"
    def render_action(self, value):
        delete_url = reverse('cddaccount:delete_reportgestion', kwargs={'pk': value})
        update_url = reverse('cddaccount:update_reportgestion', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)

class ReportFilter(FilterSet):
    class Meta:
        model = Report
        fields = ["compte__short_compte","gestion_courant"]
class ReportTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")
    jour_comptable = tables.Column(accessor='anne_comptable.year', verbose_name="Gestion")
    compte = tables.Column(verbose_name='Compte de dépôt', accessor="compte__short_compte")

    class Meta(DefaultTable.Meta):
        model = Report
        order_by="-created"
        fields = ["id","jour_comptable","amount_fonc","amount_invest","action","created"]

    def render_amount_fonc(self, value):
        v=intcomma(int(value.amount))
        return format_html("{}".format(v)) if value else 0

    def render_amount_invest(self, value):
        v=intcomma(int(value.amount))
        return format_html("{}".format(v)) if value else 0

    def render_created(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"
    def render_action(self, value):
        delete_url = reverse('cddaccount:delete_report', kwargs={'pk': value})
        update_url = reverse('cddaccount:update_report', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)



class OperationViseFilter(FilterSet):
    jour_comptable__annee_comptable = ModelChoiceFilter(queryset=AnneeComptable.objects.all(), label="Gestion")
    origin_reference=CharFilter(lookup_expr='icontains',label="Numéro OP")
    reference = CharFilter(lookup_expr='icontains', label="reference")
    reservation__ordre__compte = ModelChoiceFilter(queryset=filtrecomptes, empty_label=_("Selectionner Compte Depot"),
                               widget=forms.Select(attrs={'id': 'idcompte'}))

    typecompte = ModelChoiceFilter(queryset=TypeCompteTrx.objects.filter(actif=True), empty_label=_("Selectionner Type solde"),label="Type Solde")
    class Meta:
        model = TransactionOP
        fields = ["reservation__ordre__compte","amount","payment_mean","created","reference","origin_reference","typecompte"]

class OperationViseTable(DefaultTable):
    account_depot = tables.Column(verbose_name='Compte de dépôt' )
    account_secondaire = tables.Column(verbose_name='Destination')
    origin_reference=tables.Column(verbose_name='Numéro OP')
    action = tables.Column(verbose_name='Action', accessor="get_instance")


    created = tables.Column(verbose_name='Date', )
    libelle = tables.Column(verbose_name='Libellé', )


    cheque = tables.Column(verbose_name='Chèque')

    amount = tables.Column(verbose_name='Montant')
    typesolde = tables.Column(verbose_name="Type Solde", accessor='typecompte__name')

    class Meta(DefaultTable.Meta):
        model = TransactionOP
        template_name = 'datatables/templateB4.html'
        order_by="-created"
        fields = ["origin_reference","reference","amount","account_depot","poste_comptable","payment_mean","action","status_aster","etape_compense","created","libelle","typesolde"]

    def render_created(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

    def render_amount(self, value):
        v=intcomma(int(value.amount))
        return format_html("{}".format(v)) if value else 0

    def render_origin_reference(self, value):
        details_url = reverse('cddaccount:detail_ordre_payement', kwargs={'reference': value})
        str = """<a   href="{}"><span >{} </span></a>""".format(details_url, value)
        return format_html(str)

    def render_action(self, value):
        user = self.request.user
        str=""

        if user.has_perm('cddaccount.delete_visaordrepayment'):
            if value.has_cancel:str="Déjà annulé"
            else:
                str += """<div class="form-group">"""
                annuler_visa_url = reverse('cddaccount:annuler_visa_view',kwargs={'pk': value.id})
                str += """<br><button type="button" title="Annuler" class="annuler-visa-item btn btn-sm btn-danger" data-form-url="{}"><i class="fa fa-times" aria-hidden="true"></i></button>""".format(
                    annuler_visa_url, )
                str += """</div>"""
        return format_html(str)






class VirementDetailsFilter(FilterSet):


    class Meta:
        model = VirementDetails
        fields = [ "virement__sig_reference","beneficiaire", "iban_benef", "amount","status_aster", "created"]



class VirementDetailsTable(DefaultTable):
    virement = tables.Column(verbose_name="Virement",accessor=A('virement.sig_reference'))
    pk = tables.Column(verbose_name="Identifiant")

    class Meta(DefaultTable.Meta):
        model = VirementDetails
        template_name = 'datatables/templateB4.html'
        order_by="-created"
        fields = ["pk",'virement','beneficiaire','iban_benef','reference',"reference_aster",'amount',"created","status_aster","etape_compense","trx","wallet_provider","wallet_number","cin","dob","lieu_dob","firstname","lastname"]

    def render_created(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

    def render_amount(self, value):
        v=intcomma(int(value.amount))
        return format_html("{}".format(v)) if value else 0


    def render_date_visa(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

    def render_created(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

class SousNatureFilter(FilterSet):

    class Meta:
        model = SousNature
        fields = ["nature","name"]


class SousNatureTable(DefaultTable):
    Nature = tables.Column(verbose_name="Nature", accessor=A('nature.name'))
    action = tables.Column(verbose_name='Actions', accessor="id")

    class Meta(DefaultTable.Meta):
        model = SousNature
        order_by = ("-id")
        fields = ("id","name","nature","action","created")
    def render_action(self, value):
        delete_url = reverse('cddaccount:delete_sousnature', kwargs={'pk': value})
        update_url = reverse('cddaccount:update_sousnature', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)


class MandataireFilter(FilterSet):

    class Meta:
        model = Mandataire
        fields = ['phone', "lastname", "firstname"]


class MandataireTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor=A("actions"))
    # comptes=tables.Column(verbose_name='Comptes', accessor=A("format_comptes"))
    # signature = tables.Column(verbose_name='Signature', accessor=A('get_thumbnail_signature_url'))


    class Meta(DefaultTable.Meta):
        model = Mandataire
        order_by = "-created"
        # fields = ("phone","nin", "firstname", "lastname", "action","comptes","signature", "created", "status",)
        fields = ("phone", "nin", "firstname", "lastname", "action", "created", "status",)


    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"


    def render_is_actif(self, value):
        if value:
            _str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)





class TypeCompteTrxTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor=A("id"))
    # comptes=tables.Column(verbose_name='Comptes', accessor=A("format_comptes"))
    # signature = tables.Column(verbose_name='Signature', accessor=A('get_thumbnail_signature_url'))


    class Meta(DefaultTable.Meta):
        model = TypeCompteTrx
        # fields = ("phone","nin", "firstname", "lastname", "action","comptes","signature", "created", "status",)
        fields = ("id","code", "name","action", "nature","actif")


    def render_action(self, value):
        delete_url = reverse('cddaccount:delete_typecomptetrx', kwargs={'pk': value})
        update_url = reverse('cddaccount:update_typecomptetrx', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)



    def render_is_actif(self, value):
        if value:
            _str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)


class CompteTrxFilter(FilterSet):
    class Meta:
        model = CompteTrx
        fields = ["compte__short_compte","type","gestion","reportable"]



        #"id","type","taux","reportable","compte","balance","report","date_basculement","gestion"



class CompteTrxTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor=A("id"))
    # comptes=tables.Column(verbose_name='Comptes', accessor=A("format_comptes"))
    # signature = tables.Column(verbose_name='Signature', accessor=A('get_thumbnail_signature_url'))


    class Meta(DefaultTable.Meta):
        model = CompteTrx
        # fields = ("phone","nin", "firstname", "lastname", "action","comptes","signature", "created", "status",)
        fields = ("compte__short_compte","compte__libelle_court","action","type","gestion","balance","report","report_valide","reportable","created","date_basculement")


    def render_action(self, value):
        update_url = reverse('cddaccount:update_comptetrx', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>
        """.format(update_url,)
        return format_html(str)



    def render_reportable(self, value):
        if value:
            _str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)

    def render_date_basculement(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"
    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"




class DemandeOPFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter(label="Date création")
    reference = CharFilter(lookup_expr='icontains', label="Référence")
    sig_reference = CharFilter(lookup_expr='icontains', label="OP Référence")
    compte = ModelChoiceFilter(queryset=filtrecomptes, empty_label=_("Selectionner Compte Depot"),
                               widget=forms.Select(attrs={'id': 'idcompte'}))

    typecompte = ModelChoiceFilter(queryset=TypeCompteTrx.objects.filter(actif=True), empty_label=_("Selectionner type solde"))

    #date = StackDateFromToRangeFilter()

    class Meta:
        model = DemandeOP
        fields = [ "compte","typecompte","object","amount","created","gestion"]




class DemandeOPTable(DefaultTable):
    selection = tables.CheckBoxColumn(accessor='pk', attrs={"th__input": {"id": "selectAll"}})
    action = tables.Column(verbose_name='Actions autorisées', accessor=A("get_instance"), orderable=True)
    #crud =tables.Column(verbose_name='Modifier', accessor=A("get_instance"))
    agent = tables.Column(verbose_name="Agent de saisie", accessor=A('creator.full_name'))
    compte = tables.Column(verbose_name="Compte de dépôt",accessor='compte__short_compte')
    libelle_court = tables.Column(verbose_name="Libellé court", accessor='compte__libelle_court')
    matricule = tables.Column(accessor='gerant__username',verbose_name="Matricule Gérant")
    #reference=tables.Column(verbose_name="Reference(OV/CH)")
    reference=tables.Column(verbose_name="Référence")
    sig_reference = tables.Column(verbose_name="OP Référence", accessor='render_sig_reference')
    amount=tables.Column(verbose_name="Montant",attrs={"td": {"align": "right"}})
    created = tables.Column(verbose_name="Date de saisie")
    typesolde = tables.Column(verbose_name="Type Solde", accessor='typecompte__name')

    #date_reception = tables.Column(verbose_name="Date de réception")
    #date_prise_en_charge = tables.Column(verbose_name="Date de saisie")
    #date_visa = tables.Column(verbose_name="Date de saisie")



    class Meta(DefaultTable.Meta):
        model = DemandeOP
        #template_name = 'datatables/template_htmx.html'
        order_by="-id"
        fields = ["selection","reference","sig_reference","compte","libelle_court","object","amount","agent","matricule","created","typesolde"]




    def render_amount(self, value):
        v=intcomma(int(value.amount))
        return format_html("{}".format(v)) if value else 0


    def render_created(self, value):
        return format_html("{:%d-%m-%Y}".format(value)) if value else "---"

