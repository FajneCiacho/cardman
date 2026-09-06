"""
text_items.py - Elementy tekstowe Kanban (Faza 4, krok 4.1).

SingleLineText (tekst karty) i LimitedWidthTextItem (naglowki/kolumny).
Przeniesione 1:1 z kanban_items.py. Nie zaleza od kanban_items (leniwy import
CardItem w SingleLineText.mousePressEvent).
"""
from PyQt6.QtWidgets import QGraphicsItem, QInputDialog, QDialog
from PyQt6.QtGui import QFont, QColor, QPen, QFontMetrics, QPainterPath
from PyQt6.QtCore import Qt, QRectF


class SingleLineText(QGraphicsItem):
    """Tekst z ograniczeniem szerokości na karcie."""
    
    def __init__(self, text, max_width, parent=None):
        super().__init__(parent)
        self._text = text
        self.max_width = max_width
        self._font = QFont("Arial", 10)
        self._color = Qt.GlobalColor.black
        self.on_change = None
        self.setAcceptedMouseButtons(Qt.MouseButton.RightButton)
        try:
            self.setAcceptHoverEvents(True)
        except Exception:
            pass

    def setFont(self, font):
        self._font = font

    def font(self):
        return self._font

    def setDefaultTextColor(self, color):
        self._color = color

    def setPlainText(self, text):
        self._text = text
        self._limit_width()
        self.update()

    def toPlainText(self):
        return self._text

    def boundingRect(self):
        fm = QFontMetrics(self._font)
        return QRectF(0, 0, self.max_width, fm.height())

    def shape(self):
        """Zwraca ksztalt tylko dla rzeczywistej szerokosci tekstu."""
        fm = QFontMetrics(self._font)
        text_width = min(fm.horizontalAdvance(self._text), self.max_width)
        path = QPainterPath()
        path.addRect(QRectF(0, 0, max(text_width + 4, 10), fm.height()))
        return path

    def paint(self, painter, option, widget=None):
        painter.setFont(self._font)
        painter.setPen(QPen(self._color))
        fm = QFontMetrics(self._font)
        text = self._text
        if fm.horizontalAdvance(text) > self.max_width:
            while fm.horizontalAdvance(text + "...") > self.max_width and len(text) > 0:
                text = text[:-1]
            text += "..."
        # If this is a 'ser' field, right-align the text inside the available width
        try:
            if getattr(self, 'is_ser', False):
                text_width = fm.horizontalAdvance(text)
                x = max(0, self.max_width - text_width)
                painter.drawText(x, fm.ascent(), text)
                return
        except Exception:
            pass
        painter.drawText(0, fm.ascent(), text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            # Blokuj edycje tekstu gdy karta nie w trybie edycji
            parent = self.parentItem()
            from modules.core.kanban_items import CardItem
            if isinstance(parent, CardItem) and not getattr(parent, '_editing', False):
                event.ignore()
                return
            # Sprawdz czy kliknieto na rzeczywisty tekst
            fm = QFontMetrics(self._font)
            text_width = min(fm.horizontalAdvance(self._text), self.max_width)
            click_x = event.pos().x()
            if click_x > text_width + 4:
                event.ignore()
                return
            current_text = self._text
            # Use a dialog instance so we can set RTL layout for series fields
            dlg = QInputDialog()
            dlg.setWindowTitle("Edytuj tekst")
            dlg.setLabelText("Nowy tekst:")
            dlg.setTextValue(current_text)
            try:
                if getattr(self, 'is_ser', False):
                    dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            except Exception:
                pass
            res = dlg.exec()
            if res == QDialog.DialogCode.Accepted:
                new_text = dlg.textValue()
                old_text = self._text
                self.setPlainText(new_text)
                if self.on_change and new_text != old_text:
                    self.on_change(old_text, new_text)
            event.accept()
            return
        super().mousePressEvent(event)

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

    def _limit_width(self):
        self._text = self._text.replace("\n", " ")


class LimitedWidthTextItem(QGraphicsItem):
    """Tekst z ograniczeniem szerokości - używany w nagłówkach."""
    
    def __init__(self, max_width=800, parent=None, default_text=""):
        super().__init__(parent)
        self._text = default_text
        self.max_width = max_width
        self._font = QFont("Arial", 12)
        self._color = QColor("#FEFEFE")
        self.setZValue(20)
        self._restrict_to_x = False
        self._margin_x = 0
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)
        try:
            self.setAcceptHoverEvents(True)
        except Exception:
            pass
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)

    def setFont(self, font):
        self._font = font
        self.update()

    def font(self):
        return self._font

    def setDefaultTextColor(self, color):
        self._color = color
        self.update()

    def setPlainText(self, text):
        self._text = text.replace("\n", " ")
        self._limit_width()
        self.update()

    def toPlainText(self):
        return self._text

    def _actual_text_width(self):
        """Zwraca faktyczna szerokosc tekstu w pikselach."""
        fm = QFontMetrics(self._font)
        return min(fm.horizontalAdvance(self._text), self.max_width)

    def boundingRect(self):
        fm = QFontMetrics(self._font)
        return QRectF(0, 0, self.max_width, fm.height())

    def shape(self):
        """Zwraca ksztalt tylko dla rzeczywistej szerokosci tekstu."""
        fm = QFontMetrics(self._font)
        text_width = self._actual_text_width()
        path = QPainterPath()
        path.addRect(QRectF(0, 0, max(text_width + 4, 10), fm.height()))
        return path

    def paint(self, painter, option, widget=None):
        painter.setFont(self._font)
        painter.setPen(QPen(self._color))
        fm = QFontMetrics(self._font)
        text = self._text
        if fm.horizontalAdvance(text) > self.max_width:
            while fm.horizontalAdvance(text + "...") > self.max_width and len(text) > 0:
                text = text[:-1]
            text += "..."
        painter.drawText(0, fm.ascent(), text)

    def _limit_width(self):
        fm = QFontMetrics(self._font)
        text = self._text
        if fm.horizontalAdvance(text) > self.max_width:
            while fm.horizontalAdvance(text + "...") > self.max_width and len(text) > 0:
                text = text[:-1]
            self._text = text + "..."

    def mousePressEvent(self, event):
        # Ctrl + klik LPM - akcja przypisana do tekstu (np. edytor Glownej nazwy).
        if (event.button() == Qt.MouseButton.LeftButton
                and event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            on_ctrl_click = getattr(self, "on_ctrl_click", None)
            if on_ctrl_click is not None:
                on_ctrl_click()
                event.accept()
                return
        if event.button() == Qt.MouseButton.RightButton:
            # Sprawdz czy edycja jest dozwolona (ktorys z rodzicow ma _editing=True)
            node = self.parentItem()
            editing_allowed = False
            while node is not None:
                if getattr(node, '_editing', False):
                    editing_allowed = True
                    break
                node = node.parentItem()
            if not editing_allowed:
                super().mousePressEvent(event)
                return
            # Sprawdz czy kliknieto na rzeczywisty tekst
            text_width = self._actual_text_width()
            click_x = event.pos().x()
            if click_x > text_width + 4:
                event.ignore()
                return
            current_text = self._text
            new_text, ok = QInputDialog.getText(
                None, "Edytuj tekst", "Nowy tekst:", text=current_text
            )
            if ok:
                self.setPlainText(new_text)
            event.accept()
            return
        super().mousePressEvent(event)

    def itemChange(self, change, value):
        if (
            change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
            and self._restrict_to_x
        ):
            if not self.parentItem():
                return super().itemChange(change, value)
            parent_width = self.parentItem().boundingRect().width()
            min_x = 20
            max_x = parent_width - 220
            new_x = max(min_x, min(value.x(), max_x))
            value.setX(new_x)
            value.setY(self.pos().y())
            return value
        return super().itemChange(change, value)

    def mouseMoveEvent(self, event):
        if self._restrict_to_x and event.buttons() & Qt.MouseButton.LeftButton:
            if not self.parentItem():
                super().mouseMoveEvent(event)
                return
            parent_width = self.parentItem().boundingRect().width()
            min_x = 20
            max_x = parent_width - 220
            delta_x = event.pos().x() - event.buttonDownPos(Qt.MouseButton.LeftButton).x()
            new_x = self.pos().x() + delta_x
            new_x = max(min_x, min(new_x, max_x))
            self.setPos(new_x, self.pos().y())
        else:
            super().mouseMoveEvent(event)

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
