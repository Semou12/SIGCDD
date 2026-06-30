import traceback

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

from bankcheck.forms import TYPE_PC_CHOICES
from bankcheck.signals import chequier_status_changed
from bankcheck.models import Chequier, Cheque, ComptableMatiere
from cddaccount.forms import BENEF_CHOICES
from cddaccount.models import CompteDepot, CodeAgence, generate_account_number, SousNature, Mandataire, OrdrePayment, \
    GerantCD, compute_all_balances_for_compte, AnneeComptable
from core.models import PosteComptable, Secteur, CodeService,ProfilePC
from helpers.exceptions import SigException
from helpers.models import SimpleOtp
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
import datetime
@login_required()
def send_otp_sms_for_agent_pc(request):
    # request should be ajax and method should be GET.
    ref_otp=None
    send_otp = False
    if request.method == "POST":
        try:
            querydict_data = request.POST.dict()
            print(querydict_data)
            cheque_ref = querydict_data.get("bulkreference")


            _type = querydict_data.get("type")

            if _type == TYPE_PC_CHOICES.MATIERE:
                mandataire_id = querydict_data.get("matiere")
                mandataire = ComptableMatiere.objects.get(id=mandataire_id)
                phone = mandataire.phone.as_e164
            else:
                agent_ref = querydict_data.get("agent")
                ag = ProfilePC.objects.get(id=agent_ref)
                phone = ag.phone.as_e164
            if phone:
                send_otp = True
                otp = SimpleOtp()
                otp.phone = phone
                otp.generate_otp()
                otp.message = Chequier.static_get_otp_retrait(otp.otp)
                otp.save()
                ref_otp=otp.reference
                otp.send_otp()
        except:
            traceback.print_exc()
            pass
    context={"send_otp":send_otp,"bulkreference":cheque_ref,"otpreference":ref_otp}
    return render(request, 'bankcheck/bulk_cpt.html', context)




@login_required()
def verify_otp_sms_for_agent_pc(request):
    # request should be ajax and method should be GET.
    obj=None
    send_otp=True
    if request.method == "POST":
        try:
            querydict_data = request.POST.dict()
            print(querydict_data)
            otp = request.POST.get("otp")
            bulkreference = request.POST.get("bulkreference")
            otpreference=request.POST.get("otpreference")
            simpleOtp = SimpleOtp.objects.get(reference=otpreference)

            if simpleOtp.verify(otp):
                regs = Chequier.objects.filter(otp_apc=int(bulkreference))
                for chq in regs:
                    chq.distribue = True
                    chq.distribue_date = datetime.datetime.now()
                    chq.save()
                    try:
                        chequier_status_changed.send(sender=type(chq), instance=chq)
                    except SigException as e:
                        pass

                messages.success(request, "Chequier delivré")
                v = reverse("bankcheck:chequiers_list")
                response = HttpResponse()
                response["HX-Redirect"] = v
                return response
            else:
                 send_otp=True
                 messages.error(request, "Token invalide", extra_tags="danger")
                 v = reverse("bankcheck:chequiers_list")
                 response = HttpResponse()
                 response["HX-Redirect"] = v
                 return response


        except:
            traceback.print_exc()
            pass
    context={"obj":obj,"send_otp":send_otp,"bulkreference":bulkreference,"otpreference":otpreference}
    return render(request, 'bankcheck/bulk_cpt.html', context)
