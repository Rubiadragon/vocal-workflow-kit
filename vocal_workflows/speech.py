"""Local GPT-SoVITS API v2 adapter. No credentials, no auto model switching."""
import json,uuid
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request,urlopen,build_opener,ProxyHandler
from .core import local_path,digest,write_json

def endpoint(config):
    settings=config['speech'];url=settings['api_base'].rstrip('/');parsed=urlparse(url)
    if parsed.scheme not in ('http','https') or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use a plain HTTP(S) API origin without credentials/query')
    if parsed.hostname not in ('127.0.0.1','localhost','::1') and not settings.get('allow_remote',False):
        raise ValueError('Remote speech endpoint requires explicit allow_remote=true; audio/text may leave this computer')
    return url

def speech_doctor(config):
    settings=config['speech'];reference=local_path(config,settings['reference_audio']);available=False
    try:
        req=Request(endpoint(config)+'/openapi.json')
        opener=build_opener(ProxyHandler({}))
        with opener.open(req,timeout=3) as response:
            schema=json.loads(response.read(2*1024*1024));available='/tts' in schema.get('paths',{})
    except (OSError,ValueError):pass
    return {'reference_audio_present':reference.is_file(),'api_v2_tts_present':available,
            'model_identity_verified':False,'note':'Presence/API check does not confirm selected voice or synthesis quality.'}

def speak(config,text):
    if not text.strip() or len(text)>3000:raise ValueError('Text must contain 1–3000 characters')
    settings=config['speech'];reference=local_path(config,settings['reference_audio'])
    if not reference.is_file():raise FileNotFoundError('Provide your own authorized reference audio in local configuration')
    data={'text':text,'text_lang':settings['text_language'],'ref_audio_path':str(reference),
          'prompt_text':settings['reference_text'],'prompt_lang':settings['reference_language'],
          'media_type':'wav','streaming_mode':False}
    req=Request(endpoint(config)+'/tts',data=json.dumps(data).encode('utf-8'),headers={'Content-Type':'application/json'},method='POST')
    # Do not send local speech through an ambient HTTP proxy.
    opener=build_opener(ProxyHandler({}))
    with opener.open(req,timeout=120) as response:
        payload=response.read(32*1024*1024+1)
    if len(payload)>32*1024*1024 or payload[:4]!=b'RIFF' or payload[8:12]!=b'WAVE':
        raise ValueError('Speech endpoint did not return a bounded WAV file; no output published')
    out=local_path(config,config['workspace'])/'speech';out.mkdir(parents=True,exist_ok=True)
    target=out/('speech-'+uuid.uuid4().hex[:12]+'.wav');target.write_bytes(payload)
    report={'status':'completed','kind':'speech','output':str(target),'output_sha256':digest(target),
            'model_identity_verified':False,'listening':'pending','text_characters':len(text),
            'note':'Text/reference details deliberately omitted from the public-facing receipt.'}
    write_json(target.with_suffix('.json'),report);return report
