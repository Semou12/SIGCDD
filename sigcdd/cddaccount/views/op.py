import datetime
import traceback

from bootstrap_modal_forms.utils import is_ajax
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db import transaction
from django.db.transaction import atomic
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_tables2 import RequestConfig



from cddaccount import TYPE_RECEPTIONNAIRE, SENS_TRX, TYPE_VIREMENT, STATUS_PROVIDER
from cddaccount.models import GestionCompteDepot, \
    TransactionOP, ReservationFond, CompteDepot, OrdrePayment, PrisEnchageOrdrePayment, VisaOrdrePayment, \
    ETAPE_ORDRE_PAYMENT, TYPE_REGLEMENT, STATUS_ORDRE_PAYMENT, get_or_create_journee_comptable, PAYMENT_MEAN_TYPE, \
    BlocageFond, AnneeComptable, reject_pec_op, VirementDetails, \
    generate_rib, \
    VirementMasse, SettingsVRM, debit_account_balance_from_rsv, rejete_priseencharge_op, Mandataire, Nature, GerantCD, \
    create_basculement, DemandeOP, TypeCompteTrx, can_debit_account_for_op
from cddaccount.process import CddProcessManager
from core.models import ConfigurationOTP
from helpers.models import Role, SimpleOtp, TypeNotif
from django.conf import settings
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa

# import generic UpdateView
import logging

logger = logging.getLogger(__name__)
from cddaccount.forms import PrisEnchageOrdrePaymentModalForm, DefaultSaisieOrdrePaymentModelForm, MakeTrxPaymentForm, \
    AcceptationOrdrePayementForm, OtpValidationOrdrePaymentForm, VisaOrdrePaymentModelForm, \
    UpdateOrdrePaymentModelForm, JourneeComptableForm, SimpleOPForm, VirementMasseForm, MakeTrxPaymentVRMForm, \
    SaisieOPWithCddAccountForm, \
    UpdateOPWithCddAccountForm, SaisieOPWithPCForm, PaymentByBFModelForm, AnnuleVisaForm, \
    AcceptationPourPriseEnChargeForm, UpdateOrdrePaymentPaymentModelForm, TYPE_RELEVE, \
    TakeChequeVerifyPaymentForm, BordereauOPForm, BENEF_CHOICES, CancelOPForm, OtpForm, UpdateOPWithPCForm, \
    BulkTakeChequeVerifyPaymentForm, CreateOPfromDemandeForm

from cddaccount.tables import TransactionOPTable, OrdrePaymentTable

# Relative import of GeeksModel
from bootstrap_modal_forms.generic import (
    BSModalUpdateView,
    BSModalCreateView, BSModalDeleteView
)

from helpers.exceptions import SigException
from helpers.commons import notify_badge
from bankcheck.models import Cheque
from django.db.models import Sum, IntegerField
from django.contrib import messages

from django.db.models.functions import Coalesce
from django.contrib.staticfiles import finders

import xlrd
from xlutils.copy import copy
import os
from django.http import HttpResponse
from cddaccount.signals import op_status_changed
from cddaccount.views import PAGINATION_SIZE,default_currency
import pandas as pd
from tablib import Dataset


def get_comptes(request):
    try:
        key = request.session["select_cddacc_user_id"]
        return CompteDepot.objects.filter(id=int(key))
    except KeyError:
        return CompteDepot.objects.by_agent(request.user)


def get_cdd_with_gerant(request):
    try:
        key = request.session["select_cddacc_user_id"]
        return CompteDepot.objects.filter(id=int(key))
    except KeyError:
        ids = GestionCompteDepot.objects.by_agent(request.user).filter(actif=True).values_list("compte_id", flat=True)
        return CompteDepot.objects.by_agent(request.user).filter(id__in=ids)


# @method_decorator([ user_role_required(Role.AGENT_PC)], name='dispatch')
class OrdrePaymentDeleteView(PermissionRequiredMixin, BSModalDeleteView):
    # specify the model you want to use
    model = OrdrePayment

    permission_required = ('cddaccount.delete_{}'.format(model._meta.model_name),)

    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_message = "Success: Supression de l'ordre de paiement"
    success_url = reverse_lazy('cddaccount:ordrepayment_list')

    template_name = "core/confirm_delete_entity.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Supression de l'ordre de paiement : {}".format(self.object.reference, )
        return context


@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
@permission_required("cddaccount.priseencharge_ordrepayment")
def prise_en_charge_view(request, pk):
    template = "cddaccount/prise_en_charge.html"
    user = request.user
    ordre_payment = get_object_or_404(OrdrePayment, pk=pk)
    delete_notification(ordre_payment, user)
    if not ordre_payment.can_acces(user):
        raise Http404

    url_fichier_vm = None
    if hasattr(ordre_payment, "virementmasse"):
        url_fichier_vm = ordre_payment.virementmasse.details_file

    gerant = None
    if ordre_payment.gerant:
        gerant = ordre_payment.gerant.gerant_cd
    success_url = reverse_lazy('cddaccount:ordrepayment_list')

    success_url = ordre_payment.get_absolute_url()
    if hasattr(ordre_payment, "annulation_op"):
        messages.info(request, "Ordre de paiement déjà annulé")
        return redirect(success_url)
    if not ordre_payment.can_acces(user):
        raise Http404
    if hasattr(ordre_payment, "prise_en_charge"):
        messages.info(request, "Prise en charge déjà fait pour cet ordre de payment")
        return redirect(success_url)

    creator = ordre_payment.creator
    if hasattr(creator, "agent_postecomptable"):
        status_choises = [
            ("ACCEPTE", "ACCEPTE"),
            ("ANNULE", "ANNULER RECEPTION"),
        ]

    else:
        status_choises =  [
        ("ACCEPTE", "ACCEPTE"),
        ("REJETE", "REJETE"),
        ("ANNULE", "ANNULER RECEPTION"),
       ]


    if request.method == 'POST':
        form = AcceptationPourPriseEnChargeForm(
            request.POST)  # PriseEnChargeOrdrePaymentModelForm(request.POST, request.FILES,instance=ordre_payment)
        form.fields["status"].choices = status_choises
        if form.is_valid():
            if request and not is_ajax(request.META):
                status = form.cleaned_data["status"]
                observations = form.cleaned_data["description"]
                if status == STATUS_ORDRE_PAYMENT.ACCEPTE:
                    prise_encharge = PrisEnchageOrdrePayment()
                    prise_encharge.ordre = ordre_payment
                    prise_encharge.amount = ordre_payment.amount
                    prise_encharge.payment_mean = ordre_payment.payment_mean
                    prise_encharge.reglement = ordre_payment.reglement
                    prise_encharge.creator = user
                    prise_encharge.save()
                    ordre_payment.date_prise_en_charge = datetime.datetime.now()
                    ordre_payment.previous_etape = ordre_payment.etape
                    ordre_payment.etape = ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE
                    ordre_payment.observations = observations
                    ordre_payment.save()
                    messages.success(request, "Prise en charge effective")
                    call_notify_badge(ordre_payment)
                elif status == STATUS_ORDRE_PAYMENT.REJETE:
                    messages.error(request, observations, extra_tags="danger")
                    # cancel_op(ordre_payment,user, observations)
                    try:
                        rejete_priseencharge_op(ordre_payment, user, observations)
                        messages.success(request, "Rejet de l'op {} vers le gerant effective".format(ordre_payment.sig_reference,))
                    except SigException as e:
                        messages.error(request, e.message, extra_tags="danger")
                else:
                    ordre_payment.etape = ETAPE_ORDRE_PAYMENT.VALIDE
                    ordre_payment.previous_etape = ETAPE_ORDRE_PAYMENT.SAISIE
                    ordre_payment.observations = observations
                    ordre_payment.save()

            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")
    else:
        form = AcceptationPourPriseEnChargeForm()  # PriseEnChargeOrdrePaymentModelForm(instance=ordre_payment)
        form.fields["status"].choices = status_choises

    context = {"url_fichier_vm": url_fichier_vm, "agent": gerant, "form": form,
               'title': "Prise en charge ordre de paiement {}".format(ordre_payment.sig_reference, ),
               "object": ordre_payment, "compte": ordre_payment.compte}
    return render(request, template, context)

from django.core.exceptions import ValidationError
@login_required
@transaction.atomic()
@permission_required("cddaccount.valider_ordrepayment")
def validate_ordre_payment_view(request, reference):
    template = "cddaccount/validate_ordrepayment.html"
    user = request.user
    # success_url = reverse_lazy('cddaccount:ordrepayment_list')
    object = get_object_or_404(OrdrePayment, reference=reference)
    use_otp = True
    otp_config = ConfigurationOTP.object()
    if otp_config:
        use_otp = otp_config.validation_op
    title = "Valider OP {}".format(object.reference, )
    delete_notification(object, user)
    success_url = object.get_absolute_url()
    if not object.can_acces(user):
        raise Http404
    if hasattr(object, "annulation_op"):
        messages.info(request, "Ordre de paiement déjà annulé")
        return redirect(success_url)
    try:
        can_debit_account_for_op(object)
    except SigException as e:
        messages.error(request, e.message, extra_tags="danger")
        raise Http404(e.message)
        #return redirect(success_url)

    if request.method == 'POST':
        if use_otp:
            form = OtpValidationOrdrePaymentForm(request.POST)
        else:
            form = SimpleOPForm(request.POST)
        if form.is_valid():
            if request and not is_ajax(request.META):
                if use_otp:
                    otp = form.cleaned_data["otp"]
                    c = object.verify(otp)
                else:
                    c = True

                if c:
                    object.previous_etape = object.etape
                    object.etape = ETAPE_ORDRE_PAYMENT.VALIDE
                    object.gerant = user
                    if object.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and object.receptionnaire:
                        if object.receptionnaire == TYPE_RECEPTIONNAIRE.GERANT:
                            object.cin_receptionnaire = user.nin
                            object.phone_receptionnaire = user.phone
                        elif object.receptionnaire == TYPE_RECEPTIONNAIRE.MANDATAIRE and object.depositaire:
                            object.cin_receptionnaire = object.receptionnaire.nin
                            object.phone_receptionnaire = object.receptionnaire.phone

                        else:
                            if object.depositaire:
                                object.cin_receptionnaire = object.depositaire.nin
                                object.phone_receptionnaire = object.depositaire.phone

                    object.save()
                    # creationde de reservation
                    reservation = ReservationFond()
                    reservation.ordre = object
                    reservation.amount = object.amount
                    reservation.reliquat = object.amount
                    reservation.creator = user

                    if object.payment_mean : reservation.payment_mean = object.payment_mean

                    reservation.save()
                    debit_account_balance_from_rsv(reservation)
                    print("validation validation rsw")
                    call_notify_badge(object)
                    messages.success(request, "Ordre de paiement validé")
                else:
                    messages.error(request, "Token invalide", extra_tags="danger")

            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")
    else:
        if use_otp:
            title = "Valider par otp ordre  {}".format(object.reference, )
            object.generate_otp_and_save()
            object.send_ordrepayment_otp(user.gerant_cd.phone.as_e164)
            form = OtpValidationOrdrePaymentForm()
        else:
            form = SimpleOPForm()

    context = {"form": form, 'title': title}
    return render(request, template, context)



@login_required
@transaction.atomic()
@permission_required("cddaccount.accepter_ordrepayment")
def accepter_ordre_payment_view(request, reference):
    template = "cddaccount/accepter_ordrepayment.html"
    user = request.user
    success_url = reverse_lazy('cddaccount:ordrepayment_list')
    object = get_object_or_404(OrdrePayment, reference=reference)
    delete_notification(object, user)
    success_url = object.get_absolute_url()
    if not object.can_acces(user):
        raise Http404
    if hasattr(object, "annulation_op"):
        messages.info(request, "Ordre de paiement déjà annulé")
        return redirect(success_url)
    gerant = None
    if object.gerant:
        gerant = object.gerant.gerant_cd

    creator = object.creator
    if  hasattr(creator, "agent_postecomptable"):
        status_choises = [("ACCEPTE", "ACCEPTE")]

    else :
        status_choises = STATUS_ORDRE_PAYMENT.CHOICES_1

    if request.method == 'POST':
        form = AcceptationOrdrePayementForm(request.POST)
        form.fields["status"].choices = status_choises
        if form.is_valid():
            if request and not is_ajax(request.META):
                status = form.cleaned_data["status"]
                object.previous_etape = object.etape
                object.etape = status
                object.status = status
                object.observations = form.cleaned_data["description"]
                object.recepteur = user
                object.date_reception = datetime.datetime.now()
                object.save()
                if status == STATUS_ORDRE_PAYMENT.ACCEPTE:
                    #op_status_changed.send(sender=type(object), instance=object)
                    messages.success(request, "Ordre de paiement {}".format(status.lower()))
                    call_notify_badge(object)

                # mantis 0000041: Rendre obligatoire le motif de rejet


                elif status == STATUS_ORDRE_PAYMENT.REJETE:

                    try:
                        rejete_priseencharge_op(object, user, object.observations)
                        messages.success(request, "Rejet de l'op {} vers le gerant effective".format(object.sig_reference,))
                    except SigException as e:
                        messages.error(request, e.message, extra_tags="danger")


            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")
    else:

        form = AcceptationOrdrePayementForm()
        form.fields["status"].choices = status_choises

    context = {"form": form, 'title': "Accepter le dossier de l'ordre de paiement {}".format(object.sig_reference, ),
               "object": object, "compte": object.compte, "agent": gerant, }
    return render(request, template, context)


@login_required
def edit_bordereau_op(request):
    if not hasattr(request.user, "gerant_cd"):
        raise Http404

    read_bordereau_url = None
    can_read_bordereau = request.user.has_perm('cddaccount.bordereau_op')
    if can_read_bordereau:
        read_bordereau_url = reverse_lazy('cddaccount:bordereau_op')

    if request.method == 'POST':
        form = BordereauOPForm(request.POST)
        if form.is_valid():
            period = form.cleaned_data['period']
            today = datetime.date.today()
            title = f"BORDEREAU DES ORDRES DE VIREMENT DU "
            list_op = OrdrePayment.objects.by_agent(request.user).filter(created__date=period)

            context = {
                'list_op': list_op,
                'form': form,
                'title2': title,
                'date_du_jour': today,
                'period': period, "url_rb": read_bordereau_url, "can_read_bordereau": can_read_bordereau,
            }
            return render(request, 'cddaccount/gerant_bordereau_payment.html', context)
    else:
        form = BordereauOPForm()

    return render(request, "cddaccount/gerant_bordereau_edit.html", {'form': form})


@login_required
def all_bord_gerant_view(request):
    if not hasattr(request.user, "gerant_cd"):
        raise Http404
    read_bordereau_url = None
    can_read_bordereau = request.user.has_perm('cddaccount.bordereau_op')
    if can_read_bordereau:
        read_bordereau_url = reverse_lazy('cddaccount:bordereau_op')
    list_op = OrdrePayment.objects.by_agent(request.user)
    context = {"list_op": list_op, "url_rb": read_bordereau_url, "can_read_bordereau": can_read_bordereau, }
    template = "cddaccount/gerant_bordereau_payment.html"
    return render(request, template, context)


def viser_ordre_payement_view(request, reference):
    return default_viser_ordre_payement_view(request, reference, "default")


def modal_viser_ordre_payement_view(request, reference):
    return default_viser_ordre_payement_view(request, reference, "modal")


@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
@permission_required("cddaccount.viser_ordrepayment")
def default_viser_ordre_payement_view(request, reference, type):
    template = "cddaccount/visa.html"
    if type == "modal":
        template = "cddaccount/modal_visa.html"

    user = request.user
    ordre_payment = get_object_or_404(OrdrePayment, reference=reference)
    if not ordre_payment.can_acces(user):
        raise Http404
    gerant = None
    if ordre_payment.gerant:
        gerant = ordre_payment.gerant.gerant_cd
    success_url = reverse_lazy('cddaccount:ordrepayment_list')
    success_url = ordre_payment.get_absolute_url()

    if hasattr(ordre_payment, "annulation_op"):
        messages.info(request, "Ordre de paiement déjà annulé")
        return redirect(success_url)
    if not ordre_payment.can_acces(user):
        raise Http404
    if not ordre_payment.can_make_visa():
        messages.error(request, "Visa non disponible", extra_tags="danger")
        return redirect(success_url)

    if hasattr(ordre_payment, "prise_en_charge"):
        if hasattr(ordre_payment.prise_en_charge, "visa"):
            messages.info(request, "Visa déjà fait pour cet ordre de payment")
            return redirect(success_url)
    else:
        messages.info(request, "Ordre de paiement non encore prise en charge")
        return redirect(success_url)

    if request.method == 'POST':
        form = VisaOrdrePaymentModelForm(request.POST, request.FILES, instance=ordre_payment)
        if form.is_valid():
            if request and not is_ajax(request.META):
                visa = VisaOrdrePayment()

                visa.prise_en_charge = ordre_payment.prise_en_charge
                visa.amount = ordre_payment.prise_en_charge.amount
                visa.payment_mean = ordre_payment.prise_en_charge.payment_mean
                visa.reglement = ordre_payment.prise_en_charge.reglement
                visa.creator = user
                visa.observations = form.cleaned_data["observations"]
                visa.save()
                ordre_payment.date_visa = datetime.datetime.now()
                ordre_payment.etape = ETAPE_ORDRE_PAYMENT.VISA
                ordre_payment.observations = form.cleaned_data["observations"]
                ordre_payment.save()
                messages.success(request, "Visa effective")

            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")
    else:
        form = VisaOrdrePaymentModelForm(instance=ordre_payment)

    context = {"agent": gerant, "form": form, 'title': "Visa ordre de paiement {}".format(ordre_payment.reference, ),
               "object": ordre_payment, "compte": ordre_payment.compte}
    return render(request, template, context)


@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def detail_ordre_payement_view(request, reference):
    template = "cddaccount/details_op.html"
    user = request.user
    ordre_payment = get_object_or_404(OrdrePayment, reference=reference)
    if not ordre_payment.can_acces(user):
        raise Http404
    trx = TransactionOP.objects.filter(reservation__ordre_id=ordre_payment.id)
    table = TransactionOPTable(trx, request=request)
    ordre_obs = ordre_payment.ordre_obs.all()
    RequestConfig(request, paginate={"per_page": PAGINATION_SIZE}).configure(table)
    create_url = None
    visa_url = None
    gerant = None
    reliquat = 0
    can_make_payment = user.has_perm("cddaccount.maketrx_ordrepayment") and ordre_payment.can_make_trx()
    if can_make_payment:
        create_url = reverse_lazy('cddaccount:maketrx_ordre_payement', kwargs={"reference": reference})
        reliquat = ordre_payment.reservationfond.get_reliquat()

    can_make_visa = user.has_perm("cddaccount.viser_ordrepayment") and ordre_payment.can_make_visa()
    if can_make_visa:
        visa_url = reverse_lazy('cddaccount:modal_viser_ordre_payement', kwargs={"reference": reference})
    if ordre_payment.gerant:
        gerant = ordre_payment.gerant.gerant_cd
    else:
        try:
            a = GestionCompteDepot.objects.get(compte_id=ordre_payment.compte_id, actif=True)
            gerant = a.gerant
        except GestionCompteDepot.DoesNotExist:
            pass

    context = {"ordre_obs": ordre_obs, "reliquat": reliquat, "visa_url": visa_url, "can_make_visa": can_make_visa,
               "table": table, "can_make_payment": can_make_payment, "create_url": create_url, "agent": gerant,
               'title': "DÉTAILS ORDRE DE PAIEMENT  N° {}".format(ordre_payment.sig_reference, ),
               "object": ordre_payment, "compte": ordre_payment.compte}

    return render(request, template, context)


@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def recu_payement_view(request, reference):
    template = "cddaccount/trx_op_new.html"
    user = request.user
    trx = get_object_or_404(TransactionOP, reference=reference)
    object_depense = "Objet de la dépense : {}".format(
        trx.libelle)

    quarter = pd.Timestamp(trx.created.date()).quarter

    if trx.reglement == TYPE_REGLEMENT.ACOMPTE:
        template = "cddaccount/trx_op_new.html"
        object_depense = "Objet de la dépense : {}° accompte sur  {}".format(
            trx.get_number(), trx.origin_reference)

    journee_comptable = trx.jour_comptable.day()
    gestion = trx.jour_comptable.year()
    ordre = trx.reservation.ordre
    if not ordre.can_acces(user):
        raise Http404
    create_url = None
    gerant = None

    compte = ordre.compte
    numero = 1

    accomptes = TransactionOP.objects.filter(origin_reference=trx.origin_reference).exclude(id=trx.id)
    accomptes = accomptes.filter(created__lt=trx.created)
    rowspan = accomptes.count() + 2

    total_accompte = accomptes.aggregate(amount=Sum('amount', output_field=IntegerField()))
    total_accompte = total_accompte["amount"]

    netapayer = int(trx.amount.amount)

    if trx.reservation.ordre.gerant:
        gerant = ordre.gerant.gerant_cd
    if trx.account_secondaire:iban = trx.account_secondaire
    else : iban=ordre.iban

    context = {"quarter": quarter, "object_depense": object_depense, "netapayer": netapayer,
               "total_accompte": total_accompte, "rowspan": rowspan, "accomptes": accomptes, "gestion": gestion,
               "journee_comptable": journee_comptable, "compte": compte, "ordre": ordre, "agent": gerant,
               'title': "Recu  N° {}".format(trx.reference, ), "obj": trx,"iban":iban}
    return render(request, template, context)


from urllib.parse import urlparse, parse_qs
from djmoney.money import Money






@login_required
@transaction.atomic
@permission_required("cddaccount.create_ordrebydemande")
def create_ordre_from_demandeop_view(request, reference):
    template = "cddaccount/create_op_from_demande.html"
    user = request.user
    logger.info(" Creation  op : {} par {} ".format(reference, user.username))
    demandeop = get_object_or_404(DemandeOP, reference=reference)

    if not demandeop.can_acces(user):
        raise Http404
    parse_result = urlparse(request.build_absolute_uri())
    dict_result = parse_qs(parse_result.query)
    success_url = dict_result['success_url'][0]



    if hasattr(demandeop, "sig_refference"):
        messages.info(request, "Ordre de paiement déjà crée")
        return redirect(success_url)




    if request.method == 'POST':
        form = CreateOPfromDemandeForm(request.POST)


        if form.is_valid():
            if request and not is_ajax(request.META):
                if demandeop.gestion.bloque:
                    messages.error(request,
                                   "L année de gestion {} est fermée au paiment".format(demandeop.gestion.name),
                                   extra_tags="danger")
                    return redirect(success_url)


                try:

                    with transaction.atomic():
                        trx = OrdrePayment()
                        trx.amount =demandeop.amount
                        trx.compte = demandeop.compte
                        trx.poste_comptable = demandeop.compte.poste.reference
                        trx.payment_mean=PAYMENT_MEAN_TYPE.RETRAIT
                        trx.creator=user
                        trx.open_dateo = datetime.datetime.today()
                        trx.agent = user
                        trx.jour_comptable = user.journee_comptables.filter(actif=True).last()
                        trx.object = demandeop.object
                        trx.sens = SENS_TRX.DEBIT

                        trx.reglement = TYPE_REGLEMENT.GLOBAL
                        trx.beneficiaire = demandeop.beneficiaire
                        trx.gestion=demandeop.gestion

                        trx.typecompte=demandeop.typecompte
                        trx.save()


                        # notification
                        messages.success(request, "Paiement effectué")
                except SigException as e:
                    traceback.print_exc()
                    messages.error(request, e.message, extra_tags="danger")
            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")
    else:
        form = CreateOPfromDemandeForm(initial=initial)


    context = { "form": form,
               'title': "Ordre de paiement {}".format(object.sig_reference, ), "object": object,
               "compte": object.compte, }

    return render(request, template, context)



@login_required
@transaction.atomic
@permission_required("cddaccount.maketrx_ordrepayment")
def maketrx_ordre_payement_view(request, reference):
    template = "cddaccount/make_trx_op.html"
    user = request.user
    logger.info(" Paiement ov : {} par {} ".format(reference, user.username))
    object = get_object_or_404(OrdrePayment, reference=reference)
    delete_notification(object, user)
    if not object.can_acces(user):
        raise Http404
    # success_url = reverse_lazy('cddaccount:ordrepayment_list')

    success_url = object.get_absolute_url()
    parse_result = urlparse(request.build_absolute_uri())
    dict_result = parse_qs(parse_result.query)
    success_url = dict_result['success_url'][0]



    if hasattr(object, "annulation_op"):
        messages.info(request, "Ordre de paiement déjà annulé")
        return redirect(success_url)
    initial = None
    min = 0
    iban = object.iban
    rsv = object.reservationfond
    max = int(rsv.amount.amount)
    url_fichier_vm = None

    if hasattr(object, "virementmasse"):
        url_fichier_vm = object.virementmasse.details_file

    if object.prise_en_charge.reglement == TYPE_REGLEMENT.GLOBAL:
        min = max
    else:
        max = rsv.get_reliquat()
    max = rsv.get_reliquat()
    min = 0

    initial = {"amount": max, "max_amount": max}
    if iban: initial.update({"iban": iban})

    gerant = None
    envoie_cheque_aster = False
    if object.gerant:
        gerant = object.gerant.gerant_cd
    payment_mean_choices =object.get_authorized_payment_modes()

    if rsv.reglement:
        reglement_choices = [(rsv.reglement, rsv.reglement)]
    out_umeoa=object.transfer_out_umeoa

    if request.method == 'POST':
        if hasattr(object, "virementmasse"):
            form = MakeTrxPaymentVRMForm(request.POST)
        else:
            form = MakeTrxPaymentForm(request.POST)

        if form.is_valid():
            if request and not is_ajax(request.META):
                if object.gestion.bloque:
                    messages.error(request,
                                   "L année de gestion {} est fermée au paiment".format(object.gestion.name),
                                   extra_tags="danger")
                    return redirect(success_url)
                amount = form.cleaned_data["amount"]
                if hasattr(object, "virementmasse"):
                    reglement = TYPE_REGLEMENT.GLOBAL
                else:
                    # reglement = form.cleaned_data["reglement"]
                    iban = form.cleaned_data["iban"]
                    if amount != max:
                        reglement = TYPE_REGLEMENT.ACOMPTE
                    else:
                        reglement = TYPE_REGLEMENT.GLOBAL

                    if not object.transfer_out_umeoa:
                        if iban and len(iban) > 0:
                            iban = iban.replace(" ", "")
                            iban = iban.replace("_", "")
                            country_code = iban[:2]
                            rib = iban[-2:]
                            cal_rib = generate_rib(country_code, iban)
                            if rib != cal_rib:
                                messages.error(request, "Compte bancaire non conforme".format(max, ),
                                               extra_tags="danger")
                                return redirect(success_url)


                payment_mean = form.cleaned_data["payment_mean"]
                if object.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT:
                    if not out_umeoa and payment_mean not in [PAYMENT_MEAN_TYPE.VIREMENT,PAYMENT_MEAN_TYPE.OPERATION_ORDRE]:
                        messages.error(request, "Mode de paiement non authorisé ".format(max, ), extra_tags="danger")
                        return redirect(success_url)

                if object.payment_mean == PAYMENT_MEAN_TYPE.MOBILE and payment_mean != object.payment_mean:
                    messages.error(request, "Mode de paiement non authorisé ".format(max, ), extra_tags="danger")
                    return redirect(success_url)

                try:
                    if reglement == TYPE_REGLEMENT.GLOBAL and amount != max:
                        messages.error(request,
                                       "Le montant saisi doit etre égal a {}  pour reglement global".format(max, ),
                                       extra_tags="danger")
                        return redirect(success_url)

                    object.reservationfond.can_make_trx_with_amount(amount)
                    if object.cheque and payment_mean in [PAYMENT_MEAN_TYPE.NUMERAIRE, PAYMENT_MEAN_TYPE.CHEQUE,
                                                          PAYMENT_MEAN_TYPE.OPERATION_ORDRE] and reglement == TYPE_REGLEMENT.GLOBAL:
                        cheque = Cheque.objects.get(reference=object.cheque)
                        cheque.is_usable()
                        envoie_cheque_aster = True

                    jour_comptable = user.journee_comptables.filter(actif=True).last()
                    if jour_comptable is not None and object.gestion is not None and jour_comptable.annee_comptable.id != object.gestion.id:
                        messages.error(request,
                                       "L année de gestion actuelle {} est différente de celle de ordre{}".format(
                                           jour_comptable.annee_comptable.year(), object.gestion.year()),
                                       extra_tags="danger")
                        return redirect(success_url)


                    with transaction.atomic():

                        if object.payment_mean==PAYMENT_MEAN_TYPE.MOBILE:

                            if hasattr(object, "virementmasse"):
                                object.jour_comptable = jour_comptable
                                if object.status_provider == STATUS_PROVIDER.INIT:
                                    CddProcessManager.send_mobile_virement_trx_provider(user, object)
                                    
                                    object.jour_comptable = jour_comptable
                                    trx = TransactionOP()
                                    trx.reservation = object.reservationfond
                                    trx.amount = Money(int(amount), 'XOF')
                                    trx.account_depot = object.compte.short_compte
                                    trx.poste_comptable = object.compte.poste.reference
                                    trx.rib_cdd = object.compte.compte
                                    trx.sig_reference = object.sig_reference
                                    trx.origin_reference = object.sig_reference
                                    trx.account_secondaire = "-"
                                    trx.cheque = object.cheque
                                    trx.agent = user
                                    trx.jour_comptable = jour_comptable
                                    trx.date_rlv=jour_comptable.jour
                                    trx.libelle = object.object
                                    trx.sens = SENS_TRX.DEBIT
                                    trx.payment_mean = payment_mean
                                    trx.reglement = reglement
                                    trx.beneficiaire = object.beneficiaire
                                    trx.nature_depense = object.nature.name
                                    trx.typecompte=object.typecompte
                                    trx.save()
                                    CddProcessManager.send_virement_trx_aster(user, trx)
                                    object.status_provider = STATUS_PROVIDER.DELIVRE
                                    
                                    object.save()
                                    messages.success(request, "Paiement mobbile en cours de validation")
                                else:
                                    messages.error(request,
                                                   "Transaction en cours de traitement cher epaiement",
                                                   extra_tags="danger")
                                    return redirect(success_url)
                            else:
                                messages.error(request,
                                               "Seulement les virement de masse est concerné" ,
                                               extra_tags="danger")
                                return redirect(success_url)

                        else:
                            object.jour_comptable = jour_comptable
                            trx = TransactionOP()
                            trx.reservation = object.reservationfond
                            trx.amount = Money(int(amount), 'XOF')
                            trx.account_depot = object.compte.short_compte
                            trx.poste_comptable = object.compte.poste.reference
                            trx.rib_cdd = object.compte.compte
                            trx.sig_reference = object.sig_reference
                            trx.origin_reference = object.sig_reference
                            if iban:
                                trx.account_secondaire = iban
                            else:
                                trx.account_secondaire = "-"
                            trx.cheque = object.cheque
                            trx.agent = user
                            trx.jour_comptable = jour_comptable
                            trx.date_rlv=jour_comptable.jour
                            trx.libelle = object.object
                            trx.sens = SENS_TRX.DEBIT
                            trx.payment_mean = payment_mean
                            trx.reglement = reglement
                            trx.beneficiaire = object.beneficiaire
                            trx.nature_depense = object.nature.name
                            trx.typecompte=object.typecompte
                            trx.save()
                            if envoie_cheque_aster:
                                CddProcessManager.send_cheque_trx_aster(user, trx)
                            else:
                                CddProcessManager.send_virement_trx_aster(user, trx)
                            object.status_provider = STATUS_PROVIDER.DELIVRE

                            object.save()
                            # update balance
                            from cddaccount.models import compute_all_balances_for_compte
                            compute_all_balances_for_compte(object.compte,gestion=jour_comptable.annee_comptable_id)
                            # notification
                            messages.success(request, "Paiement effectué")
                except SigException as e:
                    traceback.print_exc()
                    messages.error(request, e.message, extra_tags="danger")
            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")
    else:

        if hasattr(object, "virementmasse"):
            form = MakeTrxPaymentVRMForm(initial=initial)

        else:
            form = MakeTrxPaymentForm(initial=initial)
            form.fields['amount'].widget.attrs.update({'min': min, 'max': max})
        # form.fields['reglement'].choices = reglement_choices

        form.fields['payment_mean'].choices = payment_mean_choices
        form.fields['amount'].max_value = int(object.prise_en_charge.amount.amount)
        if object.payment_mean  in [PAYMENT_MEAN_TYPE.RETRAIT, PAYMENT_MEAN_TYPE.NUMERAIRE]:
            form.fields['payment_mean'].initial = PAYMENT_MEAN_TYPE.NUMERAIRE
        else : form.fields['payment_mean'].initial = object.payment_mean

    context = {"url_fichier_vm": url_fichier_vm, "form": form,"out_umeoa":out_umeoa.real,
               'title': "Ordre de paiement {}".format(object.sig_reference, ), "object": object,
               "compte": object.compte, "agent": gerant, }

    return render(request, template, context)


@transaction.atomic()
def mark_cheque_as_use_for_op(ordrepayment):
    try:
        cheque = Cheque.objects.get(reference=ordrepayment.cheque)
        if not cheque.can_use_in_op():
            raise SigException('Réference chèque invalide : {}'.format(cheque, ))
        cheque.use = True
        cheque.amount = ordrepayment.amount
        cheque.cin_receptionnaire = ordrepayment.cin_receptionnaire
        if ordrepayment.phone_receptionnaire:
            cheque.phone_receptionnaire = ordrepayment.phone_receptionnaire.as_e164
        cheque.trx = ordrepayment.reference
        cheque.use_date = datetime.datetime.now()
        if ordrepayment.receptionnaire and ordrepayment.depositaire:
            cheque.endosser_par = ordrepayment.depositaire.full_name()
            cheque.phone_receptionnaire = ordrepayment.depositaire.phone.as_e164
            cheque.cin_receptionnaire = ordrepayment.depositaire.nin
        else:
            cheque.endosser_par = ordrepayment.beneficiaire
        cheque.save()
        chequier=cheque.chequier
        chequier.is_use=True
        chequier.save()
    except SigException as e:
        raise e

    except Cheque.DoesNotExist:
        raise SigException(message='Réference chèque introuvable : {}'.format(ordrepayment.cheque, ))
    except:
        traceback.print_exc()
        raise SigException('Réference chèque introuvable')


from django.urls import register_converter


class DateConverter:
    regex = '[0-9]{4}'
    regex = r'[0-9]{2}-[0-9]{2}-[0-9]{4}'
    format = '%d-%m-%Y'

    def to_python(self, value):
        return datetime.datetime.strptime(value, self.format)

    def to_url(self, value):
        return value.strftime(self.format)


register_converter(DateConverter, 'date')

from psycopg2.extras import DateRange



# @method_decorator([user_role_required(Role.GERANT)], name='dispatch')
class PrisEnchageOrdrePaymentUpdateView(PermissionRequiredMixin, BSModalUpdateView):
    model = PrisEnchageOrdrePayment
    c = "prisenchageordrepayment"
    template_name = 'core/update_entity.html'
    form_class = PrisEnchageOrdrePaymentModalForm
    permission_required = ('cddaccount.change_{}'.format(c, ),)
    success_message = 'Success: Mise à jour Prise en charge.'
    success_url = reverse_lazy('cddaccount:ordrepayment_list')

    def get_success_url(self):
        return self.object.ordre.get_absolute_url()

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            obj = form.save(commit=False)
            obj.ordre.reglement = obj.reglement
            obj.ordre.payment_mean = obj.payment_mean
            obj.ordre.reservationfond.payment_mean = obj.payment_mean
            obj.ordre.observations = obj.observations
            obj.ordre.reservationfond.save()
            obj.ordre.save()
            form.save()
        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour de l'ordre de paiement {}".format(self.object.ordre.sig_reference)
        return context


class PrisEnchageOrdrePaymentDeleteView(PermissionRequiredMixin, BSModalDeleteView):
    # specify the model you want to use
    model = PrisEnchageOrdrePayment

    permission_required = ('cddaccount.delete_{}'.format(model._meta.model_name),)

    # can specify success url
    # url to redirect after successfully
    # deleting object
    success_message = "Success: Supression de la prise en charge"
    success_url = reverse_lazy('cddaccount:ordrepayment_list')

    template_name = "core/confirm_delete_entity.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Supression de la prise en charge : {}".format(self.object, )
        return context

@login_required
def switch_contexte(request):
    template = 'cddaccount/switch_journee_comptable.html'
    if request.method == 'POST':
        form = JourneeComptableForm(request.POST)
        if form.is_valid():
            try:

                str_jour = request.POST['jour']  # 2022-12-28

                journee = form.cleaned_data["jour"]  # datetime.datetime.strptime(str_jour, '%Y-%m-%d')

                get_or_create_journee_comptable(request.user, journee)
            except SigException as e:
                messages.error(request, e.message, extra_tags="danger")
            return redirect(reverse('users:home_view'))
    else:
        form = JourneeComptableForm()

    context = {"form": form, 'title': "Change de journée comptable "}
    return render(request, template, context)


@login_required
@transaction.atomic()
@permission_required("bankcheck.receptionner_cheque", raise_exception=True)
def receptionner_cheque_view(request, reference):
    template = "cddaccount/validate_ordrepayment.html"
    user = request.user
    object = get_object_or_404(OrdrePayment, reference=reference)
    success_url = object.get_absolute_url()
    cheque = get_object_or_404(Cheque, reference=object.cheque)

    if cheque.can_delivered():
        pass
    else:
        raise Http404
    if not object.can_acces(user):
        raise Http404

    if request.method == 'POST':
        form = OtpForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data["otp"]
            if cheque.verify(otp):
                cheque.delivred = True
                cheque.delivred_date = datetime.datetime.now()
                cheque.save()
                object.cheque_delivred = True
                object.save()
                messages.success(request, "Cheque delivré")
            else:
                messages.error(request, "Token invalide", extra_tags="danger")

            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")
    else:
        form = OtpForm()

    context = {"form": form, 'title': "Valider par otp la reception de cheque  {}".format(object.reference, )}
    return render(request, template, context)


@login_required
def bulk_action(request):
    return bulk_validate_ops(request)


@login_required
@permission_required("cddaccount.delete_ordrepayment", raise_exception=True)
@transaction.atomic
def bulk_delete_ops(request):
    user = request.user
    success_url = reverse_lazy('cddaccount:ordrepayment_list')
    selected_licences_id = request.POST.getlist("selection")
    total = len(selected_licences_id)
    regs = OrdrePayment.objects.filter(id__in=selected_licences_id)
    b = 0
    for op in regs:
        op.delete()
        b += 1

    messages.add_message(request, messages.SUCCESS, "Ordre de paiement {}/{} supprimé avec succès".format(b, total))

    return redirect(success_url)


@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def temlate_op_view(request, reference):
    template = "cddaccount/template_op.html"
    user = request.user
    ordre = get_object_or_404(OrdrePayment, reference=reference)
    quarter = pd.Timestamp(ordre.created.date()).quarter
    if ordre.transfer_out_umeoa:
        template = "cddaccount/template_op_ent_pdf.html"
    if ordre.payment_mean==PAYMENT_MEAN_TYPE.RETRAIT:
        template = "cddaccount/template_ordre_paiement.html"
    if hasattr(user, "agent_saisie_cd") or hasattr(user, "gerant_cd"):
        if ordre.payment_mean == PAYMENT_MEAN_TYPE.RETRAIT:
            messages.success(request, "Vous ne pouvez pas éditer ce template")
            return redirect(reverse_lazy("users:home_view"))
        if hasattr(user, "agent_saisie_cd"):
            if user == ordre.creator:
                pass
            else:
                messages.success(request, "Vous ne pouvez pas éditer ce template")
                return redirect(reverse_lazy("users:home_view"))

        elif hasattr(user, "gerant_cd"):

            if user == ordre.creator:
                pass
            else:
                if hasattr(ordre.creator, "agent_saisie_cd") and ordre.compte.get_current_gerant() == user.gerant_cd:
                    pass
                else:
                    messages.success(request,
                                     "Vous ne pouvez pas éditer ce template")
                    return redirect(reverse_lazy("users:home_view"))

    else:
        # raise Http404
        if ordre.payment_mean != PAYMENT_MEAN_TYPE.RETRAIT:
            messages.success(request, "Vous ne pouvez pas éditer ce template")
            return redirect(reverse_lazy("users:home_view"))

    iban_items = ordre.benef_iban_items()
    gestion = ordre.gestion.year()
    journee_comptable = None
    if ordre.jour_comptable:
        journee_comptable = ordre.jour_comptable.day()
        gestion = ordre.jour_comptable.year()

    if not ordre.can_acces(user):
        raise Http404
    create_url = None
    gerant = None
    previous_url = ordre.get_absolute_url()

    compte = ordre.compte
    label_benef = "Bénéficiaire"
    if hasattr(ordre, "virementmasse"): label_benef = "Divers bénéficiaires"
    if ordre.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE:
        title = "Ordre de Paiement N° {}".format(ordre.cheque, )
    else:
        title = "Ordre de Virement N° {}".format(ordre.sig_reference, )

    context = {"previous_url": previous_url, "label_benef": label_benef, "gestion": gestion,
               "journee_comptable": journee_comptable, "compte": compte, "ordre": ordre, "agent": gerant,
               'title': title, "iban_items": iban_items,"quarter":quarter}
    return render(request, template, context)



def link_callback(uri, _rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access those
    resources.
    """
    result = finders.find(uri)
    if result:
        if not isinstance(result, (list, tuple)):
            result = [result]
        result = [os.path.realpath(path) for path in result]
        path = result[0]
    else:
        sUrl = settings.STATIC_URL  # Typically /static/
        sRoot = settings.STATIC_ROOT  # Typically /home/userX/project_static/
        mUrl = settings.MEDIA_URL  # Typically /media/
        mRoot = settings.MEDIA_ROOT  # Typically /home/userX/project_static/media/

        if uri.startswith(mUrl):
            path = os.path.join(mRoot, uri.replace(mUrl, ""))
        elif uri.startswith(sUrl):
            path = os.path.join(sRoot, uri.replace(sUrl, ""))
        else:
            return uri

    # make sure that file exists
    if not os.path.isfile(path):
        msg = f"media URI must start with {sUrl} or {mUrl}"
        raise RuntimeError(msg)
    return path


@login_required
def temlate_op_pdf_view(request, reference):
    template = "cddaccount/template_op_pdf.html"
    user = request.user
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    ordre = get_object_or_404(OrdrePayment, reference=reference)
    if ordre.transfer_out_umeoa:
        template = "cddaccount/template_op_ent_pdf.html"

    if hasattr(user, "agent_saisie_cd") or hasattr(user, "gerant_cd"):
        if hasattr(user, "agent_saisie_cd"):
            if user == ordre.creator:
                pass
            else:
                messages.success(request, "Vous ne pouvez pas éditer ce template")
                return redirect(reverse_lazy("users:home_view"))

        elif hasattr(user, "gerant_cd"):
            if user == ordre.creator:
                pass
            else:
                if hasattr(ordre.creator, "agent_saisie_cd") and ordre.compte.get_current_gerant() == user.gerant_cd:
                    pass
                else:
                    messages.success(request,
                                     "Vous ne pouvez pas éditer ce template")
                    return redirect(reverse_lazy("users:home_view"))

    else:
        # raise Http404
        messages.success(request, "Vous ne pouvez pas éditer ce template")
        return redirect(reverse_lazy("users:home_view"))

    iban_items = ordre.benef_iban_items()
    gestion = None
    journee_comptable = None
    if ordre.jour_comptable:
        journee_comptable = ordre.jour_comptable.day()
        gestion = ordre.jour_comptable.year()

    if not ordre.can_acces(user):
        raise Http404
    create_url = None
    gerant = None
    previous_url = ordre.get_absolute_url()

    compte = ordre.compte
    label_benef = "Bénéficiaire"
    if hasattr(ordre, "virementmasse"): label_benef = "Divers bénéficiaires"
    if ordre.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE:
        title = "Ordre de Paiement N° {}".format(ordre.cheque, )
    else:
        title = "Ordre de Virement N° {}".format(ordre.sig_reference, )
    if request.is_secure():
        base_url = "HTTPS://" + request.get_host()
    else:
        base_url = "HTTP://" + request.get_host()

    context = {"base_url": base_url, "previous_url": previous_url, "label_benef": label_benef, "gestion": gestion,
               "journee_comptable": journee_comptable, "compte": compte, "ordre": ordre, "agent": gerant,
               'title': title, "iban_items": iban_items}

    gettemplate = get_template(template)
    html = gettemplate.render(context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
    if pdf.err:
        return HttpResponse("Invalid PDF", status_code=400, content_type='text/plain')
    return HttpResponse(result.getvalue(), content_type='application/pdf')


from users.models import User

import time


@login_required
@transaction.atomic()
@permission_required("cddaccount.valider_ordrepayment")
def bulk_validate_ops(request):
    user = request.user
    selected_licences_id = request.POST.getlist("selection")
    regs = OrdrePayment.objects.filter(id__in=selected_licences_id)
    tpc = int(time.time())
    success_url = reverse_lazy('cddaccount:bulk_otp_confirm_op',
                               kwargs={"reference": str(tpc), "matricule": user.username})
    for op in regs:
        op.vali_multi = tpc
        op.save()

    return redirect(success_url)


@login_required
@transaction.atomic()
@permission_required("bankcheck.receptionner_cheque")
def bulk_retrait_cheque_ops(request):
    user = request.user
    selected_licences_id = request.POST.getlist("selection")
    regs = OrdrePayment.objects.filter(id__in=selected_licences_id)
    tpc = int(time.time())
    success_url = reverse_lazy('cddaccount:bulk_otp_confirm_retrait_cheque',
                               kwargs={"reference": str(tpc), "matricule": user.username})
    for op in regs:
        op.vali_multi = tpc
        op.save()

    return redirect(success_url)


@login_required
@transaction.atomic()
@permission_required("cddaccount.valider_ordrepayment")
def bulk_otp_confirm_op(request, reference, matricule):
    user = request.user
    template = "cddaccount/bulk_validation_op.html"
    success_url = success_url = reverse_lazy('cddaccount:ordrepayment_list')
    if matricule != user.username:
        raise Http404
    regs = None
    user = get_object_or_404(User, username=matricule)
    if hasattr(user, "gerant_cd"):
        agent = user.gerant_cd
        type_agent = "Gerant Compte "
        regs = OrdrePayment.objects.filter(vali_multi=reference)

    else:
        raise Http404
    op = regs.last()
    if op is None:
        messages.error(request, "Aucune  opération selectionnée", extra_tags="danger")

        return redirect(success_url)
    table = OrdrePaymentTable(regs, exclude=("selection", "action", "blocked", "gerant", "created"))
    RequestConfig(request, paginate={"per_page": 30}).configure(table)
    if request.method == 'POST':
        form = OtpValidationOrdrePaymentForm(request.POST)
        if form.is_valid():
            if request and not is_ajax(request.META):
                token = form.cleaned_data["otp"]
                origin_otp = SimpleOtp.objects.filter(otp=token).last()
                if origin_otp and origin_otp.verify(token):
                    for object in regs:
                        try:
                            can_debit_account_for_op(object)
                            object.previous_etape = object.etape
                            object.etape = ETAPE_ORDRE_PAYMENT.VALIDE
                            object.gerant = user
                            if object.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and object.depositaire is not None:
                                object.cin_receptionnaire = object.depositaire.nin
                                object.phone_receptionnaire = object.depositaire.phone

                            object.save()
                            # creationde de reservation
                            reservation = ReservationFond()
                            reservation.ordre = object
                            reservation.amount = object.amount
                            reservation.reliquat = object.amount
                            reservation.creator = user
                            reservation.save()
                            debit_account_balance_from_rsv(reservation)
                        except SigException as e:
                            messages.error(request, e.message, extra_tags="danger")


                    messages.success(request, "Validation faite avec succès")
                else:
                    messages.error(request, "Token invalide", extra_tags="danger")

            return redirect(success_url)
            messages.add_message(request, messages.SUCCESS,
                                 "Prise en charge cheque {}/{} licences fait avec succès".format(b, 20))
            return redirect(success_url)
    else:
        otp = SimpleOtp()
        otp.phone = agent.phone.as_e164
        otp.generate_otp()
        otp.message = op.get_otp_msg_all(otp.otp)
        otp.save()
        otp.send_otp()
        form = OtpValidationOrdrePaymentForm()

    context = {"form": form, 'title': "Merci de renseigner L'OTP reçu".format(reference, ), "table": table,
               "agent": agent, "type_agent": type_agent}
    return render(request, template, context)


@login_required
@transaction.atomic()
@permission_required("bankcheck.receptionner_cheque")
def bulk_otp_confirm_retrait_cheque(request, reference, matricule):
    user = request.user
    template = "cddaccount/bulk_retrait_cheque.html"
    success_url = success_url = reverse_lazy('cddaccount:ordrepayment_list')
    if matricule != user.username:
        raise Http404
    user = get_object_or_404(User, username=matricule)
    regs = OrdrePayment.objects.filter(vali_multi=reference)

    agent = user.agent_postecomptable

    op = regs.last()
    if op is None:
        messages.error(request, "Aucune  opération selectionnée", extra_tags="danger")

        return redirect(success_url)
    table = OrdrePaymentTable(regs, exclude=("selection", "action", "blocked", "gerant", "created"))
    RequestConfig(request, paginate={"per_page": 30}).configure(table)

    mdt = Mandataire.objects.by_agent(user)
    gerants = GerantCD.objects.by_agent(user)

    if request.method == 'POST':
        form = BulkTakeChequeVerifyPaymentForm(request.POST)
        form.fields["mandataire"].queryset = mdt
        form.fields["gerant"].queryset = gerants
        if form.is_valid():
            # if type==BENEF_CHOICES.BENEFICIAIRE and object.phone_receptionnaire :
            #   phone=object.phone_receptionnaire.as_e164

            if type == BENEF_CHOICES.MANDATAIRE:
                mandataire = form.cleaned_data["mandataire"]
                phone = mandataire.phone.as_e164
            if phone:
                success_url = reverse_lazy('cddaccount:visa_opcheques_list')
                messages.add_message(request, messages.SUCCESS,
                                     "Code otp envoyé avec succès")

            else:
                messages.add_message(request, messages.ERROR,
                                     "Aucun téléphoone disponibble pour ennvoyé l'otp")
            return redirect(success_url)

    else:
        form = BulkTakeChequeVerifyPaymentForm()
        form.fields["mandataire"].queryset = mdt
        form.fields["gerant"].queryset = gerants

    context = {"reference": reference, "matricule": matricule, "form": form,
               'title': "Merci de renseigner L'OTP reçu".format(reference, ), "table": table, "agent": agent}
    return render(request, template, context)





@login_required
@transaction.atomic()
@permission_required("cddaccount.annulation_ordrepayment", raise_exception=True)
def annulation_op_view(request, reference):
    template = "cddaccount/validate_ordrepayment.html"
    user = request.user

    object = get_object_or_404(OrdrePayment, reference=reference)
    success_url = object.get_absolute_url()

    if not object.can_acces(user):
        raise Http404

    if request.method == 'POST':
        form = CancelOPForm(request.POST)
        if form.is_valid():
            if request and not is_ajax(request.META):
                description = form.cleaned_data["description"]
                # cancel_op(object,user,description)
                try:
                    rejete_priseencharge_op(object, user, description)
                    messages.success(request, "Annullation effective")
                except SigException as e:
                    messages.error(request, e.message, extra_tags="danger")
            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")

    else:
        form = CancelOPForm()

    context = {"form": form, 'title': "Annuler la prise en charge N° {}".format(object.sig_reference, )}
    return render(request, template, context)


# notify.send(recipient, recipient=recipient, verb='New Contact us request')

@login_required
@transaction.atomic()
@permission_required("cddaccount.annulation_ordrepayment", raise_exception=True)
def reject_op_view(request, reference):
    template = "cddaccount/validate_ordrepayment.html"
    user = request.user

    object = get_object_or_404(OrdrePayment, reference=reference)
    success_url = object.get_absolute_url()

    if not object.can_acces(user):
        raise Http404

    if request.method == 'POST':
        form = CancelOPForm(request.POST)
        if form.is_valid():
            if request and not is_ajax(request.META):
                description = form.cleaned_data["description"]
                # cancel_op(object,user,description)
                try:
                    reject_pec_op(object, user, description)
                    messages.success(request, "Annullation effective")
                except SigException as e:
                    messages.error(request, e.message, extra_tags="danger")
            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")

    else:
        form = CancelOPForm()

    context = {"form": form, 'title': "Rejeter ordre de paiement {}".format(object.sig_reference, )}
    return render(request, template, context)


def call_notify_badge(ordrepayment):
    recepients = None
    category = None
    creator = ordrepayment.creator
    if creator.role == Role.GERANT:
        if ordrepayment.etape == ETAPE_ORDRE_PAYMENT.VALIDE:
            category = TypeNotif.live_notify_badge_receptionne_v
            recepients = User.objects.filter(agent_postecomptable__poste_id=ordrepayment.compte.poste_id)
    if creator.role == Role.AGENT_SAISIE_CD:
        if ordrepayment.etape == ETAPE_ORDRE_PAYMENT.SAISIE:
            category = TypeNotif.live_notify_badge_valide_v
            recepients = creator.agent_saisie_cd.gerant.user

    if ordrepayment.etape == ETAPE_ORDRE_PAYMENT.ACCEPTE:
        category = TypeNotif.live_notify_badge_priseencharge_v
        recepients = User.objects.filter(agent_postecomptable__poste_id=ordrepayment.compte.poste_id)

    if ordrepayment.etape == ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE:
        category = TypeNotif.live_notify_badge_visa_v
        recepients = User.objects.filter(agent_postecomptable__poste_id=ordrepayment.compte.poste_id)
    if recepients and category:
        notify_badge(ordrepayment, recepients, category, "Ordre de payment")
    print("end envoie notif")


from django.contrib.contenttypes.models import ContentType
from helpers.models import Notification


def delete_notification(ordrepayment, user):
    try:
        actortype = ContentType.objects.get_for_model(OrdrePayment)
        Notification.objects.filter(actor_content_type=actortype, actor_object_id=str(ordrepayment.id)).delete()
    except:
        traceback.print_exc()
        pass



@method_decorator([transaction.atomic()], name='dispatch')
class VirementMasseCreateView(PermissionRequiredMixin, BSModalCreateView):
    template_name = 'cddaccount/add_op.html'
    form_class = VirementMasseForm
    success_message = "Success: La saisie du virement de masse a été effectuée avec succès."
    success_url = reverse_lazy('cddaccount:nouveaux_virmasse_list')
    permission_required = ('cddaccount.add_{}'.format(form_class._meta.model._meta.model_name, ),)
    title = "Nouvelle saisie d'un virement de masse"
    raise_exception = True

    def set_default_type(self):
        self.object.payment_mean = PAYMENT_MEAN_TYPE.VIREMENT
        self.object.cheque = None
        self.object.reglement = TYPE_REGLEMENT.GLOBAL

    def get_form_class(self):
        """Return the form class to use."""
        q_search = self.request.GET.get('type', None)
        if q_search is None:
            self.form_class = VirementMasseForm
        else:
            self.form_class = VirementMasseForm

        return self.form_class

    def get_success_url(self):
        return self.object.get_absolute_url()

    # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_invalid(self, form):

        return super().form_invalid(form)

    @transaction.atomic
    def form_valid(self, form):
        user = self.request.user
        if not is_ajax(self.request.META):
            context = self.get_context_data()
            self.object = form.save(commit=False)
            self.set_default_type()

            try:
                self.object.is_valid_op()
            except SigException as e:
                messages.error(self.request, e.message, extra_tags="danger")
                return redirect(self.success_url)

            if hasattr(user, "agent_postecomptable"):

                self.object.etape = ETAPE_ORDRE_PAYMENT.VALIDE
                self.object.previous_etape = ETAPE_ORDRE_PAYMENT.SAISIE
                g = self.object.compte.get_current_gerant()
                if g:
                    self.object.gerant = g.user
            elif hasattr(user, "gerant_cd"):
                self.object.etape = ETAPE_ORDRE_PAYMENT.SAISIE
                self.object.gerant = user

            elif hasattr(self, "agent_saisie_cd"):
                self.object.etape = ETAPE_ORDRE_PAYMENT.SAISIE

            if self.object.compte.balance.amount < self.object.amount.amount:
                messages.error(self.request, "Solde du compte insuffisant pour cet ordre ", extra_tags="danger")

                return redirect(self.success_url)
            self.object.creator = user
            # creation details virement
            # datas = form.cleaned_data
            filehandle = self.request.FILES["details_file"]
            import hashlib

            file_name = filehandle
            # with open(file_name) as f:
            data = file_name.read()
            sha256_returned = hashlib.sha256(data).hexdigest()
            logger.info("SHA256 verified".format(sha256_returned))
            if VirementMasse.objects.filter(hash_file=sha256_returned).exists():
                messages.error(self.request, "Un virement de masse avec un fichier ayant le meme contenu existe ",
                               extra_tags="danger")
                return redirect(self.success_url)

            self.object.hash_file = sha256_returned
            with transaction.atomic():
                try:
                    self.object.save()
                    if hasattr(user, "agent_postecomptable"):
                        reservation = ReservationFond()
                        reservation.ordre = self.object
                        reservation.amount = self.object.amount
                        reservation.reliquat = self.object.amount
                        reservation.creator = user
                        reservation.save()

                    create_detailvirement_items_excel_file(self.object, filehandle,paymen_mean=self.object.payment_mean)
                    call_notify_badge(self.object)

                except SigException as e:
                    messages.error(self.request, e.message,
                                   extra_tags="danger")
                    self.object.delete()
                    return redirect(self.success_url)

        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        comptes = get_cdd_with_gerant(self.request)  # CompteDepot.objects.by_agent(self.request.user)

        context['form'].fields["compte"].queryset = comptes
        blocages = BlocageFond.objects.by_agent(self.request.user)
        # context['form'].fields["blocage"].queryset = blocages
        context['title'] = "Nouvelle Saisie Ordre de paiement"

        return context


def create_detailvirement_items_excel_file(virement, filehandle,paymen_mean=None,update_detailsvr=False):

    if paymen_mean== PAYMENT_MEAN_TYPE.MOBILE:
        return create_mobile_detailvirement_items_excel_file(virement, filehandle)
    df = pd.read_excel(filehandle, dtype=pd.StringDtype())
    remove_dup = False
    vrm_settings = SettingsVRM.object()
    if vrm_settings:
        plafond = vrm_settings.max_amount.amount
        remove_dup = vrm_settings.remove_dp
    else:
        ex = SigException(message="Merci de faire la config pour les virements de masse")
        raise ex


    if remove_dup:
        subset = ["BANQUE", "AGENCE", "COMPTE", "RIB", "BENEFICIAIRE", "MONTANT", "TELEPHONE"]
        df = df.drop_duplicates(subset=subset, keep="first")

    dataset = Dataset().load(df)
    detailvirements = dataset.dict

    total = sum(float(d['MONTANT']) for d in detailvirements)
    if update_detailsvr==True:
        virement.details_virements.all().delete()
    else:
        if total != float(virement.amount.amount):
            ex = SigException(
                message="Le montant saisi {} est différent de la somme des montants du fichier {}".format(virement.amount,
                                                                                                          total))
            raise ex
    nbschar = max(VirementDetails.objects.values_list("reference_aster", flat=True))
    nu = nbschar[-6:]
    max_ids = int(nu.lstrip("0"))

    for dtails in detailvirements:
        try:

            phone = None
            montant = float(dtails["MONTANT"])
            beneficiaire = str(dtails["BENEFICIAIRE"])
            banque = str(dtails["BANQUE"])
            agence = str(dtails["AGENCE"])
            account = str(dtails["COMPTE"])
            if "TELEPHONE" in dtails:
                phone = str(dtails["TELEPHONE"])
            rib = str(dtails["RIB"])
            rib_beneficiaire = "{}{}{}{}".format(banque, agence, account, rib)

            rib_beneficiaire = rib_beneficiaire.replace(" ", "")
            adrese_beneficiaire = "nonnrennseigne"  # str(dtails["ADRESSE_BENEFICIAIRE"])

            if montant > plafond:
                ex = SigException(
                    message="Le montant pour le bénéficiaire {}  {} est supérieur au montant plafonné {}".format(
                        beneficiaire, montant, plafond))
                raise ex

            iban = rib_beneficiaire
            if iban and len(iban) > 0:
                if len(iban) > 24:
                    ex = SigException(
                        message="Le rib {} du bénéficiaire {}  n'est pas conforme".format(iban, beneficiaire))
                    raise ex
                country_code = iban[:2]
                rib = iban[-2:]
                cal_rib = generate_rib(country_code, iban)
                if rib != cal_rib:
                    ex = SigException(
                        message="Le rib {} du bénéficiaire {}  n'est pas conforme".format(iban, beneficiaire))
                    raise ex

            ob = VirementDetails()
            ob.amount = montant
            ob.virement = virement
            ob.reference_aster = ob.generate_dv_reference(max_ids)
            max_ids += 1
            ob.libelle = virement.object
            ob.beneficiaire = beneficiaire
            ob.payment_mean = virement.payment_mean
            ob.iban_donneur = virement.compte.poste.comptebanque
            ob.adresse_benef = adrese_beneficiaire
            ob.iban_benef = rib_beneficiaire
            ob.date_payement = virement.open_date
            ob.compte_depot = virement.compte.short_compte
            ob.poste = virement.compte.poste.reference
            ob.phone_benef = phone
            ob.adresse_donneur = "DGCPT"
            ob.donneur = "DGCPT_{}".format(ob.poste, )
            ob.save()
        except SigException as c:
            raise c
        except:
            traceback.print_exc()
            ex = SigException()
            ex.message = "Erreur inconnue"
            raise ex

import re
def get_date_from_pattern(d):
    pattern1 = r'\d{2}/\d{2}/\d{4}'
    pattern2 = r'\d{4}-\d{2}-\d{2}'
    match = re.search(pattern1, d)
    match1 = re.search(pattern2, d)
    if match: format="%d/%m/%Y"
    if match1 : format="%Y-%m-%d %H:%M:%S"
    try:
        return datetime.datetime.strptime(d, format)
    except ValueError:

        return datetime.now()

def create_mobile_detailvirement_items_excel_file(virement, filehandle):
    df = pd.read_excel(filehandle, dtype=pd.StringDtype())
    remove_dup = False
    vrm_settings = SettingsVRM.object()
    if vrm_settings:
        plafond = vrm_settings.w_max_amount.amount
        remove_dup = vrm_settings.remove_dp
    else:
        ex = SigException(message="Merci de faire la config pour les virements de masse")
        raise ex

    subset = ["CIN","DATEENROLEMENT","LOCALITE", "NOM", "PRENOM", "MONTANT","OPERATEUR", "TELEPHONE"]

    if remove_dup:
        df = df.drop_duplicates(subset=subset, keep="first")

    dataset = Dataset().load(df)
    detailvirements = dataset.dict

    total = sum(float(d['MONTANT']) for d in detailvirements)
    if total != float(virement.amount.amount):
        ex = SigException(
            message="Le montant saisi {} est différent de la somme des montants du fichier {}".format(virement.amount,
                                                                                                      total))
        raise ex
    nbschar = max(VirementDetails.objects.values_list("reference_aster", flat=True))
    nu = nbschar[-6:]
    max_ids = int(nu.lstrip("0"))

    for dtails in detailvirements:
        try:

            phone = str(dtails["TELEPHONE"])

            if len(phone)!=9:
                ex = SigException(
                    message="Le numéro de téléphone de la ligne est obligatoire et de 9 chiffres {}".format(
                        phone,))
                raise ex
            montant = float(dtails["MONTANT"])
            prenom = str(dtails["PRENOM"])
            if len(prenom)>100:
                ex = SigException(
                    message="Le prénom de la ligne est obligatoire et inférieur ou égale à 100 caractères {}".format(
                        prenom,))
                raise ex

            nom = str(dtails["NOM"])
            if len(nom)>100:
                ex = SigException(
                    message="Le nom de la ligne est obligatoire et inférieur ou égale à 100 caractères {}".format(
                        nom,))
                raise ex

            beneficiaire = nom + " "+ prenom
            wallet_provider = str(dtails["OPERATEUR"])
            if wallet_provider not in ["ORANGE","WAVE","FREE","EXPRESSO"]:
                ex = SigException(
                    message="Le nom de l'opérateur de la ligne est obligatoire et doit être une de valeurs suivantes :ORANGE,WAVE,FREE,EXPRESSO. {}".format(
                        wallet_provider, ))
                raise ex

            wallet_number = phone
            cin = str(dtails["CIN"])

            if len(cin)>15:
                ex = SigException(
                    message="Le cni de la ligne est obligatoire et inférieur ou égale à 15 caractères {}".format(
                        cin,))
                raise ex


            dob = str(dtails["DATEENROLEMENT"])
            date_ouverture = get_date_from_pattern(dob)
            dob="{:%d/%m/%Y}".format(date_ouverture)
            lieu_dob = str(dtails["LOCALITE"])

            rib_beneficiaire = "{}_{}".format(wallet_provider,wallet_number)[0:23]

            rib_beneficiaire = rib_beneficiaire.replace(" ", "")
            adrese_beneficiaire = "nonnrennseigne"

            if montant > plafond:
                ex = SigException(
                    message="Le montant pour le bénéficiaire {}  {} est supérieur au montant plafonné {}".format(
                        beneficiaire, montant, plafond))
                raise ex


            ob = VirementDetails()
            ob.amount = montant
            ob.virement = virement
            ob.reference_aster = ob.generate_dv_reference(max_ids)
            max_ids += 1
            ob.libelle = virement.object
            ob.beneficiaire = beneficiaire
            ob.firstname=prenom
            ob.lastname=nom
            ob.payment_mean=virement.payment_mean
            ob.wallet_number=wallet_number
            ob.wallet_provider=wallet_provider
            ob.dob=dob
            ob.lieu_dob=lieu_dob
            ob.cin=cin
            ob.iban_donneur = virement.compte.poste.comptebanque
            ob.adresse_benef = adrese_beneficiaire
            ob.iban_benef = rib_beneficiaire
            ob.date_payement = virement.open_date
            ob.compte_depot = virement.compte.short_compte
            ob.poste = virement.compte.poste.reference
            ob.phone_benef = phone
            ob.adresse_donneur = "DGCPT"
            ob.donneur = "DGCPT_{}".format(ob.poste, )
            ob.save()
        except SigException as c:
            raise c
        except:
            traceback.print_exc()
            ex = SigException()
            ex.message = "Erreur inconnue"
            raise ex






@login_required
def generate_template_vrm(request):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="Fichier de virement de masse.xls"'

    # creating workbook
    currentdir = os.path.dirname(os.path.dirname(__file__))
    rd = xlrd.open_workbook(os.path.normpath(os.path.join(currentdir, 'fichierdevirementdemasse.xls')))
    wb = copy(rd)

    wb.save(response)
    return response


class OrdrePaymentUpdateView(PermissionRequiredMixin, BSModalUpdateView):
    model = OrdrePayment
    template_name = 'cddaccount/op_update.html'
    form_class = UpdateOrdrePaymentModelForm

    permission_required = ('cddaccount.change_{}'.format(model._meta.model_name),)
    success_message = 'Success: Mise à jour ordre de paiement.'
    success_url = reverse_lazy('cddaccount:ordrepayment_list')

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            obj = form.save(commit=False)
            if hasattr(object, "virementmasse"):
                messages.error(self.request, "Impossibble de modifier un virement de masse ")
                return redirect(self.success_url)
            print("------- {}-- ***-{} ".format(obj.get_sig_reference(), self.object.sig_reference))
            if obj.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and "cheque" in form.changed_data:
                if self.object.sig_reference != obj.get_sig_reference():
                    message = "Le numero de chèque ne peut etre modifié"
                    messages.error(self.request, message, extra_tags="danger")
                    return redirect(self.success_url)

            # on virifie si c'est un virement de masse

            if "details_file" in self.request.FILES:
                filehandle = self.request.FILES["details_file"]

                if filehandle and  hasattr(obj, "virementmasse"):
                    import hashlib
                    file_name = filehandle
                    data = file_name.read()
                    sha256_returned = hashlib.sha256(data).hexdigest()
                    logger.info("SHA256 verified".format(sha256_returned))
                    if VirementMasse.objects.filter(hash_file=sha256_returned).exists():
                        pass

                    with transaction.atomic():
                        obj.save()
                        print(obj.amount)
                        try:

                            viremementmasse = obj.virementmasse
                            viremementmasse.details_file=filehandle
                            viremementmasse.save()

                            create_detailvirement_items_excel_file(viremementmasse, filehandle,
                                                                   paymen_mean=obj.payment_mean,update_detailsvr=True)

                        except SigException as e:
                            messages.error(self.request, e.message,
                                           extra_tags="danger")
                            return redirect(self.success_url)
            else :obj.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        return super().form_invalid(form)

    def get_form_class(self):
        """Return the form class to use."""
        self.form_class = UpdateOPWithCddAccountForm
        if hasattr(self.request.user, "agent_postecomptable"):
            self.form_class = UpdateOPWithPCForm

        return self.form_class

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour {} : {}".format(self.object._meta.verbose_name, self.object)
        return context

    def get_initial(self):
        initial = super().get_initial()
        initial["gestion"] = self.object.gestion.id
        try:
            key = self.request.session["select_cddacc_user_id"]
            initial["account"] = key
        except:
            pass

        # etc...
        return initial


from django.core.exceptions import ImproperlyConfigured
# @method_decorator([ user_role_required(Role.GERANT,Role.AGENT_SAISIE_CD)], name='dispatch')
class OrdrePaymentDefaultCreateView(PermissionRequiredMixin, BSModalCreateView):
    template_name = 'cddaccount/add_pc_op.html'
    form_class = DefaultSaisieOrdrePaymentModelForm
    success_message = "Success: Saisie Ordre de paiement effectuée avec succès."
    success_url = reverse_lazy('cddaccount:ordrepayment_list')
    permission_required = ('cddaccount.add_{}'.format(form_class._meta.model._meta.model_name, ),)
    title = "Saisie Paiement"
    raise_exception = True

    def set_default_type(self):
        tp = self.request.GET.get('type', None)
        if tp == "v":
            self.object.payment_mean = PAYMENT_MEAN_TYPE.VIREMENT
            self.object.cheque = None
        if tp == "c":
            self.object.payment_mean = PAYMENT_MEAN_TYPE.CHEQUE
            self.object.iban = None

    def get_form_class(self):
        q_search = self.request.GET.get('type', None)
        self.form_class = SaisieOPWithCddAccountForm
        if hasattr(self.request.user, "agent_postecomptable"):
            self.form_class = SaisieOPWithPCForm
        return self.form_class

    def get_success_url(self):
        return self.object.get_absolute_url()

    # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return  super().dispatch(*args, **kwargs)


    def form_invalid(self, form):

        return super().form_invalid(form)

    @transaction.atomic
    def form_valid(self, form):
        user = self.request.user
        if not is_ajax(self.request.META):
            context = self.get_context_data()
            self.object = form.save(commit=False)
            # self.object.nature = Nature.objects.last()
            self.object.reglement = TYPE_REGLEMENT.GLOBAL
            if hasattr(user, "agent_postecomptable"):
                self.object.etape = ETAPE_ORDRE_PAYMENT.VALIDE
                self.object.previous_etape = ETAPE_ORDRE_PAYMENT.SAISIE
                jour_comptable= user.journee_comptables.filter(actif=True).last()
                if jour_comptable:
                    self.object.jour_comptable = user.journee_comptables.filter(actif=True).last()
                    self.object.open_date=self.object.jour_comptable.jour
                    self.object.created=self.object.jour_comptable.jour
                g = self.object.compte.get_current_gerant()
                if g:
                    self.object.gerant = g.user

            elif hasattr(user, "gerant_cd"):
                self.object.etape = ETAPE_ORDRE_PAYMENT.SAISIE
                self.object.gerant = user
                self.object.compte = CompteDepot.objects.get(id=int(context["account"]))

            elif hasattr(user, "agent_saisie_cd"):
                self.object.etape = ETAPE_ORDRE_PAYMENT.SAISIE
                self.object.compte = CompteDepot.objects.get(id=int(context["account"]))
            # self.object.gestion = AnneeComptable.current_gestion()
            self.object.gestion = AnneeComptable.objects.get(id=form.cleaned_data["gestion"])


            # controle non necessaire
            #try:
            #   self.object.is_valid_op()
            #except SigException as e:
            #   messages.error(self.request, e.message, extra_tags="danger")
            #   return redirect(self.success_url)

            if self.object.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and self.object.receptionnaire:

                c = form.cleaned_data["type_virement"]
                if c == TYPE_VIREMENT.SIMPLE:
                    if self.object.receptionnaire == TYPE_RECEPTIONNAIRE.GERANT:
                        self.object.cin_receptionnaire = user.nin
                        self.object.phone_receptionnaire = user.phone
                    elif self.object.receptionnaire == TYPE_RECEPTIONNAIRE.MANDATAIRE and self.object.depositaire:
                        self.object.cin_receptionnaire = self.object.depositaire.nin
                        self.object.phone_receptionnaire = self.object.depositaire.phone
                    else:
                        pass

            self.object.creator = user

            # on virifie si c'est un virement de masse
            filehandle = None
            if "details_file" in self.request.FILES:
                filehandle = self.request.FILES["details_file"]

            if filehandle:
                import hashlib
                file_name = filehandle
                data = file_name.read()
                sha256_returned = hashlib.sha256(data).hexdigest()
                logger.info("SHA256 verified".format(sha256_returned))
                if VirementMasse.objects.filter(hash_file=sha256_returned).exists():
                    pass

                with transaction.atomic():
                    try:
                        self.object.save()
                        viremementmasse = VirementMasse(ordrepayment_ptr_id=self.object.pk, details_file=filehandle,
                                                        hash_file=sha256_returned)
                        viremementmasse.__dict__.update(self.object.__dict__)
                        viremementmasse.hash_file = sha256_returned
                        viremementmasse.save()  # save_base(raw=True)

                        create_detailvirement_items_excel_file(viremementmasse, filehandle,paymen_mean=self.object.payment_mean)

                    except SigException as e:
                        messages.error(self.request, e.message,
                                       extra_tags="danger")
                        self.object.delete()
                        return redirect(self.success_url)

            else:
                self.object.save()

            if self.object.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and self.object.cheque:
                mark_cheque_as_use_for_op(self.object)
            if hasattr(user, "agent_postecomptable"):
                try:
                    self.object.created = self.object.jour_comptable.jour
                    self.object.save()
                    reservation = ReservationFond()
                    reservation.ordre = self.object
                    reservation.amount = self.object.amount
                    reservation.reliquat = self.object.amount
                    reservation.creator = user
                    reservation.created=self.object.created
                    if self.object.payment_mean :
                        reservation.payment_mean = self.object.payment_mean
                    reservation.save()
                    reservation.created = self.object.created
                    reservation.save()
                    debit_account_balance_from_rsv(reservation)
                except SigException as e:
                    messages.error(self.request, e.message, extra_tags="danger")
                    return redirect(self.success_url)

            call_notify_badge(self.object)
            if self.object.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE:
                messages.success(self.request, self.success_message)
                return redirect(self.success_url)
            else:
                if hasattr(user, "gerant_cd"):
                    c=reverse('cddaccount:temlate_op_view', kwargs={'reference': self.object.reference})
                    if self.object.payment_mean == PAYMENT_MEAN_TYPE.RETRAIT:
                        c = reverse('cddaccount:temlate_demandeop_view', kwargs={'reference': self.object.reference})

                    return HttpResponseRedirect(c)
                else: return redirect(self.success_url)

        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        pchoices=[(PAYMENT_MEAN_TYPE.CHEQUE, PAYMENT_MEAN_TYPE.CHEQUE),(PAYMENT_MEAN_TYPE.VIREMENT, PAYMENT_MEAN_TYPE.VIREMENT)]
        if self.request.user.has_perm('cddaccount.ask_demandeop'):
            pchoices.append((PAYMENT_MEAN_TYPE.RETRAIT,"ORDRE DE PAIEMENT"))
        if self.request.user.has_perm('cddaccount.ask_mobileop'):
            pchoices.append((PAYMENT_MEAN_TYPE.MOBILE,PAYMENT_MEAN_TYPE.MOBILE))
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Saisie Paiement "
        context['form'].fields["payment_mean"].choices = pchoices
        if hasattr(self.request.user, "agent_postecomptable"):
            comptes = CompteDepot.objects.by_agent(self.request.user)  # get_cdd_with_gerant(self.request)
            context['form'].fields["compte"].queryset = comptes

        else:
            try:
                key = self.request.session["select_cddacc_user_id"]
                context["account"] = key
            except:
                pass
        return context

    def get_initial(self):
        initial = super().get_initial()
        try:
            key = self.request.session["select_cddacc_user_id"]
            initial["account"] = key
            initial["gestion"] = AnneeComptable.current_gestion().id
        except:
            pass

        initial["typecompte"] = TypeCompteTrx.objects.get(code='BF').id
        initial["nature"] = Nature.objects.first().id

        if hasattr(self.request.user, "agent_postecomptable"):
            j = self.request.user.journee_comptables.filter(actif=True).last()
            initial["gestion"] = j.annee_comptable.id
        return initial


class OrdrePaymentCreateView(PermissionRequiredMixin, BSModalCreateView):
    template_name = 'cddaccount/add_pc_op.html'
    form_class = SaisieOPWithCddAccountForm
    success_message = "Success: Saisie Ordre de paiement effectuée avec succès."
    success_url = reverse_lazy('cddaccount:ordrepayment_list')
    permission_required = ('cddaccount.add_{}'.format(form_class._meta.model._meta.model_name, ),)
    title = "Saisie Paiement"

    def get_form_class(self):
        q_search = self.request.GET.get('type', None)
        self.form_class = SaisieOPWithCddAccountForm
        return self.form_class

    def get_success_url(self):
        return self.object.get_absolute_url()

    # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_invalid(self, form):
        print(form.errors)

        return super().form_invalid(form)

    @transaction.atomic
    def form_valid(self, form):
        user = self.request.user
        if not is_ajax(self.request.META):
            context = self.get_context_data()
            self.object = form.save(commit=False)
            self.object.compte = CompteDepot.objects.get(id=int(context["account"]))

            # self.object.nature = Nature.objects.last()
            self.object.reglement = TYPE_REGLEMENT.GLOBAL
            if hasattr(user, "agent_postecomptable"):
                self.object.etape = ETAPE_ORDRE_PAYMENT.VALIDE
                self.object.previous_etape = ETAPE_ORDRE_PAYMENT.SAISIE
                jour_comptable = user.journee_comptables.filter(actif=True).last()
                if jour_comptable:
                    self.object.jour_comptable = user.journee_comptables.filter(actif=True).last()
                    self.object.open_date = self.object.jour_comptable.jour
                    self.object.created = self.object.jour_comptable.jour
                g = self.object.compte.get_current_gerant()
                if g:
                    self.object.gerant = g.user

            elif hasattr(user, "gerant_cd"):
                self.object.etape = ETAPE_ORDRE_PAYMENT.SAISIE
                self.object.gerant = user
                self.object.gestion = AnneeComptable.current_gestion()

            elif hasattr(user, "agent_saisie_cd"):
                self.object.etape = ETAPE_ORDRE_PAYMENT.SAISIE
                self.object.gestion = AnneeComptable.current_gestion()
            #deprecate
            #try:
            #   self.object.is_valid_op()
            #except SigException as e:
            #   messages.error(self.request, e.message, extra_tags="danger")
            #   return redirect(self.success_url)

            if self.object.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and self.object.receptionnaire:
                c = form.cleaned_data["type_virement"]
                if c == TYPE_VIREMENT.SIMPLE:
                    if self.object.receptionnaire == TYPE_RECEPTIONNAIRE.GERANT:
                        self.object.cin_receptionnaire = user.nin
                        self.object.phone_receptionnaire = user.phone
                    elif self.object.receptionnaire == TYPE_RECEPTIONNAIRE.MANDATAIRE and self.object.depositaire:
                        self.object.cin_receptionnaire = self.object.depositaire.nin
                        self.object.phone_receptionnaire = self.object.depositaire.phone

                    else:
                        pass

            self.object.creator = user

            # on virifie si c'est un virement de masse
            filehandle = None
            if "details_file" in self.request.FILES:
                filehandle = self.request.FILES["details_file"]

            if filehandle:
                import hashlib
                file_name = filehandle
                data = file_name.read()
                sha256_returned = hashlib.sha256(data).hexdigest()

                logger.info("SHA256 verified".format(sha256_returned))
                if VirementMasse.objects.filter(hash_file=sha256_returned).exists():
                    pass
                with transaction.atomic():
                    try:
                        self.object.save()
                        viremementmasse = VirementMasse(ordrepayment_ptr_id=self.object.pk, details_file=filehandle,
                                                        hash_file=sha256_returned)
                        viremementmasse.__dict__.update(self.object.__dict__)
                        viremementmasse.hash_file = sha256_returned
                        viremementmasse.save()  # save_base(raw=True)

                        create_detailvirement_items_excel_file(viremementmasse, filehandle,paymen_mean=self.object.payment_mean)

                    except SigException as e:
                        messages.error(self.request, e.message,
                                       extra_tags="danger")
                        self.object.delete()
                        return redirect(self.success_url)

            else:
                self.object.save()

            if self.object.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and self.object.cheque:
                mark_cheque_as_use_for_op(self.object)
            if hasattr(user, "agent_postecomptable"):
                try:
                    self.object.created = self.object.jour_comptable.jour
                    self.object.save()
                    reservation = ReservationFond()
                    reservation.ordre = self.object
                    reservation.amount = self.object.amount
                    reservation.reliquat = self.object.amount
                    reservation.creator = user
                    if self.object.payment_mean :
                        reservation.payment_mean = self.object.payment_mean
                    reservation.save()
                    reservation.created = self.object.created
                    reservation.save()
                    debit_account_balance_from_rsv(reservation)
                except SigException as e:
                    messages.error(self.request, e.message, extra_tags="danger")
                    return redirect(self.success_url)
            call_notify_badge(self.object)
            if self.object.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE:
                messages.success(self.request, self.success_message)
                return redirect(self.success_url)
            else:
                if hasattr(user, "gerant_cd"):
                    c=reverse('cddaccount:temlate_op_view', kwargs={'reference': self.object.reference})
                    if self.object.payment_mean == PAYMENT_MEAN_TYPE.RETRAIT:
                        c = reverse('cddaccount:temlate_demandeop_view', kwargs={'reference': self.object.reference})
                    return HttpResponseRedirect(c)
                else : return redirect(self.success_url)


        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        id_compte = self.kwargs["pk"]
        compte = get_object_or_404(CompteDepot, id=id_compte)
        context['title'] = "Saisie Paiement sur le compte {}({})".format(compte.libelle_court, compte.short_compte)
        context["account"] = id_compte

        x = compte.get_current_gerant()

        if x :context["gerant_fullname"]=x.full_name()


        #context['form'].fields["type_nature"].choices = compte.types_account()
        context['form'].fields['amount'].min_value = 0
        context['form'].fields['amount'].max_value = int(compte.balance.amount)
        pchoices = [(PAYMENT_MEAN_TYPE.CHEQUE, PAYMENT_MEAN_TYPE.CHEQUE), (PAYMENT_MEAN_TYPE.VIREMENT, PAYMENT_MEAN_TYPE.VIREMENT)]
        if self.request.user.has_perm('cddaccount.ask_demandeop'):
            pchoices.append((PAYMENT_MEAN_TYPE.RETRAIT,"ORDRE DE PAIEMENT"))
        if self.request.user.has_perm('cddaccount.ask_mobileop'):
            pchoices.append((PAYMENT_MEAN_TYPE.MOBILE,PAYMENT_MEAN_TYPE.MOBILE))
        context['form'].fields["payment_mean"].choices = pchoices

        return context

    def get_initial(self):
        initial = super().get_initial()
        # Copy the dictionary so we don't accidentally change a mutable dict
        initial = initial.copy()
        initial['account'] = self.kwargs["pk"]
        initial["gestion"] = AnneeComptable.current_gestion().id
        initial["typecompte"] = TypeCompteTrx.objects.get(code='BF').id
        initial["nature"] = Nature.objects.first().id
        # etc...
        return initial


class OrdrePaymentByBFCreateView(PermissionRequiredMixin, BSModalCreateView):
    template_name = 'cddaccount/add_pc_op.html'
    form_class = PaymentByBFModelForm
    success_message = "Success: Saisie Ordre de paiement effectuée avec succès."
    success_url = reverse_lazy('cddaccount:ordrepayment_list')
    permission_required = ('cddaccount.add_{}'.format(form_class._meta.model._meta.model_name, ),)
    title = "Nouvelle Saisie Ordre de paiement"

    def get_success_url(self):
        return self.object.get_absolute_url()

    # @method_decorator(user_role_required("ADMIN"))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_invalid(self, form):

        return super().form_invalid(form)

    def form_valid(self, form):
        user = self.request.user
        if not is_ajax(self.request.META):
            self.object = form.save(commit=False)

            blocage = BlocageFond.objects.get(reference=form.cleaned_data['blocagefond'])

            self.object.blocage = blocage
            self.object.compte = blocage.compte
            self.object.typecompte=blocage.projet.typecompte
            self.object.beneficiaire = blocage.prestataire
            self.object.ninea = blocage.ninea
            self.object.iban = blocage.compte_iban
            self.object.payment_mean = PAYMENT_MEAN_TYPE.VIREMENT
            self.object.nature = Nature.objects.last()
            self.object.reglement = TYPE_REGLEMENT.GLOBAL
            self.object.gestion = AnneeComptable.current_gestion()
            self.object.jour_comptable = user.journee_comptables.filter(actif=True).last()

            if hasattr(user, "agent_postecomptable"):
                self.object.etape = ETAPE_ORDRE_PAYMENT.VALIDE
                self.object.etape = ETAPE_ORDRE_PAYMENT.VALIDE
                self.object.previous_etape = ETAPE_ORDRE_PAYMENT.SAISIE
                g = self.object.compte.get_current_gerant()
                if g:
                    self.object.gerant = g.user
            elif hasattr(user, "gerant_cd"):
                self.object.etape = ETAPE_ORDRE_PAYMENT.SAISIE
                self.object.gerant = user

            elif hasattr(self, "agent_saisie_cd"):
                self.object.etape = ETAPE_ORDRE_PAYMENT.SAISIE

            try:
                self.object.is_valid_op()
            except SigException as e:
                messages.error(self.request, e.message, extra_tags="danger")
                return redirect(self.success_url)

            if self.object.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and self.object.receptionnaire:
                if self.object.receptionnaire == TYPE_RECEPTIONNAIRE.GERANT:
                    self.object.cin_receptionnaire = user.nin
                    self.object.phone_receptionnaire = user.phone
                elif self.object.receptionnaire == TYPE_RECEPTIONNAIRE.MANDATAIRE and self.object.depositaire:
                    self.object.cin_receptionnaire = self.object.depositaire.nin
                    self.object.phone_receptionnaire = self.object.depositaire.phone

                else:
                    pass

            self.object.creator = user

            # on virifie si c'est un virement de masse
            filehandle = None
            if "details_file" in self.request.FILES:
                filehandle = self.request.FILES["details_file"]

            if filehandle:
                import hashlib
                file_name = filehandle
                data = file_name.read()
                sha256_returned = hashlib.sha256(data).hexdigest()
                logger.info("SHA256 verified".format(sha256_returned))
                if VirementMasse.objects.filter(hash_file=sha256_returned).exists():
                    pass

                with transaction.atomic():
                    try:
                        self.object.save()
                        viremementmasse = VirementMasse(ordrepayment_ptr_id=self.object.pk, details_file=filehandle,
                                                        hash_file=sha256_returned)
                        viremementmasse.__dict__.update(self.object.__dict__)
                        viremementmasse.hash_file = sha256_returned
                        viremementmasse.save()  # save_base(raw=True)

                        create_detailvirement_items_excel_file(viremementmasse, filehandle,paymen_mean=self.object.payment_mean)

                    except SigException as e:
                        messages.error(self.request, e.message,
                                       extra_tags="danger")
                        self.object.delete()
                        return redirect(self.success_url)

            else:
                self.object.save()

            if self.object.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE and self.object.cheque:
                mark_cheque_as_use_for_op(self.object)
            if hasattr(user, "agent_postecomptable"):
                try:
                    reservation = ReservationFond()
                    reservation.ordre = self.object
                    reservation.amount = self.object.amount
                    reservation.reliquat = self.object.amount
                    reservation.creator = user
                    if self.object.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT:
                        reservation.payment_mean = self.object.payment_mean
                    reservation.save()
                except SigException as e:
                    messages.error(self.request, e.message, extra_tags="danger")
                    return redirect(self.success_url)
            call_notify_badge(self.object)
            if self.object.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE:
                messages.success(self.request, self.success_message)
                return redirect(self.success_url)
            else:
                return redirect(self.success_url)
        # c=reverse('cddaccount:temlate_op_pdf_view', kwargs={'reference': self.object.reference})
        # return HttpResponseRedirect(c)

        return super().form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)

        id_blocage = self.kwargs["reference"]

        blocageFond = get_object_or_404(BlocageFond, reference=id_blocage)
        projet = blocageFond.projet
        compte = blocageFond.compte
        context[
            'title'] = "Saisie Ordre de paiement sur le compte {} ({}).\nSur les fonds bloqués du  projet {} réferencié {}".format(
            compte.libelle_court, compte.short_compte, projet.name, projet.ref_marche)

        context['blocagefond'] = id_blocage
        context['form'].fields["type_nature"].choices = compte.types_account()
        context['form'].fields['amount'].min_value = 0
        context['form'].fields['ninea'].value = blocageFond.ninea
        context['form'].fields['beneficiaire'].value = blocageFond.prestataire
        context['form'].fields['iban'].value = blocageFond.compte_iban

        context['form'].fields['amount'].max_value = int(blocageFond.balance.amount)
        context['form'].fields['amount'].placeholder = "Max : ".format(int(blocageFond.balance.amount), )
        return context

    def get_initial(self):
        initial = super().get_initial()
        id_blocage = self.kwargs["reference"]

        blocageFond = get_object_or_404(BlocageFond, reference=id_blocage)
        initial["beneficiaire"] = blocageFond.prestataire
        initial["blocagefond"] = id_blocage
        initial["ninea"] = blocageFond.ninea
        initial["iban"] = blocageFond.compte_iban

        # etc...
        return initial


@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def test_view(request):
    template = "cddaccount/new_recu_op.html"
    user = request.user

    context = {}
    return render(request, template, context)








@login_required
@transaction.atomic
@permission_required("cddaccount.delete_visaordrepayment")
def annuler_visa_view(request, pk):
    template = 'cddaccount/add_op.html'
    user = request.user
    trx = get_object_or_404(TransactionOP, id=pk)

    object = trx.reservation.ordre
    delete_notification(object, user)
    success_url = reverse_lazy('cddaccount:op_dejavises_list_view')  # object.get_absolute_url()
    if not object.can_acces(user):
        raise Http404
    if hasattr(object, "annulation_op"):
        messages.info(request, "Ordre de paiement déjà annulé")
        return redirect(success_url)
    print(trx.has_cancel)
    if trx.has_cancel == True:
        messages.info(request, "Annulation  visa effective")
        return redirect(success_url)

    gerant = None
    if object.gerant:
        gerant = object.gerant.gerant_cd
    if request.method == 'POST':
        form = AnnuleVisaForm(request.POST)

        if form.is_valid():
            try:
                cancel_transactionop(trx, user)
                messages.info(request, "En cours de traitemnt")
            except SigException as e:
                messages.error(request, e.message)
            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")
    else:
        form = AnnuleVisaForm()

    context = {"form": form, 'title': "Annuler Visa {}".format(object.sig_reference, ), "object": object,
               "compte": object.compte, "agent": gerant, }
    return render(request, template, context)


@transaction.atomic
def cancel_transactionop(trx, user):
    try:
        if trx.has_cancel == True:
            raise SigException(message="Annulation visa effective")
        jour_comptable = user.journee_comptables.filter(actif=True).last()
        if not jour_comptable:
            raise SigException(message="Aucune journéé comptable active")
        if jour_comptable.jour<trx.jour_comptable.jour:
            raise SigException(message="La journnée comptable doit etre superieur a {}".format(trx.jour_comptable.jour,))
        if jour_comptable.annee_comptable!=trx.jour_comptable.annee_comptable:
            v="La gestion courrente {} est differente de celle de la tranaction {}".format(jour_comptable.annee_comptable.year(),trx.jour_comptable.annee_comptable.year())

            raise SigException(message=v)
        reservation = trx.reservation
        ordre = reservation.ordre
        canceltrx = TransactionOP()
        canceltrx.reservation = reservation
        canceltrx.amount = trx.amount
        canceltrx.account_depot = trx.account_depot
        canceltrx.poste_comptable = trx.poste_comptable
        canceltrx.rib_cdd = trx.rib_cdd
        canceltrx.date_rlv=datetime.date.today()
        canceltrx.is_cancel_trx = True
        canceltrx.ref_trx = trx.reference
        canceltrx.typecompte=trx.typecompte
        canceltrx.origin_reference = trx.origin_reference
        if trx.account_secondaire:
            canceltrx.account_secondaire = trx.account_secondaire
        else:
            canceltrx.account_secondaire = "-"
        canceltrx.cheque = trx.cheque
        canceltrx.agent = user
        canceltrx.jour_comptable = jour_comptable
        x= "Annulation visa n {} pour {}".format(trx.origin_reference, trx.libelle)
        canceltrx.libelle = x[:100]
        canceltrx.sens = SENS_TRX.CREDIT
        canceltrx.payment_mean = trx.payment_mean
        canceltrx.reglement = trx.reglement
        canceltrx.nature_depense = trx.nature_depense
        canceltrx.ref_canceltrx = trx.reference
        canceltrx.save()
        trx.has_cancel = True
        trx.ref_canceltrx = canceltrx.reference
        trx.save()

        if hasattr(ordre.prise_en_charge, "visa"):
            if ordre.prise_en_charge.visa.id is not None: ordre.prise_en_charge.visa.delete()
        ordre.previous_etape = ETAPE_ORDRE_PAYMENT.ACCEPTE
        ordre.etape = ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE
        ordre.save()
        reservation.has_cancel_op=True
        reservation.save()

        if trx.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE:
            CddProcessManager.send_cheque_trx_aster(user, canceltrx)
        else:
            if trx.payment_mean == PAYMENT_MEAN_TYPE.VIREMENT:
                CddProcessManager.bulk_delete_detailvr_aster(user, trx)
            CddProcessManager.send_virement_trx_aster(user, canceltrx)

    # cancel detail_virement
    except SigException as e:
        raise e
    except:
        raise SigException(message="erreur inconnue")


class OrdrePaymentUpdatePaymentView(PermissionRequiredMixin, BSModalUpdateView):
    model = OrdrePayment
    template_name = 'cddaccount/op_update.html'
    form_class = UpdateOrdrePaymentPaymentModelForm

    permission_required = ('cddaccount.change_{}'.format(model._meta.model_name),)
    success_message = 'Success: Mise à jour ordre de paiement.'
    success_url = reverse_lazy('cddaccount:ordrepayment_list')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title'] = "Mise à jour {} : {}".format(self.object._meta.verbose_name, self.object)
        if self.object.payment_mean in [PAYMENT_MEAN_TYPE.RETRAIT,PAYMENT_MEAN_TYPE.NUMERAIRE]:
            context['form'].fields["payment_mean"].choices =[PAYMENT_MEAN_TYPE.NUMERAIRE]
        return context

    def form_valid(self, form):
        if not is_ajax(self.request.META):
            user = self.request.user
            self.object = form.save()
            if hasattr(self.object,"reservationfond"):
                self.object.reservationfond.payment_mean=self.object.payment_mean
                self.object.reservationfond.save()

        return super().form_valid(form)



@login_required
@transaction.non_atomic_requests
@permission_required("bankcheck.receptionner_cheque", raise_exception=True)
def send_otp_to_receptionnaire(request, reference):
    template = "cddaccount/takeCheque.html"
    url = reverse('cddaccount:receptionner_cheque', kwargs={'reference': reference})
    user = request.user
    object = get_object_or_404(OrdrePayment, reference=reference)
    success_url = object.get_absolute_url()
    cheque = get_object_or_404(Cheque, reference=object.cheque)
    gerant = object.compte.get_current_gerant()
    phone = None

    if not cheque.can_delivered():
        raise Http404
    if not object.can_acces(user):
        raise Http404

    if gerant:
        mdt = gerant.mandataires.all()
        phone = gerant.phone.as_e164
    else:
        mdt = Mandataire.objects.none()

    if request.method == 'POST':
        form = TakeChequeVerifyPaymentForm(request.POST)
        form.fields["mandataire"].queryset = mdt
        if form.is_valid():
            if type == BENEF_CHOICES.BENEFICIAIRE and object.phone_receptionnaire:
                phone = object.phone_receptionnaire.as_e164

            if type == BENEF_CHOICES.MANDATAIRE:
                mandataire = form.cleaned_data["mandataire"]
                phone = mandataire.phone.as_e164
            if phone:
                cheque.phone_receptionnaire = phone
                cheque.generate_otp_and_save()
                cheque.send_cheque_otp(cheque.phone_receptionnaire)
                success_url = reverse_lazy('cddaccount:visa_opcheques_list')
                messages.add_message(request, messages.SUCCESS,
                                     "Code otp envoyé avec succès")

            else:
                messages.add_message(request, messages.ERROR,
                                     "Aucun téléphoone disponibble pour ennvoyé l'otp")
            return redirect(success_url)

    else:
        form = TakeChequeVerifyPaymentForm()
        form.fields["mandataire"].queryset = mdt

    context = {"reference": object.reference, 'mandataire': mdt, "form": form,
               'title': "choisir le type de beneficiaire ".format(object.reference, )}
    return render(request, template, context)


@login_required
@transaction.non_atomic_requests
@permission_required("bankcheck.receptionner_cheque", raise_exception=True)
def send_otp_to_receptionnaire_new(request, reference):
    template = "cddaccount/retrait_cheque_avec_otp.html"
    url = reverse('cddaccount:receptionner_cheque', kwargs={'reference': reference})
    user = request.user
    object = get_object_or_404(OrdrePayment, reference=reference)
    success_url = object.get_absolute_url()
    cheque = get_object_or_404(Cheque, reference=object.cheque)
    gerant = object.compte.get_current_gerant()
    phone = None

    if not cheque.can_delivered():
        raise Http404
    if not object.can_acces(user):
        raise Http404

    if gerant:
        mdt = gerant.mandataires.all()
        phone = gerant.phone.as_e164
    else:
        mdt = Mandataire.objects.none()

    if request.method == 'POST':
        form = TakeChequeVerifyPaymentForm(request.POST)
        form.fields["mandataire"].queryset = mdt
        if form.is_valid():
            # if type==BENEF_CHOICES.BENEFICIAIRE and object.phone_receptionnaire :
            #   phone=object.phone_receptionnaire.as_e164

            if type == BENEF_CHOICES.MANDATAIRE:
                mandataire = form.cleaned_data["mandataire"]
                phone = mandataire.phone.as_e164
            if phone:
                cheque.phone_receptionnaire = phone
                cheque.generate_otp_and_save()
                cheque.send_cheque_otp(cheque.phone_receptionnaire)
                success_url = reverse_lazy('cddaccount:visa_opcheques_list')
                messages.add_message(request, messages.SUCCESS,
                                     "Code otp envoyé avec succès")

            else:
                messages.add_message(request, messages.ERROR,
                                     "Aucun téléphoone disponibble pour ennvoyé l'otp")
            return redirect(success_url)

    else:
        form = TakeChequeVerifyPaymentForm()
        form.fields["mandataire"].queryset = mdt

    context = {"cheque": cheque.reference, "reference": object.reference, 'mandataire': mdt, "form": form,
               "object": object, "compte": object.compte,
               'title': "choisir le type de beneficiaire ".format(object.reference, ), "send_otp": cheque.send_otp}
    return render(request, template, context)





from django.views.decorators.csrf import csrf_exempt
from django.http.request import QueryDict
from django.http import JsonResponse

import json


@csrf_exempt
@atomic
def process_cbk_data(request, token):
    '''
    Calls process_data of an appropriate provider.

    Raises Http404 if variant does not exist.
    '''

    payment = get_object_or_404(OrdrePayment, reference=str(token))
    querydict_data = request.POST

    if querydict_data:
        if isinstance(querydict_data, QueryDict):
            querydict_data = querydict_data.dict()

    else:
        if request.body: querydict_data = json.loads(request.body)

    logger.info(querydict_data)

    if "status" in querydict_data:
        status = querydict_data["status"]
        try:
            if status == "RECU":
                CddProcessManager.create_trx_from_rsp_and_ordre(None, payment, querydict_data)
        except Exception:
            logger.debug(" demande rsv non trouve")
    return JsonResponse({"code": "000", "message": "data received"})






@login_required
@transaction.atomic()
@permission_required("cddaccount.change_anneecomptable", raise_exception=True)
def basculer_gestion_view(request, id):
    template = "cddaccount/validate_ordrepayment.html"
    gestion = get_object_or_404(AnneeComptable, id=id)
    success_url = reverse_lazy('cddaccount:anneecomptable_list')
    if gestion.parent is None:
        messages.error(request, "Gestion n'est pas bien parametré", extra_tags="danger")
        return redirect(success_url)

    if request.method == 'POST':
        form = SimpleOPForm(request.POST)
        if form.is_valid():
            if request and not is_ajax(request.META):
                otp = form.cleaned_data["description"]
                create_basculement(gestion)
                messages.success(request, "Basculement fait ")
            return redirect(success_url)
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")
    else:
        form = SimpleOPForm()

    context = {"form": form, 'title': "Valider basculement gestion {}".format(gestion.name, )}
    return render(request, template, context)




@login_required
# @user_role_required(Role.AGENT_SAISIE_CD)
# @permission_required("cddaccount.priseencharge_ordrepayment")
def temlate_demandeop_view(request, reference):
    template = "cddaccount/template_op.html"
    user = request.user
    ordre = get_object_or_404(OrdrePayment, reference=reference)
    quarter = pd.Timestamp(ordre.created.date()).quarter
    if ordre.transfer_out_umeoa:
        template = "cddaccount/template_op_ent_pdf.html"
    if ordre.payment_mean==PAYMENT_MEAN_TYPE.RETRAIT:
        template = "cddaccount/template_demandeop.html"
    if hasattr(user, "agent_saisie_cd") or hasattr(user, "gerant_cd"):
        if hasattr(user, "agent_saisie_cd"):
            if user == ordre.creator:
                pass
            else:
                messages.success(request, "Vous ne pouvez pas éditer ce template")
                return redirect(reverse_lazy("users:home_view"))

        elif hasattr(user, "gerant_cd"):
            if user == ordre.creator:
                pass
            else:
                if hasattr(ordre.creator, "agent_saisie_cd") and ordre.compte.get_current_gerant() == user.gerant_cd:
                    pass
                else:
                    messages.success(request,
                                     "Vous ne pouvez pas éditer ce template")
                    return redirect(reverse_lazy("users:home_view"))

    else:
        # raise Http404
        messages.success(request, "Vous ne pouvez pas éditer ce template")
        return redirect(reverse_lazy("users:home_view"))

    iban_items = ordre.benef_iban_items()
    gestion = ordre.gestion.year()
    journee_comptable = None
    if ordre.jour_comptable:
        journee_comptable = ordre.jour_comptable.day()
        gestion = ordre.jour_comptable.year()

    if not ordre.can_acces(user):
        raise Http404
    create_url = None
    gerant = None
    previous_url = ordre.get_absolute_url()

    compte = ordre.compte
    label_benef = "Bénéficiaire"
    if hasattr(ordre, "virementmasse"): label_benef = "Divers bénéficiaires"
    if ordre.payment_mean == PAYMENT_MEAN_TYPE.CHEQUE:
        title = "Demande Ordre de Paiement N° {}".format(ordre.cheque, )
    else:
        title = "Demande Ordre de Virement N° {}".format(ordre.sig_reference, )

    context = {"previous_url": previous_url, "label_benef": label_benef, "gestion": gestion,
               "journee_comptable": journee_comptable, "compte": compte, "ordre": ordre, "agent": gerant,
               'title': title, "iban_items": iban_items,"quarter":quarter}
    return render(request, template, context)
