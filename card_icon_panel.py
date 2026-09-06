"""
card_icon_panel.py - Wysuwany glowny panel ikon sceny

Plugin ladowany dynamicznie. Zawiera SceneIconPanel - glowny panel programu,
przyklejony do gornej-srodkowej krawedzi okna, wysuwany po najechaniu kursorem.
"""

from PyQt6.QtWidgets import (
    QGraphicsObject, QGraphicsItem, QMessageBox, QDialog,
)
from PyQt6.QtCore import (
    Qt, QRectF, QPropertyAnimation, QEasingCurve, pyqtProperty,
)
from PyQt6.QtSvgWidgets import QGraphicsSvgItem


import os
import sys


def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if relative_path.lower().endswith('.svg'):
        return os.path.join(base_path, "assets/svg", relative_path)
    return os.path.join(base_path, relative_path)


class SvgIconButton(QGraphicsSvgItem):
    """SVG-based ikonka przyciskowa."""

    def __init__(self, svg_path, action_callback, parent=None):
        super().__init__(svg_path, parent)
        self.action_callback = action_callback
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        try:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        except Exception:
            pass

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.action_callback:
                self.action_callback()
            event.accept()
            return
        super().mousePressEvent(event)


class _IconPanelBase(QGraphicsObject):
    """
    Wspolna baza stylu dla panelu ikon sceny.
    Wspoldzieli: proporcje/marginesy/odstepy, animacje (fade) i obsluge klikniec.
    Podklasy moga nadpisac stale stylu ponizej.
    """

    # --- wspolny styl ---
    ICON_SIZE1 = 40
    ICON_SPACING = 15
    TOP_MARGIN = 10
    EDGE_MARGIN = 20
    ANIMATION_DURATION = 200
    HOVER_HOLD_MS = 400

    def __init__(self, parent=None):
        super().__init__(parent)
        self._opacity = 0.0

    # --- wspolna wlasciwosc opacity (fade calego panelu) ---
    def get_panel_opacity(self):
        return self._opacity

    def set_panel_opacity(self, value):
        self._opacity = value
        self.setOpacity(value)
        self.update()

    panelOpacity = pyqtProperty(float, fget=get_panel_opacity, fset=set_panel_opacity)


class SceneIconPanel(_IconPanelBase):
    """
    Glowny panel programu, przyklejony do gornej-srodkowej krawedzi okna.

    5 ikon w jednej linii (od prawej): BLOK, INFO2 (notatnik/wiadomosci),
    NOTES (informacje ogolne), KARTY (wyszukiwarka), USTAWIENIA.

    Panel ignoruje zoom/pan (ItemIgnoresTransformations) i trzyma stala pozycje
    na ekranie. Domyslnie schowany; wysuwany po najechaniu kursorem (obsluga w
    KanbanView, ktory po ~1 s przytrzymania wola show_panel()).

    Ikony stanowe pozostaja widoczne na scenie mimo schowania panelu:
      - BLOK1  gdy scena zablokowana,
      - INFO2A gdy notatnik zawiera wpis.
    """

    ICON_SIZE = 40
    ICON_SPACING = 15
    TOP_MARGIN = 10
    N_ICONS = 5

    def __init__(self, view, scene, password_manager=None, parent=None):
        super().__init__(parent)
        self.view = view
        self.scene_ref = scene
        self.password_manager = password_manager
        self._expanded = False
        self._reveal = 0.0

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self.setZValue(10001)
        # Klikniecia obsluguja dzieci-ikony; sam panel nie przechwytuje.
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        self._panel_width = self.N_ICONS * self.ICON_SIZE + (self.N_ICONS - 1) * self.ICON_SPACING

        # Animacja wysuwania (fade ikon chowanych z panelem)
        self.reveal_anim = QPropertyAnimation(self, b"revealAmount")
        self.reveal_anim.setDuration(self.ANIMATION_DURATION)
        self.reveal_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        self._collapsible = []
        self._create_icons()
        self._apply_visibility()

    # --- wlasciwosc wysuwania -> opacity ikon chowanych ---
    def get_reveal(self):
        return self._reveal

    def set_reveal(self, value):
        self._reveal = value
        for ic in self._collapsible:
            ic.setOpacity(value)
        self.update()

    revealAmount = pyqtProperty(float, fget=get_reveal, fset=set_reveal)

    def boundingRect(self):
        return QRectF(0, 0, self._panel_width, self.ICON_SIZE)

    def paint(self, painter, option, widget=None):
        # Tlo przezroczyste - widoczne tylko ikony.
        pass

    # --- budowa ikon ---
    def _slot_x(self, index_from_right):
        """Wspolrzedna X slotu liczona od prawej (0 = najbardziej z prawej)."""
        rightmost = self._panel_width - self.ICON_SIZE
        return rightmost - index_from_right * (self.ICON_SIZE + self.ICON_SPACING)

    def _make_icon(self, filename, callback, index_from_right):
        svg_path = resource_path(os.path.splitext(filename)[0] + ".svg")
        icon = SvgIconButton(svg_path, callback, self)
        br = icon.boundingRect()
        if br.width() > 0:
            icon.setScale(float(self.ICON_SIZE) / float(br.width()))
        icon.setPos(self._slot_x(index_from_right), 0)
        icon.setZValue(10002)
        return icon

    def _make_state_icon(self, filename, callback):
        """Ikona stanowa na scenie (poza panelem): prawy gorny rog okna."""
        svg_path = resource_path(os.path.splitext(filename)[0] + ".svg")
        icon = SvgIconButton(svg_path, callback)
        icon.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        br = icon.boundingRect()
        if br.width() > 0:
            icon.setScale(float(self.ICON_SIZE) / float(br.width()))
        icon.setZValue(10003)
        icon.setOpacity(1.0)
        scene = self.scene_ref
        if scene is not None:
            scene.addItem(icon)
        return icon

    def _create_icons(self):
        # Kolejnosc od prawej: 0=BLOK, 1=INFO2, 2=NOTES, 3=KARTY, 4=USTAWIENIA
        self.icon_blok = self._make_icon("BLOK.svg", self._on_blok, 0)
        self.icon_blok1 = self._make_state_icon("BLOK1.svg", self._on_blok)
        self.icon_info2 = self._make_icon("INFO2.svg", self._on_info2, 1)
        self.icon_info2a = self._make_state_icon("INFO2A.svg", self._on_info2)
        self.icon_notes = self._make_icon("NOTES.svg", self._on_notes, 2)
        self.icon_karty = self._make_icon("KARTY.svg", self._on_karty, 3)
        self.icon_ustawienia = self._make_icon("USTAWIENIA.svg", self._on_ustawienia, 4)

        # Ikony chowane wraz z panelem (fade). Ikony stanowe BLOK1/INFO2A NIE sa
        # tutaj - pozostaja na scenie z pelna widocznoscia.
        self._collapsible = [
            self.icon_blok, self.icon_info2,
            self.icon_notes, self.icon_karty, self.icon_ustawienia,
        ]
        for ic in self._collapsible:
            ic.setOpacity(self._reveal)

    # --- stan ---
    def _is_locked(self):
        return bool(getattr(self.scene_ref, "is_scene_blocked", False))

    def _has_message(self):
        return bool((getattr(self.scene_ref, "main_notes", "") or "").strip())

    def _apply_visibility(self):
        """Ustawia widocznosc ikon wg stanu (rozwiniety/zwiniety, blokada, wiadomosc)."""
        locked = self._is_locked()
        msg = self._has_message()
        exp = self._expanded

        # Slot BLOK: wariant zablokowany trwaly, wariant normalny chowany z panelem
        self.icon_blok1.setVisible(locked)
        self.icon_blok.setVisible(exp and not locked)
        # Slot INFO2: wariant z wiadomoscia trwaly, wariant pusty chowany z panelem
        self.icon_info2a.setVisible(msg)
        self.icon_info2.setVisible(exp and not msg)
        # Pozostale ikony (jednostanowe) - tylko gdy panel rozwiniety
        for ic in (self.icon_notes, self.icon_karty, self.icon_ustawienia):
            ic.setVisible(exp)

    # --- wysuwanie / chowanie ---
    def show_panel(self):
        if self._expanded:
            return
        self._expanded = True
        self._apply_visibility()
        self.reveal_anim.stop()
        try:
            self.reveal_anim.finished.disconnect()
        except Exception:
            pass
        self.reveal_anim.setStartValue(self._reveal)
        self.reveal_anim.setEndValue(1.0)
        self.reveal_anim.start()

    def hide_panel(self):
        if not self._expanded:
            self._apply_visibility()
            return
        self.reveal_anim.stop()
        self.reveal_anim.setStartValue(self._reveal)
        self.reveal_anim.setEndValue(0.0)

        def on_hidden():
            self._expanded = False
            self._apply_visibility()

        try:
            self.reveal_anim.finished.disconnect()
        except Exception:
            pass
        self.reveal_anim.finished.connect(on_hidden)
        self.reveal_anim.start()

    def toggle_panel(self):
        if self._expanded:
            self.hide_panel()
        else:
            self.show_panel()

    def refresh_states(self):
        """Odswieza widocznosc wariantow ikon wg stanu sceny (np. po wczytaniu zapisu)."""
        self._apply_visibility()
        self.update()

    def update_position(self):
        """Pozycjonuje panel na gorze-srodku widoku + ikony stanowe w prawym gornym rogu."""
        if not self.view:
            return
        vp = self.view.viewport().rect()
        left_px = vp.width() // 2 - self._panel_width // 2
        scene_pos = self.view.mapToScene(int(left_px), int(self.TOP_MARGIN))
        self.setPos(scene_pos)
        self._update_state_icons_position()

    def _update_state_icons_position(self):
        """BLOK1: prawy gorny rog okna (10px od krawedzi). INFO2A: 10px od
        prawej krawedzi i 5px pod ikona BLOK1."""
        if not self.view:
            return
        vp = self.view.viewport().rect()
        right_x = vp.width() - self.ICON_SIZE - 10
        top_y = 10
        self.icon_blok1.setPos(self.view.mapToScene(int(right_x), int(top_y)))
        br1 = self.icon_blok1.boundingRect()
        h1 = br1.height() * self.icon_blok1.scale()
        self.icon_info2a.setPos(
            self.view.mapToScene(int(right_x), int(top_y + h1 + 5))
        )

    # --- akcje ikon ---
    def _after_action(self):
        self.refresh_states()
        self.hide_panel()

    def _on_blok(self):
        """BLOK - blokada/odblokowanie sceny. Panel chowa sie, BLOK1 zostaje gdy zablokowane."""
        scene = self.scene_ref
        if self._is_locked() and self.password_manager is not None:
            pwd = self.password_manager.prompt_for_password(
                self.view, title="Odblokowanie sceny", text="Podaj haslo:")
            if pwd is None or not self.password_manager.verify_password(pwd):
                QMessageBox.warning(self.view, "Bledne haslo", "Niepoprawne haslo.")
                return
        new_state = not self._is_locked()
        if scene is not None and hasattr(scene, "set_scene_blocked"):
            scene.set_scene_blocked(new_state)
        self._after_action()

    def _on_info2(self):
        """INFO2 - notatnik/wiadomosci. INFO2A zostaje na scenie gdy jest wpis."""
        scene = self.scene_ref
        try:
            manager = getattr(scene, "notebook_manager", None)
            if manager is not None:
                manager.open_main_notes(view=self.view)
            else:
                from modules.ui.dialogs import MainNotesDialog
                dialog = MainNotesDialog(getattr(scene, "main_notes", ""), self.view)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    scene.main_notes = dialog.get_text()
        except Exception:
            pass
        self._after_action()

    def _on_notes(self):
        """NOTES - manager notatek produkcyjnych (telefony, pracownicy)."""
        scene = self.scene_ref
        try:
            manager = getattr(scene, "notebook_manager", None)
            if manager is not None:
                manager.open_notes_manager(view=self.view)
            else:
                from modules.ui.dialogs import NotesManagerDialog
                notes_data = getattr(scene, "notes_data", [])
                dialog = NotesManagerDialog(notes_data, self.view)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    scene.notes_data = dialog.get_notes_data()
        except Exception:
            pass
        self._after_action()

    def _on_karty(self):
        """KARTY - wyszukiwarka/lista kart (przez SearchManager)."""
        scene = self.scene_ref
        try:
            manager = getattr(scene, "search_manager", None)
            if manager is not None:
                manager.open_karty_list(scene, self.view)
            else:
                from modules.core.KARTY import KartyListDialog
                cards = []
                for t in getattr(scene, "tables", []):
                    for col in getattr(t, "columns", []):
                        for c in getattr(col, "cards", []):
                            cards.append(c)
                KartyListDialog(cards).exec()
        except Exception:
            pass
        self._after_action()

    def _on_ustawienia(self):
        """USTAWIENIA - otwiera okno ustawien (folder zapisu EXCEL/TIME LINE + przyciemnianie sceny)."""
        scene = self.scene_ref
        try:
            from modules.ui.dialogs import SettingsDialog
            dialog = SettingsDialog(scene, self.view)
            dialog.exec()
        except Exception as e:
            print("Ustawienia:", e)
        self._after_action()


# === INTERFEJS PLUGINU ===

PLUGIN_NAME = "Card Icon Panel"
PLUGIN_DESCRIPTION = "Wysuwane panele ikon (karta + scena)"
PLUGIN_VERSION = "2.0.0"
PLUGIN_REQUIRES = []


def is_available():
    return True


def get_info():
    return {
        "name": PLUGIN_NAME,
        "description": PLUGIN_DESCRIPTION,
        "version": PLUGIN_VERSION,
        "available": True,
        "requires": PLUGIN_REQUIRES,
    }


def create_scene_panel(view, scene, password_manager=None):
    """Tworzy glowny panel sceny."""
    return SceneIconPanel(view, scene, password_manager)
