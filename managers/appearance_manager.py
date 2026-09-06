"""
appearance_manager.py - Katalog wygladu kart, tabel i kolumn (Faza 3).

Odpowiedzialnosci:
- centralny katalog kolorow, nakladek, fontow, ikon statusu i overlays klienta,
- lookup (title_color, card_color, overlay_file, ...) - jedna zmiana zamiast wielu.

Katalogi odpowiadaja wartosciom RUNTIME obiektow (nie nieuzywanym stalom z config,
np. CARD_COLORS). Indeksy sa przechowywane w obiektach i serializowane bez zmian.
"""
from PyQt6.QtGui import QColor

from config import TITLE_COLORS, HEADER_OVERLAYS, BODY_OVERLAYS, OVERLAY_FILES


class AppearanceManager:
    """Centralny rejestr wygladu elementow Kanban."""

    def __init__(self):
        self.title_colors = list(TITLE_COLORS)
        self.header_overlays = list(HEADER_OVERLAYS)
        self.body_overlays = list(BODY_OVERLAYS)
        self.overlay_files = list(OVERLAY_FILES)
        # Katalogi RUNTIME (wartosci zgodne z obiektami, nie z config):
        self.status_icon_files = [
            "Produkcja.svg",
            "Wstrzymane.svg",
        ]
        self.klient_overlays = [""] + [f"GRUPA{i}.svg" for i in range(1, 9)]
        self.info_overlays = ["", "Nadzor.svg", "Poprawa.svg"]
        self.font_families = [
            "Huxley Titling",
            "Gill Sans MT Ext Condensed Bold",
            "Corporate",
        ]
        self.card_colors = [
            QColor("#F7E7DE"), QColor("#E0D9D3"), QColor("#EBD8C3"),
            QColor("#C4C4C4"), QColor("#CDDFEB"), QColor("#CCE6C8"),
        ]

    # --- lookup tytulow/kolumn/tabel ---

    def title_color(self, index):
        if not self.title_colors:
            return None
        return self.title_colors[index % len(self.title_colors)]

    def header_overlay_file(self, index):
        if not self.header_overlays:
            return ""
        return self.header_overlays[index % len(self.header_overlays)]

    def body_overlay_file(self, index):
        if not self.body_overlays:
            return ""
        return self.body_overlays[index % len(self.body_overlays)]

    # --- lookup kart ---

    def card_color(self, index):
        if not self.card_colors:
            return QColor("#F7E7DE")
        return self.card_colors[index % len(self.card_colors)]

    def overlay_file(self, index):
        if not self.overlay_files:
            return ""
        return self.overlay_files[index % len(self.overlay_files)]

    def status_icon_file(self, index):
        if not self.status_icon_files:
            return ""
        return self.status_icon_files[index % len(self.status_icon_files)]

    def klient_overlay_file(self, index):
        if not self.klient_overlays:
            return ""
        return self.klient_overlays[index % len(self.klient_overlays)]

    def info_overlay_file(self, index):
        if not self.info_overlays:
            return ""
        return self.info_overlays[index % len(self.info_overlays)]

    def font_family(self, index):
        if not self.font_families:
            return "Huxley Titling"
        return self.font_families[index % len(self.font_families)]
