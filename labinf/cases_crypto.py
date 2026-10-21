"""Observable cryptography acceptance, using originals where supplied."""
import shlex
import textwrap

KEY='00112233445566778899aabbccddeeff'
IV='0102030405060708090a0b0c0d0e0f10'
CIPHERS={'aes-128-cbc':(KEY,IV),'aes-192-cbc':(KEY+'0011223344556677',IV),
'aes-256-cbc':(KEY*2,IV),'des-cbc':('0123456789abcdef','1234567890abcdef'),
'des-ede3-cbc':('0123456789abcdef23456789abcdef01456789abcdef0123','1234567890abcdef'),
'rc4':(KEY,None),'chacha20':(KEY*2,IV)}


def py(script):return "python3 - <<'PY'\n"+textwrap.dedent(script)+"\nPY"


def enc(alg,decrypt=False,source='plain',target='cipher'):
    key,iv=CIPHERS[alg]
    return f'openssl enc -{alg} '+('-d' if decrypt else '-e')+f' -K {key} '+(f'-iv {iv} ' if iv else '')+f'-in {source} -out {target}'


def pki(r):
    r.run('alice',"mkdir pki\ncd pki\nprintf '\\n' | CA.pl -newca -extra-req '-nodes -subj /C=IT/ST=Piemonte/O=Polito/CN=TestCA'\ntest -s demoCA/cacert.pem\ntest -f demoCA/index.txt")
    r.run('alice',"cd pki\nopenssl req -new -newkey rsa:2048 -noenc -subj /C=IT/ST=Piemonte/O=Polito/CN=Alice -keyout alice.key -out alice.csr\nopenssl req -in alice.csr -text -noout\nopenssl ca -batch -in alice.csr -out alice.crt -notext\nopenssl x509 -in alice.crt -text -noout\nopenssl verify -CAfile demoCA/cacert.pem alice.crt\ngrep '^V' demoCA/index.txt\ncp alice.crt before-revocation.crt")
    r.run('alice',"cd pki\nopenssl ca -revoke alice.crt\nopenssl ca -gencrl -out revoked.crl\nopenssl crl -in revoked.crl -text -noout\nopenssl crl -in revoked.crl -CAfile demoCA/cacert.pem -verify -noout\ngrep '^R' demoCA/index.txt")
    r.run('alice',"cd pki\nopenssl verify -CAfile demoCA/cacert.pem -CRLfile revoked.crl -crl_check alice.crt",expect=2)
    # A separate valid certificate is needed for later envelope tests.
    r.run('alice',"cd pki\nopenssl req -new -key alice.key -subj /C=IT/ST=Piemonte/O=Polito/CN=AliceValid -out valid.csr\nopenssl ca -batch -in valid.csr -out valid.crt -notext")


def run_crypto(r,name):
    if name=='ciphers':
        r.run('alice',"printf '0123456789ABCDEF0123456789ABCDEF' > plain\ntest $(wc -c < plain) -eq 32")
        for alg in CIPHERS:
            expected=32 if alg in ('rc4','chacha20') else 40 if alg.startswith('des') else 48
            r.run('alice',enc(alg,target=alg+'.enc')+' -p\n'+enc(alg,True,alg+'.enc',alg+'.dec')+f'\ncmp plain {alg}.dec\ntest $(wc -c < {alg}.enc) -eq {expected}\nwc -c plain {alg}.enc')
        r.run('alice',enc('aes-128-cbc',target='nopad')+' -nopad\ntest $(wc -c < nopad) -eq 32\nprintf x >> plain')
        r.run('alice',enc('aes-128-cbc',target='badnopad')+' -nopad',expect=1)
    elif name=='kdf':
        r.run('alice',"printf 'passphrase example\\n' > kdf.txt\nopenssl enc -aes-128-cbc -in kdf.txt -out legacy-kdf.enc -pass pass:practice -p\nopenssl enc -d -aes-128-cbc -in legacy-kdf.enc -out legacy-kdf.dec -pass pass:practice\ncmp kdf.txt legacy-kdf.dec\nopenssl enc -aes-128-cbc -pbkdf2 -in kdf.txt -out kdf.enc -pass pass:practice -p\nopenssl enc -d -aes-128-cbc -pbkdf2 -in kdf.enc -out kdf.dec -pass pass:practice\ncmp kdf.txt kdf.dec")
    elif name=='bruteforce':
        script=r.material('Es1.2 Alice Secret Message.py','alice-secret.py')
        r.run('alice','python3 '+shlex.quote(script))
        # Imported generators may use either handout spelling.
        r.run('alice',py('''
            from pathlib import Path
            import subprocess
            source=next((p for p in map(Path,['alice_ctext','alice ctext','ctext_alice']) if p.exists()),None)
            assert source is not None, 'Generator did not create an Alice ciphertext'
            candidates=[]
            for n in range(16):
                result=subprocess.run(['openssl','enc','-d','-rc4','-K',f'{n:x}','-in',str(source)],capture_output=True)
                assert result.returncode==0,result.stderr
                data=result.stdout
                if data and all(x in (9,10,13) or 32<=x<=126 for x in data):candidates.append((n,data))
            assert candidates, 'No readable plaintext recovered'
            print(candidates)
        '''))
        source=r.material('testbruteforce_enc','alice-secret.py') if False else None
        # For original mode the imported arbitrary-binary ciphertext must be used.
        from .materials import find_original
        from .topology import ROOT
        if find_original(ROOT,'02','testbruteforce_enc'):
            source=r.material('testbruteforce_enc');r.run('alice','cp '+shlex.quote(source)+' testbruteforce_enc')
        r.run('alice',"test -s testbruteforce_enc\nfor nibble in {0..9} a b c d e f; do openssl enc -d -rc4 -K \"$nibble\" -in testbruteforce_enc -out brute-$nibble; done\nwc -c brute-*\necho 'All sixteen arbitrary binary plaintexts are possible without a known validity criterion.'")
    elif name in ('symmetric_speed','digest_speed'):
        r.run('alice','\n'.join(f'openssl rand -out size-{size} {size}' for size in (100,10000,1000000,100000000)),timeout=120)
        if name=='symmetric_speed':
            for alg in CIPHERS:
                for size in (100,10000,1000000,100000000):
                    r.run('alice','/usr/bin/time -p '+enc(alg,source=f'size-{size}',target='speed.enc')+'\n/usr/bin/time -p '+enc(alg,True,'speed.enc','speed.dec')+f'\ncmp size-{size} speed.dec',timeout=120)
                r.run('alice',f'openssl speed -seconds 1 -evp {alg}',timeout=40)
        else:
            for alg in ('md5','sha1','sha256','sha512','sha3-256','sha3-512'):
                for size in (100,10000,1000000,100000000):r.run('alice',f'/usr/bin/time -p openssl dgst -{alg} size-{size}',timeout=90)
                r.run('alice',f'openssl speed -seconds 1 -evp {alg}',timeout=40)
    elif name in ('rsa','signatures','challenge','hybrid'):
        r.run('alice',"openssl genrsa -out rsa.key 2048\nopenssl rsa -in rsa.key -text -noout\nopenssl rsa -in rsa.key -pubout -out rsa.pub\nprintf 'Un grandissimo segreto' > message")
        if name=='hybrid':
            r.run('alice',f"openssl rand -out large 1000000\nopenssl rand -out session.key 16\nxxd -p -c 256 session.key > session.hex\nopenssl enc -aes-128-cbc -K \"$(cat session.hex)\" -iv {IV} -in large -out large.enc\nopenssl pkeyutl -encrypt -pubin -inkey rsa.pub -in session.key -out wrapped.key\nopenssl pkeyutl -decrypt -inkey rsa.key -in wrapped.key -out recovered.key\ncmp session.key recovered.key\nopenssl enc -d -aes-128-cbc -K \"$(xxd -p -c 256 recovered.key)\" -iv {IV} -in large.enc -out recovered\ncmp large recovered")
        elif name=='challenge':
            r.run('alice',"openssl rand -out challenge.random 32\nopenssl pkeyutl -encrypt -pubin -inkey rsa.pub -in challenge.random -out challenge.enc\nopenssl pkeyutl -decrypt -inkey rsa.key -in challenge.enc -out response\ncmp challenge.random response")
        else:
            r.run('alice',"openssl pkeyutl -encrypt -pubin -inkey rsa.pub -in message -out rsa.enc\nopenssl pkeyutl -decrypt -inkey rsa.key -in rsa.enc -out rsa.dec\ncmp message rsa.dec\nopenssl pkeyutl -sign -rawin -digest sha256 -inkey rsa.key -in message -out rsa.sig\nopenssl pkeyutl -verify -rawin -digest sha256 -pubin -inkey rsa.pub -in message -sigfile rsa.sig\nopenssl pkeyutl -verifyrecover -pubin -inkey rsa.pub -in rsa.sig -out recovered.digest\nopenssl asn1parse -inform DER -in recovered.digest")
            r.run('alice',"openssl dgst -sha256 -sign rsa.key -out dgst.sig message\nopenssl dgst -sha256 -verify rsa.pub -signature dgst.sig message\nprintf '!' >> message")
            r.run('alice','openssl dgst -sha256 -verify rsa.pub -signature dgst.sig message',expect=1)
            r.run('alice','openssl rand -out too-large 246\nopenssl pkeyutl -encrypt -pubin -inkey rsa.pub -in too-large -out oversized',expect=1)
            if name=='rsa':
                r.run('alice',f"sshpass -p kali scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null message kali@{r.ip('bob')}:/workspace/scp-proof")
                r.run('bob','test -s /workspace/scp-proof')
    elif name=='ec':
        r.run('alice',"openssl ecparam -name secp192k1 -genkey -noout -out ec.key\nopenssl ec -in ec.key -pubout -out ec.pub\nopenssl ec -in ec.key -text -noout\nprintf ECDSA > ec.message\nopenssl pkeyutl -sign -rawin -digest sha256 -inkey ec.key -in ec.message -out ec.sig\nopenssl pkeyutl -verify -rawin -digest sha256 -pubin -inkey ec.pub -in ec.message -sigfile ec.sig")
    elif name=='asymmetric_speed':
        for alg in ('rsa512','rsa1024','rsa2048','rsa4096','dsa1024','dsa2048','ecdsap160','ecdsap256'):
            r.run('alice','openssl speed -seconds 1 '+alg,timeout=120)
    elif name in ('digests','mac'):
        r.run('alice',"printf 'Questo e un messaggio di prova!' > msg\nprintf shared-secret > secret\ncat secret msg > keyed\nopenssl dgst -sha256 keyed\nopenssl dgst -sha256 -hmac shared-secret msg\nopenssl mac -digest sha256 -macopt key:shared-secret -in msg HMAC\nopenssl mac -cipher AES-128-CBC -macopt hexkey:"+KEY+" -in msg CMAC")
        for alg in ('md5','sha1','sha256','sha3-256'):
            r.run('alice',f'openssl dgst -{alg} -binary msg > before\ncp msg altered\nprintf X >> altered\nopenssl dgst -{alg} -binary altered > after\n! cmp -s before after')
    elif name=='collision':
        script=r.material('IHA.sh','IHA.sh')
        r.run('alice',py(f'''
            import subprocess
            from pathlib import Path
            script={script!r}
            def h(p):return subprocess.check_output(['bash',script,p]).strip()
            Path('msg').write_bytes(b'fixed message')
            target=h('msg'); seen={{}}; second=False;collision=False
            for n in range(2000):
                Path('candidate').write_text(str(n)); value=h('candidate')
                if value==target and not second: print('second preimage',n,value);second=True
                if value in seen and not collision: print('arbitrary collision',seen[value],n,value);collision=True
                seen[value]=n
                if second and collision:break
            assert second and collision
        '''),timeout=120)
    elif name=='tamper':
        r.run('alice',"printf '456789\\n' > amount\n"+enc('rc4',source='amount',target='amount.enc'))
        r.run('alice',py('''
            from pathlib import Path
            p=bytearray(Path('amount.enc').read_bytes());p[0]^=ord('4')^ord('9');Path('tampered.enc').write_bytes(p)
        '''))
        r.run('alice',enc('rc4',True,'tampered.enc','amount.dec')+"\ngrep '^956789' amount.dec")
        for alg in ('aes-128-cbc','aes-128-ecb'):
            r.run('alice',f"printf '0123456789ABCDEF0123456789ABCDEF' > block\nopenssl enc -{alg} -K {KEY} -iv {IV} -in block -out block.enc")
            r.run('alice',py('''
                from pathlib import Path
                p=bytearray(Path('block.enc').read_bytes());p[0]^=1;Path('block.enc').write_bytes(p)
            '''))
            r.run('alice',f'openssl enc -d -{alg} -K {KEY} -iv {IV} -in block.enc -out block.dec\n! cmp -s block block.dec')
    elif name=='ecb':
        paths=[r.material(n) for n in ('ecb_plain_1','ecb_plain_2','ecb_enc')]
        r.run('alice',py(f'''
            from pathlib import Path
            from collections import Counter
            a,b,c=map(lambda p:Path(p).read_bytes(),{paths!r})
            def pattern(data):
                blocks=[data[i:i+8] for i in range(0,len(data),8)];labels={{}}
                return [labels.setdefault(block,len(labels)) for block in blocks]
            # Cipher padding can append one final block; equality of repeated blocks is the invariant.
            cp=pattern(c)
            matches=[i+1 for i,p in enumerate((a,b)) if cp[:len(pattern(p))]==pattern(p)]
            print('ECB candidate',matches);assert len(matches)==1
        '''))
    elif name=='integrity':
        script=r.material('gen_tree.sh')
        r.run('alice',f'mkdir integrity\ncd integrity\nbash {shlex.quote(script)}\nsha1sum tree/a/x/f1\nhashdeep -c sha1 -r tree > hash.list\nhashdeep -c sha1 -r -x -k hash.list tree\nprintf tamper >> tree/a/x/f1')
        r.run('alice','cd integrity\nhashdeep -c sha1 -r -x -k hash.list tree',expect=1)
    elif name in ('aead','aead_speed'):
        script=r.material('aes-gcm.py','aes-gcm.py'); script=shlex.quote(script)
        if name=='aead_speed':
            for size in (100,10000,1000000,100000000):
                r.run('alice',f'openssl rand -out aeadplain {size}\nprintf associated > aad\n/usr/bin/time -p python3 {script} -e aeadplain aad aeadcipher aeadtag -K {KEY} -iv {IV[:24]}\npython3 {script} -d aeaddec aad aeadcipher aeadtag -K {KEY} -iv {IV[:24]}\ncmp aeadplain aeaddec',timeout=120)
        else:
            r.run('alice',f'printf secret > aeadplain\nprintf associated > aad\npython3 {script} -e aeadplain aad aeadcipher aeadtag -K {KEY} -iv {IV[:24]}\npython3 {script} -d aeaddec aad aeadcipher aeadtag -K {KEY} -iv {IV[:24]}\ncmp aeadplain aeaddec')
            for changed in ('aad','aeadcipher','aeadtag'):
                r.run('alice',f'cp {changed} {changed}.saved\nprintf X >> {changed}\nprintf PRESERVE > protected-output')
                r.run('alice',f'python3 {script} -d protected-output aad aeadcipher aeadtag -K {KEY} -iv {IV[:24]}',expect=1)
                r.run('alice',f'grep -x PRESERVE protected-output\nmv {changed}.saved {changed}')
            r.run('alice',f'openssl enc -aes-128-gcm -K {KEY} -iv {IV[:24]} -in aeadplain -out unsupported',expect=1)
    elif name=='pki':pki(r)
    elif name=='compromise':
        r.run('alice',"mkdir compromise\ncd compromise\nprintf '\\n' | CA.pl -newca -extra-req '-nodes -subj /C=IT/ST=Piemonte/O=Polito/CN=CompromiseCA'\nopenssl req -new -newkey rsa:2048 -noenc -subj /C=IT/ST=Piemonte/O=Polito/CN=Alice -keyout alice.key -out alice.csr\nopenssl ca -batch -in alice.csr -out alice.crt -notext\nfor n in 1 2 3 4; do printf \"Message $n\\n\" > msg$n; date -u >> msg$n; openssl dgst -sha256 -sign alice.key -out msg$n.sig msg$n; done\nopenssl ca -revoke alice.crt -crl_compromise \"$(date -u -d '1 minute ago' +%Y%m%d%H%M%SZ)\"\nopenssl ca -gencrl -out compromised.crl\nopenssl crl -in compromised.crl -text -noout | grep -A2 'Invalidity Date'\nopenssl x509 -in alice.crt -pubkey -noout > pub\nfor n in 1 2 3 4; do openssl dgst -sha256 -verify pub -signature msg$n.sig msg$n; done")
        r.run('alice','cd compromise\nopenssl verify -CAfile demoCA/cacert.pem -CRLfile compromised.crl -crl_check alice.crt',expect=2)
    elif name=='formats':
        r.run('alice',"cd pki\nprintf 'PKCS7 laboratory message\\n' > msg\nopenssl x509 -in valid.crt -outform DER -out valid.der\nopenssl x509 -inform DER -in valid.der -out roundtrip.pem\nopenssl verify -CAfile demoCA/cacert.pem roundtrip.pem\nopenssl smime -sign -binary -in msg -out detached.pem -outform PEM -signer valid.crt -inkey alice.key -certfile demoCA/cacert.pem\nopenssl smime -verify -binary -in detached.pem -inform PEM -content msg -CAfile demoCA/cacert.pem -out detached.msg\nopenssl smime -sign -binary -nodetach -in msg -out attached.pem -outform PEM -signer valid.crt -inkey alice.key -certfile demoCA/cacert.pem\nopenssl smime -verify -binary -in attached.pem -inform PEM -CAfile demoCA/cacert.pem -out attached.msg\nopenssl smime -encrypt -aes-128-cbc -in msg -out envelope.pem -outform PEM valid.crt\nopenssl smime -decrypt -in envelope.pem -inform PEM -inkey alice.key -out recovered.msg\nfor file in detached.msg attached.msg recovered.msg; do tr -d '\\r' < \"$file\" > normalized; cmp msg normalized; done\nopenssl asn1parse -in envelope.pem -i\nopenssl crl2pkcs7 -nocrl -certfile valid.crt -certfile demoCA/cacert.pem -out chain.p7b\nopenssl pkcs7 -in chain.p7b -print_certs -noout\nopenssl pkcs12 -export -in valid.crt -inkey alice.key -certfile demoCA/cacert.pem -out alice.p12 -passout pass:practice\nopenssl pkcs12 -in alice.p12 -info -noout -passin pass:practice")
    else:return False
    return True
