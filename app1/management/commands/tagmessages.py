import argparse
import time

from django.core.management.base import BaseCommand, CommandError

from .._helpers import (
    ALL_APPS,
    add_project,
    get_po_file_path,
    get_po_file_path_general_locale,
    get_po_project_comment,
    get_supported_locale,
    safe_read_pofile,
)


class Command(BaseCommand):
    """Tag untranslated entries with a project name"""

    help = (
        'This management command is the first step to create an independent PO file'
        'that can be sent for parallel transalation. When run, this command will add'
        'a project name to entries that need translation.'
        'Usage: python manage.py tagmessages -l de -p'
    )

    def add_arguments(self, parser):
        parser.formatter_class = argparse.ArgumentDefaultsHelpFormatter

        parser.add_argument(
            '--dry-run',
            required=False,
            action='store_true',
            default=False,
            help=(
                'Helpful to see which entries will be tagged in each django.po file, '
                'before making and actual update.'
            ),
        )

        parser.add_argument(
            '-f',
            '--file-name',
            required=False,
            help=(
                'Search all untranslated and fuzzy entries by file name.'
                'If not provided all entries (untranslated and fuzzy) will be tagged'
                'e.g. app1/templates/index.html .'
                'Note that the path starts with the app name.'
                'Also if you want to loop over a specific app you could use this param '
                'in this way, -f app1'
            ),
        )

        parser.add_argument(
            '-l',
            '--locale',
            required=True,
            help='Tag only po files in a specific a locale, e.g. de',
        )

        parser.add_argument(
            '-p',
            '--project-name',
            required=False,
            default=self.generate_project_name(),
            help='Project name to tag po files, e.g. jdoe_20220101',
        )

    def handle(self, *args, **options):

        self.project_name = options.get('project_name')
        self.dry_run = options.get('dry_run')
        self.locale = get_supported_locale(options.get('locale'))
        self.project_comment = get_po_project_comment(self.project_name)

        self.tag_po_files(options.get('file_name'))

        if any(self.any_file_changed):
            self.stdout.write(
                self.style.SUCCESS(f'All done, your tag is: {self.project_name}')
            )

    def tag_po_files(self, file_name):
        if self.dry_run:
            self.stdout.write(
                self.style.NOTICE("Running in --dry-run mode, files won't be affected")
            )

        if file_name:
            self.process_by_filename(file_name)
        else:
            self.process_all_apps()

    def process_by_filename(self, file_name):
        app = self.validate_app_in_filename(file_name)

        if app:
            po_file = get_po_file_path(app.path, self.locale)
            self.process_file(po_file, process_with_filename=True)
        else:
            self.stdout.write(
                self.style.ERROR(
                    f'{self.app_name} is not a valid app.\n'
                    'Remember that the filename must start with the app directory'
                )
            )

    def process_all_apps(self):
        for app in ALL_APPS:
            po_file = get_po_file_path(app.path, self.locale)
            self.process_file(po_file)
        self.process_file(get_po_file_path_general_locale(self.locale))

    def process_file(self, po_file, process_with_filename=False):
        if po_file.exists():
            self.stdout.write(self.style.SUCCESS(f'Processing: {po_file}'))
            po = safe_read_pofile(po_file)

            self.any_file_changed = []
            self.tagged_entries = 0
            self.is_file_changed = False

            if process_with_filename:
                self.tag_by_filename(po)
            else:
                self.tag_all_untranslated_strings(po)

            if self.is_file_changed and not self.dry_run:
                po.save()
                self.any_file_changed.append(True)

            if not self.dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'A total of {self.tagged_entries} entries were tagged'
                    )
                )

        else:
            # Even if the app is provided there could be some cases
            # that the po file for the given locale doesn't exits.
            # Or the app doesn't have po files at all
            if process_with_filename:
                raise CommandError(f'Not found: {po_file}')

    def tag_by_filename(self, po):
        for entry in po:
            f = self.file_name
            if self.is_tagable(entry) and any(f in file for file, _ in entry.occurrences):
                self.tag_entry(entry)

    def tag_all_untranslated_strings(self, po):
        for entry in po:
            if self.is_tagable(entry):
                self.tag_entry(entry)

    def tag_entry(self, entry):
        if self.dry_run:
            self.stdout.write(f'{self.tagged_entries}> {entry.msgid}')
            self.tagged_entries += 1
        else:
            entry = add_project(entry, self.project_comment)
            self.is_file_changed = True
            self.tagged_entries += 1

    def is_tagable(self, entry):
        """Check if a specific entry can have a project_name comment. We check
        if it's fuzzy or untranslated, that it's a non obsolete entry and that
        it does NOT contain a previous project comment"""
        if (
            (entry.fuzzy or not entry.translated())
            and not entry.obsolete
            and not entry.comment
        ):
            return True

        return False

    def generate_project_name(self):
        return f'auto_{int(time.time())}'

    def validate_app_in_filename(self, file_name):
        self.file_name = file_name
        self.app_name = self.file_name.split('/')[0]

        return next((app for app in ALL_APPS if app.name == self.app_name), None)
