"""
export_manager.py - Eksport danych (Faza 3).

Odpowiedzialnosci:
- eksport do Excela (przez plugin export_excel),
- komunikaty o bledach/brakach biblioteki.

Przeniesione z KanbanScene._save_to_excel.
"""
from PyQt6.QtWidgets import QMessageBox


class ExportManager:
    """Jedno miejsce wywolywania eksportu danych."""

    def export_to_excel(self, scene):
        """Eksportuje karty do Excela. Zwraca bool (czy zapisano)."""
        try:
            from modules.plugins import export_excel
            if export_excel.is_available():
                return export_excel.export_to_excel(
                    scene,
                    getattr(scene, "save_folder", None) or getattr(scene, "config_folder", None),
                )
            QMessageBox.critical(
                None,
                "Brak biblioteki",
                "Brakuje biblioteki 'openpyxl'.\nZainstaluj: pip install openpyxl",
            )
            return False
        except ImportError:
            QMessageBox.critical(None, "Blad", "Nie mozna zaladowac pluginu export_excel")
            return False
