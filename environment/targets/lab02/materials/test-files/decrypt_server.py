import socket
import binascii
from Crypto.Cipher import AES, DES, DES3, ARC4
from Crypto.Util.Padding import unpad

# Helper to receive a line (ending with \n)
def recv_line(conn):
    data = b''
    while not data.endswith(b'\n'):
        chunk = conn.recv(1)
        if not chunk:
            break
        data += chunk
    return data.strip().decode()

def main():
    HOST = '0.0.0.0'
    PORT = 1337
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        print(f"Listening on {HOST}:{PORT}...")
        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr}")
                # Receive key
                conn.sendall(b"Send key (hex): ")
                key_hex = recv_line(conn)
                # Pad key and IV hex strings to 32 hex chars (16 bytes) before unhexlify
                if len(key_hex) < 32:
                    key_hex = key_hex.ljust(32, '0')
                key = binascii.unhexlify(key_hex)
                # Receive algorithm
                conn.sendall(b"Send algorithm (aes-128-cbc, des-cbc, des-ede3-cbc, rc4): ")
                algo = recv_line(conn).lower()

                if algo not in ['aes-128-cbc', 'des-cbc', 'des-ede3-cbc', 'rc4']:
                    conn.sendall(b'Ooopsy, unknown algorithm! Bye!\n')
                    continue

                # Receive IV if needed
                if algo in ['aes-128-cbc', 'des-cbc', 'des-ede3-cbc']:
                    conn.sendall(b"Send IV (hex): ")
                    iv_hex = recv_line(conn)
                    if len(iv_hex) < 32:
                        iv_hex = iv_hex.ljust(32, '0')
                    iv = binascii.unhexlify(iv_hex)
                else:
                    iv = None

                # Receive ciphertext
                conn.sendall(b"Send ciphertext in hexadecimal (TIP: use 'xxd -p FILENAME | tr -d \'\\n\' to print the hex content'): ")
                ct_hex = recv_line(conn)
                ciphertext = binascii.unhexlify(ct_hex)

                # Decrypt
                if algo == 'aes-128-cbc':
                    cipher = AES.new(key, AES.MODE_CBC, iv)
                    pt = cipher.decrypt(ciphertext)
                elif algo == 'des-cbc':
                    key = key[:8]  # DES key is 8 bytes
                    iv = iv[:8]  # DES IV is 8 bytes
                    cipher = DES.new(key, DES.MODE_CBC, iv)
                    pt = cipher.decrypt(ciphertext)
                elif algo == 'des-ede3-cbc':
                    key = key[:24]  # 3DES key is 24 bytes
                    iv = iv[:8]  # 3DES IV is 8 bytes
                    try:
                        cipher = DES3.new(key, DES3.MODE_CBC, iv)
                        pt = cipher.decrypt(ciphertext)
                    except ValueError:
                        conn.sendall(b'Uh-oh you should try with a more complex key!\n')
                        continue
                elif algo == 'rc4':
                    cipher = ARC4.new(key)
                    pt = cipher.decrypt(ciphertext)

                # Output plaintext
                conn.sendall(pt + b'\n')
                print("Decrypted text:", pt.decode(errors='replace'))

if __name__ == '__main__':
    main()
