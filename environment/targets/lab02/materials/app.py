from flask import Flask, render_template, request, send_file, make_response, session
import binascii
from Crypto.Cipher import AES, DES, DES3, ARC4, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
import os
import secrets
import random
import io
import hashlib

app = Flask(__name__)
app.secret_key = os.urandom(24)

ALGORITHMS = ['aes-128-cbc', 'des-cbc', 'des-ede3-cbc', 'rc4']

@app.route('/', methods=['GET', 'POST'])
def index():
    decrypted = None
    error = None
    if request.method == 'POST':
        key_hex = request.form.get('key', '').strip()
        algo = request.form.get('algorithm', '').lower()
        iv_hex = request.form.get('iv', '').strip()
        file = request.files.get('ciphertext')
        if not key_hex or not algo or not file:
            error = 'Please provide all required fields.'
        elif algo not in ALGORITHMS:
            error = 'Unknown algorithm!'
        else:
            try:
                # Pad key and IV hex strings to 48 hex chars (24 bytes) before unhexlify
                if algo == 'rc4':
                    # Terrible but otherwise bruteforce exercise won't work
                    key_hex = key_hex.ljust(32, '0')
                else:
                    key_hex = key_hex.ljust(48, '0')

                key = binascii.unhexlify(key_hex)
                if algo in ['aes-128-cbc', 'des-cbc', 'des-ede3-cbc']:
                    if not iv_hex:
                        error = 'IV required for this algorithm.'
                        return render_template('index.html', decrypted=decrypted, error=error)
                    if len(iv_hex) < 32:
                        iv_hex = iv_hex.ljust(32, '0')
                    iv = binascii.unhexlify(iv_hex)
                else:
                    iv = None
                ciphertext = file.read()

                # Decrypt
                if algo == 'aes-128-cbc':
                    key = key[:16]
                    iv = iv[:16]
                    cipher = AES.new(key, AES.MODE_CBC, iv)
                    pt = cipher.decrypt(ciphertext)
                elif algo == 'des-cbc':
                    key = key[:8]
                    iv = iv[:8]
                    cipher = DES.new(key, DES.MODE_CBC, iv)
                    pt = cipher.decrypt(ciphertext)
                elif algo == 'des-ede3-cbc':
                    key = key[:24]
                    iv = iv[:8]
                    try:
                        cipher = DES3.new(key, DES3.MODE_CBC, iv)
                        pt = cipher.decrypt(ciphertext)
                    except ValueError:
                        error = 'Try with a more complex key!'
                        pt = b''
                elif algo == 'rc4':
                    cipher = ARC4.new(key)
                    pt = cipher.decrypt(ciphertext)
                # Try to unpad and decode
                if algo in ['aes-128-cbc', 'des-cbc', 'des-ede3-cbc']:
                    block_size = 16 if algo == 'aes-128-cbc' else 8
                    try:
                        pt = unpad(pt, block_size)
                    except ValueError:
                        pass
                try:
                    decrypted = pt.decode(errors='replace')
                except Exception:
                    decrypted = str(pt)
            except Exception as e:
                error = f'Error: {e}'
    # On GET, always clear output
    if request.method == 'GET':
        return render_template('index.html', decrypted=None, error=None)
    return render_template('index.html', decrypted=decrypted, error=error)

@app.route('/challenge', methods=['GET', 'POST'])
def challenge():
    if request.method == 'GET' and not request.args.get('download'):
        session.pop('challenge_password', None)
        session.pop('challenge_cat', None)
        session.pop('encrypted_key_bytes', None)
        session.pop('encrypted_pwd_hex', None)
    warning = None
    encrypted_key_bytes = None
    encrypted_pwd_bytes = None
    encrypted_key_hex = None
    encrypted_pwd_hex = None
    iv_hex = None
    pubkey_text = ''
    algo = ''
    show_pwd_form = False
    cat_url = None
    correct = False
    # Use session to persist challenge data between requests
    if request.method == 'POST':
        if 'pubkey' in request.files:
            pubkey_file = request.files['pubkey']
            pubkey_text = pubkey_file.read().decode(errors='replace')
            # algo = request.form.get('algorithm', 'rsa')  # Remove algorithm selector, always use RSA
            if 'PRIVATE KEY' in pubkey_text:
                warning = 'Uh-oh! You shouldn\'t be giving your private key to strangers!'
            else:
                # Generate AES-256 key
                aes_key = get_random_bytes(32)
                # Encrypt AES key with public key
                try:
                    pubkey = RSA.import_key(pubkey_text)
                    cipher_rsa = PKCS1_OAEP.new(pubkey)
                    encrypted_key_bytes = cipher_rsa.encrypt(aes_key)
                    encrypted_key_hex = binascii.hexlify(encrypted_key_bytes).decode()
                except Exception as e:
                    warning = f'RSA error: {e}'
                    return render_template('challenge.html', warning=warning, encrypted_key_hex=None, encrypted_pwd_hex=None, iv_hex=None, show_pwd_form=False, cat_url=None, correct=False)
                # Generate random password
                words = [
                    'cat', 'moon', 'star', 'magic', 'orb', 'future', 'mystery', 'puzzle', 'dream', 'night',
                    'light', 'shadow', 'crystal', 'spell', 'secret', 'wisdom', 'fortune', 'riddle', 'key', 'gate'
                ]
                password = '-'.join(random.sample(words, 3)) + str(random.randint(100,999))
                # Encrypt password with AES-256-CBC
                iv = get_random_bytes(16)
                cipher_aes = AES.new(aes_key, AES.MODE_CBC, iv)
                encrypted_pwd_bytes = cipher_aes.encrypt(pad(password.encode(), 16))
                encrypted_pwd_hex = binascii.hexlify(encrypted_pwd_bytes).decode()
                iv_hex = binascii.hexlify(iv).decode()
                show_pwd_form = True
                # Store challenge data in session
                session['challenge_password'] = password
                session['challenge_cat'] = secrets.token_hex(8)
                session['encrypted_key_bytes'] = binascii.hexlify(encrypted_key_bytes).decode() if encrypted_key_bytes else ''
                session['encrypted_pwd_hex'] = encrypted_pwd_hex
                session['challenge_iv_hex'] = iv_hex
        elif 'user_password' in request.form:
            # User is submitting the password
            user_pwd = request.form.get('user_password', '')
            # Retrieve password from session-like env
            password = session.get('challenge_password')
            if password and user_pwd == password:
                correct = True
                cat_url = 'https://cataas.com/cat'
            else:
                warning = 'Incorrect password! Try again.'
        # Retrieve for rendering
        encrypted_key_hex = session.get('encrypted_key_bytes')
        encrypted_pwd_hex = session.get('encrypted_pwd_hex')
        iv_hex = session.get('challenge_iv_hex')
        show_pwd_form = bool(encrypted_key_hex and encrypted_pwd_hex)

    # Download endpoints (GET only, use session)
    if request.method == 'GET':
        if request.args.get('download') == 'key':
            key_hex = session.get('encrypted_key_bytes')
            if key_hex:
                return send_file(io.BytesIO(binascii.unhexlify(key_hex)), as_attachment=True, download_name='encrypted_key.bin')
        if request.args.get('download') == 'pwd':
            pwd_hex = session.get('encrypted_pwd_hex')
            if pwd_hex:
                return send_file(io.BytesIO(binascii.unhexlify(pwd_hex)), as_attachment=True, download_name='encrypted_password.bin')
    return render_template('challenge.html', warning=warning, encrypted_key_hex=encrypted_key_hex, encrypted_pwd_hex=encrypted_pwd_hex, iv_hex=iv_hex, show_pwd_form=show_pwd_form, cat_url=cat_url, correct=correct)

@app.route('/bruteforce', methods=['GET'])
def bruteforce():
    # Serve files if requested
    file_param = request.args.get('file')
    if file_param == 'ctext_alice':
        # Generate ctext_alice
        secret_messages = [
            "I really love information security!",
            "My credit card number is 1234 5678 9012 3456",
            "All my passwords are 'alice12345' and I never change them!",
            "I have a secret crush on Bob!",
            "I am beginning to suspect that Santa Claus is not real!",
            "I am a secret agent working for the CIA!",
            "NSA may or may not have tried putting backdoors in cryptographic algorithms!",
            "I am definitely not a robot!",
            "I put ketchup on my pasta and I love it!",
            "I am a secret agent working for the KGB!"
        ]

        keys = ['00', '10', '20', '30', '40', '50', '60', '70', '80', '90','A0','B0','C0','D0','E0','F0']

        message_index = random.randint(0, len(secret_messages) - 1)
        key_index = random.randint(0, len(keys) - 1)

        secret_message = secret_messages[message_index]
        secret_key = binascii.unhexlify(keys[key_index]) + b'\x00' * 15
        cipher = ARC4.new(secret_key)

        ctext_alice_bytes = cipher.encrypt(secret_message.encode())
        return send_file(io.BytesIO(ctext_alice_bytes), as_attachment=True, download_name='ctext_alice')
    elif file_param == 'bruteforce_enc':
        # Generate bruteforce_enc
        random_bytes = os.urandom(64)
        keys = ['00', '10', '20', '30', '40', '50', '60', '70', '80', '90','A0','B0','C0','D0','E0','F0']
        key_index = random.randint(0, len(keys) - 1)
        secret_key = binascii.unhexlify(keys[key_index]) + b'\x00' * 15
        cipher_bf = ARC4.new(secret_key)
        bruteforce_enc_bytes = cipher_bf.encrypt(random_bytes)
        return send_file(io.BytesIO(bruteforce_enc_bytes), as_attachment=True, download_name='bruteforce_enc')

    return render_template('bruteforce.html')

@app.route('/hash', methods=['GET', 'POST'])
def hash_page():
    hash_result = None
    error = None
    input_text = ''
    if request.method == 'POST':
        input_text = request.form.get('text', '').strip()
        if not input_text:
            error = 'Please enter some text.'
        else:
            hash_result = hashlib.sha256(input_text.encode()).hexdigest()[:1]
    return render_template('hash.html', hash_result=hash_result, error=error, input_text=input_text)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
