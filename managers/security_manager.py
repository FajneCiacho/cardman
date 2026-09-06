"""
security_manager.py - Bezpieczenstwo i szyfrowanie (Faza 3).

Odpowiedzialny za:
- Zarzadzanie haslami,
- Szyfrowanie/deszyfrowanie danych (Fernet),
- Szyfrowanie Timeline kart,
- Szyfrowanie autozapisu.

Przeniesiony z core/security.py (klasa PasswordManager -> SecurityManager).
"""

import os
import json
import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.exceptions import InvalidKey

from PyQt6.QtWidgets import QInputDialog, QMessageBox, QLineEdit


class SecurityManager:
    """
    Zarzadza haslami uzytkownika oraz kluczami szyfrowania.
    """

    def __init__(self, config_folder=None):
        if config_folder:
            self._config_folder = config_folder
        else:
            self._config_folder = os.path.dirname(os.path.abspath(__file__))
        self._config_path = os.path.join(self._config_folder, "password.json")
        self._salt = None
        self._password_hash = None
        self.current_password = None

        if os.path.exists(self._config_path):
            self._load()
        else:
            self._create_default_password()

    def set_config_folder(self, folder):
        if folder and os.path.isdir(folder):
            self._config_folder = folder
            self._config_path = os.path.join(self._config_folder, "password.json")
            self._save()

    def _load(self):
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._salt = base64.b64decode(data["salt"])
            self._password_hash = base64.b64decode(data["password_hash"])
        except Exception:
            self._create_default_password()

    def _save(self):
        data = {
            "salt": base64.b64encode(self._salt).decode("ascii"),
            "password_hash": base64.b64encode(self._password_hash).decode("ascii"),
        }
        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _create_default_password(self):
        self._salt = os.urandom(16)
        self._password_hash = self._derive_hash("1234", self._salt)
        self.current_password = "1234"
        self._save()

    def _get_kdf(self, salt):
        return PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=390000,
        )

    def _derive_hash(self, password, salt):
        kdf = self._get_kdf(salt)
        return kdf.derive(password.encode("utf-8"))

    def verify_password(self, password):
        if self._salt is None or self._password_hash is None:
            return False
        kdf = self._get_kdf(self._salt)
        try:
            kdf.verify(password.encode("utf-8"), self._password_hash)
            return True
        except InvalidKey:
            return False

    def set_current_password(self, password):
        self.current_password = password

    def get_fernet(self):
        if not self.current_password or self._salt is None:
            return None
        kdf = self._get_kdf(self._salt)
        key_bytes = kdf.derive(self.current_password.encode("utf-8"))
        key = base64.urlsafe_b64encode(key_bytes)
        return Fernet(key)

    def fernet_from_password_and_salt(self, password, salt):
        """Utworz obiekt Fernet z podanego hasla i soli."""
        if not password or salt is None:
            return None
        try:
            kdf = self._get_kdf(salt)
            key_bytes = kdf.derive(password.encode("utf-8"))
            key = base64.urlsafe_b64encode(key_bytes)
            return Fernet(key)
        except Exception:
            return None

    def prompt_for_password(self, parent=None, title="Haslo", text="Podaj haslo:"):
        pwd, ok = QInputDialog.getText(
            parent, title, text, QLineEdit.EchoMode.Password
        )
        if not ok:
            return None
        return pwd

    def change_password_dialog(self, parent=None):
        current, ok = QInputDialog.getText(
            parent, "Zmien haslo", "Podaj aktualne haslo:",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return None
        if not self.verify_password(current):
            QMessageBox.warning(parent, "Blad", "Niepoprawne aktualne haslo.")
            return None

        new1, ok = QInputDialog.getText(
            parent, "Zmien haslo", "Podaj nowe haslo:",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return None
        new2, ok = QInputDialog.getText(
            parent, "Zmien haslo", "Powtorz nowe haslo:",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return None

        if not new1:
            QMessageBox.warning(parent, "Blad", "Haslo nie moze byc puste.")
            return None
        if new1 != new2:
            QMessageBox.warning(parent, "Blad", "Hasla nie sa identyczne.")
            return None

        self._salt = os.urandom(16)
        self._password_hash = self._derive_hash(new1, self._salt)
        self._save()
        self.current_password = new1
        QMessageBox.information(parent, "Sukces", "Haslo zostalo zmienione.")
        return new1

    # === SZYFROWANIE TIMELINE ===

    def encrypt_timeline(self, timeline_text):
        """Szyfruje tekst Timeline karty."""
        fernet = self.get_fernet()
        if fernet is None or not timeline_text:
            return timeline_text
        try:
            encrypted = fernet.encrypt(timeline_text.encode("utf-8"))
            return base64.b64encode(encrypted).decode("ascii")
        except Exception:
            return timeline_text

    def decrypt_timeline(self, encrypted_text):
        """Deszyfruje tekst Timeline karty."""
        fernet = self.get_fernet()
        if fernet is None or not encrypted_text:
            return encrypted_text
        try:
            encrypted_bytes = base64.b64decode(encrypted_text.encode("ascii"))
            decrypted = fernet.decrypt(encrypted_bytes)
            return decrypted.decode("utf-8")
        except Exception:
            return encrypted_text

    def encrypt_data(self, data_dict):
        """Szyfruje slownik danych do formatu JSON."""
        fernet = self.get_fernet()
        if fernet is None:
            return None
        try:
            json_bytes = json.dumps(data_dict, ensure_ascii=False, indent=2).encode("utf-8")
            return fernet.encrypt(json_bytes)
        except Exception:
            return None

    def decrypt_data(self, encrypted_bytes):
        """Deszyfruje dane do slownika."""
        fernet = self.get_fernet()
        if fernet is None:
            return None
        try:
            decrypted = fernet.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode("utf-8"))
        except Exception:
            return None


# Alias kompatybilnosci (stara nazwa klasy z core/security.py)
PasswordManager = SecurityManager
