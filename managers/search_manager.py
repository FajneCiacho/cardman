"""
search_manager.py - Wyszukiwarka i lista kart (Faza 3).

Odpowiedzialnosci:
- wyszukiwanie kart (search_card),
- podswietlanie znalezionej karty (highlight_card / unhighlight_card),
- dialog wyszukiwania (SearchCardDialog) i lista kart (KartyListDialog).

Przeniesione z KanbanScene i card_icon_panel.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QMessageBox


class SearchManager:
    """Wyszukiwarka kart i zarzadzanie podswietleniem wyniku."""

    def __init__(self):
        self._highlighted_card = None

    # --- kolekcje ---

    def all_cards(self, scene):
        """Generator wszystkich kart na scenie."""
        for table in getattr(scene, "tables", []):
            for col in getattr(table, "columns", []):
                for card in getattr(col, "cards", []):
                    yield card

    # --- wyszukiwanie ---

    def search_card(self, scene, detal, ser):
        """Szuka karty po detalu i numerze serii (normalizacja)."""
        def normalize(text):
            return "".join(c for c in text if c.isalnum() or c == " ").upper()

        search_detal = normalize(detal)
        search_ser = normalize(ser)

        for card in self.all_cards(scene):
            main_num = card.text_items[2].toPlainText() if len(card.text_items) > 2 else ""
            ser_num = card.text_items[3].toPlainText() if len(card.text_items) > 3 else ""
            card_main = normalize(main_num)
            card_ser = normalize(ser_num)
            detal_match = (not search_detal) or (card_main == search_detal)
            ser_match = (not search_ser) or (card_ser == search_ser)
            if detal_match and ser_match and (search_detal or search_ser):
                return card
        return None

    # --- podswietlenie ---

    def highlight_card(self, scene, card):
        if self._highlighted_card:
            self._highlighted_card.clear_search_highlight()
        self._highlighted_card = card
        card.highlight_search()
        card.setAcceptedMouseButtons(
            Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
        )

    def unhighlight_card(self, scene=None):
        if self._highlighted_card:
            self._highlighted_card.clear_search_highlight()
            self._highlighted_card = None

    # --- dialogi ---

    def open_search_dialog(self, scene, parent=None):
        from modules.ui.dialogs import SearchCardDialog
        dialog = SearchCardDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            detal, ser = dialog.get_search_params()
            card = self.search_card(scene, detal, ser)
            if card:
                self.highlight_card(scene, card)
                QMessageBox.information(
                    None,
                    "Znaleziono",
                    "Karta znaleziona i podswietlona.\n"
                    "Kliknij LPM na karte aby powrocic do normalnego widoku.",
                )
            else:
                QMessageBox.warning(None, "Nie znaleziono", "Nie znaleziono karty.")

    def open_karty_list(self, scene, parent=None):
        from modules.core.KARTY import KartyListDialog
        cards = list(self.all_cards(scene))
        KartyListDialog(cards, parent).exec()
