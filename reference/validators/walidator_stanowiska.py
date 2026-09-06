"""
walidator_stanowiska.py - WalidatorStanowiska (etap 1: tylko sprawdzanie).

Sprawdza poprawnosc danych stanowiska pracy wpisywanych w formularzu:
  - ID_position jest wymagany i niepusty, tylko cyfry,
  - ID_position jest unikalny (nie istnieje inny rekord o tym samym ID),
  - Code_proces (opcjonalne) - jesli podane, tylko cyfry,
  - Allocation (opcjonalne) - graniczna dlugosc.

Nie zapisuje danych. Zwraca obiekt WynikWalidacji.
"""
import re

from modules.reference.validators.walidator_pracownika import WynikWalidacji

_NUM_PATTERN = re.compile(r"^[0-9]+$")


class WalidatorStanowiska:
    """Sprawdza poprawnosc danych stanowiska pracy (etap 1)."""

    def __init__(self, manager):
        self.manager = manager

    def waliduj(self, data, pomin_unikalnosc=False):
        w = WynikWalidacji()

        id_position = (data.get("id_position") or "").strip()
        if not id_position:
            w.add("id_position", "ID_position jest wymagany")
        elif not _NUM_PATTERN.match(id_position):
            w.add("id_position", "ID_position musi zawierac tylko cyfry")

        if not pomin_unikalnosc and id_position:
            istniejace = self.manager.get(id_position)
            if istniejace is not None:
                w.add("id_position", "Stanowisko o ID %s juz istnieje" % id_position)

        code_proces = (data.get("code_proces") or "").strip()
        if code_proces and not _NUM_PATTERN.match(code_proces):
            w.add("code_proces", "Code_proces musi zawierac tylko cyfry")

        for pole, max_len in (("allocation", 60),):
            val = (data.get(pole) or "").strip()
            if len(val) > max_len:
                w.add(pole, "%s jest za dlugie (max %d znakow)" % (pole, max_len))

        return w
