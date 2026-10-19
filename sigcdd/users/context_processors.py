from django.conf import settings


def allauth_settings(request):
    """Expose some settings from django-allauth in templates."""
    return {
        "ACCOUNT_ALLOW_REGISTRATION": settings.ACCOUNT_ALLOW_REGISTRATION,
    }


def mfa_reminder(request):
    """
    Bannière de rappel « la 2FA deviendra obligatoire le <date> » affichée aux
    utilisateurs connectés, non exemptés et sans TOTP, tant que la date limite
    n'est pas atteinte.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    try:
        from django.urls import reverse
        from django.utils import timezone
        from allauth.mfa.models import Authenticator
        from users.adapters import get_force_2fa_deadline, is_2fa_exempt

        deadline = get_force_2fa_deadline()
        if not deadline or is_2fa_exempt(user):
            return {}
        if timezone.localdate() >= deadline:
            # Déjà obligatoire : le middleware prend le relais, pas de rappel.
            return {}
        has_totp = Authenticator.objects.filter(
            user=user, type=Authenticator.Type.TOTP
        ).exists()
        return {
            "mfa_reminder": {
                "show": not has_totp,
                "deadline": deadline,
                "activate_url": reverse("mfa_activate_totp"),
            }
        }
    except Exception:
        return {}
