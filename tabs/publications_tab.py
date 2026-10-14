from PyQt5 import QtWidgets
from PyQt5.QtCore import QDate, Qt

from database import (
    add_publication,
    delete_publication_by_id,
    get_all_employees,
    get_all_publications,
    get_publication,
    get_publication_file,
    resolve_employee_names,
    update_publication,
    update_publication_file,
)
from services.file_service import FileService
from ui_common import cell_text, make_names_completer, split_names

FILES_FOLDER = "files/publications"


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

        # Список авторов
        self.refresh_authors_list()

        # кнопки
        parent.btnAddPub.clicked.connect(self.add_publication)
        self.parent.btnDeletePub.clicked.connect(self.delete_publication)

        self.table.cellClicked.connect(self.on_row_change)

        self.parent.btnUpdatePub.clicked.connect(self.update_publication_data)

        # Работа с файлом
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
        fio_list = [row["fio"] for row in get_all_employees()]
        self.parent.inputAuthors.setCompleter(make_names_completer(fio_list))

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
                    QtWidgets.QTableWidgetItem(cell_text(value))
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

    def _warn(self, text, title="Ошибка"):
        QtWidgets.QMessageBox.warning(self.parent, title, text)

    def _collect_form(self):
        """Читает и проверяет форму. Ничего не меняет в базе.

        Возвращает (данные, id авторов) или None, если что-то не так
        (причина уже показана пользователю).
        """
        title = self.inputTitle.text().strip()
        if not title:
            self._warn("Введите название публикации")
            return None

        names = split_names(self.parent.inputAuthors.text())
        if not names:
            self._warn("Поле 'Авторы' не может быть пустым")
            return None

        author_ids, unknown = resolve_employee_names(names)
        if unknown:
            self._warn(f"Сотрудник '{unknown[0]}' отсутствует в базе данных")
            return None

        data = {
            "title": title,
            "journal": self.inputJournal.text().strip(),
            "level": self.comboLevel.currentText(),
            "pages": self.inputPages.value(),
            "pub_type": self.comboType.currentText(),
            "pub_date": self.parent.inputPubDate.date().toString("yyyy-MM-dd"),
        }
        return data, author_ids

    def _attach_file(self, entity_id, old_path):
        """Копирует выбранный файл в хранилище.

        Возвращает (путь для БД, был ли прикреплён новый файл).
        """
        if not self.file_path:
            return old_path, False

        try:
            stored = FileService.save_file(self.file_path, entity_id, FILES_FOLDER, old_path)
        except OSError as exc:
            self._warn(f"Не удалось прикрепить файл: {exc}", "Файл")
            return old_path, False

        QtWidgets.QMessageBox.information(self.parent, "Файл", "Файл успешно прикреплён")
        return stored, True

    # ======================
    # ЗАГРУЗКА
    # ======================
    def load_publications(self):
        self.fill_table(get_all_publications())

    def search_publications(self):
        text = self.search.text().strip().lower()

        if not text:
            self.load_publications()
            return

        filtered = []

        for row in get_all_publications():
            # ищем по названию, изданию и авторам
            if any(text in cell_text(row[index]).lower() for index in (1, 2, 7)):
                filtered.append(row)

        self.fill_table(filtered)

    # ======================
    # CRUD
    # ======================

    def add_publication(self):
        form = self._collect_form()
        if form is None:
            return
        data, author_ids = form

        # публикация и авторы сохраняются одной транзакцией
        pub_id = add_publication(
            data["title"],
            data["journal"],
            data["level"],
            data["pages"],
            data["pub_type"],
            data["pub_date"],
            author_ids,
        )

        file_path, attached = self._attach_file(pub_id, None)
        if attached:
            update_publication_file(pub_id, file_path)
            self.history.add("publication_file", pub_id, "add", None, file_path)

        self.file_path = None
        self.current_file_path = None

        self.history.add("publication", pub_id, "add", None, get_publication(pub_id))
        self.parent.history_tab.refresh()

        QtWidgets.QMessageBox.information(self.parent, "Успех", "Публикация добавлена")

        self.clear_fields()
        self.load_publications()

    def delete_publication(self):
        row = self.table.currentRow()

        if row == -1:
            self._warn("Выберите публикацию")
            return

        publication_id = int(self.get_item_text(row, 0))
        old_data = get_publication(publication_id)

        if old_data is None:
            self._warn("Публикация уже удалена")
            self.load_publications()
            return

        reply = QtWidgets.QMessageBox.question(
            self.parent,
            "Подтверждение",
            "Вы действительно хотите удалить эту публикацию?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        stored_file = get_publication_file(publication_id)

        # Сначала запись в базе, и только потом файл: если удаление в базе
        # не удалось, вложение остаётся на месте.
        if not delete_publication_by_id(publication_id):
            QtWidgets.QMessageBox.critical(self.parent, "Ошибка", "Ошибка удаления")
            return

        FileService.delete_file(stored_file)

        self.history.add("publication", publication_id, "delete", old_data, None)
        self.parent.history_tab.refresh()

        if self.selected_publication_id == publication_id:
            self.clear_fields()

        QtWidgets.QMessageBox.information(self.parent, "Успех", "Публикация удалена")
        self.load_publications()

    def update_publication_data(self):
        if self.selected_publication_id is None:
            self._warn("Выберите публикацию")
            return

        # Сначала проверка, потом любые изменения: при ошибке в данных
        # у публикации не должны пропасть авторы.
        form = self._collect_form()
        if form is None:
            return
        data, author_ids = form

        publication_id = self.selected_publication_id
        old_data = get_publication(publication_id)

        if old_data is None:
            self._warn("Публикация не найдена: возможно, она уже удалена")
            self.clear_fields()
            self.load_publications()
            return

        success = update_publication(
            publication_id,
            data["title"],
            data["journal"],
            data["level"],
            data["pages"],
            data["pub_type"],
            data["pub_date"],
            author_ids,
        )

        if not success:
            QtWidgets.QMessageBox.critical(self.parent, "Ошибка", "Ошибка обновления")
            return

        file_path, attached = self._attach_file(publication_id, self.current_file_path)
        if attached:
            update_publication_file(publication_id, file_path)
            self.history.add(
                "publication_file", publication_id, "update", self.current_file_path, file_path
            )

        self.file_path = None
        self.current_file_path = get_publication_file(publication_id)

        self.history.add(
            "publication", publication_id, "update", old_data, get_publication(publication_id)
        )
        self.parent.history_tab.refresh()
        self.load_publications()

        QtWidgets.QMessageBox.information(self.parent, "Успех", "Обновлено")

    def open_file(self, row, col):
        pub_id = int(self.get_item_text(row, 0))
        path = get_publication_file(pub_id)

        try:
            FileService.open_file(path)
        except Exception as e:
            self._warn(str(e))

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

        if self.selected_publication_id == pub_id:
            self.current_file_path = None

        QtWidgets.QMessageBox.information(self.parent, "Файл", "Файл удалён")

        # история
        self.history.add("publication_file", pub_id, "delete", old_path, None)

        self.parent.history_tab.refresh()
        self.load_publications()

    # ======================
    # ОЧИСТКА
    # ======================

    def clear_fields(self):
        # После очистки «Обновить» не должен менять ранее выбранную публикацию
        self.selected_publication_id = None
        self.file_path = None
        self.current_file_path = None
        self.inputTitle.clear()
        self.inputJournal.clear()
        self.inputPages.setValue(1)
        self.parent.inputPubDate.setDate(QDate.currentDate())
        self.parent.inputAuthors.clear()
