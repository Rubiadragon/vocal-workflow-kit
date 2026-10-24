"""Configurable MSST -> RVC orchestration; no account or private-service hooks."""
import json,os,shutil,subprocess,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
from .core import digest,write_json,local_path,executable,doctor,ExclusiveWorkspace

def plan(config,mode,source,reuse=None):
    if mode not in ('quick','fine'):raise ValueError('Unknown cover mode')
    return {'execute':False,'mode':mode,'source':str(Path(source).resolve()),'reuse':reuse,
            'stages':(['reuse_verified_stems'] if reuse else ['decode','vocal_separation']+(['lead_separation'] if mode=='fine' else []))+['rvc_conversion','static_mix','publish_mp3'],
            'separation':{'overlap':8 if mode=='fine' else 2,'batch_size':1,'tta':mode=='fine'},
            'profile':config['profiles'][mode],'background_policy':'preserve',
            'role_review_required':mode=='fine','note':'A plan is not an inference result. No commands ran.'}

def run_cover(config,mode,source,reuse=None,roles_confirmed=False):
    source=Path(source).resolve()
    if not source.is_file():raise FileNotFoundError('Source audio not found')
    if mode=='fine' and not roles_confirmed:raise ValueError('Review lead/background roles first; use --roles-confirmed only after review')
    check=doctor(config)
    if not check['ok']:raise RuntimeError('Missing dependencies; run doctor --json')
    workspace=local_path(config,config['workspace'])
    with ExclusiveWorkspace(workspace):
        runs=workspace/'runs';runs.mkdir(exist_ok=True)
        for state in runs.glob('*/manifest.json'):
            if json.loads(state.read_text(encoding='utf-8')).get('status')=='running':
                raise RuntimeError('Unfinished prior job: inspect its processes and manifest before starting another inference')
        run=runs/(datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]);run.mkdir()
        manifest={'schema_version':1,'status':'running','mode':mode,'source':str(source),
                  'source_sha256':digest(source),'profile':config['profiles'][mode],
                  'role_review':'operator-confirmed' if roles_confirmed else 'quick-mode-all-vocals',
                  'listening':'pending','commands':[]}
        def save():write_json(run/'manifest.json',manifest)
        def command(stage,args,cwd=None):
            manifest['stage']=stage;save();log=run/(stage+'.log')
            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','NUMBA_CACHE_DIR':str(run/'cache/numba'),
                 'MPLCONFIGDIR':str(run/'cache/matplotlib'),'HF_HOME':str(workspace/'cache/huggingface')}
            with log.open('w',encoding='utf-8') as stream:
                proc=subprocess.Popen([str(a) for a in args],cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT)
                record={'stage':stage,'pid':proc.pid,'exit_code':None,'log':log.name};manifest['commands'].append(record);save()
                try:record['exit_code']=proc.wait()
                except BaseException:
                    proc.terminate()
                    try:proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait()
                    raise
            save()
            if record['exit_code']:raise RuntimeError(stage+' failed; inspect its local log')
        save()
        try:
            ff=executable(config,config['ffmpeg'])
            if reuse:
                previous=json.loads(Path(reuse).read_text(encoding='utf-8'))
                if previous.get('status')!='completed' or previous['mode']!=mode or previous['source_sha256']!=manifest['source_sha256']:
                    raise ValueError('Reuse manifest does not match source/mode or is not complete')
                stems=previous['stems']
                expected={'overlap':8 if mode=='fine' else 2,'tta':mode=='fine','batch_size':1}
                if previous.get('separation')!=expected:raise ValueError('Reuse quality profile does not match')
                manifest['separation']=previous['separation']
                for stem in stems.values():
                    if digest(stem['path'])!=stem['sha256']:raise ValueError('Reused stem hash changed')
            else:
                import yaml,soundfile as sf
                inp=run/'input';inp.mkdir();decoded=inp/'source.wav'
                command('decode',[ff,'-nostdin','-v','error','-n','-i',source,'-vn','-ac','2','-af',
                                  'aresample=44100:resampler=soxr:precision=28','-c:a','pcm_f32le',decoded])
                msst=config['msst'];root=local_path(config,msst['root']);stems={}
                for stage,prefix in [('vocals','vocal')]+([('lead','karaoke')] if mode=='fine' else []):
                    original=root/msst[prefix+'_config'];settings=yaml.safe_load(original.read_text(encoding='utf-8-sig'))
                    settings.setdefault('inference',{}).update(batch_size=1,num_overlap=8 if mode=='fine' else 2)
                    cfg=run/(stage+'.yaml');cfg.write_text(yaml.safe_dump(settings,sort_keys=False),encoding='utf-8')
                    folder=run/stage;folder.mkdir()
                    args=[executable(config,msst['python']),'-B','-u',root/msst['script'],'--model_type',msst[prefix+'_model_type'],
                          '--config_path',cfg,'--start_check_point',root/msst[prefix+'_checkpoint'],
                          '--input_folder',inp,'--store_dir',folder,'--extract_instrumental']
                    if mode=='fine':args+=['--use_tta']
                    args+=['--device_ids','0'] if config['device']=='cuda' else ['--force_cpu']
                    command('separate-'+stage,args,root)
                    def find(name):
                        candidates=[p for p in folder.rglob('*.wav') if p.stem.lower()==name]
                        if len(candidates)!=1:raise RuntimeError('MSST output layout unsupported: expected exactly one '+name+'.wav')
                        return candidates[0]
                    vocals=find('vocals');other=find('instrumental')
                    if stage=='vocals':
                        stems['instrumental']={'path':str(other),'sha256':digest(other)}
                        if mode=='fine':inp=run/'karaoke-input';inp.mkdir();shutil.copy2(vocals,inp/'source.wav')
                    else:stems['background']={'path':str(other),'sha256':digest(other)}
                    lead=run/'lead.wav';data,sr=sf.read(vocals,always_2d=True)
                    sf.write(lead,data.mean(axis=1),sr,subtype='FLOAT')
                    stems['lead']={'path':str(lead),'sha256':digest(lead)}
                manifest['separation']={'overlap':8 if mode=='fine' else 2,'tta':mode=='fine','batch_size':1}
            manifest['stems']=stems;save()
            rvc=config['rvc'];index=local_path(config,rvc['index']) if rvc.get('index') else None
            request={'root':str(local_path(config,rvc['root'])),'model':str(local_path(config,rvc['model'])),
                     'index':str(index) if index and index.is_file() else '',
                     'input':stems['lead']['path'],'output':str(run/'converted.wav'),
                     'profile':config['profiles'][mode],'device':config['device'],'frozen_pitch':mode=='fine'}
            write_json(run/'rvc-request.json',request)
            command('convert',[executable(config,rvc['python']),'-B',Path(__file__).with_name('rvc_adapter.py'),'--request',run/'rvc-request.json'])
            from .audio import mix
            mixed=mix(ff,stems['lead']['path'],request['output'],stems['instrumental']['path'],
                      stems.get('background',{}).get('path'),run,config['mix'])
            if digest(source)!=manifest['source_sha256'] or any(digest(s['path'])!=s['sha256'] for s in stems.values()):raise ValueError('Input changed during run')
            if not source.stem or any(c in source.stem for c in '<>:"/\\|?*'):raise ValueError('Unsafe source title')
            exports=workspace/'finished';exports.mkdir(exist_ok=True)
            delivery=exports/(source.stem+'-cover-'+mode+'-'+run.name+'.mp3')
            command('encode',[ff,'-nostdin','-v','error','-n','-i',mixed['master'],'-c:a','libmp3lame','-b:a','320k',delivery])
            manifest.update(status='completed',stage=None,mix=mixed,output=str(delivery),output_sha256=digest(delivery),
                            conversion_sha256=digest(request['output']),source_models_included=False)
            save();return manifest
        except BaseException as error:
            manifest.update(status='failed',error_type=type(error).__name__);save();raise
