from __future__ import absolute_import

import logging
import traceback

from celery import shared_task

logger = logging.getLogger(__name__)
from django.conf import settings

from bankcheck.process import  CheckProcessManager

@shared_task(serializer="json")
def async_batch_download_chequescanne(payload):
	logger.info("Recuperation cheques scannes depuis aster de type  : {}".format(payload, ))
	CheckProcessManager.create_chequescannes(None,payload)