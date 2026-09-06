"""
forms_card.py - Formularze KARTY (Faza 7.1).

Wczytuje zaprojektowane w Qt Designerze pliki .ui 1:1:
  - edit   -> Formularz_Edytor_Karty.ui
  - preview-> Formularz_Hover_karty.ui
  - notes  -> Formularz_Notes_Karty.ui
  - image  -> Formularz_Obraz_Detalu.ui

Mapowanie pól edytora karty:
  Detal -> text_items2   (card.text_items[2])
  Ser.  -> text_items3   (card.text_items[3])
  Szt.  -> text_items4   (card.text_items[4])
  Braki -> Nowa_zmienna_Braki   (card.braki)
  Nazwa -> text_items2_2 (card.text_items[1])
  Uruchom -> Nowa_zmienna_Uruch (card.uruchom)
  Zakonczenie -> text_items0    (card.text_items[0])
  Klient -> nowa_zmiena_kienID  (card.klient)
  Uwagi -> tylko_na_form        (card.uwagi)

Przyciski cykliczne (karta): Tło/Font/Priorytet/Status/Flaga -> indeksy karty.
Wszystkie formularze maja zablokowane wymiary (bez rozciagania).
"""
import os

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QPushButton, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from modules.ui import form_style as fs
from modules.managers.card_history import add_note_history


def _ui_file(name):
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "assets", "ui_files", name)


def _obraz_dir():
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "assets", "Obrazy")


class CardEditDialog(QDialog):
    """Edycja karty - loadUi(Formularz_Edytor_Karty.ui) 1:1."""

    def __init__(self, card, mode="edit", view=None):
        super().__init__(view)
        self.card = card
        self.mode = mode
        uic.loadUi(_ui_file("Formularz_Edytor_Karty.ui"), self)
        self.setModal(True)
        self.setFixedSize(self.width(), self.height())
        self._load_values()
        self._apply_style()

        self.Zamyka_edycje.clicked.connect(self._apply_and_close)
        self.card_color.clicked.connect(self._on_tlo)
        self.klient_overlay.clicked.connect(self._on_flaga)
        self.font_index.clicked.connect(self._on_font)
        self.Overlay_files.clicked.connect(self._on_priorytet)
        self.status_icon.clicked.connect(self._on_status)
        self.nieuzywany.clicked.connect(self._on_info)
        self._connect_live()

    def _load_values(self):
        card = self.card
        self.text_items2.setText(card.text_items[2].toPlainText())
        self.text_items3.setText(card.text_items[3].toPlainText())
        self.text_items4.setText(card.text_items[4].toPlainText())
        self.Nowa_zmienna_Braki.setText(card.braki)
        self.text_items2_2.setText(card.text_items[1].toPlainText())
        self.Nowa_zmienna_Uruch.setText(card.uruchom)
        self.text_items0.setText(card.text_items[0].toPlainText())
        self.nowa_zmiena_kienID.setText(card.klient)
        self.tylko_na_form.setText(card.uwagi)

    def _apply(self):
        card = self.card
        card.text_items[2].setPlainText(self.text_items2.text())
        card.text_items[3].setPlainText(self.text_items3.text())
        card.text_items[4].setPlainText(self.text_items4.text())
        card.braki = self.Nowa_zmienna_Braki.text()
        card.text_items[1].setPlainText(self.text_items2_2.text())
        card.uruchom = self.Nowa_zmienna_Uruch.text()
        card.text_items[0].setPlainText(self.text_items0.text())
        card.klient = self.nowa_zmiena_kienID.text()
        card.uwagi = self.tylko_na_form.text()
        card.update()

    def _apply_and_close(self):
        self._apply()
        self.accept()

    # --- podglad na zywo (wpisy edytora widoczne na karcie od razu) ---

    def _connect_live(self):
        for name, idx in (
            ("text_items2", 2), ("text_items3", 3), ("text_items4", 4),
            ("text_items2_2", 1), ("text_items0", 0),
        ):
            getattr(self, name).textChanged.connect(
                lambda text, i=idx: self._set_text_live(i, text))
        self.Nowa_zmienna_Braki.textChanged.connect(
            lambda text: self._set_attr_live("braki", text))
        self.Nowa_zmienna_Uruch.textChanged.connect(
            lambda text: self._set_attr_live("uruchom", text))
        self.nowa_zmiena_kienID.textChanged.connect(
            lambda text: self._set_attr_live("klient", text))
        self.tylko_na_form.textChanged.connect(
            lambda text: self._set_attr_live("uwagi", text))

    def _set_text_live(self, idx, text):
        card = self.card
        if idx < len(card.text_items):
            card.text_items[idx].setPlainText(text)
        card.update()

    def _set_attr_live(self, attr, text):
        setattr(self.card, attr, text)
        self.card.update()

    # --- przyciski cykliczne ---

    def _on_tlo(self):
        card = self.card
        card.color_index = (card.color_index + 1) % len(card.colors)
        card.update()

    def _on_flaga(self):
        card = self.card
        card.klient_overlay_index = (card.klient_overlay_index + 1) % len(card.klient_overlays)
        card.update()

    def _on_font(self):
        card = self.card
        card.font_index = (card.font_index + 1) % len(card.font_families)
        card._apply_font()
        card.update()

    def _on_priorytet(self):
        card = self.card
        card.overlay_index = (card.overlay_index + 1) % len(card.overlays)
        card.sync_overlay_items()
        card.update()

    def _on_status(self):
        card = self.card
        card.status_index = (card.status_index + 1) % len(card.status_icon_files)
        card.update()

    def _on_info(self):
        card = self.card
        card.info_overlay_index = (card.info_overlay_index + 1) % len(card.info_overlays)
        card.sync_overlay_items()
        card.update()

    def _apply_style(self):
        self.setStyleSheet(fs.dialog_stylesheet())
        for btn in self.findChildren(QPushButton):
            btn.setStyleSheet(fs.button_stylesheet("small"))


class CardHoverDialog(QDialog):
    """Podglad karty (Hover) - loadUi(Formularz_Hover_karty.ui) 1:1."""

    def __init__(self, card, mode="preview", view=None):
        super().__init__(view)
        self.card = card
        self.mode = mode
        uic.loadUi(_ui_file("Formularz_Hover_karty.ui"), self)
        self.setModal(True)
        self.setFixedSize(self.width(), self.height())
        self._apply_style()
        self._fill_values()

        self.Zamyka_podglad.clicked.connect(self.accept)
        self.Id_obraz.clicked.connect(self._open_image)
        self.Id_TimeLine.clicked.connect(self._open_timeline)
        self.Id_NotesKarty.clicked.connect(self._open_notes)

    def _fill_values(self):
        card = self.card
        self.text_item1.setText(card.text_items[1].toPlainText())   # Nazwa
        self.text_item2.setText(card.text_items[2].toPlainText())   # Detal
        self.text_item3.setText(card.text_items[3].toPlainText())   # Ser
        self.text_item4.setText(card.text_items[4].toPlainText())   # Szt
        self.Nowa_zmienna_Uruch.setText(card.uruchom)
        self.text_item0.setText(card.text_items[0].toPlainText())   # Zakonczenie
        self.nowa_zmiena_kienID.setText(card.klient)
        self.tylko_na_form.setText(card.uwagi)

    def _open_notes(self):
        original = self.card.note_text

        def on_change(text):
            self.card.note_text = text
            self.card.update()

        def on_save(text):
            self.card.note_text = text
            if text and text != original:
                add_note_history(self.card, text)
            self.card.update()

        self._notes_dialog = CardNotesDialog(
            card=self.card, parent=self, text=original,
            on_save=on_save, on_change=on_change,
            title="Notes Karty", auto_line2="Notes Karty:   ", live=True
        )
        self._position_child(self._notes_dialog, from_right=True)
        self._notes_dialog.show()

    def _open_image(self):
        dialog = CardImageDialog(self.card, self)
        self._position_child(dialog, from_right=False)
        dialog.exec()

    def _open_timeline(self):
        try:
            import importlib
            timeline_plugin = importlib.import_module('modules.plugins.timeline_plugin')
            if hasattr(timeline_plugin, 'show_timeline'):
                timeline_plugin.show_timeline(self.card)
                return
        except Exception:
            pass
        try:
            from modules.ui.dialogs import TimelineDialog
            scene = self.card.scene()
            pm = scene.password_manager if scene else None
            TimelineDialog(self.card.history_text, card=self.card, password_manager=pm).exec()
        except Exception:
            pass

    def _position_child(self, dialog, from_right):
        """Ustawia okno 5px od krawedzi hovera, wyrównane górą."""
        gap = 5
        if from_right:
            x = self.x() + self.width() + gap
        else:
            x = self.x() - dialog.width() - gap
        dialog.move(x, self.y())

    def _refresh_notes_icon(self):
        self.card.update()

    def _apply_style(self):
        self.setStyleSheet(fs.dialog_stylesheet())
        for btn in self.findChildren(QPushButton):
            btn.setStyleSheet(fs.button_stylesheet("small"))


class CardNotesDialog(QDialog):
    """Notes - loadUi(Formularz_Notes_Karty.ui) 1:1. Przyciski: Wyczyść / Zamknij.

    Wspólny formularz dla wszystkich notesów (karta/kolumna/tabela):
      - card        -> zapis klasyczny (card.note_text + historia)
      - on_save(t)  -> własny zapis (zamiast card)
      - on_change(t)-> aktualizacja na bieżąco (live) w podglądzie
      - live=True   -> okno niemodalne, textChanged podbija on_change
    """

    def __init__(self, card=None, parent=None, text="", on_save=None, on_change=None,
                 title="Notes Karty", auto_line2="Notes Karty:   ", live=False):
        super().__init__(parent)
        self.card = card
        self._on_save = on_save
        self._on_change = on_change
        uic.loadUi(_ui_file("Formularz_Notes_Karty.ui"), self)
        self.setModal(not live)
        self.setWindowTitle(title)
        self.setFixedSize(self.width(), self.height())

        now = __import__("datetime").datetime.now()
        self._auto_line1 = now.strftime("%Y-%m-%d, %H:%M")
        self._auto_line2 = auto_line2
        self._auto_header = self._auto_line1 + "\n" + self._auto_line2

        initial = text if text else (card.note_text if card else "")
        self.textEdit.setPlainText(self._auto_header + "\n" + initial)

        # Kursor zaraz po tekscie naglowka (np. 'Notes Kolumny:   ').
        pos = len(self._auto_line1) + 1 + len(self._auto_line2)
        cursor = self.textEdit.textCursor()
        cursor.setPosition(pos)
        self.textEdit.setTextCursor(cursor)

        self._apply_style()
        self.Usuwa_wpisy.clicked.connect(self._clear)
        self.Zapisuje_wpis.clicked.connect(self._save_and_close)
        if live:
            self.textEdit.textChanged.connect(self._live_change)

    def _content(self):
        full = self.textEdit.toPlainText()
        content = full
        if full.startswith(self._auto_header):
            content = full[len(self._auto_header):]
            if content.startswith("\n"):
                content = content[1:]
        return content.strip()

    def _clear(self):
        self.textEdit.clear()

    def _live_change(self):
        if self._on_change:
            self._on_change(self._content())

    def _save_and_close(self):
        content = self._content()
        if self._on_save is not None:
            self._on_save(content)
        elif self.card is not None:
            old = self.card.note_text
            self.card.note_text = content
            if content and content != old:
                add_note_history(self.card, content)
            self.card.update()
        self.accept()

    def _apply_style(self):
        self.setStyleSheet(fs.dialog_stylesheet())
        for btn in self.findChildren(QPushButton):
            btn.setStyleSheet(fs.button_stylesheet("small"))


class CardImageDialog(QDialog):
    """Obraz detalu - loadUi(Formularz_Obraz_Detalu.ui) 1:1. Szuka po card.text_items[2] w assets\\Obrazy."""

    def __init__(self, card=None, parent=None):
        super().__init__(parent)
        self.card = card
        uic.loadUi(_ui_file("Formularz_Obraz_Detalu.ui"), self)
        self.setModal(True)
        self.setFixedSize(self.width(), self.height())

        label = QLabel(self)
        label.setGeometry(self.textEdit.geometry())
        label.setScaledContents(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        radius = label.width() // 2
        label.setStyleSheet(f"border-radius: {radius}px;")
        self.textEdit.setParent(None)
        self.textEdit.deleteLater()
        self._image_label = label

        self._load_image()
        self._apply_style()

    def _obraz_folder(self):
        """Folder zdjec detali: ustawienie sceny (Ustawienia) albo domyslny assets\\Obrazy."""
        if self.card is not None and self.card.scene() is not None:
            folder = getattr(self.card.scene(), "obraz_folder", "")
            if folder:
                return folder
        return _obraz_dir()

    def _load_image(self):
        detal = ""
        if self.card is not None and len(self.card.text_items) > 2:
            detal = self.card.text_items[2].toPlainText().strip()
        path = self._find_image(detal)
        pix = QPixmap(path)
        if pix.isNull():
            pix = QPixmap(os.path.join(self._obraz_folder(), "Brak obrazu.png"))
        self._image_label.setPixmap(pix)

    def _find_image(self, detal):
        """Szuka obrazu po numerze glownym (text_items[2]).

        Zasady dopasowania (bez rozrozniania wielkosci liter, biale znaki
        znormalizowane):
          1) nazwa pliku == numer glowny,
          2) nazwa zaczyna sie od numeru glownego (np. 'AEL66999_2.png'),
          3) numer glowny wystepuje w nazwie (np. 'karta AEL66999.png').
        """
        obr = self._obraz_folder()
        if not os.path.isdir(obr):
            return os.path.join(obr, "Brak obrazu.png")
        needle = "".join(detal.split()).lower() if detal else ""
        if not needle:
            return os.path.join(obr, "Brak obrazu.png")

        prefix_matches = []
        contain_matches = []
        for fname in os.listdir(obr):
            base, ext = os.path.splitext(fname)
            if ext.lower() not in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
                continue
            b = "".join(base.split()).lower()
            if not b:
                continue
            if b == needle:
                return os.path.join(obr, fname)
            if b.startswith(needle):
                prefix_matches.append((len(b), b, fname))
            elif needle in b:
                contain_matches.append((len(b), b, fname))

        for grp in (prefix_matches, contain_matches):
            if grp:
                grp.sort(key=lambda x: (x[0], x[1]))
                return os.path.join(obr, grp[0][2])
        return os.path.join(obr, "Brak obrazu.png")

    def _apply_style(self):
        self.setStyleSheet(fs.dialog_stylesheet())
