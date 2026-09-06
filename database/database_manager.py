"""database_manager.py - relacyjny format projektu (Faza 5).

Mapuje slownik sceny (scene.serialize()) <-> tabele SQLite. Format jest
rownolegly do JSON: StorageManager eksportuje (save_project_db) i importuje
(load_project_db) scene przez wspolny interfejs slownika JSON, wiec scena
nie musi wiedziec o istnieniu SQLite.
"""
import json
import os
import sqlite3

from .models import CardRecord, ColumnRecord, ConnectionRecord, TableRecord

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


class DatabaseManager:
    """Eksport/import sceny do/z SQLite (bezlogiczna warstwa trwalosci)."""

    FORMAT_VERSION = 3

    def __init__(self, schema_path=None):
        self.schema_path = schema_path or SCHEMA_PATH

    # ------------------------------------------------------------------
    # Eksport (scene_data -> SQLite)
    # ------------------------------------------------------------------

    def export_scene(self, db_path, scene_data):
        """Zapisuje slownik sceny do bazy SQLite. Podnosi wyjatek przy bledzie."""
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            self._create_schema(conn)
            self._write_scene_meta(conn, scene_data)
            self._write_tables(conn, scene_data.get("tables", []))
            self._write_connections(conn, scene_data.get("connections", []),
                                    scene_data.get("tables", []))
            conn.commit()

    def _create_schema(self, conn):
        # Eksport nadpisuje projekt: usun ewentualne stare tabele z tego samego pliku.
        for name in ("connections", "cards", "columns", "tables", "scene_meta", "meta"):
            conn.execute("DROP TABLE IF EXISTS " + name)
        with open(self.schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

    def _write_scene_meta(self, conn, scene_data):
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('FORMAT_VERSION', ?)",
            (str(scene_data.get("FORMAT_VERSION", self.FORMAT_VERSION)),),
        )
        icon = scene_data.get("kanban_icon_pos")
        conn.execute(
            "INSERT OR REPLACE INTO scene_meta(id, main_notes, notes_data, kanban_icon_pos) "
            "VALUES(1, ?, ?, ?)",
            (
                scene_data.get("main_notes", ""),
                json.dumps(scene_data.get("notes_data", []), ensure_ascii=False),
                json.dumps(icon, ensure_ascii=False) if icon is not None else None,
            ),
        )

    def _write_tables(self, conn, tables_data):
        for ti, td in enumerate(tables_data):
            cur = conn.execute(
                "INSERT INTO tables(uid, sort, pos_x, pos_y, is_base_table, title_color_index, "
                "title_left, title_right, title_right1, extra_rows, body_height, "
                "kanban_text, kanban_text_x) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    td.get("id"),
                    ti,
                    td.get("pos_x", 0.0),
                    td.get("pos_y", 0.0),
                    int(bool(td.get("is_base_table", False))),
                    td.get("title_color_index", 0),
                    td.get("title_left", ""),
                    td.get("title_right", ""),
                    td.get("title_right1", ""),
                    td.get("extra_rows", 0),
                    td.get("body_height", 0.0),
                    td.get("kanban_text"),
                    td.get("kanban_text_x"),
                ),
            )
            self._write_columns(conn, cur.lastrowid, td.get("columns", []))

    def _write_columns(self, conn, table_db_id, columns_data):
        for ci, cd in enumerate(columns_data):
            cur = conn.execute(
                "INSERT INTO columns(uid, table_id, sort, header1, header2, header2a, header3, "
                "header4, notes, header_overlay_index, body_overlay_index, linked_to_right, "
                "linked_from_left) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    cd.get("id"),
                    table_db_id,
                    ci,
                    cd.get("header1", ""),
                    cd.get("header2", ""),
                    cd.get("header2a", ""),
                    cd.get("header3", ""),
                    cd.get("header4", ""),
                    cd.get("notes", ""),
                    cd.get("header_overlay_index", 0),
                    cd.get("body_overlay_index", 0),
                    int(bool(cd.get("linked_to_right", False))),
                    int(bool(cd.get("linked_from_left", False))),
                ),
            )
            self._write_cards(conn, cur.lastrowid, cd.get("cards", []))

    def _write_cards(self, conn, column_db_id, cards_data):
        for ci, card in enumerate(cards_data):
            conn.execute(
                "INSERT INTO cards(uid, column_id, sort, texts, color_index, font_index, "
                "status_index, overlay_index, klient_overlay_index, note_text, history_text, "
                "timeline_encrypted) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    card.get("id"),
                    column_db_id,
                    ci,
                    json.dumps(card.get("texts", []), ensure_ascii=False),
                    card.get("color_index", 0),
                    card.get("font_index", 0),
                    card.get("status_index", 0),
                    card.get("overlay_index", -1),
                    card.get("klient_overlay_index", 0),
                    card.get("note_text", ""),
                    card.get("history_text", ""),
                    int(bool(card.get("_timeline_encrypted", False))),
                ),
            )

    def _write_connections(self, conn, connections_data, tables_data):
        uids = [t.get("id") for t in tables_data]
        for row in connections_data:
            t1 = row.get("table1", -1)
            t2 = row.get("table2", -1)
            t1_uid = uids[t1] if 0 <= t1 < len(uids) else f"#{t1}"
            t2_uid = uids[t2] if 0 <= t2 < len(uids) else f"#{t2}"
            conn.execute(
                "INSERT INTO connections(table1_uid, table2_uid, source_anchor_id, "
                "target_anchor_id, waypoints) VALUES(?,?,?,?,?)",
                (
                    t1_uid,
                    t2_uid,
                    row.get("source_anchor_id"),
                    row.get("target_anchor_id"),
                    json.dumps(row.get("waypoints", []), ensure_ascii=False),
                ),
            )

    # ------------------------------------------------------------------
    # Import (SQLite -> scene_data)
    # ------------------------------------------------------------------

    def import_scene(self, db_path):
        """Wczytuje baze SQLite i zwraca slownik sceny (jak scene.serialize()).

        Podnosi ValueError, gdy plik nie jest projektem Cardman.
        """
        if not os.path.exists(db_path):
            raise ValueError("Brak pliku bazy: %s" % db_path)
        with sqlite3.connect(db_path) as conn:
            self._require_schema(conn)
            tables = self._read_tables(conn)
            columns = self._read_columns(conn)
            cards = self._read_cards(conn)
            connections = self._read_connections(conn, tables)
            meta = self._read_scene_meta(conn)
        return self._build_dict(tables, columns, cards, connections, meta)

    def _require_schema(self, conn):
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tables'"
        )
        if cur.fetchone() is None:
            raise ValueError("Plik nie jest projektem Cardman (brak tabel projektu).")

    def _read_scene_meta(self, conn):
        meta = {"main_notes": "", "notes_data": [], "kanban_icon_pos": None}
        try:
            cur = conn.execute(
                "SELECT main_notes, notes_data, kanban_icon_pos FROM scene_meta WHERE id=1"
            )
            row = cur.fetchone()
        except sqlite3.OperationalError:
            return meta
        if row:
            meta["main_notes"] = row[0] or ""
            meta["notes_data"] = self._load_json(row[1], [])
            meta["kanban_icon_pos"] = self._load_json(row[2], None)
        return meta

    def _read_tables(self, conn):
        cur = conn.execute(
            "SELECT id, uid, pos_x, pos_y, is_base_table, title_color_index, "
            "title_left, title_right, title_right1, extra_rows, body_height, "
            "kanban_text, kanban_text_x FROM tables ORDER BY sort"
        )
        return [self._row_to_table(r) for r in cur.fetchall()]

    def _read_columns(self, conn):
        """Zwraca {table_db_id: [ColumnRecord, ...]}."""
        cur = conn.execute(
            "SELECT id, table_id, uid, header1, header2, header2a, header3, header4, "
            "notes, header_overlay_index, body_overlay_index, linked_to_right, "
            "linked_from_left FROM columns ORDER BY table_id, sort"
        )
        grouped = {}
        for r in cur.fetchall():
            grouped.setdefault(r[1], []).append(ColumnRecord(
                uid=r[2],
                db_id=r[0],
                header1=r[3] or "",
                header2=r[4] or "",
                header2a=r[5] or "",
                header3=r[6] or "",
                header4=r[7] or "",
                notes=r[8] or "",
                header_overlay_index=r[9],
                body_overlay_index=r[10],
                linked_to_right=bool(r[11]),
                linked_from_left=bool(r[12]),
            ))
        return grouped

    def _read_cards(self, conn):
        """Zwraca {column_db_id: [CardRecord, ...]}."""
        cur = conn.execute(
            "SELECT id, column_id, uid, texts, color_index, font_index, status_index, "
            "overlay_index, klient_overlay_index, note_text, history_text, "
            "timeline_encrypted FROM cards ORDER BY column_id, sort"
        )
        grouped = {}
        for r in cur.fetchall():
            grouped.setdefault(r[1], []).append(CardRecord(
                uid=r[2],
                texts=self._load_json(r[3], []),
                color_index=r[4],
                font_index=r[5],
                status_index=r[6],
                overlay_index=r[7],
                klient_overlay_index=r[8],
                note_text=r[9] or "",
                history_text=r[10] or "",
                timeline_encrypted=bool(r[11]),
            ))
        return grouped

    def _read_connections(self, conn, tables):
        uid_to_index = {}
        for i, rec in enumerate(tables):
            key = rec["uid"] if rec["uid"] is not None else "#%d" % i
            uid_to_index[key] = i
        cur = conn.execute(
            "SELECT table1_uid, table2_uid, source_anchor_id, target_anchor_id, "
            "waypoints FROM connections"
        )
        connections = []
        for table1_uid, table2_uid, src, tgt, waypoints in cur.fetchall():
            t1 = self._uid_to_index(uid_to_index, table1_uid)
            t2 = self._uid_to_index(uid_to_index, table2_uid)
            if t1 < 0 or t2 < 0:
                continue
            connections.append({
                "table1": t1,
                "table2": t2,
                "source_anchor_id": src,
                "target_anchor_id": tgt,
                "waypoints": self._load_json(waypoints, []),
            })
        return connections

    def _build_dict(self, tables, columns, cards, connections, meta):
        tables_list = []
        for rec in tables:
            tbl = {
                "id": rec["uid"],
                "pos_x": rec["pos_x"],
                "pos_y": rec["pos_y"],
                "is_base_table": bool(rec["is_base_table"]),
                "title_color_index": rec["title_color_index"],
                "title_left": rec["title_left"] or "",
                "title_right": rec["title_right"] or "",
                "title_right1": rec["title_right1"] or "",
                "extra_rows": rec["extra_rows"],
                "body_height": rec["body_height"],
                "columns": [],
            }
            if rec["is_base_table"] and rec["kanban_text"] is not None:
                tbl["kanban_text"] = rec["kanban_text"]
                tbl["kanban_text_x"] = rec["kanban_text_x"]

            for col_rec in columns.get(rec["db_id"], []):
                col = {
                    "id": col_rec.uid,
                    "header1": col_rec.header1,
                    "header2": col_rec.header2,
                    "header2a": col_rec.header2a,
                    "header3": col_rec.header3,
                    "header4": col_rec.header4,
                    "notes": col_rec.notes,
                    "header_overlay_index": col_rec.header_overlay_index,
                    "body_overlay_index": col_rec.body_overlay_index,
                    "linked_to_right": col_rec.linked_to_right,
                    "linked_from_left": col_rec.linked_from_left,
                    "cards": [],
                }
                for card_rec in cards.get(col_rec.db_id, []):
                    col["cards"].append({
                        "id": card_rec.uid,
                        "texts": card_rec.texts,
                        "color_index": card_rec.color_index,
                        "font_index": card_rec.font_index,
                        "status_index": card_rec.status_index,
                        "overlay_index": card_rec.overlay_index,
                        "klient_overlay_index": card_rec.klient_overlay_index,
                        "note_text": card_rec.note_text,
                        "history_text": card_rec.history_text,
                        "_timeline_encrypted": card_rec.timeline_encrypted,
                    })
                tbl["columns"].append(col)
            tables_list.append(tbl)

        return {
            "tables": tables_list,
            "connections": connections,
            "kanban_icon_pos": meta["kanban_icon_pos"],
            "main_notes": meta["main_notes"],
            "notes_data": meta["notes_data"],
        }

    @staticmethod
    def _uid_to_index(uid_to_index, uid):
        if uid in uid_to_index:
            return uid_to_index[uid]
        if isinstance(uid, str) and uid.startswith("#"):
            try:
                return int(uid[1:])
            except ValueError:
                pass
        return -1

    @staticmethod
    def _load_json(value, default):
        if value is None:
            return default
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _row_to_table(r):
        return {
            "db_id": r[0],
            "uid": r[1],
            "pos_x": r[2],
            "pos_y": r[3],
            "is_base_table": bool(r[4]),
            "title_color_index": r[5],
            "title_left": r[6],
            "title_right": r[7],
            "title_right1": r[8],
            "extra_rows": r[9],
            "body_height": r[10],
            "kanban_text": r[11],
            "kanban_text_x": r[12],
        }
