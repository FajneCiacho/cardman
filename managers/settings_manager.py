"""
settings_manager.py - Konfiguracja sesji i zmienne konfiguracyjne (Faza 3).

Odpowiedzialnosci:
- session_config.json (zoom, pozycja widoku, motyw itp. - na przyszlosc),
- config_overrides.json (reczne dostosowania uzytkownika).

Przeniesione z MainWindow.
"""
import json
import os
from datetime import datetime


class SettingsManager:
    """Zapis/odczyt plikow konfiguracyjnych aplikacji."""

    def __init__(self, config_folder=None):
        self.config_folder = config_folder or "."

    # --- sciezki ---

    def _session_config_path(self):
        return os.path.join(self.config_folder, "session_config.json")

    def _config_overrides_path(self):
        return os.path.join(self.config_folder, "config_overrides.json")

    def _app_settings_path(self):
        return os.path.join(self.config_folder, "app_settings.json")

    # --- session_config ---

    def load_session_config(self):
        """Laduje zmienne konfiguracji sesji."""
        path = self._session_config_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Blad przy ladowaniu konfiguracji sesji: {e}")
        return {}

    def save_session_config(self):
        """Zapisuje zmienne konfiguracji sesji."""
        path = self._session_config_path()
        try:
            config = {
                "timestamp": str(datetime.now()),
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Blad przy zapisywaniu konfiguracji sesji: {e}")

    # --- config_overrides ---

    def load_config_overrides(self):
        """Laduje zmienne konfiguracji recznie zmieniane przez uzytkownika."""
        path = self._config_overrides_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Blad przy ladowaniu config_overrides: {e}")
        return {}

    def save_config_overrides(self, overrides):
        """Zapisuje zmienne konfiguracji recznie zmieniane."""
        path = self._config_overrides_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(overrides, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Blad przy zapisywaniu config_overrides: {e}")

    # --- app_settings ---

    def load_app_settings(self):
        """Laduje ustawienia aplikacji (folder zapisu, przyciemnianie sceny)."""
        path = self._app_settings_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Blad przy ladowaniu app_settings: {e}")
        return {}

    def save_app_settings(self, settings):
        """Zapisuje ustawienia aplikacji."""
        path = self._app_settings_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Blad przy zapisywaniu app_settings: {e}")
