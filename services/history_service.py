import logging

from history_db import add_history, get_history as db_get_history

log = logging.getLogger(__name__)


class HistoryService:
    @staticmethod
    def save_history(entity, entity_id, action, old_data, new_data):
        """Запись в журнал не должна ломать основную операцию, поэтому ошибка только логируется."""
        try:
            add_history(entity, entity_id, action, old_data, new_data)
        except Exception:
            log.exception("Не удалось сохранить запись истории (%s %s %s)", entity, entity_id, action)

    @staticmethod
    def get_history():
        return db_get_history()

    # Короткое имя, которое вызывают вкладки
    def add(self, entity, entity_id, action, old_data, new_data):
        self.save_history(entity, entity_id, action, old_data, new_data)
