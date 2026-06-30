from django.contrib.auth.models import AbstractUser,BaseUserManager
from django.db.models import CharField
from django.urls import reverse

from helpers.models import Role
from helpers.exceptions import SigException

from django.db import models
class User(AbstractUser):
    """
    Default custom user model for nasr.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    base_role = Role.SIMPLE

    role = models.CharField(max_length=50, choices=Role.choices)
    force_change_pwd = models.BooleanField("Change pwd ?", default=False)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.role = self.base_role
        return super().save(*args, **kwargs)

    def full_name(self):
        return '{} {}'.format(self.first_name, self.last_name)

    def get_absolute_url(self):
        """Get url for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})

    @property
    def nin(self):
        if self.role==Role.AGENT_PC:
            if hasattr(self,"agent_postecomptable"):
                return self.agent_postecomptable.nin
        elif self.role==Role.GERANT:
            if hasattr(self,"gerant_cd"):
                return  self.gerant_cd.nin


        elif self.role==Role.AGENT_SAISIE_CD:
            if hasattr(self,"agent_saisie_cd"):
                return   self.agent_saisie_cd.nin


        elif self.role==Role.AGENT_DCP:
            if hasattr(self,"agent_dcp"):
                return  self.agent_dcp.nin
        elif self.role==Role.AGENT_DAP:
            if hasattr(self,"agent_dap"):
                return  self.agent_dap.nin

        return ""

    @property
    def phone(self):
        if self.role == Role.AGENT_PC:
            if hasattr(self, "agent_postecomptable"):
                return self.agent_postecomptable.phone
        elif self.role == Role.GERANT:
            if hasattr(self, "gerant_cd"):
                return self.gerant_cd.phone


        elif self.role == Role.AGENT_SAISIE_CD:
            if hasattr(self, "agent_saisie_cd"):
                return self.agent_saisie_cd.phone


        elif self.role == Role.AGENT_DCP:
            if hasattr(self, "agent_dcp"):
                return self.agent_dcp.phone
        elif self.role == Role.AGENT_DAP:
            if hasattr(self, "agent_dap"):
                return self.agent_dap.phone

        return ""


    def get_open_accountting_day(self):
        if self.has_perm('cddaccount.use_anneecomptable'):
            a=self.journee_comptables.filter(actif=True).last()
            if a:
                return a.format_name()
            else: return "Merci de choisir votre journée comptable de travail!"
        else : return ""


    def get_agent_name(self):
        if self.role==Role.AGENT_PC:
            if hasattr(self,"agent_postecomptable"):
                return "AGENT PC : {}".format(self.full_name())
        elif self.role==Role.GERANT:
            if hasattr(self,"gerant_cd"):
                return  "GERANT : {}".format(self.full_name())

        elif self.role==Role.AGENT_SAISIE_CD:
            if hasattr(self,"agent_saisie_cd"):
                return  "AGENT SAISIE : {}".format(self.full_name())

        elif self.role==Role.AGENT_DCP:
            if hasattr(self,"agent_dcp"):
                return  "AGENT DCP : {}".format(self.full_name())
        elif self.role==Role.AGENT_DAP:
            if hasattr(self,"agent_dap"):
                return  "AGENT DAP : {}".format(self.full_name())

        elif self.role==Role.ADMIN:
            return  "DI : {}".format(self.full_name())

        else :return ""


    def get_structure_name(self):
        if self.role==Role.AGENT_PC:
            if hasattr(self,"agent_postecomptable"):
                return "{}".format(self.agent_postecomptable.poste.name.upper())
        elif self.role==Role.GERANT:
            if hasattr(self,"gerant_cd"):
                if self.gerant_cd.structure:
                    return "Structure : {}".format(self.gerant_cd.structure.name.upper())
                return  ""

        elif self.role==Role.AGENT_SAISIE_CD:
            if hasattr(self,"agent_saisie_cd"):
                return  ""

        elif self.role==Role.AGENT_DCP:
            if hasattr(self,"agent_dcp"):
                return "{}".format(self.agent_dcp.dcp.name.upper())
        elif self.role==Role.AGENT_DAP:
            if hasattr(self,"agent_dap"):
                return "{}".format(self.agent_dap.dap.name.upper())

        elif self.role==Role.ADMIN:
            return  "DIRECTION INFORMATIQUE"

        else :return ""

    def get_agent(self):
        if self.role==Role.AGENT_PC:
            if hasattr(self,"agent_postecomptable"):
                return self.agent_postecomptable
            else :raise SigException("","l'utilisateur n'est pas agent poste comptable")
        elif self.role==Role.GERANT:
            if hasattr(self,"gerant_cd"):
                return self.gerant_cd
            else :raise SigException("","l'utilisateur n'est pas gerant de compte")

        elif self.role==Role.AGENT_SAISIE_CD:
            if hasattr(self,"agent_saisie_cd"):
                return self.agent_saisie_cd
            else :raise SigException("","l'utilisateur n'est pas agent de saisie de compte")

        elif self.role==Role.AGENT_DCP:
            if hasattr(self,"agent_dcp"):
                return self.agent_dcp
            else :raise SigException("","l'utilisateur n'est pas agent DCP")

        elif self.role==Role.ADMIN:
            return self

        else :raise SigException("","l'utilisateur non connu")

    @property
    def badge_class(self):
        if self.role == Role.AGENT_PC:
            if hasattr(self, "agent_postecomptable"):
                return "live_notify_badge_pc"
        elif self.role == Role.GERANT:
            if hasattr(self, "gerant_cd"):
                return "live_notify_badge_gerant"

        return ""






class SimpleManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=Role.SIMPLE)


class SimpleUser(User):

    base_role = Role.SIMPLE

    objects = SimpleManager()

    class Meta:
        proxy = True

    def welcome(self):
        return "Only for simple user"


class AdminManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=Role.ADMIN)


class AdminUser(User):

    base_role = Role.ADMIN

    objects = AdminManager()

    class Meta:
        proxy = True

    def welcome(self):
        return "Only for admin user"


class GestionaireCDManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=Role.GERANT)


class GestionnaireCD(User):
    base_role = Role.GERANT
    objects = GestionaireCDManager()

    class Meta:
        proxy = True

    def welcome(self):
        return "Only for getionnaire user"


class AgentSigManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=User.Role.AGENT_DCP)


class AgentSig(User):
    base_role = Role.AGENT_DCP
    objects = AgentSigManager()

    class Meta:
        proxy = True

    def welcome(self):
        return "Only for agent  sig user"



# Create your models here.
from allauth.account.signals import password_changed,password_set,user_logged_in,user_logged_out
from django.dispatch import receiver



@receiver(password_set)
def set_user_password_set(sender, request, *args, **kwargs):
    print("pwd set")
    user =request.user
    user.force_change_pwd=False
    user.save()
    print("pwd set")

@receiver(password_changed)
def set_user_password_changer(sender, request, *args, **kwargs):
    print("pwd changed")
    user =request.user
    user.force_change_pwd=False
    user.save()
    print("pwd changed")


from django.contrib.auth.signals import user_logged_out


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    try:
        del request.session["select_cddacc_user_id"]
    except KeyError:
        pass