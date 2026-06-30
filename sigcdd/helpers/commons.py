__author__ = "csi"
import json
import logging
import random
import string
import time
import traceback

import requests
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django_otp.oath import TOTP, hotp, totp
from django_otp.util import random_hex, hex_validator



OTP_STEP = 300  # 5*60s (5min for otp validation)
OTP_STEP_IN_MIN = 5

OTP_STEP = OTP_STEP_IN_MIN * 60  # 5*60s (5min for otp validation)

logger = logging.getLogger(__name__)

class Singleton:
    def __init__(self, cls):
        self._cls = cls

    def Instance(self):
        try:
            return self._instance
        except AttributeError:
            self._instance = self._cls()
            return self._instance

    def __call__(self):
        raise TypeError("Singletons must be accessed through `Instance()`.")

    def __instancecheck__(self, inst):
        return isinstance(inst, self._cls)



class CommonsUtils:
    @classmethod
    def default_key(cls):
        return random_hex(20)

    @classmethod
    def key_validator(cls,value):
        return hex_validator()(value)

    @classmethod
    def totp_generator(cls,key, step):
        totp_obj = TOTP(bytes(key, "utf-8"), step=step)
        return totp_obj

@Singleton
class CommonHelper:


    def default_key(self):
        return random_hex(20)

    def key_validator(self,value):
        return hex_validator()(value)

    def get_totp_generator(self,key, step):
        totp_obj = TOTP(bytes(key, "utf-8"), step=step)
        return totp_obj

    def format_digits(self,digits, lenght):
        size = lenght - len(digits)
        if size == 0:
            return digits
        else:
            code = "".join("0" for x in range(size))
            return "{}{}".format(code, digits)

    def generate_otp_code(self,str_key="12345678900987654321"):
        str_key = "12345678900987654321"
        key = bytes(str_key, "utf-8")
        counter = int(time.time() * 1000)
        code = self.format_digits(str(hotp(key, counter, digits=7)), 7)
        return code

    def generate_otp_code_with_timestamp(self,timestamp, str_key="12345678900987654321"):
        # str_key = '12345678900987654321'
        key = bytes(str_key, "utf-8")
        counter = timestamp  # int(time.time() * 1000)
        code = self.format_digits(str(hotp(key, counter, digits=7)), 7)
        return code

    def is_totp_valid(self,otp, str_key="12345678900987654321"):
        # key = bytes(str_key, "utf-8")
        # totp = TOTP(key)
        # return totp.verify(otp)
        return True

    def generate_totp_code_with_timestamp(
            self,timestamp, step=30, delta=10, str_key="12345678900987654321"
    ):
        # str_key = '12345678900987654321'
        key = bytes(str_key, "utf-8")
        t = int(timestamp)  # int(time.time() * 1000)

        code = str(totp(key, step=step, t0=t, digits=6, drift=5))
        return code


    #@classmethod
    def generate_code(
        self,
        app_ame,
        model_name,
        field_name,
        size=3,
        chars=None,
        prefix=None,
        suffix=None,
    ):
        if chars is None:
            chars = string.ascii_uppercase + string.digits
        code = "".join(random.choice(chars) for x in range(size))
        # Ensure code does not aleady exist
        if prefix is not None:
            code = prefix + code
        if suffix is not None:
            code = code + suffix
        try:
            model = apps.get_model(app_ame, model_name)
            kwargs = {field_name: code}
            model.objects.get(**kwargs)
        except model.DoesNotExist:
            return code

    @classmethod
    def create_model_permission(cls, app_name, model_name, code, perm_name):
        model = apps.get_model(app_name, model_name)
        content_type = ContentType.objects.get_for_model(model)
        verbose_name = model._meta.verbose_name.title()
        name = "%s %s" % (perm_name, verbose_name)

        code_name = "%s_%s" % (code, model_name.lower())

        permission = Permission.objects.get_or_create(
            codename=code_name, content_type=content_type, defaults={"name": name}
        )


    @classmethod
    def add_permission_to_defaults(cls, app_name, code, perm_name):
        for model in apps.get_app_config(app_label=app_name).models:
            cls.create_model_permission(app_name, model, code, perm_name)

    @classmethod
    def app_create_defaults_perms(cls, app_name):
        codes_names = ["add", "change", "delete", "view"]
        for code_name in codes_names:
            perm_name = "Can {}".format(
                code_name,
            )
            cls.add_permission_to_defaults(app_name, code_name, perm_name)

    @classmethod
    def strip_accents_unicode(cls, s):
        import unicodedata
        normalized = unicodedata.normalize("NFKD", s)
        if normalized == s:
            return s
        else:
            return "".join([c for c in normalized if not unicodedata.combining(c)])

    @classmethod
    def send_html_email(cls,subject, content, to_list):
        try:
            print("envoi email")
            async_send_email.delay(subject, content, to_list)
        except:
            traceback.print_exc()
            pass

    @classmethod
    def send_sms(cls, destinataire, message, credentials):
        logger.info(message)
        logger.info(destinataire)
        _phone = destinataire
        send_sms_gateway( _phone,message, credentials)

    def remove_prefix(self,text, prefix):
        if text.startswith(prefix):
            return text[len(prefix):]
        return text  # or whatever

    def getmax_value(self,refs, prefix_matricule):
        d = 0
        for item in refs:
            if item.startswith(prefix_matricule):
                nu = self.remove_prefix(
                    item, prefix_matricule
                )  # item.removeprefix(prefix_matricule)
                nu = nu.lstrip("0")
                v = int(nu)
                if v > d:
                    d = v
        return d



from .tasks import async_http_send, async_send_email, async_send_sms



def send_sms_gateway(to, message, configs):

    try:
        async_send_sms.delay(to,message,configs)
    except:
        print("tste")
        pass



def notify_badge(sender,recipient,target,message):
    from notifications.signals import notify
    from helpers.models import Category
    notify.send(sender=sender, recipient=recipient, verb=message,target=Category.objects.get(name=target))




