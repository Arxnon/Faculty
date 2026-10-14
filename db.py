"""Единая точка работы с SQLite: соединения, транзакции, миграции, резервные копии.

* каждое соединение включает внешние ключи (в SQLite они по умолчанию выключены);
* изменения выполняются в явных транзакциях: либо всё, либо ничего;
* схема версионируется через PRAGMA user_version и обновляется миграциями;
* перед миграцией и раз в день делается копия базы в папку backups.
"""
import logging
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import paths

log = logging.getLogger(__name__)

SCHEMA_VERSION = 2
BACKUPS_TO_KEEP = 20


class DatabaseCorruptedError(RuntimeError):
    """Файл базы повреждён или создан более новой версией программы."""


def _open():
    conn = sqlite3.connect(str(paths.db_path()), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection():
    """Соединение для чтения. Всегда закрывается."""
    conn = _open()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction():
    """Соединение с транзакцией: при исключении все изменения откатываются."""
    conn = _open()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.execute("COMMIT")
        except BaseException:
            try:
                conn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
    finally:
        conn.close()


# ======================
# МИГРАЦИИ
# ======================

def _table_exists(conn, table):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    return row is not None


def _table_columns(conn, table):
    return [row["name"] for row in conn.execute(f"PRAGMA table_info({table})")]


def _add_missing_columns(conn, table, columns):
    existing = set(_table_columns(conn, table))
    for name, sql_type in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")


def _migration_1(conn):
    """Базовые таблицы. Для баз старых версий только добавляет недостающие колонки."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fio TEXT NOT NULL,
            birth_date DATE,
            position TEXT,
            degree TEXT,
            rank TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS publications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            journal TEXT,
            level TEXT,
            pages INTEGER,
            publication_type TEXT,
            pub_date TEXT,
            file_path TEXT
        )
    """)
    _add_missing_columns(conn, "publications", {
        "publication_type": "TEXT",
        "pub_date": "TEXT",
        "file_path": "TEXT",
    })
    conn.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT,
            achievement TEXT,
            city TEXT,
            organization TEXT,
            work_name TEXT,
            ach_date TEXT,
            file_path TEXT
        )
    """)
    _add_missing_columns(conn, "achievements", {
        "event": "TEXT",
        "achievement": "TEXT",
        "city": "TEXT",
        "organization": "TEXT",
        "work_name": "TEXT",
        "ach_date": "TEXT",
        "file_path": "TEXT",
    })
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity TEXT,
            entity_id INTEGER,
            action TEXT,
            old_data TEXT,
            new_data TEXT,
            timestamp TEXT
        )
    """)


def _rebuild_link_table(conn, table, owner_table, owner_col):
    """Пересоздаёт таблицу связей с внешними ключами и уникальностью пары.

    Старые строки переносятся без дубликатов и без «висящих» ссылок на
    удалённых сотрудников, публикации или достижения.
    """
    new_table = f"{table}_new"
    conn.execute(f"DROP TABLE IF EXISTS {new_table}")
    conn.execute(f"""
        CREATE TABLE {new_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
            {owner_col} INTEGER NOT NULL REFERENCES {owner_table}(id) ON DELETE CASCADE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            UNIQUE ({owner_col}, employee_id)
        )
    """)

    if _table_exists(conn, table):
        rows = conn.execute(f"""
            SELECT l.{owner_col} AS owner_id, l.employee_id AS employee_id
            FROM {table} l
            JOIN employees e ON e.id = l.employee_id
            JOIN {owner_table} o ON o.id = l.{owner_col}
            ORDER BY l.{owner_col}, l.id
        """).fetchall()
        seen = set()
        counters = {}
        for row in rows:
            key = (row["owner_id"], row["employee_id"])
            if key in seen:
                continue
            seen.add(key)
            order = counters.get(row["owner_id"], 0)
            counters[row["owner_id"]] = order + 1
            conn.execute(
                f"INSERT INTO {new_table} ({owner_col}, employee_id, sort_order) VALUES (?, ?, ?)",
                (row["owner_id"], row["employee_id"], order),
            )
        conn.execute(f"DROP TABLE {table}")

    conn.execute(f"ALTER TABLE {new_table} RENAME TO {table}")
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_owner ON {table}({owner_col})")
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_employee ON {table}(employee_id)")


def _migration_2(conn):
    """Внешние ключи, уникальные связи, порядок авторов, индексы."""
    # В самых старых версиях сотрудник достижения хранился прямо в achievements.employee_id.
    if "employee_id" in _table_columns(conn, "achievements"):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS employee_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                achievement_id INTEGER
            )
        """)
        conn.execute("""
            INSERT INTO employee_achievements (employee_id, achievement_id)
            SELECT a.employee_id, a.id
            FROM achievements a
            WHERE a.employee_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM employee_achievements ea WHERE ea.achievement_id = a.id
              )
        """)

    _rebuild_link_table(conn, "employee_publications", "publications", "publication_id")
    _rebuild_link_table(conn, "employee_achievements", "achievements", "achievement_id")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_employees_fio ON employees(fio)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_publications_date ON publications(pub_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_achievements_date ON achievements(ach_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_entity ON history(entity, entity_id)")


MIGRATIONS = {
    1: _migration_1,
    2: _migration_2,
}


def _apply_migration(conn, version):
    conn.execute("BEGIN IMMEDIATE")
    try:
        MIGRATIONS[version](conn)
        conn.execute(f"PRAGMA user_version = {int(version)}")
        conn.execute("COMMIT")
    except BaseException:
        try:
            conn.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        raise


# ======================
# РЕЗЕРВНЫЕ КОПИИ
# ======================

def backup_database(label):
    """Копия базы в папке backups (через API SQLite, поэтому она целостная)."""
    source = paths.db_path()
    if not source.exists() or source.stat().st_size == 0:
        return None

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = paths.backups_dir() / f"employee_system_{stamp}_{label}.db"

    destination = sqlite3.connect(str(target))
    try:
        with connection() as src:
            src.backup(destination)
    finally:
        destination.close()

    _prune_backups()
    log.info("Резервная копия базы: %s", target)
    return target


def _prune_backups():
    backups = sorted(paths.backups_dir().glob("employee_system_*.db"))
    for old in backups[:-BACKUPS_TO_KEEP]:
        try:
            old.unlink()
        except OSError:
            log.warning("Не удалось удалить старую копию %s", old)


def _daily_backup():
    today = datetime.now().strftime("%Y%m%d")
    if any(p.name.startswith(f"employee_system_{today}") for p in paths.backups_dir().glob("*.db")):
        return
    backup_database("daily")


# ======================
# ИНИЦИАЛИЗАЦИЯ
# ======================

def _import_legacy_data():
    """Первый запуск: переносит базу и вложения из старого места, если они там есть."""
    legacy = paths.find_legacy_db()
    if legacy is None:
        return
    shutil.copy2(legacy, paths.db_path())
    log.info("Перенесена база из старого расположения: %s", legacy)

    legacy_files = legacy.parent / "files"
    new_files = paths.user_data_dir() / "files"
    if legacy_files.is_dir() and not new_files.exists():
        shutil.copytree(legacy_files, new_files)
        log.info("Перенесены вложения: %s", legacy_files)


def init_database():
    """Готовит базу к работе: создаёт или обновляет схему. Безопасно вызывать при каждом запуске."""
    if not paths.db_path().exists():
        _import_legacy_data()

    conn = _open()
    try:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise DatabaseCorruptedError(
                "База создана более новой версией программы. Обновите программу."
            )

        check = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if check != "ok":
            raise DatabaseCorruptedError(f"База данных повреждена: {check}")

        # У баз старых версий user_version равен 0, но данные в них уже есть.
        has_tables = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
        ).fetchone()[0] > 0
    finally:
        conn.close()

    if version < SCHEMA_VERSION:
        if has_tables:
            backup_database(f"before-v{SCHEMA_VERSION}")
        conn = _open()
        try:
            for target in range(version + 1, SCHEMA_VERSION + 1):
                _apply_migration(conn, target)
                log.info("Схема базы обновлена до версии %s", target)
            problems = conn.execute("PRAGMA foreign_key_check").fetchall()
            if problems:
                log.warning("После миграции остались нарушения внешних ключей: %s", len(problems))
        finally:
            conn.close()

    _daily_backup()
