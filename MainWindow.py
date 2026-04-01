from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import Qt
from database import add_employee, get_all_employees, delete_employee_by_id


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main.ui", self)

        self.tableEmployees.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.tableEmployees.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)

        self.inputName = self.findChild(QtWidgets.QLineEdit, "inputName")
        self.inputBirthDate = self.findChild(QtWidgets.QDateEdit, "inputBirthDate")
        self.inputPosition = self.findChild(QtWidgets.QLineEdit, "inputPosition")
        self.inputDegree = self.findChild(QtWidgets.QLineEdit, "inputDegree")
        self.inputRank = self.findChild(QtWidgets.QLineEdit, "inputRank")


        self.btnAddEmp = self.findChild(QtWidgets.QPushButton, "btnAddEmp")
        self.btnUpdateEmp = self.findChild(QtWidgets.QPushButton, "btnUpdateEmp")

        self.btnDeleteEmp = self.findChild(QtWidgets.QPushButton, "btnDeleteEmp")
        self.btnDeleteEmp.clicked.connect(self.delete_employee)

        self.tableEmployees = self.findChild(QtWidgets.QTableWidget, "tableEmployees")
        self.btnAddEmp.clicked.connect(self.add_employee)

        self.btnUpdateEmp.clicked.connect(self.load_employees)

        self.chkUseInterval = self.findChild(QtWidgets.QCheckBox, "chkUseInterval")
        self.dateStart = self.findChild(QtWidgets.QDateEdit, "dateStart")
        self.dateEnd = self.findChild(QtWidgets.QDateEdit, "dateEnd")
        self.spinReportYear = self.findChild(QtWidgets.QSpinBox, "spinReportYear")

        self.chkUseInterval.stateChanged.connect(self.toggle_interval)

        self.load_employees()

    def toggle_interval(self, state):
        enabled = state == Qt.Checked
        self.dateStart.setEnabled(enabled)
        self.dateEnd.setEnabled(enabled)
        self.spinReportYear.setEnabled(not enabled)

    def add_employee(self):
        fio = self.inputName.text()
        birth_date = self.inputBirthDate.date().toString("yyyy-MM-dd")
        position = self.inputPosition.text()
        degree = self.inputDegree.text()
        rank = self.inputRank.text()

        fio_no_spaces = fio.replace(' ', '')

        if fio and not (position or degree or rank):
            QtWidgets.QMessageBox.warning(
                self,
                "Ошибка",
                "При заполнении ФИО необходимо заполнить хотя бы одно из полей: должность, звание или степень"
            )
            return

        if fio or fio.isspace():
            QtWidgets.QMessageBox.warning(self, "Ошибка", "ФИО не может быть пустым или состоять только из пробелов")
            return

        if fio_no_spaces.isdigit():
            QtWidgets.QMessageBox.warning(self, "Ошибка","ФИО не может состоять из цифр")
            return

        add_employee(fio, birth_date, position, degree, rank)

        QtWidgets.QMessageBox.information(self, "Успех", "Сотрудник добавлен")

        self.clear_fields()
        self.load_employees()

    def load_employees(self):
        data = get_all_employees()

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

    def delete_employee(self):
        selected_row = self.tableEmployees.currentRow()

        if selected_row == -1:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Выберите сотрудника")
            return

        employee_id_item = self.tableEmployees.item(selected_row, 0)

        if employee_id_item is None:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Не удалось получить ID")
            return

        try:
            employee_id = int(employee_id_item.text())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Ошибка", "Некорректный ID сотрудника")
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Подтверждение",
            "Удалить сотрудника?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )

        if reply == QtWidgets.QMessageBox.Yes:
            success = delete_employee_by_id(employee_id)

            if success:
                QtWidgets.QMessageBox.information(self, "Успех", "Сотрудник удалён")
            else:
                QtWidgets.QMessageBox.critical(self, "Ошибка", "Не удалось удалить сотрудника")

            self.load_employees()

    def clear_fields(self):
        self.inputName.clear()
        self.inputPosition.clear()
        self.inputDegree.clear()
        self.inputRank.clear()


