"""Cross-platform CLI. Commands never modify the global Docker context."""
import argparse
import ipaddress
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from .topology import ROOT, SCENARIOS, specification
from .materials import import_materials


class Environment:
    def __init__(self, lab='01', scenario=None, runtime='desktop'):
        self.lab=lab; self.scenario=scenario or SCENARIOS[lab][0];self.runtime=runtime
        self.env=os.environ.copy()
        self.env.setdefault('LABINF_KALI_IMAGE','labinf-exercise:local')
        self.env.setdefault('LABINF_ALICE_IMAGE','labinf-lab01-target:local')
        self.spec=specification(lab,self.scenario)
        self.project=(self.spec or {}).get('name',self.env.get('COMPOSE_PROJECT_NAME','labinf'))
        self.path=ROOT/'environment/docker-compose.yml'
        if runtime=='lima':
            result=subprocess.run(['limactl','list','labinf','--format','{{.Dir}}'],capture_output=True,text=True,check=True)
            directory=result.stdout.strip()
            if not directory:raise ValueError('Create the labinf VM with runtime-init --runtime lima first')
            self.env.pop('DOCKER_CONTEXT',None)
            self.env['DOCKER_HOST']=f'unix://{directory}/sock/docker.sock'
        if runtime=='lima' and self.spec:
            for svc in self.spec['services'].values():
                svc['ports']=[v.replace('127.0.0.1:', '127.0.0.1:',1) for v in svc.get('ports',[])]
                if 'LABINF_GUI_HOST_PORT' not in os.environ:
                    svc['ports']=[f'127.0.0.1:{int(v.split(":")[-2])+10000}:6080' if v.endswith(':6080') else v for v in svc['ports']]
                if 'LABINF_APP_HOST_PORT' not in os.environ:
                    svc['ports']=[f'127.0.0.1:{int(v.split(":")[-2])+10000}:5000' if v.endswith(':5000') else v for v in svc['ports']]
        self.prefix=['docker','compose','--project-name',self.project,'--file',str(self.path)]

    def prepare(self):
        if self.spec:
            self.path=ROOT/'workspace/.labinf'/f'{self.project}.json';self.path.parent.mkdir(parents=True,exist_ok=True)
            for service in self.spec['services'].values():
                for volume in service.get('volumes',[]):Path(volume['source']).mkdir(parents=True,exist_ok=True)
            self.path.write_text(json.dumps(self.spec,indent=2)+'\n')
            self.prefix=['docker','compose','--project-name',self.project,'--file',str(self.path)]
        return self

    def call(self,args,**kwargs):
        return subprocess.run(args,cwd=ROOT,env=self.env,**kwargs)

    def compose(self,*args,**kwargs):
        self.prepare()
        return self.call([*self.prefix,*args],**kwargs)

    def exec(self,node,script,root=False,**kwargs):
        return self.compose('exec','-T','--user','0' if root else 'kali',node,'bash','-seuo','pipefail',input=script,text=True,**kwargs)

    def require_docker(self):
        result=self.call(['docker','info'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        if result.returncode:raise ValueError(f'Docker daemon unavailable for {self.runtime}. Start Docker Desktop or the labinf Lima VM.')

    def conflicts(self):
        self.prepare()
        cfg=self.compose('config','--format','json',capture_output=True,text=True,check=True)
        desired=json.loads(cfg.stdout)
        requested=[ipaddress.ip_network(n['subnet']) for v in desired.get('networks',{}).values() for n in v.get('ipam',{}).get('config',[]) if 'subnet'in n]
        ids=self.call(['docker','network','ls','-q'],capture_output=True,text=True,check=True).stdout.split()
        if ids:
            existing=json.loads(self.call(['docker','network','inspect',*ids],capture_output=True,text=True,check=True).stdout)
            for network in existing:
                if network.get('Labels',{}).get('com.docker.compose.project')==self.project:continue
                for config in (network.get('IPAM',{}).get('Config') or []):
                    if 'Subnet' in config and any(ipaddress.ip_network(config['Subnet']).overlaps(s) for s in requested):
                        raise ValueError(f'Subnet conflicts with {network["Name"]}; set LABINF_NETWORK_OCTET (or LABINF_SUBNET for Lab 01).')
        # Existing own published ports are intentional on repeated starts.
        own=self.compose('ps','-q',capture_output=True,text=True,check=True).stdout.split()
        owned=set()
        if own:
            for c in json.loads(self.call(['docker','inspect',*own],capture_output=True,text=True,check=True).stdout):
                for mappings in c['NetworkSettings'].get('Ports',{}).values():
                    for mapping in mappings or []:owned.add(int(mapping['HostPort']))
        for svc in desired['services'].values():
            for mapping in svc.get('ports',[]):
                port=int(mapping.get('published',0))
                if not port or port in owned:continue
                with socket.socket() as sock:
                    try:sock.bind((mapping.get('host_ip','127.0.0.1'),port))
                    except OSError as error:raise ValueError(f'Host port {port} is in use; set LABINF_GUI_HOST_PORT or LABINF_APP_HOST_PORT.') from error

    def start(self,build=False):
        self.require_docker();self.conflicts()
        args=['up','-d','--wait','--wait-timeout','240']
        if build:args.append('--build')
        self.compose(*args,check=True)


def apply_frozen(env):
    """Require exact previously accepted local image IDs; never rebuild them."""
    from .verification import source_fingerprint
    lock=ROOT/'workspace/.labinf'/f'{env.runtime}-images.lock.json'
    data=json.loads(lock.read_text())
    if data.get('runtime')!=env.runtime or data.get('source_fingerprint')!=source_fingerprint():
        raise ValueError(f'Frozen image lock is stale or belongs to another runtime: {lock}')
    for tag,expected in data.get('images',{}).items():
        actual=json.loads(env.call(['docker','image','inspect',tag],capture_output=True,text=True,check=True).stdout)[0]['Id']
        if actual!=expected:raise ValueError(f'Frozen image {tag} changed: expected {expected}, found {actual}')
    if env.spec:
        for service in env.spec['services'].values():
            tag=service.get('image')
            if tag not in data['images']:raise ValueError(f'No frozen image recorded for {tag}')
            service['build']={}
            service.pop('build',None)
    else:
        env.env['LABINF_KALI_IMAGE']='labinf-exercise:local'
        env.env['LABINF_ALICE_IMAGE']='labinf-lab01-target:local'
    return env


def parser():
    p=argparse.ArgumentParser(description='LABINF laboratory environment and acceptance evidence')
    p.add_argument('command',nargs='?',default='menu',choices=['start','stop','restart','reset','status','build','pull','check','verify','coverage','shell','exec','gui','gui-stop','materials','runtime-init','alice','bob','chuck','read_email','menu','freeze'])
    p.add_argument('target',nargs='?')
    p.add_argument('--lab',default='01',choices=['00',*SCENARIOS])
    p.add_argument('--scenario')
    p.add_argument('--runtime',default='desktop',choices=['desktop','lima'])
    p.add_argument('--root',action='store_true')
    p.add_argument('--frozen',action='store_true',help='use the immutable image IDs from freeze for this runtime')
    p.add_argument('--all',action='store_true')
    p.add_argument('--build',action='store_true')
    p.add_argument('--start',action='store_true',help='start each selected scenario before verification')
    p.add_argument('--mode',choices=['practice','official'],default='practice')
    p.add_argument('--source',type=Path)
    p.add_argument('--case',action='append',help='run only the named manifest case(s), including dependencies')
    p.add_argument('--keep',action='store_true',help='retain scenarios started by verify --all')
    return p


def main(argv=None):
    p=parser();a,extra=p.parse_known_args(argv)
    try:
        if a.command=='materials':
            if a.target!='import' or not a.source:p.error('materials import requires --source')
            print(import_materials(ROOT,a.lab,a.source));return 0
        if a.command=='coverage':
            from .verification import coverage
            return coverage()
        if a.command=='runtime-init':
            if a.runtime!='lima':p.error('runtime-init requires --runtime lima')
            config=ROOT/'workspace/.labinf/lima.yaml'
            config.parent.mkdir(parents=True,exist_ok=True)
            text=(ROOT/'environment/runtime/lima.yaml').read_text()
            text=text.replace('mounts: []','mounts:\n - location: '+json.dumps(str(ROOT))+'\n   writable: true')
            config.write_text(text)
            return subprocess.run(['limactl','start','--name=labinf',str(config)]).returncode
        if a.command=='menu':
            print('LABINF: start, shell <node>, verify, stop, reset, coverage; add --lab 01..05')
            if not sys.stdin.isatty():return 0
            selected=input('Command (blank exits): ').strip()
            if not selected:return 0
            import shlex
            return main(shlex.split(selected))
        if extra and a.command!='exec':p.error('Unexpected arguments: '+' '.join(extra))
        if a.lab=='00':
            if a.command!='check':p.error('Lab 00 is the readiness check: check --lab 00')
            env=Environment('03',runtime=a.runtime);env.require_docker()
            for command in (['docker','version'],['docker','compose','version'],['docker','run','--rm','--user','0','--cap-add=NET_ADMIN','--cap-add=NET_RAW','--entrypoint','bash','labinf-exercise:local','-seuc',
                "iptables -N LABINF_PROBE; iptables -X LABINF_PROBE; ip xfrm state add src 192.0.2.1 dst 192.0.2.2 proto esp spi 4096 mode transport aead 'rfc4106(gcm(aes))' 0x00112233445566778899aabbccddeeff01020304 128; ip xfrm state flush; ip xfrm policy list"]):
                env.call(command,check=True)
            print('Lab 00: Docker, Compose, root Netfilter and XFRM/GCM are functional.');return 0
        env=Environment(a.lab,a.scenario,a.runtime)
        if a.frozen:
            if a.build:p.error('--frozen and --build cannot be combined')
            apply_frozen(env)
        if a.command=='freeze':
            from .verification import source_fingerprint
            reports=[]
            for report in sorted((ROOT/'workspace/runs').glob('*/summary.json')):
                content=json.loads(report.read_text())
                if content.get('source_fingerprint')==source_fingerprint():reports.extend(content['results'])
            latest={r['id']:r for r in reports if r.get('runtime')==a.runtime and r.get('mode')=='practice'}
            required=json.loads((ROOT/'docs/exercises.json').read_text())['exercises']
            if any(latest.get(e['id'],{}).get('status')!='passed' for e in required):raise ValueError('Freeze requires current-source practice acceptance for every exercise on this runtime')
            images={}
            for tag in ('labinf-exercise:local','labinf-lab02-app:local','labinf-lab01-target:local'):
                info=json.loads(env.call(['docker','image','inspect',tag],check=True,capture_output=True,text=True).stdout)[0]
                images[tag]=info['Id']
            lock=ROOT/'workspace/.labinf'/f'{a.runtime}-images.lock.json';lock.parent.mkdir(parents=True,exist_ok=True)
            lock.write_text(json.dumps({'source_fingerprint':source_fingerprint(),'runtime':a.runtime,'images':images},indent=2)+'\n')
            print(lock);return 0
        if a.command=='verify':
            from .verification import verify
            return verify(a)
        env.require_docker()
        if a.command=='check':print('Docker is reachable.');return 0
        if a.command=='start':env.start(a.build);return 0
        if a.command=='reset':env.compose('down','--remove-orphans',check=True);env.start(a.build);return 0
        if a.command in ('stop','restart','status','build','pull'):
            cmd={'status':'ps'}.get(a.command,a.command)
            return env.compose(cmd).returncode
        if a.command=='read_email':return env.compose('exec','-T','alice','cat','/var/mail/alice').returncode
        node=a.command if a.command in ('alice','bob','chuck') else a.target
        if not node:node='chuck' if a.lab in ('01','02','03','05') and env.scenario!='site' else 'alice'
        if a.command in ('shell','alice','bob','chuck'):
            args=['exec']+(['--user','0'] if a.root else [])+[node,'bash']
            return env.compose(*args).returncode
        if a.command=='exec':
            if extra and extra[0]=='--':extra=extra[1:]
            if not extra:p.error('exec requires a command after --')
            return env.compose('exec','-T','--user','0' if a.root else 'kali',node,*extra).returncode
        if a.command in ('gui','gui-stop'):
            if env.spec:
                if node not in env.spec['services'] or not env.spec['services'][node].get('ports'):raise ValueError('Select the GUI-published node (alice or chuck for this scenario)')
                port=int(env.spec['services'][node]['ports'][0].split(':')[-2])
            else:port=int(os.environ.get('LABINF_GUI_HOST_PORT','6080'))
            result=env.exec(node,'labinf-gui '+('start' if a.command=='gui' else 'stop'))
            if result.returncode==0 and a.command=='gui':print(f'http://127.0.0.1:{port}/vnc.html')
            return result.returncode
        raise ValueError('Unknown command')
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        print(f'LABINF: {error}',file=sys.stderr);return 1
