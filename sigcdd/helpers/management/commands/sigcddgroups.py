from django.core.management.base import BaseCommand
from django.utils import autoreload
app_name="sigcdd"
from django.contrib.auth.models import Group
from helpers.models import Role


class Command(BaseCommand):
    help = 'get or create default group'
    def create_group(self):
        for name in Role.names:
            Group.objects.get_or_create(name=name)

    def handle(self, *args, **options):
        print("get or create default group")
        autoreload.run_with_reloader(self.create_group)
