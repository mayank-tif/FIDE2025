from django.core.management.base import BaseCommand
from fwc.transport_email import *

class Command(BaseCommand):
    help = 'Run embedding scheduler'

    def handle(self, *args, **kwargs):
        send_transportation_email_scheduler()
        self.stdout.write(self.style.SUCCESS('Scheduler executed successfully!'))