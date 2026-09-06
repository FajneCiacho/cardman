"""
dialogs.py - Dialogi UI aplikacji Kanban
"""

import json
import base64
import os
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
    QDialogButtonBox, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QFormLayout, QMessageBox, QFileDialog, QSplitter, QWidget, QLabel,
    QSlider
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from modules.ui import form_style as fs


class MainNotesDialog(QDialog):
    """Dialog glownego notatnika."""

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Glowny Notatnik")
        self.resize(600, 400)
        self._original_text = text

        layout = QVBoxLayout(self)
        self.editor = QTextEdit()

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")

        self._auto_line1 = f"{date_str},  {time_str}"
        self._auto_line2 = "Notatka:   "
        self._auto_header = self._auto_line1 + "\n" + self._auto_line2

        if text.strip():
            display_text = f"{self._auto_header}\n{text}"
        else:
            display_text = f"{self._auto_header}\n"

        self.editor.setPlainText(display_text)
        self.editor.setFont(QFont("Arial", 11))

        cursor = self.editor.textCursor()
        cursor.setPosition(len(self._auto_header))
        self.editor.setTextCursor(cursor)

        layout.addWidget(self.editor)

        btn_row = QHBoxLayout()
        btn_clear = QPushButton("Wyczysc")
        btn_clear.setFixedSize(100, 20)
        btn_clear.clicked.connect(self._clear)
        btn_close = QPushButton("Zamknij")
        btn_close.setFixedSize(100, 20)
        btn_close.clicked.connect(self.accept)
        btn_row.setContentsMargins(0, 0, 10, 0)
        btn_row.addStretch()
        btn_row.addWidget(btn_clear)
        btn_row.addSpacing(10)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self._apply_style()

    def _clear(self):
        self.editor.clear()

    def _apply_style(self):
        self.setStyleSheet(fs.dialog_stylesheet())
        for btn in self.findChildren(QPushButton):
            btn.setStyleSheet(fs.button_stylesheet("small"))

    def get_text(self):
        full_text = self.editor.toPlainText()

        if full_text.startswith(self._auto_header):
            content_after = full_text[len(self._auto_header):]
            if content_after.startswith('\n'):
                content_after = content_after[1:]

            original_stripped = self._original_text.strip()
            content_stripped = content_after.strip()

            if not content_stripped or content_stripped == original_stripped:
                return self._original_text
            else:
                return full_text

        return full_text


class NotesManagerDialog(QDialog):
    """Manager notatek - lista notatek z edycja (jak aplikacja Notatki w telefonie)."""

    def __init__(self, notes_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Informacje (produkcja)")
        self.resize(650, 500)

        self.notes_data = notes_data if isinstance(notes_data, list) else []
        self.current_note_id = None

        layout = QVBoxLayout(self)

        splitter = QSplitter(self)
        splitter.setOrientation(Qt.Orientation.Vertical)

        # Gorna czesc: lista notatek
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)

        self.list_widget = QListWidget()
        self.list_widget.setFont(QFont("Arial", 11))
        self.list_widget.itemClicked.connect(self._on_note_selected)
        list_layout.addWidget(self.list_widget)

        splitter.addWidget(list_container)

        # Dolna czesc: edycja
        edit_container = QWidget()
        edit_layout = QVBoxLayout(edit_container)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Tytul:")
        self.title_edit.setFont(QFont("Arial", 11))
        edit_layout.addWidget(self.title_edit)

        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText("Notatkai...")
        self.content_edit.setFont(QFont("Arial", 11))
        edit_layout.addWidget(self.content_edit)

        btn_row = QHBoxLayout()
        btn_new = QPushButton("Nowa")
        btn_save = QPushButton("Zapisz")
        btn_delete = QPushButton("Usun")
        btn_close = QPushButton("Zamknij")

        btn_new.clicked.connect(self._on_new)
        btn_save.clicked.connect(self._on_save)
        btn_delete.clicked.connect(self._on_delete)
        btn_close.clicked.connect(self.accept)

        btn_row.addWidget(btn_new)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_delete)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)

        edit_layout.addLayout(btn_row)
        splitter.addWidget(edit_container)

        splitter.setSizes([250, 200])
        layout.addWidget(splitter)

        self._refresh_list()

    def _refresh_list(self):
        self.list_widget.clear()
        for note in self.notes_data:
            title = note.get("title", "Bez tytulu")
            modified = note.get("modified", "")
            display = f"{title}  [{modified}]" if modified else title
            item = QListWidgetItem(display)
            item.setData(1, note.get("id"))
            self.list_widget.addItem(item)

    def _on_note_selected(self, item):
        note_id = item.data(1)
        for note in self.notes_data:
            if note.get("id") == note_id:
                self.current_note_id = note_id
                self.title_edit.setText(note.get("title", ""))
                self.content_edit.setPlainText(note.get("content", ""))
                break

    def _on_new(self):
        note = {
            "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
            "title": "",
            "content": "",
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "modified": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        self.notes_data.append(note)
        self.current_note_id = note["id"]
        self.title_edit.clear()
        self.content_edit.clear()
        self.title_edit.setFocus()
        self._refresh_list()
        # Zaznacz nowa notatke na liscie
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).data(1) == note["id"]:
                self.list_widget.setCurrentRow(i)
                break

    def _on_save(self):
        if not self.current_note_id:
            QMessageBox.information(self, "Info", "Nie wybrano notatki.")
            return
        for note in self.notes_data:
            if note.get("id") == self.current_note_id:
                note["title"] = self.title_edit.text().strip()
                note["content"] = self.content_edit.toPlainText()
                note["modified"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                break
        self._refresh_list()
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).data(1) == self.current_note_id:
                self.list_widget.setCurrentRow(i)
                break

    def _on_delete(self):
        if not self.current_note_id:
            return
        reply = QMessageBox.question(
            self, "Potwierdzenie",
            "Usunac notatke?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.notes_data = [n for n in self.notes_data if n.get("id") != self.current_note_id]
        self.current_note_id = None
        self.title_edit.clear()
        self.content_edit.clear()
        self._refresh_list()

    def get_notes_data(self):
        return self.notes_data


class NoteDialog(QDialog):
    """Dialog do edycji notatek karty."""

    def __init__(self, text="", title="Notes Karty", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(450, 240)
        self._original_text = text

        layout = QVBoxLayout(self)
        self.editor = QTextEdit()

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")

        self._auto_line1 = f"{date_str},  {time_str}"
        self._auto_line2 = "                  Notatka :   "
        self._auto_header = self._auto_line1 + "\n" + self._auto_line2

        if text.strip():
            display_text = f"{self._auto_header}\n{text}"
        else:
            display_text = f"{self._auto_header}\n"

        self.editor.setPlainText(display_text)

        cursor = self.editor.textCursor()
        cursor.setPosition(len(self._auto_header))
        self.editor.setTextCursor(cursor)

        layout.addWidget(self.editor)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_text(self):
        full_text = self.editor.toPlainText()

        if full_text.startswith(self._auto_header):
            content_after = full_text[len(self._auto_header):]
            if content_after.startswith('\n'):
                content_after = content_after[1:]

            original_stripped = self._original_text.strip()
            content_stripped = content_after.strip()

            if not content_stripped or content_stripped == original_stripped:
                return self._original_text
            else:
                return full_text

        return full_text


class TimelineDialog(QDialog):
    """Dialog do wyświetlania historii (Timeline) karty z szyfrowaniem."""

    def __init__(self, text="", card=None, parent=None, password_manager=None):
        super().__init__(parent)
        self.setWindowTitle("TIME LINE")
        self.resize(700, 300)
        self.card = card
        self.password_manager = password_manager

        layout = QVBoxLayout(self)
        self.viewer = QTextEdit()
        self.viewer.setPlainText(text)
        self.viewer.setReadOnly(True)
        self.viewer.setFont(QFont("Consolas", 10))
        layout.addWidget(self.viewer)

        btn_layout = QHBoxLayout()

        btn_save = QPushButton("Zapsz (Szyfrowany)")
        btn_save.clicked.connect(self._save_to_json_encrypted)
        btn_layout.addWidget(btn_save)

        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

        self.setStyleSheet(fs.dialog_stylesheet())
        btn_save.setStyleSheet(fs.button_stylesheet("normal"))
        btn_close.setStyleSheet(fs.button_stylesheet("normal"))

    def _save_to_json_encrypted(self):
        """Zapisuje Timeline do zaszyfrowanego pliku JSON."""
        main_num = ""
        ser_num = ""
        if self.card:
            main_num = self.card.text_items[2].toPlainText() if len(self.card.text_items) > 2 else ""
            ser_num = self.card.text_items[3].toPlainText() if len(self.card.text_items) > 3 else ""

        date_str = datetime.now().strftime("%Y-%m-%d")

        def sanitize(s):
            return "".join(c for c in s if c.isalnum() or c in '-_.').strip() or "brak"

        main_safe = sanitize(main_num)
        ser_safe = sanitize(ser_num)
        file_name = f"{main_safe}_{ser_safe}_{date_str}_TIMELINE.json"

        start_dir = ""
        if self.card is not None and self.card.scene() is not None:
            start_dir = getattr(self.card.scene(), "save_folder", "") or ""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Zapisz TIME LINE (Szyfrowany)",
            os.path.join(start_dir, file_name) if start_dir else file_name,
            "JSON Files (*.json)"
        )

        if file_path:
            timeline_text = self.viewer.toPlainText()

            data = {
                "Karta": {
                    "Detal": main_num,
                    "Seria": ser_num,
                    "Data_Zapisu": date_str,
                },
                "TIME_LINE": timeline_text,
                "_encrypted": False
            }

            # Szyfruj jeśli dostępny password_manager
            if self.password_manager:
                fernet = self.password_manager.get_fernet()
                if fernet:
                    try:
                        encrypted = fernet.encrypt(timeline_text.encode("utf-8"))
                        data["TIME_LINE"] = base64.b64encode(encrypted).decode("ascii")
                        data["_encrypted"] = True
                    except Exception as e:
                        QMessageBox.warning(
                            self, "Ostrzeżenie",
                            f"Nie udało się zaszyfrować. Zapisuję bez szyfrowania.\n{e}"
                        )

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                if data["_encrypted"]:
                    QMessageBox.information(self, "Sukces", f"Zapisano (ZASZYFROWANE): {file_path}")
                else:
                    QMessageBox.information(self, "Sukces", f"Zapisano (niezaszyfrowane): {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie udało się zapisać: {e}")


class ColumnNotesDialog(QDialog):
    """Dialog do edycji notatek kolumny."""

    def __init__(self, current_text="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Notes Kolumny")
        self.resize(500, 300)
        self._original_text = current_text

        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")

        self._auto_line1 = f"{date_str}_{time_str}"
        self._auto_line2 = "                  Notatka :   "
        self._auto_header = self._auto_line1 + "\n" + self._auto_line2

        if current_text.strip():
            display_text = f"{self._auto_header}\n{current_text}"
        else:
            display_text = f"{self._auto_header}\n"

        self.text_edit.setPlainText(display_text)

        cursor = self.text_edit.textCursor()
        cursor.setPosition(len(self._auto_header))
        self.text_edit.setTextCursor(cursor)

        layout.addWidget(self.text_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_text(self):
        full_text = self.text_edit.toPlainText()

        if full_text.startswith(self._auto_header):
            content_after = full_text[len(self._auto_header):]
            if content_after.startswith('\n'):
                content_after = content_after[1:]

            original_stripped = self._original_text.strip()
            content_stripped = content_after.strip()

            if not content_stripped or content_stripped == original_stripped:
                return self._original_text
            else:
                return full_text

        return full_text


class SearchCardDialog(QDialog):
    """Dialog do wyszukiwania kart."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wyszukaj Karty")
        self.resize(350, 150)

        layout = QFormLayout(self)

        self.detal_input = QLineEdit()
        self.detal_input.setPlaceholderText("Detal")
        layout.addRow("Detal", self.detal_input)

        self.ser_input = QLineEdit()
        self.ser_input.setPlaceholderText("Seria")
        layout.addRow("ser:", self.ser_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_search_params(self):
        return self.detal_input.text().strip(), self.ser_input.text().strip()


class SettingsDialog(QDialog):
    """Ustawienia aplikacji: folder zapisu plikow (EXCEL, TIME LINE),
    przyciemnianie sceny razem z body kolumn oraz raporty baz wzorcowych."""

    RAPORTY_BAZY = ["pracownicy", "maszyny", "stanowiska", "kody"]

    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.setWindowTitle("Ustawienia")
        self.setFixedSize(480, 340)

        layout = QVBoxLayout(self)

        lab_folder = QLabel("Podaj ścieżkę do folderu zapisu plików (EXCEL, TIME LINE):")
        lab_folder.setStyleSheet("font-size: 9pt; font-weight: bold; color: #43170E;")
        layout.addWidget(lab_folder)

        row = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setText(getattr(scene, "save_folder", "") or "")
        self.folder_edit.setStyleSheet("font-size: 9pt;")
        row.addWidget(self.folder_edit, 1)

        btn_browse = QPushButton("Przeglądaj...")
        btn_browse.clicked.connect(self._browse)
        row.addWidget(btn_browse)
        layout.addLayout(row)

        lab_obraz = QLabel("Podaj ścieżkę do folderu 'Obrazy' (zdjęcia detali):")
        lab_obraz.setStyleSheet("font-size: 9pt; font-weight: bold; color: #43170E;")
        layout.addWidget(lab_obraz)

        row_obraz = QHBoxLayout()
        self.obraz_edit = QLineEdit()
        self.obraz_edit.setText(getattr(scene, "obraz_folder", "") or "")
        self.obraz_edit.setStyleSheet("font-size: 9pt;")
        row_obraz.addWidget(self.obraz_edit, 1)

        btn_browse_obraz = QPushButton("Przeglądaj...")
        btn_browse_obraz.clicked.connect(self._browse_obraz)
        row_obraz.addWidget(btn_browse_obraz)
        layout.addLayout(row_obraz)

        lab_dim = QLabel("Przyciemnianie sceny.")
        lab_dim.setStyleSheet("font-size: 9pt; font-weight: bold; color: #43170E;")
        layout.addWidget(lab_dim)

        dim_row = QHBoxLayout()
        self.dim_slider = QSlider(Qt.Orientation.Horizontal)
        self.dim_slider.setRange(0, 100)
        self.dim_slider.setValue(int(getattr(scene, "dim_intensity", 0) or 0))
        self.dim_slider.valueChanged.connect(self._on_dim_changed)
        dim_row.addWidget(self.dim_slider, 1)
        self.dim_value_label = QLabel("0%")
        self.dim_value_label.setStyleSheet("font-size: 9pt; font-weight: bold; color: #43170E;")
        dim_row.addWidget(self.dim_value_label)
        layout.addLayout(dim_row)
        self._on_dim_changed(self.dim_slider.value())

        # --- RAPORTY (bazy wzorcowe) ---
        sep = QLabel("RAPORTY — bazy wzorcowe (pracownicy / maszyny / stanowiska / kody)")
        sep.setStyleSheet("font-size: 9pt; font-weight: bold; color: #43170E;"
                          "border-top: 1px solid #43170E; padding-top: 4px;")
        layout.addWidget(sep)

        raport_row = QHBoxLayout()
        btn_drukuj = QPushButton("WYDRUKUJ 4 RAPORTY")
        btn_drukuj.clicked.connect(self._export_reports)
        raport_row.addWidget(btn_drukuj)

        btn_wczytaj = QPushButton("WCZYTAJ 4 RAPORTY")
        btn_wczytaj.clicked.connect(self._import_reports)
        raport_row.addWidget(btn_wczytaj)
        layout.addLayout(raport_row)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_save = QPushButton("Zapisz")
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)

        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(self.reject)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self.setStyleSheet(fs.dialog_stylesheet())
        btn_save.setStyleSheet(fs.button_stylesheet("normal"))
        btn_close.setStyleSheet(fs.button_stylesheet("normal"))
        btn_browse.setStyleSheet(fs.button_stylesheet("normal"))
        btn_browse_obraz.setStyleSheet(fs.button_stylesheet("normal"))
        btn_drukuj.setStyleSheet(fs.button_stylesheet("normal"))
        btn_wczytaj.setStyleSheet(fs.button_stylesheet("normal"))

    def _target_folder(self):
        folder = self.folder_edit.text().strip()
        if not folder:
            folder = getattr(self.scene, "save_folder", "")
        if not folder:
            folder = getattr(self.scene, "config_folder", ".")
        return folder

    def _export_reports(self):
        """Wydruk (eksport) 4 raportow do folderu zapisu."""
        try:
            from modules.reference import excel
        except Exception as e:
            QMessageBox.critical(self, "Blad", "Nie mozna zaladowac modulu raportow:\n%s" % e)
            return
        folder = self._target_folder()
        try:
            os.makedirs(folder, exist_ok=True)
            saved = []
            for name in self.RAPORTY_BAZY:
                path = excel.export_report(name, os.path.join(folder, "raport_%s.xlsx" % name))
                saved.append(path)
        except Exception as e:
            QMessageBox.critical(self, "Blad", "Nie udalo sie wydrukowac raportow:\n%s" % e)
            return
        QMessageBox.information(
            self, "RAPORTY",
            "Wydrukowano 4 raporty:\n" + "\n".join(saved) +
            "\n\nUzupelnij je w Excelu i wczytaj przyciskiem po prawej."
        )

    def _import_reports(self):
        """Wczytuje uzupelnione raporty z powrotem do bazy wzorcowej."""
        try:
            from modules.reference import excel
        except Exception as e:
            QMessageBox.critical(self, "Blad", "Nie mozna zaladowac modulu raportow:\n%s" % e)
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Wybierz folder z raportami (raport_*.xlsx)", self._target_folder()
        )
        if not folder:
            return
        missing = [os.path.join(folder, "raport_%s.xlsx" % n)
                   for n in self.RAPORTY_BAZY
                   if not os.path.isfile(os.path.join(folder, "raport_%s.xlsx" % n))]
        if missing:
            QMessageBox.warning(
                self, "Brak raportow",
                "Nie znaleziono plikow:\n" + "\n".join(missing) +
                "\n\nNajpierw wydrukuj raporty (przycisk po lewej)."
            )
            return
        if QMessageBox.question(
                self, "Wczytac do bazy?",
                "Wczytac dane z raportow do bazy wzorcowej?\n%s" % folder
        ) != QMessageBox.StandardButton.Yes:
            return
        lines = []
        for name in self.RAPORTY_BAZY:
            path = os.path.join(folder, "raport_%s.xlsx" % name)
            try:
                dodane, zaktualizowane, bledy = excel.import_report(name, path)
                lines.append("  %s: +%d nowych, %d zaktualizowanych"
                             % (name, dodane, zaktualizowane))
                for rno, msg in bledy[:5]:
                    lines.append("    wiersz %d: %s" % (rno, msg))
            except Exception as e:
                lines.append("  %s: BLAD %s" % (name, e))
        QMessageBox.information(self, "RAPORTY", "Wczytano do bazy:\n" + "\n".join(lines))

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Wybierz folder zapisu", self.folder_edit.text()
        )
        if folder:
            self.folder_edit.setText(folder)

    def _browse_obraz(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Wybierz folder 'Obrazy'", self.obraz_edit.text()
        )
        if folder:
            self.obraz_edit.setText(folder)

    def _on_dim_changed(self, value):
        """Podglad na zywo przy ruszaniu suwakiem (plynne sciemnianie)."""
        self.dim_value_label.setText("%d%%" % value)
        scene = self.scene
        scene.dim_intensity = value
        try:
            scene.apply_dim_state()
        except Exception:
            pass

    def _save(self):
        scene = self.scene
        folder = self.folder_edit.text().strip()
        if folder:
            scene.save_folder = folder
        obraz = self.obraz_edit.text().strip()
        if obraz:
            scene.obraz_folder = obraz
        scene.dim_intensity = self.dim_slider.value()
        try:
            scene.apply_dim_state()
        except Exception:
            pass

        try:
            from modules.managers.settings_manager import SettingsManager
            sm = SettingsManager(getattr(scene, "config_folder", "."))
            settings = sm.load_app_settings()
            settings["save_folder"] = folder
            settings["obraz_folder"] = obraz
            settings["dim_intensity"] = scene.dim_intensity
            sm.save_app_settings(settings)
        except Exception as e:
            print("Blad zapisu ustawien:", e)

        self.accept()
