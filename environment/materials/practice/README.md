# Practice replacements

These files are independently implemented equivalents of interfaces described by the 2023/24 handouts. They are **not professor originals**. Imported originals take precedence and are stored separately with SHA256 provenance. Generated keys and plaintexts are exercise fixtures, not recovered professor data.

IHA.sh uses the first hexadecimal digit of SHA-256 of the raw input file. This reproduces the four-bit hash experiment, not an unverified historical IHA implementation. The RC4 generator uses a one-nibble key followed by zero padding, matching OpenSSL's -K short-key behavior. aes-gcm.py uses a 16-byte raw tag and authenticates before replacing the plaintext output.
