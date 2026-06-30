# -*- coding: utf-8 -*-
import traceback

from django.conf import settings
import logging
logger = logging.getLogger(__name__)
import requests

#SMS_ACCOUNT_SID = getattr(settings, "TRESOR_ACCOUNT_SID", None)
#SMS_AUTH_TOKEN = getattr(settings, "TRESOR_TOKEN", None)
#url = getattr(settings, "TRESOR_GATEWAY_URL")


def send_sms(num, msg,config_processor):

    url= config_processor["url"]
    SMS_ACCOUNT_SID = config_processor["SMS_ACCOUNT_SID"]
    SMS_AUTH_TOKEN = config_processor["SMS_AUTH_TOKEN"]
    subject = config_processor["subject"]

    if num.startswith("+"):
        num=num.replace("+","")
    if num.startswith("00"):
        num = num

    elif num.startswith("77") or num.startswith("78") or num.startswith(
            "76") or num.startswith("70"):
        num = "00221%s" % (num,)
    else:
        num = "%s" % (num,)
    payload = {'application':SMS_ACCOUNT_SID, 'subject': subject,'recipient':num, 'content': msg}
    headers={'ApiKey':SMS_AUTH_TOKEN}

    try:
        #response = session.send(prep_req)
        response = requests.get(url,params=payload,headers=headers)
    except Exception as e:
        pass
