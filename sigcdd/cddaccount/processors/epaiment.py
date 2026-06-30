
import base64

import time,logging
import traceback
import uuid
from django.db import IntegrityError, transaction, DatabaseError
import six
from django.conf import settings
import json

from helpers.exceptions import SigException

BASE_URL = getattr(settings, "EPAIEMENT_BASE_URL", None)
USERNAME= getattr(settings, "EPAIEMENT_USERNAME", None)
PASSWORD = getattr(settings, "EPAIEMENT_PASSWORD", None)
APP_CODE = getattr(settings, "EPAIEMENT_APPCODE", None)
X_USER_ID = getattr(settings, "EPAIEMENT_X_USER_ID", None)


CLIENT_ID= getattr(settings, "EPAIEMENT_CLIENT_ID", None)
CLIENT_SECRET = getattr(settings, "EPAIEMENT_CLIENT_SECRET", None)

import requests
#SMS_AUTH_TOKEN = getattr(settings, "TRESOR_TOKEN", None)
logger = logging.getLogger(__name__)


class EpaiementManager:

	@classmethod
	@transaction.atomic
	def create_op(cls, **kwargs):
		kwargs.update({"applicationCode": APP_CODE})
		url = "{}integration/ordre-paiement".format(BASE_URL, )
		headers = {
			'accept': 'application/json',
			'Content-Type': 'application/json',
			"X-USER-ID":X_USER_ID
		}
		try:
			token =cls.get_token()

			headers.update({"Authorization": 'Bearer {}'.format(token,)})

			payload = json.dumps(kwargs)
			cert_path = "/certif/gd_bundle-g2.crt" #"/etc/nginx/certs/certificate.pem"
			response = requests.request("PUT", url, headers=headers, data=payload, verify=cert_path)
			logger.info(response.text)
			status_code=response.status_code
			if status_code==200 or status_code==201:
				c=response.json()
				if "code" in c:
					code=c["code"]
					if code=="0":
						return response.json()
					else:
						msg=c["message"]
						ex = SigException(message=msg)
						ex.message = msg
						raise ex
				else :
					msg=c["message"]
					ex = SigException(message=msg)
					ex.message = msg
					raise ex
			else:
				ex = SigException(message=response.text)
				ex.message = response.text
				raise ex
		except:
			c = traceback.format_exc(limit=0)
			c = c.replace("Traceback (most recent call last):", "")
			ex = SigException(message=c)
			ex.message = c
			raise ex


	@classmethod
	@transaction.atomic
	def get_trx_op(cls, user, **kwargs):
		kwargs.update({"applicationCode": APP_CODE})
		url = "{}/ordre-status".format(BASE_URL, )
		headers = {
			'accept': 'application/json',
			'Content-Type': 'application/json'
		}
		try:
			payload = json.dumps(kwargs)
			cert_path = cert_path = "/certif/gd_bundle-g2.crt" # "/etc/nginx/certs/certificate.pem"
			response = requests.request("PUT", url, headers=headers, data=payload, verify=cert_path)
			logger.info(response.text)
			status_code=response.status_code
			if status_code==200 or status_code==201:
				return response.json()
			else:
				ex = SigException(message=response.text)
				ex.message = response.text
				raise ex
		except:
			c = traceback.format_exc(limit=0)
			c = c.replace("Traceback (most recent call last):", "")
			ex = SigException(message=c)
			ex.message = c
			raise ex






	@classmethod
	@transaction.atomic
	def get_token(cls):
		url = "{}account/oauth".format(BASE_URL, )
		from requests.auth import HTTPBasicAuth

		payload = {'username': CLIENT_ID,
		           'password': CLIENT_SECRET,
		           'grant_type': 'password'}
		try:
			cert_path = "/certif/gd_bundle-g2.crt" #"/etc/nginx/certs/certificate.pem"
			response = requests.request("POST", url,  data=payload,auth = HTTPBasicAuth(USERNAME, PASSWORD), verify=cert_path)
			logger.info(response.text)
			status_code=response.status_code
			if status_code==200 or status_code==201:
				c=response.json()
				if "access_token" in c:
					return c["access_token"]
			else:
				ex = SigException(message=response.text)
				ex.message = response.text
				raise ex
		except:
			c = traceback.format_exc(limit=0)
			c = c.replace("Traceback (most recent call last):", "")
			ex = SigException(message=c)
			ex.message = c
			raise ex
