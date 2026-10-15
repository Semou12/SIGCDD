from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView

from users.forms import ProfileForm

User = get_user_model()

from django.http import Http404

class UserDetailView(LoginRequiredMixin, DetailView):

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_success_url(self):
        return reverse("users:home_view")


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = User
    #fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self):
        assert (
            self.request.user.is_authenticated
        )  # for mypy to know that the user is authenticated
        return self.request.user.get_absolute_url()

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        #return reverse("users:detail", kwargs={"username": self.request.user.username})
        return reverse("users:home_view")



user_redirect_view = UserRedirectView.as_view()


from helpers.models import Role
@login_required
def home_view(request):
    user = request.user
    if user.last_login is None:
        #change password
        url = redirect(reverse("account_change_password"))
        return url

    if request.user.is_superuser:
        return redirect(reverse("admin:index"))

    elif user.role == Role.ADMIN:
        url_path = reverse('core:dcp_list')
        url = redirect(url_path)
        return url

    elif user.role == Role.AGENT_TG:
        url_path = reverse('core:dash_tg_view')
        url = redirect(url_path)
        return url

    elif user.role == Role.AGENT_DS:
        url_path = reverse('core:dash_ds_view')
        url = redirect(url_path)
        return url

    elif user.role == Role.SIMPLE:
        url_path = reverse('users:user_simple_view')
        url = redirect(url_path)
        return url


    elif hasattr(user, "agent_dcp") == True:
        poste_id = user.agent_dcp
        url_path = reverse('cddaccount:comptedepot_list')
        url = redirect(url_path)
        return url

    elif hasattr(user, "agent_dap") == True:
        poste_id = user.agent_dap
        url_path = reverse('bankcheck:dap_list')
        url = redirect(url_path)
        return url

    elif hasattr(user, "agent_postecomptable") == True:
        poste_id = user.agent_postecomptable.poste_id
        url_path = reverse('core:dash_postcomptable_view',kwargs={"poste_id":poste_id})
        url = redirect(url_path)
        return url

    elif hasattr(user, "gerant_cd") == True:
        url_path = user.gerant_cd.get_absolute_url()
        url = redirect(url_path)
        return url

    elif hasattr(user, Role.AGENT_SAISIE_CD.lower()) == True:
        url_path = user.agent_saisie_cd.get_absolute_url()
        url = redirect(url_path)
        return url

    else:
        raise Http404


from allauth.account.views import PasswordChangeView
class SigcddPasswordChangeView(LoginRequiredMixin,PasswordChangeView):

    def get_success_url(self):
        """
        Return the URL to redirect to after processing a valid form.

        Using this instead of just defining the success_url attribute
        because our url has a dynamic element.
        """
        #success_url = reverse("users:detail", kwargs={"username": self.request.user.username})
        success_url = reverse("users:home_view")

        return success_url


from django.shortcuts import render, redirect
from django.contrib import messages


@login_required
def profile_view(request):
    template = "users/profile.html"
    user = request.user
    initial = {"email":user.email,"first_name":user.first_name,"last_name":user.last_name}
    if request.method == 'POST':
        form = ProfileForm(request.POST, )
        if form.is_valid():
            user.first_name=form.cleaned_data["first_name"]
            user.last_name = form.cleaned_data["last_name"]
            user.email = form.cleaned_data["email"]
            user.save()
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")

    else:
        form = ProfileForm(initial=initial)

    context = {"form": form, }
    return render(request, template, context)


@login_required
def user_simple_view(request):
    template="users/simple.html"
    return render(request, template, {})


# ===========================================================================
# Réinitialisation du mot de passe par SMS (OTP) — canal alternatif à l'e-mail
# Étapes : identifiant -> code OTP par SMS -> choix du nouveau mot de passe.
# ===========================================================================
import time

from helpers.models import SimpleOtp
from helpers.commons import OTP_STEP_IN_MIN
from users.forms import SmsResetRequestForm, SmsResetOtpForm, SmsResetPasswordForm

SMS_RESET_SESSION_KEY = "sms_pwd_reset"
SMS_RESET_FLOW_TTL = 600        # durée de vie du flux complet (10 min)
SMS_RESET_MAX_ATTEMPTS = 5      # tentatives de code avant invalidation


def _user_phone_str(user):
    """Retourne le téléphone du profil sous forme de chaîne (e164 si possible)."""
    raw = getattr(user, "phone", "") or ""
    try:
        phone = raw.as_e164  # PhoneNumberField
    except AttributeError:
        phone = str(raw)
    return (phone or "").strip()


def _mask_phone(phone):
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) <= 4:
        return "•" * len(digits)
    return digits[:2] + "•" * (len(digits) - 4) + digits[-2:]


def _reset_state(request):
    return request.session.get(SMS_RESET_SESSION_KEY)


def _clear_reset_state(request):
    request.session.pop(SMS_RESET_SESSION_KEY, None)


def sms_reset_password_request(request):
    """Étape 1 : saisie de l'identifiant, envoi de l'OTP par SMS."""
    template = "account/password_reset_sms.html"
    if request.method == "POST":
        form = SmsResetRequestForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            user = User.objects.filter(username=username, is_active=True).first()
            phone = _user_phone_str(user) if user else ""
            if user and phone:
                otp = SimpleOtp()
                otp.phone = phone
                otp.generate_otp()
                otp.message = (
                    "SIGCDD : votre code de reinitialisation de mot de passe est {}. "
                    "Il expire dans {} min.".format(otp.otp, OTP_STEP_IN_MIN)
                )
                otp.save()
                otp.send_otp()
                request.session[SMS_RESET_SESSION_KEY] = {
                    "uid": user.id,
                    "otp_ref": otp.reference,
                    "phone_mask": _mask_phone(phone),
                    "started_at": time.time(),
                    "verified": False,
                    "attempts": 0,
                }
                request.session.modified = True
                return redirect(reverse("account_reset_password_sms_verify"))
            # Identifiant inconnu ou sans téléphone : message explicite (outil interne)
            messages.error(
                request,
                _("Identifiant inconnu ou aucun numéro de téléphone associé à ce compte."),
                extra_tags="danger",
            )
    else:
        form = SmsResetRequestForm()
    return render(request, template, {"form": form})


def sms_reset_password_verify(request):
    """Étape 2 : vérification du code OTP."""
    template = "account/password_reset_sms_verify.html"
    state = _reset_state(request)
    if not state or (time.time() - state.get("started_at", 0)) > SMS_RESET_FLOW_TTL:
        _clear_reset_state(request)
        messages.error(request, _("Session expirée, merci de recommencer."), extra_tags="danger")
        return redirect(reverse("account_reset_password_sms"))

    if request.method == "POST":
        if state.get("attempts", 0) >= SMS_RESET_MAX_ATTEMPTS:
            _clear_reset_state(request)
            messages.error(request, _("Trop de tentatives. Merci de recommencer."), extra_tags="danger")
            return redirect(reverse("account_reset_password_sms"))

        form = SmsResetOtpForm(request.POST)
        if form.is_valid():
            otp_obj = SimpleOtp.objects.filter(reference=state["otp_ref"]).first()
            if otp_obj and otp_obj.verify(form.cleaned_data["otp"]):
                state["verified"] = True
                request.session[SMS_RESET_SESSION_KEY] = state
                request.session.modified = True
                return redirect(reverse("account_reset_password_sms_set"))
            state["attempts"] = state.get("attempts", 0) + 1
            request.session[SMS_RESET_SESSION_KEY] = state
            request.session.modified = True
            messages.error(request, _("Code invalide ou expiré."), extra_tags="danger")
    else:
        form = SmsResetOtpForm()
    return render(request, template, {"form": form, "phone_mask": state.get("phone_mask")})


def sms_reset_password_set(request):
    """Étape 3 : choix du nouveau mot de passe (uniquement si OTP vérifié)."""
    template = "account/password_reset_sms_set.html"
    state = _reset_state(request)
    if (not state or not state.get("verified")
            or (time.time() - state.get("started_at", 0)) > SMS_RESET_FLOW_TTL):
        _clear_reset_state(request)
        messages.error(request, _("Session expirée ou non vérifiée, merci de recommencer."), extra_tags="danger")
        return redirect(reverse("account_reset_password_sms"))

    user = User.objects.filter(id=state["uid"], is_active=True).first()
    if not user:
        _clear_reset_state(request)
        messages.error(request, _("Compte introuvable."), extra_tags="danger")
        return redirect(reverse("account_reset_password_sms"))

    if request.method == "POST":
        form = SmsResetPasswordForm(request.POST, user=user)
        if form.is_valid():
            user.set_password(form.cleaned_data["password1"])
            user.force_change_pwd = False
            user.save()
            # Invalide l'OTP et nettoie la session
            SimpleOtp.objects.filter(reference=state["otp_ref"]).delete()
            _clear_reset_state(request)
            messages.success(request, _("Mot de passe réinitialisé. Vous pouvez vous connecter."))
            return redirect(reverse("account_login"))
        for field in form:
            for error in field.errors:
                messages.error(request, "{} ({})".format(error, field.label), extra_tags="danger")
    else:
        form = SmsResetPasswordForm(user=user)
    return render(request, template, {"form": form})