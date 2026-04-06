from PyQt5 import QtWidgets
import rust_core
from PyQt5.QtGui import QTextDocument, QTextCursor, QColor, QTextCharFormat

from database import (
    add_employee,
    get_all_employees,
    delete_employee_by_id,
    search_employees_by_fio,
    update_employee
)


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
                    QtWidgets.QTableWidgetItem(str(value))
                )

        # скрываем ID
        self.tableEmployees.setColumnHidden(0, True)

    # ======================
    # ЗАГРУЗКА
    # ======================

    def load_employees(self):
        data = get_all_employees()
        self.fill_table(data)

    def search_employee(self):
        fio = self.inputSearch.text().strip()

        if not fio:
            self.load_employees()
            return

        data = search_employees_by_fio(fio)
        self.fill_table(data)

    # ======================
    # ЛОГИКА ИЗМЕНЕНИЙ
    # ======================

    def mark_dirty(self):
        if self.selected_employee_id is not None:
            self.is_dirty = True

    def on_row_change(self, row,):
        current_row = self.tableEmployees.currentRow()

        if self.is_dirty:
            reply = QtWidgets.QMessageBox.question(
                self.parent,
                "Сохранить изменения?",
                "Вы изменили данные. Сохранить?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel
            )

            if reply == QtWidgets.QMessageBox.Yes:
                self.update_employee_data()

            elif reply == QtWidgets.QMessageBox.No:
                self.is_dirty = False

            elif reply == QtWidgets.QMessageBox.Cancel:
                self.tableEmployees.blockSignals(True)
                self.tableEmployees.selectRow(current_row)
                self.tableEmployees.blockSignals(False)
                return

        self.load_employee_to_fields(row)
        self.is_dirty = False

    # ======================
    # CRUD
    # ======================

    def add_employee(self):
        fio = self.inputName.text()
        birth_date = self.inputBirthDate.date().toString("yyyy-MM-dd")
        position = self.inputPosition.text()
        degree = self.inputDegree.text()
        rank = self.inputRank.text()

        fio_stripped = fio.replace(" ", "")

        if not fio or fio_stripped == "" or fio_stripped.isdigit():
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Ошибка",
                "ФИО не может быть пустым или состоять только из пробелов и/или цифр"
            )
            return

        # добавляем сотрудника в БД и получаем его ID
        employee_id = add_employee(fio, birth_date, position, degree, rank)

        # история
        self.history.add(
            "employee",
            employee_id,
            "add",
            None,
            str({
                "fio": fio,
                "birth_date": birth_date,
                "position": position,
                "degree": degree,
                "rank": rank
            })
        )

        # обновляем вкладку истории
        self.parent.history_tab.refresh()

        QtWidgets.QMessageBox.information(self.parent, "Успех", "Сотрудник добавлен")

        self.clear_fields()
        self.load_employees()

    def delete_employee(self):
        row = self.tableEmployees.currentRow()

        if row == -1:
            QtWidgets.QMessageBox.warning(self.parent, "Ошибка", "Выберите сотрудника")
            return

        employee_id = int(self.get_item_text(row, 0))

        old_data = str({
            "fio": self.get_item_text(row, 1),
            "birth_date": self.get_item_text(row, 2),
            "position": self.get_item_text(row, 3),
            "degree": self.get_item_text(row, 4),
            "rank": self.get_item_text(row, 5),
        })

        success = delete_employee_by_id(employee_id)

        if success:
            # история
            self.history.add(
                "employee",
                employee_id,
                "delete",
                old_data,
                None
            )

            # обновляем вкладку истории
            self.parent.history_tab.refresh()

            QtWidgets.QMessageBox.information(self.parent, "Успех", "Удалено")
        else:
            QtWidgets.QMessageBox.critical(self.parent, "Ошибка", "Ошибка удаления")

        self.load_employees()

    def update_employee_data(self):
        if self.selected_employee_id is None:
            QtWidgets.QMessageBox.warning(self.parent, "Ошибка", "Выберите сотрудника")
            return

        row = self.tableEmployees.currentRow()

        old_data = str({
            "fio": self.get_item_text(row, 1),
            "birth_date": self.get_item_text(row, 2),
            "position": self.get_item_text(row, 3),
            "degree": self.get_item_text(row, 4),
            "rank": self.get_item_text(row, 5),
        })

        fio = self.inputName.text()
        birth_date = self.inputBirthDate.date().toString("yyyy-MM-dd")
        position = self.inputPosition.text()
        degree = self.inputDegree.text()
        rank = self.inputRank.text()

        #ВАЛИДАЦИЯ
        if not fio.strip() or fio.strip().isdigit():
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Ошибка",
                "ФИО не может быть пустым или состоять только из пробелов и/или цифр"
            )
            return

        new_data = str({
            "fio": fio,
            "birth_date": birth_date,
            "position": position,
            "degree": degree,
            "rank": rank,
        })

        success = update_employee(
            self.selected_employee_id,
            fio,
            birth_date,
            position,
            degree,
            rank
        )

        if success:
            self.history.add(
                "employee",
                self.selected_employee_id,
                "update",
                old_data,
                new_data
            )

            self.parent.history_tab.refresh()

            QtWidgets.QMessageBox.information(self.parent, "Успех", "Обновлено")
            self.load_employees()
            self.is_dirty = False
        else:
            QtWidgets.QMessageBox.critical(self.parent, "Ошибка", "Ошибка обновления")

    def load_employee_to_fields(self, row):
        self.selected_employee_id = int(self.get_item_text(row, 0))

        # блокируем сигналы
        self.inputName.blockSignals(True)
        self.inputBirthDate.blockSignals(True)
        self.inputPosition.blockSignals(True)
        self.inputDegree.blockSignals(True)
        self.inputRank.blockSignals(True)

        self.inputName.setText(self.get_item_text(row, 1))

        date_str = self.get_item_text(row, 2)
        if date_str:
            from PyQt5.QtCore import QDate
            self.inputBirthDate.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))

        self.inputPosition.setText(self.get_item_text(row, 3))
        self.inputDegree.setText(self.get_item_text(row, 4))
        self.inputRank.setText(self.get_item_text(row, 5))

        # включаем обратно
        self.inputName.blockSignals(False)
        self.inputBirthDate.blockSignals(False)
        self.inputPosition.blockSignals(False)
        self.inputDegree.blockSignals(False)
        self.inputRank.blockSignals(False)

    def clear_fields(self):
        self.inputName.clear()
        self.inputPosition.clear()
        self.inputDegree.clear()
        self.inputRank.clear()