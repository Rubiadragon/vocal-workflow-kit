"""Audit PCM WAV datasets and print a training plan, never start training."""
import statistics
import wave
from pathlib import Path
from .core import digest, local_path, executable

def audit_dataset(directory):
    root = Path(directory).resolve()
    if not root.is_dir(): raise ValueError('Dataset directory not found')
    rows, unreadable = [], 0
    for file in sorted(root.rglob('*.wav')):
        if file.is_symlink(): continue
        try:
            with wave.open(str(file), 'rb') as wav:
                seconds = wav.getnframes() / wav.getframerate()
                rows.append({'id': digest(file)[:16], 'seconds': round(seconds, 3),
                             'sample_rate': wav.getframerate(), 'channels': wav.getnchannels()})
        except (wave.Error, EOFError, ZeroDivisionError): unreadable += 1
    durations = [r['seconds'] for r in rows]
    return {'files': len(rows), 'unreadable': unreadable,
            'minutes': round(sum(durations) / 60, 2),
            'median_seconds': round(statistics.median(durations), 3) if durations else 0,
            'shorter_than_one_second': sum(d < 1 for d in durations), 'items': rows,
            'note': 'Duration does not establish singing coverage, cleanliness, ownership, or voice quality. PCM WAV only.'}

def training_plan(config, experiment, epochs=100, batch=4):
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}', experiment):
        raise ValueError('Use a short experiment NAME, never an absolute path')
    if not 1 <= epochs <= 10000 or not 1 <= batch <= 64: raise ValueError('Invalid epochs/batch')
    root = local_path(config, config['rvc']['root'])
    return {'execute': False, 'cwd': str(root),
            'prerequisites': ['Complete preprocessing in the upstream UI', 'Extract F0 and v2 features',
                              'Verify config.json and filelist.txt in logs/<experiment>',
                              'Provide matching v2 40k F0 pretrained generator/discriminator'],
            'argv': [executable(config, config['rvc']['python']), 'infer/modules/train/train.py',
                     '-se', '10', '-te', str(epochs), '-pg', 'assets/pretrained_v2/f0G40k.pth',
                     '-pd', 'assets/pretrained_v2/f0D40k.pth', '-g', '0', '-bs', str(batch),
                     '-e', experiment, '-sr', '40k', '-sw', '1', '-v', 'v2', '-f0', '1', '-l', '0', '-c', '0'],
            'warning': 'Legacy RVC v2 40k command template. Check your fork help first. Epoch/batch are starting points, not a quality guarantee.'}
