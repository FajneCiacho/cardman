import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox, QInputDialog, QLineEdit, QFileDialog

try:
    from modules.managers.security_manager import SecurityManager
except ImportError as e:
    print("Blad importu security:", e)
    sys.exit(1)

try:
    from modules.ui.main_window import MainWindow
except ImportError as e:
    print("Blad importu main_window:", e)
    sys.exit(1)


def _get_first_run_marker_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, ".first_run_done")


def _get_config_folder_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, ".config_folder")


def _load_config_folder():
    path = _get_config_folder_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                folder = f.read().strip()
                if folder and os.path.isdir(folder):
                    return folder
        except Exception:
            pass
    return None


def _save_config_folder(folder):
    path = _get_config_folder_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(folder)
    except Exception:
        pass


def _is_first_run():
    return not os.path.exists(_get_first_run_marker_path())


def _mark_first_run_done():
    path = _get_first_run_marker_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("done")
    except Exception:
        pass


def main():
    # Enable high-DPI scaling via environment variables (compatible with PyQt6)
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv)
    config_folder = _load_config_folder()

    if _is_first_run() or config_folder is None:
        QMessageBox.information(None, "Start", "Wybierz folder do zapisu plikow.")
        folder = QFileDialog.getExistingDirectory(None, "Wybierz folder", os.path.dirname(os.path.abspath(__file__)))
        if not folder:
            folder = os.path.dirname(os.path.abspath(__file__))
        config_folder = folder
        _save_config_folder(config_folder)
        _mark_first_run_done()

    password_manager = SecurityManager(config_folder)

    for _ in range(3):
        pwd, ok = QInputDialog.getText(None, "Logowanie", "Podaj haslo )", QLineEdit.EchoMode.Password)
        if not ok:
            return
        if password_manager.verify_password(pwd):
            password_manager.set_current_password(pwd)
            break
        else:
            QMessageBox.warning(None, "Blad", "Niepoprawne haslo.")
    else:
        QMessageBox.critical(None, "Blad", "Za duzo prob.")
        return

    window = MainWindow(password_manager, config_folder)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
