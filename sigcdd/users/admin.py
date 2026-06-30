from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

#from users.forms import UserAdminChangeForm, UserAdminCreationForm

User = get_user_model()


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    #form = UserAdminChangeForm
    #add_form = UserAdminCreationForm
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("email","first_name","last_name","phone",'mfa_exempt')}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "role","force_change_pwd",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = ["username", "email","phone","first_name","last_name","role", "is_active", "is_superuser"]
    search_fields = ["username", "email","first_name","last_name",]
    list_filter = ("role","is_active", "is_superuser")

    actions = ["disable_2fa", "enable_2fa_exemption"]

    def disable_2fa(self, request, queryset):
        from allauth.mfa.models import Authenticator
        # Supprimer les devices 2FA des utilisateurs sélectionnés
        Authenticator.objects.filter(
            user__in=queryset,
            type=Authenticator.Type.TOTP
        ).delete()
        self.message_user(request, "2FA désactivée pour les utilisateurs sélectionnés.")

    disable_2fa.short_description = "Désactiver la 2FA"

    def enable_2fa_exemption(self, request, queryset):
        queryset.update(mfa_exempt=True)
        self.message_user(request, "Exemption 2FA activée pour les utilisateurs sélectionnés.")

    enable_2fa_exemption.short_description = "Exempter de la 2FA"
