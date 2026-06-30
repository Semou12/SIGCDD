from __future__ import absolute_import
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def async_add(x,y):
    logger.info("res:{}".format(x+y))
    return x+y

