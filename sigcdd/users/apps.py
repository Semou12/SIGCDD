from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = _("Users")

    def ready(self):
        # Applique le monkey-patch de allauth.mfa.utils.is_mfa_enabled.
        # Sans cet appel, allauth utilise sa version d'origine qui se base
        # uniquement sur la présence d'un Authenticator en base, et ignore
        # totalement FORCE_2FA_ENABLED / mfa_exempt / ROLES_WITHOUT_2FA.
        # Voir users/adapters.py::patch_is_mfa_enabled() pour le détail.
        from users.adapters import patch_is_mfa_enabled
        patch_is_mfa_enabled()
