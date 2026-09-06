"""
timeline_manager.py - Zapis historii zmian (Timeline).

Nasluchuje zdarzen kart i tabel i zapisuje wpisy do zmiany historii.
Nie edytuje kart, nie rysuje - tylko dokumentuje.

Zdarzenia obslugiwane:
  - "card.created"   -> Nowa Karta ...
  - "card.moved"     -> Karta zmienila kolumne/tabele ...
  - "card.deleted"   -> Karta ... zostala usunieta
"""

from datetime import datetime

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QPushButton, QTextEdit, QVBoxLayout


class TimelineManager:
    """Dokumentuje zmiany; nasluchuje zdarzen przez EventManager."""

    HANDLED_EVENTS = ["card.created", "card.moved", "card.deleted"]

    TIMELINE_DELAY_MS = 2500  # Opoznienie wpisu (zachowane ze sceny)

    def __init__(self, change_log_max=10):
        self._change_log = []
        self._change_log_max = change_log_max
        self._pending_timeline_entries = {}

    # --- publiczne API ---

    def log(self, description):
        """Dodaje wpis do historii zmian."""
        entry = {"time": datetime.now().strftime("%Y-%m-%d %H:%M"), "text": description}
        self._change_log.insert(0, entry)
        self._change_log[:] = self._change_log[:self._change_log_max]

    def get_last_changes(self):
        """Zwraca kopie listy ostatnich zmian."""
        return list(self._change_log)

    def show_last_changes_dialog(self, parent=None):
        """Dialog 'Ostatnie 10 zmian' (przeniesiony ze sceny, Faza 3)."""
        entries = self.get_last_changes()
        dialog = QDialog(parent)
        dialog.setWindowTitle("Ostatnie 10 zmian")
        dialog.resize(520, 320)
        layout = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setFont(QFont("Consolas", 10))
        if not entries:
            text.setPlainText("Brak zapisanych zmian.")
        else:
            lines = [f"[{e['time']}]  {e['text']}" for e in entries]
            text.setPlainText("\n".join(lines))
        layout.addWidget(text)
        btn = QPushButton("Zamknij")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)
        dialog.exec()

    def schedule_entry(self, card, entry_func):
        """Planuje opozniony wpis do Timeline (2.5 sekundy)."""
        card_id = id(card)
        if card_id in self._pending_timeline_entries:
            timer = self._pending_timeline_entries[card_id]
            if timer.isActive():
                timer.stop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: self._execute_entry(card_id, entry_func))
        timer.start(self.TIMELINE_DELAY_MS)
        self._pending_timeline_entries[card_id] = timer

    def _execute_entry(self, card_id, entry_func):
        if card_id in self._pending_timeline_entries:
            del self._pending_timeline_entries[card_id]
        entry_func()

    # --- obslugiwane zdarzenia ---

    def on_card_created(self, description=None, **data):
        if description:
            self.log(description)

    def on_card_moved(self, description=None, **data):
        if description:
            self.log(description)

    def on_card_deleted(self, description=None, **data):
        if description:
            self.log(description)
