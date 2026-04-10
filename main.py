from PyQt5 import QtWidgets, uic
from tabs.employees_tab import EmployeesTab
from services.history_service import HistoryService
from tabs.history_tab import HistoryTab
from tabs.publications_tab import PublicationsTab

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

        # Подключение публикаций
        self.publications_tab = PublicationsTab(self, self.history_service)

        #Подключение истории
        self.history_tab = HistoryTab(self.history_service)
        self.tabWidget.addTab(self.history_tab, "История изменений")

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