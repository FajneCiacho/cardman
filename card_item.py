"""
card_item.py - Karta Kanban (Faza 4, krok 4.3).

Przeniesione 1:1 z kanban_items.py: CardItem.
Karta przechowuje dane i wyglad; logika zarzadzcza w managerach.
"""
from datetime import datetime

from PyQt6.QtWidgets import QGraphicsObject, QGraphicsItem
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QPen, QFontMetrics, QPainterPath, QTransform,
)
from PyQt6.QtCore import (
    Qt, QRectF, QPropertyAnimation, QAbstractAnimation,
    QEasingCurve, pyqtProperty, QPointF,
)
from PyQt6.QtSvgWidgets import QGraphicsSvgItem

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import CARD_W, CARD_H, CARD_RADIUS, DRAG_START_DISTANCE

from modules.core.text_items import SingleLineText
from modules.core.icon_utils import (
    create_icon_item, load_icon, _draw_icon_on_painter, resource_path,
)
from modules.core.column_item import ColumnItem
from modules.utils import new_id


class CardItem(QGraphicsObject):
    """Karta Kanban - główny element wizualny."""
    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.width, self.height = CARD_W, CARD_H
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        # Identyfikator karty (Faza 4.4) - stabilny w serializacji
        self.id = new_id("card-")
        self.is_dragging = False
        self.potential_drag = False
        self._drag_start_scene_pos = QPointF()
        self._drag_offset = QPointF()
        self._original_parent = None
        self._original_local_pos = None
        self._original_column = None
        self._original_index = -1

        self.setFlags(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable)
        self.current_column = None

        self.pos_anim = QPropertyAnimation(self, b"pos")
        self.pos_anim.setDuration(260)
        self.pos_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        self._scale_factor = 1.0
        self.scale_anim = QPropertyAnimation(self, b"scaleFactor")
        self.scale_anim.setDuration(80)
        self.scale_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        # Katalogi wygladu z AppearanceManager (Faza 3) lub fallback (1:1)
        _ap = self._appearance()
        if _ap is not None:
            self.colors = list(_ap.card_colors)
            self.font_families = list(_ap.font_families)
            self.status_icon_files = list(_ap.status_icon_files)
            self.overlays = list(_ap.overlay_files)
            self.klient_overlays = list(_ap.klient_overlays)
            self.info_overlays = list(_ap.info_overlays)
        else:
            self.colors = [
                QColor("#F7E2D7"), QColor("#DED0C3"), QColor("#EBD2B5"),
                QColor("#B3B3B3"), QColor("#C5DFF0"), QColor("#C9EBC3"),
            ]
            self.font_families = ["Huxley Titling", "Gill Sans MT Ext Condensed Bold", "Corporate"]
            self.status_icon_files = [
                "Produkcja.svg",
                "Wstrzymane.svg",
            ]
            self.overlays = ["", "Opis.svg"]
            self.klient_overlays = [""] + [f"GRUPA{i}.svg" for i in range(1, 9)]
            self.info_overlays = ["", "Nadzor.svg", "Poprawa.svg"]

        self.color_index = 0
        self.font_index = 0
        self._ensure_fonts_loaded()

        # Ikony - nowe pozycje
        POZ_Y = 1  # 5px nad gorna krawedzia karty
        
        # Ikony INFO
        self.info_icon_full_file = "INFO.svg"
        self.info_rect = QRectF(370, 5, 15, 15)

        self.status_index = 0
        self._last_status_index = 0
        self.status_rect = QRectF(355, 115, 30, 30)

        self.overlay_index = 0
        self._last_overlay_index = 0

        self.klient_overlay_index = 0

        # Nakladka INFO (przycisk 'Info' w edytorze karty).
        self.info_overlay_index = 0

        # Nakladki Priorytet (Opis.svg) i INFO (Nadzor/Poprawa) nad warstwa
        # fontow - osobne itemy ponad tekstem (zValue > tekst).
        self._priority_overlay_item = None
        self._info_overlay_item = None
        self._overlay_above_fonts_key = None

        # Permanent overlay (managed as separate item)
        self.permanent_overlay_file = ""
        self._perm_overlay_item = None

        self.note_text = ""
        self.history_text = ""

        # Nowe zmienne karty (Faza 7.1 - formularze karty).
        self.braki = ""
        self.uruchom = ""
        self.klient = ""
        self.uwagi = ""
        self._last_table_title = ""
        self._last_column_header = ""
        self._last_position = -1
        self._original_color_index = None
        self._is_search_highlighted = False
        self._suppress_next_context_menu = False

        # Nowe wymiary i pozycje tekstow
        TEXT_LINES = [
            ("", 45, 5, 120, "Arial", 14, True, True),
            ("", 155, 5, 260, "Arial", 8, True, True),
            ("", 30, 13, 360, "Huxley Titling", 74, True, False),
            ("", 160, 117, 110, "Arial", 22, True, False),
            ("", 280, 124, 90, "Arial", 16, True, True),
        ]

        self.text_items = []
        for txt, x, y, max_px, fam, size, bold, italic in TEXT_LINES:
            f = QFont(fam, size)
            f.setBold(bold)
            f.setItalic(italic)
            if fam == "Huxley Titling":
                f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,1)
            t = SingleLineText(txt, max_px, self)
            t.setFont(f)
            t.setDefaultTextColor(QColor("#002D57"))
            t.setPos(x, y)
            t.setZValue(2500)  # Nad nakladka karty
            self.text_items.append(t)

        # Mark the ser (series) field to use right-to-left input and right-aligned rendering
        try:
            if len(self.text_items) > 3:
                setattr(self.text_items[3], 'is_ser', True)
        except Exception:
            pass

        self._apply_font()

        self.setAcceptedMouseButtons(
            Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
        )

    @staticmethod
    def _ensure_fonts_loaded():
        if not hasattr(CardItem, '_fonts_loaded'):
            CardItem._fonts_loaded = True
            from PyQt6.QtGui import QFontDatabase
            f1 = resource_path("GLSNECB.TTF")
            if os.path.exists(f1):
                QFontDatabase.addApplicationFont(f1)
            f2 = resource_path("Corpo___.ttf")
            if os.path.exists(f2):
                QFontDatabase.addApplicationFont(f2)

    def _appearance(self):
        """Zwraca AppearanceManager sceny (lub None, gdy niepodpiety)."""
        scene = self.scene()
        if scene is not None:
            return getattr(scene, 'appearance_manager', None)
        return None

    # --- identyfikatory i skroty danych (Faza 4.4) ---

    @property
    def column_id(self):
        """ID kolumny, w ktorej karta sie znajduje (z biezecego stanu)."""
        return self.current_column.id if self.current_column is not None else None

    @property
    def table_id(self):
        """ID tabeli, w ktorej karta sie znajduje (z biezecego stanu)."""
        col = self.current_column
        return col.parent_table.id if col is not None and col.parent_table is not None else None

    @property
    def detail(self):
        """Pole Detal/Nazwa (tekst karty)."""
        return self.text_items[1].toPlainText() if len(self.text_items) > 1 else ""

    @property
    def series(self):
        """Pole ser. (tekst karty)."""
        return self.text_items[3].toPlainText() if len(self.text_items) > 3 else ""

    @property
    def status(self):
        """Indeks statusu karty."""
        return self.status_index

    def _apply_font(self):
        """Stosuje aktualny font z cyklu do Cecha."""
        if len(self.text_items) > 2:
            fam = self.font_families[self.font_index]
            size = 74
            y_offset = 0
            if fam == "Corporate":
                size = 77
            if "Gill Sans" in fam:
                y_offset = -4
            f = QFont(fam, size)
            f.setBold(fam == "Huxley Titling")
            f.setItalic(False)
            if fam == "Huxley Titling":
                f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
            elif "Gill Sans" in fam:
                f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
            elif fam == "Corporate":
                f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.3)
            self.text_items[2].setFont(f)
            self.text_items[2].setPos(30, 16 + y_offset)

    def _create_svg_overlay_item(self, svg_path):
        """Wektorowa nakladka SVG dopasowana do rozmiaru karty (bez pikselacji)."""
        try:
            item = QGraphicsSvgItem(svg_path)
            br = item.boundingRect()
            if br.width() > 0 and br.height() > 0:
                sx = self.width / br.width()
                sy = self.height / br.height()
                item.setTransform(QTransform().scale(sx, sy))
            item.setParentItem(self)
            item.setPos(0, 0)
            item.setZValue(3000)  # nad tekstem karty (2500)
            return item
        except Exception:
            return None

    def _update_perm_overlay(self):
        """Tworzy/usuwana osobny item dla permanent overlay (nad tekstem kart)."""
        if self._perm_overlay_item:
            self._perm_overlay_item.setParentItem(None)
            if self.scene():
                self.scene().removeItem(self._perm_overlay_item)
            self._perm_overlay_item = None
        if not self.permanent_overlay_file:
            return
        base_name = os.path.splitext(self.permanent_overlay_file)[0]
        svg_path = resource_path(base_name + ".svg")
        self._perm_overlay_item = self._create_svg_overlay_item(svg_path)

    def sync_overlay_items(self):
        """Aktualizuje nakladki Priorytet/INFO (nad warstwa fontow).

        Tworzy/usuwana osobne itemy z zValue ponad tekstem (2500), wiec
        Opis.svg / Nadzor.svg / Poprawa.svg wyswietlaja sie NAD fontami.
        """
        key = (self.overlay_index, self.info_overlay_index)
        if key == self._overlay_above_fonts_key:
            return
        self._overlay_above_fonts_key = key
        self._set_overlay_above_fonts("_priority_overlay_item",
                                      self._overlay_file(self.overlay_index, self.overlays))
        self._set_overlay_above_fonts("_info_overlay_item",
                                      self._overlay_file(self.info_overlay_index, self.info_overlays))

    def _overlay_file(self, index, catalog):
        if 0 <= index < len(catalog):
            return catalog[index]
        return ""

    def _set_overlay_above_fonts(self, attr, filename):
        item = getattr(self, attr, None)
        if item is not None:
            item.setParentItem(None)
            if self.scene():
                try:
                    self.scene().removeItem(item)
                except Exception:
                    pass
            setattr(self, attr, None)
        if not filename:
            return
        svg_path = resource_path(os.path.splitext(filename)[0] + ".svg")
        setattr(self, attr, self._create_svg_overlay_item(svg_path))

    def _init_timeline(self):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")
        main_num = self.text_items[2].toPlainText() if len(self.text_items) > 2 else "?"
        ser_num = self.text_items[3].toPlainText() if len(self.text_items) > 3 else "?"
        szt_num = self.text_items[4].toPlainText() if len(self.text_items) > 4 else "?"
        self.history_text += (
            f"{date_str}_{time_str}             URUCHOMIONO: {main_num}, ser. {ser_num}, szt. {szt_num}\n"
        )

    def get_scale_factor(self):
        return self._scale_factor

    def set_scale_factor(self, value):
        self._scale_factor = value
        self.setScale(value)

    scaleFactor = pyqtProperty(float, fget=get_scale_factor, fset=set_scale_factor)

    def animate_scale_in(self, callback=None):
        self.scale_anim.setDuration(80)
        self._scale_factor = 0.0
        self.setScale(0.0)
        self.scale_anim.stop()
        self.scale_anim.setStartValue(0.0)
        self.scale_anim.setEndValue(1.0)
        try:
            self.scale_anim.finished.disconnect()
        except Exception:
            pass
        if callback:
            self.scale_anim.finished.connect(callback)
        self.scale_anim.start()

    def animate_scale_out(self, callback=None):
        self.scale_anim.setDuration(80)
        self.scale_anim.stop()
        self.scale_anim.setStartValue(self._scale_factor)
        self.scale_anim.setEndValue(0.0)
        try:
            self.scale_anim.finished.disconnect()
        except Exception:
            pass
        if callback:
            self.scale_anim.finished.connect(callback)
        self.scale_anim.start()

    def animate_highlight(self, callback=None):
        self.scale_anim.setDuration(80)
        self.scale_anim.stop()
        self.scale_anim.setStartValue(1.0)
        self.scale_anim.setEndValue(1.1)
        try:
            self.scale_anim.finished.disconnect()
        except Exception:
            pass
        if callback:
            self.scale_anim.finished.connect(callback)
        self.scale_anim.start()

    def animate_unhighlight(self, callback=None):
        self.scale_anim.setDuration(80)
        self.scale_anim.stop()
        self.scale_anim.setStartValue(1.1)
        self.scale_anim.setEndValue(1.0)
        try:
            self.scale_anim.finished.disconnect()
        except Exception:
            pass
        if callback:
            self.scale_anim.finished.connect(callback)
        self.scale_anim.start()

    def highlight_search(self):
        if self._is_search_highlighted:
            return
        self._original_color_index = self.color_index
        self._is_search_highlighted = True
        self.color_index = -1
        self.update()

    def clear_search_highlight(self):
        if not self._is_search_highlighted:
            return
        self.color_index = self._original_color_index
        self._is_search_highlighted = False
        self.update()

    def to_dict(self, encrypt_timeline=False, password_manager=None):
        """Serializuje karte do slownika. Opcjonalnie szyfruje Timeline."""
        history = self.history_text
        encrypted = False
        
        if encrypt_timeline and password_manager and history:
            encrypted_history = password_manager.encrypt_timeline(history)
            if encrypted_history != history:
                history = encrypted_history
                encrypted = True
        
        return {
            "id": self.id,
            "texts": [t.toPlainText() for t in self.text_items],
            "color_index": self.color_index,
            "font_index": self.font_index,
            "status_index": self.status_index,
            "overlay_index": self.overlay_index,
            "klient_overlay_index": self.klient_overlay_index,
            "info_overlay_index": self.info_overlay_index,
            "note_text": self.note_text,
            "history_text": history,
            "_timeline_encrypted": encrypted,
            "braki": self.braki,
            "uruchom": self.uruchom,
            "klient": self.klient,
            "uwagi": self.uwagi,
        }

    @staticmethod
    def from_dict(data, password_manager=None):
        """Deserializuje karte ze slownika. Opcjonalnie deszyfruje Timeline."""
        card = CardItem()
        card.id = data.get("id") or new_id("card-")
        texts = data.get("texts", [])
        for i, text in enumerate(texts):
            if i < len(card.text_items):
                card.text_items[i].setPlainText(text)
        card.color_index = data.get("color_index", 0)
        card.font_index = data.get("font_index", 0)
        card.status_index = data.get("status_index", 0)
        card.overlay_index = data.get("overlay_index", 0)
        card.klient_overlay_index = data.get("klient_overlay_index", 0)
        card.info_overlay_index = data.get("info_overlay_index", 0)
        card.note_text = data.get("note_text", "")
        card.braki = data.get("braki", "")
        card.uruchom = data.get("uruchom", "")
        card.klient = data.get("klient", "")
        card.uwagi = data.get("uwagi", "")
        
        history = data.get("history_text", "")
        if data.get("_timeline_encrypted", False) and password_manager:
            history = password_manager.decrypt_timeline(history)
        card.history_text = history
        
        card._last_status_index = card.status_index
        card._last_overlay_index = card.overlay_index
        card._apply_font()
        card.sync_overlay_items()
        return card

    def add_position_history(self, title_text_left, header_line1, header_line2, header_line2a, header_line3, header_line4, title_text_right1, position):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")

        table_changed = (title_text_left != self._last_table_title)
        column_changed = (header_line1 != self._last_column_header)
        position_changed = (position != self._last_position)

        if not position_changed and not table_changed and not column_changed:
            return

        if title_text_right1.strip() == "#":
            self.history_text += f"{date_str}_{time_str}_______________________{title_text_left}\n"
            self._last_table_title = title_text_left
            self._last_column_header = header_line1
            self._last_position = position
            return

        if header_line4.strip() == "#":
            self.history_text += f"{date_str}_{time_str}_______________________{title_text_left}, {header_line1}\n"
            self._last_table_title = title_text_left
            self._last_column_header = header_line1
            self._last_position = position
            return

        if position == 1:
            self.history_text += f"{date_str}_{time_str}______ __***  W produkcji  ***_{title_text_left},_{header_line1}.\n"
            self.history_text += f"_________________________________________ {header_line2a},_{header_line3},_{header_line2}\n"
        else:
            self.history_text += f"{date_str}_{time_str}_____________**  Czeka w poz. {position} **_{title_text_left},_{header_line1}.\n"

        self._last_table_title = title_text_left
        self._last_column_header = header_line1
        self._last_position = position

    def add_overlay_change_history(self, prev_overlay_idx, curr_overlay_idx):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")

        if curr_overlay_idx == 0:
            self.history_text += f"{date_str}_{time_str}_____________________PILNE__(Ustawiono).\n"
        elif prev_overlay_idx == 0 and curr_overlay_idx != 0:
            self.history_text += f"{date_str}_{time_str}_____________________PILNE__( wycofano).\n"

    def add_status_icon_change_history(self, prev_status_idx, curr_status_idx):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")

        if curr_status_idx == 2:
            self.history_text += f"{date_str}_{time_str}__________________Wstrzymano_(Status).\n"
        elif prev_status_idx == 2 and curr_status_idx != 2:
            self.history_text += f"{date_str}_{time_str}__________________Wznowiono_(Status).\n"

    def add_note_history(self, note_text):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")
        self.history_text += f"{date_str}_{time_str}______Notes:_{note_text}\n"

    def _get_pos(self):
        return super().pos()

    def _set_pos(self, p):
        super().setPos(p)

    pos = pyqtProperty(QPointF, fget=_get_pos, fset=_set_pos)

    def _load_pixmap(self, filename):
        """Laduje ikone - SVG lub PNG/ICO w wysokiej jakosci."""
        return load_icon(filename)

    def boundingRect(self):
        # BEZ dodatkowego miejsca na cien
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # BEZ CIENIA

        rect = QRectF(0, 0, self.width, self.height)
        if self._is_search_highlighted:
            painter.setBrush(QColor("#D91A1A"))
        else:
            painter.setBrush(self.colors[self.color_index])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, CARD_RADIUS, CARD_RADIUS)

        # Klient overlay
        if 0 <= self.klient_overlay_index < len(self.klient_overlays):
            ov_file = self.klient_overlays[self.klient_overlay_index]
            _draw_icon_on_painter(painter, ov_file, QRectF(0, 0, 18, self.height))

        # Nakladki Priorytet (Opis.svg) i INFO (Nadzor/Poprawa) sa rysowane
        # jako osobne itemy NAD warstwa fontow (patrz sync_overlay_items).

        # Ikona INFO - tylko gdy jest wpis w notatniku
        if self.note_text.strip():
            _draw_icon_on_painter(painter, self.info_icon_full_file, self.info_rect)

        # Ikona statusu
        if self.status_index < len(self.status_icon_files):
            status_file = self.status_icon_files[self.status_index]
            _draw_icon_on_painter(painter, status_file, self.status_rect)

    def mousePressEvent(self, event):
        if self._is_search_highlighted and event.button() == Qt.MouseButton.LeftButton:
            self.clear_search_highlight()
            scene = self.scene()
            if scene:
                sm = getattr(scene, "search_manager", None)
                if sm is not None:
                    sm.unhighlight_card()
                else:
                    scene._highlighted_card = None

        if event.button() == Qt.MouseButton.RightButton:
            event.accept()
            return

        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return

        # Ctrl+klik LPM = edytor karty (Faza 7.1).
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            from modules.managers.form_manager import FormManager
            FormManager.open_edit_dialog_static(self)
            event.accept()
            return

        if self.pos_anim.state() == QAbstractAnimation.State.Running:
            event.ignore()
            return

        self.potential_drag = True
        self._drag_start_scene_pos = event.scenePos()

        self._original_parent = self.parentItem()
        self._original_local_pos = self.pos
        self._original_column = self.current_column
        self._original_index = (
            self._original_column.cards.index(self)
            if self._original_column and self in self._original_column.cards
            else -1
        )
        event.accept()

    def mouseDoubleClickEvent(self, event):
        """Dwuklik LPM = podglad karty (Hover, Faza 7.1)."""
        if event.button() == Qt.MouseButton.LeftButton:
            from modules.managers.form_manager import FormManager
            FormManager.open_preview_dialog_static(self)
            event.accept()
            return

        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        if not self.potential_drag and not self.is_dragging:
            return

        dist = (event.scenePos() - self._drag_start_scene_pos).manhattanLength()
        if self.potential_drag and dist >= DRAG_START_DISTANCE:
            self.is_dragging = True
            self.potential_drag = False

            if self._original_column:
                self._original_column.remove_card(self)

            current_scene_pos = self.scenePos()
            self._drag_offset = event.scenePos() - current_scene_pos

            self.setParentItem(None)
            self.setPos(current_scene_pos)
            self.setZValue(2000)
            self.update()
            self.pos_anim.stop()

        if self.is_dragging:
            self.setPos(event.scenePos() - self._drag_offset)

            mouse_pos = event.scenePos()
            scene = self.scene()

            target_col = None
            for item in scene.items(mouse_pos):
                if isinstance(item, ColumnItem):
                    target_col = item
                    break
                if hasattr(item, "parentItem") and isinstance(item.parentItem(), ColumnItem):
                    target_col = item.parentItem()
                    break

            for item in scene.items():
                if isinstance(item, ColumnItem):
                    if item == target_col:
                        item.update_preview(mouse_pos)
                    else:
                        item.clear_preview()

        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        if self.potential_drag:
            self.potential_drag = False

        elif self.is_dragging:
            self.is_dragging = False
            self.update()

            scene = self.scene()
            center = self.scenePos() + QPointF(self.width / 2, self.height / 2)

            kanban_icon = scene.get_kanban_icon_at(center)
            if kanban_icon:
                self.animate_scale_out(lambda: scene.remove_card_completely(self))
                event.accept()
                return

            target_col = None
            for item in scene.items(center):
                if isinstance(item, ColumnItem):
                    target_col = item
                    break

            if target_col:
                target_col.add_card_at_preview(self)
            else:
                self._return_to_original()

            for item in scene.items():
                if isinstance(item, ColumnItem):
                    item.clear_preview()

            self.setZValue(1000)

        event.accept()

    def _return_to_original(self, immediate=False):
        if not self._original_column or self._original_index < 0:
            return

        col = self._original_column

        if self not in col.cards:
            insert_at = min(self._original_index, len(col.cards))
            col.cards.insert(insert_at, self)
        else:
            insert_at = col.cards.index(self)

        if immediate:
            if self.parentItem() != col:
                self.setParentItem(col)
            local_pos = col.mapFromScene(self.scenePos())
            self.setPos(local_pos)
            col.relayout_cards()
            self.update()
        else:
            self.pos_anim.setDuration(800)
            col._animate_card_to_position(self, insert_at)

    def animate_to(self, target_pos, callback=None):
        self.pos_anim.stop()
        self.pos_anim.setEndValue(target_pos)
        try:
            self.pos_anim.finished.disconnect()
        except Exception:
            pass
        if callback:
            self.pos_anim.finished.connect(callback)
        self.pos_anim.start()

    def contextMenuEvent(self, event):
        # Po prawym dwukliku (wejscie w tryb edycji) pusczenie przycisku
        # generuje menu kontekstowe - polknij je, by nie otwierac menu Tabeli/Sceny.
        if self._suppress_next_context_menu:
            self._suppress_next_context_menu = False
            event.accept()
            return
        event.ignore()
