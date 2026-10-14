"""Пути приложения: ресурсы программы, данные пользователя, база, вложения, журнал.

Все данные пользователя лежат в одной папке (на Windows это %APPDATA%\\Faculty),
а не рядом с exe и не во временной папке PyInstaller, поэтому они переживают
перезапуск и обновление программы.
"""
import os
import sys
from pathlib import Path

APP_NAME = "Faculty"
DB_NAME = "employee_system.db"
DATA_DIR_ENV = "FACULTY_DATA_DIR"  # переопределение папки данных (нужно для тестов)


def resource_path(relative_path):
    """Файл, который поставляется вместе с программой (main.ui, style.qss)."""
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)


def user_data_dir():
    """Папка с данными пользователя; создаётся при первом обращении."""
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        path = Path(override)
    elif sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        path = Path(base) / APP_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path():
    return user_data_dir() / DB_NAME


def backups_dir():
    path = user_data_dir() / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_path():
    return user_data_dir() / "faculty.log"


def attachment_path(stored_path):
    """Полный путь к вложению по значению из БД.

    В БД хранится путь вида ``files/publications/3.pdf``: он считается от папки
    данных. Абсолютные пути (старые записи) возвращаются как есть.
    """
    if not stored_path:
        return None
    path = Path(stored_path)
    return path if path.is_absolute() else user_data_dir() / path


def legacy_db_candidates():
    """Где могла лежать база в старых версиях (рядом с программой или в рабочей папке)."""
    folders = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        folders.append(Path(meipass))
    if getattr(sys, "frozen", False):
        folders.append(Path(sys.executable).parent)
    folders.append(Path(os.path.dirname(os.path.abspath(__file__))))
    folders.append(Path.cwd())

    result = []
    for folder in folders:
        candidate = folder / DB_NAME
        if candidate not in result:
            result.append(candidate)
    return result


def find_legacy_db():
    """Старая база, которую можно перенести в папку данных при первом запуске."""
    target = db_path().resolve()
    for candidate in legacy_db_candidates():
        if candidate.is_file() and candidate.stat().st_size > 0 and candidate.resolve() != target:
            return candidate
    return None
