import sqlite3
from datetime import datetime

DB_PATH = "employee_system.db"

def add_history(entity, entity_id, action, old_data, new_data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
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
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO history (entity, entity_id, action, old_data, new_data, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (entity, entity_id, action, str(old_data), str(new_data), timestamp))
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT entity, entity_id, action, old_data, new_data, timestamp FROM history ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows