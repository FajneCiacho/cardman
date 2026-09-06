"""
maszyny_manager.py - MaszynyManager (baza wzorcowa maszyn).

CRUD + wyszukiwanie po ID_machine (nr ewidencji, unikalny).
Walidacja danych NIE jest tutaj - to rola walidatora (validators/).
"""
from modules.reference.database import ReferenceDB

TABLE = "maszyny"

# Kolejnosc kolumn - zgodnie z Tabele.xlsx (maszyny, czesc tabeli obrabiarek).
FIELDS = (
    "id_machine", "name_machine", "name_proces", "allocation",
)


class MaszynyManager:
    """Zarzadza maszynami w bazie wzorcowej."""

    def __init__(self, db=None):
        self.db = db if db is not None else ReferenceDB("maszyny")

    # --- tworzenie / odczyt / aktualizacja / usuwanie ---

    def create(self, data):
        """Dodaje maszyne. data: dict wg FIELDS. Zwraca id wiersza."""
        fields = [f for f in FIELDS if f in data]
        sql = "INSERT INTO %s (%s) VALUES (%s)" % (
            TABLE,
            ", ".join(fields),
            ", ".join("?" for _ in fields),
        )
        return self.db.execute(sql, [data[f] for f in fields])

    def get(self, machine_id):
        """Pobiera maszyne po ID_machine (nr ewidencji) lub None."""
        return self.db.fetch_one(
            "SELECT * FROM %s WHERE id_machine = ?" % TABLE, (machine_id,)
        )

    def get_by_row_id(self, row_id):
        return self.db.fetch_one("SELECT * FROM %s WHERE id = ?" % TABLE, (row_id,))

    def list_all(self):
        return self.db.fetch_all("SELECT * FROM %s ORDER BY id_machine" % TABLE)

    def update(self, machine_id, data):
        """Aktualizuje maszyne po ID_machine. Zwraca liczbe zmienionych wierszy."""
        fields = [f for f in FIELDS if f in data]
        if not fields:
            return 0
        set_sql = ", ".join("%s = ?" % f for f in fields)
        cur = self.db.execute(
            "UPDATE %s SET %s WHERE id_machine = ?" % (TABLE, set_sql),
            [data[f] for f in fields] + [machine_id],
        )
        return cur

    def delete(self, machine_id):
        """Usuwa maszyne po ID_machine. Zwraca liczbe usunietych wierszy."""
        return self.db.execute(
            "DELETE FROM %s WHERE id_machine = ?" % TABLE, (machine_id,)
        )

    # --- wyszukiwanie (autouzupelnianie formularzy) ---

    def search(self, text, limit=20):
        """Szuka po numerze/nazwie maszyny/nazwie procesu/przydziale (fragment)."""
        like = "%" + text + "%"
        return self.db.fetch_all(
            "SELECT * FROM %s WHERE id_machine LIKE ? OR name_machine LIKE ? "
            "OR name_proces LIKE ? OR allocation LIKE ? "
            "ORDER BY id_machine LIMIT ?" % TABLE,
            (like, like, like, like, limit),
        )

    def count(self):
        row = self.db.fetch_one("SELECT COUNT(*) AS n FROM %s" % TABLE)
        return row["n"] if row else 0
