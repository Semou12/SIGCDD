# adapters.py
#
# Adapted for django-allauth 0.58.0
#
# Changes vs the original:
#
#   generate_totp_token():
#     REMOVED imports from allauth.mfa.totp.internal.auth
#       → allauth.mfa.totp.internal does not exist in 0.58.0.
#     REPLACED with direct imports from allauth.mfa.totp:
#       - hotp_counter_from_time()  (replaces yield_hotp_counters_from_time())
#       - hotp_value()
#       - format_hotp_value()
#
#   CustomMFAAdapter.is_mfa_enabled():
#     REMOVED override of DefaultMFAAdapter.is_mfa_enabled()
#       → That method does not exist on DefaultMFAAdapter in 0.58.0.
#         The adapter only exposes: get_totp_label, get_totp_issuer,
#         encrypt, decrypt.
#     REPLACED with a custom has_2fa_enabled() helper used by the
#     middleware and SMSOTPAdapter, and a get_totp_label() override
#     to show how to extend the adapter legitimately in 0.58.0.
#     The bypass logic is now applied via _should_enforce_2fa() at
#     call sites (middleware + SMSOTPAdapter), not inside the adapter.
#
#   patch_is_mfa_enabled() — NEW:
#     In 0.58.0, allauth.mfa.utils.is_mfa_enabled() is a standalone
#     function (not a method on the adapter) and is imported directly by:
#       - allauth.mfa.stages   → MFALoginStage.handle()
#       - allauth.mfa.views    → AuthenticateView, TOTPDeviceDeleteView, etc.
#       - allauth.mfa.signals  → post_save receiver
#     It cannot be overridden via MFA_ADAPTER.
#     We monkey-patch it in AppConfig.ready() (see apps.py) so that users
#     whose role is in ROLES_WITHOUT_2FA are transparently excluded from
#     the MFA stage, even if they have an Authenticator record in the DB.

from typing import Any

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.mfa.adapter import DefaultMFAAdapter
from allauth.mfa.models import Authenticator
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from helpers.models import Role


# ─────────────────────────────────────────────
# Shared constant
# ─────────────────────────────────────────────

ROLES_WITHOUT_2FA = {"SUPER_ADMIN"}


def _should_enforce_2fa(user) -> bool:
    """
    Centralised business logic: returns True if the user must go through 2FA.
    Used by SMSOTPAdapter, Force2FAMiddleware, and the patched is_mfa_enabled.
    """
    if not getattr(settings, "FORCE_2FA_ENABLED", True):
        return False
    if getattr(user, "mfa_exempt", False):
        return False
    if hasattr(user, "role") and user.role in ROLES_WITHOUT_2FA:
        return False
    return True


# ─────────────────────────────────────────────
# Monkey-patch allauth.mfa.utils.is_mfa_enabled
# ─────────────────────────────────────────────

def patch_is_mfa_enabled() -> None:
    """
    Replaces allauth.mfa.utils.is_mfa_enabled with a version that honours
    ROLES_WITHOUT_2FA and mfa_exempt.

    Why monkey-patching:
      In allauth 0.58.0, is_mfa_enabled() is a module-level function imported
      *directly* by allauth.mfa.stages, allauth.mfa.views, allauth.mfa.signals:

          from allauth.mfa.utils import is_mfa_enabled

      Because each module caches its own reference at import time, we must
      patch BOTH the source module (allauth.mfa.utils) AND each consumer
      module that has already imported the name.

    Call this once from AppConfig.ready() (see apps.py) so that all allauth
    modules are already imported before we patch.
    """
    import allauth.mfa.utils as _mfa_utils
    import allauth.mfa.stages as _mfa_stages
    import allauth.mfa.views as _mfa_views
    import allauth.mfa.signals as _mfa_signals

    _original = _mfa_utils.is_mfa_enabled

    def _patched(user, types=None):
        # Exempt roles bypass the MFA stage entirely, regardless of whether
        # they have an Authenticator record in the database.
        if not _should_enforce_2fa(user):
            return False
        return _original(user, types=types)

    # Patch source module so any future `from allauth.mfa.utils import …` gets it.
    _mfa_utils.is_mfa_enabled = _patched
    # Patch consumer modules that have already bound the old reference.
    _mfa_stages.is_mfa_enabled = _patched
    _mfa_views.is_mfa_enabled = _patched
    _mfa_signals.is_mfa_enabled = _patched


# ─────────────────────────────────────────────
# Account adapters
# ─────────────────────────────────────────────

class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest, sociallogin: Any):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)


# ─────────────────────────────────────────────
# TOTP token generation (utility)
# ─────────────────────────────────────────────

def generate_totp_token(user, digits=None, can_send=True):
    """
    Generates the current TOTP token for *user* and optionally sends it via SMS.

    0.58.0 note:
      All TOTP helpers live directly in allauth.mfa.totp (no internal/ sub-package).
      hotp_counter_from_time() returns a single int — there is no iterator
      variant (yield_hotp_counters_from_time) in this version.
    """
    from allauth.mfa.totp import (
        hotp_value,
        hotp_counter_from_time,
        format_hotp_value,
    )
    from allauth.mfa.utils import decrypt

    authenticator = Authenticator.objects.filter(
        user=user,
        type=Authenticator.Type.TOTP,
    ).first()

    if not authenticator:
        return None

    secret = decrypt(authenticator.data["secret"])
    counter = hotp_counter_from_time()
    token = format_hotp_value(hotp_value(secret, counter))

    if can_send:
        from allauth.mfa import app_settings
        user.send_otp(token, app_settings.TOTP_PERIOD)

    return token


# ─────────────────────────────────────────────
# SMS OTP adapter
# ─────────────────────────────────────────────

class SMSOTPAdapter(DefaultAccountAdapter):
    """
    Handles pre_login (SMS token generation) and exposes has_2fa_enabled().
    The 2FA enforcement logic is centralised in _should_enforce_2fa().
    """

    @staticmethod
    def _sms_enabled() -> bool:
        return getattr(settings, "ACTIVATE_TOPT_SMS", False)

    def has_2fa_enabled(self, user) -> bool:
        if not _should_enforce_2fa(user):
            return False
        return Authenticator.objects.filter(
            user=user,
            type=Authenticator.Type.TOTP,
        ).exists()

    def pre_login(self, request: HttpRequest, user, **kwargs) -> HttpResponse | None:
        response = super().pre_login(request, user, **kwargs)
        if response:
            return response

        if self.has_2fa_enabled(user):
            if self._sms_enabled() and user.has_phone_or_email():
                generate_totp_token(user)

        return None


# ─────────────────────────────────────────────
# MFA adapter
# ─────────────────────────────────────────────

class CustomMFAAdapter(DefaultMFAAdapter):
    """
    Extends the allauth MFA adapter for 0.58.0.

    0.58.0 note:
      DefaultMFAAdapter in this version only exposes:
        get_totp_label(), get_totp_issuer(), encrypt(), decrypt()
      There is NO is_mfa_enabled() method on the adapter.
      The standalone helper allauth.mfa.utils.is_mfa_enabled() exists,
      but it cannot be overridden via the adapter in this version.

    To bypass the MFA stage for exempt roles, the enforcement guard lives in:
      - patch_is_mfa_enabled()              ← called in AppConfig.ready(),
                                              patches the allauth pipeline at source
      - _should_enforce_2fa()               ← called by SMSOTPAdapter.has_2fa_enabled()
      - Force2FAMiddleware._should_bypass_2fa()  ← fallback safety net
    """

    def get_totp_label(self, user) -> str:
        label = getattr(user, "display_name", None)
        if label:
            return label
        return super().get_totp_label(user)

    def get_totp_issuer(self) -> str:
        issuer = getattr(settings, "MFA_TOTP_ISSUER", None)
        if issuer:
            return issuer
        return super().get_totp_issuer()
