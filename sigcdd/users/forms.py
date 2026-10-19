from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):
        model = User

        error_messages = {
            "username": {"unique": _("This username has already been taken.")}
        }


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """
from django import forms
from phonenumber_field.formfields import PhoneNumberField
class ProfileForm(forms.ModelForm):
    #phone = PhoneNumberField(region="SN", label='Téléphone',required=False)
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


# ---------------------------------------------------------------------------
# Réinitialisation du mot de passe par SMS (OTP)
# ---------------------------------------------------------------------------
from django.contrib.auth.password_validation import validate_password


class SmsResetRequestForm(forms.Form):
    """Étape 1 : l'utilisateur saisit son identifiant."""

    username = forms.CharField(
        label=_("Identifiant"),
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": _("Votre identifiant"),
            "autofocus": True,
            "autocomplete": "username",
        }),
    )

    def clean_username(self):
        return self.cleaned_data["username"].strip()


class SmsResetOtpForm(forms.Form):
    """Étape 2 : l'utilisateur saisit le code reçu par SMS."""

    otp = forms.CharField(
        label=_("Code reçu par SMS"),
        max_length=10,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": _("Code à 6 chiffres"),
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
            "autofocus": True,
        }),
    )

    def clean_otp(self):
        otp = self.cleaned_data["otp"].strip()
        if not otp.isdigit():
            raise forms.ValidationError(_("Le code doit être numérique."))
        return otp


class SmsResetPasswordForm(forms.Form):
    """Étape 3 : l'utilisateur choisit son nouveau mot de passe."""

    password1 = forms.CharField(
        label=_("Nouveau mot de passe"),
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": _("Nouveau mot de passe"),
            "autocomplete": "new-password",
        }),
    )
    password2 = forms.CharField(
        label=_("Confirmer le mot de passe"),
        widget=forms.PasswordInput(attrs={
            "class": "form-control form-control-lg",
            "placeholder": _("Confirmer le mot de passe"),
            "autocomplete": "new-password",
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_("Les deux mots de passe ne correspondent pas."))
        return p2

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        if p1:
            # Applique les validateurs configurés dans AUTH_PASSWORD_VALIDATORS
            validate_password(p1, self.user)
        return cleaned




from allauth.mfa.forms import ActivateTOTPForm
from allauth.mfa import totp
from allauth.mfa.adapter import get_adapter

class ActivateTOTPNoEmailForm(ActivateTOTPForm):
    """Autorise l'activation TOTP sans e-mail vérifié."""
    def clean_code(self):
        code = self.cleaned_data["code"]
        if not totp.validate_totp_code(self.secret, code):
            raise get_adapter().validation_error("incorrect_code")
        return code