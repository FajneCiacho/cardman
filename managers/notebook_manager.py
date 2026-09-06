"""
notebook_manager.py - Zarzadzanie notatkami (Faza 3).

Odpowiedzialnosci:
- glowny notatnik (main_notes) i notatki produkcyjne (notes_data),
- otwieranie dialogow notatek (MainNotesDialog / NotesManagerDialog),
- stan ikony INFO2A (czy jest wpis).

Dane sa wlasnoscia managera; KanbanScene deleguje przez properties.
"""
from PyQt6.QtWidgets import QDialog


class NotebookManager:
    """Notatki sceny: glowny notatnik i notatki produkcyjne."""

    def __init__(self):
        self.main_notes = ""
        self.notes_data = []

    # --- stan ---

    def has_main_notes(self):
        """Czy glowny notatnik zawiera jakis wpis (stan INFO2A)."""
        return bool((self.main_notes or "").strip())

    # --- serializacja (dane scigane do/ze sceny) ---

    def to_dict(self):
        return {
            "main_notes": self.main_notes,
            "notes_data": self.notes_data,
        }

    def from_dict(self, data):
        self.main_notes = data.get("main_notes", "")
        self.notes_data = data.get("notes_data", [])

    # --- dialogi ---

    def open_main_notes(self, parent=None, view=None):
        """Otwiera glowny notatnik. Zwraca True, gdy zapisano zmiany."""
        from modules.ui.dialogs import MainNotesDialog
        dialog = MainNotesDialog(self.main_notes, view)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.main_notes = dialog.get_text()
            return True
        return False

    def open_notes_manager(self, parent=None, view=None):
        """Otwiera manager notatek produkcyjnych. Zwraca True, gdy zapisano."""
        from modules.ui.dialogs import NotesManagerDialog
        dialog = NotesManagerDialog(self.notes_data, view)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.notes_data = dialog.get_notes_data()
            return True
        return False
