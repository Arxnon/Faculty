from PyQt5 import QtWidgets
from services.file_service import FileService
from database import (
    get_all_achievements,
    add_achievement,
    delete_achievement_by_id,
    update_achievement,
    get_achievement_file,
    update_achievement_file,
    get_all_employees
)

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
        self.inputEmployeeName = parent.inputEmployeeName
        self.inputEvent = parent.inputEvent
        self.inputAchievement = parent.inputAchievement
        self.inputCity = parent.inputCity
        self.inputOrganization = parent.inputOrganization
        self.inputWorkName = parent.inputWorkName

        # SEARCH
        self.search = parent.searchAchievements
        self.search.textChanged.connect(self.search_achievements)

        # BUTTONS
        parent.btnAddAch.clicked.connect(self.add_achievement)
        parent.btnDeleteAch.clicked.connect(self.delete_achievement)
        parent.btnUpdateAch.clicked.connect(self.update_achievement_data)
        parent.btnFileAch.clicked.connect(self.select_file)

        # EVENTS
        self.table.cellClicked.connect(self.on_row_change)
        self.table.cellDoubleClicked.connect(self.open_file)

        self.refresh_employees()
        self.load_achievements()

    # ======================
    # EMPLOYEES
    # ======================
    def refresh_employees(self):
        employees = get_all_employees()
        self.employee_map = {emp[1]: emp[0] for emp in employees}

        self.comboEmployee.clear()
        self.comboEmployee.addItems(self.employee_map.keys())

    # ======================
    # TABLE
    # ======================
    def fill_table(self, data):
        self.table.setRowCount(len(data))
        self.table.setColumnCount(8)

        self.table.setHorizontalHeaderLabels([
            "ID",
            "Сотрудник",
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

        self.comboEmployee.setCurrentText(self.table.item(row, 1).text())
        self.inputEvent.setText(self.table.item(row, 2).text())
        self.inputAchievement.setText(self.table.item(row, 3).text())
        self.inputCity.setText(self.table.item(row, 4).text())
        self.inputOrganization.setText(self.table.item(row, 5).text())
        self.inputWorkName.setText(self.table.item(row, 6).text())

        self.current_file_path = get_achievement_file(self.selected_id)
        self.file_path = None

    # ======================
    # ADD
    # ======================
    def add_achievement(self):
        emp_id = self.employee_map.get(self.comboEmployee.currentText())

        if not emp_id:
            return

        ach_id = add_achievement(
            emp_id,
            self.inputEvent.text(),
            self.inputAchievement.text(),
            self.inputCity.text(),
            self.inputOrganization.text(),
            self.inputWorkName.text()
        )

        file_path = FileService.save_file(self.file_path, ach_id, None)
        update_achievement_file(ach_id, file_path)

        # HISTORY
        self.history.add(
            "achievement",
            ach_id,
            "add",
            None,
            str({
                "event": self.inputEvent.text(),
                "achievement": self.inputAchievement.text(),
                "city": self.inputCity.text(),
                "organization": self.inputOrganization.text(),
                "work": self.inputWorkName.text()
            })
        )

        self.file_path = None
        self.clear_fields()
        self.load_achievements()

        QtWidgets.QMessageBox.information(self.parent, "OK", "Достижение добавлено")

    # ======================
    # UPDATE
    # ======================
    def update_achievement_data(self):
        if not self.selected_id:
            return

        emp_id = self.employee_map.get(self.comboEmployee.currentText())

        old_row = self.table.currentRow()

        old_data = str({
            "event": self.table.item(old_row, 2).text(),
            "achievement": self.table.item(old_row, 3).text(),
            "city": self.table.item(old_row, 4).text(),
            "organization": self.table.item(old_row, 5).text(),
            "work": self.table.item(old_row, 6).text()
        })

        update_achievement(
            self.selected_id,
            emp_id,
            self.inputEvent.text(),
            self.inputAchievement.text(),
            self.inputCity.text(),
            self.inputOrganization.text(),
            self.inputWorkName.text()
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
            old_data,
            str({
                "event": self.inputEvent.text(),
                "achievement": self.inputAchievement.text(),
                "city": self.inputCity.text(),
                "organization": self.inputOrganization.text(),
                "work": self.inputWorkName.text()
            })
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

        old_data = str({
            "event": self.table.item(row, 2).text(),
            "achievement": self.table.item(row, 3).text(),
            "city": self.table.item(row, 4).text(),
            "organization": self.table.item(row, 5).text(),
            "work": self.table.item(row, 6).text()
        })

        delete_achievement_by_id(ach_id)

        self.history.add(
            "achievement",
            ach_id,
            "delete",
            old_data,
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
        self.inputWorkName.clear()