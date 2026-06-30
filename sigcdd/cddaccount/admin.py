from django.contrib import admin
from reversion.admin import VersionAdmin
from guardian.admin import GuardedModelAdmin
from cddaccount.models import DemandeOP,ReportGestion,CompteTrx,TypeCompteTrx, Mandataire,SousNature, Balance,FichierData,VirementMasse,VirementDetails,SettingsVRM,Report,VisaOrdrePayment,AnnulationOrdrePayment,Transaction, AnnulationBlocageFond,SettingsOP,ObsProjet,BlocageFond, JourneeComptable,AnneeComptable, Projet, AvisDeCredit, AvisDeDebit,ObsOrdrePayment,TransactionOP,ReservationFond,ValidationCompte,CompteDepot,Bank,CodeAgence,GerantCD,GestionCompteDepot,AgentSaisieCD,OrdrePayment,Depositaire,Nature,PrisEnchageOrdrePayment

@admin.register(TypeCompteTrx)
class TypeCompteTrxAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","code","name","reportable","taux","nature","actif","reporter_bascule")


@admin.register(CompteTrx)
class CompteTrxAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","type","taux","reportable","reporter_bascule","compte","balance","report_valide","report","date_basculement","gestion")
	list_filter = ("type","gestion","reportable")
	search_fields = ("compte__short_compte",)

def reset_balance_compte_admin(modeladmin, request, queryset):
    from cddaccount.tasks import async_compute_balance
    async_compute_balance.delay(list(queryset.values_list("id",flat=True)))


reset_balance_compte_admin.short_description = 'Réinitialisation le solde'


from import_export import resources

from import_export.admin import ExportActionModelAdmin
class OrdrePaymentResource(resources.ModelResource):

    class Meta:
        model = OrdrePayment

        fields = ('id', 'sig_reference', 'amount',)

@admin.register(Balance)
class BalanceAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("compte","be_credit_fonc","be_credit_inv","op_credit_fonc","op_credit_inv","op_debit_inv","op_debit_fonc","total_credit_fonc","total_credit_inv","total_debit_inv","total_debit_fonc","bs_credit_fonc","bs_credit_inv","bs_debit_inv","bs_debit_fonc")



@admin.register(FichierData)
class FichierDataAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","type","name","created")



@admin.register(ReportGestion)
class ReportGestionAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","compte","amount",'f_amount',"sens","typecompte","anne_comptable","gestion_courant")
	list_filter = ("typecompte","gestion_courant","sens")
	search_fields = ("compte__short_compte",)


@admin.register(Report)
class ReportAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","compte","amount_fonc","amount_invest","anne_comptable")

@admin.register(AnnulationOrdrePayment)
class AnnulationOrdrePaymentAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'ordre',"etape",'created')


@admin.register(Transaction)
class TransactionAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","reference","typecompte","account_depot","payment_mean",'libelle','created',"sens","fc_amount",'amount',"account_secondaire","status_aster","etape_compense","date_envoi","date_retour","date_rlv","is_cancel_trx_0")
	list_filter = ("payment_mean","sens","typecompte","jour_comptable__annee_comptable","is_cancel_trx_0")
	raw_id_fields = ("jour_comptable",)
	search_fields = ("origin_reference","account_depot","reference" )


@admin.register(SettingsOP)
class SettingsOPAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","name","rejet_notif_benef","rejet_notif_gerant","visa_notif_benef","visa_notif_gerant","aster_variant")

@admin.register(ObsProjet)
class ObsProjetAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","motif")

@admin.register(AnnulationBlocageFond)
class AnnulationBlocageFondAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","reference",'blocage',"compte","amount",'created')

@admin.register(BlocageFond)
class BlocageFondAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","reference",'compte',"projet","amount","open_date","end_date",'created')

@admin.register(JourneeComptable)
class JourneeComptableAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","jour","name","user", "actif","close")
    list_filter = ("jour","annee_comptable")

    search_fields = ("user__username",)

@admin.register(AnneeComptable)
class AnneeComptableAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","name","period","parent", "actif")


@admin.register(Projet)
class ProjetAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","typecompte","amount")

@admin.register(AvisDeCredit)
class AvisDeCreditAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","typecompte","reference","reference_aster","nature",'compte',"account_depot","account_secondaire","sens","payment_mean","bocagefond","date_avis","provenance",'created','amount')
	search_fields = ("reference_aster","compte__short_compte")
	list_filter = ("payment_mean", "sens","jour_comptable__annee_comptable","date_avis","typecompte")
	raw_id_fields = ("jour_comptable",)
@admin.register(AvisDeDebit)
class AvisDeDebitAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","typecompte","reference","reference_aster",'compte',"account_depot","account_secondaire","sens","payment_mean","projet","date_avis",'created','amount')
	search_fields = ("reference_aster", "compte__short_compte")
	list_filter = ("payment_mean", "sens", "jour_comptable__annee_comptable", "date_avis","typecompte")
	raw_id_fields = ("jour_comptable",)
@admin.register(ObsOrdrePayment)
class ObsOrdrePaymentAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","motif")

@admin.register(TransactionOP)
class TransactionOPAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","typecompte",'reservation',"account_depot","account_secondaire",'created',"sens","has_cancel",'amount','fc_amount','cheque',"payment_mean","created","ref_canceltrx","date_rlv","is_cancel_trx")
	list_filter = ("payment_mean","sens","jour_comptable__annee_comptable","typecompte","is_cancel_trx")
	search_fields = ("origin_reference","account_depot","reference")
	raw_id_fields = ("jour_comptable",)

@admin.register(ReservationFond)
class ReservationFondAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'ordre','created','amount',"payment_mean","reglement","has_trx","close","has_cancel_op")
	raw_id_fields = ("ordre",)
	list_filter = ("reglement", "payment_mean","has_trx","close","ordre__typecompte","has_cancel_op")

	search_fields = ("id","ordre__sig_reference","ordre__compte__short_compte")

@admin.register(PrisEnchageOrdrePayment)
class PrisEnchageOrdrePaymentAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'ordre','created','amount',"cancel")
	list_filter = ("cancel",)
	raw_id_fields = ("ordre",)

@admin.register(VisaOrdrePayment)
class VisaOrdrePaymentAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'prise_en_charge','created',"cancel")

@admin.register(OrdrePayment)
class OrdrePaymentAdmin(VersionAdmin, GuardedModelAdmin,ExportActionModelAdmin):
	list_display = ("id",'object',"typecompte",'compte',"gestion","poste_code",'reference','sig_reference','amount',"vali_multi","cheque_delivred","etape","payment_mean","transfer_out_umeoa","status_provider","provider_trx","created")
	list_filter = ("etape","payment_mean","compte__poste","gestion","transfer_out_umeoa","status_provider","gestion","typecompte")
	raw_id_fields = ("compte","jour_comptable")
	search_fields = ("sig_reference","compte__short_compte","cheque","provider_trx")
	resource_classes = [OrdrePaymentResource]







@admin.register(DemandeOP)
class DemandeOPAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'object','compte',"gestion",'reference','sig_reference','amount',"created")
	list_filter = ("compte__poste","gestion")
	raw_id_fields = ("compte",)
	search_fields = ("sig_reference","compte__short_compte",)
@admin.register(Nature)
class NatureAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'name')



@admin.register(SousNature)
class SousNatureAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'name',"nature")
	raw_id_fields = ("nature",)



@admin.register(Depositaire)
class DepositaireAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","lastname","firstname","nin")
	search_fields = ("lastname","firstname","nin")




@admin.register(AgentSaisieCD)
class AgentSaisieCDAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","matricule","phone","firstname", "lastname","status")

@admin.register(GestionCompteDepot)
class GestionCompteDepotAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","compte","gerant","agent_pc","period", "actif")
    search_fields = ("compte__shrot_compte",)
    raw_id_fields = ("compte",)


@admin.register(GerantCD)
class GerantCDAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","poste","matricule","phone","firstname", "lastname","status")

@admin.register(CompteDepot)
class CompteDepotAdmin(VersionAdmin, GuardedModelAdmin):
	list_filter = ("poste","nature","ministere","secteur","secrete")
	search_fields = ("compte","libelle","libelle_court")
	raw_id_fields = ("structure","direction")
	list_display = ("compte","short_compte",'balance',"nature","secteur","code_service","libelle","libelle_court","direction","poste","ministere","agent","created","open_date","actif","secrete")
	actions = [reset_balance_compte_admin]

@admin.register(CodeAgence)
class CodeAgenceAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'code',"bank","actif")
	list_filter = ("actif",)
	search_fields = ("code", "bank__name")

@admin.register(Bank)
class BankAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'code',"name")
	search_fields = ("code", "name")

@admin.register(ValidationCompte)
class ValidationCompteAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'compte',"agent","description","created")
	search_fields = ('compte__short_compte',)


@admin.register(SettingsVRM)
class SettingsVRMAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'taille','max_amount')

@admin.register(VirementMasse)
class VirementMasseAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'object','compte','reference','sig_reference','amount',"vali_multi","details_file","created")


@admin.register(VirementDetails)
class VirementDetailsAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id",'virement','iban_benef','reference',"compte_depot","reference_aster","date_payement",'amount',"created","status_aster","etape_compense","trx")
	search_fields = ("iban_benef", "virement__sig_reference", "reference_aster","compte_depot")
	list_filter = ("created",)



@admin.register(Mandataire)
class MandataireAdmin(VersionAdmin, GuardedModelAdmin):
	list_display = ("id","lastname","firstname","nin")
	search_fields = ("lastname","firstname","nin")
