from django.contrib import admin
from reversion.admin import VersionAdmin
from guardian.admin import GuardedModelAdmin
from core.models import ConfigurationOTP,Structure,Direction,DCP,AffectationAgent,PosteComptable,ProfilePC,ProfileDCP,Ministere,Secteur,CodeService,Region



def reset_comptecdd_admin(modeladmin, request, queryset):
    from cddaccount.models import reset_compteDepot_by_poste
    for postecomptable in queryset:
        reset_compteDepot_by_poste(postecomptable)

reset_comptecdd_admin.short_description = 'Réinitialisation comptedepot'





@admin.register(Structure)
class StructureAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("name", "phone", "email","street")
    search_fields = ("name",)
@admin.register(Region)
class RegionAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","name")

@admin.register(CodeService)
class CodeServiceAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","code","name")

@admin.register(Secteur)
class SecteurAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","code","name")


@admin.register(Ministere)
class MinistereAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","name")

@admin.register(Direction)
class DirectionAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id", "name","ministere","reference")



@admin.register(ProfilePC)
class ProfilePCAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","poste","matricule","phone","firstname", "lastname")

@admin.register(ProfileDCP)
class ProfileDCPAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","matricule","phone","firstname", "lastname")

@admin.register(AffectationAgent)
class AffectationAgentAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id",)

@admin.register(PosteComptable)
class PosteComptableAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("reference","priorite",'type',"name","comptebanque","phone","email","fax","street","zip_code","created","in_production")
    actions = [reset_comptecdd_admin]



@admin.register(DCP)
class DCPAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("reference","name","phone","email","fax","street","zip_code","created","in_production")
    MAX_OBJECTS = 1

    def has_add_permission(self, request):
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)

@admin.register(ConfigurationOTP)
class ConfigurationOTPAdmin(VersionAdmin, GuardedModelAdmin):
    list_display = ("id","validation_op")
    MAX_OBJECTS = 1
    def has_add_permission(self, request):
        if self.model.objects.count() >= 1:
            return False
        return super().has_add_permission(request)