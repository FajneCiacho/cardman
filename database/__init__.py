"""
database - relacyjny format projektu (Faza 5).

Rownolegly do JSON. StorageManager eksportuje/importuje scene przez
DatabaseManager; scena nie wie o istnieniu SQLite.
"""
from .database_manager import DatabaseManager

__all__ = ["DatabaseManager"]
