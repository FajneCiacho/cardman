"""
event_manager.py - Centralny router zdarzen (dyspozytor).

Rejestruje managery jako sluchaczy i rozsyla do nich zdarzenia.
Managery nie znaja siebie nawzajem - EventManager jest jedynym lacznikiem.

Konwencja: manager deklaruje zdarzenia w atrybucie HANDLED_EVENTS i
implementuje metode `on_<zdarzenie>` (kropka zamieniona na podkreslnik),
np. zdarzenie "card.moved" -> metoda `on_card_moved`.
"""

from modules.core.event_bus import EventBus


class EventManager:
    """Dyspozytor: register(manager) + emit(event, **data)."""

    def __init__(self, bus=None):
        self.bus = bus if bus is not None else EventBus()
        self._managers = []

    def register(self, manager):
        """Rejestruje managera i podpina jego metody pod deklarowane zdarzenia."""
        self._managers.append(manager)
        for event_type in getattr(manager, "HANDLED_EVENTS", []):
            handler = getattr(manager, f"on_{event_type.replace('.', '_')}", None)
            if handler is not None:
                self.bus.subscribe(event_type, handler)
        return manager

    def unregister(self, manager):
        """Odrejestrowuje managera."""
        if manager in self._managers:
            self._managers.remove(manager)
            for event_type in getattr(manager, "HANDLED_EVENTS", []):
                handler = getattr(manager, f"on_{event_type.replace('.', '_')}", None)
                if handler is not None:
                    self.bus.unsubscribe(event_type, handler)

    def emit(self, event_type, **data):
        """Publikuje zdarzenie na busie."""
        self.bus.emit(event_type, **data)

    def emit_on(self, event_type, **data):
        """Alias emit - publikuje zdarzenie przez bus."""
        self.bus.emit(event_type, **data)
