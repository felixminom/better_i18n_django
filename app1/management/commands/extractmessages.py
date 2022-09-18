import argparse

from django.core.management.base import BaseCommand

from polib import POFile

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
    """Find tagged entries with a given project name and create a new po file"""

    help = (
        'This management command creates a new PO file from tagged entries'
        'Usage: python manage.py poprojectwrite -p jdoe_20220101 -l de'
    )

    def add_arguments(self, parser):
        parser.formatter_class = argparse.ArgumentDefaultsHelpFormatter

        parser.add_argument(
            '--force',
            required=False,
            action='store_true',
            default=False,
            help='Force saving when project po file exists',
        )

        parser.add_argument(
            '-l',
            '--locale',
            required=True,
            help='Tag only po files in a specific locale, e.g. de',
        )

        parser.add_argument(
            '-p',
            '--project-name',
            required=True,
            help='Po Project name, e.g. jdoe_20220101',
        )

    def handle(self, *args, **options):
        self.project_name = options.get('project_name')
        self.locale = get_supported_locale(options.get('locale'))
        self.force = options.get('force')
        self.project_comment = get_po_project_comment(self.project_name)

        for app in ALL_APPS:
            po_file = get_po_file_path(app.path, self.locale)
            po_project_file = get_po_file_path(app.path, self.locale, self.project_name)
            self.process_po_file(po_file, po_project_file)
        self.process_po_file(
            get_po_file_path_general_locale(self.locale),
            get_po_file_path_general_locale(self.locale, self.project_name),
        )

    def process_po_file(self, po_file, project_po_file):
        if po_file.exists():
            self.stdout.write(self.style.SUCCESS(f'Processing: {po_file}'))
            if project_po_file.exists() and not self.force:
                self.stdout.write(
                    f'Project po file exists: {project_po_file}, '
                    f'please use -f to override'
                )
                return False

            po = safe_read_pofile(po_file)
            project_po = POFile()
            project_po.metadata = po.metadata

            for entry in po:
                if has_project(entry, self.project_comment):
                    project_po.append(entry)

            if len(project_po):
                project_po.save(project_po_file)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Wrote {len(project_po)} entries to {project_po_file}'
                    )
                )
