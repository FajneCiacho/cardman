"""
utils.py - Funkcje pomocnicze
"""

import sys
import os
import uuid


def new_id(prefix=""):
    """Generuje unikalny identyfikator (karty/tabeli/kolumny)."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def resource_path(relative_path):
    """
    Zwraca ścieżkę do zasobu (obsługuje PyInstaller).
    
    Args:
        relative_path: Względna ścieżka do zasobu
        
    Returns:
        str: Absolutna ścieżka do zasobu
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if relative_path.lower().endswith('.svg'):
        return os.path.join(base_path, "assets/svg", relative_path)
    return os.path.join(base_path, relative_path)


def card_label(card):
    """
    Generuje etykietę karty do logowania.
    
    Args:
        card: Obiekt CardItem
        
    Returns:
        str: Etykieta karty (Detal / Seria)
    """
    main = card.text_items[2].toPlainText().strip() if len(card.text_items) > 2 else ""
    ser = card.text_items[3].toPlainText().strip() if len(card.text_items) > 3 else ""
    if main or ser:
        return f"{main or '?'} / {ser or '?'}"
    return "Karta"
