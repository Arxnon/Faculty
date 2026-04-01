import sqlite3
from typing import List, Tuple

DB_FILE = "employee_system.db"


def create_database(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

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

def add_employee(fio, birth_date, position, degree, rank):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO employees (fio, birth_date, position, degree, rank)
    VALUES (?, ?, ?, ?, ?)
    """, (fio, birth_date, position, degree, rank))

    conn.commit()
    conn.close()


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
