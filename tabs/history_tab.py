from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

class HistoryTab(QtWidgets.QWidget):
    def __init__(self, history_service):
        super().__init__()
        self.history_service = history_service

        # Layout
        self.layout = QtWidgets.QVBoxLayout(self)

        # Таблица
        self.tableWidget = QtWidgets.QTableWidget()
        self.layout.addWidget(self.tableWidget)

        #Сортировка
        self.tableWidget.setSortingEnabled(True)  

        # Колонки
        self.tableWidget.setColumnCount(6)
        self.tableWidget.setHorizontalHeaderLabels([
            "Сущность",
            "ID",
            "Действие",
            "Старые данные",
            "Новые данные",
            "Время"
        ])

        header = self.tableWidget.horizontalHeader()

        if header is not None:
            header.setStretchLastSection(True)

            header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
            header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
            header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)

        # Перенос текста
        self.tableWidget.setWordWrap(True)

        # Загружаем данные
        self.load_history()

    # Загрузка истории
    def load_history(self):
        rows = self.history_service.get_history()

        self.tableWidget.setRowCount(len(rows))

        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                item = QtWidgets.QTableWidgetItem(str(value))

                # запрет редактирования
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                self.tableWidget.setItem(i, j, item)

        # авто-высота строк
        self.tableWidget.resizeRowsToContents()

    def refresh(self):
        self.load_history()
