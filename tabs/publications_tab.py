from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QTableWidgetItem
from database import get_all_publications


class PublicationsTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QtWidgets.QVBoxLayout(self)

        # таблица
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Название", "Журнал", "Уровень", "Страницы", "Тип"
        ])

        # растягиваем
        header = self.table.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)

        # кнопка обновления
        self.refresh_btn = QtWidgets.QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.load_data)

        self.layout.addWidget(self.table)
        self.layout.addWidget(self.refresh_btn)

        self.load_data()

    def load_data(self):
        data = get_all_publications()

        self.table.setRowCount(len(data))

        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                self.table.setItem(row_idx, col_idx, item)