"""
table_item.py - Klasa TableItem (tabela Kanban)
POPRAWKI: ikona kanban plywajaca, bez cieni, SVG, edycja tekstu tylko na tekscie
"""

from PyQt6.QtWidgets import (
    QGraphicsObject, QGraphicsItem, QGraphicsSimpleTextItem,
)
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QPen, QFontMetrics, QPainterPath, QBrush,
    QPainterPathStroker,
)
from PyQt6.QtCore import (
    Qt, QRectF, QPropertyAnimation, QEasingCurve, pyqtProperty, QPointF,
)
from PyQt6.QtSvgWidgets import QGraphicsSvgItem


import sys
import os

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if relative_path.lower().endswith('.svg'):
        return os.path.join(base_path, "assets/svg", relative_path)
    return os.path.join(base_path, relative_path)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import *
from modules.core.kanban_items import ColumnItem, LimitedWidthTextItem
from modules.utils import new_id


class KanbanIconItem(QGraphicsSvgItem):
    """Ikona Kanban - plywajaca, sluzy do tworzenia nowych kart.

    Renderowana jako prawdziwa grafika wektorowa (QGraphicsSvgItem), dzieki
    czemu pozostaje ostra przy kazdym poziomie przyblizenia (bez pikselozy).
    """

    def __init__(self, svg_path, target_width=None, target_height=None, parent=None):
        super().__init__(svg_path, parent)
        if target_width is not None:
            br = self.boundingRect()
            if br.width() > 0:
                self.setScale(float(target_width) / float(br.width()))
        self.setAcceptedMouseButtons(Qt.MouseButton.RightButton | Qt.MouseButton.LeftButton)
        # Accept hover events so we can change cursor to pointing hand
        try:
            self.setAcceptHoverEvents(True)
        except Exception:
            pass
        # Plywajaca - mozna przeciagac
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self._pending_card = None
        self.setZValue(5000)

    def hoverEnterEvent(self, event):
        try:
            view = self.scene().views()[0] if self.scene() and self.scene().views() else None
            if view:
                view.setCursor(Qt.CursorShape.PointingHandCursor)
        except Exception:
            pass
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        try:
            view = self.scene().views()[0] if self.scene() and self.scene().views() else None
            if view:
                view.setCursor(Qt.CursorShape.ArrowCursor)
        except Exception:
            pass
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            scene = self.scene()
            if scene:
                scene.create_new_card_from_kanban(self)
            event.accept()
            return
        super().mousePressEvent(event)

    def get_scene_rect(self):
        return self.sceneBoundingRect()


class _UnlockIcon(QGraphicsSvgItem):
    """Ikona Odblokuj - widoczna w trybie edycji tabeli.

    Renderowana jako grafika wektorowa (QGraphicsSvgItem), dzieki czemu jest
    ostra przy kazdym przyblizeniu (bez pikselozy). Klikniecie ikony blokuje
    tabele w pozycji (konczy tryb edycji) i ukrywa ikone.
    """

    def __init__(self, table):
        svg_path = resource_path("Odblokoj.svg")
        super().__init__(svg_path, table)
        self.table = table
        br = self.boundingRect()
        if br.width() > 0:
            self.setScale(60.0 / br.width())
        self.setPos(-50, -30)
        self.setZValue(2000)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setVisible(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.table.exit_table_edit_mode()
            event.accept()
            return
        super().mousePressEvent(event)


class ConnectionLine(QGraphicsItem):
    """Linia laczaca dwie tabele z punktami kotwiczenia i waypointami."""
    
    ANCHOR_TOLERANCE = 20

    def __init__(self, table1, table2, source_anchor_id, target_anchor_id, waypoints=None):
        super().__init__()
        self.table1 = table1
        self.table2 = table2
        self.source_anchor_id = source_anchor_id
        self.target_anchor_id = target_anchor_id
        self.waypoints = waypoints or []
        self._points = []
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.update_line()

    @staticmethod
    def get_anchor_points(table):
        """Zwraca dict {anchor_id: QPointF} w wspolrzednych sceny."""
        rect = table.sceneBoundingRect()
        l, t, r, b = rect.left(), rect.top(), rect.right(), rect.bottom()
        w, h = rect.width(), rect.height()
        anchors = {
            "TL": QPointF(l, t), "TR": QPointF(r, t),
            "BL": QPointF(l, b), "BR": QPointF(r, b),
            "TM": QPointF(l + w/2, t), "BM": QPointF(l + w/2, b),
            "LM": QPointF(l, t + h/2), "RM": QPointF(r, t + h/2),
        }
        if table.columns:
            cw = w / len(table.columns)
            for i in range(len(table.columns) - 1):
                x = l + (i + 1) * cw
                anchors[f"TC{i}"] = QPointF(x, t)
                anchors[f"BC{i}"] = QPointF(x, b)
        return anchors

    @staticmethod
    def is_near_border(table, scene_pos, tolerance=ANCHOR_TOLERANCE):
        """Sprawdza czy pozycja jest w pasie okolo krawedzi tabeli."""
        rect = table.sceneBoundingRect()
        l, t, r, b = rect.left(), rect.top(), rect.right(), rect.bottom()
        x, y = scene_pos.x(), scene_pos.y()
        on_left = abs(x - l) <= tolerance and t - tolerance <= y <= b + tolerance
        on_right = abs(x - r) <= tolerance and t - tolerance <= y <= b + tolerance
        on_top = abs(y - t) <= tolerance and l - tolerance <= x <= r + tolerance
        on_bottom = abs(y - b) <= tolerance and l - tolerance <= x <= r + tolerance
        return on_left or on_right or on_top or on_bottom

    @staticmethod
    def get_nearest_anchor_id(table, scene_pos):
        """Zwraca (anchor_id, QPointF) najblizszego punktu kotwiczenia."""
        anchors = ConnectionLine.get_anchor_points(table)
        best_id = None
        best_pt = None
        best_dist = float("inf")
        for aid, pt in anchors.items():
            d = (pt.x() - scene_pos.x())**2 + (pt.y() - scene_pos.y())**2
            if d < best_dist:
                best_dist = d
                best_id = aid
                best_pt = pt
        return best_id, best_pt

    @staticmethod
    def get_anchor_id(table, scene_pos):
        """Sprawdza klikniecie w okolice krawedzi - zwraca (anchor_id, QPointF) lub None."""
        if not ConnectionLine.is_near_border(table, scene_pos):
            return None
        return ConnectionLine.get_nearest_anchor_id(table, scene_pos)

    def update_line(self):
        if not self.table1 or not self.table2:
            return
        anchors1 = self.get_anchor_points(self.table1)
        anchors2 = self.get_anchor_points(self.table2)
        p1 = anchors1.get(self.source_anchor_id)
        p2 = anchors2.get(self.target_anchor_id)
        if p1 is None or p2 is None:
            self._points = []
            self.hide()
            self.prepareGeometryChange()
            self.update()
            return
        self._points = [p1] + self.waypoints + [p2]
        self.prepareGeometryChange()
        self.show()
        self.update()

    @staticmethod
    def _route_45(p1, p2):
        """Trasuje odcinek pod katem 45 stopni (jeden zalom)."""
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 or dy == 0:
            return [p1, p2]
        adx, ady = abs(dx), abs(dy)
        d = min(adx, ady)
        sx = 1 if dx > 0 else -1
        sy = 1 if dy > 0 else -1
        if adx >= ady:
            mid = QPointF(x1 + (adx - ady) * sx, y1)
        else:
            mid = QPointF(x1, y1 + (ady - adx) * sy)
        return [p1, mid, p2]

    def _get_routed_points(self):
        if len(self._points) < 2:
            return list(self._points)
        result = []
        for i in range(len(self._points) - 1):
            seg = self._route_45(self._points[i], self._points[i+1])
            if i == 0:
                result.extend(seg)
            else:
                result.extend(seg[1:])
        return result

    def boundingRect(self):
        routed = self._get_routed_points()
        if not routed:
            return QRectF()
        min_x = min(p.x() for p in routed) - 5
        min_y = min(p.y() for p in routed) - 5
        max_x = max(p.x() for p in routed) + 5
        max_y = max(p.y() for p in routed) + 5
        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)

    def shape(self):
        """Obszar trafien tylko na linii laczacej (pas wokol linii)."""
        routed = self._get_routed_points()
        if len(routed) < 2:
            return super().shape()
        path = QPainterPath()
        path.moveTo(routed[0])
        for i in range(1, len(routed)):
            path.lineTo(routed[i])
        stroker = QPainterPathStroker()
        stroker.setWidth(6 + 8)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return stroker.createStroke(path)

    def paint(self, painter, option, widget=None):
        routed = self._get_routed_points()
        if len(routed) < 2:
            return
        pen = QPen(QColor("#004E96"), 6)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        path = QPainterPath()
        path.moveTo(routed[0])
        for i in range(1, len(routed)):
            path.lineTo(routed[i])
        painter.drawPath(path)

    def remove_from_tables(self):
        if self.scene():
            if self.table1 and self in self.table1.connected_lines:
                self.table1.connected_lines.remove(self)
            if self.table2 and self in self.table2.connected_lines:
                self.table2.connected_lines.remove(self)
            self.scene().removeItem(self)

    def mousePressEvent(self, event):
        # Linia laczaca jest usuwana tylko przez klikniecie na linię polaczenia.
        if event.button() == Qt.MouseButton.LeftButton:
            self.remove_from_tables()
            event.accept()


class TableItem(QGraphicsObject):
    """Tabela Kanban - zawiera kolumny z kartami. BEZ CIENI."""
    
    def __init__(self, is_base_table=False):
        super().__init__()
        self.is_base_table = is_base_table
        # Identyfikator tabeli (Faza 4.4)
        self.id = new_id("table-")
        self._editing = False
        self.columns = []
        self.body_height = COLUMN_BODY_HEIGHT
        self.extra_rows = 0
        self.connected_lines = []
        self.title_color_index = 0
        self.icon_item = None

        # Ikona Odblokuj (widoczna podczas edycji; klikniecie blokuje tabele)
        self._unlock_icon = _UnlockIcon(self)

        self.setCacheMode(QGraphicsItem.CacheMode.ItemCoordinateCache)

        for _ in range(BASE_COLUMNS):
            self.add_column(False)

        self.title_text_left = LimitedWidthTextItem(max_width=1000, parent=self, default_text="")
        self.title_text_left.setFont(QFont("Arial", 32, QFont.Weight.Bold))
        fm = QFontMetrics(self.title_text_left.font())
        title_height = fm.height()
        title_y = (TABLE_TITLE_HEIGHT - title_height) / 2
        self.title_text_left.setPos(60, title_y + 1)
        self.title_text_left._restrict_to_x = True

        self.title_text_right = LimitedWidthTextItem(max_width=800, parent=self, default_text="")
        self.title_text_right.setFont(QFont("Tahoma", 12, QFont.Weight.Bold))
        self.title_text_right.setPos(550, title_y+6)
        self.title_text_right._restrict_to_x = True

        # title_text_right1 ("#") - bez pola tekstowego na TABLE_TITLE; wartosc
        # edytowana w formularzu edycji tabeli (Ignoruj wpisy z kolumny do Time Line).
        self.title_text_right1 = "*"

        self._title_texts = [self.title_text_left, self.title_text_right]

        # Licznik kart (przeniesiony z ikony KARTY) - tylko na tabeli bazowej,
        # w prawym rogu paska TABLE_TITLE, zakotwiczony do prawej krawedzi.
        self.card_counter = None
        if self.is_base_table:
            self.card_counter = QGraphicsSimpleTextItem("0", self)
            self.card_counter.setFont(QFont("Arial", 24, QFont.Weight.Bold))
            self.card_counter.setBrush(QBrush(QColor("white")))
            self.card_counter.setZValue(1600)

        self._add_kanban_elements()
        self.relayout()
        if self.is_base_table:
            self.update_card_counter()

    COUNTER_RIGHT_MARGIN = 10

    # --- wyglad przez AppearanceManager (Faza 4.5) lub fallback ---

    def _appearance(self):
        scene = self.scene()
        if scene is not None:
            return getattr(scene, 'appearance_manager', None)
        return None

    def _title_color(self, index):
        ap = self._appearance()
        if ap is not None:
            return ap.title_color(index)
        if not TITLE_COLORS:
            return "#034787"
        return TITLE_COLORS[index % len(TITLE_COLORS)]

    def _title_colors_count(self):
        ap = self._appearance()
        return len(ap.title_colors) if ap is not None else len(TITLE_COLORS)

    def _position_card_counter(self):
        """Ustawia licznik przy prawej krawedzi paska TABLE_TITLE, wysrodkowany w pionie."""
        if not self.card_counter:
            return
        right_x = len(self.columns) * COLUMN_WIDTH
        br = self.card_counter.boundingRect()
        x = right_x - self.COUNTER_RIGHT_MARGIN - br.width()
        y = (TABLE_TITLE_HEIGHT - br.height()) / 2
        self.card_counter.setPos(x, y)

    def update_card_counter(self):
        """Liczy WSZYSTKIE karty na scenie (niezaleznie od statusu) i aktualizuje licznik."""
        if not self.card_counter:
            return

        scene = self.scene()
        count = sum(
            len(getattr(col, 'cards', []))
            for t in getattr(scene, 'tables', [])
            for col in getattr(t, 'columns', [])
        )

        self.card_counter.setText(str(count))
        self._position_card_counter()

    def _add_kanban_elements(self):
        # kanban_text - Główna nazwa (edytowana w formularzu tabeli).
        # Dane wspólne dla WSZYSTKICH tabel; duży pływający napis widoczny tylko
        # na tabeli bazowej (na pozostałych dane są ukryte, ale edytowalne).
        self.kanban_text = LimitedWidthTextItem(
            max_width=1200, parent=self,
            default_text="Wydział PM 3" if self.is_base_table else ""
        )
        font = QFont("BritannicTBol", 50, QFont.Weight.Bold, italic=True)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        self.kanban_text.setFont(font)
        self.kanban_text.setDefaultTextColor(QColor("#004C94"))
        self.kanban_text.setPos(40, -85)
        self.kanban_text.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.kanban_text._restrict_to_x = True
        self.kanban_text._margin_x = 20
        # Ctrl + klik LPM na napisie Glownej nazwy otwiera edytor nazwy.
        self.kanban_text.on_ctrl_click = self.open_name_editor
        # BEZ CIENIA
        if not self.is_base_table:
            self.kanban_text.setVisible(False)

    def open_name_editor(self):
        """Otwiera formularz Edytor_Głównej_Nazwy (edycja kanban_text)."""
        from modules.ui.forms_table import TableNameDialog
        TableNameDialog(self).exec()

    def boundingRect(self):
        w = len(self.columns) * COLUMN_WIDTH
        h = TABLE_TITLE_HEIGHT + COLUMN_HEADER_HEIGHT + self.body_height
        return QRectF(-12, -2, w + 14, h + 4)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = len(self.columns) * COLUMN_WIDTH
        h = TABLE_TITLE_HEIGHT + COLUMN_HEADER_HEIGHT + self.body_height
        table_rect = QRectF(0, 0, w, h)

        # BEZ CIENIA

        current_title_color = QColor(self._title_color(self.title_color_index))
        title_rect = QRectF(0, 0, w, TABLE_TITLE_HEIGHT)
        path = QPainterPath()
        path.moveTo(0, TABLE_TITLE_HEIGHT)
        path.lineTo(0, CORNER_RADIUS)
        path.quadTo(0, 0, CORNER_RADIUS, 0)
        path.lineTo(title_rect.width() - CORNER_RADIUS, 0)
        path.quadTo(title_rect.width(), 0, title_rect.width(), CORNER_RADIUS)
        path.lineTo(title_rect.width(), TABLE_TITLE_HEIGHT)
        path.closeSubpath()
        painter.fillPath(path, current_title_color)

        # BEZ CIENIA

        # Ramka standardowa
        pen = QPen(QColor(COLOR_TABLE_BORDER), 5)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(table_rect, CORNER_RADIUS, CORNER_RADIUS)

    def mouseDoubleClickEvent(self, event):
        # Dwuklik LPM na pasku tytulu = podglad (Hover) tabeli.
        if event.button() == Qt.MouseButton.LeftButton:
            if event.pos().y() <= TABLE_TITLE_HEIGHT:
                from modules.managers.form_manager import FormManager
                FormManager.open_preview_dialog_static(self)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            if not self._editing:
                super().mousePressEvent(event)
                return
        
        if event.button() == Qt.MouseButton.LeftButton:
            # Ctrl+klik LPM na pasku tytulu = edytor tabeli.
            if (event.modifiers() & Qt.KeyboardModifier.ControlModifier
                    and event.pos().y() <= TABLE_TITLE_HEIGHT):
                from modules.managers.form_manager import FormManager
                FormManager.open_edit_dialog_static(self)
                event.accept()
                return

            scene = self.scene()
            for col in self.columns:
                for card in list(col.cards):
                    if hasattr(card, "pos_anim"):
                        card.pos_anim.stop()
                    if card.parentItem() is not col:
                        scene_pos = card.scenePos()
                        card.setParentItem(col)
                        card.setPos(col.mapFromScene(scene_pos))
                    card.is_dragging = False

            if self._editing and event.pos().y() <= TABLE_TITLE_HEIGHT:
                self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsMovable, True)

        super().mousePressEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.update_connected_lines()
        return super().itemChange(change, value)

    def update_connected_lines(self):
        for line in self.connected_lines:
            line.update_line()

    def enter_table_edit_mode(self):
        """Wlacza tryb edycji tabeli: pokazuje ikone Odblokuj."""
        if self._editing:
            return
        self._editing = True
        self._unlock_icon.setVisible(True)
        # Odblokuj teksty tytulowe
        for txt in self._title_texts:
            txt.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.update()
        scene = self.scene()
        if scene and getattr(scene, 'edit_manager', None) is not None:
            scene.edit_manager.set_editing_table(scene, self)

    def exit_table_edit_mode(self):
        """Wylacza tryb edycji tabeli."""
        if not self._editing:
            return
        self._editing = False
        self._unlock_icon.setVisible(False)
        # Zablokuj teksty tytulowe i cala tabele
        for txt in self._title_texts:
            txt.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsMovable, False)
        scene = self.scene()
        if scene and getattr(scene, 'edit_manager', None) is not None:
            scene.edit_manager.table_exited(self)
        self.update()

    def add_column(self, animated=True):
        col = ColumnItem(self)
        col.set_body_height(self.body_height)
        self.columns.append(col)
        self.relayout()
        self.update_connected_lines()
        self.update()

    def remove_column(self):
        if len(self.columns) <= BASE_COLUMNS:
            return
        col = self.columns[-1]
        if col.scene():
            col.scene().removeItem(col)
        if col in self.columns:
            self.columns.remove(col)
        self.relayout()
        self.update_connected_lines()
        self.update()
        if self.scene():
            self.scene().update()

    def relayout(self):
        for i, col in enumerate(self.columns):
            off = getattr(col, "_slide_offset", 0)
            col.setPos(i * COLUMN_WIDTH + off, TABLE_TITLE_HEIGHT)

        # Zakotwicz licznik kart do prawej krawedzi (przesuwa sie z kolumnami)
        if getattr(self, "card_counter", None):
            self._position_card_counter()

        # NIE USTAWIAJ POZYCJI IKONY - jest plywajaca i niezalezna

    def add_body_row(self):
        self.extra_rows += 1
        self.animate_body(self.body_height + BODY_STEP)

    def remove_body_row(self):
        if self.extra_rows == 0:
            return
        self.extra_rows -= 1
        self.animate_body(self.body_height - BODY_STEP)

    def animate_body(self, target):
        anim = QPropertyAnimation(self, b"bodyHeight")
        anim.setStartValue(self.body_height)
        anim.setEndValue(target)
        anim.setDuration(300)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        anim.finished.connect(self.update_connected_lines)
        self._anim = anim

    def getBody(self):
        return self.body_height

    def setBody(self, h):
        self.prepareGeometryChange()
        self.body_height = h
        for c in self.columns:
            c.set_body_height(h)
        self.update_connected_lines()
        self.update()

    bodyHeight = pyqtProperty(float, getBody, setBody)

    def link_column(self, column):
        idx = self.columns.index(column)
        if idx >= len(self.columns) - 1:
            return
        column.linked_to_right = True
        right = self.columns[idx + 1]
        right.linked_from_left = True
        column.update()
        right.update()

    def unlink_column(self, column):
        idx = self.columns.index(column)
        if idx >= len(self.columns) - 1:
            return
        column.linked_to_right = False
        right = self.columns[idx + 1]
        right.linked_from_left = False
        column.update()
        right.update()
