"""
schema.py - Schematy 4 baz wzorcowych (na podstawie Tabele.xlsx).

Tabele:
  - pracownicy.db        -> table: pracownicy            (ID_worker unikalny)
  - maszyny.db           -> table: maszyny               (ID_machine unikalny)
  - stanowiska.db        -> table: stanowiska            (ID_position unikalny)
  - kody.db              -> table: kody_operacyjne       (Code_process unikalny)

Relacje (powiazania):
  pracownik  --(Allocation)-->  gniazdo/produkcja (allocation / stanowisko)
  maszyna    --(Code_proces)--> kody_operacyjne (Code_process)
  stanowisko --(Code_proces)--> kody_operacyjne (Code_process)
  kartomarszruta (operational process) zapisywana w KARCIE, nie w bazach.
"""
import os

# Lokalizacja baz wzorcowych (jedno miejsce).
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "assets", "data",
)

# Nazwa bazy -> sciezka pliku .db
DATABASES = {
    "pracownicy": "pracownicy.db",
    "maszyny": "maszyny.db",
    "stanowiska": "stanowiska.db",
    "kody": "kody.db",
}


def db_path(name):
    """Zwraca pelna sciezke do pliku bazy wzorcowej wg nazwy."""
    return os.path.join(DATA_DIR, DATABASES[name])


# --- SQL schematow (CREATE TABLE IF NOT EXISTS) ---
SCHEMAS = {
    "pracownicy": """
        CREATE TABLE IF NOT EXISTS pracownicy (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            id_worker      TEXT    NOT NULL UNIQUE,
            worker_1name   TEXT    NOT NULL DEFAULT '',
            worker_2name   TEXT    NOT NULL DEFAULT '',
            nr_fon         TEXT    NOT NULL DEFAULT '',
            spec_worker    TEXT    NOT NULL DEFAULT '',
            allocation     TEXT    NOT NULL DEFAULT '',
            time_work      TEXT    NOT NULL DEFAULT ''
        )
    """,
    "maszyny": """
        CREATE TABLE IF NOT EXISTS maszyny (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            id_machine  TEXT    NOT NULL UNIQUE,
            name_machine TEXT   NOT NULL DEFAULT '',
            name_proces TEXT    NOT NULL DEFAULT '',
            allocation  TEXT    NOT NULL DEFAULT ''
        )
    """,
    "stanowiska": """
        CREATE TABLE IF NOT EXISTS stanowiska (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            id_position TEXT    NOT NULL UNIQUE,
            code_proces TEXT    NOT NULL DEFAULT '',
            allocation  TEXT    NOT NULL DEFAULT ''
        )
    """,
    "kody": """
        CREATE TABLE IF NOT EXISTS kody_operacyjne (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            code_process  TEXT    NOT NULL UNIQUE,
            name_proces   TEXT    NOT NULL DEFAULT ''
        )
    """,
}


def init_db(name):
    """Tworzy plik bazy wzorcowej (jesli nie istnieje) i tabelu wg schematu."""
    import sqlite3
    path = db_path(name)
    os.makedirs(DATA_DIR, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute(SCHEMAS[name])
        _migrate(conn, name)
        conn.commit()
    return path


def _migrate(conn, name):
    """Dogania nowe kolumny w istniejacych bazach (ALTER TABLE).

    Niesie dane: production_line -> allocation (nie usuwa starych kolumn,
    managery czytaja/pisza wg FIELDS, wiec pozostale kolumny nie przeszkadzaja).
    """
    # Kolumna name_machine w maszynach (dodana pozniej).
    if name == "maszyny":
        cols = {r[1] for r in conn.execute("PRAGMA table_info(maszyny)").fetchall()}
        if "name_machine" not in cols:
            conn.execute("ALTER TABLE maszyny ADD COLUMN name_machine TEXT NOT NULL DEFAULT ''")
        if "allocation" not in cols and "production_line" in cols:
            conn.execute("ALTER TABLE maszyny ADD COLUMN allocation TEXT NOT NULL DEFAULT ''")
            conn.execute("UPDATE maszyny SET allocation = production_line")
    # Kolumna allocation w stanowiskach (zamiast production_line).
    if name == "stanowiska":
        cols = {r[1] for r in conn.execute("PRAGMA table_info(stanowiska)").fetchall()}
        if "allocation" not in cols and "production_line" in cols:
            conn.execute("ALTER TABLE stanowiska ADD COLUMN allocation TEXT NOT NULL DEFAULT ''")
            conn.execute("UPDATE stanowiska SET allocation = production_line")


def init_all():
    """Tworzy wszystkie bazy wzorcowe. Zwraca dict nazwa -> sciezka."""
    return {name: init_db(name) for name in DATABASES}
