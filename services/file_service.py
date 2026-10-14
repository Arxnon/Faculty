import logging
import os
import shutil
import subprocess
import sys

from paths import attachment_path

log = logging.getLogger(__name__)


class FileService:
    """Вложения лежат в папке данных пользователя, в БД хранится путь вида files/publications/3.pdf."""

    @staticmethod
    def save_file(src_path, entity_id, folder="files", old_path=None):
        """Копирует файл в хранилище и возвращает путь для БД.

        Если файл не выбран, возвращается прежний путь. Сначала копия пишется во
        временный файл, и только потом заменяет старую: при ошибке копирования
        прежний файл остаётся на месте (ошибка OSError уходит вызывающему коду).
        """
        if not src_path:
            return old_path

        extension = os.path.splitext(src_path)[1]
        relative = f"{folder.strip('/')}/{entity_id}{extension}"
        target = attachment_path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)

        temporary = target.with_name(target.name + ".tmp")
        try:
            shutil.copyfile(src_path, temporary)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                try:
                    temporary.unlink()
                except OSError:
                    log.warning("Не удалось удалить временный файл %s", temporary)

        if old_path and old_path != relative:
            FileService.delete_file(old_path)

        return relative

    @staticmethod
    def open_file(path):
        real_path = attachment_path(path)
        if real_path is None or not real_path.exists():
            raise FileNotFoundError("Файл не найден")

        if sys.platform == "win32":
            os.startfile(str(real_path))
        elif sys.platform == "darwin":
            subprocess.call(["open", str(real_path)])
        else:
            subprocess.call(["xdg-open", str(real_path)])

    @staticmethod
    def delete_file(path):
        real_path = attachment_path(path)
        if real_path is not None and real_path.exists():
            try:
                real_path.unlink()
            except OSError:
                log.warning("Не удалось удалить файл %s", real_path, exc_info=True)
