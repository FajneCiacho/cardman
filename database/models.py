"""models.py - lekkie struktury wierszy relacyjnych (Faza 5).

Oddzielaja mapowanie (database_manager) od danych. Uzywane przez
DatabaseManager; nie zawieraja logiki biznesowej ani UI.
"""
from dataclasses import dataclass, field


@dataclass
class TableRecord:
    uid: str
    sort: int
    pos_x: float
    pos_y: float
    is_base_table: bool
    title_color_index: int
    title_left: str
    title_right: str
    title_right1: str
    extra_rows: int
    body_height: float
    kanban_text: str = None
    kanban_text_x: float = None


@dataclass
class ColumnRecord:
    uid: str
    header1: str
    header2: str
    header2a: str
    header3: str
    header4: str
    notes: str
    header_overlay_index: int
    body_overlay_index: int
    linked_to_right: bool
    linked_from_left: bool
    db_id: int = 0
    sort: int = 0


@dataclass
class CardRecord:
    uid: str
    texts: list
    color_index: int
    font_index: int
    status_index: int
    overlay_index: int
    klient_overlay_index: int
    note_text: str
    history_text: str
    timeline_encrypted: bool
    sort: int = 0


@dataclass
class ConnectionRecord:
    table1_uid: str
    table2_uid: str
    source_anchor_id: int
    target_anchor_id: int
    waypoints: list


@dataclass
class SceneMetaRecord:
    main_notes: str = ""
    notes_data: list = field(default_factory=list)
    kanban_icon_pos: dict = None
