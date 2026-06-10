import sqlite3
from typing import List, Tuple
import os
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

DB_FILE = resource_path("employee_system.db")


def create_database(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    #Сотрудники
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fio TEXT NOT NULL,
        birth_date DATE,
        position TEXT,
        degree TEXT,
        rank TEXT
    )
    """)

    conn.commit()
    conn.close()

def ensure_publications_schema():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # таблица публикаций
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS publications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        journal TEXT,
        level TEXT,
        pages INTEGER
    )
    """)

    # добавляем недостающие колонки
    columns = [
        ("publication_type", "TEXT"),
        ("pub_date", "TEXT"),
        ("file_path", "TEXT")
    ]

    for col, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE publications ADD COLUMN {col} {col_type}")
        except:
            pass

    conn.commit()
    conn.close()

def ensure_achievements_schema():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER
    )
    """)

    columns = [
        ("employee_id", "INTEGER"),
        ("event", "TEXT"),
        ("achievement", "TEXT"),
        ("city", "TEXT"),
        ("organization", "TEXT"),
        ("work_name", "TEXT"),
        ("ach_date", "TEXT"),
        ("file_path", "TEXT")
    ]

    for col, col_type in columns:
        try:
            cursor.execute(
                f"ALTER TABLE achievements ADD COLUMN {col} {col_type}"
            )
        except:
            pass

    conn.commit()
    conn.close()

def ensure_employee_publications():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_publications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        publication_id INTEGER
    )
    """)

    conn.commit()
    conn.close()

def add_publication(title, journal, level, pages, pub_type, pub_date):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO publications (title, journal, level, pages, publication_type, pub_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, journal, level, pages, pub_type, pub_date))

    pub_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return pub_id

def delete_publication_by_id(publication_id):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            # удаляем связи
            cursor.execute("""
                DELETE FROM employee_publications
                WHERE publication_id = ?
            """, (publication_id,))

            # удаляем саму публикацию
            cursor.execute("""
                DELETE FROM publications
                WHERE id = ?
            """, (publication_id,))

            conn.commit()
            return True

    except Exception as e:
        print(f"Ошибка удаления публикации: {e}")
        return False

def update_publication(publication_id, title, journal, level, pages, pub_type, pub_date):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE publications
                SET title = ?, journal = ?, level = ?, pages = ?, publication_type = ?, pub_date = ?
                WHERE id = ?
            """, (title, journal, level, pages, pub_type, pub_date, publication_id))

            conn.commit()
            return True

    except Exception as e:
        print(f"Ошибка обновления публикации: {e}")
        return False

def link_employee_publication(employee_id, publication_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO employee_publications (employee_id, publication_id)
        VALUES (?, ?)
    """, (employee_id, publication_id))

    conn.commit()
    conn.close()

def get_all_publications():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    p.id,
                    p.title,
                    p.journal,
                    p.level,
                    p.pages,
                    p.publication_type,
                    p.pub_date,
                    GROUP_CONCAT(e.fio, '; ') as authors,
                    CASE 
                        WHEN p.file_path IS NOT NULL AND p.file_path != '' THEN 'True'
                        ELSE 'False'
                    END as has_file
                FROM publications p
                LEFT JOIN employee_publications ep 
                    ON p.id = ep.publication_id
                LEFT JOIN employees e 
                    ON ep.employee_id = e.id
                GROUP BY p.id
            """)

            return cursor.fetchall()

    except Exception as e:
        print(f"Ошибка получения публикаций: {e}")
        return []

def get_all_employees() -> List[Tuple]:

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, fio, birth_date, position, degree, rank FROM employees")
            data = cursor.fetchall()
            return data
    except sqlite3.Error as e:
        print(f"Ошибка базы данных при получении сотрудников: {e}")
        return []
    except Exception as e:
        print(f"Неожиданная ошибка при получении сотрудников: {e}")
        return []

def get_publications_by_employee(employee_id):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.id, p.title, p.journal
                FROM publications p
                JOIN employee_publications ep 
                    ON p.id = ep.publication_id
                WHERE ep.employee_id = ?
                ORDER BY ep.author_order
            """, (employee_id,))
            return cursor.fetchall()
    except Exception as e:
        print(f"Ошибка: {e}")
        return []

def get_authors_by_publication(publication_id):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.fio, ep.author_order
                FROM employees e
                JOIN employee_publications ep 
                    ON e.id = ep.employee_id
                WHERE ep.publication_id = ?
                ORDER BY ep.author_order
            """, (publication_id,))
            return cursor.fetchall()
    except Exception as e:
        print(f"Ошибка: {e}")
        return []

def add_employee(fio, birth_date, position, degree, rank):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO employees (fio, birth_date, position, degree, rank)
    VALUES (?, ?, ?, ?, ?)
    """, (fio, birth_date, position, degree, rank))

    conn.commit()
    conn.close()

def delete_employee_by_id(employee_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
        rows_deleted = cursor.rowcount
        conn.commit()

        conn.close()

        return rows_deleted > 0

    except sqlite3.Error as e:
        print(f"Ошибка базы данных при удалении сотрудника {employee_id}: {e}")
        return False
    except Exception as e:
        print(f"Неожиданная ошибка при удалении сотрудника {employee_id}: {e}")
        return False

def search_employees_by_fio(fio: str) -> List[Tuple]:
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, fio, birth_date, position, degree, rank
                FROM employees
                WHERE fio LIKE ?
            """, (f"%{fio}%",))
            return cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Ошибка при поиске: {e}")
        return []

def update_employee(employee_id, fio, birth_date, position, degree, rank):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE employees
                SET fio = ?, birth_date = ?, position = ?, degree = ?, rank = ?
                WHERE id = ?
            """, (fio, birth_date, position, degree, rank, employee_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"Ошибка обновления: {e}")
        return False

def update_publication_file(pub_id, file_path):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE publications
                SET file_path = ?
                WHERE id = ?
            """, (file_path, pub_id))
            conn.commit()
    except Exception as e:
        print(f"Ошибка сохранения файла: {e}")


def get_publication_file(pub_id):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_path FROM publications WHERE id = ?
            """, (pub_id,))
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"Ошибка получения файла: {e}")
        return None

def clear_publication_authors(publication_id):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM employee_publications
                WHERE publication_id = ?
            """, (publication_id,))
            conn.commit()
    except Exception as e:
        print(f"Ошибка очистки авторов: {e}")

def add_achievement(
        event,
        achievement,
        city,
        organization,
        work_name,
        ach_date
):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO achievements
        (
            event,
            achievement,
            city,
            organization,
            work_name,
            ach_date
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        event,
        achievement,
        city,
        organization,
        work_name,
        ach_date
    ))

    ach_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return ach_id

def get_all_achievements():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    a.id,
                    GROUP_CONCAT(e.fio, '; ') as employees,
                    a.event,
                    a.achievement,
                    a.city,
                    a.organization,
                    a.work_name,
                    a.ach_date,
                    CASE
                        WHEN a.file_path IS NOT NULL
                             AND a.file_path != ''
                        THEN 'True'
                        ELSE 'False'
                    END as has_file
                FROM achievements a
                LEFT JOIN employee_achievements ea
                    ON a.id = ea.achievement_id
                LEFT JOIN employees e
                    ON ea.employee_id = e.id
                GROUP BY a.id
                ORDER BY a.id DESC
            """)

            return cursor.fetchall()

    except Exception as e:
        print(f"Ошибка получения достижений: {e}")
        return []

def update_achievement(
        ach_id,
        event,
        achievement,
        city,
        organization,
        work_name,
        ach_date
):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE achievements
                SET
                    event=?,
                    achievement=?,
                    city=?,
                    organization=?,
                    work_name=?,
                    ach_date=?
                WHERE id=?
            """, (
                event,
                achievement,
                city,
                organization,
                work_name,
                ach_date,
                ach_id
            ))

            conn.commit()
            return True

    except Exception as e:
        print(f"Ошибка обновления достижения: {e}")
        return False

def delete_achievement_by_id(ach_id):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM achievements
                WHERE id = ?
            """, (ach_id,))

            conn.commit()
            return True

    except Exception as e:
        print(f"Ошибка удаления достижения: {e}")
        return False

def update_achievement_file(ach_id, file_path):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE achievements
                SET file_path = ?
                WHERE id = ?
            """, (file_path, ach_id))
            conn.commit()
    except Exception as e:
        print(f"Ошибка сохранения файла достижения: {e}")

def get_achievement_file(ach_id):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT file_path FROM achievements WHERE id = ?
            """, (ach_id,))

            result = cursor.fetchone()
            return result[0] if result else None

    except Exception as e:
        print(f"Ошибка получения файла: {e}")
        return None

def search_achievements(text: str):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    a.id,
                    e.fio,
                    a.event,
                    a.achievement,
                    a.city,
                    a.organization,
                    a.work_name,
                    a.file_path
                FROM achievements a
                LEFT JOIN employees e ON a.employee_id = e.id
                WHERE 
                    e.fio LIKE ? OR
                    a.event LIKE ? OR
                    a.achievement LIKE ? OR
                    a.city LIKE ? OR
                    a.organization LIKE ? OR
                    a.work_name LIKE ?
            """, tuple([f"%{text}%"] * 6))

            return cursor.fetchall()

    except Exception as e:
        print(f"Ошибка поиска достижений: {e}")
        return []

def link_employee_achievement(employee_id, achievement_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO employee_achievements (employee_id, achievement_id)
        VALUES (?, ?)
    """, (employee_id, achievement_id))

    conn.commit()
    conn.close()

def clear_achievement_employees(achievement_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM employee_achievements
        WHERE achievement_id = ?
    """, (achievement_id,))

    conn.commit()
    conn.close()

def ensure_employee_achievements():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employee_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        achievement_id INTEGER
    )
    """)

    conn.commit()
    conn.close()