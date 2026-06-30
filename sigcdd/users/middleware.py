
import django
from django.conf import settings
from django.shortcuts import redirect, render

from helpers.models import Role


class EnableFirstLoginCPWMiddleWare(object):
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        response = self.process_request(request)
        if response is None and callable(self.get_response):
            response = self.get_response(request)
        return response

    def process_request(self, request):
        if settings.FIRST_LOGIN_MODE:
            if request.user.is_active and request.user.force_change_pwd and request.user.is_authenticated:
                view_match = request.path

                print(redirect(settings.FIRST_LOGIN_MODE_REDIRECT_URL).url)
                print(settings.FIRST_LOGIN_MODE_REDIRECT_URL)
                print(settings.LOGOUT_URL)
                if view_match!=redirect(settings.FIRST_LOGIN_MODE_REDIRECT_URL).url:
                    print("je suis la ")
                    print("bbbbbbb= {}".format(view_match,))
                    if view_match!=redirect(settings.LOGOUT_URL).url:
                        return redirect(settings.FIRST_LOGIN_MODE_REDIRECT_URL)
        return None


from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve
from django.contrib import messages
class SelectCddAccountWMiddleWare(MiddlewareMixin):
    # List of URL names that the user should still be allowed to access.
    allowed_pages = [
        # They should still be able to log out or change password.
        "account_change_password",
        "account_logout",
        "account_reset_password",
        # URLs required to set up two-factor
        "two-factor-setup",
        "complete_gerant",
        "select_cddaccount_for_work"
    ]
    # The message to the user if they don't have 2FA enabled and must enable it.
    require_cdd_message = (
        "Merci de selectionner votre compte dépot de travail."
    )

    def on_require_selectcdd(self, request):
        """
        If the current request requires selectaccount and the user does not have it
        enabled, this is executed. The result of this is returned from the
        middleware.
        """
        # See allauth.account.adapter.DefaultAccountAdapter.add_message.
        if "django.contrib.messages" in settings.INSTALLED_APPS:
            storage = messages.get_messages(request)
            tag = "selectcdd_required"
            for m in storage:
                if m.extra_tags == tag:
                    m.message = self.require_cdd_message
                    break
            # Otherwise, create a new message.
            else:
                pass
                #messages.error(request, self.require_cdd_message, extra_tags=tag)
            # Mark the storage as not processed so they'll be shown to the user.
            storage.used = False

        # Redirect user to two-factor setup page.
        return redirect("cddaccount:select_cddaccount_for_work")

    def require_selectcdd(self, request):
        """
        Check if this request is required to have select cdd before accessing the app.
        This should return True if this request requires selectcdd.
        You can access anything on the request, but generally request.user will
        be most interesting here.
        """
        if hasattr(request.user, "gerant_cd") == True or hasattr(request.user, Role.AGENT_SAISIE_CD.lower()) == True:
            if "select_cddacc_user_id" in request.session:
                allauth_2fa_user_id = request.session["select_cddacc_user_id"]
                return False
            return True

        else: return False

    def is_allowed_page(self, request):
        return request.resolver_match.url_name in self.allowed_pages

    def process_view(self, request, view_func, view_args, view_kwargs):
        # The user is not logged in, do nothing.
        if request.user.is_anonymous:
            return

        # If this doesn't require 2FA, then stop processing.
        if not self.require_selectcdd(request):
            return

        # If the user is on one of the allowed pages, do nothing.
        if self.is_allowed_page(request):
            return
        return self.on_require_selectcdd(request)

    def __process_request(self, request):
        match = resolve(request.path)
        if not match.url_name or not match.url_name.startswith(
                "select_cddaccount_for_work"
        ):
            try:
                del request.session["select_cddacc_user_id"]
            except KeyError:
                pass






# ============================================================
# Middleware 3 — Force 2FA setup for required roles
# ============================================================
#
# Changes for django-allauth 0.58.0:
#
#   REMOVED: from allauth.account.internal.stagekit import clear_login
#            → allauth.account.internal does not exist in 0.58.0.
#
#   REPLACED with: unstash_login(request) from allauth.account.utils
#                  This pops "account_login" from the session, which is the
#                  correct way to abort an in-progress login flow in 0.58.0.
#
#   NOTE: The primary fix for ROLES_WITHOUT_2FA being redirected to
#   /accounts/2fa/authenticate/ lives in adapters.patch_is_mfa_enabled(),
#   called from AppConfig.ready() in apps.py.
#   _should_bypass_2fa() + unstash_login() here is a fallback safety net
#   for any residual pending-login session that might already exist.
#
from django.urls import reverse
from allauth.mfa.models import Authenticator
from allauth.account.utils import unstash_login  # replaces clear_login
from users.adapters import CustomMFAAdapter, ROLES_WITHOUT_2FA  # noqa: F401

EXEMPT_URLS = [
    "/accounts/",
    "/static/",
    "/media/",
    "/api/",
    "/admin/login/",
    "/admin/logout/",
    "/bamel/login/",
    "/bamel/logout/",
]


class Force2FAMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "FORCE_2FA_ENABLED", True):
            return self.get_response(request)

        # If the user must bypass 2FA but allauth has a pending MFA stage
        # stored in session, remove it to prevent an infinite redirect loop.
        # unstash_login() is the 0.58.0 equivalent of clear_login().
        if self._should_bypass_2fa(request.user):
            unstash_login(request)  # pops "account_login" from session
            return self.get_response(request)

        user = request.user
        if (
            user.is_authenticated
            and not getattr(user, "mfa_exempt", False)
            and hasattr(user, "role")
            and user.role not in ROLES_WITHOUT_2FA
            and not self._has_2fa(user)
            and not self._is_exempt(request.path)
        ):
            return redirect(reverse("mfa_activate_totp"))

        return self.get_response(request)

    def _should_bypass_2fa(self, user) -> bool:
        """
        Returns True if this user should not go through the MFA stage,
        even if an Authenticator exists in the database.
        """
        if not getattr(user, "is_authenticated", False):
            return False
        if not getattr(settings, "FORCE_2FA_ENABLED", True):
            return True
        if getattr(user, "mfa_exempt", False):
            return True
        if hasattr(user, "role") and user.role in ROLES_WITHOUT_2FA:
            return True
        return False

    def _has_2fa(self, user) -> bool:
        return Authenticator.objects.filter(
            user=user, type=Authenticator.Type.TOTP
        ).exists()

    def _is_exempt(self, path) -> bool:
        return any(path.startswith(url) for url in EXEMPT_URLS)