"""
card_history.py - Generowanie wpisow Timeline karty.

Logika dopisywania do `card.history_text` zostala wydzielona z CardItem,
aby klasa karty pozostala lekka (odciążenie obiektów: karta przechowuje
tylko dane + serializacje, a produkcja wpisow lezy w managerze).
Funkcje przyjmuja karte jako pierwszy argument i operuja na jej atrybutach.
"""

from datetime import datetime


def init_timeline(card):
    """Pierwszy wpis (URUCHOMIONO), jesli Timeline karty jest pusty."""
    if card.history_text:
        return
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    text_items = getattr(card, "text_items", [])
    main_num = text_items[2].toPlainText() if len(text_items) > 2 else "?"
    ser_num = text_items[3].toPlainText() if len(text_items) > 3 else "?"
    szt_num = text_items[4].toPlainText() if len(text_items) > 4 else "?"
    card.history_text += (
        f"{date_str}_{time_str}             URUCHOMIONO: {main_num}, ser. {ser_num}, szt. {szt_num}\n"
    )
    # Data uruchomienia nowej karty - automatycznie z wpisu TIME LINE
    # (pole 'Uruchom' w edytorze karty, card.uruchom).
    card.uruchom = date_str


def add_position_history(card, title_text_left, header_line1, header_line2,
                         header_line2a, header_line3, header_line4,
                         title_text_right1, position):
    """Wpis o zmianie pozycji (W produkcji / W kolejce)."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    table_changed = (title_text_left != card._last_table_title)
    column_changed = (header_line1 != card._last_column_header)
    position_changed = (position != card._last_position)

    if not position_changed and not table_changed and not column_changed:
        return

    if title_text_right1.strip() == "#":
        card.history_text += f"{date_str}_{time_str}   {title_text_left}\n"
        card._last_table_title = title_text_left
        card._last_column_header = header_line1
        card._last_position = position
        return

    if header_line4.strip() == "#":
        card.history_text += f"{date_str}_{time_str}   {title_text_left}, {header_line1}\n"
        card._last_table_title = title_text_left
        card._last_column_header = header_line1
        card._last_position = position
        return

    if position == 1:
        card.history_text += f"{date_str}_{time_str}        {title_text_left}, {header_line1},   W produkcji\n"
        card.history_text += f"                        {header_line2a}, {header_line3}, {header_line2}\n"
    else:
        card.history_text += f"{date_str}_{time_str}        {title_text_left}, {header_line1},   W kolejce: {position}\n"

    card._last_table_title = title_text_left
    card._last_column_header = header_line1
    card._last_position = position


def add_note_history(card, note_text):
    """Wpis Notes do Timeline karty."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    card.history_text += f"{date_str}_{time_str}   Notes:    {note_text}\n"
