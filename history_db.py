"""Журнал изменений. Таблица history создаётся миграцией в db.py."""
import json
from datetime import datetime

from db import connection, transaction


def _to_text(value):
    """None остаётся NULL, строка сохраняется как есть, остальное (словари) идёт в JSON."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, default=str)


def add_history(entity, entity_id, action, old_data, new_data):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO history (entity, entity_id, action, old_data, new_data, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (entity, entity_id, action, _to_text(old_data), _to_text(new_data), timestamp),
        )


def get_history():
    with connection() as conn:
        rows = conn.execute(
            "SELECT entity, entity_id, action, old_data, new_data, timestamp FROM history ORDER BY id DESC"
        ).fetchall()
    return [tuple(row) for row in rows]
