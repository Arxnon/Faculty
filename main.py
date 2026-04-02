from PyQt5 import QtWidgets, uic
from tabs.employees_tab import EmployeesTab


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main.ui", self)

        try:
            with open("style.qss", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(e)

        self.employees_tab = EmployeesTab(self)


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()