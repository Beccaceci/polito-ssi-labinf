#!/usr/bin/env python3
"""Practice replacement: OpenSSL-compatible four-bit RC4 exercise."""
import secrets
from pathlib import Path
from Crypto.Cipher import ARC4
key = bytes([secrets.randbelow(16) << 4]) + bytes(15)
Path('alice_ctext').write_bytes(ARC4.new(key).encrypt(b'Alice: this is a secret laboratory message.\n'))
Path('testbruteforce_enc').write_bytes(ARC4.new(key).encrypt(secrets.token_bytes(64)))
