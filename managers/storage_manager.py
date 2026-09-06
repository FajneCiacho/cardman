"""
storage_manager.py - jedyny modul czytajacy i piszacy pliki projektu (Faza 2).

Odpowiedzialnosci:
- zapis/odczyt projektu (JSON + zaszyfrowane autozapisy),
- format SQLite jako rownolegly backend (Faza 5: save_project_db / load_project_db),
- FORMAT_VERSION + migracje starych formatow,
- backup (.bak) przed nadpisaniem pliku,
- rotacja autozapisow,
- przeplywy UI ("Wczytaj z pliku").

Scene serializujemy/deserializujemy przez scene.serialize() / scene.deserialize().
"""
import base64
import glob
import json
import os
from datetime import datetime

from PyQt6.QtWidgets import QFileDialog, QMessageBox


class StorageManager:
    """Jedno miejsce zapisu/odczytu projektu."""

    FORMAT_VERSION = 3
    MAX_AUTOSAVE_KEEP = 5

    def __init__(self, config_folder=None, password_manager=None):
        self.config_folder = config_folder or "."
        self.password_manager = password_manager

    # ------------------------------------------------------------------
    # Zapis / odczyt projektu
    # ------------------------------------------------------------------

    def save_project(self, scene, file_name, encrypt_timeline=False):
        """Zapisuje projekt do NIEZASZYFROWANEGO pliku JSON (z FORMAT_VERSION)."""
        data = scene.serialize(encrypt_timeline=encrypt_timeline)
        data["FORMAT_VERSION"] = self.FORMAT_VERSION
        self._backup_file(file_name)
        try:
            with open(file_name, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            QMessageBox.critical(None, "Blad", f"Nie udalo sie zapisac JSON: {e}")
            return False

    def save_encrypted(self, scene, file_name):
        """Zapisuje projekt jako zaszyfrowany wrapper JSON (salt + token)."""
        if self.password_manager is None:
            return False
        fernet = self.password_manager.get_fernet()
        if fernet is None:
            return False
        data = scene.serialize(encrypt_timeline=True)
        data["FORMAT_VERSION"] = self.FORMAT_VERSION
        try:
            json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            token = fernet.encrypt(json_bytes)
            self._backup_file(file_name)
            wrapper = {
                "salt": base64.b64encode(self.password_manager._salt).decode("ascii"),
                "token": base64.b64encode(token).decode("ascii"),
            }
            with open(file_name, "w", encoding="utf-8") as f:
                json.dump(wrapper, f, ensure_ascii=False)
            return True
        except Exception:
            # Fallback do poprzedniego zapisu binarnego
            try:
                self._backup_file(file_name)
                with open(file_name, "wb") as f:
                    f.write(token)
                return True
            except Exception:
                return False

    def load_project(self, scene, file_name, parent=None):
        """Wczytuje projekt z pliku.

        Obsluguje w kolejnosci: baze SQLite (autodetekcja), wrapper JSON
        (salt+token), surowy token, zwykly JSON. Migruje stary format.
        Zwraca bool (czy wczytano).
        """
        # Autodetekcja formatu SQLite (Faza 5) - rownolegly backend
        try:
            with open(file_name, "rb") as f:
                head = f.read(16)
            if head.startswith(b"SQLite format 3"):
                return self.load_project_db(scene, file_name, parent)
        except OSError:
            pass

        loaded = False
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                parsed = json.load(f)
            if isinstance(parsed, dict) and "salt" in parsed and "token" in parsed:
                data = self._decrypt_wrapper(parsed, parent)
                if data is not None:
                    self._apply(scene, data)
                    loaded = True
        except Exception:
            pass

        if not loaded and self.password_manager is not None:
            try:
                fernet = self.password_manager.get_fernet()
                if fernet is not None:
                    with open(file_name, "rb") as f:
                        token = f.read()
                    if token:
                        decrypted = fernet.decrypt(token)
                        data = json.loads(decrypted.decode("utf-8"))
                        self._apply(scene, data)
                        loaded = True
            except Exception:
                loaded = False

        if not loaded:
            try:
                with open(file_name, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._apply(scene, data)
                loaded = True
            except json.JSONDecodeError as e:
                QMessageBox.critical(None, "Blad JSON", f"Plik nie jest prawidlowym JSON:\n{e}")
            except Exception as e:
                QMessageBox.critical(None, "Blad", f"Nie udalo sie wczytac: {e}")
        return loaded

    def load_project_dialog(self, scene, parent=None):
        """'Wczytaj z pliku' - wybor pliku + potwierdzenie + wczytanie."""
        file_path, _ = QFileDialog.getOpenFileName(
            parent, "Wczytaj plik", self.config_folder or "", "JSON Files (*.json)"
        )
        if not file_path:
            return False
        reply = QMessageBox.question(
            parent,
            "Potwierdz wczytanie",
            "Wczytanie pliku zresetuje obecny stan.\nKontynuowac?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return False
        return self.load_project(scene, file_path, parent)

    def _apply(self, scene, data):
        """Migruje i wczytuje dane do sceny."""
        data = self._migrate(data)
        scene.deserialize(data)

    def _decrypt_wrapper(self, wrapper, parent=None):
        """Odszyfrowuje wrapper (salt+token). Najpierw biezace haslo, potem pytanie (max 3)."""
        try:
            salt = base64.b64decode(wrapper["salt"].encode("ascii"))
            token = base64.b64decode(wrapper["token"].encode("ascii"))
        except Exception:
            return None

        pm = self.password_manager
        if pm is None:
            return None
        if pm.current_password:
            fernet = pm.fernet_from_password_and_salt(pm.current_password, salt)
            if fernet is not None:
                try:
                    decrypted = fernet.decrypt(token)
                    return json.loads(decrypted.decode("utf-8"))
                except Exception:
                    pass

        for _ in range(3):
            pwd = pm.prompt_for_password(
                parent, title="Haslo do pliku", text="Podaj haslo do tego pliku:"
            )
            if not pwd:
                return None
            fernet = pm.fernet_from_password_and_salt(pwd, salt)
            if fernet is None:
                continue
            try:
                decrypted = fernet.decrypt(token)
                pm.set_current_password(pwd)
                return json.loads(decrypted.decode("utf-8"))
            except Exception:
                continue
        return None

    # ------------------------------------------------------------------
    # Format SQLite (Faza 5) - rownolegly backend do JSON
    # ------------------------------------------------------------------

    def save_project_db(self, scene, file_name, encrypt_timeline=False):
        """Eksportuje projekt do SQLite. JSON pozostaje glownym formatem."""
        data = scene.serialize(encrypt_timeline=encrypt_timeline)
        data["FORMAT_VERSION"] = self.FORMAT_VERSION
        try:
            from modules.database.database_manager import DatabaseManager
            DatabaseManager().export_scene(file_name, data)
            return True
        except Exception as e:
            QMessageBox.critical(None, "Blad DB", f"Nie udalo sie zapisac bazy: {e}")
            return False

    def load_project_db(self, scene, file_name, parent=None):
        """Wczytuje projekt z SQLite (import -> scene.deserialize)."""
        try:
            from modules.database.database_manager import DatabaseManager
            data = DatabaseManager().import_scene(file_name)
        except Exception as e:
            QMessageBox.critical(None, "Blad DB", f"Nie udalo sie wczytac bazy: {e}")
            return False
        self._apply(scene, data)
        return True

    def load_project_db_dialog(self, scene, parent=None):
        """Wczytaj projekt DB - wybor pliku + potwierdzenie + wczytanie."""
        file_path, _ = QFileDialog.getOpenFileName(
            parent, "Wczytaj projekt DB", self.config_folder or "",
            "SQLite Database (*.db)"
        )
        if not file_path:
            return False
        reply = QMessageBox.question(
            parent,
            "Potwierdz wczytanie",
            "Wczytanie pliku DB zresetuje obecny stan.\nKontynuowac?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return False
        return self.load_project_db(scene, file_path, parent)

    # ------------------------------------------------------------------
    # Migracje
    # ------------------------------------------------------------------

    def _migrate(self, data):
        """Migruje stary format (general_info -> notes_data) i dopisuje FORMAT_VERSION."""
        version = data.get("FORMAT_VERSION", 1)
        if version >= self.FORMAT_VERSION:
            return data
        if version < 2:
            old_info = data.get("general_info", "")
            if old_info.strip() and not data.get("notes_data"):
                data["notes_data"] = [{
                    "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
                    "title": "Informacje ogolne",
                    "content": old_info,
                    "created": "",
                    "modified": "",
                }]
        data["FORMAT_VERSION"] = self.FORMAT_VERSION
        return data

    # ------------------------------------------------------------------
    # Autozapis
    # ------------------------------------------------------------------

    def get_autosave_path(self, scene):
        """Nazwa autozapisu: (kanban_text)_(YYYY-MM-DD)_(Autozapis).json"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        kanban_text = "Kanban"
        if scene and scene.tables and len(scene.tables) > 0:
            base_table = scene.tables[0]
            if hasattr(base_table, "kanban_text"):
                kanban_text = base_table.kanban_text.toPlainText().replace(" ", "_")
        return os.path.join(self.config_folder, f"({kanban_text})_({date_str})_(Autozapis).json")

    def _autosave_files(self):
        """Lista plikow autozapisu (nowy i stare formaty nazw)."""
        files = set()
        files.update(glob.glob(os.path.join(self.config_folder, "(*)*_(Autozapis).json")))
        files.update(glob.glob(os.path.join(self.config_folder, "Autozapis_*.json")))
        files.update(glob.glob(os.path.join(self.config_folder, "*_(Autozapis).json")))
        return sorted(files, key=os.path.getmtime)

    def find_latest_autosave(self):
        """Najnowszy plik autozapisu lub None."""
        files = self._autosave_files()
        if not files:
            return None
        return files[-1]

    def rotate_autosaves(self):
        """Usuwa najstarsze autozapisy (i ich .bak), zostawiajac MAX_AUTOSAVE_KEEP."""
        files = self._autosave_files()
        while len(files) > self.MAX_AUTOSAVE_KEEP:
            oldest = files.pop(0)
            try:
                os.remove(oldest)
            except OSError:
                pass
            try:
                if os.path.exists(oldest + ".bak"):
                    os.remove(oldest + ".bak")
            except OSError:
                pass

    def save_autosave(self, scene):
        """Zapisuje zaszyfrowany autozapis i rotuje stare."""
        ok = self.save_encrypted(scene, self.get_autosave_path(scene))
        if ok:
            self.rotate_autosaves()
        return ok

    def load_autosave(self, scene, parent=None):
        """Probuje wczytac najnowszy autozapis. Zwraca bool (czy wczytano)."""
        path = self.find_latest_autosave()
        if not path or not os.path.exists(path):
            return False
        if os.path.getsize(path) == 0:
            return False
        filename = os.path.basename(path)
        reply = QMessageBox.question(
            parent,
            "Autozapis",
            f"Znaleziono autozapis: {filename}\nWczytac poprzedni stan?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return False
        return self.load_project(scene, path, parent)

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------

    def _backup_file(self, file_name):
        """Kopiuje istniejacy plik do .bak przed nadpisaniem."""
        try:
            if os.path.exists(file_name):
                with open(file_name, "rb") as src, open(file_name + ".bak", "wb") as dst:
                    dst.write(src.read())
        except Exception:
            pass
