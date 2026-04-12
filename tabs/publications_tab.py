from PyQt5 import QtWidgets
from database import (
    get_all_publications,
    add_publication
)

class PublicationsTab:
    def __init__(self, parent, history_service):
        self.parent = parent
        self.history = history_service

        # состояние
        self.selected_publication_id = None

        # таблица
        self.table = parent.tablePublications
        self.table.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.table.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # поля
        self.inputTitle = parent.inputPubTitle
        self.inputJournal = parent.inputJournal
        self.comboLevel = parent.comboLevel
        self.inputPages = parent.inputPages
        self.comboType = parent.comboType

        # поиск
        self.search = parent.searchPublications
        self.search.textChanged.connect(self.search_publications)

        # кнопки
        parent.btnAddPub.clicked.connect(self.add_publication)

        # загрузка
        self.load_publications()

    # ======================
    # ВСПОМОГАТЕЛЬНОЕ
    # ======================

    def get_item_text(self, row, col):
        item = self.table.item(row, col)
        return item.text() if item else ""

    def fill_table(self, data):
        self.table.setRowCount(len(data))
        self.table.setColumnCount(8)

        self.table.setHorizontalHeaderLabels([
            "ID",
            "Название",
            "Издание",
            "Уровень",
            "Страницы",
            "Тип",
            "Дата",
            "Авторы"
        ])

        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                self.table.setItem(
                    row_idx,
                    col_idx,
                    QtWidgets.QTableWidgetItem(str(value) if value else "")
                )

        # скрываем ID
        self.table.setColumnHidden(0, True)

    # ======================
    # ЗАГРУЗКА
    # ======================

    def load_publications(self):
        data = get_all_publications()
        self.fill_table(data)

    def search_publications(self):
        text = self.search.text().strip().lower()

        if not text:
            self.load_publications()
            return

        filtered = []
        data = get_all_publications()

        for row in data:
            # ищем по названию и журналу
            if text in str(row[1]).lower() or text in str(row[2]).lower():
                filtered.append(row)

        self.fill_table(filtered)

    # ======================
    # CRUD
    # ======================

    def add_publication(self):
        title = self.inputTitle.text()
        journal = self.inputJournal.text()
        level = self.comboLevel.currentText()
        pages = self.inputPages.value()
        pub_type = self.comboType.currentText()
        pub_date = self.parent.inputPubDate.date().toString("yyyy-MM-dd")

        if not title.strip():
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Ошибка",
                "Введите название публикации"
            )
            return

        # добавляем в БД
        pub_id = add_publication(
            title,
            journal,
            level,
            pages,
            pub_type,
            pub_date
        )

        # история
        self.history.add(
            "publication",
            pub_id,
            "add",
            None,
            str({
                "title": title,
                "journal": journal,
                "level": level,
                "pages": pages,
                "type": pub_type
            })
        )

        # обновляем историю
        self.parent.history_tab.refresh()

        QtWidgets.QMessageBox.information(self.parent, "Успех", "Публикация добавлена")

        self.clear_fields()
        self.load_publications()

    # ======================
    # ОЧИСТКА
    # ======================

    def clear_fields(self):
        self.inputTitle.clear()
        self.inputJournal.clear()
        self.inputPages.setValue(1)