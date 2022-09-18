from pathlib import Path
from typing import List

from django.apps import AppConfig, apps
from django.conf import settings
from django.core.management import CommandError
from django.utils.translation import to_locale

from polib import POEntry, POFile, pofile

ALL_APPS: List[AppConfig] = [
    app
    for app in apps.get_app_configs()
    if 'django' not in app.name
]

SUPPORTED_LANGUAGES: List[str] = [
    code for (code, _) in settings.LANGUAGES if code != settings.LANGUAGE_CODE
]


def get_supported_locale(locale: str) -> str:
    if locale in SUPPORTED_LANGUAGES:
        return locale
    else:
        raise CommandError(f"Unsupported locale: [{locale}]")


def get_po_project_comment(project_name: str) -> str:
    return f'project={project_name}'


def get_po_file_path(app_path: str, locale: str, project_name: str = None) -> Path:
    po_file_name = validate_project_name(project_name)
    return Path(app_path) / 'locale' / to_locale(locale) / 'LC_MESSAGES' / po_file_name


def get_po_file_path_general_locale(locale: str, project_name: str = None) -> Path:
    po_file_name = validate_project_name(project_name)
    return Path() / 'locale' / to_locale(locale) / 'LC_MESSAGES' / po_file_name


def validate_project_name(project_name: str = None) -> str:
    if project_name:
        po_file_name = f'po_project_{project_name}.po'
    else:
        po_file_name = 'django.po'
    return po_file_name


def safe_read_pofile(path: str) -> POFile:
    try:
        return pofile(path)
    except (IOError, ValueError) as error:
        raise CommandError(error)


def has_project(entry: POEntry, project_name_comment: str) -> bool:
    return project_name_comment in entry.comment


def add_project(entry: POEntry, project_name_comment: str) -> POEntry:
    entry.comment = f"{project_name_comment}"

    return entry