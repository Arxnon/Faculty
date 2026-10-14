"""Тесты слоя данных. Запуск из корня проекта: python -m unittest discover -s tests -v

PyQt5 не нужен: проверяются paths, db, database и history_db.
"""
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database  # noqa: E402
import db  # noqa: E402
import history_db  # noqa: E402
import paths  # noqa: E402


class TempDataDirTestCase(unittest.TestCase):
    """Каждый тест работает в своей пустой папке данных."""

    def setUp(self):
        self.data_dir = tempfile.mkdtemp(prefix="faculty-test-")
        patcher = mock.patch.dict(os.environ, {paths.DATA_DIR_ENV: self.data_dir})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutil.rmtree, self.data_dir, ignore_errors=True)


class FreshDatabaseTests(TempDataDirTestCase):
    def setUp(self):
        super().setUp()
        db.init_database()

    def add_employee(self, fio, **kwargs):
        return database.add_employee(
            fio, kwargs.get("birth", "1980-01-01"), "Доцент", "К.т.н.", "Доцент"
        )

    def add_publication(self, title, author_ids=()):
        return database.add_publication(title, "Журнал", "РИНЦ", 10, "Статья", "2025-05-01", author_ids)

    # --- схема ---

    def test_schema_version_and_pragma(self):
        with db.connection() as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_init_is_idempotent(self):
        employee_id = self.add_employee("Иванов Иван")
        db.init_database()
        db.init_database()
        self.assertEqual(database.get_employee(employee_id)["fio"], "Иванов Иван")

    def test_fresh_database_gets_daily_backup(self):
        names = [p.name for p in paths.backups_dir().glob("*.db")]
        self.assertEqual(len(names), 1)
        self.assertIn("daily", names[0])

    def test_prune_keeps_latest_backups(self):
        for index in range(30):
            (paths.backups_dir() / f"employee_system_20200101-{index:06d}_x.db").write_bytes(b"x")
        db._prune_backups()
        self.assertEqual(len(list(paths.backups_dir().glob("employee_system_*.db"))), db.BACKUPS_TO_KEEP)

    # --- сотрудники ---

    def test_add_employee_returns_id(self):
        employee_id = self.add_employee("Иванов Иван")
        self.assertIsInstance(employee_id, int)
        self.assertEqual(database.get_employee(employee_id)["fio"], "Иванов Иван")

    def test_duplicate_fio_is_rejected_ignoring_case_and_spaces(self):
        self.add_employee("Иванов Иван")
        with self.assertRaises(database.DuplicateEmployeeError):
            self.add_employee("  иванов   иван ")

    def test_update_to_duplicate_fio_is_rejected_but_own_fio_is_fine(self):
        first = self.add_employee("Иванов Иван")
        second = self.add_employee("Петров Пётр")
        with self.assertRaises(database.DuplicateEmployeeError):
            database.update_employee(second, "иванов иван", "1980-01-01", "", "", "")
        self.assertTrue(database.update_employee(first, "Иванов Иван", "1981-02-02", "Профессор", "", ""))
        self.assertEqual(database.get_employee(first)["position"], "Профессор")

    def test_update_missing_employee_returns_false(self):
        self.assertFalse(database.update_employee(12345, "Никто", "", "", "", ""))
        self.assertFalse(database.delete_employee_by_id(12345))

    def test_search_ignores_case_for_cyrillic(self):
        self.add_employee("Иванов Иван")
        self.add_employee("Петров Пётр")
        found = database.search_employees_by_fio("ИВАН")
        self.assertEqual([row["fio"] for row in found], ["Иванов Иван"])
        self.assertEqual(database.search_employees_by_fio("иванов  ив")[0]["fio"], "Иванов Иван")

    def test_resolve_names(self):
        first = self.add_employee("Иванов Иван")
        second = self.add_employee("Петров Пётр")
        ids, unknown = database.resolve_employee_names(["петров пётр", "Иванов Иван", "иванов иван", "Сидоров"])
        self.assertEqual(ids, [second, first])
        self.assertEqual(unknown, ["Сидоров"])

    # --- публикации ---

    def test_publication_authors_keep_user_order(self):
        a = self.add_employee("Яковлев А.")
        b = self.add_employee("Абрамов Б.")
        pub = self.add_publication("Статья", [a, b])
        row = [r for r in database.get_all_publications() if r[0] == pub][0]
        self.assertEqual(row[7], "Яковлев А.; Абрамов Б.")
        self.assertEqual([r["fio"] for r in database.get_authors_by_publication(pub)], ["Яковлев А.", "Абрамов Б."])
        self.assertEqual([r["id"] for r in database.get_publications_by_employee(a)], [pub])

    def test_duplicate_authors_are_collapsed(self):
        a = self.add_employee("Иванов Иван")
        pub = self.add_publication("Статья", [a, a, a])
        self.assertEqual(database.get_publication(pub)["authors"], "Иванов Иван")

    def test_add_publication_with_unknown_author_rolls_back(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.add_publication("Статья", [999])
        self.assertEqual(database.get_all_publications(), [])

    def test_failed_update_keeps_old_authors_and_title(self):
        a = self.add_employee("Иванов Иван")
        b = self.add_employee("Петров Пётр")
        pub = self.add_publication("Старое название", [a, b])
        with self.assertRaises(sqlite3.IntegrityError):
            database.update_publication(pub, "Новое", "Ж", "РИНЦ", 5, "Статья", "2025-01-01", [a, 999])
        saved = database.get_publication(pub)
        self.assertEqual(saved["title"], "Старое название")
        self.assertEqual(saved["authors"], "Иванов Иван; Петров Пётр")

    def test_update_publication_replaces_authors(self):
        a = self.add_employee("Иванов Иван")
        b = self.add_employee("Петров Пётр")
        pub = self.add_publication("Статья", [a])
        self.assertTrue(database.update_publication(pub, "Статья 2", "Ж", "РИНЦ", 5, "Статья", "2025-01-01", [b, a]))
        self.assertEqual(database.get_publication(pub)["authors"], "Петров Пётр; Иванов Иван")

    def test_pair_must_be_unique(self):
        a = self.add_employee("Иванов Иван")
        pub = self.add_publication("Статья", [a])
        with db.transaction() as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO employee_publications (employee_id, publication_id) VALUES (?, ?)", (a, pub)
                )

    def test_delete_employee_cascades_links_but_keeps_publication(self):
        a = self.add_employee("Иванов Иван")
        pub = self.add_publication("Статья", [a])
        ach = database.add_achievement("Конференция", "Диплом", "Москва", "МГУ", "Доклад", "2025-03-03", [a])
        self.assertEqual(database.count_employee_links(a), (1, 1))

        self.assertTrue(database.delete_employee_by_id(a))

        self.assertEqual(database.get_publication(pub)["authors"], "")
        self.assertEqual(database.get_achievement(ach)["employees"], "")
        with db.connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM employee_publications").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM employee_achievements").fetchone()[0], 0)

    def test_delete_publication_cascades_links(self):
        a = self.add_employee("Иванов Иван")
        pub = self.add_publication("Статья", [a])
        self.assertTrue(database.delete_publication_by_id(pub))
        self.assertEqual(database.count_employee_links(a), (0, 0))

    def test_publication_file_roundtrip(self):
        pub = self.add_publication("Статья")
        self.assertIsNone(database.get_publication_file(pub))
        database.update_publication_file(pub, "files/publications/1.pdf")
        self.assertEqual(database.get_publication_file(pub), "files/publications/1.pdf")
        self.assertEqual(database.get_all_publications()[0][8], "Да")

    # --- достижения ---

    def test_achievement_crud_with_employees(self):
        a = self.add_employee("Иванов Иван")
        b = self.add_employee("Петров Пётр")
        ach = database.add_achievement("Конференция", "Диплом", "Москва", "МГУ", "Доклад", "2025-03-03", [a, b])
        self.assertEqual(database.get_achievement(ach)["employees"], "Иванов Иван; Петров Пётр")

        self.assertTrue(database.update_achievement(
            ach, "Конференция", "Грамота", "Казань", "КФУ", "Доклад", "2025-04-04", [b]
        ))
        saved = database.get_achievement(ach)
        self.assertEqual((saved["achievement"], saved["employees"]), ("Грамота", "Петров Пётр"))

        row = database.get_all_achievements()[0]
        self.assertEqual(row[0], ach)
        self.assertEqual(row[1], "Петров Пётр")
        self.assertEqual(row[8], "")

        self.assertTrue(database.delete_achievement_by_id(ach))
        self.assertEqual(database.get_all_achievements(), [])

    def test_failed_achievement_update_rolls_back(self):
        a = self.add_employee("Иванов Иван")
        ach = database.add_achievement("Е", "Диплом", "Г", "О", "Р", "2025-03-03", [a])
        with self.assertRaises(sqlite3.IntegrityError):
            database.update_achievement(ach, "Е", "Другое", "Г", "О", "Р", "2025-03-03", [999])
        saved = database.get_achievement(ach)
        self.assertEqual((saved["achievement"], saved["employees"]), ("Диплом", "Иванов Иван"))

    # --- отчёт ---

    def test_employee_report_uses_ids_not_substrings(self):
        short = self.add_employee("Иван")
        long_ = self.add_employee("Иван Иванов")
        self.add_publication("Только у короткого", [short])
        self.add_publication("Только у длинного", [long_])
        report = {fio: (pubs, achs) for _id, fio, pubs, achs in database.get_employee_report()}
        self.assertEqual(report["Иван"][0], ["Только у короткого"])
        self.assertEqual(report["Иван Иванов"][0], ["Только у длинного"])

        filtered = database.get_employee_report([long_])
        self.assertEqual([row[1] for row in filtered], ["Иван Иванов"])

    # --- история ---

    def test_history_serializes_dicts_as_json_and_keeps_none(self):
        history_db.add_history("employee", 1, "add", None, {"fio": "Иванов Иван"})
        history_db.add_history("employee", 1, "update", {"fio": "Иванов Иван"}, "готовая строка")
        rows = history_db.get_history()
        self.assertEqual(rows[0][2:5], ("update", '{"fio": "Иванов Иван"}', "готовая строка"))
        self.assertIsNone(rows[1][3])
        self.assertEqual(rows[1][4], '{"fio": "Иванов Иван"}')


class LegacyMigrationTests(TempDataDirTestCase):
    """База из старой версии: без внешних ключей, с дублями и «висящими» связями."""

    def build_legacy_db(self, folder):
        path = Path(folder) / paths.DB_NAME
        conn = sqlite3.connect(path)
        conn.executescript("""
            CREATE TABLE employees (id INTEGER PRIMARY KEY AUTOINCREMENT, fio TEXT NOT NULL,
                birth_date DATE, position TEXT, degree TEXT, rank TEXT);
            CREATE TABLE publications (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT,
                journal TEXT, level TEXT, pages INTEGER);
            CREATE TABLE achievements (id INTEGER PRIMARY KEY AUTOINCREMENT, employee_id INTEGER);
            CREATE TABLE employee_publications (id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER, publication_id INTEGER);
            CREATE TABLE employee_achievements (id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER, achievement_id INTEGER);
            CREATE TABLE reports (id INTEGER PRIMARY KEY AUTOINCREMENT);

            INSERT INTO employees (id, fio) VALUES (1, 'Иванов И.И.'), (2, 'Петров П.П.');
            INSERT INTO publications (id, title) VALUES (1, 'Первая'), (2, 'Вторая');
            INSERT INTO employee_publications (employee_id, publication_id) VALUES
                (1, 1), (1, 1), (2, 1), (99, 1), (1, 99);
            INSERT INTO achievements (id, employee_id) VALUES (1, 2), (2, 1), (3, NULL);
            INSERT INTO employee_achievements (employee_id, achievement_id) VALUES (1, 2);
        """)
        conn.commit()
        conn.close()
        return path

    def test_legacy_database_is_migrated_in_place(self):
        self.build_legacy_db(self.data_dir)

        db.init_database()

        with db.connection() as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], db.SCHEMA_VERSION)
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
            columns = {r["name"] for r in conn.execute("PRAGMA table_info(publications)")}
            self.assertTrue({"publication_type", "pub_date", "file_path"} <= columns)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM employee_publications").fetchone()[0], 2)

        self.assertEqual(database.get_publication(1)["authors"], "Иванов И.И.; Петров П.П.")
        self.assertEqual(database.get_publication(2)["authors"], "")
        # сотрудник из старой колонки achievements.employee_id попал в таблицу связей, без дублей
        self.assertEqual(database.get_achievement(1)["employees"], "Петров П.П.")
        self.assertEqual(database.get_achievement(2)["employees"], "Иванов И.И.")
        self.assertEqual(database.get_achievement(3)["employees"], "")

    def test_backup_is_made_before_migration(self):
        self.build_legacy_db(self.data_dir)
        db.init_database()
        names = [p.name for p in paths.backups_dir().glob("*.db")]
        self.assertTrue(any("before-v" in name for name in names), names)

        backup = next(paths.backups_dir().glob("*before-v*.db"))
        conn = sqlite3.connect(backup)
        try:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM employee_publications").fetchone()[0], 5)
        finally:
            conn.close()

    def test_failed_migration_rolls_back_and_keeps_data(self):
        self.build_legacy_db(self.data_dir)

        def broken(conn):
            conn.execute("DELETE FROM employees")
            raise RuntimeError("сбой посреди миграции")

        with mock.patch.dict(db.MIGRATIONS, {2: broken}):
            with self.assertRaises(RuntimeError):
                db.init_database()

        conn = sqlite3.connect(paths.db_path())
        try:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0], 2)
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
        finally:
            conn.close()

    def test_database_from_newer_version_is_refused(self):
        db.init_database()
        conn = sqlite3.connect(paths.db_path())
        conn.execute(f"PRAGMA user_version = {db.SCHEMA_VERSION + 1}")
        conn.close()
        with self.assertRaises(db.DatabaseCorruptedError):
            db.init_database()

    def test_garbage_file_is_reported_as_corrupted(self):
        paths.db_path().write_bytes(b"this is not an sqlite database at all " * 50)
        with self.assertRaises((db.DatabaseCorruptedError, sqlite3.DatabaseError)):
            db.init_database()


class LegacyLocationImportTests(TempDataDirTestCase):
    def test_old_database_and_attachments_are_copied_on_first_run(self):
        legacy_dir = Path(tempfile.mkdtemp(prefix="faculty-legacy-"))
        self.addCleanup(shutil.rmtree, legacy_dir, ignore_errors=True)

        conn = sqlite3.connect(legacy_dir / paths.DB_NAME)
        conn.execute("CREATE TABLE employees (id INTEGER PRIMARY KEY AUTOINCREMENT, fio TEXT NOT NULL, "
                     "birth_date DATE, position TEXT, degree TEXT, rank TEXT)")
        conn.execute("INSERT INTO employees (fio) VALUES ('Старый Сотрудник')")
        conn.commit()
        conn.close()
        (legacy_dir / "files" / "publications").mkdir(parents=True)
        (legacy_dir / "files" / "publications" / "3.pdf").write_bytes(b"%PDF")

        with mock.patch.object(paths, "legacy_db_candidates", return_value=[legacy_dir / paths.DB_NAME]):
            db.init_database()

        self.assertEqual([r["fio"] for r in database.get_all_employees()], ["Старый Сотрудник"])
        self.assertTrue((paths.user_data_dir() / "files" / "publications" / "3.pdf").is_file())
        self.assertEqual(
            paths.attachment_path("files/publications/3.pdf"),
            paths.user_data_dir() / "files" / "publications" / "3.pdf",
        )

    def test_absolute_attachment_path_is_kept(self):
        absolute = Path(self.data_dir).resolve() / "x.pdf"
        self.assertEqual(paths.attachment_path(str(absolute)), absolute)
        self.assertIsNone(paths.attachment_path(None))


if __name__ == "__main__":
    unittest.main()
