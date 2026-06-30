import datetime

from datetime import timedelta, date

from django.conf import settings
from django.contrib.postgres.fields import DateRangeField
from django.db import transaction
from django.db.models.signals import post_save
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from djmoney.models.fields import MoneyField
from phonenumber_field.modelfields import PhoneNumberField
from psycopg2.extras import DateRange
from schwifty import BIC
from cddaccount import NATURE_COMPTE, NATURE_FONDS, STATUS_CREATION, PROVENANCE_FOND
from cddaccount.manager import *
from core.models import Ministere, Secteur, PosteComptable, ProfileDCP, CodeService, ProfilePC, Agent, Direction, \
	Structure

from helpers.exceptions import SigException
from helpers.models import Person
from helpers.models import Role, justificatif_directory_path
# Create your models here.
from helpers.validators import only_digit_validator
from djmoney.money import Money
LENGHT_COMPTE_DEPOT = 24

LENGHT_COMPTE_DEPOT_WHITHOUT_RIB = 22

SEQUENCE = "879"
import logging

logger = logging.getLogger(__name__)

UEMOA_COODE = {"SN": "25", "BJ": "21", "BF": "26", "CI": "39", "GW": "76", "ML": "43", "NE": "55", "TG": "37"}
#  V_CPT:=V_CODE_PAYS||substr(V_CPT,3,3)||substr(V_CPT,6,17);
# V_RIB:=97-(MOD((17*TO_NUMBER(substr(V_CPT,1,5)))+(53*TO_NUMBER(substr(V_CPT,6,5)))+(81*TO_NUMBER(substr(V_CPT,11,6)))+(3*TO_NUMBER(substr(V_CPT,17,6))),97));
# SN175010970000036121879
# SN175010ff36821879
from djmoney.models.validators import MinMoneyValidator, MaxMoneyValidator


def remove_prefix(text, prefix):
	if text.startswith(prefix):
		return text[len(prefix):]
	return text  # or whatever


def getmax_value(refs, prefix_matricule):
	d = 0
	for item in refs:
		if item.startswith(prefix_matricule):
			nu = remove_prefix(item, prefix_matricule)  # item.removeprefix(prefix_matricule)
			nu = nu.lstrip("0")
			v = int(nu)
			if v > d:
				d = v
	return d


def generate_rib(V_CODE_PAYS, V_CPT):
	V_CODE_PAYS = UEMOA_COODE[V_CODE_PAYS]
	V_CPT = "{}{}{}".format(V_CODE_PAYS, V_CPT[2:5], V_CPT[5:22])
	print(V_CPT)
	# logging.info("V_CPT: {} {} {} = {}".format(V_CODE_PAYS,V_CPT[2:5],V_CPT[5:22],V_CPT))
	MULT_17 = 17 * int(V_CPT[0:5])
	# logging.info("MULT_17 : 17* {} == {}".format(V_CPT[0:5],MULT_17))
	MULT_53 = 53 * int(V_CPT[5: 10])
	# logging.info("MULT_53 : 53* {} == {}".format(V_CPT[5: 10], MULT_53))

	MULT_81 = 81 * int(V_CPT[10: 16])

	# logging.info("MULT_81 : 81* {} == {}".format(V_CPT[10: 16], MULT_81))
	MULT_3 = 3 * int(V_CPT[16: 22])

	# logging.info("MULT_3 : 3* {} == {}".format(V_CPT[16: 22], MULT_3))
	sum_mutl = MULT_17 + MULT_53 + MULT_81 + MULT_3
	mod = sum_mutl % 97
	V_RIB = 97 - mod
	if V_RIB < 10:
		V_RIB = "0{}".format(V_RIB, )
	else:
		V_RIB = "{}".format(V_RIB, )
	return V_RIB


def generate_sequence_of_twelve(code_service, code_secteur, taille, refs):
	# ca doit etre sur 12 possition pass

	nbre_comptes = taille + 1
	short_code = str(nbre_comptes).zfill(3)  # max 999 comptes par secteur et par servvice
	start_str = f"{code_service}{code_secteur}{short_code}"

	if start_str in refs:
		nb = getmax_value(refs, '') + 1
		start_str = f"{nb}"
		print(start_str)
	return start_str.zfill(12)


def generate_bank_sequence(poste, code_agence):
	s = "{}{}".format(code_agence, poste)
	return s


def generate_account_number(poste, secteur, service, code_agence, taille, refs):
	# SN175 010 97 368 21 879
	# SN175 010  10 00003685601042

	twelve_sequence = generate_sequence_of_twelve(service, secteur, taille, refs)
	bank_ref = generate_bank_sequence(poste, code_agence)
	s = "{}{}".format(bank_ref, twelve_sequence)

	reste = LENGHT_COMPTE_DEPOT_WHITHOUT_RIB - len(s)
	if reste == 0:
		rib = generate_rib("SN", s)
		return "{}{}".format(s, rib), str(int(twelve_sequence)), rib
	else:
		raise ValueError("La taille est differente a {}".format(LENGHT_COMPTE_DEPOT_WHITHOUT_RIB))


class FichierData(TimeStampedModel):
	name = models.CharField(_('Non'), max_length=128)
	type = models.CharField(_('Type'), max_length=128)
	fichier =models.FileField(upload_to="fichier_deb")

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Chargemennt fichier')
		verbose_name_plural = _('Chargemennt fichier')

	def __str__(self):
		# noinspection PyPep8
		return "{}".format(self.name, )

class SettingsOP(TimeStampedModel):
	name = models.CharField(_('Non'), max_length=128)
	rejet_notif_benef = models.BooleanField("Notifier en cas de rejet le beneficiaire", default=False)
	rejet_notif_gerant = models.BooleanField("Notifier en cas de rejet le gerant", default=False)
	visa_notif_benef = models.BooleanField("Notifier le beneficiaire pour le visa", default=False)
	visa_notif_gerant = models.BooleanField("Notifier  le gerant pour le visa", default=False)

	visa_notif_pc = models.BooleanField("Notifier poste comptable ", default=False)

	api_avis_credit = models.BooleanField("Activer api avis de credit", default=False)
	api_avis_debit = models.BooleanField("Activer api avis de debit", default=False)
	api_compense = models.BooleanField("Activer api compense", default=False)
	extras = models.JSONField(_('Details'), null=True, blank=True, editable=False)
	aster_variant = models.CharField("Aster variant", max_length=20, null=True, blank=True, )

	@classmethod
	def object(cls):
		return cls._default_manager.all().first()  # Since only one item

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Parametrage OP')
		verbose_name_plural = _('Parametrage OP')

	def __str__(self):
		# noinspection PyPep8
		return "{}".format(self.name, )


class AnneeComptable(TimeStampedModel):
	period = DateRangeField("Période", help_text="Merci d'utiliser ce format: <em>YYYY-MM-DD</em>.")
	createur = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Agent'), on_delete=models.CASCADE,
	                             related_name="+")

	name = models.CharField(_('Nom'), max_length=128)
	actif = models.BooleanField(_('Actif?'), default=True)
	bloque = models.BooleanField(_('bloque?'), default=True)

	parent = models.ForeignKey('self', verbose_name=_("annee precedent"), null=True, blank=True,
	                           on_delete=models.SET_NULL, related_name='last_year')

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Année comptable')
		verbose_name_plural = _('Année comptable')
		permissions = [
			("use_anneecomptable", "Peut utiliser l annee comtable")
		]

	def format_period(self):
		a = "{} {}".format(self.period.lower.strftime('%Y-%m-%d'),
		                   self.period.upper.strftime('%Y-%m-%d')) if self.period else "----"
		return a

	def year(self):
		a = "{}".format(self.period.lower.strftime('%Y'))
		return a

	def contains_date(self, date):
		if self.period.lower <= date < self.period.upper:
			return True
		else:
			return False

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.name,)

	def save(self, *args, **kwargs):

		if self.name is None or len(self.name) == 0:
			self.name = "Gestion ({} {})".format(self.period.lower.strftime('%Y-%m-%d'),
			                                     self.period.upper.strftime('%Y-%m-%d'))
		if self.actif is True:
			self.__class__._default_manager.filter(actif=True).update(actif=False)
		lower_date = self.period.lower

		rg = DateRange(lower_date, lower_date + timedelta(days=1))

		if self.id:
			if self.__class__._default_manager.exclude(id=self.id).filter(period__contains=rg).exists():
				raise Exception("Une année comptable existe sur cette période pour ce compte et ce gérant ")
		else:
			if self.__class__._default_manager.filter(period__contains=rg).exists():
				raise Exception("Une année comptable existe sur cette période pour ce compte et ce gérant ")
		super().save(*args, **kwargs)

	@classmethod
	def active_gestion(cls):
		return cls._default_manager.filter(actif=True).first()  # Since only one item

	@classmethod
	def current_gestion(cls):
		# lower_date= datetime.datetime(timezone.now().year, 1, 1)
		lower_date = datetime.datetime(date.today().year, 1, 1)
		enddate = lower_date + timedelta(days=10)
		rg = DateRange(lower_date.date(), enddate.date())
		return cls._default_manager.filter(period__contains=rg).last()


class JourneeComptable(TimeStampedModel):
	jour = models.DateField("Journée")
	user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Agent'), on_delete=models.CASCADE,
	                         related_name="journee_comptables")
	annee_comptable = models.ForeignKey(AnneeComptable, verbose_name=_('Gestion'), on_delete=models.CASCADE,
	                                    related_name="+")

	name = models.CharField(_('Nom'), max_length=128)
	actif = models.BooleanField(_('Actif?'), default=True)
	close = models.BooleanField(_('Fermer?'), default=False)

	# objects=GestionCompteDepotManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Journee comptable')
		verbose_name_plural = _('Journee comptable')
		unique_together = ("annee_comptable", "user", "jour")

	def format_name(self):
		a = "J COMPTA : {}".format(self.jour.strftime('%d-%m-%Y'))
		return a

	def day(self):
		a = "{}".format(self.jour.strftime('%d-%m-%Y'))
		return a

	def year(self):
		a = "{}".format(self.jour.strftime('%Y'))
		return a

	def format_period(self):
		a = "JOURNEE COMPTABLE : {} de {}".format(self.jour.strftime('%Y-%m-%d'),
		                                          self.user.full_name()) if self.period else "----"
		return a

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.id,)

	def save(self, *args, **kwargs):

		if self.name is None or len(self.name) == 0:
			self.name = self.format_name()
		if self.actif is True:
			self.__class__._default_manager.filter(user=self.user, actif=True).update(actif=False)

		super().save(*args, **kwargs)


def get_or_create_journee_comptable(user, jour):
	try:
		annee_comptable = AnneeComptable.objects.filter(period__contains=jour).last()
		if annee_comptable:

			obj, created = JourneeComptable.objects.get_or_create(
				jour=jour, annee_comptable=annee_comptable,
				user=user, defaults={"actif": True}
			)
			obj.actif = True
			obj.save()

			# annee_comptable.actif=True
			# annee_comptable.save()

			return obj
		else:
			raise SigException(message="Aucune année comptable pour cette date : {}".format(jour, ))
	except:
		traceback.print_exc()
		raise SigException(message="Erreur inconnue")


# Create your models here.
from allauth.account.signals import user_logged_in
from django.dispatch import receiver


@receiver(user_logged_in)
def set_user_journeecomptable(sender, request, *args, **kwargs):
	if request.user.has_perm('cddaccount.use_anneecomptable'):
		get_or_create_journee_comptable(request.user, datetime.date.today())


class Nature(models.Model):
	name = models.CharField(_('Nom'), max_length=128)

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Nature')

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.name,)


class SousNature(models.Model):
	nature = models.ForeignKey(Nature, verbose_name=_('Nature'), on_delete=models.CASCADE,
	                           related_name="+")
	name = models.CharField(_('Nom'), max_length=128)

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Sous Nature')

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.name,)


class Bank(models.Model):
	name = models.CharField(_('Nom'), max_length=128, )
	bic = models.CharField(_('Bic'), max_length=12, unique=True)
	code = models.CharField(_('Code banque'), max_length=8, unique=True)

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Banque')
		verbose_name_plural = _('Banques')

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.name,)

	def reference_for_cddaccount(self):
		if len(self.code) > 5:
			raise ValueError("La taille du  code banque est superieur à 5 ")
		else:
			return self.code

	def get_country(self):
		return self.code[0:2]

	def save(self, **kwargs):
		try:
			bic = BIC(str(self.bic))
		except:
			import traceback
			c = traceback.format_exc(limit=0)
			error = ValueError(c)
			raise error
		return super().save(**kwargs)


class CodeAgence(models.Model):
	bank = models.ForeignKey(Bank, verbose_name=_('banque'), on_delete=models.CASCADE, related_name="+")
	code = models.CharField(_('Code agence'), max_length=20, unique=True, validators=[only_digit_validator])
	actif = models.BooleanField(_('Actif ?'), default=True, )

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Code agence')
		verbose_name_plural = _('Code agence')

	def __str__(self):
		# noinspection PyPep8
		return "{} ({})".format(self.code, self.bank)

	def reference_for_cddaccount(self):
		if len(self.code) > 3:
			raise ValueError("La taille du  code agence est superieur à 3 ")
		else:
			return self.code

	def get_code_guichet(self):
		code_guichet = "{}{}".format(self.bank.reference_for_cddaccount(), self.reference_for_cddaccount())
		return code_guichet



class TypeCompteTrx(models.Model):
	name = models.CharField(_('Nom'), max_length=128)
	code = models.CharField(_('Code'), max_length=20,unique=True)
	provenance = models.CharField(_('Provenance'), max_length=128,choices=PROVENANCE_FOND.CHOICES,
	                          default=PROVENANCE_FOND.BUDGET)
	nature = models.CharField(_('Nature'), max_length=128, choices=NATURE_COMPTE.CHOICES,
	                          default=NATURE_COMPTE.FONCTIONNEMENT)

	actif = models.BooleanField(_('Actif ?'), default=False, )
	reportable = models.BooleanField(_('Reportable ?'), default=False, )
	taux = models.PositiveSmallIntegerField("Taux", default=0)

	visible = models.BooleanField(_('Visibble ?'), default=True, editable=False )
	auto_gen_account = models.BooleanField(_('Auto génerer les comptes ?'), default=True, )
	reporter_bascule = models.BooleanField(_('Reporter apres basculement?'), default=True, help_text="")

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Type compte transactionnel')

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.name,)


class CompteDepot(TimeStampedModel):
	reference_demande = models.CharField(_('Numero acte de création'), max_length=128)

	agent = models.ForeignKey(ProfileDCP, verbose_name=_('Agent dcp créateur'), on_delete=models.CASCADE,
	                          related_name="+")

	ministere = models.ForeignKey(Ministere, verbose_name=_('Ministère/Institution'), on_delete=models.CASCADE,
	                              related_name="+", null=True, blank=True)
	direction = models.ForeignKey(Direction, verbose_name=_('direction'), on_delete=models.SET_NULL, related_name="+",
	                              null=True, blank=True)

	agence = models.ForeignKey(CodeAgence, verbose_name=_('Code agence'), on_delete=models.CASCADE, related_name="+")

	open_date = models.DateField(_('Date ouverture'), max_length=12)

	poste = models.ForeignKey(PosteComptable, verbose_name=_('Poste Comptable'), on_delete=models.CASCADE,
	                          related_name="comptes_depots")
	secteur = models.ForeignKey(Secteur, verbose_name=_('Secteur'), on_delete=models.CASCADE, related_name="+")

	code_service = models.ForeignKey(CodeService, verbose_name=_('Service'), on_delete=models.CASCADE, related_name="+")
	nature = models.CharField(_('Nature'), max_length=128, choices=NATURE_COMPTE.CHOICES,
	                          default=NATURE_COMPTE.FONCTIONNEMENT)

	typefond = models.CharField(_('Type fond'), max_length=128, choices=NATURE_FONDS.CHOICES,
	                            default=NATURE_FONDS.FONDSDAVANCE)

	compte = models.CharField(_('Numéro Compte'), max_length=128, unique=True, editable=True)
	short_compte = models.CharField(_('Compte Aster'), max_length=128, unique=True, editable=False)

	reference_demande = models.CharField(_('Numéro acte de création'), max_length=128, null=True, blank=True)
	libelle = models.CharField('Libellé', max_length=128)

	libelle_court = models.CharField('Libellé court', max_length=30, null=True, blank=True)

	banque = models.ForeignKey(Bank, verbose_name=_('Banque'), on_delete=models.CASCADE, related_name="+")
	guichet = models.CharField(_('Guichet'), max_length=128)

	compteBanque = models.CharField(_('Compte banque'), max_length=128)
	rib = models.CharField(_('Rib'), max_length=128)
	actif = models.BooleanField(_('Actif ?'), default=False, )
	cloture = models.BooleanField(_('Clôture ?'), default=False, )
	valide = models.BooleanField(_('Valide ?'), default=False, )
	secrete = models.BooleanField(_('Secrete ?'), default=False, )
	balance = MoneyField(max_digits=20, decimal_places=2, default_currency='XOF', null=True, default=0)

	structure = models.ForeignKey(Structure, verbose_name=_('structure'), on_delete=models.SET_NULL, related_name="+",
	                              null=True, blank=True)

	balance_insvest = MoneyField("Solde investissement", max_digits=20, decimal_places=2, default_currency='XOF',
	                             null=True, default=0)
	balance_fonct = MoneyField("Solde fonctionnement", max_digits=20, decimal_places=2, default_currency='XOF',
	                           null=True, default=0)

	objects = CompteDepotManager()

	# ("compte","nature","secteur","libelle","libelle_court","direction","poste","ministere","agent","created","open_date","actif")

	class Meta:
		app_label = 'cddaccount'
		verbose_name = "Compte de dépôt"
		ordering = ['-pk']
		permissions = [
			("add_activationcompte", "Peut activer un compte dépot"),
			("use_secretecompte", "Peut utiliser un compte dépot secrete"),
			("configure_secretecompte", "Peut configurer un compte dépot secrete"),
		]

	def as_dict(self):
		data = {"compte": self.short_compte, "libelle": self.libelle, "libelle_court": self.libelle_court,
		        "poste_comptable": self.poste.reference, "iban": self.compte,
		        "date": "{:%d-%m-%Y %H:%M}".format(self.created)}
		return data

	def sql_bind_dict(self):
		data = {"pk": str(self.id), "compte": self.short_compte, "libelle": self.libelle,
		        "libelle_court": self.libelle_court, "iban": self.compte,
		        "date_creation": "{:%d-%m-%Y %H:%M}".format(self.created)}
		return data

	def labels(self):
		return ["COMPTE", "LIBELLE", "POSTE_COMPTABLE"]


	def get_comptetrx(self, type):
		sous_compte=self.sous_comptes.get(type=type)
		if sous_compte:
			return sous_compte
		else:
			error = SigException(message="Type de solde inconnu")
			raise error

	def get_solde_by_type(self, type, compute=False):
		balance = None
		if type == NATURE_COMPTE.FONCTIONNEMENT:
			balance = self.balance_fonct
		elif type == NATURE_COMPTE.INVESTISSEMENT:
			balance = self.balance_insvest
		return balance

	def can_debit_trx_by_type_deprecate(self, amount, type, compute=False):
		if type == NATURE_COMPTE.FONCTIONNEMENT:
			balance = self.balance_fonct.amount
		elif type == NATURE_COMPTE.INVESTISSEMENT:
			balance = self.balance_insvest.amount
		else:
			return False
		if balance >= amount and self.actif and hasattr(self, "validation_cd") and not self.cloture:
			return True
		else:
			return False

	def can_debit_trx_by_type(self, amount, type, compute=False):
		compte_trx=self.get_comptetrx(type)
		if type == NATURE_COMPTE.FONCTIONNEMENT:
			balance = self.balance_fonct.amount
		elif type == NATURE_COMPTE.INVESTISSEMENT:
			balance = self.balance_insvest.amount
		else:
			return False
		if balance >= amount and self.actif and hasattr(self, "validation_cd") and not self.cloture:
			return True
		else:
			return False




	def is_open(self):
		if self.actif and hasattr(self, "validation_cd") and not self.cloture:
			return True
		else:
			return False


	def debit_by_type_remove_deprecate(self, amount, type):

		if type == NATURE_COMPTE.FONCTIONNEMENT:
			balance = self.balance_fonct
		elif type == NATURE_COMPTE.INVESTISSEMENT:
			balance = self.balance_insvest
		else:
			error = SigException(message="Type de solde inconnu ")
			raise error
		if self.can_debit_trx_by_type(amount, type):
			amount = Money(amount, "XOF")
			if type == NATURE_COMPTE.FONCTIONNEMENT:
				self.balance_fonct = balance - amount
			elif type == NATURE_COMPTE.INVESTISSEMENT:
				self.balance_insvest = balance - amount
			self.balance = self.balance_insvest + self.balance_fonct
			self.save()
		else:
			error = SigException(
				message="Montant solde compte {} {} inférieur  au montant demandé {}".format(type, balance, amount))
			raise error

	def debit_by_type(self, amount, type,gestion=None):
		if gestion is None: gestion = AnneeComptable.current_gestion().id
		sous_compte=self.sous_comptes.get(type=type,gestion_id=gestion)
		if sous_compte:
			sous_compte.debit(amount)
		else:
			error = SigException(message="Type de solde inconnu")
			raise error
	def credit_by_type(self, amount, type,gestion=None):
		if gestion is None:gestion=AnneeComptable.current_gestion().id
		sous_compte = self.sous_comptes.get(type=type,gestion_id=gestion)
		if sous_compte:
			pass
			#sous_compte.credit(amount)
		else:
			error = SigException(message="Type de solde inconnu")
			raise error

	def infos_account(self):
		types = [{"name": NATURE_COMPTE.FONCTIONNEMENT}, {"name": NATURE_COMPTE.INVESTISSEMENT}]

		mandataires = self.depositaires.all()
		c={"balance": int(self.balance.amount), "id": self.id, "type_natures": types,
		        "mandataires": [{"id": item.pk, "name": item.full_name()} for item in mandataires]}
		gerant=self.get_current_gerant()
		if gerant:
			c.update({"gerant":{"name":gerant.full_name()}})


		return c

	def types_account(self):
		types = [(NATURE_COMPTE.FONCTIONNEMENT, NATURE_COMPTE.FONCTIONNEMENT),
		         (NATURE_COMPTE.INVESTISSEMENT, NATURE_COMPTE.INVESTISSEMENT)]

		return types

	def __str__(self):
		# noinspection PyPep8
		return "{} {}".format(self.libelle, self.compte, )

	def format_iban(self):
		s = self.compte.strip()
		return " ".join((s[:5], s[5:10], s[10:22], s[22:24]))

	def benef_iban_items(self):
		s = self.compte.strip()
		d = [s[:5], s[5:11], s[11:23], s[-2:]]
		return d

	def format_aster(self):
		s = self.compte.strip()
		return " ".join((s[10:22],))

	def get_current_month_releve_old(self):
		end_date = datetime.datetime.now()
		start_date = end_date - timedelta(days=10)
		gestion = AnneeComptable.active_gestion().id
		success_url = reverse('cddaccount:releve_compte_view',
		                      kwargs={"reference": self.short_compte, "startdate": start_date, "enddate": end_date,
		                              "gestion": gestion, "inst": 0})
		return success_url

	def get_current_month_releve(self):
		end_date = datetime.datetime.now()
		# start_date = end_date - timedelta(days=10)
		gestion = AnneeComptable.active_gestion()
		start_date = gestion.period.lower
		success_url = reverse('cddaccount:releve_compte_view',
		                      kwargs={"reference": self.short_compte, "startdate": start_date, "enddate": end_date,
		                              "gestion": gestion.id, "inst": 0})
		return success_url

	def get_current_full_releve(self):
		end_date = datetime.datetime.now()
		# start_date = end_date - timedelta(days=10)
		gestion = AnneeComptable.active_gestion()
		start_date = gestion.period.lower
		success_url = reverse('cddaccount:releve_compte_detaille_view',
		                      kwargs={"reference": self.short_compte, "startdate": start_date, "enddate": end_date,
		                              "gestion": gestion.id, "inst": 0})
		return success_url

	def get_absolute_url(self):
		"""Get url for user's detail view.

		Returns:
			str: URL for user detail.

		"""
		return reverse("cddaccount:comptedepot_dash_view", kwargs={"pk": self.pk})

	def can_acces(self, user):
		return self.__class__._default_manager.filter(id=self.id).by_agent(user).exists()

	def set_iban_items(self):
		s = self.compte.strip()
		print(s)
		self.short_compte = str(int(s[10:22]))
		self.rib = s[22:24]
		self.banque = self.agence.bank
		self.guichet = self.agence.get_code_guichet()
		self.compteBanque = self.compte

	def set_shortiban_items(self, s):
		s = s.strip()

		b = s.zfill(12)
		bank_ref = self.generate_bank_sequence()
		rib = generate_rib(self.agence.bank.get_country(), "{}{}".format(bank_ref, b))
		compteBanque = "{}{}{}".format(bank_ref, b, rib)

		self.short_compte = s
		self.rib = rib
		self.banque = self.agence.bank
		self.guichet = self.agence.get_code_guichet()
		self.compte = compteBanque
		self.compteBanque = compteBanque

	def save(self, **kwargs):
		if self.compte is None or len(self.compte) == 0:
			self.banque = self.agence.bank
			self.guichet = self.agence.get_code_guichet()
			self.compte, self.short_compte, self.rib = self.generate_account_number()
			self.compteBanque = self.compte

		return super().save(**kwargs)

	def format_acccount_number(self):
		s = self.compte
		return s

	def validate(self):
		if hasattr(self, "validation_cd"):
			_str = """<button type="button" class="btn  btn-sm btn-outline-success btn-round" disabled ><i class="fa fa-check"></i></button>"""
		else:
			create_url = reverse('cddaccount:create_validationcompte', kwargs={'id': self.pk})

			_str = """<button type="button" class="validate-item btn btn-sm btn-primary " data-form-url="{}">
          <span class="fa fa-pencil">valider</span>
        </button>""".format(create_url, )

	def actions(self):
		return self

	def getmax_value(self, refs):
		d = 0
		for item in refs:
			nu = item.lstrip("0")
			try:
				v = int(nu)
				if v > d:
					d = v
			except:
				return d
		return d

	def generate_sequence_of_twelve(self):
		# ca doit etre sur 12 possition pass
		code_service = self.code_service.reference_for_cddaccount()
		code_secteur = self.secteur.reference_for_cddaccount()

		refs = self.__class__._default_manager.filter(code_service=self.code_service,
		                                              secteur=self.secteur).values_list(
			"short_compte", flat=True)

		nbre_comptes = len(refs) + 1
		# nbre_comptes = self.__class__._default_manager.filter(code_service=self.code_service, secteur=self.secteur).count() + 1
		short_code = str(nbre_comptes).zfill(3)  # max 999 comptes par secteur et par servvice

		start_str = f"{code_service}{code_secteur}{short_code}"

		if start_str in refs:
			nb = self.getmax_value(refs) + 1
			start_str = f"{nb}"
			print(start_str)
		aster_compte = start_str.zfill(12)

		return aster_compte

	def generate_bank_sequence(self):
		post_ref = self.poste.reference_for_cddaccount()
		bank_ref = self.agence.get_code_guichet()
		s = "{}{}".format(bank_ref, post_ref)
		return s

	# SN175 010 10 00 00 36 85 60 02

	def generate_account_number(self):

		# SN175 010 97 368 21 879

		twelve_sequence = self.generate_sequence_of_twelve()
		bank_ref = self.generate_bank_sequence()
		s = "{}{}".format(bank_ref, twelve_sequence)

		reste = LENGHT_COMPTE_DEPOT_WHITHOUT_RIB - len(s)
		if reste == 0:
			rib = generate_rib(self.agence.bank.get_country(), s)
			return "{}{}".format(s, rib), str(int(twelve_sequence)), rib
		else:
			raise ValueError("La taille est differente a {}".format(LENGHT_COMPTE_DEPOT_WHITHOUT_RIB))

	def get_current_gerant(self):
		a = self.compte_affections_gerants.filter(actif=True).last()

		if a: return a.gerant
		return None

	def saisie_url(self):
		return reverse('cddaccount:create_ordrepayment', kwargs={"pk": self.pk})






class CompteTrx(TimeStampedModel):
	gestion=models.ForeignKey(AnneeComptable, verbose_name=_('gestion'), on_delete=models.CASCADE,
	                          related_name="+")
	type = models.ForeignKey(TypeCompteTrx, verbose_name=_('type compte trx'), on_delete=models.CASCADE,
	                           related_name="+")
	reportable = models.BooleanField(_('Reportable ?'), default=False, )
	compte = models.ForeignKey(CompteDepot, verbose_name=_('compte'), on_delete=models.CASCADE,
	                          related_name="sous_comptes")

	balance = MoneyField("Solde disponible", max_digits=20, decimal_places=2, default_currency='XOF',
	                           null=True, default=0)
	taux = models.PositiveSmallIntegerField("Taux", default=0)

	report_valide = MoneyField("Report valide", max_digits=20, decimal_places=2, default_currency='XOF',
	                           null=True, default=0)

	report = MoneyField("Report", max_digits=20, decimal_places=2, default_currency='XOF',
	                    null=True, default=0)
	date_basculement = models.DateTimeField(_('Date basculement'), max_length=12, blank=True, null=True)
	reporter_bascule = models.BooleanField(_('Reporter apres basculement?'))
	dejabascule = models.BooleanField(_('deja bascule'), default=False, editable=False)


	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Comptes de transactions')
		unique_together=("type","compte","gestion")

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.compte.id,)


	@property
	def report_calcule(self):
		return self.report * float(self.taux / 100)


	def can_debit(self, amount):
		if self.balance >= amount and self.compte.actif and hasattr(self.compte, "validation_cd") and not self.compte.cloture:
			return True
		else:
			return False

	def debit(self, amount):
		amount = Money(amount, "XOF")
		if self.can_debit(amount):

			self.balance = self.balance - amount
			self.save()
		else:
			error = SigException(
				message="Montant solde compte {} {} inférieur  au montant demandé {}".format(self.type, self.balance, amount))
			raise error

	def can_credit(self, amount):
		if self.compte.actif and hasattr(self.compte, "validation_cd") and not self.compte.cloture:
			return True
		else:
			return False

	def credit(self, amount):
		amount = Money(amount, "XOF")
		if self.can_credit(amount):

			self.balance = self.balance + amount
			self.save()
		else:
			error = SigException(message="Impossible de créditer ce compte ")
			raise error

from django.contrib.sessions.models import Session


class GerantCD(Agent):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='gerant_cd', on_delete=models.CASCADE)
	# teaser_signature = ThumbnailerImageField(_('signature'), upload_to=signature_directory_path)
	acte_nomin = models.CharField(_('Numéro acte de nomination'), max_length=128, null=True, blank=True)
	valide = models.BooleanField(_('Valide ?'), default=False, )

	status = models.CharField(_('Statut'), max_length=128, choices=STATUS_CREATION.CHOICES,
	                          default=STATUS_CREATION.NOUVEAU)

	agent = models.ForeignKey(ProfilePC, verbose_name=_('agent poste comptable'), on_delete=models.CASCADE,
	                          related_name="+", null=True, blank=True)

	date_validation = models.DateTimeField("Date de validatiion", null=True, blank=True)
	justificatif = models.FileField(upload_to=justificatif_directory_path, verbose_name=_('Acte de nomination'),
	                                null=True, blank=True)

	poste = models.ForeignKey(PosteComptable, verbose_name=_('Poste  comptable'), on_delete=models.CASCADE,
	                          related_name="gestionnaires_cd")
	structure = models.ForeignKey(Structure, verbose_name=_('structure'), on_delete=models.SET_NULL, related_name="+",
	                              null=True, blank=True)

	objects = GerantCDManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Gérant Compte Dépôt')
		verbose_name_plural = _('Gérant Compte Dépôt')

	def __str__(self):
		return "{} {} ".format(self.full_name(), self.matricule)

	def save(self, **kwargs):
		self.fonction = Role.GERANT
		return super().save(**kwargs)

	def format_mes_compte_depots(self):
		qs = self.mes_compte_depots.filter(actif=True).select_related("compte")
		value = """<ul id="id_type_tax">"""

		for item in qs:
			delete_url = reverse('cddaccount:delete_gerantcd', kwargs={'pk': self.pk})
			update_url = reverse('cddaccount:update_gerantcd', kwargs={'pk': self.pk})
			str = """
					        <button type="button" class="update-item btn btn-sm btn-warning " data-form-url="{}">
					          <span class="fa fa-pencil"></span>
					        </button>
					         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
					          <span class="fa fa-trash"></span>
					        </button>""".format(update_url, delete_url)

			str = """<a type='button' class='update-item btn btn-sm btn-danger' data-form-url='{}'>valider</a>""".format(
				update_url, )

			x = """<a class="nav-link nav-link-label" href="#" type="button"
			data-toggle="popover" 
			data-html="true" 
			sanitize= "false"
			data-placement="top" 
			data-container="body" 
			data-original-title="Affectation" 
			data-content="{}">{}</a>""".format(str, item.compte.short_compte, )
			# x=""" <button id="btn-pop" type="button" class="btn btn-lg btn-danger" data-toggle="popover" title="Popover title" datas-content="<p>Here is a button</p><a class='btn btn-primary'>Click me!</button>" data-html="true">Click to toggle popover</button>"""

			a = """<li>{}</li>""".format(item.compte.short_compte, )
			# noinspection PyPep8,PyPep8
			value += a
		value += """</ul>"""
		return format_html(value)

	def can_acces(self, user):
		return self.__class__._default_manager.filter(id=self.id).by_agent(user).exists()

	def account_is_valid(self):
		d = self.valide and self.date_validation is not None and self.status == STATUS_CREATION.VALIDE
		return d

	def actions(self):

		delete_url = reverse('cddaccount:delete_gerantcd', kwargs={'pk': self.pk})
		update_url = reverse('cddaccount:update_gerantcd', kwargs={'pk': self.pk})
		validate_url = reverse('cddaccount:validate_gerantcd_data', kwargs={'matricule': self.matricule})
		# affectation_url = reverse('cddaccount:update_gestioncomptedepot', kwargs={'pk': self.id})
		str = """
		        <button type="button" class="update-item btn btn-sm btn-warning " data-form-url="{}">
		          <span class="fa fa-pencil"></span>
		        </button>
		         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
		          <span class="fa fa-trash"></span>
		        </button>
		        """.format(update_url, delete_url)
		if self.status == STATUS_CREATION.ATTENTE:
			str += """<button type="button" class="validate-item btn btn-sm btn-purple" data-form-url="{}">
		         <span >Valider</span>
		        </button>
		        """.format(validate_url, )

		return format_html(str)

	def get_absolute_url(self):
		"""Get url for user's detail view.

		Returns:
			str: URL for user detail.

		"""
		if self.user.is_active:
			if self.account_is_valid():
				return reverse("cddaccount:gerantcd_profile", kwargs={"matricule": self.matricule})
			else:
				return reverse("cddaccount:complete_gerant", kwargs={"pk": self.id})


class ValidationCompte(TimeStampedModel):
	agent = models.ForeignKey(ProfileDCP, verbose_name=_('agent'), on_delete=models.SET_NULL, related_name="+",
	                          blank=True, null=True)
	compte = models.OneToOneField(CompteDepot, verbose_name=_('compte depot'), on_delete=models.CASCADE,
	                              related_name="validation_cd")
	description = models.TextField(_('Description'), max_length=128, blank=True, null=True)
	actif = models.BooleanField(_('Actif?'), default=True)

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Validation Compte Dépot')
		verbose_name_plural = _('Validation Compte Dépot')

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.id,)


class GestionCompteDepot(TimeStampedModel):
	period = DateRangeField("Période", help_text="Merci d'utiliser ce format: <em>YYYY-MM-DD</em>.")
	agent_pc = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Agent poste comptable'),
	                             on_delete=models.CASCADE, related_name="+")
	gerant = models.ForeignKey(GerantCD, verbose_name=_('Gérant '), on_delete=models.CASCADE,
	                           related_name="mes_compte_depots")
	compte = models.ForeignKey(CompteDepot, verbose_name=_('Compte de dépôt'), on_delete=models.CASCADE,
	                           related_name="compte_affections_gerants")
	name = models.CharField(_('Nom'), max_length=128)
	actif = models.BooleanField(_('Actif?'), default=True)
	acte_nomin = models.CharField(_('Numéro acte de nomination'), max_length=128, null=True, blank=True)
	justificatif = models.FileField(upload_to=justificatif_directory_path, verbose_name=_('Document de nomination'),
	                                null=True, blank=True)
	objects = GestionCompteDepotManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Gestion Compte')
		verbose_name_plural = _('Gestion Compte')

	def format_period(self):
		a = "{} {}".format(self.period.lower.strftime('%Y-%m-%d'), self.format_upper()) if self.period else "----"
		return a

	def format_upper(self):
		if self.period.upper:
			return self.period.upper.strftime('%Y-%m-%d')
		else:
			return "--"

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.id,)

	def save(self, *args, **kwargs):

		if self.name is None or len(self.name) == 0:
			self.name = "{} period ({} {})".format(self.compte.libelle_court, self.period.lower.strftime('%Y-%m-%d'),
			                                       self.format_upper())
		if self.actif is True:
			self.__class__._default_manager.filter(compte_id=self.compte_id, actif=True).update(actif=False)
		lower_date = self.period.lower

		rg = DateRange(lower_date, lower_date + timedelta(days=1))
		if self.__class__._default_manager.filter(compte_id=self.compte_id, actif=True, period__contains=rg).exclude(
				id=self.id).exists():
			raise SigException(message="Une affectation existe sur cette période pour ce compte et ce gérant ")
		super().save(*args, **kwargs)


@transaction.atomic()
def create_gerant_affectation(gerant, agent_pc, compte):
	try:
		gestion = GestionCompteDepot()
		gestion.gerant = gerant
		if agent_pc:
			gestion.agent_pc = agent_pc
		gestion.compte = compte
		gestion.acte_nomin = gerant.acte_nomin
		gestion.justificatif = gerant.justificatif
		today = date.today();
		rg = DateRange(today, today + timedelta(days=1000))
		gestion.actif = True
		gestion.period = rg
		gestion.save()
	except SigException as e:
		raise e


class AgentSaisieCD(Agent):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name=Role.AGENT_SAISIE_CD.lower(),
	                            on_delete=models.CASCADE)
	valide = models.BooleanField(_('Valide ?'), default=False, )

	status = models.CharField(_('Statut'), max_length=128, choices=STATUS_CREATION.CHOICES,
	                          default=STATUS_CREATION.NOUVEAU)

	gerant = models.ForeignKey(GerantCD, verbose_name=_('gérant'), on_delete=models.CASCADE,
	                           related_name="mes_agentsaisiecd", )

	date_validation = models.DateTimeField("Date de validation", null=True, blank=True)

	comptes = models.ManyToManyField(CompteDepot, verbose_name=_('Comptes dépôts'),
	                                 related_name="comptescd_agentsaisiecd")

	objects = AgentSaisieCDManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Agent Saisie Compte Dépôt')
		verbose_name_plural = _('Agent Saisie Compte Dépôt')
		permissions = [
			("sendsms_agentsaisiecd", "Peut envoyer un sms")
		]

	def format_comptes(self):
		value = """<ul id="id_type_tax">"""
		for item in self.comptes.all():
			a = """<li><a> {}:{}</a></li>""".format(item.libelle_court, item.short_compte)
			# noinspection PyPep8,PyPep8
			value += a
		value += """</ul>"""
		return format_html(value)

	def save(self, **kwargs):
		self.fonction = Role.AGENT_SAISIE_CD
		return super().save(**kwargs)

	def account_is_valid(self):
		d = self.valide and self.date_validation is not None and self.status == STATUS_CREATION.VALIDE
		return d

	def actions(self):

		delete_url = reverse('cddaccount:delete_agentsaisiecd', kwargs={'pk': self.pk})
		update_url = reverse('cddaccount:update_agentsaisiecd', kwargs={'pk': self.pk})
		validate_url = reverse('cddaccount:validate_agentsaisiecd_data', kwargs={'matricule': self.matricule})
		str = """
		        <button type="button" class="update-item btn btn-sm btn-warning " data-form-url="{}">
		          <span class="fa fa-pencil"></span>
		        </button>


		         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
		          <span class="fa fa-trash"></span>
		        </button>
		        """.format(update_url, delete_url)
		if self.status == STATUS_CREATION.ATTENTE:
			str += """<button type="button" class="validate-item btn btn-sm btn-purple" data-form-url="{}">

		         <span >Valider</span>
		        </button>
		        """.format(validate_url, )

		sms_url = reverse('cddaccount:send_sms', kwargs={'matricule': self.matricule})

		str += """<button type="button" class="validate-item btn btn-sm btn-secondary" data-form-url="{}">

				         <span class="feather icon-message-square"></span>
				        </button>
				        """.format(sms_url, )

		return format_html(str)

	def get_absolute_url(self):
		"""Get url for user's detail view.

		Returns:
			str: URL for user detail.

		"""
		if self.user.is_active:
			if self.account_is_valid():
				return reverse("cddaccount:agentsaisiecd_profile_view", kwargs={"matricule": self.matricule})
			else:
				return reverse("cddaccount:complete_agentsaisiecd", kwargs={"pk": self.id})



class Depositaire(Person):
	comptes = models.ManyToManyField(CompteDepot, verbose_name=_('comptes depots'), related_name="depositaires")
	matricule = models.CharField(_("Matricule"), max_length=50)
	phone = PhoneNumberField(_("Téléphone"), null=False, blank=False)
	objects = DepositaireManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Depositaire')
		verbose_name_plural = _('Depositaires')

	def __str__(self):
		return self.full_name()

	def actions(self):
		delete_url = reverse('cddaccount:delete_depositaire', kwargs={'pk': self.pk})
		update_url = reverse('cddaccount:update_depositaire', kwargs={'pk': self.pk})
		str = """
		        <button type="button" class="update-item btn btn-sm btn-warning " data-form-url="{}">
		          <span class="fa fa-pencil"></span>
		        </button>
		         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
		          <span class="fa fa-trash"></span>
		        </button>
		        """.format(update_url, delete_url)
		return format_html(str)

	def format_comptes(self):
		value = """<ul id="id_type_tax">"""
		for item in self.comptes.all():
			a = """<li><a> {}:{}</a></li>""".format(item.libelle_court, item.short_compte)
			# noinspection PyPep8,PyPep8
			value += a
		value += """</ul>"""
		return format_html(value)




class Mandataire(Person):
	gerant = models.ForeignKey(GerantCD, verbose_name=_('Gerant'), related_name="mandataires", on_delete=models.CASCADE)
	matricule = models.CharField(_("Matricule"), max_length=50)
	phone = PhoneNumberField(_("Téléphone"), null=False, blank=False)
	objects = MandataireManager()

	class Meta:
		app_label = 'cddaccount'
		verbose_name = _('Mandataire')
		verbose_name_plural = _('Mandataires')

	def __str__(self):
		return self.full_name()

	def actions(self):
		delete_url = reverse('cddaccount:delete_mandataire', kwargs={'pk': self.pk})
		update_url = reverse('cddaccount:update_mandataire', kwargs={'pk': self.pk})
		str = """
		        <button type="button" class="update-item btn btn-sm btn-warning " data-form-url="{}">
		          <span class="fa fa-pencil"></span>
		        </button>
		         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
		          <span class="fa fa-trash"></span>
		        </button>
		        """.format(update_url, delete_url)
		return format_html(str)



def create_comptetr():
	comptes= CompteDepot.objects.all()
	for type in TypeCompteTrx.objects.filter(actif=True):
		for c in comptes:
			v=CompteTrx()
			if type.nature==NATURE_COMPTE.FONCTIONNEMENT:
				v.balance=c.balance_fonct
			if type.nature==NATURE_COMPTE.INVESTISSEMENT:
				v.balance=c.balance_insvest
			v.compte=c
			v.type=type
			v.reporter_bascule=False
			v.gestion = AnneeComptable.current_gestion()
			v.save()




def generate_compte_trx_by_type(typecpte):
	comptes = CompteDepot.objects.all()
	for c in comptes:
		v = CompteTrx()
		v.compte = c
		v.reportable=typecpte.reportable
		v.taux=typecpte.taux
		v.type = typecpte
		v.gestion=AnneeComptable.current_gestion()
		v.save()
@receiver(post_save, sender=TypeCompteTrx)
def generate_compte_trx(sender, **kwargs):
	instance = kwargs['instance']
	if kwargs.get('created', True):
		generate_compte_trx_by_type(instance)


