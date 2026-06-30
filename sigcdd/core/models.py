import datetime

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import Group
from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from helpers.commons import CommonHelper
from helpers.models import Person, Role, notif_by_sms,upload_directory_path
from helpers.templatetags.helpers_tags import propulseur_name
from helpers.validators import only_digit_validator
from phonenumber_field.modelfields import PhoneNumberField
from core.manager import *
from django.utils.html import format_html

from django_extensions.db.models import TimeStampedModel
from easy_thumbnails.fields import ThumbnailerImageField
from easy_thumbnails.files import get_thumbnailer
from easy_thumbnails.exceptions import InvalidImageFormatError
def logo_directory_path(instance, filename):
	return upload_directory_path("logo", filename)

class Structure(TimeStampedModel):
	ministere = models.ForeignKey('Ministere', verbose_name=_('ministere'), on_delete=models.SET_NULL,
	                              related_name="structures", null=True, blank=True)

	direction = models.ForeignKey('Direction', verbose_name=_('direction'), on_delete=models.SET_NULL, related_name="directions",null=True, blank=True)
	name = models.CharField(_('Nom'), max_length=250)
	reference = models.CharField(_('reference'), max_length=128,blank=True, null=True)
	logo = ThumbnailerImageField(_('logo'), blank=True, null=True, upload_to=logo_directory_path)
	city = models.CharField(_('Ville'), max_length=128, default="Dakar")
	street = models.CharField(_('Adresse'), max_length=128, null=True, blank=True)
	zip_code = models.CharField(_('Zip'), max_length=20, default="10200", editable=True)
	email = models.EmailField(_('Email'), max_length=128, null=True, blank=True)
	phone = models.CharField(_('Phone'), max_length=128, null=True, blank=True)
	class Meta:
		app_label = 'core'
		verbose_name = _('Structure')
		verbose_name_plural = _('Structure')

	def __str__(self):
		# noinspection PyPep8
		return "{}".format(self.name,)

	def get_thumbnail_url__(self):
		options = {'size': (120, 120), 'crop': True}
		if self.logo:
			thumb_url = get_thumbnailer(self.logo).get_thumbnail(options).url
			return thumb_url
		else:
			return ""

	def crop_image__(self):
		url = self.get_thumbnail_url()
		return format_html('<img src="{}"/>'.format(url))

	def crop_image(self):
		if self.teaser_image is None:
			return format_html("---")
		elif self.logo.url:
			v = """<img src="{}" alt="" title="">""".format(self.logo.url)
			return format_html(v)
		else:
			return format_html("---")

	def get_thumbnail_url(self):
		options = {'size': (120, 120), 'crop': True}
		if self.logo:
			try:
				thumb_url = get_thumbnailer(self.logo).get_thumbnail(options).url
				return thumb_url
			except InvalidImageFormatError:
				return ""
			except:
				return ""
		else:
			return ""




class CodeService(models.Model):
    name = models.CharField(_('Nom'), max_length=128)
    code = models.CharField(_('code'), max_length=6, unique=True,validators=[only_digit_validator])
    class Meta:
        app_label = 'core'
        verbose_name = _('Code Service')
        verbose_name_plural = _('Codes Services')

    def __str__(self):
        # noinspection PyPep8
        return u"%s"%(self.name,)

    def reference_for_cddaccount(self):
        if len(self.code) > 3:
	        raise ValueError("La taille du  code du secteur est superieur à 3 ")
        else:
	        return self.code


class Secteur(models.Model):
    name = models.CharField(_('Nom'), max_length=128)
    code = models.CharField(_('code'), max_length=6, unique=True,validators=[only_digit_validator])
    class Meta:
        app_label = 'core'
        verbose_name = _('Secteur')
        verbose_name_plural = _('Secteurs')

    def __str__(self):
        # noinspection PyPep8
        return u"%s"%(self.name,)

    def as_dict(self):
        return {
            "name": str(self.name),"id":self.pk
        }

    def reference_for_cddaccount(self):
	    if len(self.code) > 2:
		    raise ValueError("La taille du  code du secteur est superieur à 2 ")
	    else:
		    return self.code


class Agent(Person):
	matricule = models.CharField(_("Matricule"), max_length=50)
	user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='agent', on_delete=models.CASCADE)
	is_actif = models.BooleanField(_('Actif?'), default=False, )
	fonction = models.CharField(max_length=50, choices=Role.choices)
	phone = PhoneNumberField(_("Téléphone"), null=False, blank=False)
	email = models.EmailField("email",null=True, blank=True)

	class Meta:
		app_label = 'core'
		verbose_name = _('Agent')
		verbose_name_plural = _('Agents')
		abstract = True

	def format_roles(self):
		value = """<ul id="id_type_tax">"""
		for item in self.user.groups.all():
			a = """<li><a>{}</a></li>""".format(item.name)
			# noinspection PyPep8,PyPep8
			value += a
		value += """</ul>"""
		return format_html(value)

	def check_if_user_has_agent_role(self):
		for name in Role.names:
			if hasattr(self.user, name.lower()):
				return True
		return False

	def save(self, **kwargs):
		if hasattr(self,"user"):
			self.user.is_active = self.is_actif
			self.user.role = self.fonction
			#group, created = Group.objects.get_or_create(name=self.fonction)
			#self.user.groups.add(group)
			if self.user.force_change_pwd:
				self.user.is_active=True
			self.user.save()
		return super().save(**kwargs)

	def send_sms_message(self, password):
		message = self.get_message(password)
		try:
			notif_by_sms(self.phone.as_e164, message,email=self.email)
		except:
			import traceback
			traceback.print_exc()
			pass

	def get_message(self, password):
		compte = "Votre compte {} est actif".format(propulseur_name)
		identifiant = "Votre identifiant(NUIF) est  {}".format(self.matricule, )
		pwd = "Votre mot de passe est  {}".format(password, )
		site = "https://{}".format(Site.objects.get_current().domain, )
		message = "{}. {}. {}.  {}".format(compte, identifiant, pwd, site)
		return message

	def reset_pwd_for_agent(self, credentials):
		password = BaseUserManager().make_random_password(8)
		user = self.user
		user.set_password(password)
		user.save()
		compte = "Votre compte {} est actif".format(propulseur_name)
		identifiant = "Votre identifiant(NUIF) est  {}".format(self.matricule, )
		pwd = "Votre nouveau mot de passe est  {}".format(password, )
		site = "https://{}".format(Site.objects.get_current().domain, )
		message = "{}. {}. {} . {}".format(compte, identifiant, pwd, site)
		try:
			notif_by_sms(self.phone.as_e164, message,email=self.email)
		except:
			import traceback
			traceback.print_exc()
			pass


	def __str__(self):
		return "{} {} ".format(self.user, self.fonction)


from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver
#@receiver(post_save, sender=Agent)
def active_user_when_create(sender, **kwargs):
	instance = kwargs['instance']
	print("update s")
	if kwargs.get('created', True):
		user=instance.user
		user.is_active=True
		print("testetet")
		user.save()


class Region(models.Model):
    name = models.CharField(_('Nom'), max_length=128, unique=True)
    class Meta:
        app_label = 'core'
        verbose_name = _('Region')
        verbose_name_plural = _('Region')

    def __str__(self):
        # noinspection PyPep8
        return u"%s"%(self.name,)

    def as_dict(self):
        return {
            "name": str(self.name),"id":self.pk
        }



class Ministere(TimeStampedModel):
    name = models.CharField(_('Nom'), max_length=250)
    reference = models.CharField(_('référence'), max_length=6, unique=True)
    actif = models.BooleanField(_('En production?'), default=True)
    class Meta:
        app_label = 'core'
        verbose_name = _('Ministère')
        verbose_name_plural = _('Ministères')

    def __str__(self):
        # noinspection PyPep8
        return u"%s"%(self.name,)

    def as_dict(self):
        return {
            "name": str(self.name),"id":self.pk
        }

    def save(self, *args, **kwargs):
	    # self.pk = self.id = 1
	    if not self.reference:
		    try:
			    self.reference = CommonHelper.Instance().generate_code("core", "ministere", "reference", size=6)
		    except:
			    error = ValueError("A possible infinite loop was detected")
			    raise error
	    return super().save(*args, **kwargs)



class Direction(TimeStampedModel):
    name = models.CharField(_('Nom'), max_length=128)
    ministere = models.ForeignKey(Ministere, verbose_name=_('ministère'), on_delete=models.CASCADE, related_name="directions")
    reference = models.CharField(_('référence'), max_length=6, unique=True)

    class Meta:
        app_label = 'core'
        verbose_name = _('Direction')
        verbose_name_plural = _('Directions')

    def save(self, *args, **kwargs):
        # self.pk = self.id = 1
        if not self.reference:
	        try:
		        self.reference = CommonHelper.Instance().generate_code("core", "direction", "reference", size=6)
	        except:
		        error = ValueError("A possible infinite loop was detected")
		        raise error
        return super().save(*args, **kwargs)

    def __str__(self):
        # noinspection PyPep8
        return u"%s"%(self.name,)

    def as_dict(self):
        return {
            "name": str(self.name),"id":self.pk
        }
class Departement(models.Model):
    name = models.CharField(_('Nom'), max_length=128, unique=True)
    region = models.ForeignKey(Region, verbose_name=_('région'), on_delete=models.CASCADE, related_name="+")
    class Meta:
        app_label = 'core'
        verbose_name = _('Departement')
        verbose_name_plural = _('Departement')

    def __str__(self):
        # noinspection PyPep8
        return u"%s"%(self.name,)

    def as_dict(self):
        return {
            "name": str(self.name),"id":self.pk
        }


class DCP(TimeStampedModel):
	reference = models.CharField(_('référence'), max_length=6, unique=True)
	name = models.CharField(_('Non'), max_length=128)
	phone = models.CharField(_('Téléphone'), max_length=20)
	fax = models.CharField(_('Fax'), max_length=20, null=True, blank=True)
	email = models.CharField(_('Email'), max_length=128, null=True, blank=True)
	street = models.CharField(_('Adresse'), max_length=128, null=True, blank=True)
	zip_code = models.CharField(_('Zip'), max_length=20, null=True, blank=True)
	in_production = models.BooleanField(_('En production?'), default=False,
	                                    help_text=_('Activer si toute les configurations sont completes'))

	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True,
	                            blank=True)
	others = models.CharField(_('Autres'), max_length=20, null=True, blank=True)
	class Meta:
		app_label = 'core'
		verbose_name = _('Direction de la Comptabilité Publique')
		verbose_name_plural = _('Directions de la Comptabilité Publique')

	def get_dcp_id(self):
		return self.id

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.name,)

	@classmethod
	def object(cls):
		return cls._default_manager.all().first()  # Since only one item

	def save(self, *args, **kwargs):
		#self.pk = self.id = 1
		if not self.reference:
			try:
				self.reference = CommonHelper.Instance().generate_code("core", "dcp", "reference", size=6)
			except:
				error = ValueError("A possible infinite loop was detected")
				raise error
		return super().save(*args, **kwargs)


class PosteComptable(TimeStampedModel):
	dcp = models.ForeignKey(DCP, verbose_name=_('dcp'), on_delete=models.CASCADE, related_name="+")
	reference = models.CharField(_('Code'), max_length=6, unique=True,validators=[only_digit_validator])
	name = models.CharField(_('Nom'), max_length=128)
	phone = models.CharField(_('Téléphone'), max_length=20,null=True, blank=True)
	fax = models.CharField(_('Fax'), max_length=20, null=True, blank=True)
	email = models.EmailField(_('Email'), max_length=128, null=True, blank=True)
	street = models.CharField(_('Adresse'), max_length=128, null=True, blank=True)
	zip_code = models.CharField(_('Code postale'), max_length=20, null=True, blank=True)
	in_production = models.BooleanField(_('En production?'), default=False,
	                                    help_text=_('Activer si toute les configurations sont completes'))

	comptebanque = models.CharField(_('Compte bancaire Opérationnel'), max_length=128,null=True, blank=True)

	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL,null=True,blank=True)
	lon = models.FloatField(default=0)
	lat = models.FloatField(default=0)
	priorite=models.PositiveSmallIntegerField("Priorité",default=0)

	class TypePoste(models.TextChoices):
		TG = "TG", "TG"
		PGT = "PGT", "PGT"
		RGT = "RGT", "RGT"
		TPR = "TPR", "TPR"
		ACGP = "ACGP", "ACGP"
		TPE ="TPE","TPE"
		PERCEPTION="PERCEPTION","PERCEPTION"

	base_type = TypePoste.TG

	type = models.CharField(max_length=50, choices=TypePoste.choices)

	# ("reference","name","phone","email","fax","street","zip_code","created","in_production")
	objects=PosteComptableManager()

	class Meta:
		app_label = 'core'
		verbose_name = _('Poste Comptable')
		verbose_name_plural = _('Postes Comptable')

	@classmethod
	def defaultobject(cls):
		return cls._default_manager.all().first()  # Since only one item@classmethod


	def get_type_name(self):

		if self.type == self.TypePoste.TG: return  "Trésorier Général"
		elif self.type == self.TypePoste.RGT: return "Receveur Général"
		elif self.type == self.TypePoste.PGT: return "Payeur"
		elif self.type == self.TypePoste.ACGP: return "Agent Comptable des Grands Projets"
		elif self.type == self.TypePoste.TPR: return "Percepteur"
		else : return ""

	def reference_for_cddaccount(self):
		if len(self.reference) > 2:
			raise ValueError("Le code du poste comptable est superieur à 2 ")
		else: return self.reference

	def __str__(self):
		# noinspection PyPep8
		return "{} ".format(self.name,)

	def getLatLon(self):
		return {
			"lat": str(self.lat),
			"lon": str(self.lon)
		}

	def as_dict(self):
		data = {"reference": self.reference, "name": self.name, "phone": self.phone}
		if self.street:
			data["street"] = self.street
		if self.zip_code:
			data["zip_code"] = self.zip_code
		if self.email:
			data["email"] = self.email
		if self.in_production:
			data["in_production"] = self.in_production
		if self.created:
			data["created"] = self.created.isoformat()
		return data

	def create_poste_comptable_child(self):
		obj = None
		if self.type == PosteComptable.TypePoste.TPR:
			obj = TPR()
		elif self.type == PosteComptable.TypePoste.TG:
			obj = TG()
		elif self.type == PosteComptable.TypePoste.ACGP:
			obj = ACGP()
		elif self.type == PosteComptable.TypePoste.RGT:
			obj = RGT()
		elif self.type == PosteComptable.TypePoste.TG:
			obj = TG()
		if obj:
			obj.postecomptable_ptr=self
			obj.__dict__.update(self.__dict__)
			obj.created = datetime.datetime.now()
			obj.save()

	def latlon(self):
		return {"lat": self.lat, "lon": self.lon}

	def save(self, **kwargs):
		if not self.pk:
			self.created=datetime.datetime.now()
		if not self.reference:
			try:
				self.reference = CommonHelper.Instance().generate_code("core", "postecomptable", "reference", size=6)
			except:
				error = ValueError("A possible infinite loop was detected")
				raise error
		return super().save(**kwargs)


@receiver(post_save, sender=PosteComptable)
def create_pc_child(sender, **kwargs):
	instance = kwargs['instance']
	if kwargs.get('created', True):
		instance.create_poste_comptable_child()


class TG(PosteComptable):
	base_type = PosteComptable.TypePoste.TG


	class Meta:
		app_label = 'core'
		verbose_name = _('Trésorerie Générale')
		verbose_name_plural = _('Trésorerie Générale')

	def get_trgen_id(self):
		return self.id

	@classmethod
	def object(cls):
		return cls._default_manager.all().first()  # Since only one item

	def save(self, *args, **kwargs):
		if not self.pk:
			self.created=datetime.datetime.now()
		return super().save(*args, **kwargs)


	def get_trgen_info(self):
		return [self.id, str(self.name).upper()]


class PGT(PosteComptable):
	base_type = PosteComptable.TypePoste.PGT

	class Meta:
		app_label = 'core'
		verbose_name = _('Paierie Générale du Trésor')
		verbose_name_plural = _('Paierie Générale du Trésor')

	def get_paieriegen_id(self):
		return self.id

	@classmethod
	def object(cls):
		return cls._default_manager.all().first()  # Since only one item

	def save(self, *args, **kwargs):
		if not self.pk:
			self.created=datetime.datetime.now()

		return super().save(*args, **kwargs)

	def get_paieriegen_info(self):
		return [self.id, str(self.name).upper()]


class RGT(PosteComptable):
	base_type = PosteComptable.TypePoste.RGT

	class Meta:
		app_label = 'core'
		verbose_name = _('Recette Générale du Trésor ')
		verbose_name_plural = _('Recette Générale du Trésor ')

	def get_recettegen_id(self):
		return self.id

	def save(self, **kwargs):
		if not self.pk:
			self.created=datetime.datetime.now()
		if not self.reference:
			try:
				self.reference = CommonHelper.Instance().generate_code("core", "rgt", "reference", size=6)
			except:
				error = ValueError("A possible infinite loop was detected")
				raise error
		return super().save(**kwargs)

	def get_recettegen_info(self):
		return [self.id, str(self.name).upper()]



class ACGP(PosteComptable):
	base_type = PosteComptable.TypePoste.ACGP

	class Meta:
		app_label = 'core'
		verbose_name = _('Agence Comptable des Grands Projets')
		verbose_name_plural = _('Agence Comptable des Grands Projets')

	def get_acgp_id(self):
		return self.id

	@classmethod
	def object(cls):
		return cls._default_manager.all().first()  # Since only one item

	def save(self, *args, **kwargs):
		if not self.pk:
			self.created=datetime.datetime.now()

		return super().save(*args, **kwargs)

	def get_acgp_info(self):
		return [self.id, str(self.name).upper()]


class TPR(PosteComptable):
	base_type = PosteComptable.TypePoste.TPR
	region = models.ForeignKey(Region, verbose_name=_('Région'), on_delete=models.SET_NULL, related_name="+",blank=True,null=True)

	class Meta:
		app_label = 'core'
		verbose_name = _('Trésorerie Paierie Régionale')
		verbose_name_plural = _('Trésorerie Paierie Régionale')

	def get_tpr_id(self):
		return self.id

	@classmethod
	def object(cls):
		return cls._default_manager.all().first()  # Since only one item

	def save(self, *args, **kwargs):
		if not self.pk:
			self.created=datetime.datetime.now()

		return super().save(*args, **kwargs)

	def get_tpr_info(self):
		return [self.id, str(self.name).upper()]








from datetime import timedelta
from django.contrib.postgres.fields import DateRangeField
from psycopg2.extras import DateRange


class ProfileDCP(Agent):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='agent_dcp',on_delete=models.CASCADE)
    dcp = models.ForeignKey(DCP, verbose_name=_('dcp'), on_delete=models.CASCADE, related_name="+")

    class Meta:
        app_label = 'core'
        verbose_name = _('Agent DCP')
        verbose_name_plural = _('Agent DCP')
    def save(self, **kwargs):
	    self.fonction=Role.AGENT_DCP
	    return super().save(**kwargs)

post_save.connect(active_user_when_create, sender=ProfileDCP)
class ProfilePC(Agent):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='agent_postecomptable', on_delete=models.CASCADE)
	poste = models.ForeignKey(PosteComptable, verbose_name=_('Poste  comptable'), on_delete=models.CASCADE, related_name="+")
	is_master = models.BooleanField(_('Est master?'), default=False, )

	objects=ProfilePCManager()

	class Meta:
		app_label = 'core'
		verbose_name = _('Agent Poste Comptable')
		verbose_name_plural = _('Agent Poste Comptable')

	def save(self, **kwargs):
		self.fonction=Role.AGENT_PC
		return super().save(**kwargs)

	def __str__(self):
		return "{} ({} {})".format(self.user, self.firstname,self.lastname)

post_save.connect(active_user_when_create, sender=ProfilePC)

class AffectationAgent(TimeStampedModel):
	period = DateRangeField("Periode",help_text="Merci d'utiliser ce format: <em>YYYY-MM-DD</em>.")
	creator = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('createur'), on_delete=models.CASCADE, related_name="+")
	agent = models.ForeignKey(ProfilePC, verbose_name=_('agent poste comptable'), on_delete=models.CASCADE, related_name="affectations")
	poste = models.ForeignKey(PosteComptable, verbose_name=_('poste comptable'), on_delete=models.CASCADE,
	                                   related_name="+")
	name = models.CharField(_('Nom'), max_length=128)
	actif = models.BooleanField(_('Actif?'), default=True)

	class Meta:
		app_label = 'core'
		verbose_name = _('Affectation')
		verbose_name_plural = _('Affectations')

	def format_period(self):
		a = "{} {}".format(self.period.lower.strftime('%Y-%m-%d'), self.period.upper.strftime('%Y-%m-%d')) if self.period else "----"
		return a


	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.id,)

	def save(self, *args, **kwargs):
		if self.name  is None:
			self.name = "{} period ({} {})".format(self.poste.name, self.period.lower.strftime('%Y-%m-%d'),
			                                      self.period.upper.strftime('%Y-%m-%d'))
		if self.actif is True:
			self.__class__._default_manager.filter(agent_id=self.agent_id,poste_id=self.poste_id, actif=True).update(actif=False)
		lower_date = self.period.lower

		rg = DateRange(lower_date, lower_date + timedelta(days=1))
		if self.__class__._default_manager.filter(agent_id=self.agent_id,poste_id=self.poste_id, period__contains=rg).exclude(
				id=self.id).exists():
			raise Exception("Une affectation existe sur cette periode pour cet agent")
		super().save(*args, **kwargs)



class Prestataire(TimeStampedModel):
	reference = models.CharField(_('Ninéa'), max_length=128, unique=True)
	name = models.CharField(_('Nom'), max_length=128)
	phone = models.CharField(_('Téléphone'), max_length=20)
	#comptes = models.ManyToManyField(_('Telephone'), max_length=20)
	fax = models.CharField(_('Fax'), max_length=20, null=True, blank=True)
	email = models.CharField(_('Email'), max_length=128, null=True, blank=True)
	street = models.CharField(_('Adresse'), max_length=128, null=True, blank=True)
	zip_code = models.CharField(_('Zip'), max_length=20, null=True, blank=True)
	in_production = models.BooleanField(_('En production?'), default=False,
	                                    help_text=_('Activer si toute les configurations sont completes'))

	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True,
	                            blank=True)
	others = models.CharField(_('Autres'), max_length=20, null=True, blank=True)
	class Meta:
		app_label = 'core'
		verbose_name = _('Direction de la Comptabilité Publique')
		verbose_name_plural = _('Directions de la Comptabilité Publique')

	def get_dcp_id(self):
		return self.id

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.name,)

	@classmethod
	def object(cls):
		return cls._default_manager.all().first()  # Since only one item

	def save(self, *args, **kwargs):
		#self.pk = self.id = 1
		if not self.reference:
			try:
				self.reference = CommonHelper.Instance().generate_code("core", "dcp", "reference", size=6)
			except:
				error = ValueError("A possible infinite loop was detected")
				raise error
		return super().save(*args, **kwargs)






class ConfigurationOTP(TimeStampedModel):

	validation_op = models.BooleanField("Validation OP",default=True)
	#validation_op = models.BooleanField("Validation OP", default=True)
	#validation_op = models.BooleanField("Validation OP", default=True)

	class Meta:
		app_label = 'core'
		verbose_name = _('Configuration OTP')

	@classmethod
	def object(cls):
		return cls._default_manager.all().first()  # Since only one item

	def __str__(self):
		return "{}".format(self.id,)