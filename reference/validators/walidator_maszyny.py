"""
walidator_maszyny.py - WalidatorMaszyny (etap 1: tylko sprawdzanie).

Sprawdza poprawnosc danych maszyny wpisywanych w formularzu:
  - ID_machine jest wymagany i niepusty,
  - ID_machine jest unikalny (nie istnieje inny rekord o tym samym ID),
  - Name_proces / Allocation (opcjonalne) - graniczne dlugosci.

Nie zapisuje danych. Zwraca obiekt WynikWalidacji.
"""
from modules.reference.validators.walidator_pracownika import WynikWalidacji


class WalidatorMaszyny:
    """Sprawdza poprawnosc danych maszyny (etap 1)."""

    def __init__(self, manager):
        self.manager = manager

    def waliduj(self, data, pomin_unikalnosc=False):
        w = WynikWalidacji()

        id_machine = (data.get("id_machine") or "").strip()
        if not id_machine:
            w.add("id_machine", "ID_machine jest wymagany")

        if not pomin_unikalnosc and id_machine:
            istniejaca = self.manager.get(id_machine)
            if istniejaca is not None:
                w.add("id_machine", "Maszyna o ID %s juz istnieje" % id_machine)

        for pole, max_len in (("name_machine", 60), ("name_proces", 60),
                              ("allocation", 60)):
            val = (data.get(pole) or "").strip()
            if len(val) > max_len:
                w.add(pole, "%s jest za dlugie (max %d znakow)" % (pole, max_len))

        return w
