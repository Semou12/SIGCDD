import logging

from django.conf import settings
from django.http import QueryDict
from drf_yasg.utils import swagger_auto_schema
from rest_framework import authentication, permissions
from rest_framework import renderers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .process import AsterManager

logger = logging.getLogger(__name__)

from oauth2_provider.contrib.rest_framework import OAuth2Authentication

from .serializer import *

class DefSerializer(serializers.Serializer):
    trx = serializers.CharField(required=True,  max_length=100)

class IsAgentInstitution(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        user = request.user
        groups = user.groups.values_list('name', flat=True)
        return user and user.is_authenticated and  settings.RECEVEUR_GROUP in groups

class  IsGuichetUser(permissions.IsAuthenticated):

    def has_permission(self, request, view):
        user = request.user
        groups = user.groups.values_list('name', flat=True)
        return user and user.is_authenticated and  settings.GUICHETIER_GROUP in groups


class PlainTextRenderer(renderers.BaseRenderer):
    media_type = 'text/plain'
    format = 'txt'
    def render(self, data, media_type=None, renderer_context=None):
        return data.encode(self.charset)


def _call_method(function, request):
    result = {"status": "error", "message": "unknow error"}
    if request.method == 'GET':
        result= {"message": "Methode non authorise "}
        return Response(result, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    elif request.method == 'POST':
        data = request.data
        #data["wsgi_ip"] = request.META['REMOTE_ADDR']
        #data["remote_addr"] = request.META['REMOTE_ADDR']
        #logger.info("{} : INCOMMING DATA : {}".format(function.__name__.upper(),data))
        if data :
            result = {"status": "error", "message": "unknow error"}
            try:
                result = function(request.user, **data)
            except Exception as e:
                import traceback
                traceback.print_exc()
                if hasattr(e,"message"):
                    logger.debug(e.message)
                    result = {"status": "error", "message": e.message}
                else : result = {"status": "error", "message": "unknow error"}

            finally:

                logger.info("{} : SENDING DATA : {}".format(function.__name__.upper(), result))
            #return Response(result, status=status.HTTP_201_CREATED)
        else:
            result = {"status": "error", "message": "empty data"}
            #return Response({"erreur": "empty data"}, status=status.HTTP_400_BAD_REQUEST)


        serializer = TrxResponseSerializer(data=result)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors},status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data, status=status.HTTP_201_CREATED)



def test_function(user,**kwargs):
    raise Exception("Ping reussi")
    #return kwargs

from rest_framework.throttling import UserRateThrottle
class User3MinRateThrottle(UserRateThrottle):
    rate = '3/day'
    scope = 'day'


class BaseAPIViewSet(viewsets.GenericViewSet):
    authentication_classes = (OAuth2Authentication,authentication.BasicAuthentication)
    permission_classes = (permissions.IsAuthenticated,)
    renderer_classes = (renderers.JSONRenderer,)

    serializer_class = DefSerializer

    @action(detail=False,methods=['GET'],url_path="ping")
    def test1(self, request, *args, **kwargs):
        return _call_method(test_function, request)

    def call_backend_process(self,function,user, data):
        if data:
            result = {"status": "error", "message": "unknow error"}
            try:
                result = function(user, **data)
            except Exception as e:
                import traceback
                traceback.print_exc()
                if hasattr(e, "message"):
                    logger.debug(e.message)
                    result = {"status": "error", "message": e.message}
                else:
                    result = {"status": "error", "message": "unknow error"}
            finally:

                logger.info("{} : SENDING DATA : {}".format(function.__name__.upper(), result))
            # return Response(result, status=status.HTTP_201_CREATED)
        else:
            result = {"status": "error", "message": "empty data"}
            # return Response({"erreur": "empty data"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = TrxResponseSerializer(data=result)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.data, status=status.HTTP_200_CREATED)


    def call_generic_closure(self,fonction,request,*args, **kwargs):
        if request.method == 'POST':
            data=request.data
            serializer = self.get_serializer(data=data)
        elif request.method == 'GET':
            data=kwargs
            serializer = self.get_serializer(data=data)
        else:
            data = request.data
            serializer = self.get_serializer(data=data)

        serializer.is_valid(raise_exception=True)
        return self.call_backend_process(fonction, request.user,data)

class AsterAPIViewSet(BaseAPIViewSet):
    #lookup_field = "reference"
    serializer_classes = {
        'comptedepot': CompteDepotSerializer,
        'opcheque': ChequeSerializer,"avisdebit":AvisDebitSerializer,
        "default": DefSerializer, "getcheque": TrxInfosSerializer,
        "getvirement": TrxInfosSerializer, "virement": VirementSerializer, "aviscredit": AvisCreditSerializer
    }

    def get_serializer_class(self):
        if self.action in list(self.serializer_classes.keys()):
            return self.serializer_classes[self.action]
        return self.serializer_classes['default']

    @swagger_auto_schema(responses={200: TrxResponseSerializer})
    @action(methods=['POST'], url_path="newcomptedepot", detail=False)
    def comptedepot(self, request, *args, **kwargs):
        return self.call_generic_closure(AsterManager.create_a_compte, request,*args, **kwargs)

    @swagger_auto_schema(responses={200: TrxResponseSerializer})
    @action(methods=['POST'], url_path="opcheque", detail=False)
    def opcheque(self, request, *args, **kwargs):
        return self.call_generic_closure(AsterManager.send_cheque_aster, request)

    @swagger_auto_schema(responses={200: TrxResponseSerializer})
    @action(methods=['POST'], url_path="virement", detail=False)
    def virement(self, request, *args, **kwargs):
        return self.call_generic_closure(AsterManager.send_virement_aster, request)

    @swagger_auto_schema(responses={200: TrxResponseSerializer})
    @action(methods=['POST'], url_path="aviscredit", detail=False)
    def aviscredit(self, request, *args, **kwargs):
        return self.call_generic_closure(AsterManager.send_aviscredit_aster, request)

    @swagger_auto_schema(responses={200: TrxResponseSerializer})
    @action(methods=['POST'], url_path="avisdebit", detail=False)
    def avisdebit(self, request, *args, **kwargs):
        return self.call_generic_closure(AsterManager.send_avisdebit_aster, request)

    #@action(methods=['GET'], url_path="getcheque", detail=False)

    @swagger_auto_schema(responses={200: TrxResponseSerializer,500:"Internal serveur",400:"Bad request"})
    def getcheque(self, request, reference):
        kwargs={"reference":reference}
        return self.call_generic_closure(AsterManager.retrieve_trx_aster, request,**kwargs)


    #@action(methods=['POST'], url_path="getvirement", detail=False)
    @swagger_auto_schema(responses={200: TrxResponseSerializer})
    def getvirement(self, request, reference):
        kwargs = {"reference": reference}
        return self.call_generic_closure(AsterManager.create_enrolement, request,**kwargs)
