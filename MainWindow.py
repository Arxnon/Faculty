from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import Qt, QDate

from database import (
    add_employee,
    get_all_employees,
    delete_employee_by_id,
    search_employees_by_fio,
    update_employee
)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main.ui", self)
        try:
            with open("style.qss", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Не удалось загрузить стиль: {e}")

        self.selected_employee_id = None

        # Таблица
        self.tableEmployees.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.tableEmployees.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)

        # Поля
        self.inputName = self.findChild(QtWidgets.QLineEdit, "inputName")
        self.inputBirthDate = self.findChild(QtWidgets.QDateEdit, "inputBirthDate")
        self.inputPosition = self.findChild(QtWidgets.QLineEdit, "inputPosition")
        self.inputDegree = self.findChild(QtWidgets.QLineEdit, "inputDegree")
        self.inputRank = self.findChild(QtWidgets.QLineEdit, "inputRank")

        # Поиск
        self.inputSearch = self.findChild(QtWidgets.QLineEdit, "searchEmployees")
        self.inputSearch.textChanged.connect(self.search_employee)

        # Кнопки
        self.btnAddEmp.clicked.connect(self.add_employee)
        self.btnDeleteEmp.clicked.connect(self.delete_employee)
        self.btnUpdateEmp.clicked.connect(self.update_employee_data)

        # Клик по таблице
        self.tableEmployees.cellClicked.connect(self.load_employee_to_fields)

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
            QtWidgets.QMessageBox.warning(self, "Ошибка",
                                          "ФИО не может быть пустым или состоять только из пробелов и/или цифр")
            return

        add_employee(fio, birth_date, position, degree, rank)

        QtWidgets.QMessageBox.information(self, "Успех", "Сотрудник добавлен")

        self.clear_fields()
        self.load_employees()

    def delete_employee(self):
        selected_row = self.tableEmployees.currentRow()

        if selected_row == -1:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите сотрудника")
            return

        employee_id = int(self.get_item_text(selected_row, 0))

        success = delete_employee_by_id(employee_id)

        if success:
            QtWidgets.QMessageBox.information(self, "Успех", "Сотрудник удалён")
        else:
            QtWidgets.QMessageBox.critical(self, "Ошибка", "Не удалось удалить")

        self.load_employees()

    def load_employee_to_fields(self, row, _):
        self.selected_employee_id = int(self.get_item_text(row, 0))

        self.inputName.setText(self.get_item_text(row, 1))

        date_str = self.get_item_text(row, 2)
        if date_str:
            self.inputBirthDate.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))

        self.inputPosition.setText(self.get_item_text(row, 3))
        self.inputDegree.setText(self.get_item_text(row, 4))
        self.inputRank.setText(self.get_item_text(row, 5))

    def update_employee_data(self):
        if not self.selected_employee_id:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите сотрудника")
            return

        # Получаем значения из полей
        fio = self.inputName.text()
        birth_date = self.inputBirthDate.date().toString("yyyy-MM-dd")
        position = self.inputPosition.text()
        degree = self.inputDegree.text()
        rank = self.inputRank.text()

        # Получаем значения из таблицы для сравнения
        selected_row = self.tableEmployees.currentRow()
        if selected_row == -1:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите строку в таблице")
            return

        old_fio = self.get_item_text(selected_row, 1)
        old_birth_date = self.get_item_text(selected_row, 2)
        old_position = self.get_item_text(selected_row, 3)
        old_degree = self.get_item_text(selected_row, 4)
        old_rank = self.get_item_text(selected_row, 5)

        # Проверяем, изменилось ли хотя бы одно поле
        if (fio == old_fio and
                birth_date == old_birth_date and
                position == old_position and
                degree == old_degree and
                rank == old_rank):
            QtWidgets.QMessageBox.information(self, "Внимание", "Выберите поле для изменения")
            return

        # Обновляем
        success = update_employee(
            self.selected_employee_id,
            fio,
            birth_date,
            position,
            degree,
            rank
        )

        if success:
            QtWidgets.QMessageBox.information(self, "Успех", "Данные обновлены")
            self.load_employees()
            self.clear_fields()
            self.selected_employee_id = None
        else:
            QtWidgets.QMessageBox.critical(self, "Ошибка", "Не удалось обновить")

    def clear_fields(self):
        self.inputName.clear()
        self.inputPosition.clear()
        self.inputDegree.clear()
        self.inputRank.clear()

