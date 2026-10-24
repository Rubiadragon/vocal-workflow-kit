import os,tempfile,unittest,subprocess
from pathlib import Path
try:
    import numpy as np,soundfile as sf
    AUDIO=True
except ImportError:AUDIO=False
from vocal_workflows.core import digest

@unittest.skipUnless(AUDIO and os.environ.get('VW_TEST_FFMPEG'),'Set VW_TEST_FFMPEG and install audio dependencies')
class AudioTests(unittest.TestCase):
    def test_real_static_mix_and_encode_on_synthetic_audio(self):
        from vocal_workflows.audio import mix
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);t=np.arange(44100*2)/44100
            values={'lead':.04*np.sin(2*np.pi*330*t),'converted':.035*np.sin(2*np.pi*440*t),
                    'inst':np.column_stack([.03*np.sin(2*np.pi*110*t)]*2),
                    'bg':np.column_stack([.01*np.sin(2*np.pi*220*t)]*2)}
            for name,a in values.items():sf.write(root/(name+'.wav'),a,44100,subtype='FLOAT')
            before={n:digest(root/(n+'.wav')) for n in values}
            out=root/'mix';out.mkdir();ff=os.environ['VW_TEST_FFMPEG']
            r=mix(ff,root/'lead.wav',root/'converted.wav',root/'inst.wav',root/'bg.wav',out,
                  {'lead_lufs':-22,'backing_lufs':-25,'final_lufs':-20,'true_peak_db':-1.5})
            self.assertTrue(r['background_preserved']);self.assertAlmostEqual(r['duration_sec'],2)
            self.assertLessEqual(r['true_peak_db'],-1.49)
            back,_=sf.read(out/'original-backing.wav',always_2d=True)
            self.assertLess(float(np.max(np.abs(back-values['inst']-values['bg']))),1e-7)
            for n,h in before.items():self.assertEqual(digest(root/(n+'.wav')),h)
            target=out/'finished.mp3';subprocess.run([ff,'-nostdin','-v','error','-n','-i',r['master'],'-c:a','libmp3lame','-b:a','320k',str(target)],check=True)
            self.assertGreater(target.stat().st_size,1000)

if __name__=='__main__':unittest.main()
