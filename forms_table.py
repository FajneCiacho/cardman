"""
forms_table.py - Formularze TABELI (Faza 7.1).

Wczytuje zaprojektowane w Qt Designerze pliki .ui 1:1:
  - edit    -> Formularz_Edytor_Tabeli.ui
  - preview -> Formularz_Hover_Tabeli.ui

Mapowanie pól edytora tabeli:
  Główna nazwa   -> Formularz_Edytor_Głównej_Nazwy.ui (TableNameDialog)
                   edytowana na napisie kanban_text (Ctrl+LPM na tekscie)
  Linia/Gniazdo  -> title_text_left   (table.title_text_left)
  Spec.          -> tylko_na_form_2   (informacyjny, nie zapisywany)
  Opis           -> title_text_right_2 (table.title_text_right)
  Ignoruj kolumne-> title_text_right_1 (table.title_text_right1 = "#")
  Ignoruj pole   -> header_line4       (kolumny tabeli = "#")
  Kolor Belki    -> title_colors       (cykliczna zmiana title_color_index)

Hover tabeli (podglad, etykiety tylko do odczytu) przejmuje akcje dawnego MENU
TABELI (Dodaj/Usun tabele, wiersze, kolumny, Rysuj/Opisz Strefe, Połącz Tabele)
oraz Odblokuj/Zablokuj edycje.
Wszystkie formularze maja zablokowane wymiary (bez rozciagania).
"""
import os

from PyQt6 import uic
from PyQt6.QtWidgets import QDialog, QPushButton

from modules.ui import form_style as fs
from config import BASE_COLUMNS


def _ui_file(name):
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "assets", "ui_files", name)


class TableEditDialog(QDialog):
    """Edycja tabeli - loadUi(Formularz_Edytor_Tabeli.ui) 1:1."""

    def __init__(self, table, mode="edit", view=None):
        super().__init__(view)
        self.table = table
        self.mode = mode
        uic.loadUi(_ui_file("Formularz_Edytor_Tabeli.ui"), self)
        self.setModal(True)
        self.setFixedSize(self.width(), self.height())
        self._load_values()
        self._apply_style()

        self.Zamyka_edycje_3.clicked.connect(self._apply_and_close)
        self.title_colors.clicked.connect(self._on_title_colors)

    def _load_values(self):
        table = self.table
        self.title_text_left.setText(table.title_text_left.toPlainText())
        self.title_text_right_2.setText(table.title_text_right.toPlainText())
        self.title_text_right_1.setChecked(table.title_text_right1.strip() == "#")
        self.header_line4.setChecked(bool(table.columns) and
                                     table.columns[0].header_line4.strip() == "#")

    def _apply(self):
        table = self.table
        table.title_text_left.setPlainText(self.title_text_left.text().strip())
        table.title_text_right.setPlainText(self.title_text_right_2.text().strip())
        table.title_text_right1 = "#" if self.title_text_right_1.isChecked() else "*"

        flag = "#" if self.header_line4.isChecked() else "*"
        for col in table.columns:
            col.header_line4 = flag

        table.relayout()
        table.update()

    def _apply_and_close(self):
        self._apply()
        self.accept()

    def _on_title_colors(self):
        table = self.table
        table.title_color_index = (table.title_color_index + 1) % table._title_colors_count()
        table.update()

    def _apply_style(self):
        self.setStyleSheet(fs.dialog_stylesheet())
        for btn in self.findChildren(QPushButton):
            btn.setStyleSheet(fs.button_stylesheet("small"))


class TableNameDialog(QDialog):
    """Edycja Glownej nazwy - loadUi(Formularz_Edytor_Głównej_Nazwy.ui) 1:1.

    Otwierany przez Ctrl + klik LPM na napisie kanban_text (Główna nazwa).
    Zmiana tekstu jest podgladana na tabeli w czasie rzeczywistym.
    """

    def __init__(self, table, mode="edit", view=None):
        super().__init__(view)
        self.table = table
        self.mode = mode
        uic.loadUi(_ui_file("Formularz_Edytor_Głównej_Nazwy.ui"), self)
        self.setModal(True)
        self.setFixedSize(self.width(), self.height())
        self._apply_style()
        self.KANBAN_TEXT.setText(table.kanban_text.toPlainText())
        self.KANBAN_TEXT.textChanged.connect(self._on_live)
        self.Zamyka_edycje_3.clicked.connect(self._apply_and_close)

    def _on_live(self, text):
        self.table.kanban_text.setPlainText(text)
        self.table.update()

    def _apply_and_close(self):
        self._on_live(self.KANBAN_TEXT.text())
        self.accept()

    def _apply_style(self):
        self.setStyleSheet(fs.dialog_stylesheet())
        for btn in self.findChildren(QPushButton):
            btn.setStyleSheet(fs.button_stylesheet("small"))


class TableHoverDialog(QDialog):
    """Podglad tabeli (Hover) - loadUi(Formularz_Hover_Tabeli.ui) 1:1.

    Przejmuje akcje dawnego MENU TABELI oraz Zablokuj/Odblokuj edycje.
    """

    def __init__(self, table, mode="preview", view=None):
        super().__init__(view)
        self.table = table
        self.mode = mode
        uic.loadUi(_ui_file("Formularz_Hover_Tabeli.ui"), self)
        self.setModal(True)
        self.setFixedSize(self.width(), self.height())
        self._apply_style()
        self._fill_values()
        self._sync_lock_button()

        self.Zamyka_edycje_2.clicked.connect(self._apply_and_close)
        self.pushButton.clicked.connect(self._add_table)
        self.pushButton_8.clicked.connect(self._remove_table)
        self.pushButton_2.clicked.connect(self._add_row)
        self.pushButton_5.clicked.connect(self._remove_row)
        self.pushButton_3.clicked.connect(self._add_column)
        self.pushButton_7.clicked.connect(self._remove_column)
        self.pushButton_13.clicked.connect(self._connect_tables)
        self.pushButton_9.clicked.connect(self._draw_zone)
        self.pushButton_10.clicked.connect(self._describe_zone)
        self.pushButton_11.clicked.connect(self._toggle_lock)

        self.pushButton.setEnabled(self.table.is_base_table)
        has_cards = any(len(col.cards) > 0 for col in self.table.columns)
        self.pushButton_8.setEnabled(not self.table.is_base_table and not has_cards)
        self.pushButton_5.setEnabled(self.table.extra_rows > 0)
        self.pushButton_7.setEnabled(
            len(self.table.columns) > BASE_COLUMNS and
            len(self.table.columns[-1].cards) == 0
        )
        # Połącz Tabele - nieaktywne, gdy brak drugiej tabeli.
        scene = self.table.scene()
        self.pushButton_13.setEnabled(scene is not None and len(scene.tables) > 1)

    def _fill_values(self):
        table = self.table
        # Etykiety (tylko do odczytu) w podgladzie tabeli.
        self.title_text_left.setText(table.title_text_left.toPlainText())

    def _sync_lock_button(self):
        if self.table._editing:
            self.pushButton_11.setText("Zablokuj Tabele")
        else:
            self.pushButton_11.setText("Odblokuj Tabele")

    def _apply_and_close(self):
        self.accept()

    # --- akcje z MENU TABELI ---

    def _add_table(self):
        scene = self.table.scene()
        if scene is not None:
            scene.add_new_table()

    def _remove_table(self):
        scene = self.table.scene()
        if scene is not None:
            scene.remove_table(self.table)
        self.accept()

    def _add_row(self):
        self.table.add_body_row()

    def _remove_row(self):
        self.table.remove_body_row()
        self.pushButton_5.setEnabled(self.table.extra_rows > 0)

    def _add_column(self):
        self.table.add_column()
        self.pushButton_7.setEnabled(
            len(self.table.columns) > BASE_COLUMNS and
            len(self.table.columns[-1].cards) == 0
        )

    def _remove_column(self):
        self.table.remove_column()
        self.pushButton_7.setEnabled(
            len(self.table.columns) > BASE_COLUMNS and
            len(self.table.columns[-1].cards) == 0
        )

    def _connect_tables(self):
        scene = self.table.scene()
        if scene is not None:
            scene.start_connecting(self.table)
        self.accept()

    def _draw_zone(self):
        scene = self.table.scene()
        if scene is not None:
            scene.start_zone_draw()
        self.accept()

    def _describe_zone(self):
        scene = self.table.scene()
        if scene is not None:
            scene.start_zone_description()
        self.accept()

    def _toggle_lock(self):
        if self.table._editing:
            self.table.exit_table_edit_mode()
        else:
            self.table.enter_table_edit_mode()
        self._sync_lock_button()

    def _apply_style(self):
        self.setStyleSheet(fs.dialog_stylesheet())
        for btn in self.findChildren(QPushButton):
            btn.setStyleSheet(fs.button_stylesheet("small"))
