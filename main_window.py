"""
main_window.py - Glowne okno aplikacji Kanban
POPRAWKI: ikony BLOK i INFO2 w prawym gornym rogu, autozapis staly
"""

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsPixmapItem,
    QGraphicsItem, QGraphicsObject, QMessageBox,
    QFileDialog, QInputDialog, QLineEdit, QDialog
)
from PyQt6.QtGui import QPixmap, QPainter, QColor, QIcon
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtSvg import QSvgRenderer

import sys
_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _base not in sys.path:
    sys.path.insert(0, _base)

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = _base
    if relative_path.lower().endswith('.svg'):
        return os.path.join(base_path, "assets/svg", relative_path)
    return os.path.join(base_path, relative_path)

def load_icon(filename, width, height, scale_factor=6):
    """Laduje ikonę jako SVG w wysokiej rozdzielczości (bez fallbacku do PNG)."""
    base_name = os.path.splitext(filename)[0]
    svg_path = resource_path(base_name + ".svg")
    if os.path.exists(svg_path):
        try:
            renderer = QSvgRenderer(svg_path)
            if renderer.isValid():
                hi_res_width = int(width * scale_factor)
                hi_res_height = int(height * scale_factor)
                pixmap = QPixmap(hi_res_width, hi_res_height)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
                renderer.render(painter, QRectF(0, 0, hi_res_width, hi_res_height))
                painter.end()
                return pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        except Exception:
            pass

    # Fallback - pusta ikona (SVG niedostepne)
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("#CCCCCC"))
    return pixmap

try:
    from modules.core.kanban_scene import KanbanScene
except ImportError as e:
    print("BLAD: Nie mozna zaimportowac KanbanScene:", e)
    import traceback
    traceback.print_exc()
    sys.exit(1)


class BlockIconItem(QGraphicsObject):
    """Ikona blokady sceny jako kontener - preferuje SVG."""

    def __init__(self, filename_normal, filename_blocked, view, password_manager=None):
        super().__init__()
        self.view = view
        self.is_blocked = False
        self.filename_normal = filename_normal
        self.filename_blocked = filename_blocked
        self.password_manager = password_manager
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self.setZValue(10000)

        # Utwórz elementy wewnętrzne (SVG preferred)
        try:
            from modules.core.kanban_items import create_icon_item
            self.icon_normal = create_icon_item(self, filename_normal, 40, 40)
            self.icon_blocked = create_icon_item(self, filename_blocked, 40, 40)
        except Exception:
            # Fallback na pixmapy
            self.icon_normal = QGraphicsPixmapItem(load_icon(filename_normal, 40, 40), self)
            self.icon_blocked = QGraphicsPixmapItem(load_icon(filename_blocked, 40, 40), self)

        if self.icon_blocked:
            try:
                self.icon_blocked.setVisible(False)
            except Exception:
                pass

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_block()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def toggle_block(self):
        if self.is_blocked and self.password_manager is not None:
            pwd = self.password_manager.prompt_for_password(
                self.view,
                title="Odblokowanie sceny",
                text="Podaj haslo:",
            )
            if pwd is None or not self.password_manager.verify_password(pwd):
                QMessageBox.warning(self.view, "Bledne haslo", "Niepoprawne haslo.")
                return

        self.is_blocked = not self.is_blocked
        scene = self.scene()
        if scene:
            scene.set_scene_blocked(self.is_blocked)

        # Pokaż odpowiedni wewnętrzny element
        try:
            if self.is_blocked:
                self.icon_blocked.setVisible(True)
                self.icon_normal.setVisible(False)
            else:
                self.icon_blocked.setVisible(False)
                self.icon_normal.setVisible(True)
        except Exception:
            pass

    def update_position(self):
        """Aktualizuje pozycje - prawy gorny rog."""
        if self.view:
            viewport_rect = self.view.viewport().rect()
            # Prawy gorny rog
            scene_pos = self.view.mapToScene(viewport_rect.width() - 50, 15)
            self.setPos(scene_pos)

    def boundingRect(self):
        return QRectF(0, 0, 40, 40)

    def paint(self, painter, option, widget=None):
        # Kontener nie rysuje samodzielnie; dzieci robią rendering
        pass


class InfoIconItem(QGraphicsObject):
    """Ikona INFO2 jako kontener - preferuje SVG."""

    def __init__(self, filename_empty, filename_filled, view, scene):
        super().__init__()
        self.view = view
        self.kanban_scene = scene
        self.filename_empty = filename_empty
        self.filename_filled = filename_filled
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)
        self.setZValue(10000)

        try:
            from modules.core.kanban_items import create_icon_item
            self.icon_empty = create_icon_item(self, filename_empty, 40, 40)
            self.icon_filled = create_icon_item(self, filename_filled, 40, 40)
        except Exception:
            self.icon_empty = QGraphicsPixmapItem(load_icon(filename_empty, 40, 40), self)
            self.icon_filled = QGraphicsPixmapItem(load_icon(filename_filled, 40, 40), self)

        self.update_icon()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.show_main_notes()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def show_main_notes(self):
        """Pokazuje glowny notatnik (przez NotebookManager)."""
        manager = getattr(self.kanban_scene, "notebook_manager", None)
        if manager is not None:
            if manager.open_main_notes(view=self.view):
                self.update_icon()
            return
        from modules.ui.dialogs import MainNotesDialog
        dialog = MainNotesDialog(self.kanban_scene.main_notes, self.view)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.kanban_scene.main_notes = dialog.get_text()
            self.update_icon()

    def update_icon(self):
        """Aktualizuje ikone w zaleznosci od zawartosci notatnika."""
        try:
            if self.kanban_scene.main_notes.strip():
                self.icon_filled.setVisible(True)
                self.icon_empty.setVisible(False)
            else:
                self.icon_filled.setVisible(False)
                self.icon_empty.setVisible(True)
        except Exception:
            pass

    def update_position(self):
        """Aktualizuje pozycje - 30px pod BLOK."""
        if self.view:
            viewport_rect = self.view.viewport().rect()
            # 30px pod ikona BLOK
            scene_pos = self.view.mapToScene(viewport_rect.width() - 50, 15 + 40 + 20)
            self.setPos(scene_pos)

    def boundingRect(self):
        return QRectF(0, 0, 40, 40)

    def paint(self, painter, option, widget=None):
        pass


class KanbanView(QGraphicsView):
    """Widok Kanban z obsluga zoom."""

    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.zoom_step = 1.3
        self.setBackgroundBrush(QColor("#FFFFFF"))
        self.current_scale = 1.1

        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setOptimizationFlags(QGraphicsView.OptimizationFlag.DontSavePainterState)

        # Wysuwanie panelu sceny po najechaniu kursorem w gorny-srodkowy pas.
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        # HoverManager (Faza 3) zarzadza strefa REVEAL i timerem panelu
        self.hover_manager = None

    # --- wysuwanie panelu sceny (delegacja do HoverManager, Faza 3) ---

    def mouseMoveEvent(self, event):
        if self.hover_manager is not None:
            self.hover_manager.handle_mouse_move(event)
        # super() najpierw (hover text-itemow ustawia "lapke"), potem wymus kursor
        super().mouseMoveEvent(event)
        # Kursor krzyzyka podczas rysowania linii laczacych tabele
        scene = self.scene()
        if scene is not None and getattr(scene, '_connect_state', None) is not None:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def leaveEvent(self, event):
        if self.hover_manager is not None:
            self.hover_manager.handle_leave()
        super().leaveEvent(event)

    def wheelEvent(self, event):
        old_pos = self.mapToScene(event.position().toPoint())

        if event.angleDelta().y() > 0:
            factor = self.zoom_step
        else:
            factor = 1 / self.zoom_step

        self.scale(factor, factor)
        self.current_scale *= factor

        new_pos = self.mapToScene(event.position().toPoint())
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

        self.scene().update()
        self._update_icons()

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        self._update_icons()

    def _update_icons(self):
        scene = self.scene()
        if scene:
            panel = getattr(scene, 'scene_panel', None)
            if panel:
                panel.update_position()


class MainWindow(QWidget):
    """Glowne okno aplikacji."""

    def __init__(self, password_manager, config_folder=None):
        super().__init__()
        self.setWindowTitle("CARDMAN v.3")
        self.resize(1200, 900)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

        self.password_manager = password_manager
        self.config_folder = config_folder or os.path.dirname(os.path.abspath(__file__))

        # Faza 3: SettingsManager (session_config + config_overrides)
        self._setup_settings_manager()

        # Załaduj konfigurację sesji
        self.session_config = self.settings_manager.load_session_config()
        
        # Załaduj zmienne konfiguracyjne (ręczne dostosowania)
        self.config_overrides = self.settings_manager.load_config_overrides()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.scene = KanbanScene(self.password_manager, self.config_folder)
        self.view = KanbanView(self.scene)
        self.scene.view = self.view
        layout.addWidget(self.view)

        # Faza 1: EventManager + TimelineManager (logika poza obiektami)
        self._setup_event_managers()

        # Faza 2: StorageManager (jedyne miejsce zapisu/odczytu plikow)
        self._setup_storage_manager()

        # Faza 3: NotebookManager (notatki sceny)
        self._setup_notebook_manager()

        # Faza 3: SearchManager (wyszukiwarka i lista kart)
        self._setup_search_manager()

        # Faza 3: ExportManager (eksport danych)
        self._setup_export_manager()

        # Faza 3: LayoutManager (uklad sceny)
        self._setup_layout_manager()
        if self.layout_manager is not None:
            # Pozycja startowa ikony kanban (autozapis moze ja nadpisac)
            self.layout_manager.position_kanban_icon(self.scene)

        # Faza 3: EditManager (tryb edycji kart i tabel)
        self._setup_edit_manager()

        # Faza 3: HoverManager (wysuwanie panelu sceny)
        self._setup_hover_manager()

        # Faza 3: AppearanceManager (katalog wygladu)
        self._setup_appearance_manager()
        
        self._add_icons()
        self._apply_app_settings()
        self._try_load_autosave()
        self._apply_app_settings()
        self._center_and_zoom_table()

    def _apply_app_settings(self):
        """Laduje i stosuje ustawienia aplikacji (folder zapisu, przyciemnianie sceny)."""
        if self.settings_manager is None:
            return
        try:
            app_settings = self.settings_manager.load_app_settings()
        except Exception:
            app_settings = {}
        try:
            folder = app_settings.get("save_folder")
            if folder and os.path.isdir(folder):
                self.scene.save_folder = folder
        except Exception:
            pass
        try:
            obraz = app_settings.get("Obraz_folder")
            if obraz and os.path.isdir(obraz):
                self.scene.obraz_folder = obraz
        except Exception:
            pass
        try:
            intensity = app_settings.get("dim_intensity", None)
            if intensity is None:
                intensity = 50 if app_settings.get("dim_scene_with_columns", False) else 0
            self.scene.dim_intensity = int(intensity)
            self.scene.apply_dim_state()
        except Exception:
            pass

    def _setup_appearance_manager(self):
        """Tworzy AppearanceManager - katalog wygladu (kolory, nakladki, fonty)."""
        try:
            from modules.managers.appearance_manager import AppearanceManager
            self.appearance_manager = AppearanceManager()
            self.scene.appearance_manager = self.appearance_manager
        except Exception as e:
            print("BLAD: nie mozna utworzyc AppearanceManager:", e)
            self.appearance_manager = None

    def _setup_hover_manager(self):
        """Tworzy HoverManager - wysuwanie panelu sceny."""
        try:
            from modules.managers.hover_manager import HoverManager
            self.view.hover_manager = HoverManager(self.view)
        except Exception as e:
            print("BLAD: nie mozna utworzyc HoverManager:", e)
            self.view.hover_manager = None

    def _setup_edit_manager(self):
        """Tworzy EditManager - tryb edycji kart i tabel."""
        try:
            from modules.managers.edit_manager import EditManager
            self.edit_manager = EditManager()
            self.scene.edit_manager = self.edit_manager
        except Exception as e:
            print("BLAD: nie mozna utworzyc EditManager:", e)
            self.edit_manager = None

    def _setup_layout_manager(self):
        """Tworzy LayoutManager - uklad sceny."""
        try:
            from modules.managers.layout_manager import LayoutManager
            self.layout_manager = LayoutManager()
            self.scene.layout_manager = self.layout_manager
        except Exception as e:
            print("BLAD: nie mozna utworzyc LayoutManager:", e)
            self.layout_manager = None

    def _setup_settings_manager(self):
        """Tworzy SettingsManager - konfiguracja sesji i overrides."""
        try:
            from modules.managers.settings_manager import SettingsManager
            self.settings_manager = SettingsManager(self.config_folder)
        except Exception as e:
            print("BLAD: nie mozna utworzyc SettingsManager:", e)
            self.settings_manager = None

    def _setup_export_manager(self):
        """Tworzy ExportManager - eksport danych (Excel)."""
        try:
            from modules.managers.export_manager import ExportManager
            self.export_manager = ExportManager()
            self.scene.export_manager = self.export_manager
        except Exception as e:
            print("BLAD: nie mozna utworzyc ExportManager:", e)
            self.export_manager = None

    def _setup_search_manager(self):
        """Tworzy SearchManager - wyszukiwarka i lista kart."""
        try:
            from modules.managers.search_manager import SearchManager
            self.search_manager = SearchManager()
            self.scene.search_manager = self.search_manager
        except Exception as e:
            print("BLAD: nie mozna utworzyc SearchManager:", e)
            self.search_manager = None

    def _setup_notebook_manager(self):
        """Tworzy NotebookManager - notatki (glowny notatnik + produkcyjne)."""
        try:
            from modules.managers.notebook_manager import NotebookManager
            self.notebook_manager = NotebookManager()
            self.scene.notebook_manager = self.notebook_manager
        except Exception as e:
            print("BLAD: nie mozna utworzyc NotebookManager:", e)
            self.notebook_manager = None

    def _setup_storage_manager(self):
        """Tworzy StorageManager - jedyny modul czytajacy i piszacy pliki (Faza 2)."""
        try:
            from modules.managers.storage_manager import StorageManager
            self.storage_manager = StorageManager(self.config_folder, self.password_manager)
            self.scene.storage_manager = self.storage_manager
        except Exception as e:
            print("BLAD: nie mozna utworzyc StorageManager:", e)
            self.storage_manager = None

    def _setup_event_managers(self):
        """Tworzy EventManager i rejestruje managery (Faza 1)."""
        try:
            from modules.core.event_manager import EventManager
            from modules.managers.timeline_manager import TimelineManager
            self.event_manager = EventManager()
            self.timeline_manager = TimelineManager()
            self.event_manager.register(self.timeline_manager)
            self.scene.event_manager = self.event_manager
            self.scene.timeline_manager = self.timeline_manager
        except Exception as e:
            print("BLAD: nie mozna utworzyc managerow:", e)
            self.event_manager = None
            self.timeline_manager = None

    def _add_icons(self):
        """Dodaje glowny panel sceny (BLOK / INFO2 / NOTES / KARTY / USTAWIENIA)."""
        self.scene_panel = None
        try:
            from modules.plugins.card_icon_panel import create_scene_panel
            self.scene_panel = create_scene_panel(self.view, self.scene, self.password_manager)
            self.scene.addItem(self.scene_panel)
            self.scene.scene_panel = self.scene_panel
        except Exception as e:
            print("BLAD: nie mozna utworzyc panelu sceny:", e)
            self.scene_panel = None

        self._update_icons_position()

    def _center_and_zoom_table(self):
        if self.layout_manager is not None:
            self.layout_manager.center_and_zoom(self.scene, self.view)

    def _update_icons_position(self):
        if getattr(self, 'scene_panel', None):
            try:
                self.scene_panel.update_position()
            except Exception:
                pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_icons_position()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(50, self._center_and_zoom_table)
        QTimer.singleShot(100, self._update_icons_position)

    def _try_load_autosave(self):
        """Probuje wczytac najnowszy autozapis (przez StorageManager)."""
        if self.storage_manager is None:
            return
        loaded = self.storage_manager.load_autosave(self.scene, self)
        if loaded and getattr(self, 'scene_panel', None):
            self.scene_panel.refresh_states()
            self._update_icons_position()

    def closeEvent(self, event):
        """Zapisuje zaszyfrowany autozapis i konfigurację sesji przy zamknieciu."""
        # Zapisz konfigurację sesji (przez SettingsManager)
        if self.settings_manager is not None:
            self.settings_manager.save_session_config()

        # Zapisz autozapis (przez StorageManager)
        if self.storage_manager is not None:
            try:
                if not self.storage_manager.save_autosave(self.scene):
                    QMessageBox.critical(
                        self,
                        "Blad autozapisu",
                        "Nie udalo sie zapisac zaszyfrowanego autozapisu.",
                    )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Blad autozapisu",
                    f"Nie udalo sie zapisac zaszyfrowanego autozapisu:\n{e}",
                )
        event.accept()
