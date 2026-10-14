import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler

from PyQt5 import QtWidgets, uic

from db import DatabaseCorruptedError, init_database
from paths import log_path, resource_path
from services.history_service import HistoryService
from tabs.achievements_tab import AchievementsTab
from tabs.employees_tab import EmployeesTab
from tabs.history_tab import HistoryTab
from tabs.publications_tab import PublicationsTab
from tabs.reports_tab import ReportsTab

log = logging.getLogger("faculty")


def setup_logging():
    handler = RotatingFileHandler(
        log_path(), maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def handle_exception(exc_type, exc, tb):
    """Необработанная ошибка: пишем в лог и показываем сообщение, окно не закрывается."""
    log.error("Необработанное исключение", exc_info=(exc_type, exc, tb))

    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, tb)
        return

    try:
        QtWidgets.QMessageBox.critical(
            None,
            "Непредвиденная ошибка",
            f"{exc}\n\nПодробности записаны в журнал:\n{log_path()}",
        )
    except Exception:
        traceback.print_exception(exc_type, exc, tb)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(resource_path("main.ui"), self)
        self.history_service = HistoryService()

        # Стили
        try:
            with open(resource_path("style.qss"), "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except OSError:
            log.warning("Не удалось загрузить стиль", exc_info=True)

        # История создаётся первой: остальные вкладки обновляют её после правок
        self.employees_tab = EmployeesTab(self, self.history_service)
        self.publications_tab = PublicationsTab(self, self.history_service)
        self.achievements_tab = AchievementsTab(self, self.history_service)

        self.history_tab = HistoryTab(self.history_service)
        self.tabWidget.addTab(self.history_tab, "История изменений")

        self.reports_tab = ReportsTab(self)

    def closeEvent(self, event):
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Подтверждение выхода")

        if self.employees_tab.is_dirty:
            msg.setText("У вас есть несохранённые изменения. Выйти?")
        else:
            msg.setText("Вы действительно хотите выйти?")

        msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

        if msg.exec_() == QtWidgets.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


def main():
    setup_logging()
    sys.excepthook = handle_exception

    app = QtWidgets.QApplication(sys.argv)

    try:
        init_database()
    except DatabaseCorruptedError as exc:
        log.error("База данных недоступна: %s", exc)
        QtWidgets.QMessageBox.critical(None, "База данных", str(exc))
        return 1
    except Exception as exc:
        log.exception("Не удалось подготовить базу данных")
        QtWidgets.QMessageBox.critical(
            None, "База данных", f"Не удалось открыть базу данных:\n{exc}"
        )
        return 1

    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
