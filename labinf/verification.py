"""Exercise acceptance and immutable evidence; installation checks are not passes."""
from datetime import datetime,timezone
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from .controller import Environment,apply_frozen
from .topology import ROOT, SCENARIOS
from .materials import find_original,digest


class Failed(RuntimeError):pass


class Recorder:
    def __init__(self,environment,out):
        self.e=environment;self.out=out;out.mkdir(parents=True,exist_ok=True)
        self.case='preflight';self.materials=[];self.records=[]
        self.work=f'/workspace/acceptance/{out.parent.name}'
        self.exchange=f'/exchange/acceptance/{out.parent.name}'

    def run(self,node,command,root=True,expect=0,timeout=120):
        started=datetime.now(timezone.utc).isoformat();clock=time.monotonic()
        # Every invocation fails at the first unexpected command/pipeline failure.
        pre=f'mkdir -p {self.work} {self.exchange}\ncd {self.work}\n'
        try:
            result=self.e.exec(node,pre+command+'\n',root=root,capture_output=True,timeout=timeout)
            code=result.returncode;stdout=result.stdout;stderr=result.stderr
        except subprocess.TimeoutExpired as error:
            code=124;stdout=error.stdout or '';stderr=error.stderr or ''
            if isinstance(stdout,bytes):stdout=stdout.decode(errors='replace')
            if isinstance(stderr,bytes):stderr=stderr.decode(errors='replace')
        ok=code==expect if isinstance(expect,int) else code in expect
        data={'case':self.case,'node':node,'user':'root' if root else 'kali','command':command,'started_utc':started,
              'duration_seconds':round(time.monotonic()-clock,4),'exit_status':code,'expected_exit':expect,
              'stdout':stdout,'stderr':stderr,'passed':ok}
        self.records.append(data)
        with (self.out/'commands.jsonl').open('a') as stream:stream.write(json.dumps(data)+'\n')
        with (self.out/'log.txt').open('a') as stream:
            stream.write(f'\n[{self.case}] {started}\nNode: {node}; user: {data["user"]}\nCommand:\n{command}\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}\nExit status: {code}; expected: {expect}; elapsed: {data["duration_seconds"]}\n')
        if not ok:raise Failed(f'{node} exited {code}, expected {expect}: {(stderr or stdout)[-1200:]}')
        return stdout

    def ip(self,node,network=None):
        if self.e.spec:
            attachments=self.e.spec['services'][node]['networks']
            return attachments[f'net{network}']['ipv4_address'] if network else next(iter(attachments.values()))['ipv4_address']
        return os.environ.get(f'LABINF_{node.upper()}_IP',{'alice':'10.0.2.10','bob':'10.0.2.20','chuck':'10.0.2.30'}[node])

    def material(self,name,practice=None):
        source=find_original(ROOT,self.e.lab,name)
        if source:
            target=self.exchange+'/materials/'+name
            self.run('alice',f'mkdir -p {self.exchange}/materials')
            self.e.prepare()
            self.e.compose('cp',str(source),f'alice:{target}',check=True,capture_output=True)
            self.materials.append({'name':name,'sha256':digest(source),'provenance':'supplied-original','source':str(source)})
            return target
        if practice:
            source=ROOT/'environment/materials/practice'/practice
            self.materials.append({'name':name,'sha256':digest(source),'provenance':'practice-replacement','source':str(source)})
            return '/opt/labinf/materials/practice/'+practice
        raise Failed(f'Missing material: {name}')

    def collect(self,node,path,label):
        result=self.e.compose('cp',f'{node}:{path}',str(self.out/label),capture_output=True,text=True)
        if result.returncode:raise Failed(f'Cannot collect evidence {label}: {result.stderr}')


def source_fingerprint():
    h=hashlib.sha256()
    paths=[ROOT/'docs/exercises.json',ROOT/'labinf_cli.py']
    for directory in ('labinf','environment'):
        paths.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for path in sorted(paths):
        h.update(str(path.relative_to(ROOT)).encode());h.update(path.read_bytes())
    return h.hexdigest()


def coverage():
    manifest=json.loads((ROOT/'docs/exercises.json').read_text())
    history=[]
    for p in sorted((ROOT/'workspace/runs').glob('*/summary.json')):
        try:
            data=json.loads(p.read_text())
            if data.get('source_fingerprint')==source_fingerprint():history.extend(data['results'])
        except (OSError,ValueError,KeyError):continue
    latest={}
    for item in history:latest[(item['id'],item.get('runtime','desktop'),item.get('mode','practice'))]=item
    for entry in manifest['exercises']:
        records=[v for k,v in latest.items() if k[0]==entry['id']]
        status=', '.join(f'{r["runtime"]}/{r["mode"]}: {r["status"]}' for r in records) or 'UNTESTED'
        print(f'{entry["id"]:<28} {status}')
    return 0


def preflight(r):
    services=['alice','bob','chuck'] if not r.e.spec else [n for n in r.e.spec['services'] if n!='lab02-app']
    states=[]
    for node in services:
        cid=r.e.compose('ps','-q',node,capture_output=True,text=True,check=True).stdout.strip()
        if not cid:raise Failed(f'{node}: container non avviato')
        state=json.loads(r.e.call(['docker','inspect',cid],capture_output=True,text=True,check=True).stdout)[0]
        states.append(state)
        if not state['State']['Running'] or state['State'].get('Health',{}).get('Status')!='healthy':raise Failed(f'{node}: not healthy')
        old_target=r.e.lab=='01' and r.e.scenario=='lan' and node=='alice'
        tools='ip ping nc netstat python3' if old_target else 'openssl hashdeep hexedit file xxd time CA.pl perl python3 apache2 a2enmod ssh sshd ssh-copy-id tcpdump tshark iptables nft conntrack ipsec swanctl htc hts ptunnel firefox-esr xdotool'
        r.run(node,f'for tool in {tools}; do command -v "$tool"; done\nid\nuname -a\n'+('' if old_target else 'openssl version -a\nopenssl list -providers\ncat /opt/labinf/packages.txt'),timeout=40)
    # Container image descriptors remain authoritative even if a local tag moved.
    # Docker containerd can no longer inspect an old untagged index by name.
    (r.out/'containers.json').write_text(json.dumps(states,indent=2)+'\n')
    inventory=[]
    for image_id in sorted({s['Image'] for s in states}):
        info=r.e.call(['docker','image','inspect',image_id],capture_output=True,text=True)
        inventory.extend(json.loads(info.stdout) if info.returncode==0 else [{'Id':image_id,'inspect_unavailable':True}])
    (r.out/'images.json').write_text(json.dumps(inventory,indent=2)+'\n')


def verify(a):
    from .cases import execute,cleanup
    manifest=json.loads((ROOT/'docs/exercises.json').read_text())
    fingerprint=source_fingerprint()
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    folder=ROOT/'workspace/runs'/run_id;folder.mkdir(parents=True)
    results=[]; selected=[]
    pairs=[(lab,scenario) for lab in SCENARIOS for scenario in SCENARIOS[lab]] if a.all else [(a.lab,a.scenario or SCENARIOS[a.lab][0])]
    for lab,scenario in pairs:
        entries=[x for x in manifest['exercises'] if x['lab']==lab and x['scenario']==scenario]
        if a.case:
            want={x['id'] for x in entries if x['name']in a.case or x['id']in a.case}
            if not want:raise ValueError('No matching exercise cases')
            while True:
                deps={d for x in entries if x['id']in want for d in x['dependencies']}
                if deps<=want:break
                want|=deps
            entries=[x for x in entries if x['id']in want]
        env=Environment(lab,scenario,a.runtime)
        if a.frozen:apply_frozen(env)
        r=Recorder(env,folder/f'lab{lab}-{scenario}')
        healthy=True
        try:
            env.require_docker()
            if a.all or a.start:env.start(a.build)
            preflight(r)
        except Exception as error:
            healthy=False;print(f'Lab {lab}/{scenario}: preflight failed: {error}',flush=True)
            results.append({'id':f'{lab}.{scenario}.preflight','runtime':a.runtime,'mode':a.mode,'status':'failed','reason':str(error)})
        passed=set()
        try:
            for entry in entries:
                r.case=entry['id'];status='blocked';reason='preflight failed'
                start=len(r.records);material_start=len(r.materials)
                try:
                    if not healthy:raise Failed(reason)
                    if any(dep not in passed for dep in entry['dependencies']):raise Failed('dependency did not pass')
                    missing=[name for name in entry['inputs'] if not find_original(ROOT,lab,name)]
                    if a.mode=='official' and missing:raise Failed('Missing originals: '+', '.join(missing))
                    execute(r,entry['name']);status='passed';reason='';passed.add(entry['id'])
                except Exception as error:
                    reason=str(error)
                    status='blocked' if not healthy or reason.startswith(('Missing originals','dependency')) else 'failed'
                result={'id':entry['id'],'runtime':a.runtime,'mode':a.mode,'status':status,'reason':reason,'commands':len(r.records)-start,'material_provenance':list(r.materials[material_start:])}
                results.append(result);print(f'{entry["id"]}: {status}'+(f' — {reason[:220]}' if reason else ''),flush=True)
                (folder/'summary.json').write_text(json.dumps({'run_id':run_id,'source_fingerprint':fingerprint,'results':results},indent=2)+'\n')
        finally:
            if healthy:
                try:cleanup(r)
                except Exception as error:results.append({'id':f'{lab}.{scenario}.cleanup','runtime':a.runtime,'mode':a.mode,'status':'failed','reason':str(error)})
            if (a.all or a.start) and not a.keep:
                env.compose('down','--remove-orphans',capture_output=True,text=True)
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (folder/'summary.json').write_text(json.dumps({'run_id':run_id,'source_fingerprint':fingerprint,'results':results},indent=2)+'\n')
    print('Evidence:',folder)
    return 0 if results and all(x['status']=='passed' for x in results) else 1
