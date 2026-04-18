from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt


class HistoryTab(QtWidgets.QWidget):
    def __init__(self, history_service):
        super().__init__()
        self.history_service = history_service

        # MAIN LAYOUT
        self.layout = QtWidgets.QVBoxLayout(self)

        # TOP PANEL (СЛАЙДЕР)
        top_layout = QtWidgets.QHBoxLayout()

        # Отталкиваем вправо
        top_layout.addStretch()

        # Подпись (необязательно)
        self.zoomLabel = QtWidgets.QLabel("Масштаб")
        top_layout.addWidget(self.zoomLabel)

        # Слайдер
        self.zoomSlider = QtWidgets.QSlider(Qt.Horizontal)
        self.zoomSlider.setMinimum(8)
        self.zoomSlider.setMaximum(20)
        self.zoomSlider.setValue(12)
        self.zoomSlider.setFixedWidth(150)

        top_layout.addWidget(self.zoomSlider)

        # Добавляем верхнюю панель
        self.layout.addLayout(top_layout)

        #Таблица
        self.tableWidget = QtWidgets.QTableWidget()
        self.layout.addWidget(self.tableWidget)
        self.base_font = self.tableWidget.font()

        # Сортировка
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

        self.zoomSlider.valueChanged.connect(self.change_zoom)

        # Загружаем данные
        self.load_history()

    def change_zoom(self, value):
        value = max(8, min(value, 20))
        font = self.base_font
        font.setPointSize(value)
        self.tableWidget.setFont(font)

        self.tableWidget.resizeRowsToContents()
        self.tableWidget.viewport().update()

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
