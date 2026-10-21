#!/usr/bin/env python3
"""Practice implementation of the four-file CLI documented in Lab 03.

Tag format: raw 16 bytes. Invalid authentication never replaces the output.
"""
import argparse
import os
import tempfile
from pathlib import Path
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('-e', action='store_true')
    mode.add_argument('-d', action='store_true')
    for name in ('plaintext', 'associated_data', 'ciphertext', 'tag'):
        p.add_argument(name, type=Path)
    p.add_argument('-K', required=True)
    p.add_argument('-iv', required=True)
    a = p.parse_args()
    try:
        key, nonce = bytes.fromhex(a.K), bytes.fromhex(a.iv)
        if len(key) != 16 or not 8 <= len(nonce) <= 128:
            raise ValueError('AES-128 requires 32 key hex digits and an 8..128-byte nonce; use 12 bytes for new data')
        inputs = [a.plaintext, a.associated_data] if a.e else [a.associated_data, a.ciphertext, a.tag]
        outputs = [a.ciphertext, a.tag] if a.e else [a.plaintext]
        all_paths = [x.resolve() for x in inputs + outputs]
        if len(set(all_paths)) != len(all_paths):
            raise ValueError('input and output paths must be distinct')
        aes = AESGCM(key)
        aad = a.associated_data.read_bytes()
        if a.e:
            data = aes.encrypt(nonce, a.plaintext.read_bytes(), aad)
            a.ciphertext.write_bytes(data[:-16])
            a.tag.write_bytes(data[-16:])
        else:
            tag = a.tag.read_bytes()
            if len(tag) != 16:
                raise ValueError('tag must contain exactly 16 raw bytes')
            plaintext = aes.decrypt(nonce, a.ciphertext.read_bytes() + tag, aad)
            fd, temporary = tempfile.mkstemp(dir=a.plaintext.parent, prefix='.authenticated-')
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(plaintext)
                os.replace(temporary, a.plaintext)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
    except (ValueError, OSError, InvalidTag) as error:
        p.exit(1, f'AEAD failed: {error or "authentication tag mismatch"}\n')


if __name__ == '__main__':
    main()
