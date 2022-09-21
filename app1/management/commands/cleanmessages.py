import argparse

from django.core.management.base import BaseCommand

from .._helpers import (
    ALL_APPS,
    get_po_file_path,
    get_po_file_path_general_locale,
    get_po_project_comment,
    get_supported_locale,
    has_project,
    safe_read_pofile,
)


class Command(BaseCommand):
    """Remove project name tags and delete project po file"""

    help = (
        'This management command removes po project tags'
        'Usage: python manage.py cleanmessages -l de -p jdoe_20210101'
    )

    def add_arguments(self, parser):
        parser.formatter_class = argparse.ArgumentDefaultsHelpFormatter

        parser.add_argument(
            '--dry-run',
            required=False,
            action='store_true',
            default=False,
            help='Dry run, will not save changes',
        )

        parser.add_argument(
            '-l',
            '--locale',
            required=True,
            help='Tag only po files in a specific a locale, e.g. ja',
        )

        parser.add_argument(
            '-p',
            '--project-name',
            required=True,
            help='Po Project name, e.g. jdoe_20210101',
        )

    def handle(self, *args, **options):
        self.project_name = options.get('project_name')
        self.locale = get_supported_locale(options.get('locale'))
        self.dry_run = options.get('dry_run')
        self.project_comment = get_po_project_comment(self.project_name)

        for app in ALL_APPS:
            po_file = get_po_file_path(app.path, self.locale)
            self.process_po_file(po_file)

            po_project_file = get_po_file_path(app.path, self.locale, self.project_name)
            self.delete_po_project_file(po_project_file)
        self.process_po_file(get_po_file_path_general_locale(self.locale))
        self.delete_po_project_file(
            get_po_file_path_general_locale(self.locale, self.project_name)
        )

    def process_po_file(self, po_file):
        if po_file.exists():
            self.stdout.write(self.style.SUCCESS(f'Processing: {po_file}'))
            count = 0

            po = safe_read_pofile(po_file)
            for entry in po:
                if has_project(entry, self.project_comment):
                    self.remove_project(entry)
                    count += 1

            if not self.dry_run and count:
                po.save()
                self.stdout.write(self.style.SUCCESS(f'Removed {count} occurrence(s)'))

    def delete_po_project_file(self, po_file):
        if not self.dry_run and po_file.exists():
            po_file.unlink()
            self.stdout.write(self.style.SUCCESS(f'Removed project file: {po_file}'))

    def remove_project(self, entry):
        """Remove all occurrences of project name from comment"""
        comments = entry.comment.splitlines()
        updated_comments = list(filter(self.project_comment.__ne__, comments))

        if len(updated_comments):
            entry.comment = '\n'.join(updated_comments).strip()
        else:
            entry.comment = None

        return entry
