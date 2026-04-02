from history_db import add_history, get_history as db_get_history

class HistoryService:

    @staticmethod
    def save_history(entity, entity_id, action, old_data, new_data):
        try:
            add_history(entity, entity_id, action, old_data, new_data)
        except Exception as e:
            print(f"Ошибка при сохранении истории: {e}")

    @staticmethod
    def get_history():
        return db_get_history()

