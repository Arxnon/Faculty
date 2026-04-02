from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QTableWidgetItem, QMessageBox

class HistoryTab(QtWidgets.QWidget):
    def __init__(self, history_service, parent=None):
        super().__init__(parent)
        self.history_service = history_service

        # Создаём таблицу
        self.tableHistory = QtWidgets.QTableWidget(self)
        self.tableHistory.setColumnCount(6)
        self.tableHistory.setHorizontalHeaderLabels([
            "Сущность", "ID", "Действие", "Старые данные", "Новые данные", "Дата изменения"
        ])
        self.tableHistory.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableHistory.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.tableHistory.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)
        self.tableHistory.cellDoubleClicked.connect(self.show_full_text)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tableHistory)
        self.setLayout(layout)

        self.load_history()

    def load_history(self):
        self.tableHistory.setRowCount(0)
        data = self.history_service.get_history()

        for row_data in data:
            entity, entity_id, action, old_data, new_data, timestamp = row_data[:6]

            row_idx = self.tableHistory.rowCount()
            self.tableHistory.insertRow(row_idx)

            self.tableHistory.setItem(row_idx, 0, QTableWidgetItem(str(entity)))
            self.tableHistory.setItem(row_idx, 1, QTableWidgetItem(str(entity_id)))
            self.tableHistory.setItem(row_idx, 2, QTableWidgetItem(str(action)))
            self.tableHistory.setItem(row_idx, 3, QTableWidgetItem(self.format_data_for_user(old_data)))
            self.tableHistory.setItem(row_idx, 4, QTableWidgetItem(self.format_data_for_user(new_data)))
            self.tableHistory.setItem(row_idx, 5, QTableWidgetItem(str(timestamp)))

        self.tableHistory.resizeColumnsToContents()

    @staticmethod
    def format_data_for_user(data):
        if not data:
            return ""
        try:
            if isinstance(data, dict):
                return ", ".join(f"{k}: {v}" for k, v in data.items())
            if isinstance(data, str):
                return data
            return str(data)
        except (TypeError, AttributeError):
            return str(data)

    def show_full_text(self, row, column):
        item = self.tableHistory.item(row, column)
        if item:
            text = item.text()
            if len(text) > 50:  # если длинная строка, показываем окно
                QMessageBox.information(self, "Полная информация", text)