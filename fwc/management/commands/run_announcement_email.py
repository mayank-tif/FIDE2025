from django.core.management.base import BaseCommand
from fwc.announcement_email import send_pending_announcement_emails

class Command(BaseCommand):
    help = 'Run embedding scheduler'

    def handle(self, *args, **kwargs):
        send_pending_announcement_emails()
        self.stdout.write(self.style.SUCCESS('Scheduler executed successfully!'))