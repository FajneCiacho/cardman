"""
event_bus.py - Prosty bus zdarzen (pub/sub).

Filozofia (wg Cardman v.3): bus tylko PRZEKAZUJE zdarzenia miedzy obiektami.
Nie zapisuje, nie interpretuje, nie zna zadnych modulow.
"""


class EventBus:
    """Niskopoziomowy pub/sub: subscribe / unsubscribe / emit.

    Typ zdarzenia to string (np. "card.moved"). Kazdy handler otrzymuje
    te same dane (kwargs). Bled pojedynczego handlera nie przerywa
    przekazywania do pozostalych.
    """

    def __init__(self):
        self._handlers = {}  # event_type -> [handler, ...]

    def subscribe(self, event_type, handler):
        """Rejestruje handler dla typu zdarzenia."""
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type, handler):
        """Usuwa handler dla typu zdarzenia."""
        handlers = self._handlers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)

    def emit(self, event_type, **data):
        """Publikuje zdarzenie; wola wszystkich subskrybentow."""
        for handler in list(self._handlers.get(event_type, [])):
            try:
                handler(**data)
            except Exception:
                # Jeden zepsuty sluchacz nie moze zepsuc reszty
                continue

    def has_subscribers(self, event_type):
        """Czy jakikolwiek handler nasluchuje danego zdarzenia."""
        return bool(self._handlers.get(event_type))
