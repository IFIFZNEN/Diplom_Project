from cryptography.fernet import Fernet

def encrypt_key(api_key):
    key = Fernet.generate_key()
    fernet = Fernet(key)
    encrypted_api_key = fernet.encrypt(api_key.encode())
    return encrypted_api_key, key

def decrypt_key(encrypted_api_key, key):
    fernet = Fernet(key)
    decrypted_api_key = fernet.decrypt(encrypted_api_key).decode()
    return decrypted_api_key

def save_encrypted_key(encrypted_api_key, key):
    with open("api_key.txt", "wb") as file:
        file.write(encrypted_api_key)
    with open("encryption_key.txt", "wb") as file:
        file.write(key)

def load_encrypted_key():
    with open("api_key.txt", "rb") as file:
        encrypted_api_key = file.read()
    with open("encryption_key.txt", "rb") as file:
        key = file.read()
    return encrypted_api_key, key

# Пример использования
api_key = "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"
encrypted_api_key, encryption_key = encrypt_key(api_key)
save_encrypted_key(encrypted_api_key, encryption_key)

loaded_encrypted_api_key, loaded_key = load_encrypted_key()
loaded_api_key = decrypt_key(loaded_encrypted_api_key, loaded_key)
