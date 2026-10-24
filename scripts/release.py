"""Allowlist-only source release. Never copies workspaces, data or .git history."""
import argparse,hashlib,json,re,sys,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
ROOT_FILES={'README.md','AGENTS.md','AI_HANDOFF.md','LICENSE','THIRD_PARTY_NOTICES.md',
            'pyproject.toml','config.example.json','.gitignore','CHANGELOG.md','index.html','.nojekyll'}
DIRECTORIES={'vocal_workflows','docs','prompts','skills','tests','scripts','.github'}
EXTENSIONS={'.py','.md','.json','.toml','.html','.css','.js','.svg','.yml','.yaml'}
IGNORE={'__pycache__','.git','.venv','node_modules','workspace','models','datasets','dist','build','.support'}
PATTERNS=[
    ('absolute_windows_path',re.compile(r'\b[A-Za-z]:[\\/]')),
    ('absolute_home_path',re.compile(r'/(?:Users|home)/[A-Za-z0-9_.-]+')),
    ('private_ipv4',re.compile(r'\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})\b')),
    ('long_api_secret',re.compile(r'\bsk[-_][A-Za-z0-9_-]{20,}\b')),
    ('assigned_bili_credential',re.compile(r'(?i)(?:SESSDATA|bili_jct|buvid3)\s*[=:]\s*["\x27]?[A-Za-z0-9%_-]{12,}')),
    ('private_key',re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
]

def files():
    result=[]
    for p in sorted(ROOT.rglob('*')):
        rel=p.relative_to(ROOT)
        if any(part in IGNORE for part in rel.parts):continue
        allowed=(len(rel.parts)==1 and rel.name in ROOT_FILES) or (len(rel.parts)>1 and rel.parts[0] in DIRECTORIES)
        if not allowed:continue
        if p.is_symlink():raise ValueError('Symlink in public tree: '+rel.as_posix())
        if not p.is_file():continue
        if len(rel.parts)>1 and p.suffix not in EXTENSIONS:raise ValueError('Unexpected file type: '+rel.as_posix())
        if '.local.' in p.name or p.name.startswith('.env') or p.name.endswith('.log'):raise ValueError('Private filename: '+rel.as_posix())
        data=p.read_bytes()
        if len(data)>2*1024*1024 or b'\x00' in data:raise ValueError('Unexpected binary/large file: '+rel.as_posix())
        text=data.decode('utf-8-sig')
        for name,pattern in PATTERNS:
            if pattern.search(text):raise ValueError(name+' in '+rel.as_posix())
        result.append((rel.as_posix(),data))
    return result

def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');ap.add_argument('--output');args=ap.parse_args(argv)
    entries=files();manifest={'schema_version':1,'files':[{'path':p,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for p,b in entries],
                            'bundled_models':False,'bundled_audio':False,'upload_performed':False}
    if args.output:
        target=Path(args.output).resolve()
        if target.is_relative_to(ROOT):raise ValueError('Write releases outside the source tree')
        if target.exists():raise FileExistsError('Release already exists; refusing overwrite')
        target.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as archive:
            for name,data in entries+[('RELEASE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode())]:
                info=zipfile.ZipInfo('vocal-workflow-kit/'+name);info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=0o100644<<16;archive.writestr(info,data)
        print(json.dumps({'ok':True,'files':len(entries)+1,'zip_bytes':target.stat().st_size,
                          'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'upload_performed':False}))
    else:print(json.dumps({'ok':True,'files':len(entries),'privacy_scan':'passed','upload_performed':False}))
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:print(str(error),file=sys.stderr);raise SystemExit(1)
