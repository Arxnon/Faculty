import sqlite3
from typing import List, Tuple

DB_FILE = "employee_system.db"


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

def ensure_publications_table():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # создаём таблицу если её нет
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS publications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        journal TEXT,
        level TEXT,
        pages INTEGER
    )
    """)

    # пробуем добавить колонку (если её нет)
    try:
        cursor.execute("ALTER TABLE publications ADD COLUMN publication_type TEXT")
    except:
        pass  # уже есть

    conn.commit()
    conn.close()

def add_publication(title, journal, level, pages, pub_type):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO publications (title, journal, level, pages, publication_type)
        VALUES (?, ?, ?, ?, ?)
    """, (title, journal, level, pages, pub_type))

    pub_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return pub_id

def link_employee_publication(employee_id, publication_id, author_order):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO employee_publications (employee_id, publication_id, author_order)
        VALUES (?, ?, ?)
    """, (employee_id, publication_id, author_order))

    conn.commit()
    conn.close()

def get_all_publications():
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, journal, level, pages, publication_type
                FROM publications
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
