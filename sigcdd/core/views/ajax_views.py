from django.http import JsonResponse
from core.models import Direction,Structure
def load_directions_by_ministere(request):
    # request should be ajax and method should be GET.
    if  request.method == "GET":
        # get the nick name from the client side.
        try:
            id = request.GET.get("id", "0")
            if id == 0:
                return JsonResponse({"valid": True, "directions": []}, status=200)
            ascs = Direction.objects.filter(ministere_id=int(id))

            d=[{"id":asc.pk,"name":asc.name} for asc in ascs]
            return JsonResponse({"valid": True,"directions":d}, status=200)
        except:
            return JsonResponse({}, status=400)
    return JsonResponse({}, status=400)





def load_structure_by_ministere(request):
    # request should be ajax and method should be GET.
    if  request.method == "GET":
        # get the nick name from the client side.
        try:
            id = request.GET.get("id", "0")
            if id == 0:
                return JsonResponse({"valid": True, "structures": []}, status=200)
            ascs = Structure.objects.filter(ministere_id=int(id))

            d=[{"id":asc.pk,"name":asc.name} for asc in ascs]
            return JsonResponse({"valid": True,"structures":d}, status=200)
        except:
            return JsonResponse({}, status=400)
    return JsonResponse({}, status=400)