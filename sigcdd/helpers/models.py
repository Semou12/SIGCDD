from __future__ import unicode_literals

import hashlib
import hmac
import random
import string
import time
from binascii import unhexlify
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from easy_thumbnails.fields import ThumbnailerImageField
from easy_thumbnails.files import get_thumbnailer
from helpers import SexeType, TypePiece
from django_otp.oath import TOTP
from  datetime import date

def upload_directory_path(path, filename):
	ext = filename.split('.')[-1]
	chars = string.ascii_uppercase + string.digits
	rand_strings = ''.join(random.choice(chars) for i in range(10))
	filename = '{}/{}_{}.{}'.format(path, rand_strings, uuid4().hex, ext)
	return filename


def justificatif_directory_path(instance, filename):
	return upload_directory_path("justificatif", filename)

def virmasse_directory_path(instance, filename):
	return upload_directory_path("vrmasse", filename)


def cin_directory_path(instance, filename):
	return upload_directory_path("cin", filename)


def structures_directory_path(instance, filename):
	return upload_directory_path("structures", filename)


def photo_directory_path(instance, filename):
	return upload_directory_path("photos", filename)


def signature_directory_path(instance, filename):
	return upload_directory_path("signatures", filename)


def empreinte_directory_path(instance, filename):
	return upload_directory_path("empreintes", filename)


def piece_directory_path(instance, filename):
	return upload_directory_path("pieces", filename)





class Role(models.TextChoices):
	ADMIN = "ADMIN", "DI"
	AGENT_DCP = "AGENT_DCP", "Agent DCP"
	AGENT_PC = "AGENT_PC", "Agent Poste Comptable"
	AGENT_DAP = "AGENT_DAP","Agent DAP"
	AGENT_TG = "AGENT_TG", "Agent TG"
	AGENT_DS = "AGENT_DS", "Agent DS"
	GERANT = "GERANT", "Gerant"
	SIMPLE = "SIMPLE", "Simple"
	AGENT_SAISIE_CD = "AGENT_SAISIE_CD", "AGENT DE SAISIE COMPTE DEPOT"
	AGENT_SAISIE_PC = "AGENT_SAISIE_PC", "AGENT DE SAISIE POSTE COMPTABLE"

from django.contrib.auth.models import Group

class SigRole(TimeStampedModel):
	groups = models.ManyToManyField(Group)
	role = models.CharField(max_length=50, choices=Role.choices,unique=True)
	class Meta:
		app_label = "helpers"
		verbose_name = _("sigcc group/role")



class Person(TimeStampedModel):
	firstname = models.CharField(_('Prénom'), max_length=80)
	lastname = models.CharField(_('Nom'), max_length=80)
	nin = models.CharField("Numéro_identité", max_length=128, null=True, blank=True)
	cedeao_numero = models.CharField("Numéro cedeao", max_length=128, null=True, blank=True)

	adresse = models.CharField(_('Adresse'), max_length=128, null=True, blank=True)
	age = models.IntegerField(_('Age'), default=10, editable=False)
	dob = models.DateField(_('Date Naissance'), max_length=12, default=timezone.now)
	lieu_dob = models.CharField(_('Lieu Naissance'), max_length=50, null=True, blank=True)
	sexe = models.CharField(_('Sexe'), max_length=10, choices=SexeType.CHOICES, default=SexeType.H)
	teaser_image = ThumbnailerImageField(_('photo'), blank=True, null=True, upload_to=photo_directory_path)
	teaser_signature = ThumbnailerImageField(_('signature'), blank=True, null=True, upload_to=signature_directory_path)
	teaser_empreinte = ThumbnailerImageField(_('Empreinte 1'), blank=True, null=True,
	                                         upload_to=signature_directory_path)

	fingerprint2B64 = ThumbnailerImageField(_('Empreinte 2'), blank=True, null=True, upload_to=signature_directory_path)
	piece_recto = ThumbnailerImageField(_('Piece Recto'), blank=True, null=True, upload_to=piece_directory_path)
	piece_verso = ThumbnailerImageField(_('Piece verso'), blank=True, null=True, upload_to=piece_directory_path)

	type_piece = models.CharField(_('type'), max_length=20, choices=TypePiece.CHOICES, default=TypePiece.CNI)

	date_expiration = models.DateField(_('Date Expriration'), max_length=12, null=True, blank=True)
	date_delivrance = models.DateField(_('Date delivrance'), max_length=12, null=True, blank=True)

	mother_firstname = models.CharField(_('Prenom mere'), max_length=128, null=True, blank=True)
	mother_lastname = models.CharField(_('Nom mere'), max_length=128, null=True, blank=True)
	father_firstname = models.CharField(_('Prenom pere'), max_length=128, null=True, blank=True)
	father_lastname = models.CharField(_('Nom pere'), max_length=128, null=True, blank=True)

	#("father_lastname","father_firstname","mother_lastname","mother_firstname","date_delivrance","date_expiration","type_piece","piece_verso","piece_recto","fingerprint2B64","teaser_empreinte","cedeao_numero")

	class Meta:
		app_label = "helpers"
		abstract = True

	def __str__(self):
		return "{} {}".format(self.nin, self.type_piece)

	def full_name(self):
		return '{} {}'.format(self.firstname, self.lastname)

	def pere(self):
		return '{} {}'.format(self.father_firstname, self.father_lastname)

	def mere(self):
		return '{} {}'.format(self.mother_firstname, self.mother_lastname)

	def is_valid(self):
		if not self.is_process:
			return self.reference
		else:
			return True

	def format_cin(self):
		if len(self.nin) == 13:
			return "{} {} {} {}".format(self.nin[0], self.nin[1:4], self.nin[4:8], self.nin[8:13])
		else:
			return self.nin

	def get_thumbnail_url(self):
		options = {'size': (120, 120), 'crop': True}
		if self.teaser_image:
			thumb_url = get_thumbnailer(self.teaser_image).get_thumbnail(options).url
			return thumb_url
		else:
			return ""

	def get_thumbnail_signature_url(self):
		options = {'size': (120, 120), 'crop': True}
		if self.teaser_signature:
			thumb_url = get_thumbnailer(self.teaser_signature).get_thumbnail(options).url
			return thumb_url
		else:
			return ""

	def render_signature(self, ):
		img_path = ""
		s = "<p>--</p>"
		if self.teaser_signature:
			c=self.get_thumbnail_signature_url()
			url=self.teaser_signature.url
			s = f"""
	        <div class="d-block flex-shrink-0">
	                                            <a href= "{url}"><img src="{c}" class="img-fluid img-thumbnail" alt=""></a>
	                                        </div>
	        """
		return format_html(s)

	def get_thumbnail_empreinte_url(self):
		options = {'size': (120, 120), 'crop': True}
		if self.teaser_empreinte:
			thumb_url = get_thumbnailer(self.teaser_empreinte).get_thumbnail(options).url
			return thumb_url
		else:
			return ""

	def get_thumbnail_fingerprint2B64_url(self):
		options = {'size': (120, 120), 'crop': True}
		if self.teaser_empreinte:
			thumb_url = get_thumbnailer(self.fingerprint2B64).get_thumbnail(options).url
			return thumb_url
		else:
			return ""

	def get_thumbnail_piece_recto_url(self):
		options = {'size': (120, 120), 'crop': True}
		if self.piece_recto:
			thumb_url = get_thumbnailer(self.piece_recto).get_thumbnail(options).url
			return thumb_url
		else:
			return ""

	def get_thumbnail_piece_verso_url(self):
		options = {'size': (120, 120), 'crop': True}
		if self.piece_verso:
			thumb_url = get_thumbnailer(self.piece_verso).get_thumbnail(options).url
			return thumb_url
		else:
			return ""

	def crop_image(self):
		url = self.get_thumbnail_url()
		return format_html('<img src="{}"/>'.format(url))

	def get_age(self):
		days = date.today() - self.dob
		return days.days // 365

	crop_image.allow_tags = True
	# noinspection PyPep8
	crop_image.short_description = _('Logo')


class Application(models.Model):
	name = models.CharField(_("Nom"), max_length=50, unique=True)
	app_key = models.CharField(
		_("App key"), max_length=128, unique=True, editable=False
	)

	class Meta:
		app_label = "helpers"
		verbose_name = _("Application")
		verbose_name_plural = _("Applications")

	def __str__(self):
		return "%s" % (self.name,)

	def save(self, *args, **kwargs):
		if not self.app_key:
			self.app_key = self._generate_reference()
		super(Application, self).save(*args, **kwargs)

	def _generate_reference(self):
		key = settings.SECRET_KEY
		msg = str(int(time.time()))
		obj = hmac.new(
			key=key.encode("utf-8"), msg=msg.encode("utf-8"), digestmod=hashlib.sha256
		)
		return obj.hexdigest().upper()


class SmsSetting(models.Model):
	status = models.BooleanField(_("Activer ?"), default=False)
	mode = models.BooleanField(_("En prod ?"), default=False)
	sandbox = models.JSONField(_("Sandbox"), null=True, blank=True)
	live = models.JSONField(_("Live"), null=True, blank=True)

	class Meta:
		app_label = "helpers"
		verbose_name = _("Configuration SMS")
		verbose_name_plural = _("Configurations SMS")

	def __str__(self):
		return "{}".format(
			self.id,
		)


from .commons import CommonHelper,OTP_STEP,OTP_STEP_IN_MIN


def notif_by_sms(phone, message,email=None):
	sms_setting = SmsSetting.objects.last()
	if sms_setting and sms_setting.status == True:
		configs=None
		try:
			if sms_setting.mode and sms_setting.live:
				if sms_setting.live is not None:
					configs = sms_setting.live["credentials"]
			else:
				if sms_setting.sandbox is not None:
					configs = sms_setting.sandbox["credentials"]
			sms_obj = Sms()
			sms_obj.phone = phone
			sms_obj.content = message
			sms_obj.config = configs
			if email:
				sms_obj.email=email
			sid = int(time.time())
			sms_obj.sid = sid
			sms_obj.save()
			if sms_setting.status and configs is not None:

				CommonHelper.Instance().send_sms(phone, message, configs)
				if email:

					CommonHelper.Instance().send_html_email("Notification", message, [email])

		except:
			import traceback
			traceback.print_exc()
			pass


class Currency(models.Model):
	"""Model holds a currency information for a nationality"""
	code = models.CharField(max_length=3, unique=True)
	name = models.CharField(max_length=64)

	class Meta:
		app_label = 'helpers'
		verbose_name_plural = 'currencies'

	def __str__(self):
		return self.code


class ExchangeRate(models.Model):
	"""Model to persist exchange rates between currencies"""
	source = models.ForeignKey(Currency, related_name='rates', on_delete=models.CASCADE)
	target = models.ForeignKey(Currency, on_delete=models.CASCADE, )
	rate = models.DecimalField(max_digits=17, decimal_places=8)
	date = models.DateTimeField(_("Date"), auto_now_add=True, max_length=20)
	is_active = models.BooleanField(_('Est cours ?'), default=False)

	class Meta:
		app_label = 'helpers'
		verbose_name_plural = 'Taux change'

	def __str__(self):
		return '%s / %s = %s' % (self.source, self.target, self.rate)

	def save(self, *args, **kwargs):
		if self.is_active is True:
			self.__class__._default_manager.filter(is_active=True).update(
				is_active=False)

		super().save(*args, **kwargs)


def get_current_rate():
	rate = ExchangeRate.objects.filter(is_active=True, source__code="USD",
	                                   target__code=settings.DEFAULT_CURRENCY).last()
	return f"1 {rate.source.code} = {round(rate.rate, 4)} {rate.target.code}"


class Sms(TimeStampedModel):
	content = models.TextField(_('content'))
	phone = models.CharField(_('Tel'), max_length=80)
	email = models.EmailField(_('Email'), max_length=80, null=True, blank=True)
	config = models.JSONField(_('autres'), null=True, blank=True)
	sid = models.PositiveIntegerField('sid')

	class Meta:
		app_label = "helpers"
		verbose_name = _("sms")
		verbose_name_plural = _("sms")

	def __str__(self):
		return "{}".format(self.id, )

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)


class FakeModel(TimeStampedModel):
	content = models.TextField(_('content'))
	name = models.CharField(_('Name'), max_length=80)
	sid = models.PositiveIntegerField('sid')
	rate = models.DecimalField(max_digits=17, decimal_places=8)
	date = models.DateField(_("Date"), max_length=20)
	is_active = models.BooleanField(_('Est cours ?'), default=False)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="user", related_name="+")

	def __str__(self):
		return "{}".format(self.id, )




class SimpleOtp(TimeStampedModel):
	reference = models.CharField(_('Reference'), max_length=128,unique=True)
	key = models.CharField(_('key'), max_length=80, editable=False)
	drift = models.SmallIntegerField(default=1, editable=False)
	step = models.PositiveSmallIntegerField(default=OTP_STEP, editable=False)
	last_t = models.BigIntegerField(default=-1, editable=False)
	required_otp = models.BooleanField(default=True, editable=False)
	otp = models.PositiveIntegerField(_('otp'), editable=False, blank=True, null=True)
	message= models.TextField("msg", blank=True, null=True)
	phone = models.CharField(_('Phone'), max_length=80, editable=False)

	class Meta:
		app_label = 'helpers'
		verbose_name="Otp"


	def save(self, *args, **kwargs):
		if not self.reference:
			try:
				self.reference = CommonHelper.Instance().generate_code("helpers", "simpleotp", "reference", size=10)
			except:
				error = ValueError("A possible infinite loop was detected")
				raise error
		return super().save(*args, **kwargs)



	@property
	def bin_key(self):
		"""
		The secret key as a binary string.
		"""
		return unhexlify(self.key.encode())


	def generate_otp_and_save(self):
		self.generate_otp()
		self.save()

	def generate_otp(self):
		#print("======== otp=======")
		#totp_obj = CommonsUtils.totp_generator(self.key, self.step)
		totp_obj = TOTP(bytes(self.key, "utf-8"), step=300)
		self.otp = totp_obj.token()
		#print(self.otp)
		self.last_t = totp_obj.t()

	def verify(self, token):
		try:
			token = int(token)
		except Exception:
			return False
		if self.otp != token:
			return False

		#totp_obj = CommonsUtils.totp_generator(self.key, self.step)
		totp_obj = TOTP(bytes(self.key, "utf-8"), step=300)
		return totp_obj.verify(token)

	@property
	def bin_key(self):
		"""
		The secret key as a binary string.
		"""
		return unhexlify(self.key.encode())


	def get_otp_msg(self):
		compte = "Bienvenue sur SIGCDD "
		identifiant = "Votre code de validation pour le retrait cheque N {}  est {}. Ce code expire dans {} min".format(self.reference,
		                                                                                                 self.otp,
		                                                                                                 OTP_STEP_IN_MIN)
		message = "{}. {}".format(compte, identifiant)
		return message


	def send_otp(self):
		if self.required_otp:
			try:
				notif_by_sms(self.phone, self.message)
			except:
				import traceback
				traceback.print_exc()



	def __str__(self):
		# noinspection PyPep8
		return "{}".format(self.reference, )


class FtpServeur(TimeStampedModel):
	host = models.CharField(_('Host'), max_length=128,unique=True)
	username = models.CharField(_('Username'), max_length=128)
	pwd = models.CharField(_('Mot de passe'), max_length=128)
	port = models.PositiveSmallIntegerField('Port',default=22)
	actif = models.BooleanField('actif?')

	class Meta:
		app_label = 'helpers'
		verbose_name="FtpServeur"
	def __str__(self):
		# noinspection PyPep8
		return "{}".format(self.host, )

	def save(self, *args, **kwargs):
		if self.actif is True:
			self.__class__._default_manager.filter(actif=True).update(actif=False)
		super().save(*args, **kwargs)



	def get_credentials(self):
		return {"host":self.host,"password":self.pwd,"port":self.port,"username":self.username}



class DirType(models.TextChoices):
	COMPTE_DEPOT = "COMPTE_DEPOT", "COMPTE DEPOT"
	CHEQUE = "CHEQUE", "CHEQUE"
	VIREMENT = "VIREMENT", "VIREMENT"
	AVISDEBIT = "AVISDEBIT", "AVISDEBIT"
	AVISCREDIT = "AVISCREDIT", "AVISCREDIT"

class FtpDir(TimeStampedModel):
	type = models.CharField(max_length=128, choices=DirType.choices)
	reference = models.CharField(_('Reference'), max_length=128,unique=True)
	pull_dir = models.CharField(_('Repertoire recuperation'), max_length=128)
	push_dir = models.CharField(_('Repertoire depot'), max_length=128)
	serveur=models.ForeignKey(FtpServeur, on_delete=models.CASCADE, verbose_name="serveur", related_name="+")
	actif = models.BooleanField(default=True, editable=False)


	class Meta:
		app_label = 'helpers'
		verbose_name="FtpDir"
		unique_together=("type","serveur")




class ServeurType(models.TextChoices):
	SID = "SID", "SID"
	SERVER_NAME = "SERVER_NAME", "SERVER NAME"

class OracleDatabase(TimeStampedModel):
	host = models.CharField(_('Host'), max_length=128,unique=True)
	dbname = models.CharField(_('Databbase'), max_length=128)
	username = models.CharField(_('Username'), max_length=128)
	pwd = models.CharField(_('Mot de passe'), max_length=128)
	sid = models.CharField(_('sid/Serveur'), max_length=128,blank=True, null=True)
	port = models.PositiveSmallIntegerField('Port',default=1521)
	actif = models.BooleanField('actif?')
	type = models.CharField("Type",max_length=128, choices=ServeurType.choices)

	class Meta:
		app_label = 'helpers'
		verbose_name="Oracle db"
	def __str__(self):
		# noinspection PyPep8
		return "{}".format(self.host, )

	def save(self, *args, **kwargs):
		if self.actif is True:
			self.__class__._default_manager.filter(actif=True).update(actif=False)
		super().save(*args, **kwargs)

	def get_credentials(self):
		sid=None
		if self.type==ServeurType.SID and self.sid : sid=self.sid
		return {"host":self.host,"password":self.pwd,"port":self.port,"username":self.username,"database":self.dbname,"sid":sid}



from django.db import models
from notifications.base.models import AbstractNotification






class TypeNotif(models.TextChoices):

	live_notify_badge_valide_c = "live_notify_badge_valide_c"
	live_notify_badge_receptionne_c="live_notify_badge_receptionne_c"
	live_notify_badge_visa_c="live_notify_badge_visa_c"
	live_notify_badge_priseencharge_c="live_notify_badge_priseencharge_c"

	live_notify_badge_receptionne_v = "live_notify_badge_receptionne_v"
	live_notify_badge_visa_v = "live_notify_badge_visa_v"
	live_notify_badge_priseencharge_v = "live_notify_badge_priseencharge_v"
	live_notify_badge_valide_v = "live_notify_badge_valide_v"
	live_notify_badge_cdd = "live_notify_badge_cdd"




class Notification(AbstractNotification):
    # custom field example
    #category = models.ForeignKey(Category,related_name="+",verbose_name="categorie",on_delete=models.CASCADE)

    class Meta(AbstractNotification.Meta):
        abstract = False
from django.contrib.contenttypes.fields import GenericRelation
class Category(TimeStampedModel):
	name = models.CharField(max_length=128, choices=TypeNotif.choices,unique=True)

	class Meta:
		app_label = 'helpers'
		verbose_name="Type Notif"

	def __str__(self):
		# noinspection PyPep8
		return "{}".format(self.name, )



class Batch(TimeStampedModel):
	reference = models.CharField("Reference", max_length=128 )
	tache = models.CharField("Operation", max_length=200)
	actif=models.BooleanField('actif?',default=False)

	class Meta:
		app_label = 'helpers'
		verbose_name = _('Batch')
		ordering = ['-pk']
	def __str__(self):
		return "{}".format(self.id,)

