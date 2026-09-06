"""
config.py - Stałe konfiguracyjne aplikacji Kanban
"""

from PyQt6.QtGui import QColor

# === WYMIARY KART I KOLUMN ===
COLUMN_WIDTH = 430
CARD_W = 390
CARD_H = 150
CARD_GAP = 15
CARD_RADIUS = 10

# === WYMIARY TABELI ===
TABLE_TITLE_HEIGHT = 55
COLUMN_HEADER_HEIGHT = 45
COLUMN_BODY_HEIGHT = 200
BODY_STEP = 170
BASE_COLUMNS = 2

# === MENU ===
MENU_WIDTH = 180
MENU_BORDER = 2

# === KOLORY ===
COLOR_ACTIVE = "#733C08"
COLOR_DISABLED = "#BFAD9D"
COLOR_MENU_BG = "#F0DCC9"
COLOR_BORDER = "#00008F"
COLOR_TABLE_BORDER = "#002D57"
COLOR_COLUMN_HEADER = "#002D57"
ZONE_COLOR = "#00747A"
ZONE_WIDTH = 5

TITLE_COLORS = [
    "#002D57", "#008C87", "#005FB8", "#1B8703", "#DE0000", 
    "#FF4800", "#DE9400", "#9C0097", "#6900E0", "#C4067B", "#545151"
]

# === OVERLAY ===
HEADER_OVERLAYS = [
    "kolor1.svg", "kolor1A.svg", "kolor2.svg", "kolor2A.svg",
    "kolor3.svg", "kolor3A.svg", "kolor4.svg", "kolor4A.svg",
    "kolor5.svg", "kolor5A.svg", "kolor6.svg", "kolor6A.svg",
    "kolor7.svg", "kolor7A.svg", "kolor8.svg"
]
BODY_OVERLAYS = ["", "slaid1.svg", "slaid2.svg"]

# === IKONY ===
INFO_ICON_SIZE = 16
INFO_MARGIN = 5
CORNER_RADIUS = 2

# === DRAG & DROP ===
DRAG_START_DISTANCE = CARD_H * 0.60  # 60px dla CARD_H=150

# === PLIKI ===
AUTOSAVE_FILE = "Tabele_W_text_(Autozapis).json"

# === OVERLAY KARTY ===
# Priorytet (Overlay_files): domyslnie bez nakladki, potem Opis.svg.
OVERLAY_NAMES = ["", "Opis"]
OVERLAY_FILES = ["", "Opis.svg"]

# === STATUSY ===
STATUS_ICON_NAMES = ["Produkcja", "Wstrzymane"]

# === KOLORY KART ===
CARD_COLORS = [
     QColor("#E6DBC9"), QColor("#D0CBC5"), QColor("#CFC3B5"),
     QColor("#EDDBAB"), QColor("#D8DFB5"), QColor("#A8A6A6"),
]

