"""
export_excel.py - Plugin do eksportu danych do Excel

Moduł ładowany dynamicznie na żądanie użytkownika.
"""

import re
import os
from datetime import datetime

from PyQt6.QtWidgets import QMessageBox, QFileDialog

try:
    from openpyxl import Workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    Workbook = None
    OPENPYXL_AVAILABLE = False


def is_available():
    return OPENPYXL_AVAILABLE


def _extract_start_datetime_for_production(history_text):
    if not history_text:
        return ""
    matches = re.findall(r"(\d{4}-\d{2}-\d{2}) _ (\d{2}:\d{2}).*W produkcji", history_text)
    if not matches:
        return ""
    date_str, time_str = matches[-1]
    return f"{date_str} {time_str}"


def export_to_excel(scene, save_folder=None):
    if not OPENPYXL_AVAILABLE:
        QMessageBox.critical(None, "Brak biblioteki",
            "Brakuje biblioteki 'openpyxl'.\nZainstaluj: pip install openpyxl")
        return False

    kanban_text = scene.get_kanban_text() if hasattr(scene, 'get_kanban_text') else "Kanban"
    date_str = datetime.now().strftime("%Y-%m-%d")
    file_name = f"{kanban_text}_Karty_{date_str}.xlsx"

    start_path = os.path.join(save_folder or "", file_name)
    file_path, _ = QFileDialog.getSaveFileName(None, "Zapisz do Excela", start_path, "Excel Files (*.xlsx)")

    if not file_path:
        return False

    rows = []
    for table in scene.tables:
        grupa = table.title_text_left.toPlainText() if hasattr(table, "title_text_left") else ""

        for col in table.columns:
            operacja = col.header_line1.toPlainText() if hasattr(col, "header_line1") else ""
            operator = col.header_line2.toPlainText() if hasattr(col, "header_line2") else ""

            for idx, card in enumerate(col.cards):
                position = idx + 1
                main_num = card.text_items[2].toPlainText() if len(card.text_items) > 2 else ""
                detal = card.text_items[1].toPlainText() if len(card.text_items) > 1 else ""
                ser_num = card.text_items[3].toPlainText() if len(card.text_items) > 3 else ""
                szt_num = card.text_items[4].toPlainText() if len(card.text_items) > 4 else ""

                status = "W PRODUKCJI" if position == 1 else "Czeka"
                data_start = _extract_start_datetime_for_production(card.history_text) if position == 1 else ""

                status_i = ""
                if getattr(card, "overlay_index", -1) == 0:
                    status_i = "PILNE"
                elif getattr(card, "status_index", -1) == 2:
                    status_i = "Wstrzymane"

                rows.append({
                    "Cecha": main_num,
                    "Detal": detal,
                    "Seria": ser_num,
                    "Sztukl": szt_num,
                    "Grupa": grupa,
                    "Operacja": operacja,
                    "Status": status,
                    "Data rozpoczecia": data_start,
                    "Szac.czas.ukon.": "",
                    "Operator": operator,
                    "StatusI": status_i,
                    "Uwagr": "",
                })

    rows.sort(key=lambda r: (r["Cecha"] or "").upper())

    wb = Workbook()
    ws = wb.active
    ws.title = "Karty"

    headers = ["Cecha", "Detal", "Seria", "Sztukl", "Grupa", "Operacja",
               "Status", "Data rozpoczecia", "Szac.czas.ukon.", "Operator", "StatusI", "Uwagr"]
    ws.append(headers)

    for r in rows:
        ws.append([r[h] for h in headers])

    try:
        wb.save(file_path)
        QMessageBox.information(None, "Sukces", f"Zapisano Excel: {file_path}")
        return True
    except Exception as e:
        QMessageBox.critical(None, "Błąd", f"Nie udało się zapisać Excela: {e}")
        return False


PLUGIN_NAME = "Export do Excel"
PLUGIN_DESCRIPTION = "Eksportuje dane kart Kanban do pliku Excel (.xlsx)"
PLUGIN_VERSION = "1.0.0"
PLUGIN_REQUIRES = ["openpyxl"]


def get_info():
    return {
        "name": PLUGIN_NAME,
        "description": PLUGIN_DESCRIPTION,
        "version": PLUGIN_VERSION,
        "available": OPENPYXL_AVAILABLE,
        "requires": PLUGIN_REQUIRES,
    }


def execute(scene, **kwargs):
    save_folder = kwargs.get("save_folder", None)
    return export_to_excel(scene, save_folder)
