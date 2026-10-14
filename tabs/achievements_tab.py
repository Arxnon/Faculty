from PyQt5 import QtWidgets
from PyQt5.QtCore import QDate, Qt

from database import (
    add_achievement,
    delete_achievement_by_id,
    get_achievement,
    get_achievement_file,
    get_all_achievements,
    get_all_employees,
    resolve_employee_names,
    update_achievement,
    update_achievement_file,
)
from services.file_service import FileService
from ui_common import cell_text, make_names_completer, split_names

FILES_FOLDER = "files/achievements"


class AchievementsTab:
    def __init__(self, parent, history_service):
        self.parent = parent
        self.history = history_service

        self.selected_id = None
        self.file_path = None
        self.current_file_path = None

        # TABLE
        self.table = parent.tableAchievements
        self.table.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.table.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # FIELDS
        self.inputAchievement = parent.inputAchievement
        self.inputEvent = parent.inputEvent
        self.inputCity = parent.inputCity
        self.inputOrganization = parent.inputOrganization
        self.inputWork = parent.inputWork
        self.inputAchDate = parent.inputAchDate
        self.inputEmployees = parent.inputEmployeeName  # <- аналог authors

        # SEARCH
        self.search = parent.searchAchievements
        self.search.textChanged.connect(self.search_achievements)

        self.refresh_employees()

        # BUTTONS
        parent.btnAddAch.clicked.connect(self.add_achievement)
        parent.btnUpdateAch.clicked.connect(self.update_achievement_data)
        parent.btnDeleteAch.clicked.connect(self.delete_achievement)
        parent.btnFileAch.clicked.connect(self.select_file)

        # EVENTS
        self.table.cellClicked.connect(self.on_row_change)
        self.table.cellDoubleClicked.connect(self.open_file)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)

        self.load_achievements()

    # ======================
    # EMPLOYEES (как authors)
    # ======================
    def refresh_employees(self):
        """Обновляет подсказки со списком сотрудников. Вызывается и при изменении сотрудников."""
        fio_list = [row["fio"] for row in get_all_employees()]
        self.inputEmployees.setCompleter(make_names_completer(fio_list))

    def _warn(self, text, title="Ошибка"):
        QtWidgets.QMessageBox.warning(self.parent, title, text)

    def _collect_form(self):
        """Читает и проверяет форму. Ничего не меняет в базе.

        Возвращает (поля, id сотрудников) или None, если что-то не так
        (причина уже показана пользователю).
        """
        names = split_names(self.inputEmployees.text())
        if not names:
            self._warn("Необходимо указать сотрудника")
            return None

        # Сотрудников ищем в базе заново, а не в списке, загруженном при запуске:
        # так только что добавленные сотрудники находятся сразу.
        employee_ids, unknown = resolve_employee_names(names)
        if unknown:
            self._warn(f"Сотрудник '{unknown[0]}' не найден")
            return None

        fields = {
            "event": self.inputEvent.text().strip(),
            "achievement": self.inputAchievement.text().strip(),
            "city": self.inputCity.text().strip(),
            "organization": self.inputOrganization.text().strip(),
            "work_name": self.inputWork.text().strip(),
            "ach_date": self.inputAchDate.date().toString("yyyy-MM-dd"),
        }
        return fields, employee_ids

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
    # TABLE
    # ======================
    def fill_table(self, data):
        self.table.setRowCount(len(data))
        self.table.setColumnCount(9)

        self.table.setHorizontalHeaderLabels([
            "ID",
            "Сотрудники",
            "Мероприятие",
            "Достижение",
            "Город",
            "Организация",
            "Работа",
            "Дата",
            "Файл"
        ])

        for r, row in enumerate(data):
            for c, val in enumerate(row):
                self.table.setItem(r, c, QtWidgets.QTableWidgetItem(cell_text(val)))

        self.table.setColumnHidden(0, True)

    def load_achievements(self):
        self.fill_table(get_all_achievements())

    # ======================
    # SEARCH
    # ======================
    def search_achievements(self):
        text = self.search.text().lower().strip()

        if not text:
            self.load_achievements()
            return

        filtered = []

        for row in get_all_achievements():
            if any(text in cell_text(x).lower() for x in row[1:7]):
                filtered.append(row)

        self.fill_table(filtered)

    # ======================
    # SELECT ROW
    # ======================
    def _item_text(self, row, col):
        item = self.table.item(row, col)
        return item.text() if item else ""

    def on_row_change(self, row):
        self.selected_id = int(self._item_text(row, 0))

        self.inputEmployees.setText(self._item_text(row, 1))
        self.inputEvent.setText(self._item_text(row, 2))
        self.inputAchievement.setText(self._item_text(row, 3))
        self.inputCity.setText(self._item_text(row, 4))
        self.inputOrganization.setText(self._item_text(row, 5))
        self.inputWork.setText(self._item_text(row, 6))

        date_str = self._item_text(row, 7)
        if date_str:
            self.inputAchDate.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))

        self.current_file_path = get_achievement_file(self.selected_id)
        self.file_path = None

    # ======================
    # ADD
    # ======================
    def add_achievement(self):
        form = self._collect_form()
        if form is None:
            return
        fields, employee_ids = form

        # достижение и участники сохраняются одной транзакцией
        ach_id = add_achievement(
            fields["event"],
            fields["achievement"],
            fields["city"],
            fields["organization"],
            fields["work_name"],
            fields["ach_date"],
            employee_ids,
        )

        file_path, attached = self._attach_file(ach_id, None)
        if attached:
            update_achievement_file(ach_id, file_path)
            self.history.add("achievement_file", ach_id, "add", None, file_path)

        self.history.add("achievement", ach_id, "add", None, get_achievement(ach_id))
        self.parent.history_tab.refresh()

        QtWidgets.QMessageBox.information(
            self.parent,
            "Успех",
            "Достижение добавлено"
        )

        self.file_path = None
        self.clear_fields()
        self.load_achievements()

    # ======================
    # UPDATE
    # ======================
    def update_achievement_data(self):
        if not self.selected_id:
            self._warn("Выберите достижение")
            return

        # Сначала проверка, потом любые изменения
        form = self._collect_form()
        if form is None:
            return
        fields, employee_ids = form

        ach_id = self.selected_id
        old_data = get_achievement(ach_id)

        if old_data is None:
            self._warn("Достижение не найдено: возможно, оно уже удалено")
            self.clear_fields()
            self.load_achievements()
            return

        success = update_achievement(
            ach_id,
            fields["event"],
            fields["achievement"],
            fields["city"],
            fields["organization"],
            fields["work_name"],
            fields["ach_date"],
            employee_ids,
        )

        if not success:
            QtWidgets.QMessageBox.critical(self.parent, "Ошибка", "Ошибка обновления")
            return

        file_path, attached = self._attach_file(ach_id, self.current_file_path)
        if attached:
            update_achievement_file(ach_id, file_path)
            self.history.add("achievement_file", ach_id, "update", self.current_file_path, file_path)

        self.file_path = None
        self.current_file_path = get_achievement_file(ach_id)

        QtWidgets.QMessageBox.information(
            self.parent,
            "Успех",
            "Данные достижения обновлены"
        )

        self.history.add("achievement", ach_id, "update", old_data, get_achievement(ach_id))
        self.parent.history_tab.refresh()

        self.load_achievements()

    def open_context_menu(self, position):
        row = self.table.currentRow()

        if row == -1:
            return

        ach_id = int(self._item_text(row, 0))
        file_path = get_achievement_file(ach_id)

        menu = QtWidgets.QMenu()

        if file_path:
            delete_action = menu.addAction("Удалить файл")

            action = menu.exec_(
                self.table.viewport().mapToGlobal(position)
            )

            if action == delete_action:
                self.delete_file(ach_id)

    # ======================
    # DELETE
    # ======================
    def delete_achievement(self):
        row = self.table.currentRow()
        if row == -1:
            self._warn("Выберите достижение")
            return

        ach_id = int(self._item_text(row, 0))
        old_data = get_achievement(ach_id)

        if old_data is None:
            self._warn("Достижение уже удалено")
            self.load_achievements()
            return

        reply = QtWidgets.QMessageBox.question(
            self.parent,
            "Подтверждение",
            "Вы действительно хотите удалить достижение?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        stored_file = get_achievement_file(ach_id)

        if not delete_achievement_by_id(ach_id):
            QtWidgets.QMessageBox.critical(self.parent, "Ошибка", "Ошибка удаления")
            return

        # вложение удаляем вместе с записью, чтобы не копились «осиротевшие» файлы
        FileService.delete_file(stored_file)

        self.history.add("achievement", ach_id, "delete", old_data, None)
        self.parent.history_tab.refresh()

        if self.selected_id == ach_id:
            self.clear_fields()

        QtWidgets.QMessageBox.information(
            self.parent,
            "Успех",
            "Достижение удалено"
        )

        self.load_achievements()

    def delete_file(self, ach_id):
        reply = QtWidgets.QMessageBox.question(
            self.parent,
            "Удаление файла",
            "Удалить прикреплённый файл?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        old_path = get_achievement_file(ach_id)

        FileService.delete_file(old_path)
        update_achievement_file(ach_id, None)

        if self.selected_id == ach_id:
            self.current_file_path = None

        self.history.add("achievement_file", ach_id, "delete", old_path, None)

        self.parent.history_tab.refresh()

        QtWidgets.QMessageBox.information(
            self.parent,
            "Успех",
            "Файл удалён"
        )

        self.load_achievements()

    # ======================
    # FILE
    # ======================
    def select_file(self):
        file, _ = QtWidgets.QFileDialog.getOpenFileName(self.parent)
        if file:
            self.file_path = file

    def open_file(self, row, col):
        ach_id = int(self._item_text(row, 0))
        path = get_achievement_file(ach_id)

        if path:
            try:
                FileService.open_file(path)
            except Exception as e:
                self._warn(str(e))

    # ======================
    # CLEAR
    # ======================
    def clear_fields(self):
        # После очистки «Обновить» не должен менять ранее выбранное достижение
        self.selected_id = None
        self.file_path = None
        self.current_file_path = None
        self.inputEvent.clear()
        self.inputAchievement.clear()
        self.inputCity.clear()
        self.inputOrganization.clear()
        self.inputWork.clear()
        self.inputEmployees.clear()
        self.inputAchDate.setDate(QDate.currentDate())
