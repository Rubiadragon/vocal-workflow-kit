"""Standard-library configuration, provenance and exclusive local admission."""
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

def digest(file):
    h = hashlib.sha256()
    with Path(file).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write_json(file, data):
    file = Path(file); file.parent.mkdir(parents=True, exist_ok=True)
    temporary = file.with_suffix(file.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(file)

def load_config(file):
    file = Path(file).resolve()
    config = json.loads(file.read_text(encoding='utf-8-sig'))
    config['_base'] = str(file.parent)
    if config.get('device') not in ('cpu', 'cuda'):
        raise ValueError('device must be cpu or cuda')
    for name in ('fine', 'quick'):
        p = config['profiles'][name]
        for key in ('index_rate', 'protect', 'rms_mix_rate'):
            value = p[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= (0.5 if key == 'protect' else 1):
                raise ValueError('Invalid profile parameter: ' + key)
        if isinstance(p['semitones'], bool) or not isinstance(p['semitones'], (int, float)) or not -24 <= p['semitones'] <= 24:
            raise ValueError('semitones outside supported range')
        if not isinstance(p['half'], bool): raise ValueError('half must be a JSON boolean')
    return config

def local_path(config, value):
    p = Path(value).expanduser()
    return p.resolve() if p.is_absolute() else (Path(config['_base']) / p).resolve()

def executable(config, value):
    p = Path(value)
    if p.is_absolute() or len(p.parts) > 1: return str(local_path(config, value))
    return shutil.which(value) or value

def doctor(config):
    checks = []
    def check(name, path): checks.append({'component': name, 'ok': Path(path).is_file()})
    check('ffmpeg', executable(config, config['ffmpeg']))
    for name in ('msst', 'rvc'):
        check(name + '_python', executable(config, config[name]['python']))
    root = local_path(config, config['msst']['root'])
    for key in ('script', 'vocal_config', 'vocal_checkpoint', 'karaoke_config', 'karaoke_checkpoint'):
        check('msst_' + key, root / config['msst'][key])
    check('rvc_backend', local_path(config, config['rvc']['root']) / 'infer/modules/vc/modules.py')
    check('voice_model', local_path(config, config['rvc']['model']))
    if any(config['profiles'][p]['index_rate'] > 0 for p in ('fine', 'quick')):
        check('voice_index', local_path(config, config['rvc']['index']))
    return {'schema_version': 1, 'ok': all(c['ok'] for c in checks), 'checks': checks,
            'note': 'File presence only. This does not certify model compatibility or a successful inference.'}

class ExclusiveWorkspace:
    """OS-released lock; process crashes do not leave a permanent stale lock.

    This portable release serializes workflows in one workspace. It does not
    include a durable priority queue or manage other applications/services.
    """
    def __init__(self, workspace, timeout=3600): self.workspace, self.timeout = Path(workspace), timeout
    def __enter__(self):
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.stream = (self.workspace / '.gpu.lock').open('a+b')
        if self.stream.seek(0, 2) == 0: self.stream.write(b'0'); self.stream.flush()
        start = time.monotonic()
        while True:
            try:
                self.stream.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (OSError, BlockingIOError):
                if time.monotonic() - start >= self.timeout:
                    self.stream.close(); raise TimeoutError('Workspace is busy; no running job was interrupted')
                time.sleep(0.25)
    def __exit__(self, *_):
        self.stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
        self.stream.close()
