from PyQt5 import QtWidgets

class EmployeeSelectorDialog(QtWidgets.QDialog):

    def __init__(self, employees, selected=None):
        super().__init__()

        self.setWindowTitle("Выбор сотрудников")
        self.resize(400, 500)

        self.selected = selected or []

        layout = QtWidgets.QVBoxLayout(self)

        self.chk_all = QtWidgets.QCheckBox("Выбрать всех")
        layout.addWidget(self.chk_all)

        self.list_checks = []

        for fio in employees:

            chk = QtWidgets.QCheckBox(fio)

            if fio in self.selected:
                chk.setChecked(True)

            layout.addWidget(chk)

            self.list_checks.append(chk)

        self.chk_all.stateChanged.connect(self.toggle_all)

        btn_ok = QtWidgets.QPushButton("ОК")
        btn_ok.clicked.connect(self.accept)

        layout.addWidget(btn_ok)

    def toggle_all(self, state):

        checked = state == 2

        for chk in self.list_checks:
            chk.setChecked(checked)

    def get_selected(self):

        return [
            chk.text()
            for chk in self.list_checks
            if chk.isChecked()
        ]
