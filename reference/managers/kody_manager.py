"""
kody_manager.py - KodyManager (baza wzorcowa kodow procesu).

CRUD + wyszukiwanie po Code_process (unikalny).
Walidacja danych NIE jest tutaj - to rola walidatora (validators/).
"""
from modules.reference.database import ReferenceDB

TABLE = "kody_operacyjne"

# Kolejnosc kolumn - zgodnie z Tabele.xlsx (Code proces).
FIELDS = (
    "code_process", "name_proces",
)


class KodyManager:
    """Zarzadza kodami operacyjnymi w bazie wzorcowej."""

    def __init__(self, db=None):
        self.db = db if db is not None else ReferenceDB("kody")

    # --- tworzenie / odczyt / aktualizacja / usuwanie ---

    def create(self, data):
        """Dodaje kod. data: dict wg FIELDS. Zwraca id wiersza."""
        fields = [f for f in FIELDS if f in data]
        sql = "INSERT INTO %s (%s) VALUES (%s)" % (
            TABLE,
            ", ".join(fields),
            ", ".join("?" for _ in fields),
        )
        return self.db.execute(sql, [data[f] for f in fields])

    def get(self, code_process):
        """Pobiera kod po Code_process lub None."""
        return self.db.fetch_one(
            "SELECT * FROM %s WHERE code_process = ?" % TABLE, (code_process,)
        )

    def get_by_row_id(self, row_id):
        return self.db.fetch_one("SELECT * FROM %s WHERE id = ?" % TABLE, (row_id,))

    def list_all(self):
        return self.db.fetch_all("SELECT * FROM %s ORDER BY code_process" % TABLE)

    def update(self, code_process, data):
        """Aktualizuje kod po Code_process. Zwraca liczbe zmienionych wierszy."""
        fields = [f for f in FIELDS if f in data]
        if not fields:
            return 0
        set_sql = ", ".join("%s = ?" % f for f in fields)
        cur = self.db.execute(
            "UPDATE %s SET %s WHERE code_process = ?" % (TABLE, set_sql),
            [data[f] for f in fields] + [code_process],
        )
        return cur

    def delete(self, code_process):
        """Usuwa kod po Code_process. Zwraca liczbe usunietych wierszy."""
        return self.db.execute(
            "DELETE FROM %s WHERE code_process = ?" % TABLE, (code_process,)
        )

    # --- wyszukiwanie (autouzupelnianie formularzy) ---

    def search(self, text, limit=20):
        """Szuka po kodzie/nazwie procesu (fragment)."""
        like = "%" + text + "%"
        return self.db.fetch_all(
            "SELECT * FROM %s WHERE code_process LIKE ? OR name_proces LIKE ? "
            "ORDER BY code_process LIMIT ?" % TABLE,
            (like, like, limit),
        )

    def count(self):
        row = self.db.fetch_one("SELECT COUNT(*) AS n FROM %s" % TABLE)
        return row["n"] if row else 0
