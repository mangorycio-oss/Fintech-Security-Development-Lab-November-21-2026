"""Fingerprint for fixed classroom text."""

import hashlib


def demo_fingerprint():
    return hashlib.md5(b"session-3-lab").hexdigest()
