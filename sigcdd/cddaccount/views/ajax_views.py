import traceback

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

from bankcheck.models import Cheque
from cddaccount.forms import BENEF_CHOICES
from cddaccount.models import CompteDepot, CodeAgence, generate_account_number, SousNature, Mandataire, OrdrePayment, \
    GerantCD, compute_all_balances_for_compte, AnneeComptable
from core.models import PosteComptable, Secteur, CodeService
from helpers.models import SimpleOtp


def load_compte_infos(request):
    # request should be ajax and method should be GET.
    if  request.method == "GET":
        # get the nick name from the client side.
        try:
            id = request.GET.get("id", "0")
            if id == 0:
                return JsonResponse({"valid": True, "infos": {}}, status=200)
            asc = CompteDepot.objects.get(id=int(id))
            return JsonResponse({"valid": True,"infos":asc.infos_account()}, status=200)
        except:
            return JsonResponse({}, status=400)
    return JsonResponse({}, status=400)

def load_compte_by_poste(request):
    # request should be ajax and method should be GET.
    if  request.method == "GET":
        # get the nick name from the client side.
        try:
            id = request.GET.get("id", "0")
            if id == 0:
                return JsonResponse({"valid": True, "infos": {}}, status=200)
            ascs = CompteDepot.objects.filter(poste_id=int(id))
            d = [{"id": asc.pk, "name": asc.libelle_court} for asc in ascs]
            return JsonResponse({"valid": True,"infos":d}, status=200)
        except:
            traceback.print_exc()
            return JsonResponse({}, status=400)
    return JsonResponse({}, status=400)


def ajax_generate_account_number(request):
    # request should be ajax and method should be GET.
    if  request.method == "GET":
        # get the nick name from the client side.
        try:
            poste_id = request.GET.get("poste", "0")
            secteur_id = request.GET.get("secteur", "0")
            service_id = request.GET.get("service", "0")
            agence_id = request.GET.get("agence", "0")

            poste = PosteComptable.objects.get(id=int(poste_id))
            secteur = Secteur.objects.get(id=int(secteur_id))
            service = CodeService.objects.get(id=int(service_id))
            agence = CodeAgence.objects.get(id=int(agence_id))
            refs=CompteDepot.objects.filter(code_service=service,secteur=secteur).values_list("short_compte", flat=True)
            taille=len(refs)
            n=generate_account_number(poste.reference,secteur.reference_for_cddaccount(),service.reference_for_cddaccount(),agence.get_code_guichet(),taille,refs)
            return JsonResponse({"valid": True,"compte":n}, status=200)
        except:
            return JsonResponse({}, status=400)
    return JsonResponse({}, status=400)


def load_sousnnature_by_nature(request):
    # request should be ajax and method should be GET.
    if  request.method == "GET":
        # get the nick name from the client side.
        try:
            id = request.GET.get("id", "0")
            if id == 0:
                return JsonResponse({"valid": True, "directions": []}, status=200)
            ascs = SousNature.objects.filter(nature_id=int(id))

            d=[{"id":asc.pk,"name":asc.name} for asc in ascs]
            return JsonResponse({"valid": True,"sousnatures":d}, status=200)
        except:
            return JsonResponse({}, status=400)
    return JsonResponse({}, status=400)




@login_required()
def send_otp_sms_for_cheque(request):
    # request should be ajax and method should be GET.
    obj=None
    phone=None
    owner=None
    send_otp = False
    if request.method == "POST":
        try:
            print(request.POST)
            querydict_data = request.POST.dict()
            print(querydict_data)
            _type = querydict_data.get("type")


            cheque_ref = querydict_data.get("cheque")
            ordre_ref = querydict_data.get("ordre")
            cheque = Cheque.objects.get(reference=cheque_ref)
            gerant = cheque.chequier.compte.get_current_gerant()

            if _type == BENEF_CHOICES.MANDATAIRE:
                mandataire_id = querydict_data.get("mandataire")
                mandataire = Mandataire.objects.get(id=mandataire_id)
                phone = mandataire.phone.as_e164
            elif _type == BENEF_CHOICES.GERANT:
                phone=gerant.phone.as_e164
            if phone:
                cheque.send_otp=True
                cheque.phone_receptionnaire = phone
                cheque.generate_otp_and_save()
                send_otp=True
                cheque.send_cheque_otp(cheque.phone_receptionnaire)


        except:
            traceback.print_exc()
            pass
    context={"send_otp":send_otp,"ordre_ref":ordre_ref}
    return render(request, 'cddaccount/component.html', context)


from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
import datetime
@login_required()
def verify_otp_sms_for_cheque(request):
    # request should be ajax and method should be GET.
    obj=None
    send_otp=True
    if request.method == "POST":
        try:
            otp = request.POST.get("otp")
            ordre_ref = request.POST.get("ordre")
            ordre = OrdrePayment.objects.get(reference=ordre_ref)
            cheque = Cheque.objects.get(reference=ordre.cheque)
            send_otp=cheque.send_otp

            if cheque.verify(otp):
                cheque.delivred = True
                cheque.delivred_date = datetime.datetime.now()
                #cheque.send_otp=False
                cheque.save()
                ordre.cheque_delivred = True
                ordre.save()
                messages.success(request, "Cheque delivré")
                v = reverse("cddaccount:consulter_op_list")
                response = HttpResponse()
                response["HX-Redirect"] = v
                return response
            else:
                 send_otp=True
                 messages.error(request, "Token invalide", extra_tags="danger")


        except:
            traceback.print_exc()
            pass
    context={"obj":obj,"send_otp":send_otp,"ordre_ref":ordre_ref}
    return render(request, 'cddaccount/component.html', context)

@login_required()
def ajax_getsolde_cdd(request): #mantis 133 - ajouter un formulaire de consultation du solde d'un compte

    if  request.method == "GET":
        # recupere les montants - compte de depot
        try:
            compte_id = request.GET.get("compte", "0")
            gestion_id = request.GET.get("gestion", AnneeComptable.current_gestion().id)
            compteobj = CompteDepot.objects.get(id=int(compte_id))
            c= compute_all_balances_for_compte(compteobj,gestion_id,update=False)
            details=c["soldes"]
            ss=""
            for l in details:
                ss=ss+"{} {}  dispo:{}\n".format(l.get("name",""),l.get("nature",""),l.get("disponible",""))
            compte_depots_datas={"solde":int(c["disponible"]),"solde_invest":int(c["invest_balance"]["disponible"]),"solde_fonct":int(c["fonct_balance"]["disponible"]),"detail":ss}
	
            return JsonResponse(compte_depots_datas, status=200)
        except:
            traceback.print_exc()
            return JsonResponse({}, status=400)
    return JsonResponse({}, status=400)


@login_required()
def ajax_getcdd_current_gerant(request):  # mantis 133 - ajouter un formulaire de consultation du solde d'un compte

    if request.method == "GET":
        # recupere les montants - compte de depot
        try:
            compte_id = request.GET.get("compte", "0")
            compteobj = CompteDepot.objects.get(id=int(compte_id))
            x=compteobj.get_current_gerant()
            if x:
                compte_depots_datas={"name":x.full_name(),"phone":""}
                return JsonResponse(compte_depots_datas, status=200)
            else :return JsonResponse({}, status=400)
        except:
            traceback.print_exc()
            return JsonResponse({}, status=400)
    return JsonResponse({}, status=400)


@login_required()
def send_otp_sms_for_multicheque(request):
    # request should be ajax and method should be GET.
    obj=None
    phone=None
    owner=None
    send_otp = False
    if request.method == "POST":
        try:
            print(request.POST)
            querydict_data = request.POST.dict()
            print(querydict_data)
            _type = querydict_data.get("type")


            cheque_ref = querydict_data.get("reference")
            ordre_ref = querydict_data.get("matricule")

            if _type == BENEF_CHOICES.MANDATAIRE:
                mandataire_id = querydict_data.get("mandataire")
                mandataire = Mandataire.objects.get(id=mandataire_id)
                phone = mandataire.phone.as_e164
            elif _type == BENEF_CHOICES.GERANT:
                gerant_id = querydict_data.get("gerant")
                gerant = GerantCD.objects.get(id=gerant_id)
                phone=gerant.phone.as_e164
            if phone:
                otp = SimpleOtp()
                otp.phone = phone
                otp.generate_otp()
                op = OrdrePayment.objects.filter(vali_multi=cheque_ref).last()
                if op:
                    otp.message = op.get_otp_msg_all(otp.otp)
                otp.save()
                otp.send_otp()
                send_otp=True


        except:
            traceback.print_exc()
            pass
    context={"send_otp":send_otp,"ordre_ref":cheque_ref}
    return render(request, 'cddaccount/retraitcomponent.html', context)





@login_required()
def verify_otp_sms_for_multicheque(request):
    # request should be ajax and method should be GET.
    obj=None
    send_otp=True
    if request.method == "POST":
        try:
            otp = request.POST.get("otp")
            ordre_ref = request.POST.get("ordre")


            origin_otp = SimpleOtp.objects.filter(otp=otp).last()
            if origin_otp and origin_otp.verify(otp):
                regs = OrdrePayment.objects.filter(vali_multi=ordre_ref)
                for object in regs:
                    cheque = Cheque.objects.get(reference=object.cheque)
                    cheque.delivred = True
                    cheque.delivred_date = datetime.datetime.now()
                    # cheque.send_otp=False
                    cheque.save()
                    object.cheque_delivred = True
                    object.save()
                messages.success(request, "Cheques delivrés")
                v = reverse("cddaccount:consulter_op_list")
                response = HttpResponse()
                response["HX-Redirect"] = v
                return response



            else:
                 send_otp=True
                 messages.error(request, "Token invalide", extra_tags="danger")


        except:
            traceback.print_exc()
            pass
    context={"obj":obj,"send_otp":send_otp,"ordre_ref":ordre_ref}
    return render(request, 'cddaccount/component.html', context)