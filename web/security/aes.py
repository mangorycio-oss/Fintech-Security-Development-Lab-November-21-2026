import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

CIPHER = AESGCM(AESGCM.generate_key(bit_length=256))


def encrypt(data, context):
    nonce = os.urandom(12)
    return base64.urlsafe_b64encode(nonce + CIPHER.encrypt(nonce, data, context)).decode()


def decrypt(encoded, context):
    payload = base64.urlsafe_b64decode(encoded)
    return CIPHER.decrypt(payload[:12], payload[12:], context)
