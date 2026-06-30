from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from djmoney.models.fields import MoneyField
from datetime  import date
from phonenumber_field.modelfields import PhoneNumberField
from bankcheck import STATUS_COMMANDE, STATUS_CHEQUE
from bankcheck.manager import *
# Create your models here.
from cddaccount.models import CompteDepot, GerantCD,SettingsOP,PosteComptable
from core.models import ProfilePC, Agent
from djmoney.models.validators import MaxMoneyValidator, MinMoneyValidator
from helpers.exceptions import SigException
from helpers.models import notif_by_sms, Person
from helpers.commons import CommonHelper, OTP_STEP, OTP_STEP_IN_MIN
LENGHT_COMPTE_DEPOT=24
from django.urls import reverse
LENGHT_COMPTE_DEPOT_WHITHOUT_RIB=22
import logging
logger = logging.getLogger(__name__)
import  datetime

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text  # or whatever

def getmax_value(refs,prefix_matricule):
    d=0
    for item in refs:
        if item.startswith(prefix_matricule):
            nu = remove_prefix(item,prefix_matricule)   #item.removeprefix(prefix_matricule)
            nu=nu.lstrip("0")
            v= int(nu)
            if v>d:
                d=v
    return d



class SettingsChequier(TimeStampedModel):
	first_sequence = models.PositiveBigIntegerField(_('Premier reference'))
	last_sequence = models.PositiveBigIntegerField(_('Dernier reference'))
	name = models.CharField(_('Non'), max_length=128)

	@classmethod
	def object(cls):
		return cls._default_manager.all().first()  # Since only one item

	class Meta:
		app_label = 'bankcheck'
		verbose_name = _('Sequence Setting')
		verbose_name_plural = _('sequence Settings')

	def __str__(self):
		# noinspection PyPep8
		return "{}".format(self.name, )





class DAP(TimeStampedModel):
	reference = models.CharField(_('réference'), max_length=6, unique=True)
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
	class Meta:
		app_label = 'bankcheck'
		verbose_name = _('DAP')
		verbose_name_plural = _('DAP')

	@classmethod
	def object(cls):
		return cls._default_manager.all().first()  # Since only one item

	def __str__(self):
		# noinspection PyPep8
		return "{}".format(self.name, )

	def save(self, *args, **kwargs):

		if not self.reference:
			try:
				self.reference = CommonHelper.Instance().generate_code("bankcheck", "dap", "reference", size=6)
			except:
				error = ValueError("A possible infinite loop was detected")
				raise error
		return super().save(*args, **kwargs)



class AgentDAP(Agent):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='agent_dap', on_delete=models.CASCADE)
	valide = models.BooleanField(_('Valide ?'), default=False, )
	dap = models.ForeignKey(DAP, verbose_name=_('dap'), on_delete=models.CASCADE,related_name="+")
	date_validation=models.DateTimeField("Date de validatiion",null=True,blank=True)


	#objects = AgentDAPManager()

	class Meta:
		app_label = 'bankcheck'
		verbose_name = _('Agent dap')
		verbose_name_plural = _('Agent dap')

	def save(self, **kwargs):
		self.fonction=Role.AGENT_DAP
		return super().save(**kwargs)

	def account_is_valid(self):
		d=self.valide and self.date_validation is not None
		return d


class TypeChequier(TimeStampedModel):
	nom = models.CharField(_('nom'), max_length=128)
	taille= models.PositiveSmallIntegerField("taille")

	class Meta:
		app_label = 'bankcheck'
		verbose_name="type chequier"

	def __str__(self):
		# noinspection PyPep8
		return "{} {}".format(self.nom, self.taille, )

class Commande(TimeStampedModel):
	reference = models.CharField(_('Réferene'), max_length=128, unique=True)
	compte = models.ForeignKey(CompteDepot, verbose_name=_('Compte de dépôt'), on_delete=models.CASCADE, related_name="+")
	demandeur = models.ForeignKey(GerantCD, verbose_name=_('gérant'), on_delete=models.SET_NULL, related_name="+",
	                          blank=True, null=True)

	agent_pc = models.ForeignKey(ProfilePC, verbose_name=_('agent pc'), on_delete=models.SET_NULL, related_name="+",
	                          blank=True, null=True)
	agent_dap = models.ForeignKey(AgentDAP, verbose_name=_('agent dap'), on_delete=models.SET_NULL, related_name="+",
	                             blank=True, null=True)

	traiter = models.BooleanField("Traiter ?", default=False)
	accepter = models.BooleanField("Accepter ?", default=False)
	status = models.CharField(_('Statut'), max_length=128, choices=STATUS_COMMANDE.CHOICES,
	                          default=STATUS_COMMANDE.NOUVEAU)

	process_date = models.DateField(_('Date validation'), max_length=12, null=True, blank=True)
	acceptation_date = models.DateField(_('Date acceptation'), max_length=12, null=True, blank=True)
	first_sequence = models.PositiveBigIntegerField(_('Premier réference'), null=True, blank=True)
	last_sequence = models.PositiveBigIntegerField(_('Dernier réference'), null=True, blank=True)
	objects=CommandeManager()
	class Meta:
		app_label = 'bankcheck'
		verbose_name="Commande chéquier"
		ordering = ['-pk']
		permissions = [
			("accepter_commande", "Peut accepter la comande chequier"),
			("valider_commande", "Peut valider la coommande de chequier")
		]

	def can_acces(self,user):
		return  self.__class__._default_manager.filter(id=self.id).by_agent(user).exists()

	def get_instance(self):
		return self

	def get_next_sequence(self, last_sequence):
		initial=[]
		for item in self.items.all():
			for i in range(item.nombres):
				initial.append(item.as_dict())

	def format_items(self):

		value = """<ul id="id_type_tax" style="list-style: none;">"""

		for item in self.items.all():
			a = """<li><a>{}</a></li>""".format(item.nombres,)
			# noinspection PyPep8,PyPep8
			value += a
		value += """</ul>"""
		return format_html(value)

	def save(self, *args, **kwargs):
		if not self.reference:
			try:
				self.reference = self.generate_dv_reference()#CommonHelper.Instance().generate_code("bankcheck", "commande", "reference", size=9)
			except:
				error = ValueError("A possible infinite loop was detected")
				raise error
		return super().save(*args, **kwargs)

	def generate_dv_reference(self):

		today= date.today()
		year = str(today.year)
		year = year[-2:]
		prefix = year
		refs = self.__class__._default_manager.filter(created__year=today.year).values_list("reference", flat=True)

		nbs=len(refs)+1
		b = f"{nbs}"
		b = b.zfill(4)
		new_ref= '{}{}'.format(prefix,b)
		if new_ref in refs:
			nb = getmax_value(refs,'') + 1
			b = f"{nb}"
			b = b.zfill(6)
			new_ref = '{}{}'.format(prefix, b)

		return new_ref

class ElementCommande(TimeStampedModel):
	commande = models.ForeignKey(Commande, verbose_name=_('commande'), on_delete=models.CASCADE, related_name="items")
	type =models.ForeignKey(TypeChequier,verbose_name=_('Nombre chèque'),on_delete=models.CASCADE, related_name="+")
	nombres=models.PositiveSmallIntegerField("nombre",default=1)

	first_reference = models.PositiveBigIntegerField(_('Premier réference'),null=True,blank=True)
	last_reference = models.PositiveBigIntegerField(_('Dernier réference'),null=True,blank=True)

	class Meta:
		app_label = 'bankcheck'
		verbose_name="Element commande"

	def as_dict(self):
		data = {"type": self.type,"nombres": self.nombres}
		return data

	def set_sequence_range(self, last_sequence):
		self.first_reference=last_sequence+1
		self.last_reference= self.first_reference+self.nombres*self.type.taille


from django_otp.oath import TOTP

from binascii import unhexlify
class Chequier(TimeStampedModel):
	dap = models.ForeignKey(DAP, related_name='+', on_delete=models.CASCADE, verbose_name="Dap")
	demande = models.CharField(_('Numéro de demande'), max_length=128)
	reference = models.CharField(_('Réference'), max_length=128,unique=True)
	compte= models.ForeignKey(CompteDepot, verbose_name=_('Compte dépôt'), on_delete=models.CASCADE, related_name="+")
	debut= models.PositiveBigIntegerField("début")

	editeur = models.ForeignKey(AgentDAP, verbose_name=_('agent dap'), on_delete=models.SET_NULL, related_name="+",
	                             blank=True, null=True)

	fin = models.PositiveBigIntegerField("fin")
	taille= models.PositiveSmallIntegerField("taille")
	type =models.ForeignKey(TypeChequier,verbose_name=_('Type'),on_delete=models.CASCADE, related_name="+")
	vide=models.BooleanField("Est épuisé ?",default=False)
	blocked=models.BooleanField("Est bloqué",default=False)
	prise_en_charge = models.BooleanField("Prise en charge", default=False)
	delivered = models.BooleanField("Est délivré ",default=False)
	distribue = models.BooleanField("Est distribué ", default=False)

	blocked_date = models.DateTimeField(_('Date blocage'), max_length=12,null=True,blank=True)
	prise_en_charge_date = models.DateTimeField(_('Date prise en charge'), max_length=12,null=True,blank=True)

	distribue_date = models.DateTimeField(_('Date distribution'), max_length=12, null=True, blank=True)

	vide_date = models.DateTimeField(_('Date vide'), max_length=12,null=True,blank=True)
	activate_date = models.DateTimeField(_('Date activation'), max_length=12, null=True, blank=True)
	delivered_date = models.DateTimeField(_('Date de délivrance'), max_length=12, null=True, blank=True)
	otp_gerant = models.PositiveIntegerField(_('otp gerant'), editable=False, blank=True, null=True)
	otp_apc = models.PositiveIntegerField(_('otp agent pc'), editable=False, blank=True, null=True)
	phone_gerant = models.CharField(_('Tel gérant'), max_length=128,blank=True, null=True)
	phone_postecomptable = models.CharField(_('Tel poste comptable'), max_length=128,blank=True, null=True)

	gerant = models.CharField(_('gérant'), max_length=128,editable=False)
	agent_pc = models.CharField(_('agent poste comptable'), max_length=128, editable=False)

	is_printed = models.BooleanField("Deja imprimer", default=False)

	is_use = models.BooleanField("Deja entamé", default=False)

	objects=ChequierManager()
	class Meta:
		app_label = 'bankcheck'
		verbose_name="Chequier"
		ordering = ['-pk']

		permissions = [
			("delivrer_chequier", "Peut delivrer un chequier"),
			("bloquer_chequier", "Peut bloquer un chequier"),
			("priseencharge_chequier", "Peut faire la prise en charge un chequier")
		]
	def is_valid(self):
		return not self.blocked and not self.vide,

	def get_otp_retrait(self,otp):
		compte = "Bienvenue sur SIGCDD "
		identifiant = "Votre code de validation pour le retrait de vos chequier est {}. Ce code expire dans {} min".format(otp,
		                                                                                                 OTP_STEP_IN_MIN)
		message = "{}. {}".format(compte, identifiant)
		return message

	@classmethod
	def static_get_otp_retrait(cls,otp):
		compte = "Bienvenue sur SIGCDD "
		identifiant = "Votre code de validation pour le retrait de vos chequier est {}. Ce code expire dans {} min".format(
			otp,
			OTP_STEP_IN_MIN)
		message = "{}. {}".format(compte, identifiant)
		return message


	def __str__(self):
		# noinspection PyPep8
		return "{} {}".format(self.id, self.compte, )


	def save(self, *args, **kwargs):
		if not self.reference:
			try:
				self.reference = CommonHelper.Instance().generate_code("bankcheck", "chequier", "reference", size=10)
			except:
				error = ValueError("A possible infinite loop was detected")
				raise error
		return super().save(*args, **kwargs)

	def can_acces(self,user):
		return  self.__class__._default_manager.filter(id=self.id).by_agent(user).exists()

	def get_instance(self):
		return self





class Cheque(TimeStampedModel):
	chequier = models.ForeignKey(Chequier, related_name='cheques', on_delete=models.CASCADE, verbose_name="Chequier")
	reference = models.CharField(_('Réference'), max_length=128,unique=True)
	amount = MoneyField(max_digits=20, decimal_places=2, default_currency='XOF', null=True, default=0,validators=[MinMoneyValidator(0)])

	use=models.BooleanField("Est consommé ?",default=False)
	delivred = models.BooleanField("Est livré ?", default=False)
	blocked=models.BooleanField("Est bloqué",default=False)
	actif = models.BooleanField("Actif",default=True)

	en_compense = models.BooleanField("En compense", default=False)
	en_annulation = models.BooleanField("Annuler", default=False)
	en_mis_op = models.BooleanField("Mise en opposition", default=False)

	compense_date = models.DateTimeField(_('Date compense'), max_length=12, null=True, blank=True)
	annulation_date = models.DateTimeField(_('Date annulation'), max_length=12, null=True, blank=True)
	mis_op_date = models.DateTimeField(_('Date mis en op'), max_length=12, null=True, blank=True)



	delivred_date = models.DateTimeField(_('Date réception'), max_length=12,null=True,blank=True)
	blocked_date = models.DateTimeField(_('Date blocage'), max_length=12, null=True, blank=True)
	use_date = models.DateTimeField(_('Date vide'), max_length=12,null=True,blank=True)
	observations = models.TextField(_('observations'), default="RAS")
	trx = models.CharField(_('trx'), max_length=128, null=True,blank=True)
	endosser_par=models.CharField(_('Endosser par'), max_length=128, null=True,blank=True)

	cin_receptionnaire = models.CharField(_('NIN récupérateur'), max_length=128, null=True, blank=True)
	phone_receptionnaire = models.CharField(_('Tel récupérateur'), max_length=128, null=True, blank=True)

	key = models.CharField(_('key'), max_length=80, editable=False)
	drift = models.SmallIntegerField(default=1, editable=False)
	step = models.PositiveSmallIntegerField(default=OTP_STEP, editable=False)
	last_t = models.BigIntegerField(default=-1, editable=False)
	required_otp = models.BooleanField(default=True, editable=False)
	otp = models.PositiveIntegerField(_('otp'), editable=False, blank=True, null=True)
	send_otp = models.BooleanField(default=False, )
	objects=ChequeManager()

	class Meta:
		app_label = 'bankcheck'
		verbose_name="Cheque"

		ordering = ['-pk']
		permissions = [
			("receptionner_cheque", "Peut receptionner cheque"),
			("search_cheque","Peut rechercher cheque")
		]

	def is_valid(self):
		return self.chequier.is_valid() and not self.blocked and not self.use



	def can_delivered(self):

		return self.chequier.is_valid() and not self.blocked and self.use and not self.delivred

	def is_usable(self):
		msg=None
		if hasattr(self, "compense"):
			msg="Chèque {} déjà compensé".format(self.reference,)
		if hasattr(self, "miseop_cheque"):
			msg = "Chèque {} mise en opposition".format(self.reference, )
		if hasattr(self, "annulation_cheque"):
			msg = "Chèque {} déjà est annulé".format(self.reference, )
		if hasattr(self, "rejet"):
			msg = "Chèque {} déjà est rejeté ".format(self.reference, )
		if msg : raise SigException(message=msg)

		if not self.chequier.is_valid() or self.blocked:
			raise SigException(message="Numéro de chèque inconnu")
		return True

	def get_status_cheque(self):
		msg=None
		if hasattr(self, "compense"):
			msg="Chèque {} déjà compensé".format(self.reference,)
		elif hasattr(self, "miseop_cheque"):
			msg = "Chèque {} mise en opposition".format(self.reference, )
		elif hasattr(self, "annulation_cheque"):
			msg = "Chèque {} déjà est annulé".format(self.reference, )
		elif hasattr(self, "rejet"):
			msg = "Chèque {} déjà est rejeté ".format(self.reference, )

		if not self.chequier.is_valid() or self.blocked:
			msg = "Chèque {} déjà est bloquée ".format(self.reference, )
		return msg


	def can_use_for_compense(self):
		try:
			result = self.is_usable()
			if self.use and self.delivred :
				return True
			else:
				msg = "Chèque {} pas encore réceptionné".format(self.reference, )
				raise SigException(message=msg)
		except SigException as e: raise e

	def can_use_for_annulation(self):
		try:
			result = self.is_usable()
		except SigException as e: raise e
	def can_use_for_miseop(self):
		try:
			result = self.is_usable()
			if self.use and self.delivred :
				return True
			else:
				msg = "Chèque {} pas encore réceptionné".format(self.reference, )
				raise SigException(message=msg)
		except SigException as e: raise e

	def can_use_in_op(self):
		try:
			self.is_usable()
			if self.use:
				msg = "Il existe déjà un OP sur ce chèque {} ".format(self.reference, )
				raise SigException(message=msg)
			else:
				return True
		except SigException as e: raise e

	@property
	def bin_key(self):
		"""
		The secret key as a binary string.
		"""
		return unhexlify(self.key.encode())

	def can_acces(self,user):
		return  self.__class__._default_manager.filter(id=self.id).by_agent(user).exists()

	def generate_otp_and_save(self):
		self.generate_otp()
		self.save()

	def generate_otp(self):
		#totp_obj = CommonsUtils.totp_generator(self.key, self.step)
		totp_obj = TOTP(bytes(self.key, "utf-8"), step=300)
		self.otp = totp_obj.token()

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


	def send_cheque_otp(self,phone):
		if self.required_otp:
			message = self.get_otp_msg()
			try:
				notif_by_sms(phone, message)
			except:
				import traceback
				traceback.print_exc()

	def __str__(self):
		# noinspection PyPep8
		return "{}".format(self.reference, )


from bankcheck.signals import chequier_status_changed


@receiver(chequier_status_changed, sender=Chequier)
def generate_cheques(sender, **kwargs):
	try:
		chequier = kwargs['instance']
		if chequier.distribue and chequier.distribue_date and chequier.delivered_date and chequier.delivered and chequier.prise_en_charge_date and chequier.prise_en_charge:
			for i in range(chequier.debut, chequier.fin+1, 1):
				try:
					cheque = Cheque()
					cheque.chequier = chequier
					cheque.reference = str(i)
					cheque.actif = True
					cheque.observations = ""
					cheque.save()
				except Cheque.DoesNotExist:
					pass
	except:
		import traceback
		traceback.print_exc()
		c = traceback.format_exc(limit=0)
		c = c.replace("Traceback (most recent call last):", "")
		raise SigException(c)




class CompenseCheque(TimeStampedModel):
	cheque = models.OneToOneField(Cheque, related_name='compense', on_delete=models.CASCADE, verbose_name="cheques")
	reference = models.CharField(_('Réference cheque'), max_length=128,unique=True)
	beneficiare = models.CharField(_('Bénéficiaire'), max_length=128)
	banque = models.CharField(_('Banque'), max_length=128)
	compte = models.CharField(_('compte'), max_length=128, null=True, blank=True)
	amount = MoneyField(max_digits=20, decimal_places=2, default_currency='XOF', null=True, default=0,validators=[MinMoneyValidator(0)])

	aster_date = models.DateTimeField(_('Date aster'), max_length=12, null=True, blank=True)
	date_compense = models.DateTimeField(_('Date compense'), max_length=12,null=True,blank=True)
	observations = models.TextField(_('observations'), default="RAS")
	trx = models.CharField(_('trx'), max_length=128, null=True,blank=True)


	aster = models.CharField(_('Aster'), max_length=128, null=True, blank=True)
	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True,
	                            blank=True)
	objects=CompenseChequeManager()

	class Meta:
		app_label = 'bankcheck'
		verbose_name="Compense Cheque"

		ordering = ['-pk']
		permissions = [
			("faire_compense", "Peut compenser cheque")
		]

	@classmethod
	def check_if_api_open(cls):
		obj=SettingsOP.object()
		if obj and obj.api_compense:
			return True
		else :return  False

	def is_valid(self):
		return self.chequier.is_valid() and not self.blocked and not self.use

	def can_delivered(self):
		return self.chequier.is_valid() and not self.blocked  and self.use and not self.delivred

	def can_acces(self,user):
		return  self.__class__._default_manager.filter(id=self.id).by_agent(user).exists()
	def __str__(self):
		# noinspection PyPep8
		return "{}".format(self.reference, )


class MiseEnOpposition(TimeStampedModel):
	cheque = models.OneToOneField(Cheque, related_name='miseop_cheque', on_delete=models.CASCADE, verbose_name="chèque")
	reference = models.CharField(_('Réference'), max_length=128, unique=True)
	amount = MoneyField(max_digits=20, decimal_places=2, default_currency='XOF', null=True, default=0,
	                    validators=[MinMoneyValidator(0)], verbose_name="Montant")

	acceptation_date = models.DateTimeField(_('Date acceptation'), max_length=12, null=True, blank=True)
	accepter = models.BooleanField("Est accepter ?", default=False)
	approbation_date = models.DateTimeField(_('Date approbation'), max_length=12, null=True, blank=True)
	approuver = models.BooleanField("Approuver ?", default=False)
	observations = models.TextField(_('observations'), default="RAS")

	demandeur = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Demandeur', related_name='+', on_delete=models.SET_NULL, null=True,
	                            blank=True)
	accepteur = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Accepteur',related_name='+', on_delete=models.SET_NULL, null=True,
	                            blank=True)

	approbateur = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Approbateur',related_name='+', on_delete=models.SET_NULL, null=True,
	                            blank=True)

	objects=MiseEnOppositionManager()

	class Meta:
		app_label = 'bankcheck'
		verbose_name = "Mise en Opposition Cheque"
		ordering = ['-pk']
		permissions = [
			("faire_miseenopposition", "Peut faire la mise en opposition cheque"),
			("accepter_miseenopposition", "Peut accepter la demande de mise en opposition cheque"),
			("approuver_miseenopposition", "Peut faire  l'approbation de la mise en opposition cheque")
		]
	def get_instance(self):
		return self

	def is_valid(self):
		return self.chequier.is_valid() and not self.blocked and not self.use

	def can_delivered(self):
		return self.chequier.is_valid() and not self.blocked and self.use and not self.delivred

	def can_acces(self, user):
		return self.__class__._default_manager.filter(id=self.id).by_agent(user).exists()

	def __str__(self):
		# noinspection PyPep8
		return "{}".format(self.reference, )


class AnnulationCheque(TimeStampedModel):
	cheque = models.OneToOneField(Cheque, related_name='annulation_cheque', on_delete=models.CASCADE, verbose_name="cheque")
	reference = models.CharField(_('Réference'), max_length=128, unique=True)
	amount = MoneyField(max_digits=20, decimal_places=2, default_currency='XOF', null=True, default=0,
	                    validators=[MinMoneyValidator(0)])

	acceptation_date = models.DateTimeField(_('Date acceptation'), max_length=12, null=True, blank=True)
	accepter = models.BooleanField("Est accepter ?", default=False)
	approbation_date = models.DateTimeField(_('Date approbation'), max_length=12, null=True, blank=True)
	approuver = models.BooleanField("Approuver ?", default=False)
	observations = models.TextField(_('observations'), default="RAS")

	demandeur = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Demandeur',related_name='+', on_delete=models.SET_NULL,
	                              null=True,
	                              blank=True)
	accepteur = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Accepteur',related_name='+', on_delete=models.SET_NULL,
	                              null=True,
	                              blank=True)

	approbateur = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Approbateur',related_name='+', on_delete=models.SET_NULL,
	                                null=True,
	                                blank=True)

	objects=AnnulationChequeManager()

	class Meta:
		app_label = 'bankcheck'
		verbose_name = "Annulation Cheque"

		ordering = ['-pk']
		permissions = [
			("accepter_annulationcheque", "Peut accepter la demande l'annulation cheque"),
			("approuver_annulationcheque", "Peut faire  l'approbation de l'annulation cheque")
		]

	def is_valid(self):
		return self.chequier.is_valid() and not self.blocked and not self.use

	def can_delivered(self):
		return self.chequier.is_valid() and not self.blocked and self.use and not self.delivred

	def can_acces(self, user):
		return self.__class__._default_manager.filter(id=self.id).by_agent(user).exists()

	def __str__(self):
		# noinspection PyPep8
		return "{}".format(self.reference, )

	def get_instance(self):
		return self



class RejetCheque(TimeStampedModel):
	cheque = models.OneToOneField(Cheque, related_name='rejet', on_delete=models.CASCADE, verbose_name="cheque")
	reference = models.CharField(_('Réference'), max_length=128, unique=True)
	op = models.CharField(_('Ref op'), max_length=128)
	amount = MoneyField(max_digits=20, decimal_places=2, default_currency='XOF', null=True, default=0,
	                    validators=[MinMoneyValidator(0)])

	acceptation_date = models.DateTimeField(_('Date acceptation'), max_length=12, null=True, blank=True)
	accepter = models.BooleanField("Est accepter ?", default=False)
	approbation_date = models.DateTimeField(_('Date approbation'), max_length=12, null=True, blank=True)
	approuver = models.BooleanField("Approuver ?", default=False)
	observations = models.TextField(_('observations'), default="RAS")

	demandeur = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Demandeur',related_name='+', on_delete=models.SET_NULL,
	                              null=True,
	                              blank=True)
	accepteur = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Accepteur',related_name='+', on_delete=models.SET_NULL,
	                              null=True,
	                              blank=True)

	approbateur = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Approbateur',related_name='+', on_delete=models.SET_NULL,
	                                null=True,
	                                blank=True)



	objects=RejetChequeManager()

	class Meta:
		app_label = 'bankcheck'
		verbose_name = "Rejet Cheque"

		ordering = ['-pk']
		permissions = [
			("accepter_rejetcheque", "Peut accepter la demande de rejet cheque"),
			("approuver_rejetcheque", "Peut faire  l'approbation de rejet cheque")
		]

	def is_valid(self):
		return self.chequier.is_valid() and not self.blocked and not self.use

	def can_delivered(self):
		return self.chequier.is_valid() and not self.blocked and self.use and not self.delivred

	def can_acces(self, user):
		return self.__class__._default_manager.filter(id=self.id).by_agent(user).exists()

	def __str__(self):
		# noinspection PyPep8
		return "{}".format(self.reference, )

	def get_instance(self):
		return self




class ChequeScanne(TimeStampedModel):
	cheque = models.ForeignKey(Cheque, related_name='chequescanne', on_delete=models.SET_NULL, verbose_name="chèque", null=True, blank=True)
	num_cheque = models.CharField(_('numéro chèque'), max_length=128)
	code_cheque = models.CharField(_('code chèque'), max_length=128)
	code_place = models.CharField(_('code place'), max_length=128)
	reference = models.CharField(_('Réference chéque'), max_length=128,unique=True)
	beneficiare = models.CharField(_('Bénéficiaire'), max_length=128,null=True, blank=True)
	agenceremittante = models.CharField(_('AGENCE REMETTANTE'), max_length=128, null=True, blank=True)
	adresse_benef = models.CharField(_('Adresse Bénéficiaire'), max_length=128, null=True, blank=True)
	banque = models.CharField(_('Banque tire'), max_length=128,null=True, blank=True)
	agence = models.CharField(_('Agence tire'), max_length=128, null=True, blank=True)
	rib = models.CharField(_('Clé Rib tire'), max_length=128, null=True, blank=True)
	compte = models.CharField(_('Numéro compte tire'), max_length=128,)
	typeop = models.CharField(_('Type op'), max_length=128, )

	poste = models.ForeignKey(PosteComptable, max_length=3 ,on_delete=models.SET_NULL, verbose_name="poste comptable",null=True, blank=True)
	agent_poste= models.ForeignKey(ProfilePC, related_name='comptable', on_delete=models.SET_NULL, verbose_name="comptable",null=True, blank=True)
	amount = MoneyField(max_digits=20, decimal_places=2, default_currency='XOF', null=True, default=0,validators=[MinMoneyValidator(0)], verbose_name="Montant")

	aster_date = models.DateTimeField(_('Date aster'), max_length=12, null=True, blank=True)
	date_compense = models.DateTimeField(_('Date compense'), max_length=12,null=True,blank=True)
	observations = models.TextField(_('observations'), default="RAS")

	traite = models.PositiveSmallIntegerField('Traite' )
	rejet = models.PositiveSmallIntegerField('Rejet')
	sens = models.CharField(_('Sens'), max_length=128)

	statut = models.CharField(_('Statut '), max_length=128, choices=STATUS_CHEQUE.CHOICES,
	                               default=STATUS_CHEQUE.INCONNU)

	compte_aster = models.CharField(_('Compte Aster'), max_length=128,null=True,blank=True)
	creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True,
	                            blank=True)
	objects=ChequeScanneManager()

	class Meta:
		app_label = 'bankcheck'
		verbose_name="Cheque Scanne"

		ordering = ['-pk']



	def send_visa_msg(self,):
		obj=SettingsOP.object()
		from  helpers.tasks import async_send_sms
		if obj and self.poste and self.statut!=STATUS_CHEQUE.VISE:
			try:
				if obj.visa_notif_pc:
					message = self.get_msg()
					#notif_by_sms(gerant.phone.as_e164, message)
					print("envois sssm credit")
					pcs = ProfilePC.objects.filter(poste=self.poste)
					for pc in pcs:
						async_send_sms(pc.phone.as_e164, message)
			except:
				import traceback
				traceback.print_exc()


	def get_msg(self):
		compte = "Bienvenue sur SIGCDD "
		statut="suspect"
		if self.statut==STATUS_CHEQUE.REJET:
			statut = "rejete"
		if self.statut==STATUS_CHEQUE.NON_VISE:
			statut = "non vise"
		if self.statut==STATUS_CHEQUE.MISE_EN_OPPOSITION:
			statut = "mise en opposition"
		if self.statut==STATUS_CHEQUE.VISE:
			statut = "vise"
		_date= "{:%d-%m-%Y %H:%M}".format(datetime.datetime.now())
		identifiant = "Votre cheque N {}  est {} . Date {} ".format(self.num_cheque,statut,_date)
		message = "{}. {}".format(compte, identifiant)
		return message


@receiver(post_save, sender=ChequeScanne)
def notify_postecomptabble(sender, **kwargs):
  instance = kwargs['instance']
  if kwargs.get('created', True):
	  try:
		  instance.send_visa_msg()
	  except SigException as e:
		  raise e


@receiver(post_save, sender=MiseEnOpposition)
def create_chequesuspect(sender, **kwargs):
	instance = kwargs['instance']
	cheque = instance.cheque
	from cddaccount.models.transaction import TransactionOP
	if kwargs.get('created', True):
		chequescanne = ChequeScanne()
		chequescanne.cheque=cheque
		trx = TransactionOP.objects.filter(cheque=cheque.reference).last()
		if trx:
			chequescanne.statut = STATUS_CHEQUE.VISE
			if hasattr(cheque, "rejet"):
				chequescanne.statut = STATUS_CHEQUE.REJET
			if hasattr(cheque, "miseop_cheque"):
				chequescanne.statut = STATUS_CHEQUE.MISE_EN_OPPOSITION
		else:
			chequescanne.statut = STATUS_CHEQUE.NON_VISE
			if hasattr(cheque, "rejet"):
				chequescanne.statut = STATUS_CHEQUE.REJET
			if hasattr(cheque, "miseop_cheque"):
				chequescanne.statut = STATUS_CHEQUE.MISE_EN_OPPOSITION

		chequescanne.reference = cheque.reference
		chequescanne.amount = cheque.amount
		chequescanne.compte_aster = cheque.chequier.compte.short_compte
		chequescanne.poste = cheque.chequier.compte.poste
		chequescanne.rejet=0
		chequescanne.traite=0
		chequescanne.sens="interne"
		chequescanne.save()


class ComptableMatiere(Person):
	poste = models.ForeignKey(PosteComptable, verbose_name=_('poste'), related_name="comptablematiere",on_delete=models.CASCADE)
	matricule = models.CharField(_("Matricule"), max_length=50)
	phone = PhoneNumberField(_("Téléphone"), null=False, blank=False)
	objects=ComptableMatiereManager()

	class Meta:
		app_label = 'bankcheck'
		verbose_name = _('Comptable Matière')
		verbose_name_plural = _('Comptable Matière')
	def __str__(self):
		return self.full_name()

	def actions(self):

		delete_url = reverse('bankcheck:delete_comptablematiere', kwargs={'pk': self.pk})
		update_url = reverse('bankcheck:update_comptablematiere', kwargs={'pk': self.pk})
		str = """
		        <button type="button" class="update-item btn btn-sm btn-warning " data-form-url="{}">
		          <span class="fa fa-pencil"></span>
		        </button>
		         <button type="button" class="delete-item btn btn-sm btn-danger" data-form-url="{}">
		          <span class="fa fa-trash"></span>
		        </button>
		        """.format(update_url,delete_url )
		return format_html(str)



class Imprimeur(TimeStampedModel):
	name = models.CharField(_('Non'), max_length=128)
	phone = models.CharField(_('Téléphone'), max_length=20)
	fax = models.CharField(_('Fax'), max_length=20, null=True, blank=True)
	email = models.CharField(_('Email'), max_length=128, null=True, blank=True)
	street = models.CharField(_('Adresse'), max_length=128, null=True, blank=True)

	others = models.CharField(_('Autres'), max_length=20, null=True, blank=True)
	class Meta:
		app_label = 'bankcheck'
		verbose_name = _('Imprimeur')
		verbose_name_plural = _('Imprimeur')



	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.name,)


class Bordereau(TimeStampedModel):
	imprimeur = models.ForeignKey(Imprimeur, verbose_name=_('imprimeur'), related_name="+",
	                          on_delete=models.CASCADE)
	reference = models.CharField(_('Reference'), max_length=128)
	chequiers = models.ManyToManyField(Chequier, verbose_name=_('chequiers'), null=True, blank=True,related_name="+")

	class Meta:
		app_label = 'bankcheck'
		verbose_name = _('Bordereau')
		verbose_name_plural = _('Bordereaus')

	def __str__(self):
		# noinspection PyPep8
		return u"%s" % (self.reference,)

	def format_reference(self):
		return "{}/{}".format(self.reference[:4],self.reference[4:])

	def save(self, *args, **kwargs):
		#self.pk = self.id = 1
		if not self.reference:
			try:
				prefix= "{}".format(date.today().strftime('%Y'))
				self.reference = CommonHelper.Instance().generate_code("bankcheck", "bordereau", "reference", size=6,prefix=prefix,chars="012345789")
			except:
				error = ValueError("A possible infinite loop was detected")
				raise error
		return super().save(*args, **kwargs)