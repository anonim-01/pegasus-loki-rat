import hashlib
import os

def hash_and_salt(password):
    """Hashes and salts a password."""
    salt = os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return password_hash, salt
