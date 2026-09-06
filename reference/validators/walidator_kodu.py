"""
walidator_kodu.py - WalidatorKodu (etap 1: tylko sprawdzanie).

Sprawdza poprawnosc danych kodu operacyjnego wpisywanych w formularzu:
  - Code_process jest wymagany, niepusty, tylko cyfry,
  - Code_process jest unikalny (nie istnieje inny rekord o tym samym kodzie),
  - Name_proces (opcjonalne) - graniczna dlugosc.

Nie zapisuje danych. Zwraca obiekt WynikWalidacji.
"""
import re

_NUM_PATTERN = re.compile(r"^[0-9]+$")


class WalidatorKodu:
    """Sprawdza poprawnosc danych kodu operacyjnego (etap 1)."""

    def __init__(self, manager):
        self.manager = manager

    def waliduj(self, data, pomin_unikalnosc=False):
        from modules.reference.validators.walidator_pracownika import WynikWalidacji
        w = WynikWalidacji()

        code = (data.get("code_process") or "").strip()
        if not code:
            w.add("code_process", "Code_process jest wymagany")
        elif not _NUM_PATTERN.match(code):
            w.add("code_process", "Code_process musi zawierac tylko cyfry")

        if not pomin_unikalnosc and code:
            istniejacy = self.manager.get(code)
            if istniejacy is not None:
                w.add("code_process", "Kod %s juz istnieje" % code)

        name = (data.get("name_proces") or "").strip()
        if len(name) > 60:
            w.add("name_proces", "Name_proces jest za dlugie (max 60 znakow)")

        return w
