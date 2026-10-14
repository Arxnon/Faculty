from PyQt5 import QtWidgets
from PyQt5.QtCore import QDate

from database import (
    DuplicateEmployeeError,
    add_employee,
    count_employee_links,
    delete_employee_by_id,
    get_all_employees,
    get_employee,
    search_employees_by_fio,
    update_employee,
)
from ui_common import cell_text

FIO_ERROR = "ФИО не может быть пустым или состоять только из пробелов и/или цифр"


def is_valid_fio(fio):
    stripped = (fio or "").strip()
    return bool(stripped) and not stripped.replace(" ", "").isdigit()


class EmployeesTab:
    def __init__(self, parent, history_service):
        self.parent = parent
        self.history = history_service

        # Состояние
        self.selected_employee_id = None
        self.is_dirty = False

        # Таблица
        self.tableEmployees = parent.tableEmployees
        self.tableEmployees.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.tableEmployees.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)
        self.tableEmployees.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # Поля
        self.inputName = parent.inputName
        self.inputBirthDate = parent.inputBirthDate
        self.inputPosition = parent.inputPosition
        self.inputDegree = parent.inputDegree
        self.inputRank = parent.inputRank

        # Поиск
        self.inputSearch = parent.searchEmployees
        self.inputSearch.textChanged.connect(self.search_employee)

        # Кнопки
        parent.btnAddEmp.clicked.connect(self.add_employee)
        parent.btnDeleteEmp.clicked.connect(self.delete_employee)
        parent.btnUpdateEmp.clicked.connect(self.update_employee_data)

        # Таблица клик
        self.tableEmployees.cellClicked.connect(self.on_row_change)

        # Отслеживание изменений
        self.inputName.textChanged.connect(self.mark_dirty)
        self.inputPosition.textChanged.connect(self.mark_dirty)
        self.inputDegree.textChanged.connect(self.mark_dirty)
        self.inputRank.textChanged.connect(self.mark_dirty)
        self.inputBirthDate.dateChanged.connect(self.mark_dirty)

        self.load_employees()

    # ======================
    # ВСПОМОГАТЕЛЬНОЕ
    # ======================
    def get_item_text(self, row, col):
        item = self.tableEmployees.item(row, col)
        return item.text() if item else ""

    def _row_of(self, employee_id):
        """Номер строки таблицы с данным сотрудником (или None)."""
        for row in range(self.tableEmployees.rowCount()):
            if self.get_item_text(row, 0) == str(employee_id):
                return row
        return None

    def _select_row_by_id(self, employee_id):
        row = self._row_of(employee_id)
        if row is not None:
            self.tableEmployees.selectRow(row)
        return row

    def _form_data(self):
        return {
            "fio": " ".join(self.inputName.text().split()),
            "birth_date": self.inputBirthDate.date().toString("yyyy-MM-dd"),
            "position": self.inputPosition.text().strip(),
            "degree": self.inputDegree.text().strip(),
            "rank": self.inputRank.text().strip(),
        }

    @staticmethod
    def _row_to_dict(row):
        return {
            "fio": row["fio"],
            "birth_date": row["birth_date"],
            "position": row["position"],
            "degree": row["degree"],
            "rank": row["rank"],
        }

    def _record(self, employee_id, action, old_data, new_data):
        self.history.add("employee", employee_id, action, old_data, new_data)
        self.parent.history_tab.refresh()

    def refresh_related_tabs(self):
        """Список сотрудников используют вкладки публикаций и достижений."""
        publications = getattr(self.parent, "publications_tab", None)
        if publications is not None:
            publications.refresh_authors_list()
            publications.load_publications()

        achievements = getattr(self.parent, "achievements_tab", None)
        if achievements is not None:
            achievements.refresh_employees()
            achievements.load_achievements()

    def fill_table(self, data):
        self.tableEmployees.setRowCount(len(data))
        self.tableEmployees.setColumnCount(6)
        self.tableEmployees.setHorizontalHeaderLabels([
            "Id", "ФИО", "Дата рождения", "Должность", "Степень", "Звание"
        ])

        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                self.tableEmployees.setItem(
                    row_idx,
                    col_idx,
                    QtWidgets.QTableWidgetItem(cell_text(value))
                )

        # скрываем ID
        self.tableEmployees.setColumnHidden(0, True)

        if self.selected_employee_id is not None:
            self._select_row_by_id(self.selected_employee_id)

    # ======================
    # ЗАГРУЗКА
    # ======================

    def load_employees(self):
        self.fill_table(get_all_employees())

    def search_employee(self):
        fio = self.inputSearch.text().strip()

        if not fio:
            self.load_employees()
            return

        self.fill_table(search_employees_by_fio(fio))

    # ======================
    # ЛОГИКА ИЗМЕНЕНИЙ
    # ======================

    def mark_dirty(self):
        if self.selected_employee_id is not None:
            self.is_dirty = True

    def on_row_change(self, row):
        clicked_id = int(self.get_item_text(row, 0))

        if self.is_dirty and self.selected_employee_id is not None:
            reply = QtWidgets.QMessageBox.question(
                self.parent,
                "Сохранить изменения?",
                "Вы изменили данные. Сохранить?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel
            )

            if reply == QtWidgets.QMessageBox.Yes:
                if not self.update_employee_data():
                    # Не сохранилось: остаёмся на прежнем сотруднике, ничего не теряем
                    self._select_row_by_id(self.selected_employee_id)
                    return

            elif reply == QtWidgets.QMessageBox.No:
                self.is_dirty = False

            else:
                self._select_row_by_id(self.selected_employee_id)
                return

        # После сохранения таблица перезагружена и порядок строк мог измениться,
        # поэтому нужную строку ищем по id, а не по номеру.
        new_row = self._select_row_by_id(clicked_id)
        if new_row is not None:
            self.load_employee_to_fields(new_row)
        self.is_dirty = False

    # ======================
    # CRUD
    # ======================

    def add_employee(self):
        data = self._form_data()

        if not is_valid_fio(data["fio"]):
            QtWidgets.QMessageBox.warning(self.parent, "Ошибка", FIO_ERROR)
            return

        try:
            employee_id = add_employee(**data)
        except DuplicateEmployeeError as exc:
            QtWidgets.QMessageBox.warning(self.parent, "Ошибка", str(exc))
            return

        self._record(employee_id, "add", None, data)

        QtWidgets.QMessageBox.information(self.parent, "Успех", "Сотрудник добавлен")

        self.clear_fields()
        self.load_employees()
        self.refresh_related_tabs()

    def delete_employee(self):
        row = self.tableEmployees.currentRow()

        if row == -1:
            QtWidgets.QMessageBox.warning(self.parent, "Ошибка", "Выберите сотрудника")
            return

        employee_id = int(self.get_item_text(row, 0))
        employee = get_employee(employee_id)

        if employee is None:
            QtWidgets.QMessageBox.warning(self.parent, "Ошибка", "Сотрудник уже удалён")
            self.load_employees()
            return

        question = f"Удалить сотрудника «{employee['fio']}»?"
        publications, achievements = count_employee_links(employee_id)
        if publications or achievements:
            question += (
                f"\n\nОн указан в публикациях: {publications}, в достижениях: {achievements}. "
                "Эти связи будут удалены (сами публикации и достижения останутся)."
            )

        reply = QtWidgets.QMessageBox.question(
            self.parent,
            "Подтверждение",
            question,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            return

        old_data = self._row_to_dict(employee)

        if delete_employee_by_id(employee_id):
            self._record(employee_id, "delete", old_data, None)
            QtWidgets.QMessageBox.information(self.parent, "Успех", "Удалено")
        else:
            QtWidgets.QMessageBox.critical(self.parent, "Ошибка", "Ошибка удаления")

        if self.selected_employee_id == employee_id:
            self.clear_fields()

        self.load_employees()
        self.refresh_related_tabs()

    def update_employee_data(self):
        """Сохраняет изменения выбранного сотрудника. Возвращает True, если всё получилось."""
        if self.selected_employee_id is None:
            QtWidgets.QMessageBox.warning(self.parent, "Ошибка", "Выберите сотрудника")
            return False

        data = self._form_data()

        if not is_valid_fio(data["fio"]):
            QtWidgets.QMessageBox.warning(self.parent, "Ошибка", FIO_ERROR)
            return False

        # Прежние данные берём из базы, а не из таблицы: к этому моменту
        # в таблице уже может быть выделена другая строка.
        old_row = get_employee(self.selected_employee_id)
        if old_row is None:
            QtWidgets.QMessageBox.warning(self.parent, "Ошибка", "Сотрудник не найден: возможно, он уже удалён")
            self.clear_fields()
            self.load_employees()
            return False

        try:
            success = update_employee(self.selected_employee_id, **data)
        except DuplicateEmployeeError as exc:
            QtWidgets.QMessageBox.warning(self.parent, "Ошибка", str(exc))
            return False

        if not success:
            QtWidgets.QMessageBox.critical(self.parent, "Ошибка", "Ошибка обновления")
            return False

        self._record(self.selected_employee_id, "update", self._row_to_dict(old_row), data)

        QtWidgets.QMessageBox.information(self.parent, "Успех", "Обновлено")
        self.is_dirty = False
        self.load_employees()
        self.refresh_related_tabs()
        return True

    def load_employee_to_fields(self, row):
        self.selected_employee_id = int(self.get_item_text(row, 0))

        widgets = (
            self.inputName, self.inputBirthDate, self.inputPosition,
            self.inputDegree, self.inputRank,
        )
        # блокируем сигналы, чтобы заполнение полей не считалось правкой
        for widget in widgets:
            widget.blockSignals(True)

        self.inputName.setText(self.get_item_text(row, 1))

        date_str = self.get_item_text(row, 2)
        if date_str:
            self.inputBirthDate.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))

        self.inputPosition.setText(self.get_item_text(row, 3))
        self.inputDegree.setText(self.get_item_text(row, 4))
        self.inputRank.setText(self.get_item_text(row, 5))

        for widget in widgets:
            widget.blockSignals(False)

    def clear_fields(self):
        # Сначала сбрасываем выбор, чтобы очистка полей не отмечала форму изменённой
        self.selected_employee_id = None
        self.inputName.clear()
        self.inputPosition.clear()
        self.inputDegree.clear()
        self.inputRank.clear()
        self.is_dirty = False
