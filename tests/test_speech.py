import io,json,tempfile,threading,unittest,wave
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
from unittest.mock import patch
from vocal_workflows.speech import speak,speech_doctor

class SpeechTests(unittest.TestCase):
    def test_local_v2_contract_without_real_voice(self):
        data=io.BytesIO()
        with wave.open(data,'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\x00\x00'*160)
        audio=data.getvalue();received=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def do_GET(self):self.send_response(200);self.end_headers();self.wfile.write(b'{"paths":{"/tts":{}}}')
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200);self.end_headers();self.wfile.write(audio)
        server=HTTPServer(('127.0.0.1',0),Handler);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);(root/'reference.wav').write_bytes(audio)
                c={'_base':str(root),'workspace':'workspace','speech':{'api_base':'http://127.0.0.1:'+str(server.server_port),'allow_remote':False,
                   'reference_audio':'reference.wav','reference_text':'Synthetic reference.','reference_language':'en','text_language':'en'}}
                self.assertTrue(speech_doctor(c)['api_v2_tts_present']);r=speak(c,'Synthetic text.')
                self.assertEqual(r['status'],'completed');self.assertEqual(Path(r['output']).read_bytes(),audio)
                self.assertEqual(received[0]['media_type'],'wav');self.assertFalse(received[0]['streaming_mode'])
                self.assertNotIn('Synthetic text.',json.dumps(r));self.assertFalse(r['model_identity_verified'])
        finally:server.shutdown();server.server_close();worker.join()

if __name__=='__main__':unittest.main()
