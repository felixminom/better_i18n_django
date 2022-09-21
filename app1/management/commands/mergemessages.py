import csv

from os import path

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import to_locale

from .._helpers import (
    get_po_project_comment,
    get_supported_locale,
    has_project,
    safe_read_pofile,
)


class Command(BaseCommand):
    '''This management command import po projects.'''

    help = (
        'This management command will merge back translated strings located in the'
        'PO file created with extractmessages.'
        'Usage: python manage.py mergemessages -a app1 -l de -p jdoe_20220101 path/to/translated/PO/file'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '-a',
            '--app',
            required=True,
            help='The Django app to import the PO project into',
        )

        parser.add_argument(
            '-l',
            '--locale',
            required=True,
            help='The locale of the PO project (e.g. ja)',
        )

        parser.add_argument(
            '-p',
            '--project',
            required=True,
            help='The project name of the PO project',
        )

        parser.add_argument(
            'file',
            help='The input file to import the PO project',
        )

        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            required=False,
            help=(
                'Run the management command without writing any changes to the django.po'
                ' files'
            ),
        )

    def handle(self, *args, **options):
        self.app = options.get('app')
        self.locale = get_supported_locale(options.get('locale'))
        self.project = options.get('project')
        self.file = options.get('file')
        self.is_dry = options.get('dry_run')
        self.locale_name = to_locale(self.locale)
        self.django_po_path = (
            f"{self.app}/locale/{self.locale_name}/LC_MESSAGES/django.po"
        )
        self.django_po_path_general_locale = (
            f"locale/{self.locale_name}/LC_MESSAGES/django.po"
        )

        self.affected_pages_templates = []
        self.affected_pages = []

        self.validate_folder_locale()
        self.validate_app()
        self.validate_locale()
        self.validate_django_po()
        self.validate_file()

        self.stdout.write("Importing PO project...")
        self.write_project_to_django_po()

        self.stdout.write(self.style.SUCCESS('Import successfull! 🎉'))

    def validate_folder_locale(self):
        if self.app == 'locale':
            self.django_po_path = self.django_po_path_general_locale

    def validate_app(self):
        if not path.exists(f"{self.app}/"):
            raise CommandError(f"The app '{self.app}' does not exist!")

    def validate_locale(self):
        if self.app == 'locale':
            test_path = f"locale/{self.locale_name}/"
        else:
            test_path = f"{self.app}/locale/{self.locale_name}/"
        if not path.exists(test_path):
            raise CommandError(
                f"The locale '{self.locale}' does not exist in the app '{self.app}'"
            )

    def validate_django_po(self):
        if not path.exists(self.django_po_path):
            raise CommandError(
                f"The app '{self.app}' does not contain a django.po translation file"
            )

    def validate_file(self):
        if not path.exists(self.file):
            raise CommandError(f"Unable to find the specified file [{self.file}]")

    def write_project_to_django_po(self):
        tag = get_po_project_comment(self.project)
        django_po = safe_read_pofile(self.django_po_path)

        for project_entry in safe_read_pofile(self.file):
            if tag not in project_entry.comment:
                self.show_warning(
                    f"Entry [{project_entry.msgid}] is not part of this project, so it"
                    " will be ignored!"
                )
            else:
                for entry in django_po:
                    matches_id = entry.msgid == project_entry.msgid

                    if has_project(entry, tag) and matches_id:
                        if entry.msgstr:
                            self.show_warning(
                                f"Overwriting current translation of [{entry.msgid}]"
                            )
                        self.get_entry_ocurrences(entry)
                        entry.msgstr = project_entry.msgstr

        if not self.is_dry:
            self.stdout.write('Writing changes to django.po file...')
            django_po.save()
        else:
            self.stdout.write(
                'Dry-run complete. No changes were written to the django.po file'
            )

    def show_warning(self, message):
        self.stdout.write(self.style.WARNING(f"⚠️  WARNING: {message}"))

    def get_entry_ocurrences(self, entry):
        for file, _ in entry.occurrences:
            if file not in self.affected_pages_templates:
                self.affected_pages_templates.append(file)
