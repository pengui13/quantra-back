from django.core.management.base import BaseCommand
from assets.models import Asset



class Command(BaseCommand):
    def handle(self, *args, **options):
        Asset.objects.all().delete()