from PyQt5 import QtWidgets, uic
import os, sys
from tabs.employees_tab import EmployeesTab
from services.history_service import HistoryService
from tabs.history_tab import HistoryTab
from tabs.publications_tab import PublicationsTab
from tabs.achievements_tab import AchievementsTab
from database import ensure_publications_schema, ensure_employee_publications, ensure_achievements_schema, ensure_employee_achievements
from tabs.reports_tab import ReportsTab

ensure_publications_schema()
ensure_employee_publications()
ensure_achievements_schema()
ensure_employee_achievements()

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(
            resource_path("main.ui"),
            self
        )
        self.history_service = HistoryService()

        # Стили
        try:
            with open(
                    resource_path("style.qss"),
                    "r",
                    encoding="utf-8"
            ) as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Не удалось загрузить стиль: {e}")

        # Подключаем вкладку сотрудники
        self.employees_tab = EmployeesTab(self, self.history_service)

        # Подключение публикаций
        self.publications_tab = PublicationsTab(self, self.history_service)

        # Подключение достижений
        self.achievements_tab = AchievementsTab(self, self.history_service)

        #Подключение истории
        self.history_tab = HistoryTab(self.history_service)
        self.tabWidget.addTab(self.history_tab, "История изменений")

        # Подключение отчетов
        self.reports_tab = ReportsTab(self)


    def closeEvent(self, event):
        print("closeEvent called")

        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Подтверждение выхода")

        if self.employees_tab.is_dirty:
            msg.setText("У вас есть несохранённые изменения. Выйти?")
        else:
            msg.setText("Вы действительно хотите выйти?")

        msg.setStandardButtons(
            QtWidgets.QMessageBox.Yes |
            QtWidgets.QMessageBox.No
        )

        reply = msg.exec_()

        if reply == QtWidgets.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()