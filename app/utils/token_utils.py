from cryptography.fernet import Fernet
import base64

def get_secret_key():
    from flask import current_app
    return current_app.config["FLASK_SECRET_KEY"]

def generate_token(payload):
    key = get_secret_key()
    cipher= Fernet(key)
    token= cipher.encrypt(payload.encode()).decode()
    return token



