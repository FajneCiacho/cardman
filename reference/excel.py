"""
excel.py - Import/eksport baz wzorcowych do Excela (droga wprowadzania danych).

Przeplyw w pracy (jak w zakladzie):
  eksport raportu (szablon z kolumnami) -> uzupelniasz w Excelu ->
  import z powrotem do bazy. Nie wpisujesz recznie.

Konwencja arkusza:
  - wiersz 1 = naglowki (nazwy kolumn wg schematu, np. ID_worker),
  - kolejne wiersze = dane. Klucz (ID_worker / ID_machine / ID_position /
    Code_process) decyduje: rekord jest UPDATE'owany, jesli juz istnieje,
    albo dodawany, jesli go nie ma.
"""
import os

from openpyxl import Workbook, load_workbook

from modules.reference import schema

# Baza -> (nazwa arkusza, kolumna klucza, pola). Pola = nazwy kolumn SQL.
REGISTRY = {
    "pracownicy": {
        "arkusz": "Pracownicy",
        "klucz": "id_worker",
        "pola": ["id_worker", "worker_1name", "worker_2name", "nr_fon",
                 "spec_worker", "allocation", "time_work"],
    },
    "maszyny": {
        "arkusz": "Maszyny",
        "klucz": "id_machine",
        "pola": ["id_machine", "name_machine", "name_proces", "allocation"],
    },
    "stanowiska": {
        "arkusz": "Stanowiska",
        "klucz": "id_position",
        "pola": ["id_position", "code_proces", "allocation"],
    },
    "kody": {
        "arkusz": "Kody",
        "klucz": "code_process",
        "pola": ["code_process", "name_proces"],
    },
}


def _manager_for(name):
    """Zwraca managera dla bazy wzorcowej (wspolny interfejs CRUD)."""
    from modules.reference.managers.pracownicy_manager import PracownicyManager
    from modules.reference.managers.maszyny_manager import MaszynyManager
    from modules.reference.managers.stanowiska_manager import StanowiskaManager
    from modules.reference.managers.kody_manager import KodyManager
    return {
        "pracownicy": PracownicyManager,
        "maszyny": MaszynyManager,
        "stanowiska": StanowiskaManager,
        "kody": KodyManager,
    }[name]()


def export_report(name, path=None):
    """Eksportuje baze wzorcowa do pliku xlsx (szablon z kolumnami).

    Zwraca sciezke zapisanego pliku.
    """
    if name not in REGISTRY:
        raise ValueError("Nieznana baza wzorcowa: %r" % name)
    cfg = REGISTRY[name]
    mgr = _manager_for(name)

    wb = Workbook()
    ws = wb.active
    ws.title = cfg["arkusz"]
    ws.append(cfg["pola"])

    for row in mgr.list_all():
        ws.append([row.get(p, "") for p in cfg["pola"]])

    if path is None:
        path = os.path.join(schema.DATA_DIR, "raport_%s.xlsx" % name)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    wb.save(path)
    return path


def import_report(name, path):
    """Importuje dane z pliku xlsx do bazy wzorcowej (upsert wg klucza).

    Zwraca (dodane, zaktualizowane, bledy). Bledy to lista (wiersz, komunikat).
    """
    if name not in REGISTRY:
        raise ValueError("Nieznana baza wzorcowa: %r" % name)
    cfg = REGISTRY[name]
    mgr = _manager_for(name)

    wb = load_workbook(path, data_only=True)
    if cfg["arkusz"] not in wb.sheetnames:
        raise ValueError("Arkusza %r nie ma w pliku (mam: %s)" % (
            cfg["arkusz"], ", ".join(wb.sheetnames)))
    ws = wb[cfg["arkusz"]]

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return 0, 0, []
    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    col_idx = {h: i for i, h in enumerate(header)}

    dodane = 0
    zaktualizowane = 0
    bledy = []
    for rno, row in enumerate(rows[1:], start=2):
        if all(c is None or str(c).strip() == "" for c in row):
            continue  # pusta linia
        data = {}
        for pole in cfg["pola"]:
            if pole in col_idx:
                val = row[col_idx[pole]]
                data[pole] = "" if val is None else str(val).strip()

        klucz = data.get(cfg["klucz"], "")
        if not klucz:
            bledy.append((rno, "brak klucza %s" % cfg["klucz"]))
            continue

        try:
            if mgr.get(klucz) is not None:
                mgr.update(klucz, data)
                zaktualizowane += 1
            else:
                mgr.create(data)
                dodane += 1
        except Exception as exc:
            bledy.append((rno, str(exc)))

    return dodane, zaktualizowane, bledy
