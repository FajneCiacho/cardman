"""
kanban_scene.py - Glowna scena Kanban
POPRAWKI: autozapis ignoruje kanban_text, wczytywanie plikow, menu bez folder/zamknij, raport
"""

import os
import re
from datetime import datetime

from PyQt6.QtWidgets import (
    QGraphicsScene, QGraphicsTextItem, QGraphicsRectItem,
    QGraphicsPixmapItem, QGraphicsItem, QGraphicsPathItem,
    QMenu, QInputDialog, QDialog, QMessageBox,
    QApplication, QGraphicsView
)
from PyQt6.QtGui import QAction
from PyQt6.QtGui import (
    QFont, QPixmap, QPainter, QColor, QPen, QBrush, QTransform, QPainterPath,
    QPainterPathStroker
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import *
from modules.core.kanban_items import CardItem, ColumnItem
from modules.core.table_item import TableItem, ConnectionLine, KanbanIconItem, resource_path
from modules.utils import new_id


class ZoneRect(QGraphicsRectItem):
    """Prostokat strefy.

    Strefa jest usuwana tylko przez klikniecie na linie obrysu (shape() ogranicza
    obszar trafien do pasa wokol linii, wiec klikniecie wewnatrz strefy jej nie usuwa).
    """
    
    def __init__(self, rect):
        super().__init__(rect)
        pen = QPen(QColor(ZONE_COLOR), ZONE_WIDTH)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        self.setPen(pen)
        self.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        self.setZValue(-5000)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

    def shape(self):
        """Obszar trafien tylko na linii obrysu (nie wewnatrz strefy)."""
        path = QPainterPath()
        path.addRect(self.rect())
        stroker = QPainterPathStroker()
        stroker.setWidth(self.pen().widthF() + 4.0)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        return stroker.createStroke(path)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.scene():
                self.scene().removeItem(self)
            event.accept()
            return
        super().mousePressEvent(event)


class KanbanScene(QGraphicsScene):
    """Glowna scena Kanban - zarzadza tabelami, kartami i polaczeniami."""
    
    AUTOSAVE_SUFFIX = "_(Autozapis).json"
    
    def __init__(self, password_manager=None, config_folder=None):
        super().__init__()
        self.setSceneRect(-45000, -30000, 90000, 60000)
        self.tables = []
        self._connect_state = None  # None, "anchor", "waypoints"
        self._connect_source_table = None
        self._connect_source_anchor_id = None
        self._connect_waypoints = []
        self._connect_preview_item = None
        self._connect_prev_drag_mode = None

        # EventManager (Faza 1) - obiekty zglaszaja zdarzenia, nie wola managera
        self.event_manager = None
        self.timeline_manager = None
        self.view = None
        # StorageManager (Faza 2) - jedyne miejsce zapisu/odczytu plikow
        self.storage_manager = None
        # NotebookManager (Faza 3) - notatki (glowny notatnik + produkcyjne)
        self.notebook_manager = None
        # SearchManager (Faza 3) - wyszukiwarka i lista kart
        self.search_manager = None
        # ExportManager (Faza 3) - eksport danych (Excel)
        self.export_manager = None
        # LayoutManager (Faza 3) - uklad sceny (pozycje, blokada, ikona kanban)
        self.layout_manager = None
        # EditManager (Faza 3) - tryb edycji kart i tabel (wzajemnie wykluczajace)
        self.edit_manager = None
        # AppearanceManager (Faza 3) - katalog wygladu (kolory, nakladki, fonty)
        self.appearance_manager = None
        
        # Tworz tabele bazowa
        base_table = TableItem(is_base_table=True)
        self.tables.append(base_table)
        self.addItem(base_table)
        
        # Tworz plywajaca ikone Kanban (oddzielna od tabeli)
        self.kanban_icon = self._create_kanban_icon()
        # Pozycje ikony ustawia LayoutManager po utworzeniu managera (MainWindow)
        
        # Glowny notatnik + notatki produkcyjne (dane przez NotebookManager, Faza 3)
        self._main_notes = ""
        self._notes_data = []

        self.zone_draw_mode = False
        self.zone_start = None
        self.zone_preview = None
        self._pending_card = None
        self.zone_description_mode = False
        self.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.BspTreeIndex)
        self.setBspTreeDepth(8)
        self.is_scene_blocked = False
        self.block_icon = None
        self.info_icon = None
        self.scene_panel = None
        self.password_manager = password_manager
        self.config_folder = config_folder or os.path.dirname(os.path.abspath(__file__))
        # Timeline jest teraz zarzadzany przez TimelineManager (Faza 1)
        # Ustawienia aplikacji (Ustawienia -> ikona USTAWIENIA)
        self.save_folder = self.config_folder
        self.obraz_folder = ""
        self.dim_intensity = 0  # 0-100 (0 = wylaczone)
        self.dim_scene_with_columns = False  # wsteczna kompatybilnosc
        self._dim_overlay = None
        
    # --- NotebookManager (Faza 3): delegacja danych notatek ---

    @property
    def main_notes(self):
        if self.notebook_manager is not None:
            return self.notebook_manager.main_notes
        return self._main_notes

    @main_notes.setter
    def main_notes(self, value):
        if self.notebook_manager is not None:
            self.notebook_manager.main_notes = value
        else:
            self._main_notes = value

    @property
    def notes_data(self):
        if self.notebook_manager is not None:
            return self.notebook_manager.notes_data
        return self._notes_data

    @notes_data.setter
    def notes_data(self, value):
        if self.notebook_manager is not None:
            self.notebook_manager.notes_data = value
        else:
            self._notes_data = value

    def _create_kanban_icon(self):
        """Tworzy plywajaca ikone Kanban (renderowana wektorowo z SVG - bez pikselozy)."""
        svg_path = resource_path("kanban.svg")
        icon = KanbanIconItem(svg_path, target_width=50)

        # Ensure icon has no rotation applied (keep transform for scaling)
        try:
            icon.setRotation(0)
        except Exception:
            pass

        # Szerokosc +25%, wysokosc +20% (niesymetryczne skalowanie wektorowe).
        try:
            icon.setTransform(QTransform().scale(1.30, 1.20))
        except Exception:
            pass

        # Make movable and floating
        try:
            icon.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            icon.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        except Exception:
            pass
        icon.setZValue(5000)
        self.addItem(icon)
        return icon

    def _position_kanban_icon(self):
        """Pozycjonowanie ikony kanban (przez LayoutManager, Faza 3)."""
        if self.layout_manager is not None:
            self.layout_manager.position_kanban_icon(self)

    def get_kanban_icon_at(self, scene_pos):
        """Hit-test ikony kanban (przez LayoutManager, Faza 3)."""
        if self.layout_manager is not None:
            return self.layout_manager.get_kanban_icon_at(self, scene_pos)
        return None

    def create_new_card_from_kanban(self, kanban_icon):
        """Tworzy karte z ikony kanban (przez LayoutManager, Faza 3)."""
        if self.layout_manager is not None:
            return self.layout_manager.create_new_card_from_kanban(self, kanban_icon)
        return None

    def create_new_card(self):
        """Fabryka nowej karty (Faza 4.4): pojedyncze miejsce tworzenia kart."""
        card = CardItem()
        self.addItem(card)
        return card

    def _update_card_counter(self):
        """Odswieza licznik kart na tabeli bazowej (wywolywane tylko przy +1/-1 karty)."""
        if self.tables:
            base = self.tables[0]
            if getattr(base, 'card_counter', None):
                base.update_card_counter()

    def emit(self, event_type, **data):
        """Publikuje zdarzenie przez EventManager (Faza 1)."""
        if self.event_manager is not None:
            self.event_manager.emit(event_type, **data)

    def set_scene_blocked(self, blocked):
        self.is_scene_blocked = blocked
        if self.layout_manager is not None:
            self.layout_manager.set_scene_blocked(self, blocked)

    # --- przyciemnianie sceny razem z body kolumn (Ustawienia) ---

    def _dim_alpha_scene(self):
        return int(120 * max(0, min(100, self.dim_intensity)) / 100.0)

    def _ensure_dim_overlay(self, intensity=None):
        """Tworzy/aktualizuje nakladke przyciemnienia tla sceny (pod tabelami)."""
        alpha = self._dim_alpha_scene()
        if self._dim_overlay is not None:
            self._dim_overlay.setBrush(QBrush(QColor(0, 0, 0, alpha)))
            return
        rect = QGraphicsRectItem(self.sceneRect())
        rect.setBrush(QBrush(QColor(0, 0, 0, alpha)))
        rect.setPen(QPen(Qt.PenStyle.NoPen))
        rect.setZValue(-10000)
        rect.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        rect.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.addItem(rect)
        self._dim_overlay = rect

    def _remove_dim_overlay(self):
        """Usuwa nakladke przyciemnienia tla sceny."""
        if self._dim_overlay is not None:
            try:
                self.removeItem(self._dim_overlay)
            except Exception:
                pass
            self._dim_overlay = None

    def apply_dim_state(self):
        """Stosuje stan przyciemniania sceny + body kolumn (suwak 0-100)."""
        intensity = max(0, min(100, int(self.dim_intensity)))
        if intensity > 0:
            self._ensure_dim_overlay(intensity)
        else:
            self._remove_dim_overlay()
        dimmed = intensity > 0
        for table in self.tables:
            for col in getattr(table, "columns", []):
                col.set_dim(dimmed, intensity)
                col.update()
        self.update()

    def start_zone_description(self):
        self.zone_description_mode = True

    def remove_card_completely(self, card):
        main = card.text_items[2].toPlainText().strip() if len(card.text_items) > 2 else ""
        ser = card.text_items[3].toPlainText().strip() if len(card.text_items) > 3 else ""
        card_label = f"{main or '?'} / {ser or '?'}" if main or ser else "Karta"
        
        if card.current_column:
            card.current_column.remove_card(card)
        self.removeItem(card)
        if self._pending_card == card:
            self._pending_card = None
        self.emit("card.deleted", card=card, description=f"Karta {card_label} zostala usunieta.")
        self._update_card_counter()

    def add_new_table(self):
        base = self.tables[0]
        table = TableItem(is_base_table=False)
        # Nowe tabele BEZ ikony Kanban
        table.setPos(base.x(), base.y() + base.boundingRect().height() + 100)
        self.tables.append(table)
        self.addItem(table)

    def remove_table(self, table):
        if table.is_base_table:
            return
        if self._connect_state and self._connect_source_table == table:
            self._cancel_connecting()
        for line in list(table.connected_lines):
            line.remove_from_tables()
        table.prepareGeometryChange()
        table.setGraphicsEffect(None)
        if table in self.tables:
            self.tables.remove(table)
        self.removeItem(table)
        self.update()

    def start_connecting(self, table):
        self._connect_state = "anchor"
        self._connect_source_table = table
        self._connect_source_anchor_id = None
        self._connect_waypoints = []
        self._connect_preview_item = None
        self._update_connect_cursor()

    def _update_connect_cursor(self):
        """Kursor krzyzyka podczas rysowania linii laczacej tabele."""
        view = getattr(self, 'view', None)
        if view is None:
            return
        if self._connect_state is not None:
            view.setCursor(Qt.CursorShape.CrossCursor)
            # Wylacz "lapke" (ScrollHandDrag) na czas rysowania linii
            if view.dragMode() != QGraphicsView.DragMode.NoDrag:
                self._connect_prev_drag_mode = view.dragMode()
                view.setDragMode(QGraphicsView.DragMode.NoDrag)
        else:
            view.setCursor(Qt.CursorShape.ArrowCursor)
            prev = getattr(self, '_connect_prev_drag_mode', None)
            if prev is not None:
                view.setDragMode(prev)
                self._connect_prev_drag_mode = None

    def _cancel_connecting(self):
        self._connect_state = None
        self._connect_source_table = None
        self._connect_source_anchor_id = None
        self._connect_waypoints = []
        if self._connect_preview_item:
            self.removeItem(self._connect_preview_item)
            self._connect_preview_item = None
        self._update_connect_cursor()

    def _update_connect_preview(self, mouse_pos):
        if self._connect_preview_item:
            self.removeItem(self._connect_preview_item)
            self._connect_preview_item = None
        if not self._connect_source_table or not self._connect_source_anchor_id:
            return
        anchors = ConnectionLine.get_anchor_points(self._connect_source_table)
        p1 = anchors.get(self._connect_source_anchor_id)
        if p1 is None:
            return
        # Zastosuj trase 45-stopniowa do kazdego odcinka
        raw = [p1] + self._connect_waypoints + [mouse_pos]
        routed = []
        for i in range(len(raw) - 1):
            seg = ConnectionLine._route_45(raw[i], raw[i+1])
            if i == 0:
                routed.extend(seg)
            else:
                routed.extend(seg[1:])
        path = QPainterPath()
        path.moveTo(routed[0])
        for pt in routed[1:]:
            path.lineTo(pt)
        item = QGraphicsPathItem(path)
        pen = QPen(QColor("#004E96"), 6, Qt.PenStyle.DashLine)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        item.setPen(pen)
        self.addItem(item)
        self._connect_preview_item = item

    def start_zone_draw(self):
        self.zone_draw_mode = True
        self.zone_start = None

    def _create_zone_text(self, pos, text):
        item = QGraphicsTextItem(text)
        font = QFont("Gendy", 45)
        font.setBold(True)
        font.setItalic(True)
        item.setFont(font)
        item.setDefaultTextColor(QColor("#007A80"))
        item.setPos(pos)
        item.setZValue(-4000)
        item.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable, False)
        item.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable, False)

        def remove_text(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.removeItem(item)

        item.mouseDoubleClickEvent = remove_text
        self.addItem(item)

    def get_kanban_text(self):
        if self.tables and hasattr(self.tables[0], "kanban_text"):
            return self.tables[0].kanban_text.toPlainText().replace(" ", "_")
        return "Kanban"

    def serialize(self, encrypt_timeline=True):
        """Serializuje scene do slownika JSON. Timeline jest szyfrowany.
        (Faza 2) Pliki czyta/pisze StorageManager, tu jest tylko czysta serializacja."""
        data = {
            "tables": [], 
            "connections": [],
            "kanban_icon_pos": {"x": self.kanban_icon.x(), "y": self.kanban_icon.y()} if self.kanban_icon else None,
            "main_notes": self.main_notes,
            "notes_data": self.notes_data,
        }

        table_index_map = {}
        for ti, table in enumerate(self.tables):
            table_index_map[id(table)] = ti
            table_data = {
                "id": table.id,
                "pos_x": table.pos().x(),
                "pos_y": table.pos().y(),
                "is_base_table": table.is_base_table,
                "title_color_index": table.title_color_index,
                "title_left": table.title_text_left.toPlainText(),
                "title_right": table.title_text_right.toPlainText(),
                "title_right1": table.title_text_right1,
                "extra_rows": table.extra_rows,
                "body_height": table.body_height,
                "columns": [],
            }
            if hasattr(table, "kanban_text"):
                table_data["kanban_text"] = table.kanban_text.toPlainText()
                table_data["kanban_text_x"] = table.kanban_text.x()

            for col in table.columns:
                col_data = {
                    "id": col.id,
                    "header1": col.header_line1.toPlainText(),
                    "header2": col.header_line2.toPlainText(),
                    "header2a": col.header_line2a.toPlainText(),
                    "header3": col.header_line3.toPlainText(),
                    "header4": col.header_line4,
                    "notes": col.notes,
                    "opis": col.opis,
                    "worker_sel": col.worker_sel,
                    "tylko_nr": col.tylko_nr,
                    "w1_imie": col.w1_imie,
                    "w1_nazwisko": col.w1_nazwisko,
                    "w1_id": col.w1_id,
                    "w1_spec": col.w1_spec,
                    "w2_imie": col.w2_imie,
                    "w2_nazwisko": col.w2_nazwisko,
                    "w2_id": col.w2_id,
                    "w2_spec": col.w2_spec,
                    "header_overlay_index": col.header_overlay_index,
                    "body_overlay_index": col.body_overlay_index,
                    "linked_to_right": col.linked_to_right,
                    "linked_from_left": col.linked_from_left,
                    "cards": [card.to_dict(encrypt_timeline, self.password_manager) for card in col.cards],
                }
                table_data["columns"].append(col_data)
            data["tables"].append(table_data)

        for table in self.tables:
            for line in table.connected_lines:
                t1_idx = table_index_map.get(id(line.table1), -1)
                t2_idx = table_index_map.get(id(line.table2), -1)
                conn = {
                    "table1": t1_idx,
                    "table2": t2_idx,
                    "source_anchor_id": line.source_anchor_id,
                    "target_anchor_id": line.target_anchor_id,
                    "waypoints": [{"x": wp.x(), "y": wp.y()} for wp in line.waypoints],
                }
                if conn not in data["connections"] and t1_idx >= 0 and t2_idx >= 0:
                    data["connections"].append(conn)

        return data

    def deserialize(self, data):
        """Wczytuje scene ze slownika JSON (czysta deserializacja, bez plikow)."""
        # Usun stare tabele (oprocz bazowej)
        for table in self.tables[1:]:
            for line in list(table.connected_lines):
                line.remove_from_tables()
            table.prepareGeometryChange()
            table.setGraphicsEffect(None)
            self.removeItem(table)
        self.tables = self.tables[:1]

        base = self.tables[0]
        for col in base.columns:
            for card in list(col.cards):
                col.remove_card(card)
                self.removeItem(card)

        while len(base.columns) > BASE_COLUMNS:
            col = base.columns.pop()
            self.removeItem(col)

        # Wczytaj glowne notatki
        self.main_notes = data.get("main_notes", "")
        # Notatki (nowy format) - migracja general_info->notes_data w StorageManager
        self.notes_data = data.get("notes_data", [])

        # Wczytaj pozycje ikony Kanban
        icon_pos = data.get("kanban_icon_pos")
        if icon_pos and self.kanban_icon:
            self.kanban_icon.setPos(icon_pos.get("x", 0), icon_pos.get("y", -220))

        tables_data = data.get("tables", [])
        if not tables_data:
            return

        all_tables = []

        for ti, td in enumerate(tables_data):
            if ti == 0:
                table = base
            else:
                table = TableItem(is_base_table=False)
                self.tables.append(table)
                self.addItem(table)

            table.setPos(td.get("pos_x", 0), td.get("pos_y", 0))
            table.id = td.get("id") or new_id("table-")
            table.title_color_index = td.get("title_color_index", 0)
            table.title_text_left.setPlainText(td.get("title_left", "Tytul"))
            table.title_text_right.setPlainText(td.get("title_right", ""))
            table.title_text_right1 = td.get("title_right1", "_")
            table.extra_rows = td.get("extra_rows", 0)

            if hasattr(table, 'kanban_text'):
                default = "Wydzial PM" if table.is_base_table else ""
                table.kanban_text.setPlainText(td.get("kanban_text", default))
                kanban_x = td.get("kanban_text_x", 40)
                table.kanban_text.setPos(kanban_x, table.kanban_text.y())

            target_height = td.get("body_height", COLUMN_BODY_HEIGHT)
            table.body_height = target_height

            col_data_list = td.get("columns", [])
            while len(table.columns) < len(col_data_list):
                table.add_column(False)

            for ci, cd in enumerate(col_data_list):
                if ci >= len(table.columns):
                    break
                col = table.columns[ci]
                col.id = cd.get("id") or new_id("col-")
                col.header_line1.setPlainText(cd.get("header1", ""))
                col.header_line2.setPlainText(cd.get("header2", ""))
                col.header_line2a.setPlainText(cd.get("header2a", "Oper."))
                col.header_line3.setPlainText(cd.get("header3", ""))
                col.header_line4 = cd.get("header4", "*")
                col.notes = cd.get("notes", "")
                col.opis = cd.get("opis", "")
                col.worker_sel = cd.get("worker_sel", 1)
                col.tylko_nr = cd.get("tylko_nr", False)
                col.w1_imie = cd.get("w1_imie", "")
                col.w1_nazwisko = cd.get("w1_nazwisko", "")
                col.w1_id = cd.get("w1_id", "")
                col.w1_spec = cd.get("w1_spec", "")
                col.w2_imie = cd.get("w2_imie", "")
                col.w2_nazwisko = cd.get("w2_nazwisko", "")
                col.w2_id = cd.get("w2_id", "")
                col.w2_spec = cd.get("w2_spec", "")
                col.header_overlay_index = cd.get("header_overlay_index", 0)
                col.body_overlay_index = cd.get("body_overlay_index", 0)
                col.linked_to_right = cd.get("linked_to_right", False)
                col.linked_from_left = cd.get("linked_from_left", False)
                col.update_header_overlay()
                col.update_body_overlay()
                col.update_info_icon()
                col.set_body_height(target_height)

                for card_data in cd.get("cards", []):
                    card = CardItem.from_dict(card_data, self.password_manager)
                    col.add_card(card)

            table.relayout()
            table.update()
            all_tables.append(table)

        # Wczytaj polaczenia miedzy tabelami
        for conn in data.get("connections", []):
            t1_idx = conn.get("table1", -1)
            t2_idx = conn.get("table2", -1)
            if 0 <= t1_idx < len(all_tables) and 0 <= t2_idx < len(all_tables):
                table1 = all_tables[t1_idx]
                table2 = all_tables[t2_idx]
                source_anchor_id = conn.get("source_anchor_id", "TL")
                target_anchor_id = conn.get("target_anchor_id", "BR")
                waypoints_data = conn.get("waypoints", [])
                waypoints = [QPointF(wp["x"], wp["y"]) for wp in waypoints_data]
                line = ConnectionLine(table1, table2, source_anchor_id, target_anchor_id, waypoints)
                self.addItem(line)
                table1.connected_lines.append(line)
                table2.connected_lines.append(line)

        self.update()
        self._update_card_counter()

    def show_main_menu(self, screen_pos):
        menu = QMenu()
        menu.setFixedWidth(MENU_WIDTH)
        menu.setStyleSheet(f"""
            QMenu {{ background-color: {COLOR_MENU_BG}; border: {MENU_BORDER}px solid {COLOR_BORDER}; border-radius: 6px; }}
            QMenu::item {{ padding: 4px 10px; color: {COLOR_ACTIVE}; font-size: 9pt; font-weight: bold; }}
            QMenu::item:disabled {{ color: {COLOR_DISABLED}; background-color: #F0F0F0; }}
            QMenu::item:selected {{ background-color: #E6E6E6; }}
            QMenu::separator {{ height: 1px; background: {COLOR_BORDER}; margin: 2px 5px; }}
        """)

        act_header = QAction("MENU GLOWNE", menu)
        act_header.setEnabled(False)
        menu.addAction(act_header)
        menu.addSeparator()

        # (Usunięto: 'Wyszukaj Karty' — przeniesione do ikony 'Karty')

        act_last_changes = QAction("Ostatnie 10 zmian", menu)
        menu.addAction(act_last_changes)
        menu.addSeparator()

        act_change_password = QAction("Zmien haslo", menu)
        menu.addAction(act_change_password)
        menu.addSeparator()

        act_save_excel = QAction("Zapisz do Excela", menu)
        menu.addAction(act_save_excel)

        act_load = QAction("Wczytaj z pliku", menu)
        menu.addAction(act_load)

        action = menu.exec(screen_pos)

        if action == act_last_changes:
            if self.timeline_manager is not None:
                self.timeline_manager.show_last_changes_dialog(self)
            else:
                QMessageBox.warning(None, "Blad", "TimelineManager jest niedostepny.")
        elif action == act_change_password:
            if self.password_manager is not None:
                self.password_manager.change_password_dialog(None)
            else:
                QMessageBox.warning(None, "Blad", "Zarzadzanie haslem jest niedostepne.")
        elif action == act_save_excel:
            if self.export_manager is not None:
                self.export_manager.export_to_excel(self)
            else:
                QMessageBox.warning(None, "Blad", "ExportManager jest niedostepny.")
        elif action == act_load:
            if self.storage_manager is not None:
                self.storage_manager.load_project_dialog(self)
            else:
                QMessageBox.warning(None, "Blad", "Zapis plikow jest niedostepny.")

    def contextMenuEvent(self, event):
        if self.is_scene_blocked:
            event.accept()
            return

        item = self.itemAt(event.scenePos(), QTransform())
        if item is None:
            self.show_main_menu(event.screenPos())
            event.accept()
        else:
            super().contextMenuEvent(event)

    # Tryb edycji kart/tabel zarzadza EditManager (Faza 3)

    def mousePressEvent(self, event):
        from modules.ui.main_window import BlockIconItem, InfoIconItem
        
        # Klikniecie poza edytowana karta/tabela zamyka tryb edycji
        if self.edit_manager is not None and self.edit_manager.handle_scene_click(self, event):
            return

        if self.is_scene_blocked:
            item = self.itemAt(event.scenePos(), QTransform())
            allowed = isinstance(item, (BlockIconItem, InfoIconItem))
            # Zezwol na klikniecia w panel sceny (np. ikona BLOK zeby odblokowac)
            if not allowed and getattr(self, "scene_panel", None) is not None:
                node = item
                while node is not None:
                    if node is self.scene_panel:
                        allowed = True
                        break
                    node = node.parentItem()
            if not allowed:
                event.accept()
                return

        # Tryb lczenia tabel
        if self._connect_state is not None:
            if event.button() == Qt.MouseButton.RightButton:
                self._cancel_connecting()
                event.accept()
                return
            if event.button() == Qt.MouseButton.LeftButton:
                pos = event.scenePos()
                if self._connect_state == "anchor":
                    if self._connect_source_table:
                        result = ConnectionLine.get_anchor_id(self._connect_source_table, pos)
                        if result:
                            aid, apt = result
                            self._connect_source_anchor_id = aid
                            self._connect_state = "waypoints"
                            self._connect_waypoints = []
                            self._update_connect_preview(pos)
                    event.accept()
                    return
                elif self._connect_state == "waypoints":
                    for table in self.tables:
                        if table is self._connect_source_table:
                            continue
                        if table.sceneBoundingRect().contains(pos):
                            result = ConnectionLine.get_anchor_id(table, pos)
                            if result:
                                aid, apt = result
                            else:
                                aid, apt = ConnectionLine.get_nearest_anchor_id(table, pos)
                            line = ConnectionLine(
                                self._connect_source_table, table,
                                self._connect_source_anchor_id, aid,
                                self._connect_waypoints
                            )
                            self.addItem(line)
                            self._connect_source_table.connected_lines.append(line)
                            table.connected_lines.append(line)
                            self._cancel_connecting()
                            event.accept()
                            return
                    self._connect_waypoints.append(pos)
                    self._update_connect_preview(pos)
                    event.accept()
                    return

        if self.zone_draw_mode and event.button() == Qt.MouseButton.LeftButton:
            self.zone_start = event.scenePos()
            self.zone_preview = ZoneRect(QRectF(self.zone_start, self.zone_start))
            self.addItem(self.zone_preview)
            event.accept()
            return

        if self.zone_description_mode and event.button() == Qt.MouseButton.LeftButton:
            pos = event.scenePos()
            text, ok = QInputDialog.getText(None, "Opis strefy", "Opisz Strefe:")
            if ok and text.strip():
                self._create_zone_text(pos, text.strip())
            self.zone_description_mode = False
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._connect_state == "waypoints":
            self._update_connect_preview(event.scenePos())
            event.accept()
            return
        if self.zone_draw_mode and self.zone_preview and self.zone_start:
            rect = QRectF(self.zone_start, event.scenePos()).normalized()
            self.zone_preview.setRect(rect)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.zone_draw_mode and self.zone_preview:
            rect = self.zone_preview.rect()
            if rect.width() < 5 or rect.height() < 5:
                self.removeItem(self.zone_preview)
            self.zone_preview = None
            self.zone_start = None
            self.zone_draw_mode = False
            event.accept()
            return
        super().mouseReleaseEvent(event)
