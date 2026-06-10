import os
import shutil
import sys
import subprocess


class FileService:
    BASE_DIR = "files"

    @staticmethod
    def save_file(src_path, entity_id, folder="files", old_path=None):
        if not src_path:
            return old_path

        os.makedirs(folder, exist_ok=True)

        ext = os.path.splitext(src_path)[1]
        new_path = os.path.join(folder, f"{entity_id}{ext}")

        if old_path and os.path.exists(old_path):
            try:
                os.remove(old_path)
            except:
                pass

        shutil.copy(src_path, new_path)

        return new_path

    @staticmethod
    def open_file(path):
        if not path or not os.path.exists(path):
            raise FileNotFoundError("Файл не найден")

        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.call(["open", path])
        else:
            subprocess.call(["xdg-open", path])

    @staticmethod
    def delete_file(path):
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass