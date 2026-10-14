from datetime import datetime

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from openpyxl import Workbook

from database import (
    get_all_achievements,
    get_all_employees,
    get_all_publications,
    get_employee_report,
)
from dialogs.employee_selector import EmployeeSelectorDialog
from ui_common import cell_text


def parse_date(value):
    """Дата из строки yyyy-MM-dd или None, если строка не дата."""
    try:
        return datetime.strptime(str(value or ""), "%Y-%m-%d").date()
    except ValueError:
        return None


class ReportsTab:
    def __init__(self, parent):
        self.parent = parent

        self.table = parent.tableReports

        parent.btnReportByEmployee.clicked.connect(self.report_by_employee)
        parent.btnReportByYear.clicked.connect(self.report_by_year)
        parent.btnReportByLevel.clicked.connect(self.report_by_level)

        # Выбранные сотрудники: пустой список означает «все»
        self.selected_employees = []

        parent.btnSelectEmployees.clicked.connect(self.select_employees)
        parent.chkUseInterval.toggled.connect(self.toggle_interval)
        parent.btnExportExcel.clicked.connect(self.export_excel)

        # начальное состояние полей интервала соответствует флажку
        self.toggle_interval(parent.chkUseInterval.isChecked())

    # ======================
    # ВСПОМОГАТЕЛЬНОЕ
    # ======================

    def _show_table(self, headers, rows):
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))

        for r, row_data in enumerate(rows):
            for c, value in enumerate(row_data):
                self.table.setItem(r, c, QtWidgets.QTableWidgetItem(cell_text(value)))

        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

    # ======================
    # ПО СОТРУДНИКАМ
    # ======================

    def report_by_employee(self):
        selected_ids = None
        if self.selected_employees:
            by_fio = {row["fio"]: row["id"] for row in get_all_employees()}
            selected_ids = {by_fio[fio] for fio in self.selected_employees if fio in by_fio}

        # связи берутся по id, а не поиском ФИО внутри текста
        report = get_employee_report(selected_ids)

        rows = [
            (fio, "\n".join(pubs), "\n".join(achs))
            for _id, fio, pubs, achs in report
        ]

        self._show_table(["Сотрудник", "Публикации", "Достижения"], rows)
        self.parent.lblReportInfo.setText(f"Сотрудников: {len(rows)}")

    def select_employees(self):
        employees = [row["fio"] for row in get_all_employees()]

        dlg = EmployeeSelectorDialog(employees, self.selected_employees, self.parent)

        if dlg.exec_():
            self.selected_employees = dlg.get_selected()

            if self.selected_employees:
                self.parent.lblSelectedEmployees.setText("; ".join(self.selected_employees))
            else:
                self.parent.lblSelectedEmployees.setText("Все сотрудники")

    # ======================
    # ПО ГОДУ
    # ======================

    def report_by_year(self):
        year = self.parent.spinReportYear.value()
        use_interval = self.parent.chkUseInterval.isChecked()

        start_date = self.parent.dateStart.date().toPyDate()
        end_date = self.parent.dateEnd.date().toPyDate()

        if use_interval and start_date > end_date:
            QMessageBox.warning(
                self.parent, "Ошибка", "Начало интервала позже его конца"
            )
            return

        def fits(day):
            if day is None:
                return False
            if use_interval:
                return start_date <= day <= end_date
            return day.year == year

        rows = []

        for pub in get_all_publications():
            if fits(parse_date(pub[6])):
                rows.append(("Публикация", pub[1], pub[6], pub[7]))

        for ach in get_all_achievements():
            if fits(parse_date(ach[7])):
                rows.append(("Достижение", ach[3], ach[7], ach[1]))

        self._show_table(["Тип", "Название", "Дата", "Сотрудники"], rows)
        self.parent.lblReportInfo.setText(f"Найдено записей: {len(rows)}")

    def toggle_interval(self, checked):
        self.parent.dateStart.setEnabled(checked)
        self.parent.dateEnd.setEnabled(checked)
        self.parent.spinReportYear.setEnabled(not checked)

    # ======================
    # ПО УРОВНЮ
    # ======================

    def report_by_level(self):
        level = self.parent.comboReportLevel.currentText()

        publications = get_all_publications()
        if level != "Все уровни":
            publications = [p for p in publications if p[3] == level]

        rows = [(p[1], p[2], p[3], p[7]) for p in publications]

        self._show_table(["Название", "Издание", "Уровень", "Авторы"], rows)
        self.parent.lblReportInfo.setText(
            f"Публикаций уровня '{level}': {len(rows)}"
        )

    # ======================
    # ЭКСПОРТ
    # ======================

    def export_excel(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self.parent, "Экспорт", "Сначала сформируйте отчет.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Сохранить отчет",
            "report.xlsx",
            "Excel (*.xlsx)"
        )

        if not filename:
            return

        if not filename.lower().endswith(".xlsx"):
            filename += ".xlsx"

        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Отчет"

            headers = []
            for col in range(self.table.columnCount()):
                item = self.table.horizontalHeaderItem(col)
                headers.append(item.text() if item else "")
            ws.append(headers)

            for row in range(self.table.rowCount()):
                values = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    values.append(item.text() if item else "")
                ws.append(values)

            # Всё записывается как текст: строка вида «=1+1» не должна
            # превратиться в формулу при открытии в Excel.
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    if isinstance(cell.value, str):
                        cell.data_type = "s"

            wb.save(filename)

            QMessageBox.information(self.parent, "Экспорт", "Отчет успешно сохранен.")

        except OSError as e:
            QMessageBox.critical(
                self.parent, "Ошибка", f"Не удалось сохранить файл: {e}"
            )
