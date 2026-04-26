from PyQt5 import QtWidgets
from PyQt5.QtCore import QDate
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCompleter
from services.file_service import FileService
from database import (
    get_all_publications,
    add_publication,
    delete_publication_by_id,
    update_publication,
    get_publication_file,
    update_publication_file,
    clear_publication_authors,
    get_all_employees,
    link_employee_publication
)

class MultiCompleter(QCompleter):
    def splitPath(self, path):
        return [(path or "").split(";")[-1].strip()]

    def pathFromIndex(self, index):
        widget = self.widget()
        if widget is None:
            return ""

        text = widget.text() or ""
        parts = text.split(";")

        value = index.data()
        if value is None:
            return text

        if len(parts) > 1:
            return "; ".join([p.strip() for p in parts[:-1]]) + "; " + value
        else:
            return value

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

        #Список авторов
        self.refresh_authors_list()

        # кнопки
        parent.btnAddPub.clicked.connect(self.add_publication)
        self.parent.btnDeletePub.clicked.connect(self.delete_publication)

        self.table.cellClicked.connect(self.on_row_change)

        self.parent.btnUpdatePub.clicked.connect(self.update_publication_data)

        #Работа с файлом
        self.file_path = None
        self.current_file_path = None

        self.parent.btnFilePub.clicked.connect(self.select_file)
        self.table.cellDoubleClicked.connect(self.open_file)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)

        # загрузка
        self.load_publications()

    # ======================
    # ВСПОМОГАТЕЛЬНОЕ
    # ======================

    def refresh_authors_list(self):
        employees = get_all_employees()
        fio_list = [emp[1] for emp in employees]

        completer = MultiCompleter(fio_list)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)

        self.parent.inputAuthors.setCompleter(completer)

    def get_item_text(self, row, col):
        item = self.table.item(row, col)
        return item.text() if item else ""

    def fill_table(self, data):
        self.table.setRowCount(len(data))
        self.table.setColumnCount(9)

        self.table.setHorizontalHeaderLabels([
            "ID",
            "Название",
            "Издание",
            "Уровень",
            "Страницы",
            "Тип",
            "Дата",
            "Авторы",
            "Файл"
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

    def on_row_change(self, row):
        self.selected_publication_id = int(self.get_item_text(row, 0))

        self.parent.inputPubTitle.setText(self.get_item_text(row, 1))
        self.parent.inputJournal.setText(self.get_item_text(row, 2))
        self.parent.comboLevel.setCurrentText(self.get_item_text(row, 3))
        pages = self.get_item_text(row, 4)
        self.parent.inputPages.setValue(int(pages) if pages.isdigit() else 1)
        self.parent.comboType.setCurrentText(self.get_item_text(row, 5))
        self.current_file_path = get_publication_file(self.selected_publication_id)
        self.file_path = None

        date_str = self.get_item_text(row, 6)
        if date_str:
            self.parent.inputPubDate.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))

        self.parent.inputAuthors.setText(self.get_item_text(row, 7))

    def select_file(self):
        file, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.parent,
            "Выберите файл",
            "",
            "Все файлы (*);;PDF (*.pdf);;Word (*.docx)"
        )

        if file:
            self.file_path = file

    def open_context_menu(self, position):
        row = self.table.currentRow()

        if row == -1:
            return

        pub_id = int(self.get_item_text(row, 0))
        file_path = get_publication_file(pub_id)

        menu = QtWidgets.QMenu()

        if file_path:
            delete_action = menu.addAction("Удалить файл")
            action = menu.exec_(self.table.viewport().mapToGlobal(position))

            if action == delete_action:
                self.delete_file(pub_id)


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

        file_path = FileService.save_file(
            self.file_path,
            pub_id,
            None
        )

        update_publication_file(pub_id, file_path)

        if file_path:
            QtWidgets.QMessageBox.information(
                self.parent,
                "Файл",
                "Файл успешно прикреплён"
            )

        if file_path:
            self.history.add(
                "publication_file",
                pub_id,
                "add",
                None,
                file_path
            )

        self.file_path = None
        self.current_file_path = None

        authors_text = self.parent.inputAuthors.text()
        authors_list = [a.strip() for a in authors_text.split(";") if a.strip()]

        employees = get_all_employees()

        for author in authors_list:
            for emp in employees:
                if emp[1] == author:
                    link_employee_publication(emp[0], pub_id)
                    break  # ← ВАЖНО: только первый найденный. Проверка на дубликаты дескать

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

    def delete_publication(self):
        row = self.table.currentRow()

        if row == -1:
            QtWidgets.QMessageBox.warning(self.parent, "Ошибка", "Выберите публикацию")
            return

        publication_id = int(self.get_item_text(row, 0))

        old_data = str({
            "title": self.get_item_text(row, 1),
            "journal": self.get_item_text(row, 2),
            "level": self.get_item_text(row, 3),
            "pages": self.get_item_text(row, 4),
            "type": self.get_item_text(row, 5),
            "date": self.get_item_text(row, 6),
            "authors": self.get_item_text(row, 7),
        })

        reply = QtWidgets.QMessageBox.question(
            self.parent,
            "Подтверждение",
            "Вы действительно хотите удалить эту публикацию?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        path = get_publication_file(publication_id)
        FileService.delete_file(path)

        success = delete_publication_by_id(publication_id)

        if success:
            self.history.add(
                "publication",
                publication_id,
                "delete",
                old_data,
                None
            )

            self.parent.history_tab.refresh()

            QtWidgets.QMessageBox.information(self.parent, "Успех", "Публикация удалена")
            self.load_publications()
        else:
            QtWidgets.QMessageBox.critical(self.parent, "Ошибка", "Ошибка удаления")

    def update_publication_data(self):
        if self.selected_publication_id is None:
            QtWidgets.QMessageBox.warning(self.parent, "Ошибка", "Выберите публикацию")
            return

        clear_publication_authors(self.selected_publication_id)

        authors_text = self.parent.inputAuthors.text()
        authors_list = [a.strip() for a in authors_text.split(";") if a.strip()]

        employees = get_all_employees()

        for author in authors_list:
            for emp in employees:
                if emp[1] == author:
                    link_employee_publication(emp[0], self.selected_publication_id)
                    break

        row = self.table.currentRow()

        old_data = str({
            "title": self.get_item_text(row, 1),
            "journal": self.get_item_text(row, 2),
            "level": self.get_item_text(row, 3),
            "pages": self.get_item_text(row, 4),
            "type": self.get_item_text(row, 5),
            "date": self.get_item_text(row, 6),
            "authors": self.get_item_text(row, 7),
        })

        title = self.parent.inputPubTitle.text()
        journal = self.parent.inputJournal.text()
        level = self.parent.comboLevel.currentText()
        pages = self.parent.inputPages.value()
        pub_type = self.parent.comboType.currentText()
        pub_date = self.parent.inputPubDate.date().toString("yyyy-MM-dd")

        success = update_publication(
            self.selected_publication_id,
            title,
            journal,
            level,
            pages,
            pub_type,
            pub_date
        )

        file_path = FileService.save_file(
            self.file_path,
            self.selected_publication_id,
            self.current_file_path
        )

        update_publication_file(self.selected_publication_id, file_path)

        if self.file_path:
            self.history.add(
                "publication_file",
                self.selected_publication_id,
                "update",
                self.current_file_path,
                file_path
            )

        if file_path:
            QtWidgets.QMessageBox.information(
                self.parent,
                "Файл",
                "Файл успешно прикреплён"
            )

        self.file_path = None
        self.current_file_path = None

        if success:
            self.history.add(
                "publication",
                self.selected_publication_id,
                "update",
                old_data,
                str({
                    "title": title,
                    "journal": journal,
                    "level": level,
                    "pages": pages,
                    "type": pub_type,
                    "date": pub_date,
                    "authors": "; ".join(authors_list)
                })
            )

            self.parent.history_tab.refresh()
            self.load_publications()

            QtWidgets.QMessageBox.information(self.parent, "Успех", "Обновлено")
        else:
            QtWidgets.QMessageBox.critical(self.parent, "Ошибка", "Ошибка обновления")

    def open_file(self, row, col):
        pub_id = int(self.get_item_text(row, 0))
        path = get_publication_file(pub_id)

        try:
            FileService.open_file(path)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self.parent, "Ошибка", str(e))

    def delete_file(self, pub_id):
        reply = QtWidgets.QMessageBox.question(
            self.parent,
            "Удаление файла",
            "Удалить прикреплённый файл?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        old_path = get_publication_file(pub_id)

        FileService.delete_file(old_path)
        update_publication_file(pub_id, None)

        QtWidgets.QMessageBox.information(self.parent, "Файл", "Файл удалён")

        # история
        self.history.add(
            "publication_file",
            pub_id,
            "delete",
            old_path,
            None
        )

        self.parent.history_tab.refresh()
        self.load_publications()

    # ======================
    # ОЧИСТКА
    # ======================

    def clear_fields(self):
        self.inputTitle.clear()
        self.inputJournal.clear()
        self.inputPages.setValue(1)
        self.parent.inputPubDate.setDate(QDate.currentDate())
        self.parent.inputAuthors.clear()