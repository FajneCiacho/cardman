"""
walidator_pracownika.py - WalidatorPracownika (etap 1: tylko sprawdzanie).

Sprawdza poprawnosc danych pracownika wpisywanych w formularzu:
  - ID_worker jest wymagany i niepusty,
  - imie i nazwisko sa wymagane (tylko litery + my\u017cnik),
  - ID_worker jest unikalny (nie istnieje inny rekord o tym samym ID),
  - opcjonalne pola (nr_fon, spec, allocation) nie maja wymaganej dlugosci -
    sa dobrowolne, ale walidator sprawdza dlugosci graniczne,
  - Time_work (ilosc zmian pracy) - dopuszczalne wpisy: 1, 2, 3.

Nie zapisuje danych. Zwraca obiekt WynikWalidacji.
"""
import re

_NUM_PATTERN = re.compile(r"^[0-9]+$")
_NAME_PATTERN = re.compile(r"^[A-Za-z\u0104\u0106\u0118\u0141\u0143\u00d3\u015a\u0179\u017b\u00dc"
                           r"\u0105\u0107\u0119\u0142\u0144\u00f3\u015b\u017a\u017c\u00fc\u00f3\-']+$")


class WynikWalidacji:
    """Wynik walidacji: poprawne? + lista bledow (pole, komunikat)."""

    def __init__(self):
        self.bledy = []  # lista (nazwa_pola, komunikat)

    @property
    def poprawne(self):
        return not self.bledy

    def add(self, pole, komunikat):
        self.bledy.append((pole, komunikat))

    def __bool__(self):
        return self.poprawne

    def __str__(self):
        if self.poprawne:
            return "OK"
        return "; ".join("%s: %s" % b for b in self.bledy)


class WalidatorPracownika:
    """Sprawdza poprawnosc danych pracownika (etap 1)."""

    def __init__(self, manager):
        self.manager = manager

    def waliduj(self, data, pomin_unikalnosc=False):
        """Waliduje slownik danych pracownika. Zwraca WynikWalidacji."""
        w = WynikWalidacji()

        id_worker = (data.get("id_worker") or "").strip()
        if not id_worker:
            w.add("id_worker", "ID_worker jest wymagany")
        elif not _NUM_PATTERN.match(id_worker):
            w.add("id_worker", "ID_worker musi zawierac tylko cyfry")

        imie = (data.get("worker_1name") or "").strip()
        if not imie:
            w.add("worker_1name", "Imie jest wymagane")
        elif not _NAME_PATTERN.match(imie):
            w.add("worker_1name", "Imie zawiera niedozwolone znaki")

        nazwisko = (data.get("worker_2name") or "").strip()
        if not nazwisko:
            w.add("worker_2name", "Nazwisko jest wymagane")
        elif not _NAME_PATTERN.match(nazwisko):
            w.add("worker_2name", "Nazwisko zawiera niedozwolone znaki")

        if not pomin_unikalnosc and id_worker:
            istniejacy = self.manager.get(id_worker)
            if istniejacy is not None:
                w.add("id_worker", "Pracownik o ID %s juz istnieje" % id_worker)

        # Pola opcjonalne - tylko graniczne dlugosci.
        dlugosci = {
            "nr_fon": 30,
            "spec_worker": 60,
            "allocation": 60,
        }
        for pole, max_len in dlugosci.items():
            val = (data.get(pole) or "").strip()
            if len(val) > max_len:
                w.add(pole, "%s jest za dlugie (max %d znakow)" % (pole, max_len))

        # Time_work - ilosc zmian pracy: tylko 1, 2, 3.
        time_work = (data.get("time_work") or "").strip()
        if time_work and time_work not in ("1", "2", "3"):
            w.add("time_work", "Time_work musi byc 1, 2 lub 3")

        return w
