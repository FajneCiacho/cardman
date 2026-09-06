"""
column_item.py - Kolumna Kanban (Faza 4, krok 4.2).

Przeniesione 1:1 z kanban_items.py: _card_label, ColumnItem.
Kolumna jest tylko geometria i zawartoscia (wygld przez appearance/icon_utils).
"""
from PyQt6.QtWidgets import QGraphicsObject, QGraphicsItem
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtProperty

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import (
    CARD_W, CARD_H, CARD_GAP, COLUMN_WIDTH, COLUMN_HEADER_HEIGHT,
    COLUMN_BODY_HEIGHT, COLOR_COLUMN_HEADER, CORNER_RADIUS,
    HEADER_OVERLAYS, BODY_OVERLAYS, INFO_ICON_SIZE, INFO_MARGIN,
)
from modules.core.text_items import LimitedWidthTextItem
from modules.core.icon_utils import create_icon_item
from modules.managers.card_history import init_timeline, add_position_history
from modules.utils import new_id


def _card_label(card):
    main = card.text_items[2].toPlainText().strip() if len(card.text_items) > 2 else ""
    ser = card.text_items[3].toPlainText().strip() if len(card.text_items) > 3 else ""
    if main or ser:
        return f"{main or '?'} / {ser or '?'}"
    return "Karta"


class ColumnItem(QGraphicsObject):
    """Kolumna w tabeli Kanban."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_table = parent
        # Identyfikator kolumny (Faza 4.4)
        self.id = new_id("col-")
        self.body_height = COLUMN_BODY_HEIGHT
        self._slide_offset = 0.0
        self.linked_to_right = False
        self.linked_from_left = False
        self.header_overlay_index = 0
        self.body_overlay_index = 0
        self.notes = ""
        # 'Opis' kolumny (col.opis) - pole informacyjne widoczne w hoverze,
        # osobne od notatnika kolumny (col.notes).
        self.opis = ""
        # Wybor pracownika (worker_1=1 / worker_2=2), RODO (TylkoNrewid)
        # i dane obu linii pracownika (worker_1 + worker_2) - trwale zapisywane.
        self.worker_sel = 1
        self.tylko_nr = False
        self.w1_imie = ""
        self.w1_nazwisko = ""
        self.w1_id = ""
        self.w1_spec = ""
        self.w2_imie = ""
        self.w2_nazwisko = ""
        self.w2_id = ""
        self.w2_spec = ""
        self._dimmed = False
        self._dim_intensity = 0

        self.cards = []
        self.preview_idx = -1

        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)
        self.setCacheMode(QGraphicsItem.CacheMode.ItemCoordinateCache)

        self.header_overlay = None
        self.update_header_overlay()

        self.body_overlay = None
        self.update_body_overlay()

        self.info_icon = None

        self.header_line1 = LimitedWidthTextItem(max_width=500, parent=self, default_text="")
        self.header_line1.setFont(QFont("Arial", 23, QFont.Weight.Bold))
        self.header_line1.setPos(30, 4)

        self.header_line2 = LimitedWidthTextItem(max_width=200, parent=self, default_text="")
        self.header_line2.setFont(QFont("Arial", 7, italic=True))
        self.header_line2.setPos(40,35)

        self.header_line2a = LimitedWidthTextItem(max_width=200, parent=self, default_text="")
        self.header_line2a.setFont(QFont("Arial", 7, italic=True))
        self.header_line2a.setPos(270,35)

        self.header_line3 = LimitedWidthTextItem(max_width=110, parent=self, default_text="")
        self.header_line3.setFont(QFont("Arial", 7, italic=True))
        self.header_line3.setPos(395,35)

        # Znacznik "Ignoruj wpisy z pola kolumny do Time Line" ('#' / '*') - bez pola tekstowego
        # na COLUMN_HEADER; edytowany wyłącznie w formularzu edycji tabeli.
        self.header_line4 = "*"
        self.update_info_icon()

    def max_cards(self):
        return int(self.body_height // (CARD_H + CARD_GAP))

    def update_info_icon(self):
        # INFO.svg - tylko wyświetlanie ikony (bez akcji), INFO1.svg usunięty.
        # Ikona pozostaje w tej samej pozycji, widoczna gdy są notatki.
        if not self.notes.strip():
            if self.info_icon is not None:
                self.info_icon.setVisible(False)
            return
        if self.info_icon is not None:
            self.info_icon.setVisible(True)
            return
        self.info_icon = create_icon_item(self, "INFO.svg", INFO_ICON_SIZE, INFO_ICON_SIZE)
        self.info_icon.setPos(INFO_MARGIN + 402, INFO_MARGIN)
        self.info_icon.setZValue(1500)
        self.info_icon.setVisible(True)

    # --- wyglad przez AppearanceManager (Faza 4.5) lub fallback ---

    def _appearance(self):
        scene = self.scene()
        if scene is not None:
            return getattr(scene, 'appearance_manager', None)
        return None

    def _header_overlay_file(self, index):
        ap = self._appearance()
        if ap is not None:
            return ap.header_overlay_file(index)
        if not HEADER_OVERLAYS:
            return ""
        return HEADER_OVERLAYS[index % len(HEADER_OVERLAYS)]

    def _header_overlays_count(self):
        ap = self._appearance()
        return len(ap.header_overlays) if ap is not None else len(HEADER_OVERLAYS)

    def _body_overlay_file(self, index):
        ap = self._appearance()
        if ap is not None:
            return ap.body_overlay_file(index)
        if not BODY_OVERLAYS:
            return ""
        return BODY_OVERLAYS[index % len(BODY_OVERLAYS)]

    def _body_overlays_count(self):
        ap = self._appearance()
        return len(ap.body_overlays) if ap is not None else len(BODY_OVERLAYS)

    def update_header_overlay(self):
        filename = self._header_overlay_file(self.header_overlay_index)
        # Usuń poprzedni overlay jeśli istnieje
        try:
            if self.header_overlay is not None:
                try:
                    if self.header_overlay.scene():
                        self.scene().removeItem(self.header_overlay)
                except Exception:
                    pass
                self.header_overlay = None
        except Exception:
            pass

        if filename:
            # Preferuj SVG/vektor przez create_icon_item
            item = create_icon_item(self, filename, COLUMN_WIDTH, COLUMN_HEADER_HEIGHT)
            if item is not None:
                item.setPos(0, 0)
                item.setZValue(10)
                try:
                    item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                    item.setAcceptHoverEvents(False)
                    item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
                except Exception:
                    pass
                self.header_overlay = item
            else:
                self.header_overlay = None
        else:
            self.header_overlay = None
        self.setCacheMode(QGraphicsItem.CacheMode.NoCache)
        self.setCacheMode(QGraphicsItem.CacheMode.ItemCoordinateCache)

    def update_body_overlay(self):
        filename = self._body_overlay_file(self.body_overlay_index)
        # Usuń poprzedni overlay jeśli istnieje
        try:
            if self.body_overlay is not None:
                try:
                    if self.body_overlay.scene():
                        self.scene().removeItem(self.body_overlay)
                except Exception:
                    pass
                self.body_overlay = None
        except Exception:
            pass

        if filename:
            item = create_icon_item(self, filename, COLUMN_WIDTH, self.body_height)
            if item is not None:
                item.setPos(0, COLUMN_HEADER_HEIGHT)
                item.setZValue(1500)
                try:
                    item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                    item.setAcceptHoverEvents(False)
                    item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
                except Exception:
                    pass
                self.body_overlay = item
            else:
                self.body_overlay = None
        else:
            self.body_overlay = None
        self.setCacheMode(QGraphicsItem.CacheMode.NoCache)
        self.setCacheMode(QGraphicsItem.CacheMode.ItemCoordinateCache)

    def boundingRect(self):
        return QRectF(0, 0, COLUMN_WIDTH, COLUMN_HEADER_HEIGHT + self.body_height)

    def paint(self, painter, option, widget=None):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(COLOR_COLUMN_HEADER))
        painter.drawRect(QRectF(0, 0, COLUMN_WIDTH, COLUMN_HEADER_HEIGHT))

        y1 = COLUMN_HEADER_HEIGHT
        y2 = COLUMN_HEADER_HEIGHT + self.body_height
        R = CORNER_RADIUS
        path = QPainterPath()
        path.moveTo(0, y1)
        path.lineTo(0, y2 - R)
        path.quadTo(0, y2, R, y2)
        path.lineTo(COLUMN_WIDTH - R, y2)
        path.quadTo(COLUMN_WIDTH, y2, COLUMN_WIDTH, y2 - R)
        path.lineTo(COLUMN_WIDTH, y1)
        path.closeSubpath()
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawPath(path)

        # Przyciemnienie body kolumny (razem z przyciemnianiem sceny)
        if self._dimmed:
            alpha = int(60 * max(0, min(100, self._dim_intensity)) / 100.0)
            painter.setBrush(QColor(0, 0, 0, alpha))
            painter.drawPath(path)

        pen_norm = QPen(QColor("#002D57"), 4)  # (#43170E)
        pen_white = QPen(QColor("#FFFFFF"), 6)  # (#FFFFFF)

        # Make pens cosmetic so their device-pixel width stays visible when zooming
        try:
            pen_norm.setCosmetic(True)
            pen_white.setCosmetic(True)
        except Exception:
            pass

        # Draw crisp separator lines without antialiasing (keeps visibility when zoomed out)
        painter.save()
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        except Exception:
            pass

        painter.setPen(pen_norm)
        painter.drawLine(QPointF(0, -1), QPointF(COLUMN_WIDTH, -1))
        painter.drawLine(QPointF(0, y2), QPointF(COLUMN_WIDTH, y2))
        painter.setPen(pen_white if self.linked_from_left else pen_norm)
        painter.drawLine(QPointF(0, y1), QPointF(0, y2 - 5))
        painter.setPen(pen_white if self.linked_to_right else pen_norm)
        painter.drawLine(QPointF(COLUMN_WIDTH, y1), QPointF(COLUMN_WIDTH, y2 - 5))

        painter.restore()

    def mouseDoubleClickEvent(self, event):
        # Dwuklik LPM na belce kolumny = podglad (Hover).
        if event.button() == Qt.MouseButton.LeftButton:
            if event.pos().y() < COLUMN_HEADER_HEIGHT:
                from modules.managers.form_manager import FormManager
                FormManager.open_preview_dialog_static(self)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Ctrl+klik LPM na belce kolumny = edytor kolumny.
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                if event.pos().y() < COLUMN_HEADER_HEIGHT:
                    from modules.managers.form_manager import FormManager
                    FormManager.open_edit_dialog_static(self)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def set_dim(self, dimmed, intensity=0):
        """Ustawia przyciemnienie body kolumny (wraz ze scena)."""
        self._dimmed = bool(dimmed)
        self._dim_intensity = int(intensity)

    def set_body_height(self, h):
        self.prepareGeometryChange()
        self.body_height = h
        self.relayout_cards()
        self.update()

    def get_slide_offset(self):
        return self._slide_offset

    def set_slide_offset(self, value):
        self._slide_offset = value
        table = self.parentItem()
        if table is not None and hasattr(table, "relayout"):
            table.relayout()
        self.update()

    slideOffset = pyqtProperty(float, get_slide_offset, set_slide_offset)

    def update_preview(self, scene_point):
        local_point = self.mapFromScene(scene_point)
        local_y = local_point.y() - COLUMN_HEADER_HEIGHT
        if local_y < 0:
            idx = 0
        else:
            idx = int(local_y // (CARD_H + CARD_GAP))
        idx = max(0, min(idx, len(self.cards)))

        if idx != self.preview_idx:
            self.preview_idx = idx
            self.relayout_cards()

        self.update()

    def clear_preview(self):
        if self.preview_idx != -1:
            self.preview_idx = -1
            self.relayout_cards()
            self.update()

    def add_card_at_preview(self, card):
        old_col = card.current_column
        old_table = old_col.parent_table if old_col else None
        new_table = self.parent_table
        card_label_str = _card_label(card)

        if card.current_column:
            card.current_column.remove_card(card)

        insert_at = self.preview_idx if self.preview_idx != -1 else len(self.cards)
        self.cards.insert(insert_at, card)
        card.current_column = self
        self.preview_idx = -1

        self._animate_card_to_position(card, insert_at)
        scene = self.scene()
        if scene is not None:
            if getattr(card, "_is_new_card", False):
                main_num = card.text_items[2].toPlainText() if len(card.text_items) > 2 else "?"
                ser_num = card.text_items[3].toPlainText() if len(card.text_items) > 3 else "?"
                szt_num = card.text_items[4].toPlainText() if len(card.text_items) > 4 else "?"
                scene.emit("card.created", card=card,
                           description=f"Nowa Karta: ({main_num})  ser. ({ser_num})  szt. ({szt_num})")
                card._is_new_card = False
                if hasattr(scene, "_update_card_counter"):
                    scene._update_card_counter()
            elif old_col is not None:
                t1 = old_table.title_text_left.toPlainText() if old_table and hasattr(old_table, "title_text_left") else "?"
                t2 = new_table.title_text_left.toPlainText() if new_table and hasattr(new_table, "title_text_left") else "?"
                k1 = old_col.header_line1.toPlainText() if hasattr(old_col, "header_line1") else "?"
                k2 = self.header_line1.toPlainText() if hasattr(self, "header_line1") else "?"
                if old_table != new_table:
                    scene.emit("card.moved", card=card, old_column=old_col, new_column=self,
                               description=f"Karta {card_label_str} zmieniła tabelę: [{t1}] {k1} → [{t2}] {k2}")
                else:
                    scene.emit("card.moved", card=card, old_column=old_col, new_column=self,
                               description=f"Karta {card_label_str} zmieniła kolumnę: [{t1}] {k1} → {k2}")

        if not card.history_text:
            init_timeline(card)

        table = self.parent_table
        if table:
            title_text_left = table.title_text_left.toPlainText()
            title_text_right1 = table.title_text_right1
            header_line1 = self.header_line1.toPlainText()
            header_line2 = self.header_line2.toPlainText()
            header_line2a = self.header_line2a.toPlainText()
            header_line3 = self.header_line3.toPlainText()
            header_line4 = self.header_line4
            position = insert_at + 1
            add_position_history(
                card,
                title_text_left, header_line1, header_line2, header_line2a,
                header_line3, header_line4, title_text_right1,
                position
            )

    def _animate_card_to_position(self, card, idx):
        # Custom gaps: first top margin = 40, gap between 1st and 2nd = 40, remaining gaps = CARD_GAP
        first_margin = 30
        gap_01 = 30
        other_gap = CARD_GAP
        base_y = COLUMN_HEADER_HEIGHT + first_margin
        if idx == 0:
            y = base_y
        elif idx == 1:
            y = base_y + CARD_H + gap_01
        else:
            y = base_y + CARD_H + gap_01 + (idx - 1) * (CARD_H + other_gap)
        local = QPointF((COLUMN_WIDTH - card.width) / 2, y)

        def done():
            card.setParentItem(self)
            card.setPos(local)
            self.relayout_cards()

        card.animate_to(self.mapToScene(local), done)

    def add_card(self, card):
        if card.current_column:
            card.current_column.remove_card(card)

        self.cards.append(card)
        card.current_column = self

        idx = len(self.cards) - 1
        # Custom gaps: first top margin = 40, gap between 1st and 2nd = 40, remaining gaps = CARD_GAP
        first_margin = 30
        gap_01 = 30
        other_gap = CARD_GAP
        base_y = COLUMN_HEADER_HEIGHT + first_margin
        if idx == 0:
            y = base_y
        elif idx == 1:
            y = base_y + CARD_H + gap_01
        else:
            y = base_y + CARD_H + gap_01 + (idx - 1) * (CARD_H + other_gap)
        local = QPointF((COLUMN_WIDTH - card.width) / 2, y)

        card.setParentItem(self)
        card.setPos(local)

    def remove_card(self, card):
        if card in self.cards:
            self.cards.remove(card)
            self.relayout_cards()
            self._update_cards_position_history()

    def _update_cards_position_history(self):
        table = self.parent_table
        if not table:
            return
        title_text_left = table.title_text_left.toPlainText()
        title_text_right1 = table.title_text_right1
        header_line1 = self.header_line1.toPlainText()
        header_line2 = self.header_line2.toPlainText()
        header_line2a = self.header_line2a.toPlainText()
        header_line3 = self.header_line3.toPlainText()
        header_line4 = self.header_line4

        for idx, card in enumerate(self.cards):
            position = idx + 1
            add_position_history(
                card,
                title_text_left, header_line1, header_line2, header_line2a,
                header_line3, header_line4, title_text_right1,
                position
            )

    def relayout_cards(self):
        # Custom gaps: first top margin = 40, gap between 1st and 2nd = 40, remaining gaps = CARD_GAP
        first_margin = 30
        gap_01 = 30
        other_gap = CARD_GAP

        for i, c in enumerate(self.cards):
            if c.is_dragging:
                continue
            if c.parentItem() == self:
                offset = 1 if (self.preview_idx != -1 and i >= self.preview_idx) else 0
                idx = i + offset
                # compute y based on idx
                base_y = COLUMN_HEADER_HEIGHT + first_margin
                if idx == 0:
                    y = base_y
                elif idx == 1:
                    y = base_y + CARD_H + gap_01
                else:
                    y = base_y + CARD_H + gap_01 + (idx - 1) * (CARD_H + other_gap)
                x = (COLUMN_WIDTH - CARD_W) / 2
                c.animate_to(QPointF(x, y))
