from os import path

from django.core.management.commands import makemessages
from django.utils.translation import to_locale

from polib import POFile

from .._helpers import (
    ALL_APPS,
    SUPPORTED_LANGUAGES,
    get_po_file_path,
    get_supported_locale,
    safe_read_pofile,
)


class Command(makemessages.Command):
    '''Creates messages for all locales languages for every app'''

    def add_arguments(self, parser):
        super().add_arguments(parser)

        parser.add_argument(
            '--allow-obsolete',
            action='store_true',
            default=False,
            required=False,
            help='Does not remove obsolete message strings',
        )

    def handle(self, *args, **options):
        valid_locales = map(get_supported_locale, options["locale"])

        self.locales = (
            list(map(to_locale, valid_locales)) if valid_locales else SUPPORTED_LANGUAGES
        )

        self.stdout.write("Making messages for all apps")

        options["no_obsolete"] = not options["allow_obsolete"]

        if options["all"]:
            self.locales = list(map(to_locale, SUPPORTED_LANGUAGES))
            self.all = False
            
        options["locale"] = self.locales

        backup = self.backup_comments()

        super().handle(*args, **options)

        self.restore_comments(backup)
        #self.post_process_po_files()

        self.stdout.write(self.style.SUCCESS("All Done! 🎉"))

    def post_process_po_files(self):
            print(app.path)
            for locale in self.locales:
                po_path = get_po_file_path(app.path, locale)

                if path.exists(po_path):
                    self.stdout.write(f"Processing [{locale}] for [{app.label}]:")

                    django_po = safe_read_pofile(po_path)
                    django_po = self.remove_fuzzy_translations(django_po)

                    self.stdout.write(' • Writing changes the django.po file...')
                    django_po.save()

                    self.stdout.write(' • Checking for possible duplicates...')
                    self.check_for_duplicates(po_path)

                    self.stdout.write(' • Done!')
                    self.stdout.write('')

    def remove_fuzzy_translations(self, django_po):
        self.stdout.write(" • Removing fuzzy translations...")

        for fuzzy_entry in django_po.fuzzy_entries():
            fuzzy_entry.previous_msgid = None
            fuzzy_entry.previous_msgctxt = None
            fuzzy_entry.flags.remove('fuzzy')
            fuzzy_entry.msgstr = ''

        return django_po

    def check_for_duplicates(self, po_path):
        django_po = safe_read_pofile(po_path)

        for (i, entry) in enumerate(django_po):
            next_index = i + 1
            duplicates = []

            for compare in django_po[next_index:]:
                has_same_id = entry.msgid.strip() == compare.msgid.strip()
                has_same_context = entry.msgctxt == compare.msgctxt

                if has_same_id and has_same_context:
                    duplicates.append(compare.linenum)

            if duplicates:
                self.stdout.write(
                    self.style.WARNING(
                        f"    ⚠️  Possible duplicate(s) of line "
                        f"[{entry.linenum}]: {duplicates}"
                    )
                )

    def backup_comments(self):
        backup = {}

        for app in ALL_APPS:
            print(type(app))
            for locale in self.locales:
                po_path = get_po_file_path(app.path, locale)

                if path.exists(po_path):
                    django_po = safe_read_pofile(po_path)
                    temp_po = POFile()

                    for entry in django_po:
                        if entry.comment:
                            temp_po.append(entry)

                    backup[po_path] = temp_po

        self.stdout.write('PO project comments backed up')
        return backup

    def restore_comments(self, backup):
        for po_path, backup_po in backup.items():
            django_po = safe_read_pofile(po_path)

            for backup_entry in backup_po:
                po_entry = django_po.find(backup_entry.msgid)

                if po_entry:
                    po_entry.comment = backup_entry.comment

            django_po.save()

        self.stdout.write('PO project comments restored')