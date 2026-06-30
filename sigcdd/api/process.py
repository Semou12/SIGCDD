import base64
import time
import traceback
import uuid
from datetime  import datetime
import six
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction, DatabaseError
from django_otp.oath import hotp

from helpers.exceptions import SigException
from helpers.models import OracleDatabase
from helpers.oracle_db import SOracleDB
import  logging
logger = logging.getLogger(__name__)
class AsterManager:

    @classmethod
    @transaction.atomic
    def create_a_compte(cls, user, **kwargs):
        try:
            datas = {}
            rows = [dict(kwargs)]
            sys_date = datetime.now()
            n = sys_date

            sequences = [(r["pk"], r["iban"], r["libelle_court"], r["libelle"], r["compte"], n,0) for r
                         in rows]
            sql = ('insert into TIM_COMPTE(numero, rib_complet, libn, libl, rib_court,date_insertion,niveau_traitement) '
                   'values(:1, :2,:3,:4,:5,:6,:7)')

            d = OracleDatabase.objects.filter(actif=True).last()
            if d:
                credentials = d.get_credentials()
                db = SOracleDB(
                    host=credentials["host"],
                    username=credentials["username"],
                    password=credentials["password"],
                    dbname=credentials["database"],
                    port=credentials["port"],
                    sid=credentials["sid"]
                )

                db.connect()
                with db.connection.cursor() as cursor:
                    cursor.executemany(sql, sequences, batcherrors=True)
                    db.connection.commit()
                    for error in cursor.getbatcherrors():
                        ex = SigException(message=error.message)
                        raise ex

                db.disconnect()
                # datas=res
                return {"status": settings.SUCCESS, "data": datas, "message": "Comptes depots ajoutes avec succès"}
            else:
                ex = SigException(message="Serveur base de données Aster non configuré")
                raise ex
        except:
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = SigException(message=c)
            raise ex

    @classmethod
    @transaction.atomic
    def send_cheque_aster(cls, user, **kwargs):
        try:

            datas = {}
            rows = [dict(kwargs)]
            logger.info(" Envoie cheque : {} par {} ".format(rows, user.username))



            sys_date = datetime.now()
            n=sys_date
            sequences = [(r["reference"],r["origin_reference"],r["compte"],r["montant"],r["journee"],r["type_op"],r["payment_mean"],"NOUVEAU",r["libelle"][0:44],n,0,r["sens"],r["type_compte"]) for r in rows]

            sql = ('insert into TIM_OPERATION(numero,reference_op, rib_complet,montant, date_pec, type_op, mode_paiement,status, observation,date_insertion,niveau_traitement,sens,typesolde) '
                   'values(:1, :2,:3,:4,:5,:6,:7,:8,:9,:10,:11,:12,:13)')
            d=OracleDatabase.objects.filter(actif=True).last()
            if d:
                credentials=d.get_credentials()
                db = SOracleDB(
                    host=credentials["host"],
                    username=credentials["username"],
                    password=credentials["password"],
                    dbname=credentials["database"],
                    port=credentials["port"],sid=credentials["sid"]
                )

                db.connect()
                with db.connection.cursor() as cursor:
                    cursor.executemany(sql, sequences,batcherrors = True)
                    db.connection.commit()
                    for error in cursor.getbatcherrors():
                        ex = SigException(message= error.message)
                        raise ex

                db.disconnect()
                return {"status": settings.SUCCESS, "data": datas,"message":"Comptes depots ajoutes avec succes"}
            else:
                ex = SigException(message="Serveur base de données Aster non configuré")
                raise ex
        except :
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = SigException(message=c)
            raise ex


    @classmethod
    @transaction.atomic
    def send_virement_aster(cls, user, **kwargs):
        try:
            datas = {}
            rows = [dict(kwargs)]
            logger.info(" Envoie virement : {} par {} ".format(rows, user.username))

            from datetime  import datetime
            sys_date = datetime.now()
            n=sys_date
            sequences = [(r["reference"],r["origin_reference"],r["compte"],r["montant"],r["journee"],r["type_op"],r["payment_mean"],"NOUVEAU",r["libelle"][0:44],n,r["compte_destination"],0,r["sens"],r["type_compte"]) for r in rows]

            sql = ('insert into TIM_OPERATION(numero,reference_op, rib_complet,montant, date_pec, type_op, mode_paiement,status, observation,date_insertion,iban,niveau_traitement,sens,typesolde) '
                   'values(:1, :2,:3,:4,:5,:6,:7,:8,:9,:10,:11,:12 ,:13,:14)')
            d=OracleDatabase.objects.filter(actif=True).last()
            if d:
                credentials=d.get_credentials()
                db = SOracleDB(
                    host=credentials["host"],
                    username=credentials["username"],
                    password=credentials["password"],
                    dbname=credentials["database"],
                    port=credentials["port"],sid=credentials["sid"]
                )

                db.connect()
                with db.connection.cursor() as cursor:
                    cursor.executemany(sql, sequences,batcherrors = True)
                    db.connection.commit()
                    for error in cursor.getbatcherrors():
                        ex = SigException(message= error.message)
                        raise ex

                db.disconnect()
                return {"status": settings.SUCCESS, "data": datas,"message":"Virements effectif"}
            else:
                ex = SigException(message="Serveur base de données Aster non configuré")
                raise ex
        except :
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = SigException(message=c)
            raise ex

    @classmethod
    @transaction.atomic
    def send_aviscredit_aster(cls, user, **kwargs):
        try:

            datas = {}
            rows = [dict(kwargs)]
            logger.info(" Envoie avis : {} par {} ".format(rows, user.username))

            from datetime  import datetime
            sys_date = datetime.now()

            n=sys_date#"TO_DATE('2015/05/15', 'YYYY/MM/DD')"
            sequences = [(r["reference"],r["origin_reference"],r["compte"],r["montant"],r["journee"],r["payment_mean"],r["payment_mean"],"NOUVEAU",r["libelle"],n,0) for r in rows]

            sql = ('insert into TIM_AVISCREDIT(numero,reference_op, rib_complet,montant, date_pec, type_op, mode_paiement,status, observation,date_insertion,niveau_traitement) '
                   'values(:1, :2,:3,:4,:5,:6,:7,:8,:9,:10,:11)')
            d=OracleDatabase.objects.filter(actif=True).last()
            if d:
                credentials=d.get_credentials()
                db = SOracleDB(
                    host=credentials["host"],
                    username=credentials["username"],
                    password=credentials["password"],
                    dbname=credentials["database"],
                    port=credentials["port"],sid=credentials["sid"]
                )

                db.connect()
                with db.connection.cursor() as cursor:
                    cursor.executemany(sql, sequences,batcherrors = True)
                    db.connection.commit()
                    for error in cursor.getbatcherrors():
                        ex = SigException(message= error.message)
                        raise ex

                db.disconnect()
                return {"status": settings.SUCCESS, "data": datas,"message":"Avis de credit fait avec succès"}
            else:
                ex = SigException(message="Serveur base de données Aster non configuré")
                raise ex
        except :
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = SigException(message=c)
            raise ex


    @classmethod
    @transaction.atomic
    def send_avisdebit_aster(cls, user, **kwargs):
        try:
            datas = {}
            rows = [dict(kwargs)]

            from datetime import datetime
            sys_date = datetime.now()

            n = sys_date
            sequences = [(r["reference"],r["origin_reference"], r["compte"], r["montant"], r["journee"], r["payment_mean"],
                          r["payment_mean"], "NOUVEAU", r["libelle"], n,0) for r in rows]

            sql = (
                'insert into TIM_AVISDEBIT(numero,reference_op, rib_complet,montant, date_pec, type_op, mode_paiement,status, observation,date_insertion,niveau_traitement) '
                'values(:1, :2,:3,:4,:5,:6,:7,:8,:9,:10,:11)')
            d = OracleDatabase.objects.filter(actif=True).last()
            if d:
                credentials = d.get_credentials()
                db = SOracleDB(
                    host=credentials["host"],
                    username=credentials["username"],
                    password=credentials["password"],
                    dbname=credentials["database"],
                    port=credentials["port"],sid=credentials["sid"]
                )

                db.connect()
                with db.connection.cursor() as cursor:
                    cursor.executemany(sql, sequences, batcherrors=True)
                    db.connection.commit()
                    for error in cursor.getbatcherrors():
                        ex = SigException(message=error.message)
                        raise ex

                db.disconnect()
                return {"status": settings.SUCCESS, "data": datas, "message": "Avis de debit fait avec succes"}
            else:
                ex = SigException(message="Serveur base de données Aster non configuré")
                raise ex
        except:
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = SigException(message=c)
            raise ex

    @classmethod
    @transaction.atomic
    def bulk_send_trx_aster(cls, user, rows):
        try:
            datas = {}
            if not rows:
                return {"status": settings.SUCCESS, "data": datas, "message": "Transactions envoyés"}

            logger.info(" Envoie cheque : {} par {} ".format(rows, user.username))

            from datetime  import datetime
            sys_date = datetime.now()
            n=sys_date
            sequences = [(r["reference"],r["origin_reference"],r["compte"],r["montant"],r["journee"],r["payment_mean"],r["payment_mean"],"NOUVEAU",r["libelle"],n,r["compte_destination"],0,r["sens"],r["type_compte"]) for r in rows]

            sql = ('insert into TIM_OPERATION(numero,reference_op, rib_complet,montant, date_pec, type_op, mode_paiement,status, observation,date_insertion,iban,niveau_traitement,sens,typesolde) '
                   'values(:1, :2,:3,:4,:5,:6,:7,:8,:9,:10,:11,:12,,:13,:14)')
            d=OracleDatabase.objects.filter(actif=True).last()
            if d:
                credentials=d.get_credentials()
                db = SOracleDB(
                    host=credentials["host"],
                    username=credentials["username"],
                    password=credentials["password"],
                    dbname=credentials["database"],
                    port=credentials["port"],sid=credentials["sid"]
                )

                db.connect()
                with db.connection.cursor() as cursor:
                    cursor.executemany(sql, sequences,batcherrors = True)
                    db.connection.commit()
                    for error in cursor.getbatcherrors():
                        ex = SigException(message= error.message)
                        raise ex

                db.disconnect()
                return {"status": settings.SUCCESS, "data": datas,"message":"Transactions envoyés"}
            else:
                ex = SigException(message="Serveur base de données Aster non configuré")
                raise ex
        except :
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = SigException(message=c)
            raise ex

    @classmethod
    @transaction.atomic
    def bulk_retrieve_trx_aster(cls, user, **kwargs):
        try:

            format = "%d-%m-%Y"
            from datetime import datetime,date


            if "journee_comptable" in kwargs:
                date_pec=datetime.strptime(kwargs["journee_comptable"], format)
            else:
                date_pec = date.today()


            d = OracleDatabase.objects.filter(actif=True).last()
            if d:
                credentials = d.get_credentials()
                db = SOracleDB(
                    host=credentials["host"],
                    username=credentials["username"],
                    password=credentials["password"],
                    dbname=credentials["database"],
                    port=credentials["port"],sid=credentials["sid"]
                )
                db.connect()
                sql = "select numero,reference_op,montant, date_pec, type_op, mode_paiement,status, observation,date_insertion,niveau_traitement from tim_operation where trunc(date_insertion) = :date_pec"
                with db.connection.cursor() as cursor:
                    cursor.execute(sql, date_pec=date_pec)
                    datas = cursor.fetchall()
                db.disconnect()
                return {"status": settings.SUCCESS, "data": datas, "message": "Liste des trx demandes"}
            else:
                ex = SigException(message="Serveur base de données Aster non configuré")
                raise ex

            return {"status": settings.SUCCESS, "data": {}}
        except:
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = Exception()
            ex.message = c
            raise ex

    @classmethod
    @transaction.atomic
    def retrieve_trx_aster(cls, user, **kwargs):
        try:
            numero=kwargs["numero"]
            d = OracleDatabase.objects.filter(actif=True).last()
            if d:
                credentials = d.get_credentials()
                db = SOracleDB(
                    host=credentials["host"],
                    username=credentials["username"],
                    password=credentials["password"],
                    dbname=credentials["database"],
                    port=credentials["port"], sid=credentials["sid"]
                )
                db.connect()
                sql = "select numero,reference_op,montant, date_pec, type_op, mode_paiement,status, observation,date_insertion,niveau_traitement from tim_operation where numero = :numero"
                with db.connection.cursor() as cursor:
                    cursor.execute(sql, numero=numero)
                    datas = cursor.fetchall()
                db.disconnect()
                return {"status": settings.SUCCESS, "data": datas, "message": "Liste des trx demandes"}
            else:
                ex = SigException(message="Serveur base de données Aster non configuré")
                raise ex
        except:
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = Exception()
            ex.message = c
            raise ex

    @classmethod
    @transaction.atomic
    def bulk_detailvirement_aster(cls, user, rows):
        try:

            datas = {}
            if not rows:
                return {"status": settings.SUCCESS, "data": datas, "message": "Transactions envoyés"}
            from datetime  import datetime
            sys_date = datetime.now()
            n=sys_date
            logger.info(" Envoie details vr : {} par {} ".format(rows, user.username))

            sequences = [(r["reference"],r["num_interne_ordre"],create_date(r["date_ordre"]),create_date(r["date_payement"]),r["type_operation"], r["libelle"][0:50],r["montant"],r["poste"],r["cpt_aster"],r["type_rib_donneur"],r["rib_donneur"],r["nom_donneur"],r["adresse_donneur"],r["type_rib_beneficiaire"],r["rib_beneficiaire"],r["nom_beneficiaire"],r["adresse_beneficiaire"],r["sens"],r["source"],n,r["traite"]) for r in rows]

            sql = (
                'insert into TIM_DETAIL_VIR(REFERENCE,NUM_INTERNE_ORDRE,DATE_ORDRE,DATE_PAY,TYPE_OPERATION,LIBELLE,MONTANT,POSTE,CPT_ASTER,TYPE_RIB_DONNEUR, RIB_DONNEUR, NOM_DONNEUR, ADRESSE_DONNEUR,TYPE_RIB_BENEFICIAIRE, RIB_BENEFICIAIRE,NOM_BENEFICIAIRE,ADRESSE_BENEFICIAIRE,SENS,SOURCE,DATE_INSERTION,TRAITE)'
                'values(:1, :2,:3,:4,:5,:6,:7,:8,:9,:10,:11,:12,:13,:14,:15,:16,:17,:18,:19,:20,:21)')
            d=OracleDatabase.objects.filter(actif=True).last()
            if d:
                credentials=d.get_credentials()
                db = SOracleDB(
                    host=credentials["host"],
                    username=credentials["username"],
                    password=credentials["password"],
                    dbname=credentials["database"],
                    port=credentials["port"],sid=credentials["sid"]
                )

                db.connect()
                with db.connection.cursor() as cursor:
                    cursor.executemany(sql, sequences,batcherrors = True)
                    db.connection.commit()
                    for error in cursor.getbatcherrors():
                        ex = SigException(message= error.message)
                        raise ex

                db.disconnect()
                return {"status": settings.SUCCESS, "data": datas,"message":"Transactions envoyés"}
            else:
                ex = SigException(message="Serveur base de données Aster non configuré")
                raise ex
        except :
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = SigException(message=c)
            raise ex

    @classmethod
    @transaction.atomic
    def bulk_retrieve_detailvrm_table_aster(cls, user, **kwargs):
        try:

            format = "%d-%m-%Y"
            from datetime import datetime,date
            date_payement = date.today()#datetime.strptime(kwargs["journee_comptable"], format)

            traite = 1

            d = OracleDatabase.objects.filter(actif=True).last()
            if d:
                credentials = d.get_credentials()
                db = SOracleDB(
                    host=credentials["host"],
                    username=credentials["username"],
                    password=credentials["password"],
                    dbname=credentials["database"],
                    port=credentials["port"],sid=credentials["sid"]
                )
                db.connect()
                sql = "select reference,traite,message_aster,date_traitement from TIM_DETAIL_VIR where trunc(date_pay) = :date_payement  and traite=:traite"
                with db.connection.cursor() as cursor:
                    cursor.execute(sql, date_payement=date_payement, traite=traite)
                    datas = cursor.fetchall()
                db.disconnect()
                return {"status": settings.SUCCESS, "data": datas, "message": "Liste des trx demandes"}
            else:
                ex = SigException(message="Serveur base de données Aster non configuré")
                raise ex
            datas = {}
            return {"status": settings.SUCCESS, "data": datas}
        except:
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = Exception()
            ex.message = c
            raise ex



    @classmethod
    @transaction.atomic
    def bulk_retrieve_detailvrm_aster(cls, user, **kwargs):
        try:

            format = "%d-%m-%Y"
            from datetime import datetime,date

            if "journee_comptable" in kwargs:
                date_payement = datetime.strptime(kwargs["journee_comptable"], format)
            else:
                date_payement = date.today()

            #traite = 1

            d = OracleDatabase.objects.filter(actif=True).last()
            if d:
                credentials = d.get_credentials()
                db = SOracleDB(
                    host=credentials["host"],
                    username=credentials["username"],
                    password=credentials["password"],
                    dbname=credentials["database"],
                    port=credentials["port"],sid=credentials["sid"]
                )
                db.connect()
                sql = "select reference,traite,date_pay,cpt_aster from VIEW_DETAIL_VIR where trunc(date_pay) = :date_payement"
                with db.connection.cursor() as cursor:
                    cursor.execute(sql, date_payement=date_payement)
                    datas = cursor.fetchall()
                db.disconnect()
                return {"status": settings.SUCCESS, "data": datas, "message": "Liste des trx demandes"}
            else:
                ex = SigException(message="Serveur base de données Aster non configuré")
                raise ex
            datas = {}
            return {"status": settings.SUCCESS, "data": datas}
        except:
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = Exception()
            ex.message = c
            raise ex

    @classmethod
    @transaction.atomic
    def bulk_retrieve_chequescanne_aster(cls, user, **kwargs):
        try:
            format = "%d-%m-%Y"
            from datetime import datetime,date
            date_traitement =  date.today() #datetime.strptime(kwargs["journee_comptable"], format)
            traite = 1
            d = OracleDatabase.objects.filter(actif=True).last()
            if d:
                credentials = d.get_credentials()
                db = SOracleDB(
                    host=credentials["host"],
                    username=credentials["username"],
                    password=credentials["password"],
                    dbname=credentials["database"],
                    port=credentials["port"],sid=credentials["sid"]
                )
                db.connect()
                s="TYPEOPERATION,REFERENCE1,AGENCEREMETTANTE,CODEPLACE,NOMBENEF,ADRESSEBENEF,NUMEROCHEQUE,DATECHEQUE,BANQUETIRE,AGENCETIRE,NUMEROCOMPTETIRE,CLERIBTIRE,MONTANTCHEQUE,CODECHEQUE,REJET,TRAITE,SENS,POSTE"

                sql = "select {} from VIEW_DETAIL_CHQR where trunc(DATECHEQUE) = :DATECHEQUE".format(s,)
                with db.connection.cursor() as cursor:
                    cursor.execute(sql, DATECHEQUE=date_traitement)
                    datas = cursor.fetchall()
                db.disconnect()
                return {"status": settings.SUCCESS, "data": datas, "message": "Liste des cheques scannes demandes"}
            else:
                ex = SigException(message="Serveur base de données Aster non configuré")
                raise ex
            datas = {}
            return {"status": settings.SUCCESS, "data": datas}
        except:
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = Exception()
            ex.message = c
            raise ex




    @classmethod
    @transaction.atomic
    def bulk_retrieve_aviscredit_aster(cls, user, **kwargs):
        try:
            format = "%d-%m-%Y"
            from datetime import datetime,date
            datas={}

            date_pec= date.today()

            status="TRAITE"

            d = OracleDatabase.objects.filter(actif=True).last()
            if d:
                credentials = d.get_credentials()
                db = SOracleDB(
                    host=credentials["host"],
                    username=credentials["username"],
                    password=credentials["password"],
                    dbname=credentials["database"],
                    port=credentials["port"],sid=credentials["sid"]
                )
                db.connect()
                colums= "NUMERO,RIB_COMPLET,MONTANT,DATE_PEC ,TYPE_OP,MODE_PAIEMENT,OBSERVATION, STATUS,MESSAGE_ASTER,DATE_INSERTION,DATE_TRAITEMENT,IBAN , REFERENCE_OP,TYPESOLDE"
                sql = "select {} from TIM_AVISCREDIT where trunc(date_insertion) = :date_pec".format(colums,)


                with db.connection.cursor() as cursor:
                    cursor.execute(sql, date_pec=date_pec)
                    datas = cursor.fetchall()
                    #print(datas)

                db.disconnect()
                return {"status": settings.SUCCESS, "data": datas, "message": "Liste des trx demandes"}
            else:
                ex = SigException(message="Serveur base de données Aster non configuré")
                raise ex
            datas = {}
            return {"status": settings.SUCCESS, "data": datas}
        except:
            traceback.print_exc()
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = Exception()
            ex.message = c
            raise ex



    @classmethod
    @transaction.atomic
    def bulk_retrieve_avisdebit_aster(cls, user, **kwargs):
        try:
            format = "%d-%m-%Y"
            from datetime import datetime,date
            datas={}

            date_pec= date.today()#datetime.strptime(kwargs["journee_comptable"], format)

            status="TRAITE"

            d = OracleDatabase.objects.filter(actif=True).last()
            if d:
                credentials = d.get_credentials()
                db = SOracleDB(
                    host=credentials["host"],
                    username=credentials["username"],
                    password=credentials["password"],
                    dbname=credentials["database"],
                    port=credentials["port"],sid=credentials["sid"]
                )
                db.connect()
                colums= "NUMERO,RIB_COMPLET,MONTANT,DATE_PEC ,TYPE_OP,MODE_PAIEMENT,OBSERVATION, STATUS,MESSAGE_ASTER,DATE_INSERTION,DATE_TRAITEMENT,IBAN , REFERENCE_OP,TYPESOLDE"
                sql = "select {} from TIM_AVISDEBIT where trunc(date_insertion) = :date_pec".format(colums,)

                with db.connection.cursor() as cursor:
                    cursor.execute(sql, date_pec=date_pec)
                    datas = cursor.fetchall()
                db.disconnect()
                return {"status": settings.SUCCESS, "data": datas, "message": "Liste des trx demandes"}
            else:
                ex = SigException(message="Serveur base de données Aster non configuré")
                raise ex
            datas = {}
            return {"status": settings.SUCCESS, "data": datas}
        except:
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = Exception()
            ex.message = c
            raise ex





    @classmethod
    @transaction.atomic
    def bulk_delete_detailvr_aster(cls, user, **kwargs):
        try:
            bind_values=kwargs["numeros"]
            date_payement=kwargs["date_payment"]

            d = OracleDatabase.objects.filter(actif=True).last()
            if d:
                credentials = d.get_credentials()
                db = SOracleDB(
                    host=credentials["host"],
                    username=credentials["username"],
                    password=credentials["password"],
                    dbname=credentials["database"],
                    port=credentials["port"], sid=credentials["sid"]
                )
                db.connect()

                bind_names = [":" + str(i + 1) for i in range(len(bind_values))]
                bind_values.append(date_payement)
                sql = "delete from TIM_DETAIL_VIR where reference in (%s) and trunc(date_pay) = :date_pec" % (",".join(bind_names))
                with db.connection.cursor() as cursor:
                    cursor.execute(sql, bind_values)
                    #cursor.executemany("delete from TIM_DETAIL_VIR where reference = :1",[(i,) for i in bind_values],arraydmlrowcounts=True)
                    #row_counts = cursor.getarraydmlrowcounts()
                    #print(row_counts)

                db.connection.commit()
                db.disconnect()
                return {"status": settings.SUCCESS,  "message": "Liste des trx demandes"}
            else:
                ex = SigException(message="Serveur base de données Aster non configuré")
                raise ex
        except:
            c = traceback.format_exc(limit=0)
            c = c.replace("Traceback (most recent call last):", "")
            ex = Exception()
            ex.message = c
            raise ex




def create_date(date_str):
    from datetime import datetime
    date_object = datetime.strptime(date_str, '%d/%m/%Y').date()
    return date_object