from __future__ import unicode_literals

import django_tables2 as tables
from django.urls import reverse
from django.utils.html import format_html
from django_filters import FilterSet,CharFilter
from django_tables2.utils import A

from bankcheck.models import ComptableMatiere, ChequeScanne, RejetCheque, DAP, AgentDAP, TypeChequier, Commande, \
	Chequier, Cheque, AnnulationCheque, \
	MiseEnOpposition, CompenseCheque, Bordereau
from helpers.filters import StackDateTimeFromToRangeFilter


class DAPFilter(FilterSet):
	created = StackDateTimeFromToRangeFilter()

	# date = StackDateFromToRangeFilter()

	class Meta:
		model = DAP
		fields = ['name', "in_production", "created", "modified"]


class DefaultTable(tables.Table):
    class Meta:
        template_name = 'datatables/templateB4.html'
        attrs = {'class': 'table table-striped table-bordered  responsive dataex-res-rowcontrol'}


class DAPTable(DefaultTable):
	action = tables.Column(verbose_name='Actions', accessor="id")

	class Meta(DefaultTable.Meta):
		model = DAP
		order_by = ("-created")
		fields = ("name", "phone", "email", "action", "created")

	def render_created(self, value):
		return format_html("{:%d-%m-%Y %H:%M:%S}".format(value)) if value else "---"

	def render_in_production(self, value):
		if value:
			_str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
		else:
			_str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

		return format_html(_str)

	def render_action(self, value):
		delete_url = reverse('bankcheck:delete_dap', kwargs={'pk': value})
		update_url = reverse('bankcheck:update_dap', kwargs={'pk': value})
		str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


        """.format(update_url, )
		return format_html(str)



class AgentDAPFilter(FilterSet):
    #date = StackDateFromToRangeFilter()

    class Meta:
        model = AgentDAP
        fields = ['phone', "lastname","firstname","is_actif"]


class AgentDAPTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")
    roles = tables.Column(verbose_name='Roles', accessor="format_roles")
    #img = tables.Column(verbose_name='Photo', accessor=A('get_thumbnail_url'))
    #signature = tables.Column(verbose_name='Signature', accessor=A('get_thumbnail_signature_url'))

    class Meta(DefaultTable.Meta):
        model = AgentDAP
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
        delete_url = reverse('bankcheck:delete_agentdap', kwargs={'pk': value})
        update_url = reverse('bankcheck:update_agentdap', kwargs={'pk': value})
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

class TypeChequierFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter()
    class Meta:
        model = TypeChequier
        fields = ["nom","created"]

class TypeChequierTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor="id")

    class Meta(DefaultTable.Meta):
        model = TypeChequier
        order_by = ("-created")
        fields = ("nom","taille", "action","created")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_action(self, value):
        delete_url = reverse('bankcheck:delete_typechequier', kwargs={'pk': value})
        update_url = reverse('bankcheck:update_typechequier', kwargs={'pk': value})
        str = """
        <button type="button" class="update-item btn btn-sm btn-warning" data-form-url="{}">
          <span class="fa fa-pencil"></span>
        </button>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)


class CommandeFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter()
    compte__short_compte = CharFilter(lookup_expr='icontains', label="Compte")
    reference = CharFilter(lookup_expr='icontains', label="Réference")
    class Meta:
        model = Commande
        fields = ["created","reference","compte__short_compte"]

class CommandeTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor=A("get_instance"))
    items = tables.Column(verbose_name='Chéquiers', accessor=A("format_items"))
    compte = tables.Column(verbose_name="Compte dépôt", accessor='compte__short_compte')
    demandeur=tables.Column(verbose_name='Demandeur', accessor=A("demandeur.full_name"))
    agent_pc = tables.Column(verbose_name='Comptable', accessor=A("agent_pc.full_name"))

    class Meta(DefaultTable.Meta):
        model = Commande
        order_by = ("-created")
        fields = ("reference","compte","status","items","demandeur","agent_pc", "action","created")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_action__(self, value):
        delete_url = reverse('bankcheck:delete_commande', kwargs={'pk': value.id})
        update_url = reverse('bankcheck:update_commande', kwargs={'reference': value.reference})
        str = """
        <a type="button" class="update-item btn btn-sm btn-warning" href="{}">
          <span class="fa fa-pencil"></span>
        </a>


         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
          <span class="fa fa-trash"></span>
        </button>
        """.format(update_url, delete_url)
        return format_html(str)

    def render_action(self, value):
	    user = self.request.user
	    if value.traiter:
		    str = "-"
		    prise_en_charge = reverse('bankcheck:bordereau_commande_view', kwargs={'reference': value.reference})
		    if user.has_perm('bankcheck.valider_commande'):
			    str = """<br><a  href="{}"><span >Bordereau </span></a>""".format(prise_en_charge, )

	    else:
		    str = """<div class="form-group">"""
		    if value.accepter:
			    if user.has_perm('bankcheck.valider_commande'):
				    prise_en_charge = reverse('bankcheck:valider_commande_chequier', kwargs={'reference': value.reference})
				    str__ = """<br><a type="button" class="valider-bf-item btn btn-sm btn-warning btn-block" href="{}"><span >Editer bordereau </span></a>""".format(
					    prise_en_charge, )
				    str +="En cours d'edition"
			    else:
				    str += """ATTENTE TRAITEMENT"""
		    else:
			    delete_url = reverse('bankcheck:delete_commande', kwargs={'pk': value.id})
			    update_url = reverse('bankcheck:update_commande', kwargs={'reference': value.reference})

			    if user.has_perm('bankcheck.delete_commande'):
				    str += """<button type="button" class="delete-item btn btn-sm btn-danger btn-block" data-form-url="{}" >
	                                      <span class="fa fa-trash">Supprimer</span>
	                                    </button>
	                                    """.format(delete_url, )
			    if user.has_perm('bankcheck.change_commande'):
				    str += """<a type="button" class="update-item btn btn-sm btn-primary btn-block" href="{}" >
	                                          <span class="fa fa-pencil">Modifier</span>
	                                        </a>""".format(update_url, )

			    if user.has_perm('bankcheck.accepter_commande'):
				    prise_en_charge = reverse('bankcheck:accepter_commande_chequier', kwargs={'reference': value.reference})
				    str += """<br><a type="button" class="demander-bf-item btn btn-sm btn-purple btn-block" href="{}"><span >Accepter commande </span></a>""".format(
					    prise_en_charge, )
			    else:
				    str += """ATTENTE ACCEPTATION"""

		    str += "</div>"

	    return format_html(str)



class ChequierFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter(label="Date création")
    compte__short_compte = CharFilter(lookup_expr='icontains', label="compte")
    class Meta:
        model = Chequier
        fields = ["created","reference","demande","gerant","agent_pc","compte__short_compte","compte__poste"]


class ChequierTable(DefaultTable):
	selection = tables.CheckBoxColumn(accessor='pk', attrs={"th__input": {"id": "selectAll"}})
	action = tables.Column(verbose_name='Actions', accessor=A("get_instance"))
	compte = tables.Column(verbose_name="Compte dépôt", accessor='compte__short_compte')
	editeur = tables.Column(verbose_name='Editeur', accessor=A("editeur.full_name"))

	class Meta(DefaultTable.Meta):
		model = Chequier
		order_by = ("-created")
		fields = ("selection", "reference", "compte", "debut", "fin", "taille", "vide", "blocked","distribue","action", "delivered",
		"created","editeur")


	def render_created(self, value):
		return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"


	def render_reference(self, value):
		details_url = reverse('bankcheck:details_chequier', kwargs={'reference': value})
		str = """<a   href="{}"><span >{} </span></a>""".format(details_url, value)
		return format_html(str)


	def render_action(self, value):
		user = self.request.user
		str = """<div class="form-group">"""
		if user.has_perm('bankcheck.bloquer_chequier'):
			if value.blocked:
				str += "BLOQUE"
			else:
				prise_en_charge = reverse('bankcheck:bloquer_chequier',
				                          kwargs={'reference': value.reference})
				str += """<br><a type="button" class="bloquer-item btn btn-sm btn-danger btn-block" href="{}"><span >Bloquer chequier </span></a>""".format(
					prise_en_charge, )

		if user.has_perm('bankcheck.priseencharge_chequier'):
			if value.prise_en_charge:
				str += "RECEPTIONNE"
			else:
				prise_en_charge = reverse('bankcheck:priseencharge_chequier',
				                          kwargs={'reference': value.reference})
				str += """<br><button type="button" class="prise-en-charge-item btn btn-sm btn-danger btn-block" data-form-url="{}"><span >Reception chequier </span></button>""".format(
					prise_en_charge, )

		if user.has_perm('bankcheck.delivrer_chequier'):
			if value.delivered :
				str += "<br>AFFECTE"
			elif value.prise_en_charge :
				if value.distribue:
					delete_url = reverse('bankcheck:delivrer_chequier', kwargs={'reference': value.reference})


					str += """<br><a type="button" class="delivrer-item btn btn-sm btn-warning btn-block" href="{}"><span >Affecter</span></a>""".format(
						delete_url, )


				else:str += "ATTENTE DISTRIBUTION"
			else:
				str += "ATTENTE RECEPTIONN "
			str += "</div>"
		return format_html(str)



class ChequeFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter()
    class Meta:
        model = Cheque
        fields = ["created","reference"]

class ChequeTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor=A("get_instance"))
    compte = tables.Column(verbose_name="Compte", accessor='chequier__compte__short_compte')

    class Meta(DefaultTable.Meta):
        model = Cheque
        order_by = ("-created")
        fields = ("reference","compte", "action","amount","use","blocked","observations","created")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_action__(self, value):
	    user = self.request.user
	    str = """<div class="form-group">"""
	    if user.has_perm('bankcheck.bloquer_chequier'):
		    if value.bloquer:
			    str += "BLOQUE"
		    else:
			    prise_en_charge = reverse('bankcheck:bloquer_chequier',
			                              kwargs={'reference': value.reference})
			    str += """<br><a type="button" class="bloquer-item btn btn-sm btn-danger btn-block" href="{}"><span >Bloquer chequier </span></a>""".format(
				    prise_en_charge, )

	    if user.has_perm('bankcheck.delivrer_chequier'):
		    if value.delivered:
			    str += "LIVRE"
		    else:
			    delete_url = reverse('bankcheck:delivrer_chequier', kwargs={'reference': value.reference})
			    str += """<button type="button" class="delivrer-item btn btn-sm btn-warning btn-block" data-form-url="{}" >
	                                              Delivrer</span>
	                                            </button>
	                                            """.format(delete_url, )
		    str += "</div>"
	    return format_html(str)

class MiseEnOppositionFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter(label="Date création")
    class Meta:
        model = MiseEnOpposition
        fields = ["created","cheque__reference"]

class AnnulationChequeFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter()
    class Meta:
        model = AnnulationCheque
        fields = ["created","cheque__reference"]

class CompenseChequeFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter()
    class Meta:
        model = CompenseCheque
        fields = ["created","cheque__reference"]



class CompenseChequeTable(DefaultTable):
    #action = tables.Column(verbose_name='Actions', accessor=A("get_instance"))
    cheque = tables.Column(verbose_name="Chèque", accessor='cheque__reference')


    class Meta(DefaultTable.Meta):
        model = CompenseCheque
        order_by = ("-created")
        fields = ("reference","cheque","amount","banque","date_compense","observations","created")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_date_compense(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"



    def render_action__(self, value):
	    user = self.request.user
	    str = """<div class="form-group">"""
	    if user.has_perm('bankcheck.bloquer_chequier'):
		    if value.bloquer:
			    str += "BLOQUE"
		    else:
			    prise_en_charge = reverse('bankcheck:bloquer_chequier',
			                              kwargs={'reference': value.reference})
			    str += """<br><a type="button" class="bloquer-item btn btn-sm btn-danger btn-block" href="{}"><span >Bloquer chequier </span></a>""".format(
				    prise_en_charge, )

	    if user.has_perm('bankcheck.delivrer_chequier'):
		    if value.delivered:
			    str += "LIVRE"
		    else:
			    delete_url = reverse('bankcheck:delivrer_chequier', kwargs={'reference': value.reference})
			    str += """<button type="button" class="delivrer-item btn btn-sm btn-warning btn-block" data-form-url="{}" >
	                                              Delivrer</span>
	                                            </button>
	                                            """.format(delete_url, )
		    str += "</div>"
	    return format_html(str)


class MiseEnOppositionTable(DefaultTable):
	action = tables.Column(verbose_name='Actions', accessor=A("get_instance"))
	cheque = tables.Column(verbose_name="Chèque", accessor='cheque__reference')
	demandeur = tables.Column(verbose_name="Demandeur", accessor='demandeur.full_name')
	accepteur = tables.Column(verbose_name="Accepteur", accessor='accepteur.full_name')

	class Meta(DefaultTable.Meta):
		model = MiseEnOpposition
		order_by = ("-created")
		fields = ("cheque", "amount", "accepter", "acceptation_date", "observations", "created", "action", "demandeur", "accepteur")

	def render_created(self, value):
		return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

	def render_date_acceptation(self, value):
		return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

	def render_date_approbation(self, value):
		return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"


	def render_action(self, value):
		user = self.request.user
		str = """<div class="form-group">"""


		if value.accepter:
			str = "DEJA MISE EN OPPOSITION"
		else:
			if user.has_perm('bankcheck.accepter_miseenopposition'):
				prise_en_charge = reverse('bankcheck:accepter_miseenopposition',
				                          kwargs={'reference': value.reference})
				str += """<button type="button" class="accepter-item btn btn-sm btn-primary btn-block" data-form-url="{}" >
						                                              VALIDER</span>
						                                            </button>
						                                            """.format(prise_en_charge, )
			else:
				str += "ATTENTE MISE EN OPPOSITION"

			delete_url = reverse('bankcheck:delete_miseenopposition', kwargs={'pk': value.pk})
			update_url = reverse('bankcheck:update_miseenopposition', kwargs={'pk': value.pk})

			if user.has_perm('bankcheck.delete_miseenopposition'):
				str += """<button type="button" class="delete-item btn btn-sm btn-danger btn-block" data-form-url="{}" >
				                                      <span class="fa fa-trash">Supprimer</span>
				                                    </button>
				                                    """.format(delete_url, )
			if user.has_perm('bankcheck.change_miseenopposition'):
				str += """<button type="button" class="update-item btn btn-sm btn-primary btn-block" data-form-url="{}" >
				                                          <span class="fa fa-pencil">Modifier</span>
				                                        </button>""".format(update_url, )

		str += "</div>"
		return format_html(str)

class AnnulationChequeTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor=A("get_instance"))
    cheque = tables.Column(verbose_name="Chèque", accessor='cheque__reference')
    demandeur = tables.Column(verbose_name="Demandeur", accessor='demandeur.full_name')
    accepteur = tables.Column(verbose_name="Accepteur", accessor='accepteur.full_name')


    class Meta(DefaultTable.Meta):
        model = AnnulationCheque
        order_by = ("-created")
        fields = ("cheque","amount","accepter","acceptation_date","observations","created","action","demandeur","accepteur")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_date_acceptation(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_date_approbation(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_action(self, value):
	    user = self.request.user
	    str = """<div class="form-group">"""
	    if value.accepter:
		    str += "DEJA ANNULE"
	    else:
		    if user.has_perm('bankcheck.accepter_annulationcheque'):
			    prise_en_charge = reverse('bankcheck:accepter_annulationcheque',
			                              kwargs={'reference': value.reference})
			    str += """<button type="button" class="accepter-item btn btn btn-primary btn-block" data-form-url="{}" >
					                                              Valider Annulation </span>
					                                            </button>
					                                            """.format(prise_en_charge, )
		    else:
			    str += "ATTENTE ANNULLATION"

		    delete_url = reverse('bankcheck:delete_annulationcheque', kwargs={'pk': value.pk})
		    update_url = reverse('bankcheck:update_annulationcheque', kwargs={'pk': value.pk})

		    if user.has_perm('bankcheck.delete_annulationcheque'):
			    str += """<button type="button" class="delete-item btn btn btn-danger btn-block" data-form-url="{}" >
			                                      <span class="fa fa-trash"></span>
			                                    </button>
			                                    """.format(delete_url, )
		    if user.has_perm('bankcheck.change_annulationcheque'):
			    str += """<button type="button" class="update-item btn btn btn-warning" data-form-url="{}" >
			                                          <span class="fa fa-pencil"></span>
			                                        </button>""".format(update_url, )

	    str += "</div>"
	    return format_html(str)




class ChequeFullTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor=A("get_instance"))
    compte = tables.Column(verbose_name="Compte", accessor='chequier__compte__short_compte')



    class Meta(DefaultTable.Meta):
        model = Cheque
        order_by = ("-created")
        fields = ("reference","compte", "action","amount","endosser_par","cin_receptionnaire","phone_receptionnaire","use","delivred","en_compense","mis_op_date","en_annulation","annulation_date","en_mis_op","mis_op_date","trx","delivred_date","blocked","observations","created","observations")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_mis_op_date(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"


    def render_annulation_date(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_compense_date(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"






class RejetChequeFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter()
    class Meta:
        model = RejetCheque
        fields = ["created","cheque__reference"]

class RejetChequeTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor=A("get_instance"))
    cheque = tables.Column(verbose_name="Chèque", accessor='cheque__reference')
    demandeur = tables.Column(verbose_name="Demandeur", accessor='demandeur.full_name')
    accepteur = tables.Column(verbose_name="Accepteur", accessor='accepteur.full_name')


    class Meta(DefaultTable.Meta):
        model = RejetCheque
        order_by = ("-created")
        fields = ("cheque","amount","accepter","acceptation_date","observations","created","action","demandeur","accepteur")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_date_acceptation(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_date_approbation(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_action(self, value):
	    user = self.request.user
	    str = """<div class="form-group">"""
	    if value.accepter:
		    str += "DEJA REJETE"
	    else:
		    if user.has_perm('bankcheck.accepter_rejetcheque'):
			    prise_en_charge = reverse('bankcheck:accepter_rejetcheque',
			                              kwargs={'reference': value.reference})
			    str += """<button type="button" class="accepter-item btn btn btn-primary btn-block" data-form-url="{}" >
					                                              Valider Rejet </span>
					                                            </button>
					                                            """.format(prise_en_charge, )
		    else:
			    str += "ATTENTE REJET"

		    delete_url = reverse('bankcheck:delete_rejetcheque', kwargs={'pk': value.pk})
		    update_url = reverse('bankcheck:update_rejetcheque', kwargs={'pk': value.pk})

		    if user.has_perm('bankcheck.delete_rejetcheque'):
			    str += """<button type="button" class="delete-item btn btn btn-danger btn-block" data-form-url="{}" >
			                                      <span class="fa fa-trash"></span>
			                                    </button>
			                                    """.format(delete_url, )
		    if user.has_perm('bankcheck.change_rejetcheque'):
			    str += """<button type="button" class="update-item btn btn btn-warning" data-form-url="{}" >
			                                          <span class="fa fa-pencil"></span>
			                                        </button>""".format(update_url, )

	    str += "</div>"
	    return format_html(str)






class ChequeScanneFilter(FilterSet):
    created = StackDateTimeFromToRangeFilter(label="Date création")
    class Meta:
        model = ChequeScanne
        fields = ["created","reference","compte_aster"]



class ChequeScanneTable(DefaultTable):
    #action = tables.Column(verbose_name='Actions', accessor=A("get_instance"))
    cheque = tables.Column(verbose_name="Chèque", accessor='reference')
    poste = tables.Column(verbose_name="Code Poste", accessor='poste.reference')
    name = tables.Column(verbose_name="Nom Poste", accessor='poste.name')


    class Meta(DefaultTable.Meta):
        model = ChequeScanne
        order_by = ("-created")
        fields = ("cheque","typeop","statut","code_cheque","code_place","amount","banque","agence","rib","compte","date_compense","poste","name","beneficiare","adresse_benef","rejet","traite","sens","created")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_date_compense(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"





class ComptableMatiereFilter(FilterSet):
    #date = StackDateFromToRangeFilter()

    class Meta:
        model = ComptableMatiere
        fields = ['phone', "lastname","firstname"]


class ComptableMatiereTable(DefaultTable):
    action = tables.Column(verbose_name='Actions', accessor=A("id"))
    poste = tables.Column(verbose_name="Code Poste", accessor='poste.reference')
    name = tables.Column(verbose_name="Nom Poste", accessor='poste.name')


    class Meta(DefaultTable.Meta):
        model = ComptableMatiere
        order_by = "-created"
        fields = ("phone","nin", "firstname", "lastname", "action","poste","name","signature", "created", "status",)

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M:%S}".format(value)) if value else "---"

    def render_is_actif(self, value):
        if value:
            _str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
        else:
            _str = """<button type="button" class="btn  btn-sm btn-outline-danger btn-round" disabled ><i class="fa fa-times"></i></button>"""

        return format_html(_str)

    def render_action(self, value):
        delete_url = reverse('bankcheck:delete_comptablematiere', kwargs={'pk': value})
        update_url = reverse('bankcheck:update_comptablematiere', kwargs={'pk': value})
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






class BordereauFilter(FilterSet):
	#created = StackDateFromToRangeFilter()

    class Meta:
        model = Bordereau
        fields = ['created', "imprimeur","reference"]


class BordereauTable(DefaultTable):
    #action = tables.Column(verbose_name='Actions', accessor=A("get_instance"))
    cheque = tables.Column(verbose_name="Reference", accessor='reference')
    imprimeur = tables.Column(verbose_name="imprimeur", accessor='imprimeur.name')
    name = tables.Column(verbose_name="Nom Poste", accessor='poste.name')


    class Meta(DefaultTable.Meta):
        model = Bordereau
        order_by = ("-created")
        fields = ("reference","imprimeur","created")

    def render_created(self, value):
        return format_html("{:%d-%m-%Y %H:%M}".format(value)) if value else "---"

    def render_reference(self, value):
	    details_url = reverse('bankcheck:commande_traiter',kwargs={'reference': value})
	    str = """<a   href="{}"><span >{} </span></a>""".format(details_url, value)
	    return format_html(str)