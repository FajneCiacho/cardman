import os
import sys

from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtSvgWidgets import QGraphicsSvgItem

ICON_SCALE_FACTOR = 12

# resource_path should be set by the importer (kanban_items) to keep consistent base path
resource_path = None

# lokalny cache ikon gdy importowany samodzielnie
_ICON_CACHE = {}


def _ensure_resource_path():
    global resource_path
    if resource_path is None:
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        def _rp(rel):
            if rel.lower().endswith('.svg'):
                return os.path.join(base_path, "assets/svg", rel)
            return os.path.join(base_path, rel)
        resource_path = _rp


def load_icon(filename, width=None, height=None, scale_factor=ICON_SCALE_FACTOR):
    _ensure_resource_path()
    key = (filename, width, height, scale_factor)
    try:
        from PyQt6.QtGui import QPainter
    except Exception:
        pass
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]

    base_name = os.path.splitext(filename)[0]
    svg_path = resource_path(base_name + ".svg")
    if os.path.exists(svg_path):
        try:
            renderer = QSvgRenderer(svg_path)
            if renderer.isValid():
                if width and height:
                    hi_res_width = int(width * scale_factor)
                    hi_res_height = int(height * scale_factor)
                    pixmap = QPixmap(hi_res_width, hi_res_height)
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
                    renderer.render(painter, QRectF(0, 0, hi_res_width, hi_res_height))
                    painter.end()
                    result = pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    _ICON_CACHE[key] = result
                    return result
                else:
                    size = renderer.defaultSize()
                    hi_res_w = max(1, size.width() * scale_factor)
                    hi_res_h = max(1, size.height() * scale_factor)
                    hi_res = QPixmap(hi_res_w, hi_res_h)
                    hi_res.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(hi_res)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
                    renderer.render(painter, QRectF(0, 0, hi_res_w, hi_res_h))
                    painter.end()
                    result = hi_res.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    _ICON_CACHE[key] = result
                    return result
        except Exception:
            pass

    pixmap = QPixmap(resource_path(filename))
    if not pixmap.isNull():
        if width and height:
            result = pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            _ICON_CACHE[key] = result
            return result
        _ICON_CACHE[key] = pixmap
        return pixmap

    result = QPixmap()
    _ICON_CACHE[key] = result
    return result


def create_icon_item(parent, filename, width=None, height=None):
    _ensure_resource_path()
    svg_path = resource_path(os.path.splitext(filename)[0] + ".svg")
    if os.path.exists(svg_path):
        try:
            svg_item = QGraphicsSvgItem(svg_path, parent)
            if width is not None:
                br = svg_item.boundingRect()
                if br.width() > 0:
                    scale = float(width) / float(br.width())
                    svg_item.setScale(scale)
            return svg_item
        except Exception:
            pass

    pix = load_icon(filename, width, height)
    from PyQt6.QtWidgets import QGraphicsPixmapItem
    pm_item = QGraphicsPixmapItem(pix, parent)
    return pm_item


def _draw_icon_on_painter(painter, filename, rect: QRectF):
    _ensure_resource_path()
    base_name = os.path.splitext(filename)[0]
    svg_path = resource_path(base_name + ".svg")
    if os.path.exists(svg_path):
        try:
            renderer = QSvgRenderer(svg_path)
            if renderer.isValid():
                int_rect = QRectF(int(rect.x()), int(rect.y()), max(1, int(rect.width())), max(1, int(rect.height())))
                painter.save()
                try:
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
                except Exception:
                    pass
                renderer.render(painter, int_rect)
                painter.restore()
                return
        except Exception:
            pass

    pix = QPixmap(resource_path(filename))
    if not pix.isNull():
        target = rect.toRect()
        if pix.size() != target.size() and target.width() > 0 and target.height() > 0:
            scaled = pix.scaled(target.width(), target.height(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
            painter.drawPixmap(target, scaled)
        else:
            painter.drawPixmap(target, pix)
