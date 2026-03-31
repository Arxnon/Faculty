import sqlite3

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


def get_all_employees():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("SELECT id, fio, birth_date, position, degree, rank FROM employees")
    data = cursor.fetchall()

    conn.close()
    return data

def delete_employee_by_id(employee_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id))
    conn.commit()
    conn.close()
