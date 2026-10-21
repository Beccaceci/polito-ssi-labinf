"""Compose scenarios. All paths are absolute; no management network bypasses routers."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {'01': ('lan', 'dns'), '02': ('lan',), '03': ('lan',), '04': ('shared', 'routed'), '05': ('lan', 'site')}


def specification(lab, scenario, root=ROOT):
    if scenario not in SCENARIOS[lab]:
        raise ValueError(f'Invalid scenario {scenario} for lab {lab}; choose {SCENARIOS[lab]}')
    if lab == '01' and scenario == 'lan':
        return None
    octet = int(os.environ.get('LABINF_NETWORK_OCTET', 170 + int(lab)))
    if not 1 <= octet <= 254:
        raise ValueError('LABINF_NETWORK_OCTET must be between 1 and 254')
    networks, services, addresses = {}, {}, {}
    def net(name, n):
        subnet = f'10.{octet}.{n}.0/24'
        networks[name] = {'driver':'bridge', 'driver_opts': {'com.docker.network.driver.mtu':'9000'}, 'ipam':{'config':[{'subnet':subnet,'gateway':f'10.{octet}.{n}.1'}]}}
    def node(name, attachments, **extra):
        private = root/'workspace'/'nodes'/f'lab{lab}-{scenario}'/name
        exchange = root/'workspace'/'exchange'/f'lab{lab}-{scenario}'
        addrs = {n:f'10.{octet}.{n}.{host}' for n,host in attachments}
        addresses[name] = next(iter(addrs.values()))
        env = {'LABINF_START_APACHE':'true','LABINF_START_SSH':'true','LABINF_START_DNS':'false'}
        env.update(extra)
        services[name] = {'image':os.environ.get('LABINF_EXERCISE_IMAGE','labinf-exercise:local'),
          'build':{'context':str(root/'environment'),'dockerfile':'Dockerfile.kali'},
          'hostname':name, 'init':True, 'user':'kali',
          'command':['/usr/local/bin/labinf-exercise-init'],
          'cap_add':['NET_ADMIN','NET_RAW'],
          'sysctls':{'net.ipv4.ip_forward':'1' if name in ('frank','gateway','gwa','gwb') else '0',
                     'net.ipv4.conf.all.send_redirects':'0','net.ipv4.conf.default.send_redirects':'0',
                     'net.ipv4.conf.all.rp_filter':'0','net.ipv4.conf.default.rp_filter':'0'},
          'environment':env,
          'volumes':[{'type':'bind','source':str(private),'target':'/workspace'},
                     {'type':'bind','source':str(private),'target':'/home/kali/workspace'},
                     {'type':'bind','source':str(exchange),'target':'/exchange'},
                     {'type':'bind','source':str(root/'workspace/materials'),'target':'/materials/imports','read_only':True}],
          'networks':{f'net{n}':{'ipv4_address':ip} for n,ip in addrs.items()},
          'healthcheck':{'test':['CMD-SHELL','sudo -n supervisorctl -c /etc/supervisor/labinf.conf status ssh | grep -q RUNNING && if test "$${LABINF_START_APACHE}" = true; then curl --fail --silent http://127.0.0.1/ >/dev/null; fi'],
                        'interval':'3s','timeout':'3s','retries':20,'start_period':'10s'}}
    if lab == '05' and scenario == 'site':
        for n in (1,2,3):net(f'net{n}',n)
        node('alice',[(1,10)], LABINF_ROUTE_TO=f'10.{octet}.2.0/24',LABINF_ROUTE_VIA=f'10.{octet}.1.254')
        node('gwa',[(1,254),(3,10)],LABINF_ROUTE_TO=f'10.{octet}.2.0/24',LABINF_ROUTE_VIA=f'10.{octet}.3.20')
        node('gwb',[(2,254),(3,20)],LABINF_ROUTE_TO=f'10.{octet}.1.0/24',LABINF_ROUTE_VIA=f'10.{octet}.3.10')
        node('bob',[(2,20)],LABINF_ROUTE_TO=f'10.{octet}.1.0/24',LABINF_ROUTE_VIA=f'10.{octet}.2.254')
    elif lab == '04' and scenario == 'routed':
        for n in (1,2):net(f'net{n}',n)
        node('alice',[(1,10)],LABINF_ROUTE_TO=f'10.{octet}.2.0/24',LABINF_ROUTE_VIA=f'10.{octet}.1.254')
        node('frank',[(1,254),(2,254)])
        node('bob',[(2,20)],LABINF_ROUTE_TO=f'10.{octet}.1.0/24',LABINF_ROUTE_VIA=f'10.{octet}.2.254')
    elif lab == '01' and scenario == 'dns':
        net('net1',1);net('net2',2)
        node('alice',[(1,10)])
        node('bob',[(1,20)],LABINF_DEFAULT_VIA=f'10.{octet}.1.254',LABINF_RESOLVER=f'10.{octet}.2.53')
        node('gateway',[(1,254),(2,254)])
        return_route={'LABINF_ROUTE_TO':f'10.{octet}.1.0/24','LABINF_ROUTE_VIA':f'10.{octet}.2.254'}
        node('dns',[(2,53)],LABINF_START_DNS='true',LABINF_DNS_ANSWER=f'10.{octet}.2.80',**return_route)
        node('web',[(2,80)],**return_route)
    else:
        net('net1',1)
        node('alice',[(1,10)])
        node('bob',[(1,20)])
        if lab == '04':
            node('frank',[(1,40)])
            services['alice']['environment'].update(LABINF_ROUTE_TO=f'10.{octet}.1.20/32',LABINF_ROUTE_VIA=f'10.{octet}.1.40')
            services['bob']['environment'].update(LABINF_ROUTE_TO=f'10.{octet}.1.10/32',LABINF_ROUTE_VIA=f'10.{octet}.1.40')
        else:node('chuck',[(1,30)])
    for name, service in services.items():
        if name == 'chuck' or (lab == '01' and scenario == 'dns' and name == 'alice'):
            service['privileged'] = True
    gui_node = 'chuck' if 'chuck' in services else 'alice'
    services[gui_node]['ports']=[f'127.0.0.1:{os.environ.get("LABINF_GUI_HOST_PORT",6080+int(lab))}:6080']
    if lab == '02':
        services['lab02-app']={'build':{'context':str(root/'environment/targets/lab02')},
         'image':'labinf-lab02-app:local','networks':['net1'],
         'ports':[f'127.0.0.1:{os.environ.get("LABINF_APP_HOST_PORT",15002)}:5000'],
         'healthcheck':{'test':['CMD','python','-c','import urllib.request; urllib.request.urlopen("http://localhost:5000/")'], 'interval':'3s','timeout':'3s','retries':20}}
    for service in services.values():
        if 'environment' in service:
            service['environment'].update({f'{n.upper()}_IP':ip for n,ip in addresses.items()})
            service['environment']['LABINF_OCTET']=str(octet)
    return {'name':f'labinf-{lab}-{scenario}','services':services,'networks':networks}
