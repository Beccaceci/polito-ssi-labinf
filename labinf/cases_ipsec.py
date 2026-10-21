"""Reciprocal kernel IPsec, IKE and TLS checks on isolated Linux nodes."""
import re
import shlex
from .cases_crypto import py,KEY,IV
from .cases_network import listener


def flush(r,nodes=('alice','bob')):
    for node in nodes:r.run(node,'ip xfrm policy flush\nip xfrm state flush')


def transport(r,mode):
    flush(r)
    a,b=r.ip('alice'),r.ip('bob')
    for node in ('alice','bob'):
        for src,dst,spi in ((a,b,0x1000),(b,a,0x2000)):
            if mode in ('esp','esp_auth','esp_ah'):
                r.run(node,f"ip xfrm state add src {src} dst {dst} proto esp spi {spi} reqid 10 mode transport enc 'cbc(aes)' 0x{KEY}"+(f" auth-trunc 'hmac(sha1)' 0x{'ab'*20} 96" if mode=='esp_auth' else ''))
            if mode in ('ah','esp_ah'):
                r.run(node,f"ip xfrm state add src {src} dst {dst} proto ah spi {spi+0x2000} reqid 20 mode transport auth-trunc 'hmac(sha1)' 0x{'ab'*20} 96")
            if mode=='gcm':
                r.run(node,f"ip xfrm state add src {src} dst {dst} proto esp spi {spi} reqid 10 mode transport aead 'rfc4106(gcm(aes))' 0x{KEY}01020304 128")
        for src,dst,direction in ((a,b,'out' if node=='alice' else 'in'),(b,a,'in' if node=='alice' else 'out')):
            tmpl=''
            if mode!='ah':tmpl+=' tmpl proto esp reqid 10 mode transport level required'
            if mode in ('ah','esp_ah'):tmpl+=' tmpl proto ah reqid 20 mode transport level required'
            r.run(node,f'ip xfrm policy add src {src}/32 dst {dst}/32 dir {direction}'+tmpl)


def capture_start(r,node,name,filter):
    r.run(node,f'nohup tcpdump -U -i any -w {r.work}/{name}.pcap {shlex.quote(filter)} > {r.work}/{name}-capture.log 2>&1 </dev/null & echo $! > {r.work}/{name}.pid\nsleep .5\nkill -0 "$(cat {name}.pid)"')


def capture_stop(r,node,name,match):
    r.run(node,f'kill -INT "$(cat {name}.pid)"\nsleep .3\ntcpdump -nn -r {name}.pcap > {name}.txt\ngrep -E {shlex.quote(match)} {name}.txt')
    r.collect(node,f'{r.work}/{name}.pcap',name+'.pcap')


def state_counters(r,node):
    r.run(node,"ip -s xfrm state\nip -s xfrm state | grep -E '[1-9][0-9]*\\(packets\\)'")


def tls_setup(r):
    a=r.ip('alice')
    r.run('alice',f"mkdir -p {r.exchange}/tls\ncd {r.exchange}/tls\nopenssl req -x509 -newkey rsa:2048 -noenc -days 2 -subj /CN=LabCA -addext basicConstraints=critical,CA:TRUE -keyout ca.key -out ca.crt\nopenssl req -new -newkey rsa:2048 -noenc -subj /CN=alice.lab -keyout server.key -out server.csr\nprintf 'subjectAltName=DNS:alice.lab,IP:{a}\\nextendedKeyUsage=serverAuth\\n' > server.ext\nopenssl x509 -req -days 2 -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -extfile server.ext -out server.crt\nopenssl req -new -newkey rsa:2048 -noenc -subj /CN=Bob -keyout client.key -out client.csr\nprintf 'extendedKeyUsage=clientAuth\\n' > client.ext\nopenssl x509 -req -days 2 -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -extfile client.ext -out client.crt\nopenssl verify -CAfile ca.crt server.crt client.crt")


def tls_server(r,mutual=False,null=False):
    r.run('alice','if test -f tls.pid && kill -0 "$(cat tls.pid)" 2>/dev/null; then kill "$(cat tls.pid)"; sleep .2; fi')
    cert=f'{r.exchange}/tls/'
    cmd=f'openssl s_server -accept 4433 -www -no_dhe -no_ticket -tls1_2 -key {cert}server.key -cert {cert}server.crt'
    if mutual:cmd+=f' -CAfile {cert}ca.crt -Verify 1 -verify_return_error'
    if null:cmd+=" -cipher 'NULL-SHA:@SECLEVEL=0'"
    r.run('alice',f'nohup {cmd} > tls-server.log 2>&1 </dev/null & echo $! > tls.pid')
    listener(r,'alice',4433)


def client(r,extra='',host=None):
    host=host or r.ip('alice')
    return f"printf 'GET / HTTP/1.0\\r\\nHost: alice.lab\\r\\n\\r\\n' | timeout 12 openssl s_client -connect {host}:4433 -servername alice.lab -verify_hostname alice.lab -verify_return_error -CAfile {r.exchange}/tls/ca.crt -tls1_2 -quiet {extra}"


def ike(r,cert=False):
    flush(r)
    a,b=r.ip('alice'),r.ip('bob')
    for node in ('alice','bob'):
        r.run(node,"if ipsec statusall >/dev/null 2>&1; then ipsec stop; fi\nmkdir -p /etc/ipsec.d/cacerts /etc/ipsec.d/certs /etc/ipsec.d/private")
    if cert:
        for node,cn in (('alice','Alice'),('bob','Bob')):
            r.run(node,f"mkdir -p ike\ncd ike\nopenssl req -x509 -newkey rsa:2048 -noenc -subj /C=IT/O=Polito/CN={cn}CA -addext basicConstraints=critical,CA:TRUE -keyout ca.key -out ca.crt -days 2\nopenssl req -new -newkey rsa:2048 -noenc -subj /C=IT/O=Polito/CN={cn} -keyout identity.key -out identity.csr\nopenssl x509 -req -in identity.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out identity.crt -days 2\ncp identity.key /etc/ipsec.d/private/identity.key\ncp identity.crt /etc/ipsec.d/certs/identity.crt\ncp ca.crt {r.exchange}/{node}-ca.crt")
        for node,peer in (('alice','bob'),('bob','alice')):
            r.run(node,f'cp {r.exchange}/{peer}-ca.crt /etc/ipsec.d/cacerts/peer.crt')
    conn='host2-host2' if cert else 'host-host'
    for node,local,remote in (('alice',a,b),('bob',b,a)):
        label='cert' if cert else 'psk';suffix='ali' if node=='alice' else 'bob'
        original=r.material(f'ipsec.conf_{label}_{suffix}',f'ipsec.conf_{label}_{suffix}')
        secret=r.material(f'ipsec.secrets_{label}_{suffix}',f'ipsec.secrets_{label}_{suffix}')
        replacements={'@LOCAL_IP@':local,'@REMOTE_IP@':remote,'@LOCAL_CN@':'Alice' if node=='alice' else 'Bob','@REMOTE_CN@':'Bob' if node=='alice' else 'Alice'}
        r.run(node,py(f'''
            from pathlib import Path
            for source,target in [({original!r},'/etc/ipsec.conf'),({secret!r},'/etc/ipsec.secrets')]:
                text=Path(source).read_text()
                for before,after in {replacements!r}.items():text=text.replace(before,after)
                # Course example addresses are parameters, not portable topology constants.
                text=text.replace('192.168.27.128',{a!r}).replace('192.168.27.132',{b!r})
                Path(target).write_text(text)
        '''))
        r.run(node,'ipsec start\nfor n in {1..50}; do if ipsec statusall | grep -q "Listening IP addresses"; then exit 0; fi; sleep .2; done\nexit 1')
    capture_start(r,'bob','ike-cert' if cert else 'ike-psk','udp port 500 or udp port 4500 or ip proto 50')
    r.run('alice',f'ipsec up {conn}\nipsec statusall',timeout=80)
    r.run('alice',f'ping -c 3 -W 2 {b}\ncurl --fail --max-time 10 http://{b}/')
    for node in ('alice','bob'):
        if cert:r.run(node,'ipsec listcerts\nipsec listcacerts')
        state_counters(r,node)
        r.run(node,'ipsec statusall | grep ESTABLISHED\nip xfrm policy')
    capture_stop(r,'bob','ike-cert' if cert else 'ike-psk','ESP|isakmp|NONESP')
    for node in ('alice','bob'):r.run(node,'ipsec stop')
    flush(r)


def run_ipsec(r,name):
    a,b=r.ip('alice'),r.ip('bob')
    if name in ('esp','esp_auth','ah','esp_ah','gcm'):
        transport(r,name);capture_start(r,'bob',name,'ip proto 50 or ip proto 51')
        r.run('alice',f'ping -c 3 -W 2 {b}\ncurl --fail --max-time 8 http://{b}/')
        for node in ('alice','bob'):state_counters(r,node)
        capture_stop(r,'bob',name,'AH' if name=='ah' else 'ESP')
        flush(r)
    elif name=='ipsec_speed':
        r.run('alice','mkdir -p /var/www/html/ipsec\n'+'\n'.join(f'openssl rand -out /var/www/html/ipsec/{n} {s}'for n,s in [('10k',10000),('100k',100000),('1M',1000000),('10M',10000000),('100M',100000000)]))
        for mode in ('none','esp','esp_auth','ah','esp_ah','gcm'):
            flush(r)
            if mode!='none':transport(r,mode)
            for file in ('10k','100k','1M','10M','100M'):
                r.run('bob',f'curl --fail --trace-time --max-time 60 -v -o /dev/null -w "mode={mode} file={file} bytes=%{{size_download}} elapsed=%{{time_total}} speed=%{{speed_download}}\\n" http://{a}/ipsec/{file}',timeout=70)
        flush(r)
    elif name in ('ike_psk','ike_cert'):ike(r,name=='ike_cert')
    elif name=='tls':
        tls_setup(r);tls_server(r)
        out=r.run('bob',client(r));assert 'HTTP/1.0 200' in out
        r.run('bob',client(r).replace('-verify_hostname alice.lab','-verify_hostname wrong.lab'),expect=1)
        r.run('bob',client(r).replace(f'-CAfile {r.exchange}/tls/ca.crt','-CAfile /etc/ssl/certs/ca-certificates.crt'),expect=1)
        tls_server(r,null=True)
        out=r.run('bob',client(r,"-cipher 'NULL-SHA:@SECLEVEL=0'"));assert 'NULL-SHA' in out
        tls_server(r)
    elif name=='resumption':
        tls_server(r)
        out=r.run('bob',f"printf Q | timeout 20 openssl s_client -connect {a}:4433 -servername alice.lab -tls1_2 -no_ticket -reconnect -CAfile {r.exchange}/tls/ca.crt -verify_return_error")
        assert 'Reused, TLSv1.2' in out,'No actual session reuse'
    elif name=='mtls':
        tls_server(r,mutual=True)
        r.run('bob',client(r),expect=1)
        out=r.run('bob',client(r,f'-cert {r.exchange}/tls/client.crt -key {r.exchange}/tls/client.key'));assert 'HTTP/1.0 200' in out
        r.run('bob',client(r,f'-cert {r.exchange}/tls/server.crt -key {r.exchange}/tls/server.key'),expect=1)
        tls_server(r)
    elif name=='https_speed':
        config=r.material('apache2-ssl','apache2-ssl')
        r.run('alice',f'cp {shlex.quote(config)} /etc/apache2/sites-available/default-ssl.conf\ncp {r.exchange}/tls/server.crt /etc/ssl/certs/labinf-server.crt\ncp {r.exchange}/tls/server.key /etc/ssl/private/labinf-server.key\ncp {r.exchange}/tls/ca.crt /etc/ssl/certs/labinf-ca.crt\na2enmod ssl\na2ensite default-ssl\nmkdir -p /var/www/html/ipsec\napachectl configtest\nlabinf-service restart apache2\n'+'\n'.join(f'openssl rand -out /var/www/html/ipsec/{n} {s}'for n,s in [('10k',10000),('100k',100000),('1M',1000000),('10M',10000000),('100M',100000000)]))
        for mutual in (False,True):
            if mutual:r.run('alice',"sed -i 's/SSLVerifyClient none/SSLVerifyClient require/' /etc/apache2/sites-available/default-ssl.conf\nlabinf-service restart apache2")
            for file in ('10k','100k','1M','10M','100M'):
                flags=f'--certificate={r.exchange}/tls/client.crt --private-key={r.exchange}/tls/client.key' if mutual else ''
                r.run('bob',f'wget --timeout=20 --tries=1 --ca-certificate={r.exchange}/tls/ca.crt {flags} https://{a}/ipsec/{file} -O download\nwc -c download',timeout=60)
    elif name=='site':
        ga,gb=r.ip('gwa',3),r.ip('gwb',3)
        octet=r.e.spec['services']['alice']['environment']['LABINF_OCTET'];na=f'10.{octet}.1.0/24';nb=f'10.{octet}.2.0/24'
        flush(r,('gwa','gwb'))
        for node,src,dst,outnet,innet in [('gwa',ga,gb,na,nb),('gwb',gb,ga,nb,na)]:
            for s,d,spi in ((ga,gb,0x1000),(gb,ga,0x2000)):
                r.run(node,f"ip xfrm state add src {s} dst {d} proto esp spi {spi} reqid 10 mode tunnel enc 'cbc(aes)' 0x{KEY} auth-trunc 'hmac(sha1)' 0x{'ab'*20} 96")
            r.run(node,f'ip xfrm policy add src {outnet} dst {innet} dir out tmpl src {src} dst {dst} proto esp reqid 10 mode tunnel\nip xfrm policy add src {innet} dst {outnet} dir in tmpl src {dst} dst {src} proto esp reqid 10 mode tunnel\nip xfrm policy add src {innet} dst {outnet} dir fwd tmpl src {dst} dst {src} proto esp reqid 10 mode tunnel')
        capture_start(r,'gwb','site','ip proto 50')
        r.run('alice',f'ping -c 3 -W 2 {b}\ncurl --fail --max-time 8 http://{b}/')
        for node in ('gwa','gwb'):state_counters(r,node)
        capture_stop(r,'gwb','site','ESP')
        flush(r,('gwa','gwb'))
    else:return False
    return True
