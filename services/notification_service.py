from PyQt5.QtWidgets import QSystemTrayIcon
from PyQt5.QtGui import QIcon


class NotificationService:
    def __init__(self):
        self.tray = QSystemTrayIcon()

        # лучше использовать файл иконки
        self.tray.setIcon(QIcon())  # или QIcon("icon.png")

        self.tray.show()

    def show(self, title, message):
        self.tray.showMessage(
            title,
            message,
            QSystemTrayIcon.Information,  # или MessageIcon.Information
            3000
        )