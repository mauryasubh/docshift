"""
python manage.py setup_site
Fixes the common SITE_ID / DoesNotExist issue for allauth OAuth.
Run this once after first migrate.
"""
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = 'Update the default Site domain to 127.0.0.1:8000 for local OAuth'

    def add_arguments(self, parser):
        parser.add_argument('--domain', default='127.0.0.1:8000',
                            help='Domain to set (default: 127.0.0.1:8000)')
        parser.add_argument('--name', default='DocShift',
                            help='Display name (default: DocShift)')

    def handle(self, *args, **options):
        domain = options['domain']
        name   = options['name']
        site, created = Site.objects.update_or_create(
            id=1,
            defaults={'domain': domain, 'name': name},
        )
        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{action} Site id=1: domain={site.domain} name={site.name}'
        ))
        self.stdout.write(
            '\nNow go to Django Admin → Social Accounts → Social Applications\n'
            'and make sure:\n'
            '  1. Provider ID = "github" or "google" (exact lowercase)\n'
            f'  2. Site "{domain}" is in Chosen sites\n'
        )
