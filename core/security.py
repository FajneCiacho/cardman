"""
security.py - KOMPATYBILNOSC (Faza 3).

Kod bezpieczenstwa przeniesiony do modules/managers/security_manager.py.
Ten plik tylko re-eksportuje, aby stare importy dalej dzialaly.
"""
from modules.managers.security_manager import SecurityManager, PasswordManager

__all__ = ["SecurityManager", "PasswordManager"]
