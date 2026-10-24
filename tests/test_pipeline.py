import json,tempfile,unittest,shutil
from pathlib import Path
from unittest.mock import patch
try:
    import numpy as np,soundfile as sf,yaml
    AUDIO=True
except ImportError:AUDIO=False
from vocal_workflows.core import load_config
from vocal_workflows.pipeline import run_cover

BASE=Path(__file__).resolve().parents[1]

@unittest.skipUnless(AUDIO,'audio dependencies not installed')
class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        config=json.loads((BASE/'config.example.json').read_text(encoding='utf-8'))
        file=self.root/'config.local.json';file.write_text(json.dumps(config));self.c=load_config(file)
        msst=self.root/'dependencies/msst';(msst/'configs').mkdir(parents=True)
        for name in ['config_vocals_mel_band_roformer_kim.yaml','config_karaoke.yaml']:(msst/'configs'/name).write_text('inference: {}\n')
        self.source=self.root/'synthetic.wav';self.wave(self.source,2);self.calls=[];self.fail=False
    def tearDown(self):self.tmp.cleanup()
    def wave(self,file,channels):
        file.parent.mkdir(parents=True,exist_ok=True)
        a=.03*np.sin(np.arange(44100)*2*np.pi*220/44100)
        sf.write(file,a if channels==1 else np.column_stack([a]*channels),44100,subtype='FLOAT')
    def popen(self,args,**_):
        args=list(map(str,args));self.calls.append(args)
        if '--store_dir' in args:
            d=Path(args[args.index('--store_dir')+1])/'source';self.wave(d/'vocals.wav',2);self.wave(d/'instrumental.wav',2)
        elif '--request' in args:
            r=json.loads(Path(args[-1]).read_text());self.wave(Path(r['output']),1)
        elif args[-1].endswith('.mp3'):
            shutil.copyfile(args[args.index('-i')+1],args[-1]) # mock container, not a real MP3
        else:self.wave(Path(args[-1]),2)
        fail=self.fail and '--store_dir' in args
        class Proc:
            pid=123
            def wait(self,timeout=None):return 1 if fail else 0
            def terminate(self):pass
            def kill(self):pass
        return Proc()
    def mix(self,ff,lead,converted,inst,bg,out,settings):
        self.wave(Path(out)/'final.wav',2)
        return {'master':str(Path(out)/'final.wav'),'background_preserved':bool(bg)}
    def execute(self,mode='fine',reuse=None):
        with patch('vocal_workflows.pipeline.doctor',return_value={'ok':True}),patch('vocal_workflows.pipeline.subprocess.Popen',side_effect=self.popen),patch('vocal_workflows.audio.mix',side_effect=self.mix):
            return run_cover(self.c,mode,self.source,reuse,True)
    def test_two_stage_and_background_preserved(self):
        r=self.execute();self.assertEqual(r['status'],'completed');self.assertTrue(r['mix']['background_preserved'])
        self.assertEqual(sum('--store_dir' in a for a in self.calls),2);self.assertTrue(all('--use_tta' in a for a in self.calls if '--store_dir' in a))
    def test_quick_has_one_stage(self):
        r=self.execute('quick');self.assertFalse(r['mix']['background_preserved']);self.assertEqual(sum('--store_dir' in a for a in self.calls),1)
    def test_reuse_skips_separation_and_checks_hash(self):
        r=self.execute();manifest=next(p for p in (self.root/'workspace/runs').glob('*/manifest.json') if json.loads(p.read_text())['status']=='completed')
        count=len(self.calls);self.execute(reuse=str(manifest));self.assertFalse(any('--store_dir' in a for a in self.calls[count:]))
        Path(r['stems']['lead']['path']).write_bytes(b'tampered')
        with self.assertRaises(ValueError):self.execute(reuse=str(manifest))
    def test_failure_recorded_without_retry(self):
        self.fail=True
        with self.assertRaises(RuntimeError):self.execute()
        self.assertEqual(sum('--store_dir' in a for a in self.calls),1)
        m=next((self.root/'workspace/runs').glob('*/manifest.json'));self.assertEqual(json.loads(m.read_text())['status'],'failed')
    def test_roles_need_explicit_review(self):
        with self.assertRaises(ValueError):run_cover(self.c,'fine',self.source)

if __name__=='__main__':unittest.main()
