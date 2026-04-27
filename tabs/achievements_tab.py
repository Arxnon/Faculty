from PyQt5 import QtWidgets
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import QCompleter

from services.file_service import FileService
from database import (
    get_all_achievements,
    add_achievement,
    delete_achievement_by_id,
    update_achievement,
    get_achievement_file,
    update_achievement_file,
    clear_achievement_employees,
    get_all_employees,
    link_employee_achievement
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
        self.inputEmployees = parent.inputEmployeeName # <- аналог authors

        # SEARCH
        self.search = parent.searchAchievements
        self.search.textChanged.connect(self.search_achievements)

        # BUTTONS
        parent.btnAddAch.clicked.connect(self.add_achievement)
        parent.btnUpdateAch.clicked.connect(self.update_achievement_data)
        parent.btnDeleteAch.clicked.connect(self.delete_achievement)
        parent.btnFileAch.clicked.connect(self.select_file)

        # EVENTS
        self.table.cellClicked.connect(self.on_row_change)
        self.table.cellDoubleClicked.connect(self.open_file)

        self.refresh_employees()
        self.load_achievements()

        self.employee_map = {}

    # ======================
    # EMPLOYEES (как authors)
    # ======================
    def refresh_employees(self):
        employees = get_all_employees()
        fio_list = [emp[1] for emp in employees]

        self.employee_map = {emp[1]: emp[0] for emp in employees}

        completer = MultiCompleter(fio_list)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)

        self.inputEmployees.setCompleter(completer)

    # ======================
    # TABLE
    # ======================
    def fill_table(self, data):
        self.table.setRowCount(len(data))
        self.table.setColumnCount(8)

        self.table.setHorizontalHeaderLabels([
            "ID",
            "Сотрудники",
            "Мероприятие",
            "Достижение",
            "Город",
            "Организация",
            "Работа",
            "Файл"
        ])

        for r, row in enumerate(data):
            for c, val in enumerate(row):
                self.table.setItem(r, c, QtWidgets.QTableWidgetItem(str(val) if val else ""))

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

        data = get_all_achievements()
        filtered = []

        for row in data:
            if any(text in str(x).lower() for x in row[1:7]):
                filtered.append(row)

        self.fill_table(filtered)

    # ======================
    # SELECT ROW
    # ======================
    def on_row_change(self, row):
        self.selected_id = int(self.table.item(row, 0).text())

        self.inputEmployees.setText(self.table.item(row, 1).text())
        self.inputEvent.setText(self.table.item(row, 2).text())
        self.inputAchievement.setText(self.table.item(row, 3).text())
        self.inputCity.setText(self.table.item(row, 4).text())
        self.inputOrganization.setText(self.table.item(row, 5).text())
        self.inputWork.setText(self.table.item(row, 6).text())

        date_str = self.table.item(row, 7).text() if self.table.item(row, 7) else ""
        if date_str:
            self.inputAchDate.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))

        self.current_file_path = get_achievement_file(self.selected_id)
        self.file_path = None

    # ======================
    # ADD
    # ======================
    def add_achievement(self):
        ach_id = add_achievement(
            self.inputEvent.text(),
            self.inputAchievement.text(),
            self.inputCity.text(),
            self.inputOrganization.text(),
            self.inputWork.text(),
            self.inputAchDate.date().toString("yyyy-MM-dd")
        )

        # employees
        employees_text = self.inputEmployees.text()
        employees_list = [e.strip() for e in employees_text.split(";") if e.strip()]

        for emp in employees_list:
            if emp in self.employee_map:
                link_employee_achievement(self.employee_map[emp], ach_id)

        file_path = FileService.save_file(self.file_path, ach_id, None)
        update_achievement_file(ach_id, file_path)

        self.history.add(
            "achievement",
            ach_id,
            "add",
            None,
            str({
                "event": self.inputEvent.text(),
                "achievement": self.inputAchievement.text(),
                "city": self.inputCity.text(),
                "org": self.inputOrganization.text(),
                "work": self.inputWork.text()
            })
        )

        self.file_path = None
        self.clear_fields()
        self.load_achievements()

    # ======================
    # UPDATE
    # ======================
    def update_achievement_data(self):
        if not self.selected_id:
            return

        clear_achievement_employees(self.selected_id)

        employees_list = [
            e.strip() for e in self.inputEmployees.text().split(";") if e.strip()
        ]

        for emp in employees_list:
            if emp in self.employee_map:
                link_employee_achievement(self.employee_map[emp], self.selected_id)

        update_achievement(
            self.selected_id,
            self.inputEvent.text(),
            self.inputAchievement.text(),
            self.inputCity.text(),
            self.inputOrganization.text(),
            self.inputWork.text(),
            self.inputAchDate.date().toString("yyyy-MM-dd")
        )

        file_path = FileService.save_file(
            self.file_path,
            self.selected_id,
            self.current_file_path
        )

        update_achievement_file(self.selected_id, file_path)

        self.history.add(
            "achievement",
            self.selected_id,
            "update",
            None,
            "updated"
        )

        self.file_path = None
        self.load_achievements()

    # ======================
    # DELETE
    # ======================
    def delete_achievement(self):
        row = self.table.currentRow()
        if row == -1:
            return

        ach_id = int(self.table.item(row, 0).text())

        delete_achievement_by_id(ach_id)

        self.history.add(
            "achievement",
            ach_id,
            "delete",
            None,
            None
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
        ach_id = int(self.table.item(row, 0).text())
        path = get_achievement_file(ach_id)

        if path:
            FileService.open_file(path)

    # ======================
    # CLEAR
    # ======================
    def clear_fields(self):
        self.inputEvent.clear()
        self.inputAchievement.clear()
        self.inputCity.clear()
        self.inputOrganization.clear()
        self.inputWork.clear()
        self.inputEmployees.clear()
        self.inputAchDate.setDate(QDate.currentDate())