"""
edit_manager.py - Tryb edycji tabel (Faza 3).

Odpowiedzialnosci:
- zarzadzanie aktywnym trybem edycji tabeli,
- zamykanie trybu edycji po kliknieciu poza obiektem.

Przeniesione z KanbanScene (_set_editing_table/mousePressEvent).
Tryb edycji karty usuniety (zastepiony formularzami karty, Faza 7.1).
"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTransform


class EditManager:
    """Stan trybu edycji tabel."""

    def __init__(self):
        self.editing_table = None

    # --- ustawianie aktywnego obiektu edycji ---

    def set_editing_table(self, scene, table):
        """Wlacza edycje tabeli (wylaczajac ewentualna poprzednia tabele)."""
        if self.editing_table and self.editing_table is not table:
            self.editing_table.exit_table_edit_mode()
        self.editing_table = table

    def table_exited(self, table):
        if self.editing_table is table:
            self.editing_table = None

    # --- klikniecia ---

    @staticmethod
    def _is_item_or_child(item, target):
        if item is target:
            return True
        node = item.parentItem()
        while node is not None:
            if node is target:
                return True
            node = node.parentItem()
        return False

    def handle_scene_click(self, scene, event):
        """Zamyka tryb edycji przy kliknieciu poza obiektem."""
        if self.editing_table and event.button() == Qt.MouseButton.LeftButton:
            item = scene.itemAt(event.scenePos(), QTransform())
            if item is None or not self._is_item_or_child(item, self.editing_table):
                self.editing_table.exit_table_edit_mode()
                self.editing_table = None

        return False
