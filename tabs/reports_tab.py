from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from openpyxl import Workbook
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

        self.filter_active = False

        self.selected_employees = []

        parent.btnSelectEmployees.clicked.connect(
            self.select_employees
        )

        self.parent.chkUseInterval.toggled.connect(
            self.toggle_interval
        )

        self.parent.btnExportExcel.clicked.connect(
            self.export_excel
        )

    # ======================
    # ПО СОТРУДНИКАМ
    # ======================

    def report_by_employee(self):

        employees = get_all_employees()

        if self.filter_active:
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
        self.parent.lblReportInfo.setText(
            f"Сотрудников: {len(employees)}"
        )

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

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
            self.filter_active = True
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

        from datetime import datetime

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

        use_interval = self.parent.chkUseInterval.isChecked()

        start_date = self.parent.dateStart.date().toPyDate()
        end_date = self.parent.dateEnd.date().toPyDate()

        # Публикации
        for pub in get_all_publications():

            date_str = str(pub[6]) if pub[6] else ""

            try:
                pub_date = datetime.strptime(
                    date_str,
                    "%Y-%m-%d"
                ).date()

            except:
                continue

            if use_interval:

                if start_date <= pub_date <= end_date:
                    rows.append([
                        "Публикация",
                        pub[1],
                        date_str,
                        pub[7] or ""
                    ])

            else:

                if pub_date.year == int(year):
                    rows.append([
                        "Публикация",
                        pub[1],
                        date_str,
                        pub[7] or ""
                    ])

        # Достижения
        for ach in get_all_achievements():

            date_str = str(ach[7]) if ach[7] else ""

            try:
                ach_date = datetime.strptime(
                    date_str,
                    "%Y-%m-%d"
                ).date()

            except:
                continue

            if use_interval:

                if start_date <= ach_date <= end_date:
                    rows.append([
                        "Достижение",
                        ach[3],
                        date_str,
                        ach[1] or ""
                    ])

            else:

                if ach_date.year == int(year):
                    rows.append([
                        "Достижение",
                        ach[3],
                        date_str,
                        ach[1] or ""
                    ])

        self.table.setRowCount(len(rows))

        for r, row_data in enumerate(rows):

            for c, value in enumerate(row_data):
                self.table.setItem(
                    r,
                    c,
                    QtWidgets.QTableWidgetItem(str(value))
                )

        self.parent.lblReportInfo.setText(
            f"Найдено записей: {len(rows)}"
        )

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        self.table.resizeColumnsToContents()

    def toggle_interval(self, checked):

        self.parent.dateStart.setEnabled(checked)
        self.parent.dateEnd.setEnabled(checked)

    # ======================
    # ПО УРОВНЮ
    # ======================

    def report_by_level(self):

        level = self.parent.comboReportLevel.currentText()

        if level == "Все уровни":
            publications = get_all_publications()
        else:
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

        self.parent.lblReportInfo.setText(
            f"Публикаций уровня '{level}': {len(publications)}"
        )

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        self.table.resizeColumnsToContents()

    def export_excel(self):

        if self.table.rowCount() == 0:
            QMessageBox.warning(
                self.parent,
                "Экспорт",
                "Сначала сформируйте отчет."
            )

            return

        filename, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Сохранить отчет",
            "report.xlsx",
            "Excel (*.xlsx)"
        )

        if not filename:
            return

        try:

            wb = Workbook()
            ws = wb.active

            ws.title = "Отчет"

            headers = []

            for col in range(self.table.columnCount()):
                item = self.table.horizontalHeaderItem(col)

                headers.append(
                    item.text() if item else ""
                )

            ws.append(headers)

            for row in range(self.table.rowCount()):

                values = []

                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)

                    values.append(
                        item.text() if item else ""
                    )

                ws.append(values)

            wb.save(filename)

            QMessageBox.information(
                self.parent,
                "Экспорт",
                "Отчет успешно сохранен."
            )

        except Exception as e:

            QMessageBox.critical(
                self.parent,
                "Ошибка",
                str(e)
            )