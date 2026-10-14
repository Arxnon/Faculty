"""Общие мелочи интерфейса, которые раньше были скопированы по нескольким вкладкам."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCompleter


class MultiCompleter(QCompleter):
    """Автодополнение для поля, где ФИО перечисляются через «;»."""

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
        return value


def make_names_completer(names):
    completer = MultiCompleter(names)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setCompletionMode(QCompleter.PopupCompletion)
    return completer


def split_names(text):
    """'Иванов; Петров ;' -> ['Иванов', 'Петров']"""
    return [part.strip() for part in (text or "").split(";") if part.strip()]


def cell_text(value):
    """Текст для ячейки таблицы: None становится пустой строкой, а не словом 'None'."""
    return "" if value is None else str(value)
