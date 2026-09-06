-- schema.sql - relacyjny format projektu (Faza 5).
-- Rownolegly do JSON: StorageManager eksportuje/importuje scene do SQLite.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS scene_meta (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    main_notes      TEXT,
    notes_data      TEXT,   -- JSON: lista notatek
    kanban_icon_pos TEXT    -- JSON: {"x":..,"y":..} lub NULL
);

CREATE TABLE IF NOT EXISTS tables (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    uid               TEXT,      -- stabilny identyfikator tabeli (tabela.id)
    sort              INTEGER,   -- pozycja na liscie sceny (kolejnosc serializacji)
    pos_x             REAL,
    pos_y             REAL,
    is_base_table     INTEGER,   -- 0/1
    title_color_index INTEGER,
    title_left        TEXT,
    title_right       TEXT,
    title_right1      TEXT,
    extra_rows        INTEGER,
    body_height       REAL,
    kanban_text       TEXT,      -- tylko tabela bazowa
    kanban_text_x     REAL
);

CREATE TABLE IF NOT EXISTS columns (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    uid                  TEXT,
    table_id             INTEGER NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
    sort                 INTEGER,
    header1              TEXT,
    header2              TEXT,
    header2a             TEXT,
    header3              TEXT,
    header4              TEXT,
    notes                TEXT,
    header_overlay_index INTEGER,
    body_overlay_index   INTEGER,
    linked_to_right      INTEGER,   -- 0/1
    linked_from_left     INTEGER    -- 0/1
);

CREATE TABLE IF NOT EXISTS cards (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    uid                  TEXT,
    column_id            INTEGER NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
    sort                 INTEGER,
    texts                TEXT,    -- JSON: lista tekstow karty
    color_index          INTEGER,
    font_index           INTEGER,
    status_index         INTEGER,
    overlay_index        INTEGER,
    klient_overlay_index INTEGER,
    note_text            TEXT,
    history_text         TEXT,
    timeline_encrypted   INTEGER  -- 0/1
);

CREATE TABLE IF NOT EXISTS connections (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    table1_uid        TEXT,       -- uid tabeli zrodlowej
    table2_uid        TEXT,       -- uid tabeli docelowej
    source_anchor_id  INTEGER,
    target_anchor_id  INTEGER,
    waypoints         TEXT        -- JSON: [{x,y}, ...]
);

CREATE INDEX IF NOT EXISTS idx_columns_table  ON columns(table_id);
CREATE INDEX IF NOT EXISTS idx_cards_column   ON cards(column_id);
CREATE INDEX IF NOT EXISTS idx_connections_t1 ON connections(table1_uid);
CREATE INDEX IF NOT EXISTS idx_connections_t2 ON connections(table2_uid);
