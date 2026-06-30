import datetime
import traceback
from binascii import unhexlify
from datetime import timedelta, date

from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.contrib.postgres.fields import DateRangeField
from django.contrib.sites.models import Site
from django.db import transaction
from django.db.models import Sum, IntegerField, F, Value, DateField, DateTimeField, Count,ExpressionWrapper,CharField
from django.db.models.functions import Coalesce
from django.db.models.signals import post_save, pre_delete, post_delete
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from djmoney.models.fields import MoneyField
from num2words import num2words
from phonenumber_field.modelfields import PhoneNumberField
from psycopg2.extras import DateRange
from schwifty import BIC
from django.utils import timezone
from cddaccount import TYPE_OBJECT, NATURE_COMPTE, NATURE_FONDS, STATUS_CREATION, PAYMENT_MEAN_TYPE, TYPE_REGLEMENT, \
	STATUS_ORDRE_PAYMENT, ETAPE_ORDRE_PAYMENT, DISPOSITION_TYPE, TYPE_GESTION, TYPE_RECEPTIONNAIRE, SENS_TRX, \
	ETAPE_ASTER, STATUT_ASTER, STATUS_PROVIDER, MonthType, PROVENANCE_FOND
from cddaccount.manager import *
from core.models import Ministere, Secteur, PosteComptable, ProfileDCP, CodeService, ProfilePC, Agent, Direction, \
	Structure
from helpers.commons import CommonHelper, OTP_STEP, OTP_STEP_IN_MIN
from helpers.exceptions import SigException
from helpers.models import Person, notif_by_sms, FtpDir, virmasse_directory_path
from helpers.models import Role, justificatif_directory_path, DirType
# Create your models here.
from helpers.validators import only_digit_validator
from .account import generate_rib, getmax_value, TypeCompteTrx, CompteDepot, JourneeComptable, AnneeComptable, Nature, \
	SousNature, Depositaire, SettingsOP, ValidationCompte, FichierData, CompteTrx

from django.db import transaction
from django.db.models import IntegerField, Max
from django.db.models.functions import Substr, Cast
from django.db import connection

LENGHT_COMPTE_DEPOT = 24

LENGHT_COMPTE_DEPOT_WHITHOUT_RIB = 22

SEQUENCE = "879"
import logging

logger = logging.getLogger(__name__)


from djmoney.models.validators import MinMoneyValidator, MaxMoneyValidator


# Create your models here.
from allauth.account.signals import user_logged_in
from django.dispatch import receiver



from django.contrib.sessions.models import Session


class Projet(TimeStampedModel):
	typecompte = models.ForeignKey(TypeCompteTrx, verbose_name=_('Type de compte'), on_delete=models.SET_NULL,
	                               related_name="+", blank=True, null=True)
	name = models.CharField(max_length=128, verbose_name=_('Nom'))
	period = DateRangeField("Période", help_text="Merci d'utiliser ce format: <em>YYYY-MM-DD</em>.", blank=True,
	                        null=True)
	compte = models.ForeignKey(CompteDepot, verbose_name=_('compte'), related_name="+", on_delete=models.CASCADE)
	amount = MoneyField(_('Montant'), max_digits=20, decimal_places=2, default_currency='XOF', default=0,
	                    validators=[MinMoneyValidator(0)])

	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.CASCADE)

	prestataire = models.CharField(_('Nom prestataire'), max_length=128)
	ninea = models.CharField(_('Ninea prestataire'), max_length=128)
	compte_iban = models.CharField(_('Compte bancaire prestataire'), max_length=128, null=True, blank=True)
	ref_marche = models.CharField(_('Référence projet'), max_length=128, unique=True)
	demande_blocage = models.BooleanField("demander blocage", default=False)
	accepter_blocage = models.BooleanField("Accepter blocage", default=False)
	status = models.CharField(_('Statut'), max_length=128, choices=STATUS_ORDRE_PAYMENT.CHOICES,
	                          default=STATUS_ORDRE_PAYMENT.NOUVEAU)

	demande_date = models.DateField(_('Date demande'), max_length=12, null=True, blank=True)
	acceptation_date = models.DateField(_('Date acceptation'), max_length=12, null=True, blank=True)
	agent_postecomptable = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.SET_NULL,
	                                         blank=True, null=True)
	observations = models.TextField(_('observations'), default="RAS")
	objects = ProjetManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Projet')
		ordering = ['-pk']
		verbose_name_plural = _('Projets')
		permissions = [
			("demanderbf_project", "Peut faire une demande de blocage de fonds"),
			("validerbf_project", "Peut valider une demande de blocage de fonds")
		]

	def __str__(self):
		return "{}".format(self.name, )

	def fomat_status(self):
		tag = "info"
		s = "en cours"
		if hasattr(self, "blocagefond"):
			tag = "success"
			s = "Fond Bloqué"
		else:
			if self.status == STATUS_ORDRE_PAYMENT.REJETE:
				s = "Rejeté"
				tag = "danger"

		a = """<span class="badge bagde-{} users-view-status">{}</span>""".format(tag, s)
		return format_html(a)

	def format_period(self):
		a = "{} {}".format(self.period.lower.strftime('%Y-%m-%d'),
		                   self.period.upper.strftime('%Y-%m-%d')) if self.period else "----"
		return a

	def can_acces(self, user):
		return self.__class__._default_manager.filter(id=self.id).by_agent(user).exists()

	def get_instance(self):
		return self


class ObsProjet(TimeStampedModel):
	motif = models.CharField(_('motif'), max_length=128)
	projet = models.ForeignKey(Projet, verbose_name=_('ordre'), on_delete=models.CASCADE, related_name="projet_obs")
	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.CASCADE)
	observations = models.TextField(_('observations'), default="RAS")

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.id,)


class BlocageFond(TimeStampedModel):
	# date_comptable=models.DateField("date comptable", max_length=12)
	reference = models.CharField(_('référence'), max_length=128, unique=True)
	projet = models.OneToOneField(Projet, verbose_name=_('projet'), related_name="blocagefond",
	                              on_delete=models.CASCADE)
	compte = models.ForeignKey(CompteDepot, verbose_name=_('compte'), related_name="+", on_delete=models.CASCADE)
	amount = MoneyField(_('Montant'), max_digits=20, decimal_places=2, default_currency='XOF', default=0,
	                    validators=[MinMoneyValidator(0)])
	balance = MoneyField(_('Solde'), max_digits=20, decimal_places=2, default_currency='XOF', default=0,
	                     validators=[MinMoneyValidator(0)])
	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.CASCADE)
	open_date = models.DateField(_('Date ouverture'), max_length=12, null=True, blank=True)
	end_date = models.DateField(_('Date Fin'), max_length=12, null=True, blank=True)
	prestataire = models.CharField(_('Prestataire'), max_length=128)
	ninea = models.CharField(_('Ninea prestataire'), max_length=128)
	compte_iban = models.CharField(_('Compte bancaire prestataire'), max_length=128, null=True, blank=True)
	ref_marche = models.CharField(_('Référence projet'), max_length=128, unique=True)
	jour_comptable = models.ForeignKey(JourneeComptable, verbose_name=_('journee comptable'), related_name="+",
	                                   on_delete=models.SET_NULL, null=True, blank=True)
	close = models.BooleanField("Ferme", default=False)
	objects = BlocageFondManager()

	class Meta:
		app_label = 'cddaccount'
		ordering = ['-pk']
		verbose_name = _('Blocage de fonds')
		verbose_name_plural = _('Blocages de fonds')

	@property
	def amount_in_words(self):
		return num2words(self.amount.amount, lang='fr')

	def benef_iban_items(self):
		if self.compte_iban:
			s = self.compte_iban.strip()
			d = [s[:5], s[5:11], s[11:23], s[-2:]]
			return d
		else:
			return []

	def __str__(self):
		return "{} {}".format(self.ref_marche, self.projet.name)

	def get_instance(self):
		return self

	def can_acces(self, user):
		return self.__class__._default_manager.filter(id=self.id).by_agent(user).exists()

	def can_debit_trx(self, amount):
		if self.balance >= amount and not self.close:
			return True
		else:
			return False

	def can_credit_trx(self, amount):
		if not self.close:
			return True
		else:
			return False

	def debit(self, amount):
		if self.can_debit_trx(amount):
			self.balance = self.balance - amount
			self.save()
		else:
			error = SigException(
				message="Montant solde blocage {} inférieur  au montant demandé {}".format(self.balance, amount))
			raise error

	def credit(self, amount):
		if self.can_credit_trx(amount):
			self.balance = self.balance + amount
			self.save()
		else:
			error = SigException(message="Impossible de créditer ce compte ")
			raise error

	def save(self, *args, **kwargs):
		if not self.reference:
			try:
				self.reference = CommonHelper.Instance().generate_code("cddaccount", "blocagefond", "reference", size=9)
			except:
				error = ValueError("A possible infinite loop was detected")
				raise error
		return super().save(*args, **kwargs)


from django_otp.oath import TOTP


class OrdrePayment(TimeStampedModel):
	choices = [(PAYMENT_MEAN_TYPE.CHEQUE, PAYMENT_MEAN_TYPE.CHEQUE),
	           (PAYMENT_MEAN_TYPE.VIREMENT, PAYMENT_MEAN_TYPE.VIREMENT)]
	reference = models.CharField(_('référence'), max_length=128, unique=True)
	# date_comptable = models.DateField("date comptable", max_length=12)
	jour_comptable = models.ForeignKey(JourneeComptable, verbose_name=_('journée comptable'), related_name="+",
	                                   on_delete=models.SET_NULL, null=True, blank=True)

	object = models.CharField(_('Object'), max_length=128)
	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="ordrepayments", on_delete=models.CASCADE)
	compte = models.ForeignKey(CompteDepot, verbose_name=_('Compte de dépôt'), on_delete=models.CASCADE,
	                           related_name="compte_ordres")
	secteur = models.ForeignKey(Secteur, verbose_name=_('Secteur'), on_delete=models.CASCADE, related_name="+")
	gerant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="+", blank=True,
	                           null=True)

	recepteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="+", blank=True,
	                              null=True, verbose_name=_('Récepteur'))

	open_date = models.DateField(_('Date ouverture'), max_length=12)
	amount = MoneyField(_('Montant'), max_digits=20, decimal_places=2, default_currency='XOF', null=True, default=0,
	                    validators=[MinMoneyValidator(0)])
	initial_amount = MoneyField(_('Montant initial'), max_digits=20, decimal_places=2, default_currency='XOF',
	                            null=True, validators=[MinMoneyValidator(0)])
	balance_before = MoneyField(_('Solde avant'), max_digits=20, decimal_places=2, default_currency='XOF', null=True,
	                            default=0, validators=[MinMoneyValidator(0)])
	balance_after = MoneyField(_('Solde après'), max_digits=20, decimal_places=2, default_currency='XOF', null=True,
	                           default=0, validators=[MinMoneyValidator(0)])

	beneficiaire = models.CharField(_('Bénéficiaire'), max_length=128)
	ninea = models.CharField(_('Ninea'), max_length=128, blank=True, null=True)
	nature = models.ForeignKey(Nature, verbose_name=_('Nature'), on_delete=models.CASCADE, related_name="+")

	sousnature = models.ForeignKey(SousNature, verbose_name=_('Sous Nature'), on_delete=models.SET_NULL,
	                               related_name="+", blank=True, null=True)
	type_nature = models.CharField(_('Type nature'), max_length=128, choices=NATURE_COMPTE.CHOICES,
	                               default=NATURE_COMPTE.FONCTIONNEMENT)
	type_gestion = models.CharField(_('Type gestion'), max_length=128, choices=TYPE_GESTION.CHOICES,
	                                default=TYPE_GESTION.COURANT)
	reglement = models.CharField(_('Type règlement'), max_length=128, choices=TYPE_REGLEMENT.CHOICES,
	                             default=TYPE_REGLEMENT.GLOBAL)
	payment_mean = models.CharField(_('Moyen de paiement'), max_length=128, choices=PAYMENT_MEAN_TYPE.CHOICES,
	                                default=PAYMENT_MEAN_TYPE.CHEQUE)

	cheque = models.CharField(_('Numéro chèque'), max_length=128, blank=True, null=True)
	iban = models.CharField(_('Compte bancaire'), max_length=30, blank=True, null=True)
	status = models.CharField(_('Statut'), max_length=128, choices=STATUS_ORDRE_PAYMENT.CHOICES,
	                          default=STATUS_ORDRE_PAYMENT.NOUVEAU)
	previous_etape = models.CharField(_('Etape précèdante'), max_length=128, choices=ETAPE_ORDRE_PAYMENT.CHOICES,
	                                  null=True, blank=True)

	etape = models.CharField(_('Etape'), max_length=128, choices=ETAPE_ORDRE_PAYMENT.CHOICES,
	                         default=ETAPE_ORDRE_PAYMENT.SAISIE)

	blocage = models.ForeignKey(BlocageFond, verbose_name=_('Blocage'), on_delete=models.SET_NULL,
	                            related_name="ops_blocage", blank=True, null=True)
	date_prise_en_charge = models.DateTimeField(_('Date prise en charge'), max_length=12, blank=True, null=True)
	date_visa = models.DateTimeField(_('Date visa'), max_length=12, blank=True, null=True)

	date_reception = models.DateTimeField(_('Date réception'), max_length=12, blank=True, null=True)

	key = models.CharField(_('key'), max_length=80, editable=False)
	drift = models.SmallIntegerField(default=1, editable=False)
	step = models.PositiveSmallIntegerField(default=OTP_STEP, editable=False)
	last_t = models.BigIntegerField(default=-1, editable=False)
	required_otp = models.BooleanField(default=True, editable=False)
	otp = models.PositiveIntegerField(_('otp'), editable=False, blank=True, null=True)

	vali_multi = models.CharField(_('validation_multi'), max_length=80, editable=False, blank=True, null=True)

	receptionnaire = models.CharField("Le mandataire va recupérer le chèque ?", max_length=80,
	                                  choices=TYPE_RECEPTIONNAIRE.CHOICES, default=TYPE_RECEPTIONNAIRE.GERANT)

	cin_receptionnaire = models.CharField(_('Cin récupérateur'), max_length=128, null=True, blank=True)
	phone_receptionnaire = PhoneNumberField(_("Tel Bénéficiaire"), null=False, blank=False)
	depositaire = models.ForeignKey(Depositaire, verbose_name=_('Mandataire'), on_delete=models.SET_NULL,
	                                related_name="+", blank=True, null=True)

	observations = models.TextField(_('observations'), default="RAS")

	cheque_delivred = models.BooleanField(default=False, editable=True)

	transfer_out_umeoa = models.BooleanField(_('Virement Etranger'), default=False)
	sig_reference = models.CharField(_('Référence SIGCDD'), max_length=80, blank=True, null=True)

	gestion = models.ForeignKey(AnneeComptable, verbose_name=_('Gestion current'), related_name="+",
	                            on_delete=models.SET_NULL, blank=True, null=True)

	status_provider = models.CharField(_('Statut provider'), max_length=128, choices=STATUS_PROVIDER.CHOICES,
	                                   default=STATUS_PROVIDER.INIT)
	provider_trx = models.CharField(_('trx provider'), max_length=128, blank=True, null=True)
	rsp_provider = models.JSONField("details", blank=True, null=True)

	id_sender_rq = models.CharField(_('id sender request'), max_length=128, blank=True, null=True)

	typecompte = models.ForeignKey(TypeCompteTrx, verbose_name=_('Type de compte'), on_delete=models.SET_NULL,
	                                related_name="+", blank=True, null=True)

	objects = OrdrePaymentManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Ordre de paiement')
		verbose_name_plural = _('Ordres de paiement')
		ordering = ['-created']
		permissions = [
			("priseencharge_ordrepayment", "Peut Faire la prise en charge de l'ordre de paiement"),
			("viser_ordrepayment", "Peut viser l'ordre de paiement"),
			("valider_ordrepayment", "Peut valider la saisie de l'ordre de paiement"),
			("accepter_ordrepayment", "Peut accepter l'ordre de paiement"),
			("maketrx_ordrepayment", "Peut faire un paiement sur l'ordre de paiement"),
			("annulation_ordrepayment", "Peut annuler sur l'ordre de paiement"),
			("bordereau_op", "Peut editer tous les ordres de paiement"),
			("ask_demandeop","Peut demander un ordre de paiement"),
			("ask_mobileop", "Peut faire un op via mobile money")
		]

	@property
	def poste_code(self):
		"""
		The secret key as a binary string.
		"""
		return self.compte.poste.reference

	@property
	def bin_key(self):
		"""
		The secret key as a binary string.
		"""
		return unhexlify(self.key.encode())

	def render_sig_reference(self):
		if self.sig_reference:
			details_url = reverse('cddaccount:detail_ordre_payement', kwargs={'reference': self.reference})
			str = """<a   href="{}"><span >{} </span></a>""".format(details_url, self.sig_reference)
		else:
			str = "--"
		return format_html(str)

	def get_reference_template(self):
		if self.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT:
			details_url = reverse('cddaccount:temlate_op_view', kwargs={'reference': self.reference})
			str = """<a  href="{}" target="_blank"><span><i class="fa fa-file"></i></span></a>""".format(details_url)
		elif self.payment_mean == PAYMENT_MEAN_TYPE.RETRAIT:
			details_url = reverse('cddaccount:temlate_op_view', kwargs={'reference': self.reference})
			str = """<a  href="{}" target="_blank"><span><i class="fa fa-file"></i></span></a>""".format(details_url)
		elif self.payment_mean == PAYMENT_MEAN_TYPE.MOBILE:
			details_url = reverse('cddaccount:temlate_op_view', kwargs={'reference': self.reference})
			str = """<a  href="{}" target="_blank"><span><i class="fa fa-file"></i></span></a>""".format(details_url)
		else:
			str = "&nbsp;"
		return format_html(str)


	def get_reference_templateop(self):
		if self.payment_mean == PAYMENT_MEAN_TYPE.RETRAIT:
			details_url = reverse('cddaccount:temlate_demandeop_view', kwargs={'reference': self.reference})
			str = """<a  href="{}" target="_blank"><span><i class="fa fa-file"></i></span></a>""".format(details_url)
		else:
			str = "&nbsp;"
		return format_html(str)

	def mean_tuples(self):
		return [(self.payment_mean, self.payment_mean)]

	def get_reliquat(self):
		if hasattr(self, "reservationfond"):
			return self.reservationfond.reliquat
		else:
			return ""

	def get_mean_code(self):
		if self.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE:
			return "CH"
		elif self.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT:
			return "OV"
		elif self.payment_mean == PAYMENT_MEAN_TYPE.MOBILE:
			return "OV"
		elif self.payment_mean == PAYMENT_MEAN_TYPE.RETRAIT:
			return "OP"
		else:
			return "--"

	def get_sig_reference(self):
		year = str(datetime.date.today().year)
		year = year[-2:]
		if self.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE:
			return "CH{}{}".format(year, self.cheque)
		elif self.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT:
			return self.generate_ov_reference()
		elif self.payment_mean == PAYMENT_MEAN_TYPE.MOBILE:
			return self.generate_ov_reference()
		elif self.payment_mean == PAYMENT_MEAN_TYPE.RETRAIT:
			return self.generate_ov_reference(codeprefix="OP")
		else:
			return ""

	def getmax_value(self, refs, prefix=None):
		d = 0
		for item in refs:
			if prefix:
				item = item.replace(prefix, "")
			nu = item
			nu = nu.lstrip("0")
			try:
				v = int(nu)
				if v > d:
					d = v
			except:
				pass
		return d

	def generate_ov_reference(self,codeprefix=None):

		today = date.today()
		year = str(today.year)
		year = year[-2:]
		if codeprefix:
			prefix = "{}{}{}".format(codeprefix,year, self.compte.short_compte)

		else : prefix = "OV{}{}".format(year,self.compte.short_compte)

		# mantis#0000043: reprendre la codification des ordres de virement
		# refs = self.__class__._default_manager.filter(created__year=today.year, created__month=today.month,created__day=today.day).values_list("sig_reference", flat=True)
		refs = self.__class__._default_manager.filter(created__year=today.year,
		                                              compte__short_compte=self.compte.short_compte,
		                                              sig_reference__startswith=prefix).values_list("sig_reference",
		                                                                                            flat=True)

		nbs = len(
			refs) + 1  # self.__class__._default_manager.filter(created__year=today.year,created__month=today.month,created__day=today.day).count()+1

		b = f"{nbs}"
		b = b.zfill(6)
		new_ref = '{}{}'.format(prefix, b)
		if new_ref in refs:
			nb = self.getmax_value(refs, prefix=prefix) + 1
			b = f"{nb}"
			b = b.zfill(6)
			new_ref = '{}{}'.format(prefix, b)

		return new_ref

	def benef_iban_items(self):
		if self.iban:
			s = self.iban.strip()
			d = [s[:5], s[5:10], s[10:22], s[-2:]]
			return d
		else:
			return []

	def get_virements_details(self):
		return []

	@property
	def amount_in_words(self):
		return num2words(self.amount.amount, lang='fr')

	def can_acces(self, user):
		return self.__class__._default_manager.filter(id=self.id).by_agent(user).exists()

	def can_cancel(self):
		if hasattr(self, "prise_en_charge"):
			prise_en_charge = self.prise_en_charge
			if hasattr(prise_en_charge, "visa"):
				if self.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT:
					raise SigException(message="Virement déjà effectué")
				if self.payment_mean == PAYMENT_MEAN_TYPE.RETRAIT:
					raise SigException(message="Virement déjà effectué")

				if self.payment_mean == PAYMENT_MEAN_TYPE.MOBILE:
					raise SigException(message="Virement déjà effectué")
				if self.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and self.cheque and self.cheque_delivred:
					raise SigException(message="Chèque déjà réceptionné")
		return True

	def generate_otp_and_save(self):
		self.generate_otp()
		self.save()

	def generate_otp(self):
		# totp_obj = CommonsUtils.totp_generator(self.key, self.step)
		totp_obj = TOTP(bytes(self.key, "utf-8"), step=300)
		self.otp = totp_obj.token()
		self.last_t = totp_obj.t()

	def get_absolute_url_old(self):

		name = ""
		if self.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT and self.etape == ETAPE_ORDRE_PAYMENT.SAISIE:
			name = 'nouveaux_virements_list'
			if hasattr(self, "virementmasse"): name = "nouveaux_virmasse_list"

		elif self.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT and self.etape == ETAPE_ORDRE_PAYMENT.VALIDE:
			name = 'valides_virements_list'
			if hasattr(self, "virementmasse"): name = "valides_virmasse_list"
		elif self.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT and self.etape == ETAPE_ORDRE_PAYMENT.ACCEPTE:
			name = 'accepter_virements_list'
			if hasattr(self, "virementmasse"): name = "accepter_virmasse_list"
		elif self.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT and self.etape == ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE:
			name = 'priseencharge_virements_list'
			if hasattr(self, "virementmasse"): name = "priseencharge_virmasse_list"
		elif self.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT and self.etape == ETAPE_ORDRE_PAYMENT.VISA:
			name = 'visa_virements_list'
			if hasattr(self, "virementmasse"): name = "visa_virmasse_list"

		elif self.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and self.etape == ETAPE_ORDRE_PAYMENT.SAISIE:
			name = 'nouveaux_opcheques_list'
		elif self.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and self.etape == ETAPE_ORDRE_PAYMENT.VALIDE:
			name = 'valides_opcheques_list'
		elif self.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and self.etape == ETAPE_ORDRE_PAYMENT.ACCEPTE:
			name = 'accepter_opcheques_list'
		elif self.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and self.etape == ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE:
			name = 'priseencharge_opcheques_list'
		elif self.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and self.etape == ETAPE_ORDRE_PAYMENT.VISA:
			name = 'visa_opcheques_list'
		return reverse("cddaccount:{}".format(name, ))

	def get_absolute_url(self):
		name = ""
		if self.etape == ETAPE_ORDRE_PAYMENT.SAISIE:
			name = 'nouveaux_op_list'
		elif self.etape == ETAPE_ORDRE_PAYMENT.VALIDE:
			name = 'valides_op_list'
		elif self.etape == ETAPE_ORDRE_PAYMENT.ACCEPTE:
			name = 'accepter_op_list'
		elif self.etape == ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE:
			name = 'priseencharge_op_list'
		elif self.etape == ETAPE_ORDRE_PAYMENT.VISA:
			name = 'visa_op_list'
		return reverse("cddaccount:{}".format(name, ))

	def verify(self, token):
		try:
			token = int(token)
		except Exception:
			return False
		if self.otp != token:
			return False

		# totp_obj = CommonsUtils.totp_generator(self.key, self.step)
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
		identifiant = "le code de validation de l'opération N° {}  pour le compte {} est {}. Ce code expire dans {} min".format(
			self.sig_reference,
			self.compte.short_compte, self.otp,
			OTP_STEP_IN_MIN)
		message = "{}. {}".format(compte, identifiant)
		return message

	def get_otp_msg_all(self, otp):
		compte = "Bienvenue sur SIGCDD "
		identifiant = "Votre code de validation  des ordres de paiement  est {}. Ce code expire dans {} min".format(otp,
		                                                                                                            OTP_STEP_IN_MIN)
		message = "{}. {}".format(compte, identifiant)
		return message

	def get_rejet_msg(self):
		compte = "Bienvenue sur SIGCDD "
		date = "{:%d-%m-%Y %H:%M}".format(self.modified, )
		identifiant = "Votre paiement N° {}  a été rejeté pour motif {}. Date {} ".format(self.sig_reference,
		                                                                                  self.observations, date)
		message = "{}. {}".format(compte, identifiant)
		return message

	def get_visa_msg(self, amount):
		compte = "Bienvenue sur SIGCDD "
		_date = "{:%d-%m-%Y %H:%M}".format(datetime.datetime.now())
		identifiant = "Le paiement N° {} d'un montant de {} est effectif. Date {} ".format(self.sig_reference, amount,
		                                                                                   _date)
		message = "{}. {}".format(compte, identifiant)
		return message

	def send_rejet_msg(self):
		obj = SettingsOP.object()
		if obj:
			message = self.get_rejet_msg()
			try:
				if obj.rejet_notif_benef and self.phone_receptionnaire:
					notif_by_sms(self.phone_receptionnaire.as_e164, message)
				if obj.rejet_notif_gerant and self.gerant:
					notif_by_sms(self.gerant.gerant_cd.phone.as_e164, message)
			except:
				import traceback
				traceback.print_exc()

	def send_ordrepayment_otp(self, phone):
		if self.required_otp:
			message = self.get_otp_msg()
			try:
				notif_by_sms(phone, message)
				print("envoie termdine")
			except:
				print("envoie termine")
				pass

	def can_make_visa(self):
		if hasattr(self, "reservationfond") and hasattr(self, "prise_en_charge") and self.reservationfond.close:
			if not hasattr(self.prise_en_charge, "visa"):
				return True
		else:
			return False

	def can_make_trx(self):
		if hasattr(self, "reservationfond") and hasattr(self, "prise_en_charge"):
			return self.reservationfond.can_make_trx()
		else:
			return False

	def is_valid_op(self):
		if self.blocage:
			if self.blocage.can_debit_trx(self.amount):
				return True
			else:
				raise SigException(
					message="Montant solde blocage {} inférieur au montant demandé {}".format(self.blocage.balance,
					                                                                          self.amount))
		else:
			if self.compte.can_debit_trx(self.amount):
				return True
			else:
				raise SigException(
					message="Montant solde compte {} inférieur  au montant demandé {}".format(self.compte.balance,
					                                                                          self.amount))

	def get_instance(self):
		return self

	def get_actions(self, user):
		actions = ["update", "delete", "prise_en_charge", "visa"]
		if not user.has_perm('cddaccount.viser_ordrepayment'):
			actions.remove("visa")
		if not user.has_perm('cddaccount.delete_ordrepayment'):
			actions.remove("delete")

		if not user.has_perm('cddaccount.update_ordrepayment'):
			actions.remove("update")
		if not user.has_perm('cddaccount.priseencharge_ordrepayment'):
			actions.remove("prise_en_charge")
		return actions

	def prise_en_charge(self):
		prise_en_charge_url = "#"  # reverse('cddaccount:validate_gerantcd_data', kwargs={'reference': self.reference})
		if hasattr(self, "prise_en_charge"):
			str = """DEJAs PRIS EN CHARGE"""
		else:

			str = """<button type="button" class="priseencharge-item btn btn-sm btn-purple" data-form-url="{}">
										         <span >Faire Prise en charge </span>
										        </button>""".format(prise_en_charge_url, )
		return format_html(str)

	def visa(self, ):
		visa_url = "#"  # reverse('cddaccount:validate_gerantcd_data', kwargs={'reference': self.reference})
		if hasattr(self, "prise_en_charge"):
			if hasattr(self.prise_en_charge, "visa"):
				str = """VISA OK """
			else:
				str = """<button type="button" class="visa-item btn btn-sm btn-purple" data-form-url="{}">
						         <span >Faire Visa </span>
						        </button>
						        """.format(visa_url, )
		else:
			str = "Attente prise en charge"

		return format_html(str)

	def crud(self):
		if hasattr(self, "prise_en_charge"):
			str = "---"
		else:
			delete_url = reverse('cddaccount:delete_ordrepayment', kwargs={'pk': self.pk})
			update_url = reverse('cddaccount:update_ordrepayment', kwargs={'pk': self.pk})
			str = """
			        <button type="button" class="update-item btn btn-sm btn-warning " data-form-url="{}">
			          <span class="fa fa-pencil"></span>
			        </button>
			         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
			          <span class="fa fa-trash"></span>
			        </button>
			        """.format(update_url, delete_url, )

		return format_html(str)

	def save(self, *args, **kwargs):
		if not self.compte.is_open():
			error = ValueError("Compte de depot non actif")
			raise error
		# if hasattr(self,"prise_en_charge"):
		#	raise ValueError("Impossible de modifier cet ordre de paiement ")
		if not hasattr(self, "secteur"):
			self.secteur = self.compte.secteur
		if self.open_date is None:
			self.open_date = date.today()

		if self.key is None or len(self.key) == 0:
			self.key = CommonHelper.Instance().default_key()

		# if self.compte.balance.amount<self.amount.amount:
		#	raise ValueError("Solde du compte insuffisant pour cet ordre ")
		if not self.reference:
			try:
				self.reference = CommonHelper.Instance().generate_code("cddaccount", "ordrepayment", "reference",
				                                                       size=9)
			except:
				error = ValueError("A possible infinite loop was detected")
				raise error
			self.sig_reference = self.get_sig_reference()

		if self.typecompte:
			self.type_nature=self.typecompte.nature

		return super().save(*args, **kwargs)

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.sig_reference,)

	def get_reglement(self):
		if hasattr(self, "reservationfond"):
			return self.reservationfond.reglement if self.reservationfond.reglement else self.reglement
		else:
			return self.reglement

	def get_payment_mean(self):
		if hasattr(self, "reservationfond"):
			return self.reservationfond.payment_mean if self.reservationfond.payment_mean else self.payment_mean
		else:
			return self.payment_mean

	def pay_cbk_link(self):
		success_link = reverse('cddaccount:process_cbk_data', kwargs={'token': self.reference})
		return "{}{}".format(get_base_url(), success_link)

	def get_authorized_payment_modes(self):
		payment_mean_choices = [(PAYMENT_MEAN_TYPE.VIREMENT, PAYMENT_MEAN_TYPE.VIREMENT),
		                        (PAYMENT_MEAN_TYPE.CHEQUE, "COMPENSE"), (PAYMENT_MEAN_TYPE.NUMERAIRE, "NUMERAIRE"),
		                        (PAYMENT_MEAN_TYPE.OPERATION_ORDRE, "OPERATION ORDRE")]
		if self.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT:
			payment_mean_choices = [(PAYMENT_MEAN_TYPE.VIREMENT, PAYMENT_MEAN_TYPE.VIREMENT),
			                        (PAYMENT_MEAN_TYPE.OPERATION_ORDRE, "OPERATION ORDRE")]
		elif self.payment_mean == PAYMENT_MEAN_TYPE.RETRAIT:
			payment_mean_choices = [(PAYMENT_MEAN_TYPE.NUMERAIRE, "NUMERAIRE")]
		elif self.payment_mean == PAYMENT_MEAN_TYPE.MOBILE:
			payment_mean_choices = [(PAYMENT_MEAN_TYPE.MOBILE, PAYMENT_MEAN_TYPE.MOBILE)]




		if hasattr(self, "virementmasse"):
			if self.payment_mean==PAYMENT_MEAN_TYPE.MOBILE:
				payment_mean_choices = [(PAYMENT_MEAN_TYPE.MOBILE, PAYMENT_MEAN_TYPE.MOBILE)]
			else: payment_mean_choices = [(PAYMENT_MEAN_TYPE.VIREMENT, PAYMENT_MEAN_TYPE.VIREMENT)]

		out_umeoa = self.transfer_out_umeoa
		if out_umeoa:
			payment_mean_choices = [(PAYMENT_MEAN_TYPE.OPERATION_ORDRE, "OPERATION ORDRE")]

		rsv=self.reservationfond
		if rsv.payment_mean  and rsv.has_trx:
			payment_mean_choices = [(rsv.payment_mean, rsv.payment_mean)]
		return payment_mean_choices


PAYMENT_USES_SSL = getattr(settings, 'PAYMENT_USES_SSL', 0)


def get_base_url():
	"""
	Returns host url according to project settings. Protocol is chosen by
	checking PAYMENT_USES_SSL variable.
	If PAYMENT_HOST is not specified, gets domain from Sites.
	Otherwise checks if it's callable and returns it's result. If it's not a
	callable treats it as domain.
	"""
	protocol = 'https' if PAYMENT_USES_SSL else 'http'

	current_site = Site.objects.get_current()
	domain = current_site.domain
	url = "{}://{}".format(protocol, domain)
	return url


class ObsOrdrePayment(TimeStampedModel):
	motif = models.CharField(_('motif'), max_length=128)
	ordre = models.ForeignKey(OrdrePayment, verbose_name=_('ordre'), on_delete=models.CASCADE, related_name="ordre_obs")
	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.CASCADE)
	observations = models.TextField(_('observations'), default="RAS")

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.id,)


class PrisEnchageOrdrePayment(TimeStampedModel):
	ordre = models.OneToOneField(OrdrePayment, verbose_name=_('ordre'), on_delete=models.CASCADE,
	                             related_name="prise_en_charge")
	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.CASCADE)

	amount = MoneyField(_('Montant'), max_digits=20, decimal_places=2, default_currency='XOF', null=True, default=0,
	                    validators=[MinMoneyValidator(0)])

	reglement = models.CharField(_('Type règlement'), max_length=128, choices=TYPE_REGLEMENT.CHOICES,
	                             default=TYPE_REGLEMENT.GLOBAL)
	payment_mean = models.CharField(_('Moyen de paiement'), max_length=128, choices=PAYMENT_MEAN_TYPE.CHOICES,
	                                default=PAYMENT_MEAN_TYPE.CHEQUE)
	status = models.CharField(_('Statut'), max_length=128, choices=STATUS_ORDRE_PAYMENT.CHOICES,
	                          default=STATUS_ORDRE_PAYMENT.NOUVEAU)
	observations = models.TextField(_('observations'), default="RAS")
	cancel = models.BooleanField("Annuler ?", default=False, editable=False)
	objects = PrisEnchageOrdrePaymentManager()

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.id,)

	def save(self, *args, **kwargs):
		# if hasattr(self,"visa") and self.cancel:
		#	raise ValueError("Impossible de modifier cet ordre de paiement ")
		if self.amount.amount > self.ordre.amount.amount:
			raise ValueError("Montant ne doit etre supérieur au montant de l' ordre de paiement ")

		return super().save(*args, **kwargs)

	def send_rejet_msg(self):
		obj = SettingsOP.object()
		if obj:
			message = self.ordre.get_rejet_msg()
			try:
				if obj.rejet_notif_benef and self.ordre.phone_receptionnaire:
					notif_by_sms(self.ordre.phone_receptionnaire.as_e164, message)
				if obj.rejet_notif_gerant and self.ordre.gerant:
					notif_by_sms(self.ordre.gerant.gerant_cd.phone.as_e164, message)
			except:
				import traceback
				traceback.print_exc()

	def send_visa_msg(self, amount):
		obj = SettingsOP.object()
		if obj:
			message = self.ordre.get_visa_msg(amount)
			try:
				if obj.visa_notif_benef and self.ordre.phone_receptionnaire:
					notif_by_sms(self.ordre.phone_receptionnaire.as_e164, message)
				if obj.visa_notif_gerant and self.ordre.gerant:
					notif_by_sms(self.ordre.gerant.gerant_cd.phone.as_e164, message)
			except:
				import traceback
				traceback.print_exc()

	def get_mean_code(self):
		if self.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE:
			return "CH"
		elif self.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT:
			return "OV"
		else:
			return "--"


class VisaOrdrePayment(TimeStampedModel):
	prise_en_charge = models.OneToOneField(PrisEnchageOrdrePayment, verbose_name=_('ordre'), on_delete=models.CASCADE,
	                                       related_name="visa")
	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.CASCADE)
	observations = models.TextField(_('observations'), default="RAS")
	jour_comptable = models.ForeignKey(JourneeComptable, verbose_name=_('journée comptable'), related_name="+",
	                                   on_delete=models.SET_NULL, null=True, blank=True)
	cancel = models.BooleanField("Annuler ?", default=False, editable=False)
	reglement = models.CharField(_('Type règlement'), max_length=128, choices=TYPE_REGLEMENT.CHOICES)
	payment_mean = models.CharField(_('Moyen de paiement'), max_length=128, choices=PAYMENT_MEAN_TYPE.CHOICES)

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.id,)


class ReservationFond(TimeStampedModel):
	ordre = models.OneToOneField(OrdrePayment, verbose_name=_('ordre'), on_delete=models.CASCADE,
	                             related_name="reservationfond")
	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.CASCADE)
	amount = MoneyField(_('Montant'), max_digits=20, decimal_places=2, default_currency='XOF', null=True, default=0,
	                    validators=[MinMoneyValidator(0)])
	reliquat = MoneyField(_('Reliquat'), max_digits=20, decimal_places=2, default_currency='XOF', null=True, default=0,
	                      validators=[MinMoneyValidator(0)])
	observations = models.TextField(_('observations'), default="RAS")

	payment_mean = models.CharField(_('Moyen de paiement'), max_length=128, choices=PAYMENT_MEAN_TYPE.CHOICES,
	                                null=True, blank=True)
	reglement = models.CharField(_('Règlement'), max_length=128, choices=TYPE_REGLEMENT.CHOICES,
	                             null=True, blank=True)
	close = models.BooleanField("ferme", default=False)
	has_trx = models.BooleanField("has trx", default=False)
	has_cancel_op = models.BooleanField("has cancel op", default=False)

	objects = ReservationFondManager()

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.id,)

	def get_trx_amount(self):
		trx = self.rsv_trx.aggregate(total=Coalesce(Sum((F("fc_amount")), output_field=IntegerField()), Value(0)))
		total = trx["total"]
		return abs(total)

	def get_reliquat(self):
		return int(self.amount.amount) - self.get_trx_amount()

	def can_make_trx(self):
		trx = self.rsv_trx.aggregate(total=Coalesce(Sum((F("fc_amount")), output_field=IntegerField()), Value(0)))
		total = abs(trx["total"])
		if total < int(self.amount.amount):
			return True
		else:
			return False

	def can_make_trx_with_amount(self, amount):
		trx = self.rsv_trx.aggregate(total=Coalesce(Sum((F("fc_amount")), output_field=IntegerField()), Value(0)))
		total = abs(trx["total"])
		if total < int(self.amount.amount):
			reste = int(self.amount.amount) - total
			if reste >= int(amount):
				return True
			else:
				raise SigException("", "Montant {} supérieur au reste disponible {}".format(amount, reste))

		else:
			raise SigException("", "Impossible de faire le paiement")

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Reservation Fond')
		verbose_name_plural = _('Reservation Fond')


@receiver(pre_delete, sender=OrdrePayment)
def try_to_delete_op(sender, **kwargs):
	instance = kwargs['instance']
	if hasattr(instance, "reservationfond") and instance.reservationfond is not None:
		raise SigException(message="Impossible de supprimer cet ordre")


@receiver(post_delete, sender=OrdrePayment)
@transaction.atomic()
def unmark_cheque_as_use_for_op(sender, **kwargs):
	ordrepayment = kwargs['instance']
	if ordrepayment.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and ordrepayment.cheque and ordrepayment.etape == ETAPE_ORDRE_PAYMENT.SAISIE:
		try:
			from bankcheck.models import Cheque
			cheque = Cheque.objects.get(reference=ordrepayment.cheque)
			cheque.use = False
			cheque.amount = ordrepayment.amount
			cheque.cin_receptionnaire = None
			cheque.phone_receptionnaire = None
			cheque.trx = None
			cheque.use_date = None
			cheque.endosser_par = None
			cheque.phone_receptionnaire = None
			cheque.cin_receptionnaire = None
			cheque.save()
		except Cheque.DoesNotExist:
			pass


# @receiver(post_save, sender=ReservationFond)
def sendsignal_debit_account_balance(sender, **kwargs):
	print("entree dans ")
	instance = kwargs['instance']
	if kwargs.get('created', True):
		debit_account_balance_from_rsv(instance)


def debit_account_balance_from_rsv(reservationfond):
	instance = reservationfond
	ordre = instance.ordre
	if ordre.blocage:
		blocage = ordre.blocage
		current_balance = blocage.balance
		balance_after = current_balance - ordre.amount
		blocage.debit(ordre.amount)
	else:
		compte = ordre.compte
		current_balance = compte.balance
		balance_after = current_balance - ordre.amount
		ordre.balance_before = current_balance
		# compte.debit(ordre.amount)
		#compte.debit_by_type(ordre.amount.amount, ordre.typecompte,gestion=ordre.gestion_id)  # on debite en fonction ty type
	ordre.balance_after = balance_after
	ordre.save()


class Transaction(TimeStampedModel):
	# date_comptable = models.DateField("date comptable", max_length=12)
	jour_comptable = models.ForeignKey(JourneeComptable, verbose_name=_('journée comptable'), related_name="+",
	                                   on_delete=models.SET_NULL, null=True, blank=True)
	amount = MoneyField(_('Montant'), max_digits=20, decimal_places=2, default_currency='XOF', null=True, default=0,
	                    validators=[MinMoneyValidator(0)])
	reference = models.CharField(max_length=64, editable=False, verbose_name=_('Référence'), unique=True)
	origin_reference = models.CharField(max_length=64, editable=False, verbose_name=_('Origine référence'))

	libelle = models.CharField(max_length=128, editable=True, verbose_name=_('libellé'))
	nature_depense = models.CharField(max_length=128, editable=True, verbose_name=_('nature dépense'))

	account_depot = models.CharField(max_length=128, editable=False, verbose_name=_('compte de dépôt'))

	account_secondaire = models.CharField(max_length=128, editable=False, verbose_name=_('compte secondaire'))
	agent = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="agent comptable", on_delete=models.SET_NULL,
	                          related_name="+",
	                          null=True, blank=True)
	sens = models.CharField(_('Sens'), max_length=128, choices=SENS_TRX.CHOICES)
	payment_mean = models.CharField(_('Moyen de paiement'), max_length=128, choices=PAYMENT_MEAN_TYPE.CHOICES)
	status_aster = models.CharField(_('Statut Aster'), max_length=128, choices=STATUT_ASTER.CHOICES,
	                                default=STATUT_ASTER.ENCOURS)
	etape_compense = models.CharField(_('Etape compense'), max_length=128, choices=ETAPE_ASTER.CHOICES,
	                                  default=ETAPE_ASTER.NOUVEAU)
	date_envoi = models.DateTimeField("Date envoi", null=True, blank=True)
	date_retour = models.DateTimeField("Date retour", null=True, blank=True)
	poste_comptable = models.CharField(max_length=128, editable=True, verbose_name=_('poste '), null=True, blank=True)
	rib_cdd = models.CharField(max_length=24, editable=False, verbose_name=_('ri cdd '), null=True, blank=True)

	obs_aster = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('obs aster'))
	beneficiaire = models.CharField(max_length=128, verbose_name=_('Bénéficiaire '), null=True, blank=True)

	fc_amount = MoneyField(_('Valeur financiere'), max_digits=20, decimal_places=2, default_currency='XOF', null=True,
	                       default=0)
	type_nature = models.CharField(_('Type nature'), max_length=128, choices=NATURE_COMPTE.CHOICES,
	                               default=NATURE_COMPTE.FONCTIONNEMENT)

	typecompte = models.ForeignKey(TypeCompteTrx, verbose_name=_('Type de compte'), on_delete=models.SET_NULL,
	                               related_name="typecompte_trx", blank=True, null=True)

	date_rlv = models.DateTimeField("Date rlv", null=True, blank=True)
	is_cancel_trx_0 = models.BooleanField("Transaction d'annulation ?", default=False)

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Transaction')
		ordering = ["-created"]
		verbose_name_plural = _('Transaction')

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.reference,)

	def get_sens(self):
		if self.sens == SENS_TRX.DEBIT:
			return None
		else:
			return "A"

	def get_rlv(self):
		if hasattr(self, "transactionop") and self.transactionop.is_cancel_trx and self.transactionop.ref_trx:
			return self.created.date()
		else : return self.jour_comptable.jour

	def as_dict(self):
		data = {"sens": self.get_sens(), "libelle": self.libelle, "origin_reference": self.origin_reference,
		        "reference": self.reference, "compte": self.rib_cdd, "montant": float(self.amount.amount),
		        "payment_mean": self.payment_mean, "created": "{:%d/%m/%Y %H:%M}".format(self.created)}
		if self.jour_comptable:
			data.update({"gestion": self.jour_comptable.year(), "journee": self.jour_comptable.day()})
		if self.date_rlv:
			a = "{}".format(self.date_rlv.strftime('%d-%m-%Y'))
			data.update({"journee": a})
		if self.poste_comptable:
			data.update({"postecomptable_code": self.poste_comptable})
		if self.account_secondaire:
			data.update({"compte_destination": self.account_secondaire})
		if self.typecompte:
			data.update({"type_compte": self.typecompte.code})

		return data

	def get_mean_code(self):
		if self.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE:
			return "CH"
		elif self.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT:
			return "OV"
		else:
			return "--"

	def trx_amount(self):
		if self.sens == SENS_TRX.DEBIT:
			self.fc_amount = - self.amount
		elif self.sens == SENS_TRX.CREDIT:
			self.fc_amount = self.amount
		else:
			return 0

	def credit_amount_invest(self):
		if hasattr(self, "transactionop") and self.transactionop.is_cancel_trx and self.transactionop.ref_trx:
			return ""
		if self.sens == SENS_TRX.CREDIT and self.type_nature == NATURE_COMPTE.INVESTISSEMENT:
			return intcomma(int(self.amount.amount))
		else:
			return ""

	def credit_amount_fonct(self):
		if hasattr(self, "transactionop") and self.transactionop.is_cancel_trx and self.transactionop.ref_trx:
			return ""
		if self.sens == SENS_TRX.CREDIT and self.type_nature == NATURE_COMPTE.FONCTIONNEMENT:
			return intcomma(int(self.amount.amount))
		else:
			return ""

	def debit_amount_invest(self):
		if hasattr(self, "transactionop") and self.transactionop.is_cancel_trx and self.transactionop.ref_trx:
			if self.type_nature == NATURE_COMPTE.INVESTISSEMENT:
				return "-{}".format(intcomma(int(self.amount.amount)), )
			else: return ""
		if self.sens == SENS_TRX.DEBIT and self.type_nature == NATURE_COMPTE.INVESTISSEMENT:
			return intcomma(int(self.amount.amount))
		else:
			return ""

	def debit_amount_fonct(self):
		if hasattr(self, "transactionop") and self.transactionop.is_cancel_trx and self.transactionop.ref_trx:
			if self.type_nature == NATURE_COMPTE.FONCTIONNEMENT:
				return "-{}".format(intcomma(int(self.amount.amount)), )
			else: return ""
		if self.sens == SENS_TRX.DEBIT and self.type_nature == NATURE_COMPTE.FONCTIONNEMENT:

			return intcomma(int(self.amount.amount))
		else:
			return ""

	def debit_amount(self):
		if hasattr(self, "transactionop") and self.transactionop.is_cancel_trx and self.transactionop.ref_trx:
			return "-{}".format(intcomma(int(self.amount.amount)), )
		else:
			if self.sens == SENS_TRX.DEBIT:
				return intcomma(int(self.amount.amount))
			else:
				return ""

	def credit_amount(self):
		if hasattr(self, "transactionop") and self.transactionop.is_cancel_trx and self.transactionop.ref_trx:
			return ""
		else:
			if self.sens == SENS_TRX.CREDIT:
				return intcomma(int(self.amount.amount))
			else:
				return ""

	def get_number(self):

		d = ""
		if "-" in self.reference:
			d = self.reference.split("-")[1]
		return d

	def date_journee_comptable(self):
		if self.jour_comptable:
			return self.jour_comptable.jour
		else:
			return self.created.date()

	def save(self, **kwargs):
		self.trx_amount()
		if self.agent and self.jour_comptable is None:
			self.jour_comptable = self.agent.journee_comptables.filter(actif=True).last()
		if not self.reference:
			d = self.__class__._default_manager.filter(reference__startswith=self.origin_reference,
			                                           account_depot=self.account_depot).count() + 1
			reference_facture = "{}-{}".format(self.origin_reference, str(d))
			self.reference = reference_facture
		if not self.libelle:
			self.libelle = "TRX={}".format(self.reference, )

		return super().save(**kwargs)


class TransactionOP(Transaction):
	cheque = models.CharField(max_length=64, editable=False, verbose_name=_('Chèque associé'), null=True, blank=True)
	reservation = models.ForeignKey(ReservationFond, verbose_name="Réservation", on_delete=models.CASCADE,
	                                related_name="rsv_trx", )

	reglement = models.CharField(_('Type règlement'), max_length=128, choices=TYPE_REGLEMENT.CHOICES,
	                             default=TYPE_REGLEMENT.GLOBAL)

	has_cancel = models.BooleanField("Annuler", default=False)
	ref_canceltrx = models.CharField(max_length=64, editable=False, verbose_name=_("Opération annulée"), null=True,
	                                 blank=True)

	is_cancel_trx = models.BooleanField("Transaction d'annulation ?", default=False)
	ref_trx = models.CharField(max_length=64, editable=False, verbose_name=_('Opération source'), null=True, blank=True)

	objects = OPTransationManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Transaction OP')
		verbose_name_plural = _('Transaction OP')
		ordering = ['-pk']

	def save(self, *args, **kwargs):

		self.type_nature = self.reservation.ordre.type_nature

		return super().save(*args, **kwargs)

	def get_instance(self):
		return self

	def as_dict(self):
		d = super().as_dict()
		d.update({"comptable_id": self.reservation.ordre.compte.poste_id})

		if self.cheque:
			d.update({"cheque": self.cheque})

		type_op = ""
		if self.origin_reference.startswith("OP") == True:
			type_op = PAYMENT_MEAN_TYPE.RETRAIT
		elif self.origin_reference.startswith("OV") == True:
			type_op = PAYMENT_MEAN_TYPE.VIREMENT
		elif self.reservation.ordre.payment_mean == PAYMENT_MEAN_TYPE.MOBILE:
			type_op = type_op
		else:
			type_op = PAYMENT_MEAN_TYPE.CHEQUE

		d.update({"type_op": type_op})

		return d

	def labels(self):
		return ["COMPTE", "POSTE_COMPTABLE", "MONTANT"]

	def send_visa_msg(self, amount):
		obj = SettingsOP.object()
		if obj:
			message = self.reservation.ordre.get_visa_msg(amount)
			try:
				if obj.visa_notif_benef and self.reservation.ordre.phone_receptionnaire:
					notif_by_sms(self.reservation.ordre.phone_receptionnaire.as_e164, message)
				if obj.visa_notif_gerant and self.reservation.ordre.gerant:
					notif_by_sms(self.reservation.ordre.gerant.gerant_cd.phone.as_e164, message)
			except:
				import traceback
				traceback.print_exc()


def make_visa_from_ordrepayment(ordre_payment, instance, obs):
	visa = VisaOrdrePayment()
	visa.prise_en_charge = ordre_payment.prise_en_charge
	visa.amount = ordre_payment.prise_en_charge.amount
	visa.payment_mean = instance.payment_mean
	visa.reglement = instance.reglement
	visa.creator = instance.agent
	visa.observations = obs
	visa.save()
	ordre_payment.date_visa = datetime.datetime.now()
	ordre_payment.etape = ETAPE_ORDRE_PAYMENT.VISA
	ordre_payment.observations = obs
	ordre_payment.save()


from cddaccount.signals import op_status_changed, projet_status_changed
from django.dispatch.dispatcher import receiver


@receiver(op_status_changed, sender=OrdrePayment)
def delete_reservationconf(sender, **kwargs):
	try:
		ordre = kwargs['instance']
		if ordre.etape == ETAPE_ORDRE_PAYMENT.REJETE and ordre.previous_etape == ETAPE_ORDRE_PAYMENT.VALIDE and ordre.status == STATUS_ORDRE_PAYMENT.REJETE:
			if not hasattr(ordre, "prise_en_charge") and hasattr(ordre, "reservationfond"):

				amount = ordre.reservationfond.amount
				ordre.reservationfond.delete()
				ordre.etape = ETAPE_ORDRE_PAYMENT.SAISIE
				ordre.previous_etape = ETAPE_ORDRE_PAYMENT.SAISIE
				if ordre.blocage:
					blocage = ordre.blocage

					blocage.credit(amount)
				else:
					compte = ordre.compte

					# compte.credit(amount)
					compte.credit_by_type(amount, ordre.type_nature)
				ordre.save()
				obs = ObsOrdrePayment()
				obs.ordre = ordre
				obs.observations = ordre.observations
				obs.motif = ordre.status
				obs.creator = ordre.recepteur
				obs.save()
				ordre.save()
				ordre.send_rejet_msg()
	except:
		import traceback
		traceback.print_exc()
		pass


class AvisDeCredit(Transaction):
	reference_aster = models.CharField(max_length=64, verbose_name=_('Référence aster'), unique=True)
	compte = models.ForeignKey(CompteDepot, verbose_name=_('compte'), on_delete=models.CASCADE,
	                           related_name="avisdecredits")
	date_avis = models.DateField(_('Date avis'), max_length=12)
	nature = models.CharField(_('Disponible général'), max_length=128, choices=NATURE_COMPTE.CHOICES,
	                          default=NATURE_COMPTE.FONCTIONNEMENT)

	bocagefond = models.ForeignKey(BlocageFond, verbose_name="Blocage fond", on_delete=models.SET_NULL,
	                               related_name="+", null=True, blank=True)

	provenance = models.ForeignKey(PosteComptable, verbose_name=_('provenance'), on_delete=models.SET_NULL,
	                               related_name="+", null=True, blank=True)

	date_validation = models.DateTimeField('Date de validation', null=True, blank=True, max_length=20)

	agent_validation = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="agent validation",
	                                     on_delete=models.SET_NULL, related_name="+",
	                                     null=True, blank=True)

	ligne = models.CharField(max_length=64, verbose_name=_('ligne'), null=True, blank=True)
	objet = models.CharField(max_length=64, verbose_name=_('Objet'), null=True, blank=True, choices=TYPE_OBJECT.CHOICES,
	                         default=TYPE_OBJECT.AMENDEFORTAITAIRE)
	autres = models.CharField(max_length=64, verbose_name=_('autres'), null=True, blank=True)
	liod = models.CharField(max_length=64, verbose_name=_('liod'), null=True, blank=True)
	page = models.CharField(max_length=64, verbose_name=_('page'), null=True, blank=True)

	objects = AvisDeCreditManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Avis de Crédit')
		verbose_name_plural = _('Avis de Crédit')
		ordering = ['-pk']

	def as_dict(self):
		d = super().as_dict()
		d.update({"comptable_id": self.compte.poste_id})
		return d

	def labels(self):
		return ["COMPTE", "POSTE_COMPTABLE", "MONTANT"]

	def send_visa_msg(self, ):
		obj = SettingsOP.object()
		if obj:
			try:
				gerant = self.compte.get_current_gerant()
				if obj.visa_notif_gerant and gerant:
					message = self.get_avis_msg()
					notif_by_sms(gerant.phone.as_e164, message)
					print("envois sssm credit")
			except:
				import traceback
				traceback.print_exc()

	def get_avis_msg(self):
		compte = "Bienvenue sur SIGCDD "
		amount = self.amount.amount

		_date = "{:%d-%m-%Y %H:%M}".format(datetime.datetime.now())
		identifiant = "Votre avis de credit N {} d'un montant de {} est effectif. Date {} ".format(self.reference_aster,
		                                                                                           amount, _date)
		message = "{}. {}".format(compte, identifiant)
		return message

	def generate_reference(self):
		today = date.today()
		year = str(today.year)
		year = year[-2:]

		prefix = "AC{}".format(year, )
		# refs = self.__class__._default_manager.filter(created__year=today.year, created__month=today.month,created__day=today.day).values_list("sig_reference", flat=True)
		refs = self.__class__._default_manager.filter(compte=self.compte, created__year=today.year).values_list(
			"reference_aster", flat=True)

		nbs = len(
			refs) + 1  # self.__class__._default_manager.filter(created__year=today.year,created__month=today.month,created__day=today.day).count()+1

		b = f"{nbs}"
		b = b.zfill(6)
		new_ref = '{}{}'.format(prefix, b)
		if new_ref in refs:
			nb = getmax_value(refs, prefix) + 1
			b = f"{nb}"
			b = b.zfill(6)
			new_ref = '{}{}'.format(prefix, b)

		return new_ref

	def save(self, *args, **kwargs):
		if not self.compte.is_open():
			error = ValueError("Compte de depot non actif")
			raise error
		self.sens = SENS_TRX.CREDIT
		self.payment_mean = PAYMENT_MEAN_TYPE.VIREMENT
		self.account_depot = self.compte.short_compte
		self.poste_comptable = self.compte.poste.reference
		self.origin_reference = self.reference_aster
		self.nature_depense = self.libelle
		self.rib_cdd = self.compte.compte
		self.type_nature = self.nature

		if self.date_avis is None:
			self.date_avis = date.today()
		self.date_rlv = self.date_avis

		if not self.reference:
			self.reference_aster = self.generate_reference()
			self.origin_reference = self.reference_aster
			self.reference = self.reference_aster
		if self.typecompte:
			self.nature=self.typecompte.nature
			self.type_nature = self.nature


		return super().save(*args, **kwargs)

	@classmethod
	def check_if_api_open(cls):
		obj = SettingsOP.object()
		if obj and obj.api_avis_credit:
			return True
		else:
			return False

	def can_acces(self, user):
		return self.__class__._default_manager.filter(id=self.id).by_agent(user).exists()


class AvisDeDebit(Transaction):
	reference_aster = models.CharField(max_length=64, verbose_name=_('Référence aster'), unique=True)
	compte = models.ForeignKey(CompteDepot, verbose_name=_('compte'), on_delete=models.CASCADE,
	                           related_name="avisdedebits")
	disposition = models.CharField(_('Disponible général'), max_length=128, choices=DISPOSITION_TYPE.CHOICES,
	                               default=DISPOSITION_TYPE.COURANT)
	date_avis = models.DateField(_('Date avis'), max_length=12)

	projet = models.ForeignKey(Projet, verbose_name="project", on_delete=models.SET_NULL, related_name="+", null=True,
	                           blank=True, )

	date_validation = models.DateTimeField('Date de validation', null=True, blank=True, max_length=20)

	agent_validation = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="agent validation",
	                                     on_delete=models.SET_NULL, related_name="+",
	                                     null=True, blank=True)

	ligne = models.CharField(max_length=64, verbose_name=_('ligne'), null=True, blank=True)
	liod = models.CharField(max_length=64, verbose_name=_('liod'), null=True, blank=True)
	page = models.CharField(max_length=64, verbose_name=_('page'), null=True, blank=True)

	objects = AvisDeDebitManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Avis de Débit')
		verbose_name_plural = _('Avis de Débit')

		ordering = ['-pk']

	def as_dict(self):
		d = super().as_dict()
		d.update({"comptable_id": self.compte.poste_id})
		return d

	def labels(self):
		return ["COMPTE", "POSTE_COMPTABLE", "MONTANT"]

	@classmethod
	def check_if_api_open(cls):
		obj = SettingsOP.object()
		if obj and obj.api_avis_debit:
			return True
		else:
			return False

	def can_acces(self, user):
		return self.__class__._default_manager.filter(id=self.id).by_agent(user).exists()

	def generate_reference(self):
		today = date.today()
		year = str(today.year)
		year = year[-2:]

		prefix = "AD{}".format(year, )
		# refs = self.__class__._default_manager.filter(created__year=today.year, created__month=today.month,created__day=today.day).values_list("sig_reference", flat=True)
		refs = self.__class__._default_manager.filter(compte=self.compte, created__year=today.year).values_list(
			"reference_aster", flat=True)

		nbs = len(
			refs) + 1  # self.__class__._default_manager.filter(created__year=today.year,created__month=today.month,created__day=today.day).count()+1

		b = f"{nbs}"
		b = b.zfill(6)
		new_ref = '{}{}'.format(prefix, b)
		if new_ref in refs:
			nb = getmax_value(refs, prefix) + 1
			b = f"{nb}"
			b = b.zfill(6)
			new_ref = '{}{}'.format(prefix, b)

		return new_ref

	def save(self, *args, **kwargs):
		if not self.compte.is_open():
			error = ValueError("Compte de depot non actif")
			raise error
		self.sens = SENS_TRX.DEBIT
		self.payment_mean = PAYMENT_MEAN_TYPE.VIREMENT
		self.account_depot = self.compte.short_compte
		self.poste_comptable = self.compte.poste.reference
		self.nature_depense = self.libelle
		self.rib_cdd = self.compte.compte
		self.type_nature = self.disposition
		if self.date_avis is None:
			self.date_avis = date.today()
		self.date_rlv=self.date_avis

		if not self.reference:
			self.reference_aster = self.generate_reference()
			self.origin_reference = self.reference_aster
			self.reference = self.reference_aster

		if self.typecompte:
			self.disposition=self.typecompte.nature
			self.type_nature = self.disposition

		return super().save(*args, **kwargs)


#@receiver(post_save, sender=AvisDeDebit)
def debit_account_balance(sender, **kwargs):
	instance = kwargs['instance']
	if kwargs.get('created', True):
		if instance.jour_comptable.annee_comptable == AnneeComptable.active_gestion():
			try:
				compte = instance.compte
				# compte.debit(instance.amount)
				compte.debit_by_type(instance.amount.amount, instance.typecompte)

			except SigException as e:
				raise e


@receiver(post_save, sender=PrisEnchageOrdrePayment)
def set_journeecompt(sender, **kwargs):
	instance = kwargs['instance']
	if kwargs.get('created', True):
		if instance.ordre.jour_comptable is None:
			instance.ordre.jour_comptable = instance.creator.journee_comptables.filter(actif=True).last()
			instance.ordre.save()


@receiver(post_save, sender=AvisDeCredit)
def credit_account_balance(sender, **kwargs):
	instance = kwargs['instance']
	if kwargs.get('created', True):
		if instance.jour_comptable.annee_comptable == AnneeComptable.active_gestion():
			try:
				compte = instance.compte
				# compte.credit(instance.amount)
				#compte.credit_by_type(instance.amount, instance.typecompte.nature)
				instance.send_visa_msg()
			except SigException as e:
				raise e


def can_debit_trx_by_type_bf( amount, type, compute_disponible):
	type = type.nature
	if type == NATURE_COMPTE.FONCTIONNEMENT:
		balance = compute_disponible["fonct_balance"]["disponible"]
	elif type == NATURE_COMPTE.INVESTISSEMENT:
		balance = compute_disponible["invest_balance"]["disponible"]
	else:
		return False
	if balance >= amount:
		return True
	else:
		return False


def get_solde_by_type_bf( type, compute_disponible):
	balance = None
	if type.nature == NATURE_COMPTE.FONCTIONNEMENT:
		balance = compute_disponible["fonct_balance"]["disponible"]
	elif type.nature == NATURE_COMPTE.INVESTISSEMENT:
		balance = compute_disponible["invest_balance"]["disponible"]
	return balance






@receiver(projet_status_changed, sender=Projet)
@transaction.atomic()
def create_blocagefond(sender, **kwargs):
	try:
		projet = kwargs['instance']
		if projet.status == STATUS_ORDRE_PAYMENT.ACCEPTE and projet.accepter_blocage and not hasattr(projet,
		                                                                                             "blocagefond"):
			gestion_id=AnneeComptable.current_gestion().id

			compute_disponible = compute_all_balances_for_compte(projet.compte, update=False, gestion=gestion_id,
			                                                     for_gerant=True,
			                                                     type_compte=projet.typecompte)


			if can_debit_trx_by_type_bf(int(projet.amount.amount), projet.typecompte, compute_disponible):
				object = BlocageFond()
				object.projet = projet
				object.amount = projet.amount
				object.balance = projet.amount
				object.compte = projet.compte
				object.creator = projet.agent_postecomptable
				object.prestataire = projet.prestataire
				object.compte_iban = projet.compte_iban
				object.ninea = projet.ninea
				object.ref_marche = projet.ref_marche
				object.open_date = projet.period.lower
				object.open_date = projet.period.upper
				object.save()
			else:
				raise SigException("Montant suupérieur au solde du compte")
	except:
		import traceback
		traceback.print_exc()
		raise SigException("Erreur sur le blocage de fond")


@receiver(post_save, sender=BlocageFond)
def debit_account_after_new_bf(sender, **kwargs):
	instance = kwargs['instance']
	if kwargs.get('created', True):
		try:
			compte = instance.compte
			#compte.debit(instance.amount)
		except SigException as e:
			raise e


class AnnulationBlocageFond(TimeStampedModel):
	# date_comptable=models.DateField("date comptable", max_length=12)
	reference = models.CharField(_('référence'), max_length=128, unique=True)
	blocage = models.OneToOneField(BlocageFond, verbose_name=_('projet'), related_name="annulationblocagefond",
	                               on_delete=models.CASCADE)
	compte = models.ForeignKey(CompteDepot, verbose_name=_('compte'), related_name="+", on_delete=models.CASCADE)
	amount = MoneyField(_('Montant'), max_digits=20, decimal_places=2, default_currency='XOF', default=0,
	                    validators=[MinMoneyValidator(0)])
	demandeur = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.CASCADE)
	approbateur = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.SET_NULL, null=True,
	                                blank=True)
	approbation_date = models.DateTimeField(_('Date approbation'), max_length=12, null=True, blank=True)

	approuver = models.BooleanField("Valider", default=False)

	observations = models.TextField(_('observations'), default="RAS")

	objects = AnnulationBlocageFondManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Annulation Blocage de fonds')
		verbose_name_plural = _('Annulations Blocages de fonds')
		#

		permissions = [
			("approuver_annulationblocagefond", "Peut valider demande annulation fond bloque")
		]

	def __str__(self):
		return "{}".format(self.reference, )

	def get_instance(self):
		return self

	def can_acces(self, user):
		return self.__class__._default_manager.filter(id=self.id).by_agent(user).exists()


class AnnulationOrdrePayment(TimeStampedModel):
	ordre = models.OneToOneField(OrdrePayment, verbose_name=_('ordre'), on_delete=models.CASCADE,
	                             related_name="annulation_op")
	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.CASCADE)

	etape = models.CharField(_('Statut'), max_length=128, choices=ETAPE_ORDRE_PAYMENT.CHOICES,
	                         default=ETAPE_ORDRE_PAYMENT.SAISIE)
	observations = models.TextField(_('observations'), default="RAS")

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.id,)


@transaction.atomic()
def cancel_op(op, user, observations):
	try:
		if op.can_cancel():
			annulationOrdrePayment = AnnulationOrdrePayment()
			annulationOrdrePayment.ordre = op
			annulationOrdrePayment.creator = user
			# annulationOrdrePayment.etape=op.etape
			# op.etape == "ACCEPTE"
			annulationOrdrePayment.etape = op.etape
			annulationOrdrePayment.observations = observations
			annulationOrdrePayment.save()
			if hasattr(op, "prise_en_charge"):
				# on tag la prise en charge
				op.prise_en_charge.cancel = True
				op.prise_en_charge.save()
				if hasattr(op.prise_en_charge, "visa"):
					op.prise_en_charge.visa.cancel = True
					op.prise_en_charge.visa.save()
					if op.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and op.cheque and not op.cheque_delivred:
						# on verifie si le cheque est receptionne
						from bankcheck.models import Cheque
						cheque = Cheque.objects.get(reference=op.cheque)
						cheque.observations = "Ordre de paiement lie à ce cheque a tete annulé"
						cheque.save()

			if hasattr(op, "reservationfond"):
				amount = op.reservationfond.amount
				rsv = op.reservationfond
				rsv.delete()
				if op.blocage:
					blocage = op.blocage
					blocage.credit(amount)
				else:
					compte = op.compte
					# compte.credit(amount)
					compte.credit_by_type(amount, op.type_nature)
	except SigException as e:
		raise e


@transaction.atomic()
def reject_pec_op(op, user, observations):
	try:
		priseencharge = None
		if hasattr(op, "prise_en_charge"):
			priseencharge = op.prise_en_charge
			if hasattr(priseencharge, "visa"):
				ex = SigException(message="Opération déjà visée")
				raise ex

		if hasattr(op, "reservationfond"):
			amount = op.reservationfond.amount
			rsv = op.reservationfond
			t = rsv.get_trx_amount()
			if t > 0:
				ex = SigException(message="Opération déjà visée")
				raise ex
		if priseencharge is not None:
			priseencharge.delete()
		op.etape = ETAPE_ORDRE_PAYMENT.ACCEPTE
		op.previous_etape = ETAPE_ORDRE_PAYMENT.VALIDE

		op.observations = observations
		op.save()
		obs = ObsOrdrePayment()
		obs.ordre = op
		obs.observations = op.observations
		obs.motif = op.status
		obs.creator = user
		obs.save()
	# op.send_rejet_msg()
	except SigException as e:
		raise e


@transaction.atomic()
def cancel_op(op, user, observations):
	try:
		if op.can_cancel():
			annulationOrdrePayment = AnnulationOrdrePayment()
			annulationOrdrePayment.ordre = op
			annulationOrdrePayment.creator = user
			# op.etape=="ACCEPTE"
			annulationOrdrePayment.etape = op.etape
			annulationOrdrePayment.observations = observations
			annulationOrdrePayment.save()
			if hasattr(op, "prise_en_charge"):
				# on tag la prise en charge
				op.prise_en_charge.cancel = True
				op.prise_en_charge.save()
				if hasattr(op.prise_en_charge, "visa"):
					op.prise_en_charge.visa.cancel = True
					op.prise_en_charge.visa.save()
					if op.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and op.cheque and not op.cheque_delivred:
						# on verifie si le cheque est receptionne
						from bankcheck.models import Cheque
						cheque = Cheque.objects.get(reference=op.cheque)
						cheque.observations = "Ordre de paiement lie à ce cheque a tete annulé"
						cheque.save()

			if hasattr(op, "reservationfond"):
				amount = op.reservationfond.amount
				rsv = op.reservationfond
				rsv.delete()
				if op.blocage:
					blocage = op.blocage
					blocage.credit(amount)
				else:
					compte = op.compte
					compte.credit_by_type(amount, op.type_nature)
	except SigException as e:
		raise e @ transaction.atomic()


@transaction.atomic()
def rejete_priseencharge_op(op, user, observations):
	try:
		priseencharge = None
		if hasattr(op, "prise_en_charge"):
			priseencharge = op.prise_en_charge
			if hasattr(priseencharge, "visa"):
				ex = SigException(message="Opération déjà visée")
				raise ex

		if hasattr(op, "reservationfond"):
			amount = op.reservationfond.amount
			rsv = op.reservationfond
			t = rsv.get_trx_amount()
			if t > 0:
				ex = SigException(message="Opération déjà visée")
				raise ex
			#on verifie les trx_op
			for trx_op in rsv.rsv_trx.all():
				trx_op.delete(keep_parents=True)

			rsv.delete()
			if op.blocage:
				blocage = op.blocage
				blocage.credit(amount)
			#else:
			#	compte = op.compte
			#	compte.credit_by_type(amount, op.type_nature)

		if priseencharge is not None:
			priseencharge.delete()

		creator = op.creator
		if hasattr(creator, "agent_postecomptable"):
			op.etape = ETAPE_ORDRE_PAYMENT.VALIDE
			op.previous_etape = ETAPE_ORDRE_PAYMENT.SAISIE
		else:
			op.etape = ETAPE_ORDRE_PAYMENT.SAISIE
			op.previous_etape = ETAPE_ORDRE_PAYMENT.SAISIE
		op.observations = observations
		op.save()
		obs = ObsOrdrePayment()
		obs.ordre = op
		obs.observations = op.observations
		obs.motif = op.status
		obs.creator = user
		obs.save()
		op.send_rejet_msg()
	except SigException as e:
		raise e


class Report(TimeStampedModel):
	compte = models.ForeignKey(CompteDepot, verbose_name=_('compte'), related_name="+", on_delete=models.CASCADE)
	taux_fonc = models.DecimalField(_('taux fonctionnement'), max_digits=20, decimal_places=2, default=0)
	taux_invest = models.DecimalField(_('taux investissement'), max_digits=20, decimal_places=2, default=0)
	amount_fonc = MoneyField(_('Montant fonctionnement '), max_digits=20, decimal_places=2, default_currency='XOF',
	                         default=0, validators=[MinMoneyValidator(0)])
	amount_invest = MoneyField(_('Montant investissement '), max_digits=20, decimal_places=2, default_currency='XOF',
	                           default=0, validators=[MinMoneyValidator(0)])

	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.CASCADE)
	anne_comptable = models.ForeignKey(AnneeComptable, related_name="+", on_delete=models.CASCADE,
	                                   verbose_name=_('Gestion'), )

	gestion_courant = models.ForeignKey(AnneeComptable, verbose_name=_('Gestion current'), related_name="+",
	                                    on_delete=models.CASCADE)


	objects = ReportManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Report')
		ordering = ['-pk']
		verbose_name_plural = _('Reports')
		unique_together = ("compte", "anne_comptable")

	def __str__(self):
		return "{}".format(self.id, )



class ReportGestion(TimeStampedModel):
	compte = models.ForeignKey(CompteDepot, verbose_name=_('compte'), related_name="compte_reports", on_delete=models.CASCADE)
	taux = models.DecimalField(_('taux'), max_digits=20, decimal_places=2, default=0)

	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.CASCADE)
	anne_comptable = models.ForeignKey(AnneeComptable, related_name="+", on_delete=models.CASCADE,
	                                   verbose_name=_('Gestion'), )

	gestion_courant = models.ForeignKey(AnneeComptable, verbose_name=_('Gestion current'), related_name="+",
	                                    on_delete=models.CASCADE)

	typecompte = models.ForeignKey(TypeCompteTrx, verbose_name=_('Type de compte'), on_delete=models.CASCADE,
	                               related_name="+", )
	amount = MoneyField(_('Montant'), max_digits=20, decimal_places=2, default_currency='XOF',
	                           default=0, validators=[MinMoneyValidator(0)])
	f_amount = MoneyField(_('Montant financiaire'), max_digits=20, decimal_places=2, default_currency='XOF',
	                    default=0)
	sens = models.CharField(_('Sens'), max_length=128, choices=SENS_TRX.CHOICES)

	objects = ReportManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Report gestion')
		ordering = ['-pk']
		verbose_name_plural = _('Reports de Gestion')

	def __str__(self):
		return "{}".format(self.id, )
	def save(self, *args, **kwargs):
		self.f_amount = self.amount
		if self.sens==SENS_TRX.DEBIT:
			self.f_amount=-self.amount
		return super().save(*args, **kwargs)

def generate_data(type):
	if type == DirType.CHEQUE:
		datas = [item.as_dict() for item in
		         TransactionOP.objects.filter(etape_compense=ETAPE_ASTER.NOUVEAU).exclude(cheque=None)]
	elif type == DirType.VIREMENT:
		datas = [item.as_dict() for item in
		         TransactionOP.objects.filter(etape_compense=ETAPE_ASTER.NOUVEAU, cheque=None)]
	elif type == DirType.AVISCREDIT:
		datas = [item.as_dict() for item in AvisDeCredit.objects.filter(etape_compense=ETAPE_ASTER.NOUVEAU)]
	elif type == DirType.AVISDEBIT:
		datas = [item.as_dict() for item in AvisDeDebit.objects.filter(etape_compense=ETAPE_ASTER.NOUVEAU)]
	elif type == DirType.COMPTE_DEPOT:
		datas = [item.as_dict() for item in CompteDepot.objects.all()]
	else:
		datas = []
	labels = []
	return datas


def generate_trx_data(payload):
	try:
		type = payload["type"]
		filters = {"etape_compense": ETAPE_ASTER.NOUVEAU}
		if "etape_compense" in payload:
			filters = {"etape_compense": payload["etape_compense"]}
		if "poste_comptable" in payload:
			filters.update({"poste_comptable": payload["poste_comptable"]})
		if "journee_comptable" in payload:
			format = "%d-%m-%Y"
			journee = datetime.datetime.strptime(payload["journee_comptable"], format)
			filters.update({"jour_comptable__jour": journee.date()})

		if type == DirType.CHEQUE:
			datas = [item.as_dict() for item in TransactionOP.objects.filter(**filters).exclude(cheque=None)]
		elif type == DirType.VIREMENT:
			filters.update({"cheque": None})
			datas = [item.as_dict() for item in TransactionOP.objects.filter(**filters)]
		elif type == DirType.AVISCREDIT:
			datas = [item.as_dict() for item in AvisDeCredit.objects.filter(**filters)]
		elif type == DirType.AVISDEBIT:
			datas = [item.as_dict() for item in AvisDeDebit.objects.filter(**filters)]
		else:
			datas = []
	except:
		traceback.print_exc()
		datas = []
	return datas


class SettingsVRM(TimeStampedModel):
	taille = models.PositiveSmallIntegerField("Taille")
	max_amount = MoneyField(_('Montant max par ligne'), max_digits=20, decimal_places=2, default_currency='XOF',
	                        null=True, default=0,
	                        validators=[MinMoneyValidator(0), MaxMoneyValidator(50000000)])

	w_max_amount = MoneyField(_('Montant max par ligne mobile'), max_digits=20, decimal_places=2,
	                          default_currency='XOF',
	                          null=True, default=0,
	                          validators=[MinMoneyValidator(0), MaxMoneyValidator(50000000)])
	w_taille = models.PositiveSmallIntegerField("Taille mobile")

	remove_dp = models.BooleanField("Supprime les duplicatat", default=False)

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Virement Masse Configuration')

	@classmethod
	def object(cls):
		return cls._default_manager.all().first()  # Since only one item

	def __str__(self):
		return "{}".format(self.id, )


class VirementMasse(OrdrePayment):
	details_file = models.FileField(upload_to=virmasse_directory_path, verbose_name=_('Fichier details'))
	hash_file = models.CharField("hash", max_length=128)

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Virement Masse')
		ordering = ['-pk']

	def __str__(self):
		return "{}".format(self.id, )

	def get_virements_details(self):
		return [item.as_dict() for item in self.details_virements.all()]

	def mobile_as_dict(self):
		lines = [item.mobile_as_dict() for item in self.details_virements.all()]
		data = {
			"callBackUrl": self.pay_cbk_link(),
			"dateOrdre": "{:%d/%m/%Y %H:%M:%S}".format(self.created),
			"identifiantExterne": self.sig_reference,
			"lignes": lines,
			"mois": MonthType.DICT_NUMBER_TO_MONTHS[str(self.created.month)],
			"posteComptableCode": self.compte.poste.reference,
			"perimetreFonctionnelCode": "SALAIRES",
			"donneurOrdreCode": "SIGCDD"
		}
		return data


class VirementDetails(TimeStampedModel):
	reference = models.CharField("Référence", max_length=128, unique=True)
	reference_aster = models.CharField("Référence Aster", max_length=128)
	reference_virement = models.CharField("Référence virement", max_length=128, editable=False)
	virement = models.ForeignKey(OrdrePayment, verbose_name=_('Virement'), related_name="details_virements",
	                             on_delete=models.CASCADE)
	compte_depot = models.CharField("Compte de dépôt", max_length=30)
	poste = models.CharField("Poste comptable", max_length=5)

	beneficiaire = models.CharField("Bénéficiare", max_length=128)
	adresse_benef = models.CharField("Adresse bénéficiaire", max_length=128)
	# iban_benef = models.CharField(_('Compte bancaire bénéf'), max_length=30)
	iban_benef = models.CharField(_('Compte bénéficiaire'), max_length=24)

	donneur = models.CharField("Donneur", max_length=45)
	phone_benef = models.CharField(_('Tél bénéficiaire'), max_length=15, null=True, blank=True)
	adresse_donneur = models.CharField("Adresse donneur", max_length=50, default="DGCPT")
	iban_donneur = models.CharField(_('Compte bancaire donneur'), max_length=24, null=True, blank=True)

	libelle = models.CharField(_('Libellé'), max_length=128, null=True, blank=True)

	amount = MoneyField(_('Montant'), max_digits=20, decimal_places=2, default_currency='XOF', null=True, default=0,
	                    validators=[MinMoneyValidator(0), MaxMoneyValidator(50000000)])

	date_payement = models.DateField("Date paiement", max_length=128)

	status_aster = models.CharField(_('Statut Aster'), max_length=128, choices=STATUT_ASTER.CHOICES,
	                                default=STATUT_ASTER.ENCOURS)
	etape_compense = models.CharField(_('Etape Compense'), max_length=128, choices=ETAPE_ASTER.CHOICES,
	                                  default=ETAPE_ASTER.NOUVEAU)
	date_envoi = models.DateTimeField("Date envoie", null=True, blank=True)
	date_retour = models.DateTimeField("Date retour", null=True, blank=True)

	obs_aster = models.CharField(max_length=120, null=True, blank=True, verbose_name=_('obs aster'))

	wallet_provider = models.CharField(max_length=128, editable=True, verbose_name=_('Wallet  provider'), null=True,
	                                   blank=True)
	wallet_number = models.CharField(max_length=128, editable=True, verbose_name=_('Wallet number'), null=True,
	                                 blank=True)
	cin = models.CharField(max_length=128, editable=True, verbose_name=_('cin'), null=True,
	                       blank=True)
	dob = models.CharField(max_length=128, editable=True, verbose_name=_('date naissance'), null=True,
	                       blank=True)
	lieu_dob = models.CharField(max_length=128, editable=True, verbose_name=_('lieu naissance'), null=True,
	                            blank=True)
	payment_mean = models.CharField(_('Moyen paiement'), max_length=128, choices=PAYMENT_MEAN_TYPE.CHOICES,
	                                default=PAYMENT_MEAN_TYPE.VIREMENT)

	firstname = models.CharField("Prénom", max_length=128, null=True,
	                             blank=True)
	lastname = models.CharField("nom", max_length=128, null=True,
	                            blank=True)

	trx = models.ForeignKey(Transaction, verbose_name="transaction", related_name="trx_detailvirements", null=True,
	                        blank=True, on_delete=models.SET_NULL)
	objects = VirementDetailsManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Virement details')
		# unique_together=("reference_aster","date_payement")
		ordering = ['-pk']

	def __str__(self):
		return "{}".format(self.id, )

	def getmax_value(self, refs):
		d = 0
		for item in refs:
			nu = item[-6:]
			nu = nu.lstrip("0")
			v = int(nu)
			if v > d:
				d = v
		return d
	
	#def generate_dv_reference(self, max_ids=None):
	#	prefix = "CD"

	#	if max_ids is not None:
	#		try:
	#			current = int(max_ids)
	#		except (TypeError, ValueError):
	#			current = 0
	#	else:
	#		agg = (
	#			self.__class__._default_manager
	#			.filter(compte_depot=self.compte_depot, reference_aster__startswith=prefix)
	#			.annotate(num=Cast(Substr('reference_aster', 3, 6), IntegerField()))
	#			.aggregate(max_num=Max('num'))
	#		)
	#		current = agg["max_num"] or 0

	#	nxt = (current % 999999) + 1
	#	new_ref = f"{prefix}{nxt:06d}"
	#
	#	# vérifie si la référence existe déjà (sécurité supplémentaire)
	#	for _ in range(999999):
	#		if not self.__class__._default_manager.filter(reference_aster=new_ref).exists():
	#			return new_ref
	#		nxt = (nxt % 999999) + 1
	#		new_ref = f"{prefix}{nxt:06d}"

	#	raise RuntimeError("Impossible de générer une référence unique.")

	def generate_dv_reference(self, *_):
		prefix = "CD"
		# on limite quelques tentatives au cas (rare) de collision quand la séquence recycle
		for _ in range(5):
			with connection.cursor() as cur:
				cur.execute("SELECT nextval('sigcdd_dv_ref_seq')")
				n = cur.fetchone()[0]  # 1..999999999 (CYCLE)
			ref = f"{prefix}{n:09d}"
			# Option A: retourner directement; gérer IntegrityError au save()
			return ref
		raise RuntimeError("Impossible d'obtenir une référence (séquence saturée).")

	def save(self, *args, **kwargs):
		if not self.reference:
			self.reference_virement = self.virement.sig_reference
			try:
				if not self.reference_aster:
					self.reference_aster = self.generate_dv_reference()
				self.reference = "{}-{}".format(self.reference_virement, self.reference_aster)
			except:
				error = ValueError("A possible infinite loop was detected")
				raise error

		if self.payment_mean != PAYMENT_MEAN_TYPE.MOBILE and self.iban_benef and len(self.iban_benef) > 10:
			iban = self.iban_benef.replace(" ", "")
			country_code = iban[:2]
			rib = iban[-2:]
			cal_rib = generate_rib(country_code, iban)
			if rib != cal_rib:
				raise ValueError("Compte bancaire beneficiaire non conforme")
		return super().save(*args, **kwargs)

	def as_dict(self):
		libelle = "{}/{}".format(self.virement.sig_reference, self.libelle)
		data = {"adresse_beneficiaire": self.adresse_benef[0:45], "nom_beneficiaire": self.beneficiaire[0:45],
		        "rib_beneficiaire": self.iban_benef, "rib_donneur": self.iban_donneur,
		        "cpt_aster": self.virement.compte.short_compte, "libelle": libelle[0:45],
		        "num_interne_ordre": self.reference_virement, "reference": self.reference_aster,
		        "compte": self.compte_depot, "montant": float(self.amount.amount),
		        "date_ordre": "{:%d/%m/%Y}".format(self.created),
		        "date_payement": "{:%d/%m/%Y}".format(self.date_payement)}
		if self.poste:
			data.update({"poste": self.poste})
			data.update({"nom_donneur": self.donneur})
			data.update({"adresse_donneur": self.adresse_donneur})
		if self.trx:
			data.update({"transaction": self.trx.reference})

		data.update({"num_interne_ordre": None})  #

		data.update(
			{"type_operation": "015", "sens": "A", "source": "C", "type_rib_donneur": "2", "type_rib_beneficiaire": "2",
			 "traite": "0"})
		return data

	def mobile_as_dict(self):
		libelle = "{}/{}".format(self.virement.sig_reference, self.libelle)
		data = {"annee": self.created.year,
		        "cni": self.cin,
		        "DATEENROLEMENT ": self.dob,
		        "etatPaiement": "NEW",
		        "libelleOperation": libelle[0:45],
		        "LOCALITE": self.lieu_dob,
		        "mois": MonthType.DICT_NUMBER_TO_MONTHS[str(self.created.month)],
		        "montant": float(self.amount.amount),
		        "nomBeneficiaire": self.lastname,
		        "numeroCompte": self.wallet_number,
		        "operateur": self.wallet_provider,
		        "prenomBeneficiaire": self.firstname
		        }
		return data


@receiver(post_save, sender=TransactionOP)
def debit_account_balance(sender, **kwargs):
	instance = kwargs['instance']
	if kwargs.get('created', True):
		if instance.sens == SENS_TRX.DEBIT:
			complete_trx_process(instance)
			instance.send_visa_msg(instance.amount.amount)
		# balance = instance.reservation.ordre.compte.acc_balance.filter(anne_comptable=instance.jour_comptable.annee_comptable).last()
		# if balance: update_balance(balance)
		elif instance.sens == SENS_TRX.CREDIT:
			reservation = instance.reservation
			total = reservation.get_trx_amount()
			if reservation.amount >= Money(total, "XOF"):
				reservation.reliquat = reservation.amount - Money(total, "XOF")
			reservation.close = False
			reservation.save()


def complete_trx_process(instance):
	try:
		reservation = instance.reservation
		total = reservation.get_trx_amount()
		if reservation.amount > Money(total, "XOF"):
			reservation.reliquat = reservation.amount - Money(total, "XOF")
		else:
			reservation.reliquat = 0
			reservation.close = True
		reservation.payment_mean = instance.payment_mean
		reservation.reglement = instance.reglement
		reservation.has_trx = True
		reservation.save()

		ordre = reservation.ordre
		# create des lignes details virement pour les virement
		if not hasattr(reservation.ordre, "virementmasse") and instance.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT:
			if instance.amount <= Money(50000000, "XOF"):
				ob = VirementDetails()
				ob.amount = instance.amount
				ob.virement = ordre
				ob.reference_donneur = instance.reference
				ob.libelle = instance.libelle
				ob.payment_mean = PAYMENT_MEAN_TYPE.VIREMENT
				ob.beneficiaire = ordre.beneficiaire
				ob.iban_donneur = ordre.compte.poste.comptebanque
				ob.adresse_benef = "Divers bénéficiaires"
				ob.iban_benef = instance.account_secondaire
				ob.date_payement = instance.jour_comptable.jour
				ob.compte_depot = ordre.compte.short_compte
				ob.poste = ordre.compte.poste.reference
				ob.adresse_donneur = "DGCPT"
				ob.donneur = "DGCPT_{}".format(ob.poste, )
				ob.trx = instance
				ob.save()
		else:
			ordre.details_virements.all().update(trx=instance, date_payement=instance.jour_comptable.jour)

		if reservation.get_reliquat() == 0 or instance.reglement == TYPE_REGLEMENT.GLOBAL:
			make_visa_from_ordrepayment(ordre, instance, "Visa effectué avec succès")

	except SigException as e:
		traceback.print_exc()
		raise e
	except:
		traceback.print_exc()
		raise SigException(message="erreur inconnue")


class Balance(TimeStampedModel):
	compte = models.ForeignKey(CompteDepot, verbose_name=_('compte depot'), on_delete=models.CASCADE,
	                           related_name="acc_balance")
	provenance = models.CharField("solde",max_length=128)
	be_credit_fonc = MoneyField(_('Balance entre crédit fonc'), max_digits=20, decimal_places=2, default_currency='XOF',
	                            default=0, validators=[MinMoneyValidator(0)])
	be_credit_inv = MoneyField(_('Balance entre crédit inv'), max_digits=20, decimal_places=2, default_currency='XOF',
	                           default=0, validators=[MinMoneyValidator(0)])
	op_credit_fonc = MoneyField(_('Opération  crédit fonc'), max_digits=20, decimal_places=2, default_currency='XOF',
	                            default=0, validators=[MinMoneyValidator(0)])
	op_credit_inv = MoneyField(_('Opération  crédit inv'), max_digits=20, decimal_places=2, default_currency='XOF',
	                           default=0, validators=[MinMoneyValidator(0)])
	op_debit_fonc = MoneyField(_('Opération  crédit fonc'), max_digits=20, decimal_places=2, default_currency='XOF',
	                           default=0, validators=[MinMoneyValidator(0)])
	op_debit_inv = MoneyField(_('Opération  débit inv'), max_digits=20, decimal_places=2, default_currency='XOF',
	                          default=0, validators=[MinMoneyValidator(0)])

	total_credit_fonc = MoneyField(_('Total  crédit fonc'), max_digits=20, decimal_places=2, default_currency='XOF',
	                               default=0, validators=[MinMoneyValidator(0)])
	total_credit_inv = MoneyField(_('Total  crédit inv'), max_digits=20, decimal_places=2, default_currency='XOF',
	                              default=0, validators=[MinMoneyValidator(0)])
	total_debit_fonc = MoneyField(_('Total  crédit fonc'), max_digits=20, decimal_places=2, default_currency='XOF',
	                              default=0, validators=[MinMoneyValidator(0)])
	total_debit_inv = MoneyField(_('Total  débit inv'), max_digits=20, decimal_places=2, default_currency='XOF',
	                             default=0, validators=[MinMoneyValidator(0)])

	bs_credit_fonc = MoneyField(_('Balance sortie  crédit fonc'), max_digits=20, decimal_places=2,
	                            default_currency='XOF',
	                            default=0, validators=[MinMoneyValidator(0)])
	bs_credit_inv = MoneyField(_('Balance sortie  crédit inv'), max_digits=20, decimal_places=2, default_currency='XOF',
	                           default=0, validators=[MinMoneyValidator(0)])
	bs_debit_fonc = MoneyField(_('Balance sortie  crédit fonc'), max_digits=20, decimal_places=2,
	                           default_currency='XOF',
	                           default=0, validators=[MinMoneyValidator(0)])
	bs_debit_inv = MoneyField(_('Balance sortie  débit inv'), max_digits=20, decimal_places=2, default_currency='XOF',
	                          default=0, validators=[MinMoneyValidator(0)])
	anne_comptable = models.ForeignKey(AnneeComptable, related_name="+", on_delete=models.CASCADE)
	objects = BalanceManager()

	# ("compte","be_credit_fonc","be_credit_inv","op_credit_fonc","op_credit_inv","op_debit_inv","op_debit_fonc","total_credit_fonc","total_credit_inv","total_debit_inv","total_debit_fonc","bs_credit_fonc","bs_credit_inv","bs_debit_inv","bs_debit_fonc")

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Balance')
		verbose_name_plural = _('Balance')
		unique_together = ("compte", "anne_comptable")

	def __str__(self):
		# noinspection PyPep8
		return "{}".format(self.compte, )

	def has_no_entries(self):
		if self.be_credit_inv == Money(0, "XOF") and self.be_credit_fonc == Money(0,
		                                                                          "XOF") and self.op_debit_fonc == Money(
				0, "XOF") and self.op_debit_inv == Money(0, "XOF") and self.op_credit_inv == Money(0,
		                                                                                           "XOF") and self.op_credit_fonc == Money(
				0, "XOF"):
			return True
		else:
			return False

	def balance_to_dict(self):
		a = {"be_credit_fonc": int(self.be_credit_fonc.amount), "be_credit_inv": int(self.be_credit_inv.amount),
		     "op_debit_fonc": int(self.op_debit_fonc.amount), "op_debit_inv": int(self.op_debit_inv.amount),
		     "op_credit_fonc": int(self.op_credit_fonc.amount), "op_credit_inv": int(self.op_credit_inv.amount),

		     "total_debit_fonc": int(self.total_debit_fonc.amount),
		     "total_debit_inv": int(self.total_debit_inv.amount),
		     "total_credit_fonc": int(self.total_credit_fonc.amount),
		     "total_credit_inv": int(self.total_credit_inv.amount),

		     "bs_debit_fonc": int(self.bs_debit_fonc.amount),
		     "bs_debit_inv": int(self.bs_debit_inv.amount),
		     "provenance":self.provenance,
		     "bs_credit_fonc": int(self.bs_credit_fonc.amount), "bs_credit_inv": int(self.bs_credit_inv.amount),
		     "libelle": self.compte.libelle_court, "poste": self.compte.poste.name, "compte": self.compte.short_compte
		     }
		return a





from djmoney.money import Money

@receiver(post_save, sender=Report)
def credit_account_balance_by_report(sender, **kwargs):
	instance = kwargs['instance']
	if kwargs.get('created', True):
		try:
			if instance.gestion_courant == AnneeComptable.active_gestion():
				compte = instance.compte
				compte.credit_by_type(instance.amount_fonc, NATURE_COMPTE.FONCTIONNEMENT)
				compte.credit_by_type(instance.amount_invest, NATURE_COMPTE.INVESTISSEMENT)
				balance = compte.acc_balance.filter(anne_comptable=instance.gestion_courant).last()
				if balance: update_balance(balance)

		except SigException as e:
			raise e


def update_balance_credit(account, amount, type):
	balance = account.acc_balance
	if type == NATURE_COMPTE.FONCTIONNEMENT:
		balance.total_credit_fonc = balance.total_credit_fonc + amount
		balance.bs_credit_fonc = balance.bs_credit_fonc + amount
		balance.op_credit_fonc = balance.op_credit_fonc + amount

	if type == NATURE_COMPTE.INVESTISSEMENT:
		balance.bs_credit_inv = balance.bs_credit_inv + amount
		balance.total_credit_inv = balance.total_credit_inv + amount
		balance.op_credit_inv = balance.op_credit_inv + amount


def update_balance_debit(account, amount, type):
	balance = account.acc_balance
	if type == NATURE_COMPTE.FONCTIONNEMENT:
		balance.total_debit_fonc = balance.total_debit_fonc + amount
		balance.bs_debit_fonc = balance.bs_debit_fonc + amount
		balance.op_debit_fonc = balance.op_debit_fonc + amount

	if type == NATURE_COMPTE.INVESTISSEMENT:
		balance.bs_debit_inv = balance.bs_debit_inv + amount
		balance.total_debit_inv = balance.total_debit_inv + amount
		balance.op_debit_inv = balance.op_debit_inv + amount


def update_balance(balance):
	compte = balance.compte
	gestion = balance.anne_comptable.id
	if balance:
		reports = Report.objects.filter(compte=compte, gestion_courant_id=gestion).values(
			"compte__short_compte").annotate(
			fonc=Sum('amount_fonc', output_field=IntegerField()),
			inv=Sum('amount_invest', output_field=IntegerField()))
		if reports.exists():
			report = reports[0]
			balance.be_credit_inv = report["inv"]
			balance.be_credit_fonc = report["fonc"]

		avis_debits = AvisDeDebit.objects.filter(compte=compte, jour_comptable__annee_comptable__id=gestion).values(
			"disposition").annotate(
			montant=Sum('amount', output_field=IntegerField()))
		op_debit_inv = 0
		op_debit_fonc = 0
		if avis_debits.exists():
			for s in avis_debits:
				if s["disposition"] == "INVESTISSEMENT":
					op_debit_inv = s["montant"]
				if s["disposition"] == "FONCTIONNEMENT":
					op_debit_fonc = s["montant"]

		avis_credits = AvisDeCredit.objects.filter(compte=compte, jour_comptable__annee_comptable_id=gestion).values(
			"nature").annotate(
			montant=Sum('amount', output_field=IntegerField()))
		if avis_credits.exists():
			for s in avis_credits:
				if s["nature"] == "INVESTISSEMENT":
					balance.op_credit_inv = s["montant"]
				if s["nature"] == "FONCTIONNEMENT":
					balance.op_credit_fonc = s["montant"]

		trxop = TransactionOP.objects.filter(account_depot=compte.short_compte,
		                                     jour_comptable__annee_comptable_id=gestion).values(
			"reservation__ordre__type_nature").annotate(
			montant=Sum('amount', output_field=IntegerField()))
		if trxop.exists():
			for s in trxop:
				if s["reservation__ordre__type_nature"] == "INVESTISSEMENT":
					op_debit_inv = op_debit_inv + s["montant"]
				if s["reservation__ordre__type_nature"] == "FONCTIONNEMENT":
					op_debit_fonc = op_debit_fonc + s["montant"]
		balance.op_debit_inv = op_debit_inv
		balance.op_debit_fonc = op_debit_fonc

		balance.total_debit_inv = balance.op_debit_inv
		balance.total_debit_fonc = balance.op_debit_fonc
		balance.total_credit_inv = balance.op_credit_inv + balance.be_credit_inv
		balance.total_credit_fonc = balance.op_credit_fonc + balance.be_credit_fonc

		if balance.total_debit_inv > balance.total_credit_inv:
			balance.bs_debit_inv = balance.total_debit_inv - balance.total_credit_inv
			balance.bs_credit_inv = 0
		else:
			balance.bs_credit_inv = balance.total_credit_inv - balance.total_debit_inv
			balance.bs_debit_inv = 0

		if balance.total_debit_fonc > balance.total_credit_fonc:
			balance.bs_debit_fonc = balance.total_debit_fonc - balance.total_credit_fonc
			balance.bs_credit_fonc = 0
		else:
			balance.bs_credit_fonc = balance.total_credit_fonc - balance.total_debit_fonc
			balance.bs_debit_fonc = 0
		balance.save()


@receiver(post_save, sender=ValidationCompte)
def update_comptedepot(sender, **kwargs):
	instance = kwargs['instance']
	compte = instance.compte
	compte.actif = instance.actif
	compte.save()
	anne_comptable = AnneeComptable.active_gestion()
	if anne_comptable and not compte.acc_balance.filter(anne_comptable=anne_comptable).exists():
		# create balance
		balance = Balance()
		balance.compte = compte
		balance.anne_comptable = anne_comptable
		balance.save()


def create_balance(poste_id):
	anne_comptable = AnneeComptable.active_gestion()
	if anne_comptable:
		if poste_id is None:
			cpts = CompteDepot.objects.all()
		else:
			cpts = CompteDepot.objects.filter(poste_id=poste_id)
		for c in cpts:
			balance = Balance()
			balance.anne_comptable = anne_comptable
			balance.compte = c
			balance.save()


def reset_compteDepot():
	ReservationFond.objects.all().delete()
	Report.objects.all().delete()
	Transaction.objects.all().delete()
	OrdrePayment.objects.all().delete()
	FichierData.objects.all().delete()
	Balance.objects.all().delete()
	CompteDepot.objects.update(balance=0, balance_fonct=0, balance_insvest=0)


# create_balance(None)

def reset_compteDepot_by_poste(poste):
	poste_id = poste.id
	ReservationFond.objects.filter(ordre__compte__poste_id=poste_id).delete()
	Report.objects.filter(compte__poste_id=poste_id).delete()
	Transaction.objects.filter(poste_comptable=poste.reference).delete()
	OrdrePayment.objects.filter(compte__poste_id=poste_id).delete()
	FichierData.objects.all().delete()
	Balance.objects.filter(compte__poste_id=poste_id).delete()
	CompteDepot.objects.filter(poste_id=poste_id).update(balance=0, balance_fonct=0, balance_insvest=0)


# create_balance(poste_id)

def correctamount_comptedepot():  # mantis 0000145: edition : Situation des disponibilités montant négatifs n'apparaissent pas
	gestion = 2023

	anne_report = gestion
	x = date(anne_report, 2, 2)

	rg_last = DateRange(x, x + timedelta(days=1))
	lannee_comptable = AnneeComptable.objects.filter(period__contains=rg_last).last()

	comptes = CompteDepot.objects.all()

	for uncompte in comptes:
		list_avis_credit = AvisDeCredit.objects.filter(type_nature="FONCTIONNEMENT",
		                                               compte__short_compte=uncompte.short_compte,
		                                               date_avis__year=gestion)
		totalavis_credit = 0
		for x in list_avis_credit:
			totalavis_credit = totalavis_credit + x.amount

		list_avis_debit = AvisDeDebit.objects.filter(type_nature="FONCTIONNEMENT",
		                                             compte__short_compte=uncompte.short_compte,
		                                             date_avis__year=gestion)
		totalavis_debit = 0
		for x in list_avis_debit:
			totalavis_debit = totalavis_debit + x.amount

		list_report = Report.objects.filter(amount_fonc__gt=0, compte__short_compte=uncompte.short_compte,
		                                    gestion_courant=lannee_comptable)
		total_report = 0
		for x in list_report:
			total_report = total_report + x.amount_fonc

		list_op = OrdrePayment.objects.filter(type_nature="FONCTIONNEMENT", compte__short_compte=uncompte.short_compte,
		                                      jour_comptable__annee_comptable_id=1)  # 2023
		total_op = 0
		for x in list_op:
			total_op = total_op + x.amount

		total_fonct = totalavis_credit + total_report - totalavis_debit - total_op

		totalavis_credit = 0
		total_report = 0
		totalavis_debit = 0
		total_op = 0

		list_avis_credit = AvisDeCredit.objects.filter(type_nature="INVESTISSEMENT",
		                                               compte__short_compte=uncompte.short_compte,
		                                               date_avis__year=gestion)
		totalavis_credit = 0
		for x in list_avis_credit:
			totalavis_credit = totalavis_credit + x.amount

		list_avis_debit = AvisDeDebit.objects.filter(type_nature="INVESTISSEMENT",
		                                             compte__short_compte=uncompte.short_compte,
		                                             date_avis__year=gestion)
		totalavis_debit = 0
		for x in list_avis_debit:
			totalavis_debit = totalavis_debit + x.amount

		list_report = Report.objects.filter(amount_invest__gt=0, compte__short_compte=uncompte.short_compte,
		                                    gestion_courant=lannee_comptable)
		total_report = 0
		for x in list_report:
			total_report = total_report + x.amount_invest

		list_op = OrdrePayment.objects.filter(type_nature="INVESTISSEMENT", compte__short_compte=uncompte.short_compte,
		                                      jour_comptable__annee_comptable_id=1)
		total_op = 0
		for x in list_op:
			total_op = total_op + x.amount

		total_invest = totalavis_credit + total_report - totalavis_debit - total_op

		uncompte.balance_fonct.amount = total_fonct
		uncompte.balance_insvest.amount = total_invest

		uncompte.balance.amount = total_fonct + total_invest
		uncompte.save()


import operator
import itertools


def create_dict_from_groupby(iterator):
	groupby_dict = {}
	for key, group in iterator:
		groupby_dict[key] = list(group)
	return groupby_dict


def get_items_by_compte(datas, inputkey):
	for key, group in datas.items():
		if inputkey == key:
			return list(group)
	return None


def update_balance_by_date(comptes, enddate, gestion):
	compte_ids = comptes.values_list("short_compte", flat=True)
	list_reports = {}
	list_avis_debits = {}
	list_avis_credit = {}
	list_trx_op = {}
	balances = []

	total_op_debit_inv = 0

	reports = Report.objects.filter(compte__short_compte__in=compte_ids, gestion_courant_id=gestion,
	                                created__lte=enddate).values("compte__short_compte").annotate(
		fonc=Sum('amount_fonc', output_field=IntegerField()),
		inv=Sum('amount_invest', output_field=IntegerField()))

	if reports.exists():
		datas_r = sorted(list(reports), key=lambda k: k['compte__short_compte'], reverse=False)
		list_reports = create_dict_from_groupby(itertools.groupby(datas_r, operator.itemgetter('compte__short_compte')))

	avis_debits = AvisDeDebit.objects.filter(compte__short_compte__in=compte_ids,
	                                         jour_comptable__annee_comptable__id=gestion, created__lte=enddate).values(
		"compte__short_compte", "disposition").annotate(
		montant=Sum('amount', output_field=IntegerField()))

	if avis_debits.exists():
		datas_d = sorted(list(avis_debits), key=lambda k: k['compte__short_compte'], reverse=False)
		list_avis_debits = create_dict_from_groupby(
			itertools.groupby(datas_d, operator.itemgetter('compte__short_compte')))

	avis_credits = AvisDeCredit.objects.filter(compte__short_compte__in=compte_ids,
	                                           jour_comptable__annee_comptable_id=gestion, created__lte=enddate).values(
		"compte__short_compte", "nature").annotate(
		montant=Sum('amount', output_field=IntegerField()))
	if avis_credits.exists():
		datas_c = sorted(list(avis_credits), key=lambda k: k['compte__short_compte'], reverse=False)
		list_avis_credit = create_dict_from_groupby(
			itertools.groupby(datas_c, operator.itemgetter('compte__short_compte')))

	trxop = TransactionOP.objects.filter(account_depot__in=compte_ids, jour_comptable__annee_comptable_id=gestion,
	                                     created__lte=enddate).values("account_depot",
	                                                                  "reservation__ordre__type_nature").annotate(
		montant=Sum('amount', output_field=IntegerField()))
	if trxop.exists():
		datas = sorted(list(trxop), key=lambda k: k['account_depot'], reverse=False)
		list_trx_op = create_dict_from_groupby(itertools.groupby(datas, operator.itemgetter('account_depot')))

	tol_be_credit_fonc = 0
	tol_be_credit_inv = 0
	tol_op_debit_fonc = 0
	tol_op_debit_inv = 0
	tol_op_credit_fonc = 0
	tol_op_credit_inv = 0

	tol_total_debit_fonc = 0
	tol_total_debit_inv = 0
	tol_total_credit_fonc = 0
	tol_total_credit_inv = 0

	tol_bs_debit_fonc = 0
	tol_bs_debit_inv = 0
	tol_bs_credit_fonc = 0
	tol_bs_credit_inv = 0

	for compte in comptes:
		balance = Balance()
		balance.compte = compte
		op_debit_inv = 0
		op_debit_fonc = 0
		compte_reports = get_items_by_compte(list_reports, compte.short_compte)
		# print(compte_reports)
		if compte_reports:
			balance.be_credit_inv = compte_reports[0]["inv"]
			balance.be_credit_fonc = compte_reports[0]["fonc"]

		compte_avis_debits = get_items_by_compte(list_avis_debits, compte.short_compte)
		if compte_avis_debits:
			for s in compte_avis_debits:
				if s["disposition"] == "INVESTISSEMENT":
					op_debit_inv = s["montant"]
				if s["disposition"] == "FONCTIONNEMENT":
					op_debit_fonc = s["montant"]

		compte_avis_credit = get_items_by_compte(list_avis_credit, compte.short_compte)
		if compte_avis_credit:
			for s in compte_avis_credit:
				if s["nature"] == "INVESTISSEMENT":
					balance.op_credit_inv = s["montant"]
				if s["nature"] == "FONCTIONNEMENT":
					balance.op_credit_fonc = s["montant"]

		compte_tr_op = get_items_by_compte(list_trx_op, compte.short_compte)
		if compte_tr_op:
			for s in compte_tr_op:
				if s["reservation__ordre__type_nature"] == "INVESTISSEMENT":
					op_debit_inv = op_debit_inv + s["montant"]
				if s["reservation__ordre__type_nature"] == "FONCTIONNEMENT":
					op_debit_fonc = op_debit_fonc + s["montant"]

		balance.op_debit_inv = op_debit_inv
		balance.op_debit_fonc = op_debit_fonc

		balance.total_debit_inv = balance.op_debit_inv
		balance.total_debit_fonc = balance.op_debit_fonc
		balance.total_credit_inv = balance.op_credit_inv + balance.be_credit_inv
		balance.total_credit_fonc = balance.op_credit_fonc + balance.be_credit_fonc

		if balance.total_debit_inv > balance.total_credit_inv:
			balance.bs_debit_inv = balance.total_debit_inv - balance.total_credit_inv
			balance.bs_credit_inv = 0
		else:
			balance.bs_credit_inv = balance.total_credit_inv - balance.total_debit_inv
			balance.bs_debit_inv = 0

		if balance.total_debit_fonc > balance.total_credit_fonc:
			balance.bs_debit_fonc = balance.total_debit_fonc - balance.total_credit_fonc
			balance.bs_credit_fonc = 0
		else:
			balance.bs_credit_fonc = balance.total_credit_fonc - balance.total_debit_fonc
			balance.bs_debit_fonc = 0

		if not balance.has_no_entries():
			balances.append(balance.balance_to_dict())
			tol_be_credit_fonc += int(balance.be_credit_fonc.amount)
			tol_be_credit_inv += int(balance.be_credit_inv.amount)

			tol_op_debit_fonc += int(balance.op_debit_fonc.amount)
			tol_op_debit_inv += int(balance.op_debit_inv.amount)
			tol_op_credit_fonc += int(balance.op_credit_fonc.amount)
			tol_op_credit_inv += int(balance.op_credit_inv.amount)

			tol_total_debit_fonc += int(balance.total_debit_fonc.amount)
			tol_total_debit_inv += int(balance.total_debit_inv.amount)
			tol_total_credit_fonc += int(balance.total_credit_fonc.amount)
			tol_total_credit_inv += int(balance.total_credit_inv.amount)

			tol_bs_debit_fonc += int(balance.bs_debit_fonc.amount)
			tol_bs_debit_inv += int(balance.bs_debit_inv.amount)
			tol_bs_credit_fonc += int(balance.bs_credit_fonc.amount)
			tol_bs_credit_inv += int(balance.bs_credit_inv.amount)

	totaux = {"tol_be_credit_fonc": tol_be_credit_fonc, "tol_be_credit_inv": tol_be_credit_inv,
	          "tol_op_debit_fonc": tol_op_debit_fonc, "tol_op_debit_inv": tol_op_debit_inv,
	          "tol_op_credit_fonc": tol_op_credit_fonc, "tol_op_credit_inv": tol_op_credit_inv,
	          "tol_total_debit_fonc": tol_total_debit_fonc, "tol_total_debit_inv": tol_total_debit_inv,
	          "tol_total_credit_fonc": tol_total_credit_fonc, "tol_total_credit_inv": tol_total_credit_inv,
	          "tol_bs_debit_fonc": tol_bs_debit_fonc, "tol_bs_debit_inv": tol_bs_debit_inv,
	          "tol_bs_credit_fonc": tol_bs_credit_fonc, "tol_bs_credit_inv": tol_bs_credit_inv}

	return balances, totaux


def update_balance_generique_by_date(comptes, enddate, gestion):
	comptes = sorted(comptes, key=lambda k: k['short_compte'], reverse=False)
	compte_ids = [i['short_compte'] for i in comptes]  # comptes.values_list("short_compte", flat=True)
	list_reports = {}
	list_avis_debits = {}
	list_avis_credit = {}
	list_trx_op = {}
	balances = []

	total_op_debit_inv = 0

	reports = ReportGestion.objects.filter(compte__short_compte__in=compte_ids, gestion_courant_id=gestion,
	                                created__date__lte=enddate).values("compte__short_compte","typecompte_id").annotate(
		montant=Sum('f_amount', output_field=IntegerField()),
		nature=ExpressionWrapper(F("typecompte__nature"), output_field=CharField()),
		provenance=ExpressionWrapper(F("typecompte__provenance"), output_field=CharField())
	)

	if reports.exists():
		datas_r = sorted(list(reports), key=lambda k: k['compte__short_compte'], reverse=False)
		list_reports = create_dict_from_groupby(itertools.groupby(datas_r, operator.itemgetter('compte__short_compte')))

	avis_debits = AvisDeDebit.objects.filter(compte__short_compte__in=compte_ids,
	                                         jour_comptable__annee_comptable__id=gestion,
	                                         date_avis__lte=enddate).values(
		"compte__short_compte", "typecompte_id").annotate(
		montant=Sum('amount', output_field=IntegerField()),

	nature = ExpressionWrapper(F("typecompte__nature"), output_field=CharField()),
	provenance = ExpressionWrapper(F("typecompte__provenance"), output_field=CharField())
	)

	if avis_debits.exists():
		datas_d = sorted(list(avis_debits), key=lambda k: k['compte__short_compte'], reverse=False)
		list_avis_debits = create_dict_from_groupby(
			itertools.groupby(datas_d, operator.itemgetter('compte__short_compte')))

	avis_credits = AvisDeCredit.objects.filter(compte__short_compte__in=compte_ids,
	                                           jour_comptable__annee_comptable_id=gestion,
	                                           date_avis__lte=enddate).values(
		"compte__short_compte", "typecompte_id").annotate(
		montant=Sum('amount', output_field=IntegerField()),

	nature = ExpressionWrapper(F("typecompte__nature"), output_field=CharField()),
	provenance = ExpressionWrapper(F("typecompte__provenance"), output_field=CharField()))
	if avis_credits.exists():
		datas_c = sorted(list(avis_credits), key=lambda k: k['compte__short_compte'], reverse=False)
		list_avis_credit = create_dict_from_groupby(
			itertools.groupby(datas_c, operator.itemgetter('compte__short_compte')))

	trxop = TransactionOP.objects.filter(account_depot__in=compte_ids, jour_comptable__annee_comptable_id=gestion,
	                                     has_cancel=False, is_cancel_trx=False,
	                                     reservation__ordre__date_visa__date__lte=enddate).values("account_depot",
	                                                                                              "typecompte_id").annotate(
		montant=Sum('amount', output_field=IntegerField()),

	nature = ExpressionWrapper(F("typecompte__nature"), output_field=CharField()),
	provenance = ExpressionWrapper(F("typecompte__provenance"), output_field=CharField()))
	if trxop.exists():
		datas = sorted(list(trxop), key=lambda k: k['account_depot'], reverse=False)
		list_trx_op = create_dict_from_groupby(itertools.groupby(datas, operator.itemgetter('account_depot')))

	tol_be_credit_fonc = 0
	tol_be_credit_inv = 0
	tol_op_debit_fonc = 0
	tol_op_debit_inv = 0
	tol_op_credit_fonc = 0
	tol_op_credit_inv = 0

	tol_total_debit_fonc = 0
	tol_total_debit_inv = 0
	tol_total_credit_fonc = 0
	tol_total_credit_inv = 0

	tol_bs_debit_fonc = 0
	tol_bs_debit_inv = 0
	tol_bs_credit_fonc = 0
	tol_bs_credit_inv = 0

	for compte in comptes:
		short_compte = compte["short_compte"]
		id = compte["id"]
		balance = Balance()
		balance.compte_id = id
		balance.provenance=""
		balance_provenanceBudget = Balance()
		balance_provenanceBudget.provenance=PROVENANCE_FOND.BUDGET
		balance_provenanceBudget.compte_id = id
		balance_provenanceFond = Balance()
		balance_provenanceFond.provenance = PROVENANCE_FOND.FONDPROPRE
		balance_provenanceFond.compte_id = id
		op_debit_inv = 0
		op_debit_fonc = 0

		op_debit_inv_fond =0
		op_debit_inv_budget=0
		op_debit_fonc_fond =0
		op_debit_fonc_budget=0

		compte_reports = get_items_by_compte(list_reports, short_compte)
		# print(compte_reports)
		if compte_reports:
			for s in compte_reports:
				if s["provenance"] == PROVENANCE_FOND.BUDGET:
					if s["nature"] == NATURE_COMPTE.INVESTISSEMENT:
						balance_provenanceBudget.be_credit_inv = s["montant"]
					if s["nature"] == NATURE_COMPTE.FONCTIONNEMENT:
						balance_provenanceBudget.be_credit_fonc = s["montant"]
				if s["provenance"] == PROVENANCE_FOND.FONDPROPRE:
					if s["nature"] == NATURE_COMPTE.INVESTISSEMENT:
						balance_provenanceFond.be_credit_inv = s["montant"]
					if s["nature"] == NATURE_COMPTE.FONCTIONNEMENT:
						balance_provenanceFond.be_credit_fonc = s["montant"]

				balance.be_credit_fonc=balance_provenanceBudget.be_credit_fonc+balance_provenanceFond.be_credit_fonc
				balance.be_credit_inv = balance_provenanceBudget.be_credit_inv + balance_provenanceFond.be_credit_inv


		compte_avis_debits = get_items_by_compte(list_avis_debits, short_compte)
		if compte_avis_debits:
			for s in compte_avis_debits:
				if s["provenance"] == PROVENANCE_FOND.BUDGET:
					if s["nature"] == NATURE_COMPTE.INVESTISSEMENT:
						op_debit_inv_budget = s["montant"]
					if s["nature"] == NATURE_COMPTE.FONCTIONNEMENT:
						op_debit_fonc_budget = s["montant"]
				if s["provenance"] == PROVENANCE_FOND.FONDPROPRE:
					if s["nature"] == NATURE_COMPTE.INVESTISSEMENT:
						op_debit_inv_fond = s["montant"]
					if s["nature"] == NATURE_COMPTE.FONCTIONNEMENT:
						op_debit_fonc_fond = s["montant"]



		compte_avis_credit = get_items_by_compte(list_avis_credit, short_compte)
		if compte_avis_credit:
			for s in compte_avis_credit:

				if s["provenance"] == PROVENANCE_FOND.BUDGET:
					if s["nature"] == NATURE_COMPTE.INVESTISSEMENT:
						balance_provenanceBudget.op_credit_inv = s["montant"]
					if s["nature"] == NATURE_COMPTE.FONCTIONNEMENT:
						balance_provenanceBudget.op_credit_fonc = s["montant"]
				if s["provenance"] == PROVENANCE_FOND.FONDPROPRE:
					if s["nature"] == NATURE_COMPTE.INVESTISSEMENT:
						balance_provenanceFond.op_credit_inv = s["montant"]
					if s["nature"] == NATURE_COMPTE.FONCTIONNEMENT:
						balance_provenanceFond.op_credit_fonc = s["montant"]
				balance.op_credit_inv = balance_provenanceFond.op_credit_inv+balance_provenanceBudget.op_credit_inv
				balance.op_credit_fonc = balance_provenanceBudget.op_credit_fonc+balance_provenanceFond.op_credit_fonc

		compte_tr_op = get_items_by_compte(list_trx_op, short_compte)
		if compte_tr_op:
			for s in compte_tr_op:

				if s["provenance"] == PROVENANCE_FOND.BUDGET:
					if s["nature"] == NATURE_COMPTE.INVESTISSEMENT:
						op_debit_inv_budget =op_debit_inv_budget+ s["montant"]
					if s["nature"] == NATURE_COMPTE.FONCTIONNEMENT:
						op_debit_fonc_budget = op_debit_fonc_budget+s["montant"]
				if s["provenance"] == PROVENANCE_FOND.FONDPROPRE:
					if s["nature"] == NATURE_COMPTE.INVESTISSEMENT:
						op_debit_inv_fond = op_debit_inv_fond+s["montant"]
					if s["nature"] == NATURE_COMPTE.FONCTIONNEMENT:
						op_debit_fonc_fond = op_debit_fonc_fond+ s["montant"]

		op_debit_inv = op_debit_inv_fond + op_debit_inv_budget
		op_debit_fonc = op_debit_fonc_fond + op_debit_fonc_budget

		balance_provenanceBudget.op_debit_inv = op_debit_inv_budget
		balance_provenanceBudget.op_debit_fonc = op_debit_fonc_budget
		balance_provenanceFond.op_debit_inv = op_debit_inv_fond
		balance_provenanceFond.op_debit_fonc = op_debit_fonc_fond

		balance_provenanceFond.total_debit_inv = balance_provenanceFond.op_debit_inv
		balance_provenanceFond.total_debit_fonc = balance_provenanceFond.op_debit_fonc
		balance_provenanceFond.total_credit_inv = balance_provenanceFond.op_credit_inv + balance_provenanceFond.be_credit_inv
		balance_provenanceFond.total_credit_fonc = balance_provenanceFond.op_credit_fonc + balance_provenanceFond.be_credit_fonc

		balance_provenanceBudget.total_debit_inv = balance_provenanceBudget.op_debit_inv
		balance_provenanceBudget.total_debit_fonc = balance_provenanceBudget.op_debit_fonc
		balance_provenanceBudget.total_credit_inv = balance_provenanceBudget.op_credit_inv + balance_provenanceBudget.be_credit_inv
		balance_provenanceBudget.total_credit_fonc = balance_provenanceBudget.op_credit_fonc + balance_provenanceBudget.be_credit_fonc

		balance.op_debit_inv = op_debit_inv
		balance.op_debit_fonc = op_debit_fonc

		balance.total_debit_inv = balance.op_debit_inv
		balance.total_debit_fonc = balance.op_debit_fonc
		balance.total_credit_inv = balance.op_credit_inv + balance.be_credit_inv
		balance.total_credit_fonc = balance.op_credit_fonc + balance.be_credit_fonc

		if balance.total_debit_inv > balance.total_credit_inv:
			balance.bs_debit_inv = balance.total_debit_inv - balance.total_credit_inv
			balance.bs_credit_inv = 0
		else:
			balance.bs_credit_inv = balance.total_credit_inv - balance.total_debit_inv
			balance.bs_debit_inv = 0

		if balance.total_debit_fonc > balance.total_credit_fonc:
			balance.bs_debit_fonc = balance.total_debit_fonc - balance.total_credit_fonc
			balance.bs_credit_fonc = 0
		else:
			balance.bs_credit_fonc = balance.total_credit_fonc - balance.total_debit_fonc
			balance.bs_debit_fonc = 0

		if not balance.has_no_entries():

			balances.append(balance_provenanceFond.balance_to_dict())
			balances.append(balance_provenanceBudget.balance_to_dict())
			balances.append(balance.balance_to_dict())
			tol_be_credit_fonc += int(balance.be_credit_fonc.amount)
			tol_be_credit_inv += int(balance.be_credit_inv.amount)

			tol_op_debit_fonc += int(balance.op_debit_fonc.amount)
			tol_op_debit_inv += int(balance.op_debit_inv.amount)
			tol_op_credit_fonc += int(balance.op_credit_fonc.amount)
			tol_op_credit_inv += int(balance.op_credit_inv.amount)

			tol_total_debit_fonc += int(balance.total_debit_fonc.amount)
			tol_total_debit_inv += int(balance.total_debit_inv.amount)
			tol_total_credit_fonc += int(balance.total_credit_fonc.amount)
			tol_total_credit_inv += int(balance.total_credit_inv.amount)

			tol_bs_debit_fonc += int(balance.bs_debit_fonc.amount)
			tol_bs_debit_inv += int(balance.bs_debit_inv.amount)
			tol_bs_credit_fonc += int(balance.bs_credit_fonc.amount)
			tol_bs_credit_inv += int(balance.bs_credit_inv.amount)

	totaux = {"be_credit_fonc": tol_be_credit_fonc, "be_credit_inv": tol_be_credit_inv,
	          "op_debit_fonc": tol_op_debit_fonc, "op_debit_inv": tol_op_debit_inv,
	          "op_credit_fonc": tol_op_credit_fonc, "op_credit_inv": tol_op_credit_inv,
	          "total_debit_fonc": tol_total_debit_fonc, "total_debit_inv": tol_total_debit_inv,
	          "total_credit_fonc": tol_total_credit_fonc, "total_credit_inv": tol_total_credit_inv,
	          "bs_debit_fonc": tol_bs_debit_fonc, "bs_debit_inv": tol_bs_debit_inv,
	          "bs_credit_fonc": tol_bs_credit_fonc, "bs_credit_inv": tol_bs_credit_inv}


	return balances, totaux


def update_balance_generique_by_date_deprecate(comptes, enddate, gestion):
	comptes = sorted(comptes, key=lambda k: k['short_compte'], reverse=False)
	compte_ids = [i['short_compte'] for i in comptes]  # comptes.values_list("short_compte", flat=True)
	list_reports = {}
	list_avis_debits = {}
	list_avis_credit = {}
	list_trx_op = {}
	balances = []

	total_op_debit_inv = 0

	reports = ReportGestion.objects.filter(compte__short_compte__in=compte_ids, gestion_courant_id=gestion,
	                                created__date__lte=enddate).values("compte__short_compte","typecompte__nature").annotate(
		montant=Sum('amount', output_field=IntegerField()))

	if reports.exists():
		datas_r = sorted(list(reports), key=lambda k: k['compte__short_compte'], reverse=False)
		list_reports = create_dict_from_groupby(itertools.groupby(datas_r, operator.itemgetter('compte__short_compte')))

	avis_debits = AvisDeDebit.objects.filter(compte__short_compte__in=compte_ids,
	                                         jour_comptable__annee_comptable__id=gestion,
	                                         date_avis__lte=enddate).values(
		"compte__short_compte", "typecompte__nature").annotate(
		montant=Sum('amount', output_field=IntegerField()))

	if avis_debits.exists():
		datas_d = sorted(list(avis_debits), key=lambda k: k['compte__short_compte'], reverse=False)
		list_avis_debits = create_dict_from_groupby(
			itertools.groupby(datas_d, operator.itemgetter('compte__short_compte')))

	avis_credits = AvisDeCredit.objects.filter(compte__short_compte__in=compte_ids,
	                                           jour_comptable__annee_comptable_id=gestion,
	                                           date_avis__lte=enddate).values(
		"compte__short_compte", "typecompte__nature").annotate(
		montant=Sum('amount', output_field=IntegerField()))
	if avis_credits.exists():
		datas_c = sorted(list(avis_credits), key=lambda k: k['compte__short_compte'], reverse=False)
		list_avis_credit = create_dict_from_groupby(
			itertools.groupby(datas_c, operator.itemgetter('compte__short_compte')))

	trxop = TransactionOP.objects.filter(account_depot__in=compte_ids, jour_comptable__annee_comptable_id=gestion,
	                                     has_cancel=False, is_cancel_trx=False,
	                                     reservation__ordre__date_visa__date__lte=enddate).values("account_depot",
	                                                                                              "typecompte__nature").annotate(
		montant=Sum('amount', output_field=IntegerField()))
	if trxop.exists():
		datas = sorted(list(trxop), key=lambda k: k['account_depot'], reverse=False)
		list_trx_op = create_dict_from_groupby(itertools.groupby(datas, operator.itemgetter('account_depot')))

	tol_be_credit_fonc = 0
	tol_be_credit_inv = 0
	tol_op_debit_fonc = 0
	tol_op_debit_inv = 0
	tol_op_credit_fonc = 0
	tol_op_credit_inv = 0

	tol_total_debit_fonc = 0
	tol_total_debit_inv = 0
	tol_total_credit_fonc = 0
	tol_total_credit_inv = 0

	tol_bs_debit_fonc = 0
	tol_bs_debit_inv = 0
	tol_bs_credit_fonc = 0
	tol_bs_credit_inv = 0

	for compte in comptes:
		short_compte = compte["short_compte"]
		id = compte["id"]
		balance = Balance()
		balance.compte_id = id
		op_debit_inv = 0
		op_debit_fonc = 0
		compte_reports = get_items_by_compte(list_reports, short_compte)
		# print(compte_reports)
		if compte_reports:
			for s in compte_reports:
				if s["typecompte__nature"] == "INVESTISSEMENT":
					balance.be_credit_inv = s["montant"]
				if s["typecompte__nature"] == "FONCTIONNEMENT":
					balance.be_credit_fonc = s["montant"]

		compte_avis_debits = get_items_by_compte(list_avis_debits, short_compte)
		if compte_avis_debits:
			for s in compte_avis_debits:
				if s["typecompte__nature"] == "INVESTISSEMENT":
					op_debit_inv = s["montant"]
				if s["typecompte__nature"] == "FONCTIONNEMENT":
					op_debit_fonc = s["montant"]

		compte_avis_credit = get_items_by_compte(list_avis_credit, short_compte)
		if compte_avis_credit:
			for s in compte_avis_credit:
				if s["typecompte__nature"] == "INVESTISSEMENT":
					balance.op_credit_inv = s["montant"]
				if s["typecompte__nature"] == "FONCTIONNEMENT":
					balance.op_credit_fonc = s["montant"]

		compte_tr_op = get_items_by_compte(list_trx_op, short_compte)
		if compte_tr_op:
			for s in compte_tr_op:
				if s["typecompte__nature"] == "INVESTISSEMENT":
					op_debit_inv = op_debit_inv + s["montant"]
				if s["typecompte__nature"] == "FONCTIONNEMENT":
					op_debit_fonc = op_debit_fonc + s["montant"]

		balance.op_debit_inv = op_debit_inv
		balance.op_debit_fonc = op_debit_fonc

		balance.total_debit_inv = balance.op_debit_inv
		balance.total_debit_fonc = balance.op_debit_fonc
		balance.total_credit_inv = balance.op_credit_inv + balance.be_credit_inv
		balance.total_credit_fonc = balance.op_credit_fonc + balance.be_credit_fonc

		if balance.total_debit_inv > balance.total_credit_inv:
			balance.bs_debit_inv = balance.total_debit_inv - balance.total_credit_inv
			balance.bs_credit_inv = 0
		else:
			balance.bs_credit_inv = balance.total_credit_inv - balance.total_debit_inv
			balance.bs_debit_inv = 0

		if balance.total_debit_fonc > balance.total_credit_fonc:
			balance.bs_debit_fonc = balance.total_debit_fonc - balance.total_credit_fonc
			balance.bs_credit_fonc = 0
		else:
			balance.bs_credit_fonc = balance.total_credit_fonc - balance.total_debit_fonc
			balance.bs_debit_fonc = 0

		if not balance.has_no_entries():
			balances.append(balance.balance_to_dict())
			tol_be_credit_fonc += int(balance.be_credit_fonc.amount)
			tol_be_credit_inv += int(balance.be_credit_inv.amount)

			tol_op_debit_fonc += int(balance.op_debit_fonc.amount)
			tol_op_debit_inv += int(balance.op_debit_inv.amount)
			tol_op_credit_fonc += int(balance.op_credit_fonc.amount)
			tol_op_credit_inv += int(balance.op_credit_inv.amount)

			tol_total_debit_fonc += int(balance.total_debit_fonc.amount)
			tol_total_debit_inv += int(balance.total_debit_inv.amount)
			tol_total_credit_fonc += int(balance.total_credit_fonc.amount)
			tol_total_credit_inv += int(balance.total_credit_inv.amount)

			tol_bs_debit_fonc += int(balance.bs_debit_fonc.amount)
			tol_bs_debit_inv += int(balance.bs_debit_inv.amount)
			tol_bs_credit_fonc += int(balance.bs_credit_fonc.amount)
			tol_bs_credit_inv += int(balance.bs_credit_inv.amount)

	totaux = {"be_credit_fonc": tol_be_credit_fonc, "be_credit_inv": tol_be_credit_inv,
	          "op_debit_fonc": tol_op_debit_fonc, "op_debit_inv": tol_op_debit_inv,
	          "op_credit_fonc": tol_op_credit_fonc, "op_credit_inv": tol_op_credit_inv,
	          "total_debit_fonc": tol_total_debit_fonc, "total_debit_inv": tol_total_debit_inv,
	          "total_credit_fonc": tol_total_credit_fonc, "total_credit_inv": tol_total_credit_inv,
	          "bs_debit_fonc": tol_bs_debit_fonc, "bs_debit_inv": tol_bs_debit_inv,
	          "bs_credit_fonc": tol_bs_credit_fonc, "bs_credit_inv": tol_bs_credit_inv}


	return balances, totaux


def update_newbalance_by_date(comptes, enddate, gestion):
	x = comptes.values("code_service__code", "short_compte", "id")
	tol_be_credit_fonc = 0
	tol_be_credit_inv = 0
	tol_op_debit_fonc = 0
	tol_op_debit_inv = 0
	tol_op_credit_fonc = 0
	tol_op_credit_inv = 0

	tol_total_debit_fonc = 0
	tol_total_debit_inv = 0
	tol_total_credit_fonc = 0
	tol_total_credit_inv = 0

	tol_bs_debit_fonc = 0
	tol_bs_debit_inv = 0
	tol_bs_credit_fonc = 0
	tol_bs_credit_inv = 0
	c = []

	datas_r = sorted(list(x), key=lambda k: k['code_service__code'], reverse=False)
	for key, cpts in itertools.groupby(datas_r, operator.itemgetter('code_service__code')):

		balances, totaux = update_balance_generique_by_date(list(cpts), enddate, gestion)
		if len(balances) > 0:
			c.append({"code": key, "balances": balances, "totaux": totaux})

			tol_be_credit_fonc += int(totaux["be_credit_fonc"])
			tol_be_credit_inv += int(totaux["be_credit_inv"])

			tol_op_debit_fonc += int(totaux["op_debit_fonc"])
			tol_op_debit_inv += int(totaux["op_debit_inv"])
			tol_op_credit_fonc += int(totaux["op_credit_fonc"])
			tol_op_credit_inv += int(totaux["op_credit_inv"])

			tol_total_debit_fonc += int(totaux["total_debit_fonc"])
			tol_total_debit_inv += int(totaux["total_debit_inv"])
			tol_total_credit_fonc += int(totaux["total_credit_fonc"])
			tol_total_credit_inv += int(totaux["total_credit_inv"])

			tol_bs_debit_fonc += int(totaux["bs_debit_fonc"])
			tol_bs_debit_inv += int(totaux["bs_debit_inv"])
			tol_bs_credit_fonc += int(totaux["bs_credit_fonc"])
			tol_bs_credit_inv += int(totaux["bs_credit_inv"])
	totaux = {"be_credit_fonc": tol_be_credit_fonc, "be_credit_inv": tol_be_credit_inv,
	          "op_debit_fonc": tol_op_debit_fonc, "op_debit_inv": tol_op_debit_inv,
	          "op_credit_fonc": tol_op_credit_fonc, "op_credit_inv": tol_op_credit_inv,
	          "total_debit_fonc": tol_total_debit_fonc, "total_debit_inv": tol_total_debit_inv,
	          "total_credit_fonc": tol_total_credit_fonc, "total_credit_inv": tol_total_credit_inv,
	          "bs_debit_fonc": tol_bs_debit_fonc, "bs_debit_inv": tol_bs_debit_inv,
	          "bs_credit_fonc": tol_bs_credit_fonc, "bs_credit_inv": tol_bs_credit_inv}

	return c, totaux

def delete_a_validate_op_initiate_by_pc(ordre, agent_comptable):
	try:
		if ordre.creator == agent_comptable and ordre.etape == ETAPE_ORDRE_PAYMENT.VALIDE:
			if hasattr(ordre, "reservationfond"):
				if not hasattr(ordre, "prise_en_charge"):
					amount = ordre.reservationfond.amount
					rsv = ordre.reservationfond
					rsv.delete()
					ordre.reservationfond = None
					ordre.save()

					if ordre.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and ordre.cheque:
						# on verifie si le cheque est receptionne
						from bankcheck.models import Cheque
						cheque = Cheque.objects.get(reference=ordre.cheque)
						cheque.observations = "Ordre de paiement lie à ce cheque a tete annulé"
						cheque.save()
						cheque.use = False
						cheque.amount = 0
						cheque.cin_receptionnaire = None
						cheque.phone_receptionnaire = None
						cheque.trx = None
						cheque.use_date = None
						cheque.endosser_par = None

						cheque.save()

					if ordre.blocage:
						blocage = ordre.blocage
						blocage.credit(amount)
					else:
						compte = ordre.compte
						compte.credit_by_type(amount, ordre.type_nature)
					ordre.delete()
				else:
					raise SigException(message="Impossibble de supprimer cet ordre")
			else:
				ordre.delete()

	except:
		import traceback
		traceback.print_exc()
		pass

def get_by_id(vals, expId):
	#return [item for item in vals if item['typecompte'] == expId][0]
	my_item = next(iter(item for item in vals if item['typecompte'] == expId), None)
	return my_item
	#return next(x for x in vals if x['typecompte'] == expId)
def compute_balance_new(compte, startdate, enddate, gestion, all_trx, rsv_objs, typecompte,update=True,with_trx=False,with_cancel_trx=True):
	last_balance = 0
	an = AnneeComptable.objects.get(id=gestion)
	print_date_1 = an.period.lower
	start_january = datetime.datetime(print_date_1.year, 1, 1)
	last_january = datetime.datetime(print_date_1.year - 1, 1, 1)

	last_rg = DateRange(last_january.date(), last_january.date() + datetime.timedelta(days=1))

	previous_anne_comptable = an.parent
	last_balances = []
	reports_from_cancel_trx = []
	reports_from_non_cancel_trx = []

	if previous_anne_comptable:
		last_balances = ReportGestion.objects.filter(compte=compte, gestion_courant=an).values("sens","typecompte").annotate(
			amount=Coalesce(Sum('amount', output_field=IntegerField()), Value(0)),
			nature = ExpressionWrapper(F("typecompte__nature"), output_field=CharField()),
			name = ExpressionWrapper(F("typecompte__name"), output_field=CharField())
		)
		last_balances = format_trx_datas(last_balances)

	annee_comptable = startdate.year
	include_endate = enddate + datetime.timedelta(days=0)

	trx = all_trx.filter(jour_comptable__jour__range=(startdate, include_endate),jour_comptable__annee_comptable_id=gestion)


	cheques = trx.filter(payment_mean=PAYMENT_MEAN_TYPE.CHEQUE).count()

	canceleds_trx = trx.filter(is_cancel_trx_0=True)
	none_canceleds_trx = trx.exclude(is_cancel_trx_0=True)

	canceleds_trx_debit = canceleds_trx.values("sens","typecompte").annotate(amount=Sum('amount', output_field=IntegerField())
	,nature = ExpressionWrapper(F("typecompte__nature"), output_field=CharField()),
	name = ExpressionWrapper(F("typecompte__name"), output_field=CharField())
	)

	none_canceleds_trx_debit = none_canceleds_trx.values("sens","typecompte").annotate(
		amount=Sum('amount', output_field=IntegerField()),
		nature=ExpressionWrapper(F("typecompte__nature"), output_field=CharField()),
		name=ExpressionWrapper(F("typecompte__name"), output_field=CharField())
	)
	none_canceleds_trx_debit = format_trx_datas(none_canceleds_trx_debit)

	canceleds_trx_debit = format_trx_datas(canceleds_trx_debit)
	if startdate > start_january:
		reporttrx = all_trx.filter(jour_comptable__jour__range=(start_january, startdate - datetime.timedelta(days=1)),jour_comptable__annee_comptable_id=gestion)

		report_canceleds_trx = reporttrx.filter(is_cancel_trx_0=True)
		report_none_canceleds_trx = reporttrx.exclude(is_cancel_trx_0=True)
		report_canceleds_debit = report_canceleds_trx.values("sens","typecompte").annotate(
			amount=Sum('amount', output_field=IntegerField()),
		nature=ExpressionWrapper(F("typecompte__nature"), output_field=CharField()),
		name=ExpressionWrapper(F("typecompte__name"), output_field=CharField()))
		report_none_canceleds_debit = report_none_canceleds_trx.values("sens","typecompte").annotate(
			amount=Sum('amount', output_field=IntegerField()),
			nature=ExpressionWrapper(F("typecompte__nature"), output_field=CharField()),
			name=ExpressionWrapper(F("typecompte__name"), output_field=CharField())
		)

		reports_from_cancel_trx=format_trx_datas(report_canceleds_debit)
		reports_from_non_cancel_trx = format_trx_datas(report_none_canceleds_debit)

	else:
		pass


	t_pcharges_by_typeompte =[]
	if rsv_objs:
		t_pcharges_by_typeompte = rsv_objs.values("ordre__typecompte_id").annotate(amount=Coalesce(Sum('reliquat', output_field=IntegerField()), Value(0)),
		                                nombre=Count('id', output_field=IntegerField()),nature=ExpressionWrapper(F("ordre__typecompte__nature"), output_field=CharField()),
			name=ExpressionWrapper(F("ordre__typecompte__name"), output_field=CharField()),typecompte=ExpressionWrapper(F("ordre__typecompte_id"), output_field=IntegerField()))
		if t_pcharges_by_typeompte:
			t_pcharges_by_typeompte=list(t_pcharges_by_typeompte)


	infos_solde = []

	context = {"disponible": 0, "last_balance": 0, "cheques": cheques,
	           "balance": 0,
	           "debit": 0, "credit": 0, "annee_comptable": annee_comptable,
	           "montant_inst": 0}
	invest_balance = {'disponible': 0, 'last_balance': 0, 'cheques': 0, 'solde': 0, 'debit': 0, 'credit': 0,
	                  'annee_comptable': 0, 'montant_inst': 0,'balance': 0}

	fonct_balance={'disponible': 0,'balance': 0, 'last_balance': 0, 'cheques': 0, 'solde': 0, 'debit': 0, 'credit': 0,'annee_comptable': 0, 'montant_inst': 0}

	for tcpte in typecompte:

		b=get_by_id(last_balances,tcpte.id)
		rfc = get_by_id(list(reports_from_cancel_trx), tcpte.id)
		rfnc = get_by_id(list(reports_from_non_cancel_trx), tcpte.id)
		lb_credit=b.get("credit",0) if b else 0
		lb_debit=  b.get("debit",0) if b else 0
		last_balance=lb_credit - lb_debit

		print("----- Debut type solde ---- {}".format(tcpte.name,))


		print("information report gestion =={}".format(b, ))
		print("dernier balance via report {}".format(last_balance, ))

		print("report from trxx annule=={}".format(rfc, ))
		print("report from trxx non annule=={}".format(rfnc, ))

		last_report_rfnc_credit = rfnc.get("credit", 0) if rfnc else 0
		last_report_rfnc_debit =  rfnc.get("debit", 0) if rfnc else 0
		last_report_rfnc=last_report_rfnc_credit - last_report_rfnc_debit

		last_report_rfc_credit = rfc.get("credit", 0) if rfc else 0
		last_report_rfc_debit = rfc.get("debit", 0) if rfc else 0
		last_report_rfc =last_report_rfc_credit- last_report_rfc_debit

		last_balance = last_balance + last_report_rfc + last_report_rfnc
		print("last balance o balance entree  : {}".format(last_balance,))

		x = get_by_id(canceleds_trx_debit, tcpte.id)
		y = get_by_id(none_canceleds_trx_debit, tcpte.id)
		minst = get_by_id(t_pcharges_by_typeompte, tcpte.id)
		print("trx  annnules debit ==  {}".format(x, ))
		print("trx non  annnules =={}".format(y, ))


		credit  = y.get("credit",0) if y else 0
		debit_non_annule = y.get("debit", 0) if y else 0
		#print("credit  : {}".format(credit, ))
		credit=last_balance + credit

		debit_annule= x.get("credit",0) if x else 0

		debit = debit_non_annule  - debit_annule

		print("credit  : {}  debbit {}".format(credit, debit))
		print("----- fin type solde ----")
		montant_inst=minst.get("amount",0)if minst else 0
		solde=credit-debit
		disponible=solde-montant_inst

		item = {"disponible": int(disponible), "last_balance": int(last_balance), "cheques": cheques,
		           "solde": int(solde),
		           "debit": int(debit), "credit": int(credit), "annee_comptable": annee_comptable,
		           "montant_inst": montant_inst,"typecompte":tcpte.id,"nature":tcpte.nature,"name":tcpte.name}
		infos_solde.append(item)
		if tcpte.nature==NATURE_COMPTE.FONCTIONNEMENT:
			fonct_balance["credit"] = fonct_balance["credit"] + item["credit"]
			fonct_balance["debit"] = fonct_balance["debit"] + item["debit"]
			fonct_balance["cheques"] = fonct_balance["cheques"] + item["cheques"]
			fonct_balance["balance"] = fonct_balance["balance"] + item["solde"]
			fonct_balance["last_balance"] = fonct_balance["last_balance"] + item["last_balance"]
			fonct_balance["disponible"] = fonct_balance["disponible"] + item["disponible"]
			fonct_balance["montant_inst"] = fonct_balance["montant_inst"] + item["montant_inst"]
		if tcpte.nature==NATURE_COMPTE.INVESTISSEMENT:
			invest_balance["credit"] = invest_balance["credit"] + item["credit"]
			invest_balance["debit"] = invest_balance["debit"] + item["debit"]
			invest_balance["cheques"] = invest_balance["cheques"] + item["cheques"]
			invest_balance["balance"] = invest_balance["balance"] + item["solde"]
			invest_balance["last_balance"] = invest_balance["last_balance"] + item["last_balance"]
			invest_balance["disponible"] = invest_balance["disponible"] + item["disponible"]
			invest_balance["montant_inst"] = invest_balance["montant_inst"] + item["montant_inst"]


		context["credit"]=context["credit"]+item["credit"]
		context["debit"] = context["debit"] + item["debit"]
		context["cheques"] = context["cheques"] + item["cheques"]
		context["balance"] = context["balance"] + item["solde"]
		context["last_balance"] = context["last_balance"] + item["last_balance"]
		context["disponible"] = context["disponible"] + item["disponible"]
		context["montant_inst"] = context["montant_inst"] + item["montant_inst"]



		if update==True:
			try:
				ctrx=compte.sous_comptes.get(compte_id=compte.id,type_id=tcpte.id,gestion_id=gestion)
				ctrx.balance=item["disponible"]
				ctrx.report = item["disponible"]
				ctrx.save()
			except CompteTrx.DoesNotExist:
				pass

	context.update({"compte":compte.short_compte,"soldes":infos_solde,"invest_balance":invest_balance,"fonct_balance":fonct_balance})

	if with_trx:
		trx = trx.order_by('date_rlv')
		return (rsv_objs,trx,context)
	else:return context


def format_trx_datas(input_datas,inverse=False):
	output=[]
	if input_datas:
		datas = sorted(list(input_datas), key=lambda k: k['typecompte'], reverse=False)
		for key, items in itertools.groupby(datas, operator.itemgetter('typecompte')):
			_datas = list(items)
			last_credit = 0
			last_debit = 0

			item = _datas[0]
			for _item in _datas:
				if _item["sens"] == SENS_TRX.CREDIT: last_credit += _item["amount"]
				if _item["sens"] == SENS_TRX.DEBIT: last_debit += _item["amount"]
			if inverse:
				output.append(
					{"nature": item["nature"], "name": item["name"], "debit": last_credit, "credit": last_debit,
					 "typecompte": key})
			else:

				output.append(
					{"nature": item["nature"], "name": item["name"], "debit": last_debit, "credit": last_credit,
					 "typecompte": key})
	return output

def compute_all_balances_for_compte(compte, gestion=None, startdate=None, enddate=None, inst=1, update=True,
                                    for_gerant=False,type_compte=None,with_trx=False,with_cancel_trx=False,for_releve=False):
	if not gestion:
		an = AnneeComptable.active_gestion()
		gestion = an.id
	else:
		an = AnneeComptable.objects.get(id=gestion)
	print_date_1 = an.period.lower
	start_january = datetime.datetime(print_date_1.year, 1, 1)
	if not startdate: startdate = start_january
	if not enddate: enddate = datetime.datetime(print_date_1.year, 12, 31)
	include_endate = enddate + datetime.timedelta(days=0)


	all_trx = Transaction.objects.filter(account_depot=compte.short_compte,jour_comptable__annee_comptable_id=gestion,
	                                     jour_comptable__jour__range=(start_january, include_endate))


	all_type_soldes=TypeCompteTrx.objects.all()
	if type_compte :
		all_type_soldes=all_type_soldes.filter(id=type_compte.id)
		#all_trx = all_trx.filter(typecompte=type_compte)

	all_type_soldes_id=all_type_soldes.values_list("id",flat=True)
	all_trx = all_trx.filter(typecompte_id__in=all_type_soldes_id)


	rsv_objs = ReservationFond.objects.none()
	if inst == 1:
		if for_releve == 1:
			etapes= etapes = [ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE]
		else :etapes = [ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE, ETAPE_ORDRE_PAYMENT.VALIDE, ETAPE_ORDRE_PAYMENT.ACCEPTE]
		rsv_objs = ReservationFond.objects.filter(ordre__compte__short_compte=compte.short_compte, close=False,
		                                          ordre__etape__in=etapes,
		                                          created__range=(start_january, include_endate),
		                                          ordre__gestion_id=gestion,ordre__typecompte_id__in=all_type_soldes_id)

	soldes=compute_balance_new(compte, startdate, enddate, gestion,all_trx,rsv_objs,all_type_soldes,update=update,with_trx=with_trx,with_cancel_trx=with_cancel_trx)
	return soldes


def update_trx_with_typetrx():
	inde=TypeCompteTrx.objects.get(code="BI")
	fod = TypeCompteTrx.objects.get(code="BF")
	Transaction.objects.filter(type_nature=NATURE_COMPTE.INVESTISSEMENT).update(typecompte=inde)
	Transaction.objects.filter(type_nature=NATURE_COMPTE.FONCTIONNEMENT).update(typecompte=fod)


def create_reportgestion():
	inde = TypeCompteTrx.objects.get(code="BI")
	fod = TypeCompteTrx.objects.get(code ="BF")
	for r in Report.objects.all():
	    rg=ReportGestion()
	    rg.typecompte=inde
	    rg.compte=r.compte
	    rg.created=r.created
	    rg.creator=r.creator
	    rg.anne_comptable=r.anne_comptable
	    rg.gestion_courant=r.gestion_courant
	    rg.amount=r.amount_invest
	    rg.sens = SENS_TRX.CREDIT
	    rg.save()

	    rg1 = ReportGestion()
	    rg1.typecompte = fod
	    rg1.compte = r.compte
	    rg1.created = r.created
	    rg1.anne_comptable = r.anne_comptable
	    rg1.gestion_courant = r.gestion_courant
	    rg1.amount = r.amount_fonc
	    rg1.creator = r.creator
	    rg1.sens=SENS_TRX.CREDIT
	    rg1.save()



def create_basculement(gestion):
	gestion_precedent=gestion.parent
	if gestion_precedent:
		cpts=CompteTrx.objects.filter(gestion_id=gestion_precedent.id,reportable=True,reporter_bascule=True,dejabascule=False)
		for  r in cpts:
			rg = ReportGestion()
			rg.typecompte = r.type
			rg.compte = r.compte
			rg.creator = gestion.createur
			rg.anne_comptable = r.gestion
			rg.gestion_courant = gestion
			rg.amount = r.report_valide
			rg.sens = SENS_TRX.CREDIT
			rg.save()
			#on encrie un contre report

			rg1 = ReportGestion()
			rg1.typecompte = r.type
			rg1.compte = r.compte
			rg1.creator = gestion.createur
			rg1.anne_comptable = r.gestion
			rg1.gestion_courant = r.gestion
			rg1.amount = r.report_valide
			rg1.sens = SENS_TRX.DEBIT
			rg1.save()
			r.date_basculement=timezone.now()
			r.dejabascule=True
			r.save()
	#creation nouveaux  compte
	comptes = CompteDepot.objects.all()
	for c in comptes:
		for typecpte in TypeCompteTrx.objects.filter(actif=True,auto_gen_account=True):
			obj, created = CompteTrx.objects.get_or_create(
				compte_id=c.id,
				gestion_id=gestion.id,type_id=typecpte.id,
				defaults={"taux":typecpte.taux,"reporter_bascule":typecpte.reporter_bascule,"reportable":typecpte.reportable},
			)

@receiver(post_save, sender=AnneeComptable)
def create_report_from_bascule(sender, **kwargs):
	instance = kwargs['instance']
	if kwargs.get('created', True):
		#recalcule tout les solde
		create_basculement(instance)

class DemandeOP(TimeStampedModel):
	choices = [(PAYMENT_MEAN_TYPE.RETRAIT, PAYMENT_MEAN_TYPE.RETRAIT)]
	reference = models.CharField(_('référence'), max_length=128, unique=True)
	# date_comptable = models.DateField("date comptable", max_length=12)

	object = models.CharField(_('Object'), max_length=128)
	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.CASCADE)
	compte = models.ForeignKey(CompteDepot, verbose_name=_('Compte de dépôt'), on_delete=models.CASCADE,
	                           related_name="+")

	amount = MoneyField(_('Montant'), max_digits=20, decimal_places=2, default_currency='XOF', null=True, default=0,
	                    validators=[MinMoneyValidator(0)])


	beneficiaire = models.CharField(_('Bénéficiaire'), max_length=128)
	ninea = models.CharField(_('Ninea'), max_length=128, blank=True, null=True)



	cin_receptionnaire = models.CharField(_('Cin récupérateur'), max_length=128, null=True, blank=True)
	phone_receptionnaire = PhoneNumberField(_("Tel Bénéficiaire"), null=False, blank=False)
	sig_reference = models.CharField(_('Référence SIGCDD'), max_length=80, blank=True, null=True)

	gestion = models.ForeignKey(AnneeComptable, verbose_name=_('Gestion current'), related_name="+",
	                            on_delete=models.SET_NULL, blank=True, null=True)

	typecompte = models.ForeignKey(TypeCompteTrx, verbose_name=_('Type de compte'), on_delete=models.SET_NULL,
	                                related_name="+", blank=True, null=True)

	objects = OrdrePaymentManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Demande OP')
		verbose_name_plural = _('Demandes OP')
		ordering = ['-created']

	def __str__(self):
		return "{}".format(self.id, )




	def save(self, *args, **kwargs):
		if not self.reference:
			try:
				self.reference = CommonHelper.Instance().generate_code("cddaccount", "demandeop", "reference",
				                                                       size=9,prefix="D")
			except:
				error = ValueError("A possible infinite loop was detected")
				raise error

		return super().save(*args, **kwargs)

def update_trx_with_typetrx():
	inde=TypeCompteTrx.objects.get(code="BI")
	fod = TypeCompteTrx.objects.get(code="BF")
	Transaction.objects.filter(type_nature=NATURE_COMPTE.INVESTISSEMENT).update(typecompte=inde)
	Transaction.objects.filter(type_nature=NATURE_COMPTE.FONCTIONNEMENT).update(typecompte=fod)


def get_rlv():
	for trx in Transaction.objects.all():
		if trx.date_rlv is None:
			if hasattr(trx, "transactionop") and trx.transactionop.is_cancel_trx and trx.transactionop.ref_trx:
				trx.date_rlv =  trx.created.date()
			else : trx.date_rlv =  trx.jour_comptable.jour
			trx.save()


def up_rsv():
	rsvs=ReservationFond.objects.filter(payment_mean__isnull=True)
	for rsv in rsvs:
		trx= rsv.rsv_trx.last()
		if trx:
			rsv.payment_mean=trx.payment_mean
		else : rsv.payment_mean=rsv.ordre.payment_mean
		rsv.save()





def can_debit_trx_by_type( amount, type, compute_disponible):
	type = type.nature
	if type == NATURE_COMPTE.FONCTIONNEMENT:
		balance = compute_disponible["fonct_balance"]["disponible"]
	elif type == NATURE_COMPTE.INVESTISSEMENT:
		balance = compute_disponible["invest_balance"]["disponible"]
	else:
		return False
	print("type {} ======balance {}======= amouunt   {}===========================".format(type,balance,amount))
	if balance >= amount:
		return True
	else:
		return False

def can_debit_account_for_op(op):
	cpt=op.compte
	compute_disponible = compute_all_balances_for_compte(op.compte, update=False, gestion=op.gestion_id,
	                                                     for_gerant=True,
	                                                     type_compte=op.typecompte)

	if can_debit_trx_by_type(int(op.amount.amount), op.typecompte, compute_disponible):
		return True
	else:
		"Montant solde {} du compte {} est inférieur au montant des op {}".format(
			op.typecompte.name, cpt.short_compte, int(op.amount.amount))
		raise SigException("Montant supérieur au solde du compte")




def update_cancel_trx():
	for trx in TransactionOP.objects.all():
		if trx.ref_trx :
			trx.is_cancel_trx=True
			trx.is_cancel_trx_0=trx.is_cancel_trx
			trx.save()
