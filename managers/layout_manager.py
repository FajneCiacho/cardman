"""
layout_manager.py - Uklad sceny: pozycje, blokada, ikona kanban (Faza 3).

Odpowiedzialnosci:
- pozycjonowanie ikony kanban nad tabela bazowa,
- hit-test ikony kanban i tworzenie karty z ikony,
- blokada/odblokowanie sceny,
- centrowanie + zoom widoku na tabeli bazowej.

Przeniesione z KanbanScene i MainWindow._center_and_zoom_table.
"""


class LayoutManager:
    """Zarzadza ukladem sceny."""

    def position_kanban_icon(self, scene):
        """Ustawia ikone nad tabela bazowa, wyrownana do prawej krawedzi."""
        if scene.tables and scene.kanban_icon:
            table = scene.tables[0]
            table_rect = table.boundingRect()
            table_pos = table.pos()
            x = table_pos.x() + table_rect.width() - 125
            y = table_pos.y() - 123
            scene.kanban_icon.setPos(x, y)

    def get_kanban_icon_at(self, scene, scene_pos):
        """Sprawdza czy pozycja jest na ikonie Kanban."""
        if scene.kanban_icon:
            icon_rect = scene.kanban_icon.sceneBoundingRect()
            if icon_rect.contains(scene_pos):
                return scene.kanban_icon
        return None

    def create_new_card_from_kanban(self, scene, kanban_icon):
        """Tworzy nowa karte z ikony kanban (przez fabryke sceny, Faza 4.4)."""
        card = scene.create_new_card()
        card._is_new_card = True
        icon_pos = kanban_icon.scenePos()
        card.setPos(icon_pos.x() - 100, icon_pos.y() + 150)
        card.setZValue(2000)
        card.setScale(1.0)
        scene._pending_card = card
        # Po uruchomieniu nowej karty otwiera sie od razu edytor karty.
        try:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._open_card_editor(scene, card))
        except Exception:
            pass
        return card

    def _open_card_editor(self, scene, card):
        """Otwiera edytor karty dla nowo utworzonej karty."""
        try:
            from modules.managers.form_manager import FormManager
            FormManager.open_edit_dialog_static(card)
        except Exception as exc:
            print("LayoutManager: nie mozna otworzyc edytora karty:", exc)

    def set_scene_blocked(self, scene, blocked):
        """Blokuje/odblokowuje wszystkie elementy sceny."""
        for table in scene.tables:
            table.setEnabled(not blocked)
            for col in table.columns:
                col.setEnabled(not blocked)
                for card in col.cards:
                    card.setEnabled(not blocked)

    def center_and_zoom(self, scene, view):
        """Centruje widok na tabeli bazowej i ustawia zoom."""
        table = scene.tables[0]
        rect = table.sceneBoundingRect()
        view.centerOn(rect.center())
        vp = view.viewport().rect()
        if vp.width() > 0 and vp.height() > 0 and rect.width() > 0 and rect.height() > 0:
            sx = (vp.width() * 0.65) / rect.width()
            sy = (vp.height() * 0.65) / rect.height()
            s = min(sx, sy)
            view.resetTransform()
            view.centerOn(rect.center())
            view.scale(s, s)
