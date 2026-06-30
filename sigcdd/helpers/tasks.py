from __future__ import absolute_import

import logging
import traceback

from celery import shared_task

logger = logging.getLogger(__name__)
from django.conf import settings

@shared_task
def add(x, y):
    return x + y


import requests
@shared_task(serializer="json")
def async_http_send(url, headers, payload):
    import json
    logger.info(
        "==== post url {} ====".format(
            url,
        )
    )
    try:
        response = requests.request(
            "POST", url, headers=headers, data=json.dumps(payload),timeout=60
        )
        logger.info(
            "==== response  statut {} ====".format(
                response.status_code,
            )
        )
        logger.info(response.text)
        d = {"http_code": response.status_code, "message": response.text}

    except:
        #traceback.print_exc()
        d = {"http_code": response.status_code, "message": response.text}

    return d



from django.core.mail import EmailMessage


@shared_task()
def async_send_email(subject,content,to_list):
    msg_html = content
    sender = settings.DEFAULT_FROM_EMAIL
    msg = EmailMessage(subject, msg_html, from_email=sender,to=to_list)

    return msg.send(fail_silently=False)



@shared_task()
def async_send_sms_old(phone,content):
    from helpers.tresorsmsgateway import send_sms
    try:
        send_sms(phone,content)
    except:
        pass
    d = {"http_code": 200, "message": "sennt"}
    return d




@shared_task()
def async_send_sms(phone,content,config_processor):
    from helpers.tresorsmsgateway import send_sms
    try:
        send_sms(phone,content,config_processor)
    except:
        pass
    d = {"http_code": 200, "message": "sennt"}
    return d