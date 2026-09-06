"""
form_style.py - Jeden styl graficzny dla wszystkich formularzy (Faza 7).

Uzgodniona kolorystyka:
  - globalne tlo i obramowanie:  #D7EDF2
  - przyciski wypukle:           #29B3D9

Wszystkie formularze (karta, kolumna, tabela, notes, obraz, timeline,
search, save, load_excel) uzywaja funkcji z tego modulu - dzieki temu
styl jest jednolity, a zmiana kolorow robi sie w jednym miejscu.
"""
from PyQt6.QtWidgets import QDialog


# --- Kolory globalne ---
GLOBAL_BG = "#D7EDF2"
GLOBAL_BORDER = "#D7EDF2"
BUTTON_BG = "#29B3D9"
BUTTON_BORDER = "#1E9CC0"
BUTTON_BG_TOP = "#4CC4E8"
BUTTON_BG_BOTTOM = "#29B3D9"
BUTTON_BG_PRESSED = "#1E9CC0"
TEXT_COLOR = "#10324A"
FIELD_BG = "#FFFFFF"
FIELD_BORDER = "#9FC7D6"


def dialog_stylesheet():
    """Style dla calego okna dialogowego (tlo globalne)."""
    return f"""
        QDialog {{
            background-color: {GLOBAL_BG};
            border: 1px solid {GLOBAL_BORDER};
        }}
        QLabel {{
            color: {TEXT_COLOR};
            background: transparent;
            font-size: 8pt;
            font-weight: bold;
        }}
        QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
            background-color: {FIELD_BG};
            border: 1px solid {FIELD_BORDER};
            border-radius: 4px;
            color: {TEXT_COLOR};
            padding: 2px 4px;
            selection-background-color: {BUTTON_BG};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid {BUTTON_BG};
        }}
    """


def button_stylesheet(size="normal"):
    """Wypukly przycisk (gradient) w kolorze #29B3D9."""
    pad = "4px 12px" if size == "normal" else "2px 6px"
    radius = "7px" if size == "normal" else "5px"
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 {BUTTON_BG_TOP},
                                        stop:1 {BUTTON_BG_BOTTOM});
            border: 1px solid {BUTTON_BORDER};
            border-radius: {radius};
            padding: {pad};
            color: #FFFFFF;
            font-weight: bold;
            font-size: 8pt;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                        stop:0 #5AD0F0,
                                        stop:1 #37BCE0);
        }}
        QPushButton:pressed {{
            background-color: {BUTTON_BG_PRESSED};
            border: 2px solid {GLOBAL_BG};
        }}
        QPushButton:disabled {{
            background: #A9C9D6;
            border: 1px solid #8FB6C4;
            color: #E8F4F8;
        }}
    """


def section_line_stylesheet():
    """Linia pod sekcja (np. 'Oznaczenia Karty')."""
    return f"""
        QFrame {{
            background-color: {BUTTON_BG};
            border: none;
            max-height: 1px;
        }}
    """


def apply_dialog_style(dialog, button_size="normal"):
    """Naklada globalny styl na dialog i wszystkie jego przyciski.

    Wywolac po zbudowaniu widgetow (na koncu __init__).
    """
    from PyQt6.QtWidgets import QPushButton, QFrame
    if isinstance(dialog, QDialog):
        dialog.setStyleSheet(dialog_stylesheet())
    for btn in dialog.findChildren(QPushButton):
        btn.setStyleSheet(button_stylesheet(button_size))
    for frame in dialog.findChildren(QFrame):
        if frame.maximumHeight() <= 3 or str(frame.objectName()).startswith("line"):
            frame.setStyleSheet(section_line_stylesheet())


def style_button(btn, size="normal"):
    """Stylizuje pojedynczy przycisk (wypukly, #29B3D9)."""
    btn.setStyleSheet(button_stylesheet(size))
    return btn


def make_section_line():
    """Pozioma linia sekcji (HL2px w kolorze tla)."""
    from PyQt6.QtWidgets import QFrame
    from PyQt6.QtCore import Qt
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    line.setStyleSheet(section_line_stylesheet())
    line.setMaximumHeight(2)
    return line
