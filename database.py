"""Операции с данными: сотрудники, публикации, достижения.

Все функции открывают своё соединение через модуль db. Операции, которые меняют
несколько таблиц сразу (публикация вместе с авторами и т. п.), выполняются
в одной транзакции. Ошибки SQLite не скрываются: исключение дойдёт до обработчика
в main.py, который запишет его в журнал и покажет окно с ошибкой.
"""
from db import connection, transaction


class DuplicateEmployeeError(ValueError):
    """Сотрудник с таким ФИО уже есть."""


def _norm(text):
    """Ключ для сравнения имён: без лишних пробелов и без учёта регистра (в том числе кириллицы)."""
    return " ".join((text or "").split()).casefold()


def _clean(text):
    return " ".join((text or "").split())


# ======================
# СОТРУДНИКИ
# ======================

def get_all_employees():
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, fio, birth_date, position, degree, rank FROM employees"
        ).fetchall()
    return sorted(rows, key=lambda row: _norm(row["fio"]))


def get_employee(employee_id):
    with connection() as conn:
        return conn.execute(
            "SELECT id, fio, birth_date, position, degree, rank FROM employees WHERE id = ?",
            (employee_id,),
        ).fetchone()


def _assert_unique_fio(conn, fio, exclude_id=None):
    target = _norm(fio)
    for row in conn.execute("SELECT id, fio FROM employees"):
        if row["id"] != exclude_id and _norm(row["fio"]) == target:
            raise DuplicateEmployeeError(
                f"Сотрудник «{row['fio']}» уже есть в базе. "
                "Если это тёзка, добавьте к ФИО отличие (например, год рождения)."
            )


def add_employee(fio, birth_date, position, degree, rank):
    """Добавляет сотрудника и возвращает его id."""
    fio = _clean(fio)
    with transaction() as conn:
        _assert_unique_fio(conn, fio)
        cursor = conn.execute(
            "INSERT INTO employees (fio, birth_date, position, degree, rank) VALUES (?, ?, ?, ?, ?)",
            (fio, birth_date, position, degree, rank),
        )
        return cursor.lastrowid


def update_employee(employee_id, fio, birth_date, position, degree, rank):
    """Возвращает True, если запись найдена и обновлена."""
    fio = _clean(fio)
    with transaction() as conn:
        _assert_unique_fio(conn, fio, exclude_id=employee_id)
        cursor = conn.execute(
            "UPDATE employees SET fio = ?, birth_date = ?, position = ?, degree = ?, rank = ? WHERE id = ?",
            (fio, birth_date, position, degree, rank, employee_id),
        )
        return cursor.rowcount > 0


def delete_employee_by_id(employee_id):
    """Удаляет сотрудника; его связи с публикациями и достижениями удаляются каскадом."""
    with transaction() as conn:
        cursor = conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        return cursor.rowcount > 0


def count_employee_links(employee_id):
    """(число публикаций, число достижений) сотрудника."""
    with connection() as conn:
        pubs = conn.execute(
            "SELECT COUNT(*) FROM employee_publications WHERE employee_id = ?", (employee_id,)
        ).fetchone()[0]
        achs = conn.execute(
            "SELECT COUNT(*) FROM employee_achievements WHERE employee_id = ?", (employee_id,)
        ).fetchone()[0]
    return pubs, achs


def search_employees_by_fio(text):
    """Поиск по части ФИО без учёта регистра (LIKE в SQLite не умеет регистр кириллицы)."""
    needle = _norm(text)
    return [row for row in get_all_employees() if needle in _norm(row["fio"])]


def resolve_employee_names(names):
    """По списку ФИО возвращает (id сотрудников без повторов, ненайденные имена)."""
    index = {}
    for row in get_all_employees():
        index.setdefault(_norm(row["fio"]), row["id"])

    ids = []
    unknown = []
    for name in names:
        employee_id = index.get(_norm(name))
        if employee_id is None:
            unknown.append(name)
        elif employee_id not in ids:
            ids.append(employee_id)
    return ids, unknown


# ======================
# СВЯЗИ (авторы публикаций, участники достижений)
# ======================

def _replace_links(conn, table, owner_col, owner_id, employee_ids):
    conn.execute(f"DELETE FROM {table} WHERE {owner_col} = ?", (owner_id,))
    seen = set()
    order = 0
    for employee_id in employee_ids:
        if employee_id in seen:
            continue
        seen.add(employee_id)
        conn.execute(
            f"INSERT INTO {table} ({owner_col}, employee_id, sort_order) VALUES (?, ?, ?)",
            (owner_id, employee_id, order),
        )
        order += 1


def _names_map(conn, table, owner_col):
    """{id владельца: 'ФИО1; ФИО2'} в порядке, заданном пользователем."""
    rows = conn.execute(f"""
        SELECT l.{owner_col} AS owner_id, e.fio AS fio
        FROM {table} l
        JOIN employees e ON e.id = l.employee_id
        ORDER BY l.{owner_col}, l.sort_order, l.id
    """)
    grouped = {}
    for row in rows:
        grouped.setdefault(row["owner_id"], []).append(row["fio"])
    return {owner_id: "; ".join(names) for owner_id, names in grouped.items()}


# ======================
# ПУБЛИКАЦИИ
# ======================

def add_publication(title, journal, level, pages, pub_type, pub_date, author_ids=()):
    """Добавляет публикацию вместе с авторами одной транзакцией и возвращает её id."""
    with transaction() as conn:
        cursor = conn.execute(
            """
            INSERT INTO publications (title, journal, level, pages, publication_type, pub_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, journal, level, pages, pub_type, pub_date),
        )
        publication_id = cursor.lastrowid
        _replace_links(conn, "employee_publications", "publication_id", publication_id, author_ids)
        return publication_id


def update_publication(publication_id, title, journal, level, pages, pub_type, pub_date, author_ids=None):
    """Обновляет публикацию; если переданы author_ids, авторы заменяются в той же транзакции."""
    with transaction() as conn:
        cursor = conn.execute(
            """
            UPDATE publications
            SET title = ?, journal = ?, level = ?, pages = ?, publication_type = ?, pub_date = ?
            WHERE id = ?
            """,
            (title, journal, level, pages, pub_type, pub_date, publication_id),
        )
        if cursor.rowcount == 0:
            return False
        if author_ids is not None:
            _replace_links(conn, "employee_publications", "publication_id", publication_id, author_ids)
        return True


def delete_publication_by_id(publication_id):
    with transaction() as conn:
        cursor = conn.execute("DELETE FROM publications WHERE id = ?", (publication_id,))
        return cursor.rowcount > 0


def get_all_publications():
    """Строки: id, название, издание, уровень, страницы, тип, дата, авторы, файл ('Да' или '')."""
    with connection() as conn:
        rows = conn.execute("""
            SELECT id, title, journal, level, pages, publication_type, pub_date, file_path
            FROM publications
            ORDER BY id DESC
        """).fetchall()
        authors = _names_map(conn, "employee_publications", "publication_id")
    return [
        (
            row["id"], row["title"], row["journal"], row["level"], row["pages"],
            row["publication_type"], row["pub_date"], authors.get(row["id"], ""),
            "Да" if row["file_path"] else "",
        )
        for row in rows
    ]


def get_publication(publication_id):
    """Одна публикация словарём (или None)."""
    with connection() as conn:
        row = conn.execute(
            """
            SELECT id, title, journal, level, pages, publication_type, pub_date, file_path
            FROM publications WHERE id = ?
            """,
            (publication_id,),
        ).fetchone()
        if row is None:
            return None
        authors = _names_map(conn, "employee_publications", "publication_id")
    return {
        "title": row["title"],
        "journal": row["journal"],
        "level": row["level"],
        "pages": row["pages"],
        "type": row["publication_type"],
        "date": row["pub_date"],
        "authors": authors.get(row["id"], ""),
    }


def get_publications_by_employee(employee_id):
    with connection() as conn:
        return conn.execute(
            """
            SELECT p.id, p.title, p.journal
            FROM publications p
            JOIN employee_publications ep ON ep.publication_id = p.id
            WHERE ep.employee_id = ?
            ORDER BY p.pub_date DESC, p.id DESC
            """,
            (employee_id,),
        ).fetchall()


def get_authors_by_publication(publication_id):
    with connection() as conn:
        return conn.execute(
            """
            SELECT e.fio, ep.sort_order
            FROM employees e
            JOIN employee_publications ep ON ep.employee_id = e.id
            WHERE ep.publication_id = ?
            ORDER BY ep.sort_order, ep.id
            """,
            (publication_id,),
        ).fetchall()


def update_publication_file(publication_id, file_path):
    with transaction() as conn:
        conn.execute("UPDATE publications SET file_path = ? WHERE id = ?", (file_path, publication_id))


def get_publication_file(publication_id):
    with connection() as conn:
        row = conn.execute(
            "SELECT file_path FROM publications WHERE id = ?", (publication_id,)
        ).fetchone()
    return row["file_path"] if row else None


# ======================
# ДОСТИЖЕНИЯ
# ======================

def add_achievement(event, achievement, city, organization, work_name, ach_date, employee_ids=()):
    """Добавляет достижение вместе с участниками одной транзакцией и возвращает его id."""
    with transaction() as conn:
        cursor = conn.execute(
            """
            INSERT INTO achievements (event, achievement, city, organization, work_name, ach_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event, achievement, city, organization, work_name, ach_date),
        )
        achievement_id = cursor.lastrowid
        _replace_links(conn, "employee_achievements", "achievement_id", achievement_id, employee_ids)
        return achievement_id


def update_achievement(ach_id, event, achievement, city, organization, work_name, ach_date, employee_ids=None):
    with transaction() as conn:
        cursor = conn.execute(
            """
            UPDATE achievements
            SET event = ?, achievement = ?, city = ?, organization = ?, work_name = ?, ach_date = ?
            WHERE id = ?
            """,
            (event, achievement, city, organization, work_name, ach_date, ach_id),
        )
        if cursor.rowcount == 0:
            return False
        if employee_ids is not None:
            _replace_links(conn, "employee_achievements", "achievement_id", ach_id, employee_ids)
        return True


def delete_achievement_by_id(ach_id):
    with transaction() as conn:
        cursor = conn.execute("DELETE FROM achievements WHERE id = ?", (ach_id,))
        return cursor.rowcount > 0


def get_all_achievements():
    """Строки: id, сотрудники, мероприятие, достижение, город, организация, работа, дата, файл ('Да' или '')."""
    with connection() as conn:
        rows = conn.execute("""
            SELECT id, event, achievement, city, organization, work_name, ach_date, file_path
            FROM achievements
            ORDER BY id DESC
        """).fetchall()
        names = _names_map(conn, "employee_achievements", "achievement_id")
    return [
        (
            row["id"], names.get(row["id"], ""), row["event"], row["achievement"], row["city"],
            row["organization"], row["work_name"], row["ach_date"], "Да" if row["file_path"] else "",
        )
        for row in rows
    ]


def get_achievement(ach_id):
    """Одно достижение словарём (или None)."""
    with connection() as conn:
        row = conn.execute(
            """
            SELECT id, event, achievement, city, organization, work_name, ach_date
            FROM achievements WHERE id = ?
            """,
            (ach_id,),
        ).fetchone()
        if row is None:
            return None
        names = _names_map(conn, "employee_achievements", "achievement_id")
    return {
        "employees": names.get(row["id"], ""),
        "event": row["event"],
        "achievement": row["achievement"],
        "city": row["city"],
        "organization": row["organization"],
        "work": row["work_name"],
        "date": row["ach_date"],
    }


def update_achievement_file(ach_id, file_path):
    with transaction() as conn:
        conn.execute("UPDATE achievements SET file_path = ? WHERE id = ?", (file_path, ach_id))


def get_achievement_file(ach_id):
    with connection() as conn:
        row = conn.execute("SELECT file_path FROM achievements WHERE id = ?", (ach_id,)).fetchone()
    return row["file_path"] if row else None


# ======================
# ОТЧЁТЫ
# ======================

def get_employee_report(employee_ids=None):
    """Для каждого сотрудника: (id, ФИО, [названия публикаций], [достижения]).

    employee_ids=None означает всех сотрудников. Связи берутся по id, поэтому
    тёзки и совпадения подстрок в ФИО не путаются.
    """
    with connection() as conn:
        employees = conn.execute("SELECT id, fio FROM employees").fetchall()

        publications = {}
        for row in conn.execute("""
            SELECT ep.employee_id AS employee_id, p.title AS title
            FROM employee_publications ep
            JOIN publications p ON p.id = ep.publication_id
            ORDER BY p.pub_date, p.id
        """):
            publications.setdefault(row["employee_id"], []).append(row["title"] or "")

        achievements = {}
        for row in conn.execute("""
            SELECT ea.employee_id AS employee_id, a.achievement AS achievement
            FROM employee_achievements ea
            JOIN achievements a ON a.id = ea.achievement_id
            ORDER BY a.ach_date, a.id
        """):
            achievements.setdefault(row["employee_id"], []).append(row["achievement"] or "")

    result = []
    for employee in sorted(employees, key=lambda row: _norm(row["fio"])):
        if employee_ids is not None and employee["id"] not in employee_ids:
            continue
        result.append((
            employee["id"], employee["fio"],
            publications.get(employee["id"], []),
            achievements.get(employee["id"], []),
        ))
    return result
