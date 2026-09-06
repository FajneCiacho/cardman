"""
stanowiska_manager.py - StanowiskaManager (baza wzorcowa stanowisk pracy).

CRUD + wyszukiwanie po ID_position (unikalny).
Walidacja danych NIE jest tutaj - to rola walidatora (validators/).
"""
from modules.reference.database import ReferenceDB

TABLE = "stanowiska"

# Kolejnosc kolumn - zgodnie z Tabele.xlsx (stanowiska, czesc tabeli obrabiarek).
FIELDS = (
    "id_position", "code_proces", "allocation",
)


class StanowiskaManager:
    """Zarzadza stanowiskami pracy w bazie wzorcowej."""

    def __init__(self, db=None):
        self.db = db if db is not None else ReferenceDB("stanowiska")

    # --- tworzenie / odczyt / aktualizacja / usuwanie ---

    def create(self, data):
        """Dodaje stanowisko. data: dict wg FIELDS. Zwraca id wiersza."""
        fields = [f for f in FIELDS if f in data]
        sql = "INSERT INTO %s (%s) VALUES (%s)" % (
            TABLE,
            ", ".join(fields),
            ", ".join("?" for _ in fields),
        )
        return self.db.execute(sql, [data[f] for f in fields])

    def get(self, position_id):
        """Pobiera stanowisko po ID_position lub None."""
        return self.db.fetch_one(
            "SELECT * FROM %s WHERE id_position = ?" % TABLE, (position_id,)
        )

    def get_by_row_id(self, row_id):
        return self.db.fetch_one("SELECT * FROM %s WHERE id = ?" % TABLE, (row_id,))

    def list_all(self):
        return self.db.fetch_all("SELECT * FROM %s ORDER BY id_position" % TABLE)

    def update(self, position_id, data):
        """Aktualizuje stanowisko po ID_position. Zwraca liczbe zmienionych wierszy."""
        fields = [f for f in FIELDS if f in data]
        if not fields:
            return 0
        set_sql = ", ".join("%s = ?" % f for f in fields)
        cur = self.db.execute(
            "UPDATE %s SET %s WHERE id_position = ?" % (TABLE, set_sql),
            [data[f] for f in fields] + [position_id],
        )
        return cur

    def delete(self, position_id):
        """Usuwa stanowisko po ID_position. Zwraca liczbe usunietych wierszy."""
        return self.db.execute(
            "DELETE FROM %s WHERE id_position = ?" % TABLE, (position_id,)
        )

    # --- wyszukiwanie (autouzupelnianie formularzy) ---

    def search(self, text, limit=20):
        """Szuka po numerze/przydziale (fragment)."""
        like = "%" + text + "%"
        return self.db.fetch_all(
            "SELECT * FROM %s WHERE id_position LIKE ? OR code_proces LIKE ? "
            "OR allocation LIKE ? ORDER BY id_position LIMIT ?" % TABLE,
            (like, like, like, limit),
        )

    def count(self):
        row = self.db.fetch_one("SELECT COUNT(*) AS n FROM %s" % TABLE)
        return row["n"] if row else 0
