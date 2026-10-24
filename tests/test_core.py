import json,tempfile,unittest,wave,math,struct
from pathlib import Path
from vocal_workflows.core import load_config,doctor,ExclusiveWorkspace
from vocal_workflows.training import audit_dataset,training_plan
from vocal_workflows.pipeline import plan
from vocal_workflows.speech import endpoint

BASE=Path(__file__).resolve().parents[1]

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.data=json.loads((BASE/'config.example.json').read_text(encoding='utf-8'))
        self.file=self.root/'config.local.json';self.file.write_text(json.dumps(self.data),encoding='utf-8')
        self.config=load_config(self.file)
    def tearDown(self):self.temp.cleanup()
    def test_missing_dependencies_are_reported_without_paths(self):
        d=doctor(self.config);self.assertFalse(d['ok']);self.assertNotIn(str(self.root),json.dumps(d));self.assertTrue(d['checks'])
    def test_fine_plan_is_not_execution(self):
        p=plan(self.config,'fine','input.wav');self.assertFalse(p['execute']);self.assertEqual(p['separation']['overlap'],8);self.assertTrue(p['role_review_required'])
    def test_quick_plan_is_one_stage(self):
        p=plan(self.config,'quick','input.wav');self.assertNotIn('lead_separation',p['stages']);self.assertFalse(p['separation']['tta'])
    def test_training_never_uses_absolute_experiment(self):
        with self.assertRaises(ValueError):training_plan(self.config,'../unsafe')
        p=training_plan(self.config,'example_voice');self.assertFalse(p['execute']);self.assertIn('example_voice',p['argv'])
    def test_invalid_protect_rejected(self):
        self.data['profiles']['fine']['protect']=.9;self.file.write_text(json.dumps(self.data))
        with self.assertRaises(ValueError):load_config(self.file)
    def test_remote_speech_rejected_by_default(self):
        self.config['speech']['api_base']='https://example.org'
        with self.assertRaises(ValueError):endpoint(self.config)
    def test_local_speech_allowed(self):self.assertEqual(endpoint(self.config),'http://127.0.0.1:9880')
    def test_dataset_does_not_export_filenames(self):
        audio=self.root/'sample.wav'
        with wave.open(str(audio),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
            f.writeframes(b''.join(struct.pack('<h',int(1000*math.sin(i/20))) for i in range(16000)))
        a=audit_dataset(self.root);self.assertEqual(a['files'],1);self.assertEqual(a['median_seconds'],1);self.assertNotIn('sample.wav',json.dumps(a))
    def test_lock_refuses_second_holder(self):
        with ExclusiveWorkspace(self.root):
            with self.assertRaises(TimeoutError):
                with ExclusiveWorkspace(self.root,timeout=.01):pass

if __name__=='__main__':unittest.main()
