"""Immutable original imports; replacement provenance is never inferred as original."""
import hashlib
import json
import shutil
import tempfile
import zipfile
import tarfile
from pathlib import Path, PurePosixPath


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def import_materials(root, lab, source):
    source=Path(source).expanduser().resolve()
    destination=root/'workspace/materials'/f'lab{lab}'
    destination.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination,prefix='.import-') as tmp:
        staging=Path(tmp)/'files';staging.mkdir()
        if source.is_dir():
            for p in source.rglob('*'):
                if p.is_symlink():raise ValueError(f'Material symlinks are not supported: {p}')
                if p.is_file():
                    out=staging/p.relative_to(source);out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,out)
        else:
            archive=zipfile.ZipFile(source) if zipfile.is_zipfile(source) else tarfile.open(source)
            with archive:
                members=archive.infolist() if isinstance(archive,zipfile.ZipFile) else archive.getmembers()
                for m in members:
                    name=m.filename if isinstance(archive,zipfile.ZipFile) else m.name
                    rel=PurePosixPath(name)
                    if rel.is_absolute() or '..' in rel.parts or '\\' in name:raise ValueError('Unsafe material archive path')
                    if isinstance(archive,zipfile.ZipFile):
                        if (m.external_attr>>16)&0o170000 == 0o120000:raise ValueError('Archive symlinks are not supported')
                        if m.is_dir():continue
                        stream=archive.open(m)
                    else:
                        if m.isdir():continue
                        if not m.isfile():raise ValueError('Only regular material files are supported')
                        stream=archive.extractfile(m)
                    out=staging/str(rel);out.parent.mkdir(parents=True,exist_ok=True)
                    with stream, out.open('wb') as dest:shutil.copyfileobj(stream,dest)
        files=[{'path':str(p.relative_to(staging)),'sha256':digest(p)} for p in sorted(staging.rglob('*')) if p.is_file()]
        if not files:raise ValueError('No material files found')
        key=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()[:16]
        target=destination/key
        if not target.exists():
            staging.rename(target)
            (target/'provenance.json').write_text(json.dumps({'provenance':'imported-original','source':str(source),'files':files},indent=2)+'\n')
        return target


def find_original(root, lab, name):
    candidates=[]
    imports=root/'workspace/materials'/f'lab{lab}'
    for manifest in sorted(imports.glob('*/provenance.json')):
        data=json.loads(manifest.read_text())
        for item in data['files']:
            p=manifest.parent/item['path']
            if p.name==name:
                if digest(p)!=item['sha256']:raise ValueError(f'Imported material checksum mismatch: {p}')
                candidates.append(p)
    bundled=root/'environment/materials/original'/f'lab{lab}'
    candidates+=list(bundled.rglob(name)) if bundled.exists() else []
    if len({digest(p) for p in candidates})>1:
        raise ValueError(f'Conflicting originals for {name}; keep one imported revision per exercise')
    return candidates[0] if candidates else None
