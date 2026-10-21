"""Firewall and tunnel acceptance on owned isolated scenarios."""
import shlex
import time
from .cases_crypto import py


def reset(r):
    for node in ('alice','bob','frank'):
        r.run(node,'iptables -P INPUT ACCEPT\niptables -P OUTPUT ACCEPT\niptables -P FORWARD ACCEPT\niptables -F\niptables -t nat -F\niptables -X\nconntrack -F',timeout=30)


def listener(r,node,port):
    r.run(node,f'for n in {{1..50}}; do if ss -ltnH "sport = :{port}" | grep -q .; then exit 0; fi; sleep .1; done\nexit 1')


def ssh(r,host,port=22):
    return f'sshpass -p kali ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=8 -p {port} kali@{host} id -un'


def run_network(r,name):
    a,b,f=r.ip('alice'),r.ip('bob'),r.ip('frank')
    reset(r)
    if name=='routing':
        for source,target in (('alice',b),('bob',a)):
            r.run(source,f'ip route get {target}\nping -c 2 -W 2 {target}\ncurl --fail --max-time 5 http://{target}/')
        r.run('frank','ip -brief addr\nip route\nsysctl net.ipv4.ip_forward net.ipv4.conf.all.send_redirects\niptables -I FORWARD -j DROP')
        r.run('alice',f'ping -c 1 -W 1 {b}',expect=1)
        r.run('frank','iptables -L FORWARD -v -n\niptables -F FORWARD')
    elif name=='personal':
        r.run('alice','iptables -P INPUT DROP')
        r.run('bob',f'ping -c 1 -W 1 {a}',expect=1)
        r.run('bob',f'curl --fail --max-time 2 http://{a}/',expect=28)
        r.run('alice','iptables -A INPUT -p icmp -j ACCEPT\niptables -A INPUT -p tcp --dport 80 -j ACCEPT\niptables -A INPUT -p tcp --dport 81 -j ACCEPT')
        r.run('bob',f'ping -c 1 -W 1 {a}\ncurl --fail --max-time 5 http://{a}/\nnmap -sT -Pn -n -p 22,80,81 --max-retries 0 --host-timeout 15s {a} > ports\ngrep "80/tcp.*open" ports\ngrep "81/tcp.*closed" ports\ngrep "22/tcp.*filtered" ports',timeout=30)
    elif name=='stateless':
        r.run('frank',f'iptables -P FORWARD DROP\niptables -A FORWARD -p tcp -s {a} --dport 80 -j ACCEPT\niptables -A FORWARD -p tcp -d {a} --sport 80 -j ACCEPT')
        r.run('alice',f'curl --fail --max-time 5 http://{b}/')
        r.run('bob',f'nmap -sS -Pn -n -p 22 --source-port 80 {a} > weakness\ngrep "22/tcp.*open" weakness')
        r.run('frank',f'iptables -I FORWARD 2 -p tcp -d {a} --sport 80 --syn -j DROP')
        r.run('bob',f'nmap -sS -Pn -n -p 22 --source-port 80 --max-retries 0 {a} > fixed\ngrep "22/tcp.*filtered" fixed')
        r.run('frank',f'iptables -A FORWARD -p tcp -d {a} --dport 22 -j ACCEPT\niptables -A FORWARD -p tcp -s {a} --sport 22 -j ACCEPT\niptables -A FORWARD -p icmp --icmp-type echo-request -j ACCEPT\niptables -A FORWARD -p icmp --icmp-type echo-reply -j ACCEPT')
        r.run('bob',ssh(r,a)+f'\nping -c 1 -W 2 {a}')
        r.run('alice',f'nc -z -w 1 {b} 22',expect=1)
    elif name=='spoof':
        dev=r.run('frank',f"ip -o route get {a} | sed -n 's/.* dev \\([^ ]*\\).*/\\1/p'").strip()
        r.run('frank',f'iptables -I FORWARD -i {dev} ! -s {a}/32 -j DROP')
        r.run('alice',py(f'''
            import socket,struct
            src=socket.inet_aton('192.0.2.99');dst=socket.inet_aton('{b}')
            header=struct.pack('!BBHHHBBH4s4s',69,0,28,7,0,64,17,0,src,dst)
            total=sum(struct.unpack('!10H',header));total=(total&65535)+(total>>16);total=(total&65535)+(total>>16)
            header=header[:10]+struct.pack('!H',(~total)&65535)+header[12:]
            s=socket.socket(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_RAW);s.sendto(header+struct.pack('!HHHH',12345,12345,8,0),('{b}',0))
        '''))
        r.run('frank','iptables -L FORWARD -v -n -x\niptables -L FORWARD -v -n -x | awk \'$3=="DROP" && $1>0 {ok=1} END {exit !ok}\'')
    elif name=='stateful':
        r.run('frank',f'iptables -P FORWARD DROP\niptables -A FORWARD -p tcp -s {a} --dport 80 -j ACCEPT\niptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT')
        r.run('alice',f'curl --fail --max-time 5 http://{b}/')
        r.run('bob',f'nmap -sA -Pn -n -p 22,25 --source-port 80 --max-retries 0 {a} > stateful\ngrep "22/tcp.*filtered" stateful\ngrep "25/tcp.*filtered" stateful')
        r.run('frank','conntrack -L\niptables -L -v -n')
    elif name=='limit':
        r.run('frank',f'iptables -P FORWARD DROP\niptables -A FORWARD -p icmp -d {a} --icmp-type echo-request -m limit --limit 20/minute --limit-burst 1 -j ACCEPT\niptables -A FORWARD -p icmp --icmp-type echo-reply -j ACCEPT\niptables -A FORWARD -j DROP')
        output=r.run('bob',f'ping -q -c 5 -i .2 -W 1 {a}')
        assert '1 received' in output,output
        r.run('frank','iptables -L FORWARD -v -n -x\niptables -L FORWARD -v -n -x | awk \'$3=="ACCEPT" && $1==1 {allow=1} $3=="DROP" && $1>=3 {drop=1} END {exit !(allow&&drop)}\'')
    elif name in ('http_tunnel','icmp_tunnel'):
        r.run('frank','iptables -P FORWARD DROP\niptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT')
        if name=='http_tunnel':
            r.run('frank',f'iptables -A FORWARD -p tcp -s {a} -d {b} --dport 80 -j ACCEPT')
            r.run('bob','labinf-service stop apache2\nnohup hts -w -k 1 -F 127.0.0.1:22 80 > /workspace/hts.log 2>&1 </dev/null & echo $! > /workspace/hts.pid\nfor n in {1..40}; do ss -ltnH "sport = :80" | grep -q . && exit 0; sleep .25; done\ncat /workspace/hts.log\nexit 1',timeout=20)
            r.run('alice',f'nohup htc -w -k 1 -F 8000 {b}:80 > /workspace/htc.log 2>&1 </dev/null & echo $! > /workspace/htc.pid\nfor n in {{1..40}}; do ss -ltnH "sport = :8000" | grep -q . && exit 0; sleep .25; done\ncat /workspace/htc.log\nexit 1',timeout=20)
        else:
            r.run('frank','iptables -A FORWARD -p icmp --icmp-type echo-request -j ACCEPT\niptables -A FORWARD -p icmp --icmp-type echo-reply -j ACCEPT')
            r.run('bob','nohup ptunnel > /workspace/ptunnel-server.log 2>&1 </dev/null & echo $! > /workspace/ptunnel.pid')
            r.run('alice',f'nohup ptunnel -p {b} -lp 8000 -da {b} -dp 22 > /workspace/ptunnel-client.log 2>&1 </dev/null & echo $! > /workspace/ptunnel.pid')
        r.run('alice',f'nc -z -w 1 {b} 22',expect=1)
        listener(r,'alice',8000)
        r.run('alice',ssh(r,'127.0.0.1',8000).replace('ConnectTimeout=8','ConnectTimeout=25'),timeout=55)
        r.run('frank','iptables -L FORWARD -v -n -x')
    elif name=='socks':
        r.run('alice','ssh-keygen -t rsa -b 2048 -N "" -f gateway-key')
        r.run('alice',f'sshpass -p ali ssh-copy-id -i gateway-key.pub -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ali@{f}')
        r.run('frank',"printf 'Port 1080\\nPasswordAuthentication no\\nAllowTcpForwarding no\\n' > /etc/ssh/sshd_config.d/00-labinf-gateway.conf\nsshd -t\nlabinf-service restart ssh")
        listener(r,'frank',1080)
        start=f'nohup ssh -N -D 127.0.0.1:1080 -p 1080 -i gateway-key -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ali@{f} > /workspace/socks.log 2>&1 </dev/null & echo $! > /workspace/socks.pid'
        r.run('alice',start);listener(r,'alice',1080)
        r.run('alice',f'curl --socks5-hostname 127.0.0.1:1080 --max-time 5 http://{b}/',expect=97)
        r.run('alice','kill "$(cat /workspace/socks.pid)"')
        r.run('frank',f"printf '\\nMatch User ali\\n AllowTcpForwarding yes\\n PermitOpen {b}:80\\n' >> /etc/ssh/sshd_config.d/00-labinf-gateway.conf\nsshd -t\nlabinf-service restart ssh")
        r.run('alice',start);listener(r,'alice',1080)
        r.run('alice',f'curl --fail --socks5-hostname 127.0.0.1:1080 --max-time 5 http://{b}/')
        r.run('alice',f'curl --socks5-hostname 127.0.0.1:1080 --max-time 5 telnet://{b}:22',expect=97)
    elif name=='proxy':
        # Independently authored forward-proxy replacement; imported originals are used if present.
        frank=r.material('frank-apache2-config','frank-apache2-config')
        bob=r.material('bob-apache2-config','bob-apache2-config')
        r.run('frank',f"mkdir -p /etc/apache2/ssl\nopenssl req -x509 -newkey rsa:2048 -noenc -subj /CN=Frank -addext subjectAltName=IP:{f} -keyout /etc/apache2/ssl/key.pem -out /etc/apache2/ssl/cert.pem -days 2\ncp /etc/apache2/ssl/cert.pem {r.exchange}/proxy-ca.pem\ncp {shlex.quote(frank)} /etc/apache2/sites-available/lab-proxy.conf\nsed -i 's/@BOB_IP@/{b}/g' /etc/apache2/sites-available/lab-proxy.conf\na2enmod ssl proxy proxy_http\na2ensite lab-proxy\napachectl configtest\nlabinf-service restart apache2")
        r.run('bob',f'cp {shlex.quote(bob)} /etc/apache2/sites-available/000-default.conf\nmkdir -p /var/www/html/icons\nprintf GIF89a > /var/www/html/icons/example.gif\nlabinf-service restart apache2')
        url=f'curl --fail --proxy https://{f}:443 --proxy-cacert {r.exchange}/proxy-ca.pem --noproxy "" --max-time 8'
        r.run('alice',url+f' http://{b}/')
        r.run('frank',"sed -i 's/#FILTER //g' /etc/apache2/sites-available/lab-proxy.conf\napachectl configtest\nlabinf-service restart apache2")
        r.run('alice',url+f' http://{b}/icons/example.gif',expect=22)
        r.run('frank',"htpasswd -bc /etc/apache2/htpasswd ali practice\nsed -i 's/#AUTH //g' /etc/apache2/sites-available/lab-proxy.conf\napachectl configtest\nlabinf-service restart apache2")
        r.run('alice',url+f' http://{b}/',expect=22)
        r.run('alice',url+f' --proxy-user ali:practice http://{b}/')
    else:return False
    return True
