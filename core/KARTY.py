"""
Moduł KARTY: ikona 'Karty' z licznikiem i dialogiem listy kart.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QWidget, QLabel, QPushButton, QHBoxLayout,
    QGraphicsObject
)
from PyQt6.QtGui import QFont, QBrush
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtWidgets import QGraphicsSimpleTextItem

from modules.core.kanban_items import create_icon_item
try:
    from config import STATUS_ICON_NAMES
except Exception:
    STATUS_ICON_NAMES = []


# Lightweight dialog showing sorted cards list with marker buttons
class KartyListDialog(QDialog):
    def __init__(self, cards, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Karty")
        self.resize(300, 600)
        layout = QVBoxLayout(self)

        self.list = QListWidget()
        self.list.setSelectionMode(self.list.SelectionMode.NoSelection)
        font = QFont("Arial", 8)
        self.list.setFont(font)

        # cards: list of CardItem
        # prepare entries sorted by main_num (text_items[2])
        items = []
        for c in cards:
            main = c.text_items[2].toPlainText().strip() if len(c.text_items) > 2 else ""
            ser = c.text_items[3].toPlainText().strip() if len(c.text_items) > 3 else ""
            items.append((main, ser, c))
        items.sort(key=lambda x: x[0] or "")

        for main, ser, card in items:
            widget = QWidget()
            h = QHBoxLayout(widget)
            h.setContentsMargins(6, 2, 6, 2)
            label = QLabel(f"{main} / {ser}")
            label.setFont(font)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            btn = QPushButton("🔍")
            btn.setFixedWidth(28)
            btn.setToolTip("Podświetl kartę")
            # attach card to button callback
            btn.clicked.connect(self._make_highlight_callback(card))
            h.addWidget(label)
            h.addStretch()
            h.addWidget(btn)

            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, widget)

        layout.addWidget(self.list)

    def _make_highlight_callback(self, card):
        def cb():
            try:
                # Use card.highlight_search() if exists
                if hasattr(card, 'highlight_search'):
                    card.highlight_search()
                else:
                    card._is_search_highlighted = True
                    card.update()
                # bring into view if in a scene/view
                s = card.scene()
                if s and hasattr(s, 'view'):
                    try:
                        v = s.view
                        v.centerOn(card.sceneBoundingRect().center())
                    except Exception:
                        pass
            except Exception:
                pass
        return cb


class KartyIconItem(QGraphicsObject):
    """Ikona 'Karty' z licznikiem kart uruchomionych (status Produckja) i dialogiem."""

    def __init__(self, filename, view, scene, parent=None):
        super().__init__(parent)
        self.view = view
        self.scene_ref = scene
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)
        self.setAcceptHoverEvents(True)
        self.setFlag(self.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self.setZValue(10000)

        # Icon (SVG preferred)
        try:
            self.icon_item = create_icon_item(self, filename, 50, 50)
        except Exception:
            self.icon_item = None

        # Licznik kart zostal przeniesiony do paska TABLE_TITLE tabeli bazowej
        # (patrz TableItem.update_card_counter). Ta ikona sluzy tylko jako
        # wyszukiwarka/lista kart (dwuklik -> KartyListDialog).

    def hoverEnterEvent(self, event):
        try:
            v = self.view if hasattr(self, 'view') else (self.scene().views()[0] if self.scene() and self.scene().views() else None)
            if v:
                v.setCursor(Qt.CursorShape.PointingHandCursor)
        except Exception:
            pass
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        try:
            v = self.view if hasattr(self, 'view') else (self.scene().views()[0] if self.scene() and self.scene().views() else None)
            if v:
                v.setCursor(Qt.CursorShape.ArrowCursor)
        except Exception:
            pass
        super().hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Open dialog with sorted list
            cards = []
            try:
                for t in getattr(self.scene_ref, 'tables', []):
                    for col in getattr(t, 'columns', []):
                        for c in getattr(col, 'cards', []):
                            cards.append(c)
            except Exception:
                pass
            dialog = KartyListDialog(cards)
            dialog.exec()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def update_position(self):
        # place under INFO2 (approx same column as block/info)
        if self.view:
            viewport_rect = self.view.viewport().rect()
            # below INFO2: offset y by 25 + 50 + 30 + 50
            # dodatkowe przesuniecie: +10 px w prawo, +50 px w dol
            scene_pos = self.view.mapToScene(viewport_rect.width() - 60 + 10, 25 + 50 + 30 + 50 + 50)
            self.setPos(scene_pos)

    def boundingRect(self):
        return QRectF(0, 0, 40, 40)

    def paint(self, painter, option, widget=None):
        pass


__all__ = ["KartyListDialog", "KartyIconItem"]
