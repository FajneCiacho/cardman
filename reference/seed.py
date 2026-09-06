"""
seed.py - Przykladowe dane do 4 baz wzorcowych.

Uruchomienie:  python -m modules.reference.seed
Wypelnia assets/data/*.db przykladowymi danymi (do testowania formularzy
i raportow Excel). Istniejace rekordy o tych samych kluczach sa nadpisywane.
"""
from modules.reference.managers.pracownicy_manager import PracownicyManager
from modules.reference.managers.maszyny_manager import MaszynyManager
from modules.reference.managers.stanowiska_manager import StanowiskaManager
from modules.reference.managers.kody_manager import KodyManager
from modules.reference.database import ReferenceDB


PRACOWNICY = [
    {"id_worker": "40257", "worker_1name": "Jan", "worker_2name": "Kowalski",
     "nr_fon": "768432", "spec_worker": "Tokarz Manualny",
     "allocation": "Gniazdo Tokarek", "time_work": "1"},
    {"id_worker": "40258", "worker_1name": "Anna", "worker_2name": "Nowak",
     "nr_fon": "555123", "spec_worker": "Frezarka",
     "allocation": "Gniazdo Frezarek", "time_work": "1"},
    {"id_worker": "40259", "worker_1name": "Piotr", "worker_2name": "Wisniewski",
     "nr_fon": "555456", "spec_worker": "Operator CNC",
     "allocation": "Gniazdo CNC", "time_work": "2"},
    {"id_worker": "40260", "worker_1name": "Maria", "worker_2name": "Zielinska",
     "nr_fon": "555789", "spec_worker": "Szlifierz",
     "allocation": "Gniazdo Szlifowania", "time_work": "3"},
]


MASZYNY = [
    {"id_machine": "40-356", "name_machine": "Tokarka rewolwerowa R-5",
     "name_proces": "Toczenie manualne", "allocation": "Gniazdo Tokarek"},
    {"id_machine": "40-357", "name_machine": "Tokarka uniwersalna T-12",
     "name_proces": "Toczenie automatyczne", "allocation": "Gniazdo Tokarek"},
    {"id_machine": "41-102", "name_machine": "Frezarka pionowa F-3",
     "name_proces": "Frezowanie", "allocation": "Gniazdo Frezarek"},
    {"id_machine": "42-220", "name_machine": "Centrum CNC X-200",
     "name_proces": "Obrobka CNC", "allocation": "Gniazdo CNC"},
    {"id_machine": "43-001", "name_machine": "Szlifierka do plaszczyzn S-1",
     "name_proces": "Szlifowanie", "allocation": "Gniazdo Szlifowania"},
]


STANOWISKA = [
    {"id_position": "10658", "code_proces": "254", "allocation": "Gniazdo Tokarek"},
    {"id_position": "10659", "code_proces": "255", "allocation": "Gniazdo Tokarek"},
    {"id_position": "10710", "code_proces": "260", "allocation": "Gniazdo Frezarek"},
    {"id_position": "10800", "code_proces": "270", "allocation": "Gniazdo CNC"},
    {"id_position": "10901", "code_proces": "280", "allocation": "Gniazdo Szlifowania"},
]


KODY = [
    {"code_process": "254", "name_proces": "Toczenie manualne"},
    {"code_process": "255", "name_proces": "Toczenie automatyczne"},
    {"code_process": "260", "name_proces": "Frezowanie"},
    {"code_process": "270", "name_proces": "Obrobka CNC"},
    {"code_process": "280", "name_proces": "Szlifowanie"},
]


def _seed(manager, rows):
    for data in rows:
        key = None
        if "id_worker" in data:
            key = data["id_worker"]
        elif "id_machine" in data:
            key = data["id_machine"]
        elif "id_position" in data:
            key = data["id_position"]
        elif "code_process" in data:
            key = data["code_process"]
        if key is not None and manager.get(key) is not None:
            manager.update(key, data)
        else:
            manager.create(data)


def main():
    _seed(PracownicyManager(ReferenceDB("pracownicy")), PRACOWNICY)
    _seed(MaszynyManager(ReferenceDB("maszyny")), MASZYNY)
    _seed(StanowiskaManager(ReferenceDB("stanowiska")), STANOWISKA)
    _seed(KodyManager(ReferenceDB("kody")), KODY)

    for mgr in (PracownicyManager(ReferenceDB("pracownicy")),
                MaszynyManager(ReferenceDB("maszyny")),
                StanowiskaManager(ReferenceDB("stanowiska")),
                KodyManager(ReferenceDB("kody"))):
        print("%-12s -> %d rekordow" % (mgr.__class__.__name__, mgr.count()))


if __name__ == "__main__":
    main()
