import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import os

class CryptoService:
    def __init__(self, master_key_derived=None):
        self._fernet = None
        if master_key_derived:
            self.set_master_key(master_key_derived)

    def set_master_key(self, master_key_derived: bytes):
        self._fernet = Fernet(base64.urlsafe_b64encode(master_key_derived))

    def derive_key(self, master_password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(master_password.encode('utf-8'))
        return key

    def generate_salt(self) -> bytes:
        return os.urandom(16)

    def encrypt_data(self, data: str) -> bytes:
        if not self._fernet:
            raise ValueError("Мастер-ключ не установлен. Вызовите set_master_key сначала.")
        return self._fernet.encrypt(data.encode('utf-8'))

    def decrypt_data(self, encrypted_data: bytes) -> str:
        if not self._fernet:
            raise ValueError("Мастер-ключ не установлен. Вызовите set_master_key сначала.")
        return self._fernet.decrypt(encrypted_data).decode('utf-8')

    def hash_password(self, password: str) -> bytes:
        password_bytes = password.encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        return hashed

    def verify_password(self, password: str, hashed_password: bytes) -> bool:
        password_bytes = password.encode('utf-8')
        try:
            return bcrypt.checkpw(password_bytes, hashed_password)
        except ValueError:
            return False