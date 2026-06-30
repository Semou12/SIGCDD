from __future__ import absolute_import

import logging
import traceback

from celery import shared_task

logger = logging.getLogger(__name__)
from django.conf import settings

from cddaccount.process import  CddProcessManager
@shared_task
def add(x, y):
    return x + y

@shared_task(serializer="json")
def async_batch_upload_aster_send(payload):
	logger.info("Envoie trx vers aster de type  : {}".format(payload, ))
	CddProcessManager.bulk_send_trx_aster(None,payload)

@shared_task(serializer="json")
def async_batch_download_trx_aster_send(payload):
	logger.info("Recuperation trx depuis aster de type  : {}".format(payload, ))
	CddProcessManager.bulk_retrieve_trx_aster(None,payload)



@shared_task(serializer="json")
def async_batch_download_detailvr_aster_send(payload):
	logger.info("Recuperation detail vr depuis aster de type  : {}".format(payload, ))
	CddProcessManager.bulk_retrieve_detailvrm_aster(None,payload)


@shared_task(serializer="json")
def async_batch_download_aviscredit_aster_send(payload):
	logger.info("Recuperation avis credit depuis aster de type  : {}".format(payload, ))
	CddProcessManager.bulk_retrieve_aviscredit_aster(None,payload)



@shared_task(serializer="json")
def async_batch_download_avisdebit_aster_send(payload):
	logger.info("Recuperation avis debit depuis aster de type  : {}".format(payload, ))
	CddProcessManager.bulk_retrieve_avisdebit_aster(None,payload)

from cddaccount.chargement_process import chargement_items_excel_file,generate_and_send_sitdisp,CompteDepot
@shared_task()
def async_loading_data(id):
	print("----- fdfdfdff----")
	logger.info("chargement fichier : {}")
	chargement_items_excel_file(id)
	print("----- fisn ----")



@shared_task()
def async_generate_and_send_sitdisp(user,list_mail):
	generate_and_send_sitdisp(user,list_mail)



@shared_task()
def async_compute_balance(list_compte):
	print("----- debut reinitialisationn sollde----")
	comptes=CompteDepot.objects.filter(id__in=list_compte)
	from cddaccount.models import compute_all_balances_for_compte
	for compte in comptes:
		compute_all_balances_for_compte(compte)
	print("----- fin reinitialisationn sollde----")



from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.core.files.base import ContentFile
@shared_task
def generate_pdf_task(html):
	result = BytesIO()
	pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), result)
	if not pdf.err:
		return ContentFile(result.getvalue(), 'report.pdf')
	else:
		return None