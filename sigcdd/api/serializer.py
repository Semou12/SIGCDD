from rest_framework import serializers


class CompteDepotSerializer(serializers.Serializer):
    compte = serializers.CharField(max_length=16, required=True)
    iban = serializers.CharField(max_length=25, required=True)
    libelle = serializers.CharField(max_length=290, required=True)

    libelle_court = serializers.CharField(max_length=128, required=True)
    poste_comptable = serializers.CharField(max_length=10, required=True)
    date = serializers.DateField(format="%d-%m-%Y", input_formats=['%d-%m-%Y', 'iso-8601'],required=False)



class TransactionSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=120, required=True)
    libelle = serializers.CharField(max_length=250, required=True)
    montant = serializers.DecimalField(required=True,max_digits=13,decimal_places=0,min_value=0)
    compte = serializers.CharField(max_length=24, required=True)
    poste_comptable = serializers.CharField(max_length=10, required=True)
    journee_comptable = serializers.DateField(format="%d-%m-%Y", input_formats=['%d-%m-%Y', 'iso-8601'])
    gestion = serializers.IntegerField( required=True,min_value=2012)

class ChequeSerializer(TransactionSerializer):
    cheque = serializers.CharField(max_length=40, required=True)

class VirementSerializer(TransactionSerializer):
    iban = serializers.CharField(max_length=40, required=True)


class AvisCreditSerializer(TransactionSerializer):
    pass


class AvisDebitSerializer(TransactionSerializer):
    pass


class TrxResponseSerializer(serializers.Serializer):
    status =serializers.CharField(max_length=40, required=True)
    #code = serializers.CharField(max_length=40, required=True)
    message = serializers.CharField(max_length=500, required=False)
    data = serializers.JSONField(required=False)

class TrxInfosSerializer(serializers.Serializer):
    reference =serializers.CharField(max_length=40, required=True)


class Response500Serializer(serializers.Serializer):
    status =serializers.CharField(max_length=40, required=True)
    #code = serializers.CharField(max_length=40, required=True)
    message = serializers.CharField(max_length=500, required=False)
    data = serializers.JSONField(required=False)



