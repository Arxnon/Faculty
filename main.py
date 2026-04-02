from PyQt5 import QtWidgets, uic
from tabs.employees_tab import EmployeesTab
from services.history_service import HistoryService
from tabs.history_tab import HistoryTab


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main.ui", self)
        self.history_service = HistoryService()

        # Стили
        try:
            with open("style.qss", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Не удалось загрузить стиль: {e}")

        # Подключаем вкладку сотрудники
        self.employees_tab = EmployeesTab(self, self.history_service)

        #Подключение истории
        self.history_tab = HistoryTab(self.history_service)
        self.tabWidget.addTab(self.history_tab, "История изменений")

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()