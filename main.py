import sys
import os
from PyQt5 import QtWidgets

from MainWindow import MainWindow
from database import DB_FILE, create_database


if __name__ == "__main__":
    if not os.path.exists(DB_FILE):
        create_database(DB_FILE)
        print("БД создана")

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())