import json_log_formatter
from django.utils import timezone
import logging
import json
import re
class CustomisedJSONFormatter(json_log_formatter.VerboseJSONFormatter):
    def json_record(self, message: str, extra: dict, record: logging.LogRecord) -> dict:
        if 'asctime' in extra:
            extra['asctime'] = extra.asctime
        extra['message']=message
        extra['level'] = record.levelname
        extra['name'] = record.name
        extra['created'] = record.created
        extra['funcName'] = "{}.{}:{}".format(record.name,record.funcName,record.lineno)
        if 'time' not in extra:
            extra['time'] = timezone.now()
        if record.exc_info:
            extra['exc_info'] = self.formatException(record.exc_info)

        return extra




def add_replacer(match_obj):
    key = str(match_obj.group(1))
    v = match_obj.group(2)

    if key in ["cardNumber", "cardnumber"]:
        v = maskify(v)
    else:
        v = "*" * len(v)
    s = '"{}":"{}"'.format(key, v)
    return s

def maskify(cc):
    new_string = ''
    if len(cc) > 4:
        new_string += '*' * (len(cc) - 4) + cc[-4:]
    else:
        return cc
    return new_string


class SensitiveDataFilter(logging.Filter):
    """Demonstrate how to filter sensitive data:"""

    def filter(self, record):
        # The call signature matches string interpolation: args can be a tuple or a lone dict
        if isinstance(record.args, dict):
            record.args = self.sanitize_dict(record.args)
        else:
            record.args = tuple(self.sanitize_dict(i) for i in record.args)

        return True

    @staticmethod
    def sanitize_dict(d):
        sensitiveKeys = ["cvv", "pan", "password", "cardNumber", "clientID","expiredate","cardnumber"]
        if isinstance(d, dict):
            st = json.dumps(d)
            for key in sensitiveKeys:
                st = re.sub("[\'\"]({})[\'\"]:.?[\'\"]([a-zA-Z0-9]+/*[a-zA-Z0-9]+)[\'\"]".format(key, ),add_replacer, st)
            jre = json.loads(st)
            return jre
        else: return d




