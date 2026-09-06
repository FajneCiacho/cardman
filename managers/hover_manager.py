"""
hover_manager.py - Wysuwanie panelu sceny po najechaniu kursorem (Faza 3).

Odpowiedzialnosci:
- stan maszynowy strefy REVEAL (gorny-srodkowy pas widoku),
- timer przytrzymania myszy -> pokaz panelu sceny,
- ukrywanie panelu po opuszczeniu strefy / widoku.

Przeniesione z KanbanView (_panel_hover_timer/_panel_zone_active/mouseMoveEvent/leaveEvent).
"""
from PyQt6.QtCore import QTimer


class HoverManager:
    """Zarzadza wysuwaniem panelu sceny na podstawie pozycji kursora."""

    REVEAL_ZONE_HEIGHT = 70   # gorny pas (px) uruchamiajacy wysuw
    REVEAL_ZONE_HALF_W = 130  # polowa szerokosci strefy wokol srodka (px)

    def __init__(self, view):
        self.view = view
        self._panel_hover_timer = QTimer(view)
        self._panel_hover_timer.setSingleShot(True)
        self._panel_hover_timer.timeout.connect(self._reveal_scene_panel)
        self._panel_zone_active = False

    def _scene_panel(self):
        scene = self.view.scene()
        return getattr(scene, 'scene_panel', None) if scene else None

    def _in_reveal_zone(self, pos):
        vp = self.view.viewport().rect()
        center_x = vp.width() // 2
        return (pos.y() <= self.REVEAL_ZONE_HEIGHT and
                abs(pos.x() - center_x) <= self.REVEAL_ZONE_HALF_W)

    def _reveal_scene_panel(self):
        panel = self._scene_panel()
        if panel:
            panel.show_panel()

    def handle_mouse_move(self, event):
        """Delegacja z KanbanView.mouseMoveEvent (czesc dot. panelu sceny)."""
        panel = self._scene_panel()
        if panel is not None:
            in_zone = self._in_reveal_zone(event.position().toPoint())
            if in_zone and not self._panel_zone_active:
                self._panel_zone_active = True
                self._panel_hover_timer.start(panel.HOVER_HOLD_MS)
            elif not in_zone and self._panel_zone_active:
                self._panel_zone_active = False
                self._panel_hover_timer.stop()
                panel.hide_panel()

    def handle_leave(self):
        """Delegacja z KanbanView.leaveEvent."""
        if self._panel_zone_active:
            self._panel_zone_active = False
            self._panel_hover_timer.stop()
            panel = self._scene_panel()
            if panel:
                panel.hide_panel()
