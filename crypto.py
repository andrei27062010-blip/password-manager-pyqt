import bcrypt

class CryptoService:
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

if __name__ == "__main__":
    crypto_service = CryptoService()

    test_password = "MySuperSecretPassword123!"
    hashed_pwd = crypto_service.hash_password(test_password)
    print(f"Original password: {test_password}")
    print(f"Hashed password: {hashed_pwd}")

    print(f"Verifying '{test_password}': {crypto_service.verify_password(test_password, hashed_pwd)}")
    print(f"Verifying 'WrongPassword': {crypto_service.verify_password('WrongPassword', hashed_pwd)}")
    print(f"Verifying '{test_password}' with wrong hash format: {crypto_service.verify_password(test_password, b'invalid_hash')}")
