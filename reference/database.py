"""
database.py - Lekka warstwa dostepu do pojedynczej bazy wzorcowej.

ReferenceDB otwiera konkretny plik .db (pracownicy/maszyny/kody) i gwarantuje,
ze tabela istnieje. Managery korzystaja z tej klasy do zapytan SQL.
"""
import sqlite3

from modules.reference import schema


class ReferenceDB:
    """Dostep do jednej bazy wzorcowej (pracownicy / maszyny / kody)."""

    def __init__(self, name):
        if name not in schema.DATABASES:
            raise ValueError("Nieznana baza wzorcowa: %r (dostepne: %s)" % (
                name, ", ".join(sorted(schema.DATABASES))))
        self.name = name
        schema.init_db(name)  # gwarantuje istnienie pliku + tabeli

    # --- polaczenie ---

    def connect(self):
        conn = sqlite3.connect(schema.db_path(self.name))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # --- pomocnicze ---

    def fetch_all(self, sql, params=()):
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def fetch_one(self, sql, params=()):
        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row is not None else None

    def execute(self, sql, params=()):
        """Wykonuje INSERT/UPDATE/DELETE. Zwraca id ostatniego wiersza."""
        with self.connect() as conn:
            cur = conn.execute(sql, params)
            conn.commit()
            return cur.lastrowid
