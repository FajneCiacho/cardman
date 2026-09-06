"""
form_manager.py - FormManager: centralny manager formularzy (Faza 7, architektura dynamiczna).

Formularze nie sa importowane statycznie w tym module, lecz ladowane leniwie
przez `importlib` na podstawie rejestru (nazwa -> (modul, klasa)). Dzieki temu:
  - jedna regula (rejestr) dla calej rodziny formularzy: karta / kolumna / tabela,
    podglad / edycja, notes / obraz / timeline,
  - nowe formularze = nowy modul + jeden wpis w rejestrze (bez zmian w importach),
  - brak gestych zaleznosci importowych na starcie aplikacji.
"""
from PyQt6.QtCore import QTimer, Qt


class FormManager:
    """Zarzadza formularzami przez dynamiczny rejestr (lazy import)."""

    HOVER_HOLD_MS = 1200  # fallbackowy podglad po ~1.2s najechania

    # Rejestr formularzy: nazwa -> (sciezka modulu, nazwa klasy w module).
    REGISTRY = {
        "card_edit":       ("modules.ui.forms_card", "CardEditDialog"),
        "card_preview":    ("modules.ui.forms_card", "CardHoverDialog"),
        "column_edit":     ("modules.ui.forms_column", "ColumnEditDialog"),
        "column_preview":  ("modules.ui.forms_column", "ColumnHoverDialog"),
        "table_edit":      ("modules.ui.forms_table", "TableEditDialog"),
        "table_preview":   ("modules.ui.forms_table", "TableHoverDialog"),
    }

    def __init__(self, view):
        self.view = view
        self._hover_timer = QTimer(view)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._open_preview)
        self._hover_item = None
        self._dialog_open = False

    # --- rejestr / leniwy import ---

    @classmethod
    def register(cls, name, module_path, class_name):
        """Rejestruje/podmienia wpis w rejestrze. Zwraca nazwe."""
        cls.REGISTRY[name] = (module_path, class_name)
        return name

    @classmethod
    def resolve(cls, name):
        """Leniwie importuje modul i zwraca klase formularza."""
        module_path, class_name = cls.REGISTRY[name]
        mod = __import__(module_path, fromlist=[class_name])
        return getattr(mod, class_name)

    # --- pomocnicze ---

    def scene(self):
        return self.view.scene()

    def _editing_any(self):
        scene = self.scene()
        em = getattr(scene, 'edit_manager', None) if scene else None
        if em is None:
            return False
        return em.editing_table is not None

    def _item_under_cursor(self, pos):
        scene = self.scene()
        if scene is None:
            return None
        from PyQt6.QtCore import QPointF
        from modules.core.card_item import CardItem
        from modules.core.column_item import ColumnItem
        from modules.core.table_item import TableItem
        for it in scene.items(QPointF(pos)):
            if isinstance(it, (CardItem, ColumnItem, TableItem)):
                return it
        return None

    # --- otwarcie przez rejestr ---

    def _open(self, name, item, mode=None):
        """Utworzenie + uruchomienie dialog, jesli formularz jeszcze nie otwarty."""
        if self._dialog_open:
            return
        try:
            dialog_cls = self.resolve(name)
        except (ImportError, KeyError, AttributeError) as exc:
            print("FORM-MANAGER: brak formularza %r (%s)" % (name, exc))
            return
        self._run_dialog(self._build(dialog_cls, item, mode))

    def _build(self, dialog_cls, item, mode):
        """Buduje konkretny dialog zgodnie z jego sygnatura (kompatybilnosc z Faza 6)."""
        return dialog_cls(item, mode=mode, view=self.view)

    # --- delegacja po typie elementu ---

    def _form_name(self, item, mode):
        from modules.core.card_item import CardItem
        from modules.core.column_item import ColumnItem
        from modules.core.table_item import TableItem
        if isinstance(item, CardItem):
            base = "card"
        elif isinstance(item, ColumnItem):
            base = "column"
        elif isinstance(item, TableItem):
            base = "table"
        else:
            return None
        return "%s_%s" % (base, mode)

    def open_edit_dialog(self, item):
        name = self._form_name(item, "edit")
        if name in self.REGISTRY:
            self._open(name, item, mode="edit")

    def open_preview_dialog(self, item):
        name = self._form_name(item, "preview")
        if name in self.REGISTRY:
            self._open(name, item, mode="preview")

    # --- statyczne wywolania (z poziomu itemow sceny, bez widoku) ---

    @staticmethod
    def _dialog_for(item, name):
        dialog_cls = FormManager.resolve(name)
        return dialog_cls(item, mode="preview" if name.endswith("preview") else "edit")

    @classmethod
    def open_edit_dialog_static(cls, item):
        name = cls._item_form_name(item, "edit")
        if name is not None:
            cls._run_static(cls._dialog_for(item, name))

    @classmethod
    def open_preview_dialog_static(cls, item):
        name = cls._item_form_name(item, "preview")
        if name is not None:
            cls._run_static(cls._dialog_for(item, name))

    @staticmethod
    def _item_form_name(item, mode):
        from modules.core.card_item import CardItem
        from modules.core.column_item import ColumnItem
        from modules.core.table_item import TableItem
        if isinstance(item, CardItem):
            base = "card"
        elif isinstance(item, ColumnItem):
            base = "column"
        elif isinstance(item, TableItem):
            base = "table"
        else:
            return None
        name = "%s_%s" % (base, mode)
        if name not in FormManager.REGISTRY:
            return None
        return name

    @staticmethod
    def _run_static(dialog):
        dialog.exec()

    # --- obsługa hover (fallback podgladu) ---

    def handle_mouse_move(self, event):
        if self._dialog_open:
            return
        if event.buttons() != Qt.MouseButton.NoButton:
            self.cancel_hover()
            return
        if self._editing_any():
            self.cancel_hover()
            return
        item = self._item_under_cursor(event.position().toPoint())
        if item is not self._hover_item:
            self._hover_item = item
            self._hover_timer.stop()
            if item is not None:
                self._hover_timer.start(self.HOVER_HOLD_MS)

    def handle_leave(self):
        self.cancel_hover()

    def handle_wheel(self):
        self.cancel_hover()

    def cancel_hover(self):
        self._hover_timer.stop()
        self._hover_item = None

    def _open_preview(self):
        item = self._hover_item
        if item is None:
            return
        if self._editing_any():
            return
        self._hover_item = None
        self.open_preview_dialog(item)

    # --- uruchamianie ---

    def _run_dialog(self, dialog):
        self._dialog_open = True
        try:
            dialog.exec()
        finally:
            self._dialog_open = False
            self.cancel_hover()
