from PyQt5 import QtWidgets
from database import (
    get_all_employees,
    get_all_publications,
    get_all_achievements
)
from dialogs.employee_selector import EmployeeSelectorDialog

class ReportsTab:
    def __init__(self, parent):
        self.parent = parent

        self.table = parent.tableReports

        self.btnEmployee = parent.btnReportByEmployee
        self.btnYear = parent.btnReportByYear
        self.btnLevel = parent.btnReportByLevel

        self.btnEmployee.clicked.connect(self.report_by_employee)
        self.btnYear.clicked.connect(self.report_by_year)
        self.btnLevel.clicked.connect(self.report_by_level)

        self.selected_employees = []

        parent.btnSelectEmployees.clicked.connect(
            self.select_employees
        )

        self.parent.chkUseInterval.toggled.connect(
            self.toggle_interval
        )

    # ======================
    # ПО СОТРУДНИКАМ
    # ======================

    def report_by_employee(self):

        employees = get_all_employees()

        if self.selected_employees:
            employees = [
                e for e in employees
                if e[1] in self.selected_employees
            ]

        self.table.clear()
        self.table.setColumnCount(3)

        self.table.setHorizontalHeaderLabels([
            "Сотрудник",
            "Публикации",
            "Достижения"
        ])

        self.table.setRowCount(len(employees))

        publications = get_all_publications()
        achievements = get_all_achievements()

        for row, emp in enumerate(employees):

            fio = emp[1]

            pubs = []
            achs = []

            for p in publications:
                authors = str(p[7]) if p[7] else ""

                if fio in authors:
                    pubs.append(p[1])

            for a in achievements:
                employees_text = str(a[1]) if a[1] else ""

                if fio in employees_text:
                    achs.append(a[3])

            self.table.setItem(
                row, 0,
                QtWidgets.QTableWidgetItem(fio)
            )

            self.table.setItem(
                row, 1,
                QtWidgets.QTableWidgetItem("\n".join(pubs))
            )

            self.table.setItem(
                row, 2,
                QtWidgets.QTableWidgetItem("\n".join(achs))
            )

        self.table.resizeColumnsToContents()

    def select_employees(self):

        employees = sorted([
            emp[1]
            for emp in get_all_employees()
        ])

        dlg = EmployeeSelectorDialog(
            employees,
            self.selected_employees
        )

        if dlg.exec_():

            self.selected_employees = dlg.get_selected()

            if self.selected_employees:

                self.parent.lblSelectedEmployees.setText(
                    "; ".join(self.selected_employees)
                )

            else:

                self.parent.lblSelectedEmployees.setText(
                    "Все сотрудники"
                )

    # ======================
    # ПО ГОДУ
    # ======================

    def report_by_year(self):

        year = str(self.parent.spinReportYear.value())

        self.table.clear()
        self.table.setColumnCount(4)

        self.table.setHorizontalHeaderLabels([
            "Тип",
            "Название",
            "Дата",
            "Сотрудники"
        ])

        rows = []

        for pub in get_all_publications():

            date = str(pub[6])

            if year in date:
                rows.append([
                    "Публикация",
                    pub[1],
                    date,
                    pub[7]
                ])

        for ach in get_all_achievements():

            # когда появится дата достижения
            # можно заменить индекс

            rows.append([
                "Достижение",
                ach[3],
                "",
                ach[1]
            ])

        self.table.setRowCount(len(rows))

        for r, row_data in enumerate(rows):
            for c, value in enumerate(row_data):
                self.table.setItem(
                    r,
                    c,
                    QtWidgets.QTableWidgetItem(str(value))
                )

        self.table.resizeColumnsToContents()

    def toggle_interval(self, checked):

        self.parent.dateStart.setEnabled(checked)
        self.parent.dateEnd.setEnabled(checked)

    # ======================
    # ПО УРОВНЮ
    # ======================

    def report_by_level(self):

        level = self.parent.comboReportLevel.currentText()

        publications = [
            p for p in get_all_publications()
            if p[3] == level
        ]

        self.table.clear()
        self.table.setColumnCount(4)

        self.table.setHorizontalHeaderLabels([
            "Название",
            "Издание",
            "Уровень",
            "Авторы"
        ])

        self.table.setRowCount(len(publications))

        for r, pub in enumerate(publications):

            self.table.setItem(
                r, 0,

        QtWidgets.QTableWidgetItem(str(pub[1]))
            )

            self.table.setItem(
                r, 1,
                QtWidgets.QTableWidgetItem(str(pub[2]))
            )

            self.table.setItem(
                r, 2,
                QtWidgets.QTableWidgetItem(str(pub[3]))
            )

            self.table.setItem(
                r, 3,
                QtWidgets.QTableWidgetItem(str(pub[7]))
            )

        self.table.resizeColumnsToContents()