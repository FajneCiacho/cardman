"""
pracownicy_manager.py - PracownicyManager (baza wzorcowa pracownikow).

CRUD + wyszukiwanie po ID_worker (nr ewidencyjny, unikalny).
Walidacja danych NIE jest tutaj - to rola walidatora (validators/).
"""
from modules.reference.database import ReferenceDB

TABLE = "pracownicy"

# Kolejnosc kolumn (id_worker, imie, nazwisko, nr_fon, ...) - zgodnie z Tabele.xlsx.
FIELDS = (
    "id_worker", "worker_1name", "worker_2name",
    "nr_fon", "spec_worker", "allocation", "time_work",
)


class PracownicyManager:
    """Zarzadza pracownikami w bazie wzorcowej."""

    def __init__(self, db=None):
        self.db = db if db is not None else ReferenceDB("pracownicy")

    # --- tworzenie / odczyt / aktualizacja / usuwanie ---

    def create(self, data):
        """Dodaje pracownika. data: dict wg FIELDS. Zwraca id wiersza."""
        fields = [f for f in FIELDS if f in data]
        sql = "INSERT INTO %s (%s) VALUES (%s)" % (
            TABLE,
            ", ".join(fields),
            ", ".join("?" for _ in fields),
        )
        return self.db.execute(sql, [data[f] for f in fields])

    def get(self, worker_id):
        """Pobiera pracownika po ID_worker (nr ewidencyjny) lub None."""
        return self.db.fetch_one(
            "SELECT * FROM %s WHERE id_worker = ?" % TABLE, (worker_id,)
        )

    def get_by_row_id(self, row_id):
        return self.db.fetch_one("SELECT * FROM %s WHERE id = ?" % TABLE, (row_id,))

    def list_all(self):
        return self.db.fetch_all("SELECT * FROM %s ORDER BY id_worker" % TABLE)

    def update(self, worker_id, data):
        """Aktualizuje pracownika po ID_worker. Zwraca liczbe zmienionych wierszy."""
        fields = [f for f in FIELDS if f in data]
        if not fields:
            return 0
        set_sql = ", ".join("%s = ?" % f for f in fields)
        cur = self.db.execute(
            "UPDATE %s SET %s WHERE id_worker = ?" % (TABLE, set_sql),
            [data[f] for f in fields] + [worker_id],
        )
        return cur

    def delete(self, worker_id):
        """Usuwa pracownika po ID_worker. Zwraca liczbe usunietych wierszy."""
        return self.db.execute("DELETE FROM %s WHERE id_worker = ?" % TABLE, (worker_id,))

    # --- wyszukiwanie (autouzupelnianie formularzy) ---

    def search(self, text, limit=20):
        """Szuka po imieniu/nazwisku/ID (fragment). Do podpowiedzi w formularzu."""
        like = "%" + text + "%"
        return self.db.fetch_all(
            "SELECT * FROM %s WHERE id_worker LIKE ? OR worker_1name LIKE ? "
            "OR worker_2name LIKE ? ORDER BY id_worker LIMIT ?" % TABLE,
            (like, like, like, limit),
        )

    def count(self):
        row = self.db.fetch_one("SELECT COUNT(*) AS n FROM %s" % TABLE)
        return row["n"] if row else 0
