from django.contrib import admin
from reversion.admin import VersionAdmin
from guardian.admin import GuardedModelAdmin
from bankcheck.models import Bordereau,Imprimeur, ComptableMatiere, ChequeScanne, RejetCheque,DAP,TypeChequier,Commande,ElementCommande,Chequier,Cheque,AgentDAP,SettingsChequier,MiseEnOpposition,CompenseCheque,AnnulationCheque



@admin.register(Imprimeur)
class ImprimeurAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","name","phone","fax")

@admin.register(Bordereau)
class BordereauAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","reference","imprimeur","created")
    raw_id_fields = ("chequiers",)


@admin.register(ComptableMatiere)
class ComptableMatiereAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","matricule","phone","firstname", "lastname","poste")



@admin.register(SettingsChequier)
class SettingsChequierAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'name',"first_sequence","last_sequence")
	MAX_OBJECTS = 1

	def has_add_permission(self, request):
		if self.model.objects.count() >= 1:
			return False
		return super().has_add_permission(request)


class ChequeInline(admin.TabularInline):
	model = Cheque

@admin.register(Cheque)
class ChequeAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'reference',"chequier","amount","use","blocked","actif",'created')
	search_fields = ("reference",)

	raw_id_fields = ("chequier",)



@admin.register(Chequier)
class ChequierAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'reference',"compte","editeur",'debut','fin',"dap","taille","type","delivered","blocked","vide",'created','otp_apc',"agent_pc",'otp_gerant',"gerant")
	inlines = [ChequeInline]
	raw_id_fields = ("compte",)
	search_fields = ("compte__poste__reference","compte__short_compte","reference")

class ElementCommandeInline(admin.TabularInline):
	model = ElementCommande
@admin.register(Commande)
class CommandeAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'reference',"compte","demandeur",'agent_pc','created')
	inlines = [ElementCommandeInline]

@admin.register(AgentDAP)
class AgentDAPAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","matricule","phone","firstname", "lastname","dap")


@admin.register(TypeChequier)
class TypeChequierAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","taille","nom")

@admin.register(DAP)
class DAPAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("reference","name","phone","email","fax","street","zip_code","created","in_production")



@admin.register(CompenseCheque)
class CompenseChequeAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'reference',"cheque","amount","banque","creator","date_compense",'created')


@admin.register(AnnulationCheque)
class AnnulationChequeAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'reference',"cheque","amount","demandeur",'created')


@admin.register(MiseEnOpposition)
class MiseEnOppositionAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'reference',"cheque","amount","demandeur",'created')

@admin.register(RejetCheque)
class RejetChequesAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'reference',"cheque","amount","demandeur",'created')


@admin.register(ChequeScanne)
class ChequeScanneAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'reference',"statut","cheque","amount","banque","compte_aster","poste",'agent_poste','created')






