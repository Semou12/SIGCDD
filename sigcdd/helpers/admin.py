from django.contrib import admin
from reversion.admin import VersionAdmin

from helpers.models import Category,OracleDatabase, FtpServeur,FtpDir, SigRole, Application, SmsSetting,Currency, ExchangeRate,Sms,FakeModel,SimpleOtp

@admin.register(Category)
class CategoryAdmin(VersionAdmin, admin.ModelAdmin):
    list_display = ("id", "name")


@admin.register(OracleDatabase)
class OracleDatabaseAdmin(VersionAdmin, admin.ModelAdmin):
    list_display = ("id", "host","username","dbname","port","type","sid","actif")

@admin.register(FtpDir)
class FtpDirAdmin(VersionAdmin, admin.ModelAdmin):
    list_display = ("id", "serveur","pull_dir","push_dir","type")

@admin.register(FtpServeur)
class FtpServeurAdmin(VersionAdmin, admin.ModelAdmin):
    list_display = ("id", "host","username","port")

@admin.register(SigRole)
class SigRoleAdmin(VersionAdmin, admin.ModelAdmin):
    list_display = ("id", "role")

@admin.register(SimpleOtp)
class SimpleOtpAdmin(VersionAdmin, admin.ModelAdmin):
    list_display = ("id", "phone","message","created")
@admin.register(FakeModel)
class FakeModelAdmin(VersionAdmin, admin.ModelAdmin):
    list_display = ("id", "user","date","created","is_active","rate","sid")


@admin.register(SmsSetting)
class SmsSettingAdmin(VersionAdmin, admin.ModelAdmin):
    list_display = ("id", "status", "mode")


@admin.register(Application)
class ApplicationAdmin(VersionAdmin, admin.ModelAdmin):
    list_display = ("name", "app_key")
from django.contrib import admin



from reversion.admin import VersionAdmin

@admin.register(Sms)
class SmsAdmin(VersionAdmin, admin.ModelAdmin):
    list_display =("sid","created","phone","content")


class CurrencyAdmin(admin.ModelAdmin):
    search_fields = ('code',)
    list_display = ('code', 'name')


class ExchangeRateAdmin(admin.ModelAdmin):
    search_fields = ('source__code', 'target__code')
    list_display = ('source', 'target', 'rate',"is_active","date")
    list_select_related = ('source', 'target')
    raw_id_fields = ('source', 'target')
    list_filter = ('source__code','is_active')

    class Meta:
        model = ExchangeRate


admin.site.register(Currency, CurrencyAdmin)
admin.site.register(ExchangeRate, ExchangeRateAdmin)