import shlex
import subprocess
import sys

from django.core.management.base import BaseCommand
from django.utils import autoreload
app_name="sigcdd"


def restart_celery():
    #celery_worker_cmd = "celery -A django_celery_example worker"
    celery_worker_cmd="celery -A {}  worker --beat --scheduler django_celery_beat.schedulers:DatabaseScheduler --loglevel=info".format(app_name)
    cmd = f'pkill -f "{celery_worker_cmd}"'
    if sys.platform == "win32":
        cmd = "taskkill /f /t /im celery.exe"

    subprocess.call(shlex.split(cmd))
    subprocess.call(shlex.split(f"{celery_worker_cmd} --loglevel=info"))

class Command(BaseCommand):
    def handle(self, *args, **options):
        print("Starting celery worker with autoreload...")
        autoreload.run_with_reloader(restart_celery)
