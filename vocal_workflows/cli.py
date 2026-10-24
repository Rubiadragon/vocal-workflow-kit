import argparse,json,sys,zipfile,platform
from pathlib import Path
from . import __version__
from .core import load_config,doctor
from .training import audit_dataset,training_plan

def main(argv=None):
    ap=argparse.ArgumentParser(description='Local voice workflows; no bundled models, songs, or credentials')
    ap.add_argument('--config',default='config.local.json');sub=ap.add_subparsers(dest='action',required=True)
    p=sub.add_parser('doctor');p.add_argument('--json',action='store_true');p.add_argument('--speech',action='store_true')
    p=sub.add_parser('dataset-audit');p.add_argument('directory')
    p=sub.add_parser('train-plan');p.add_argument('--kind',choices=['rvc','speech'],default='rvc');p.add_argument('--experiment',default='example_voice');p.add_argument('--epochs',type=int,default=100);p.add_argument('--batch',type=int,default=4)
    for name in ('fine','quick'):
        p=sub.add_parser(name);p.add_argument('--source',required=True);p.add_argument('--dry-run',action='store_true')
        p.add_argument('--reuse');p.add_argument('--roles-confirmed',action='store_true')
    p=sub.add_parser('speak');p.add_argument('--text',required=True);p.add_argument('--dry-run',action='store_true')
    p=sub.add_parser('support-bundle');p.add_argument('--out',required=True)
    args=ap.parse_args(argv)
    try:
        if args.action=='dataset-audit':result=audit_dataset(args.directory)
        else:
            config=load_config(args.config)
            if args.action=='doctor':
                result=doctor(config)
                if args.speech:
                    from .speech import speech_doctor
                    result['speech']=speech_doctor(config)
            elif args.action=='train-plan':
                result=training_plan(config,args.experiment,args.epochs,args.batch) if args.kind=='rvc' else {
                    'execute':False,'kind':'speech','guide':'docs/04-speech.md',
                    'stages':['authorized dataset','upstream ASR and manual transcript correction','reference segmentation',
                              'upstream text/semantic preparation','SoVITS fine-tuning','GPT fine-tuning','held-out synthesis test'],
                    'warning':'Use the GPT-SoVITS UI matching your installed version. Do not load RVC weights into TTS.'}
            elif args.action in ('fine','quick'):
                from .pipeline import plan,run_cover
                result=plan(config,args.action,args.source,args.reuse) if args.dry_run else run_cover(config,args.action,args.source,args.reuse,args.roles_confirmed)
            elif args.action=='speak':
                if args.dry_run:result={'execute':False,'kind':'speech','characters':len(args.text),'note':'No API call made; voice quality untested'}
                else:
                    from .speech import speak
                    result=speak(config,args.text)
            else:
                target=Path(args.out)
                if target.exists():raise FileExistsError('Support bundle already exists; refusing overwrite')
                target.parent.mkdir(parents=True,exist_ok=True)
                # Strict allowlist. Never copy config, logs, audio, workspace, or env.
                result={'schema_version':1,'tool_version':__version__,'python':platform.python_version(),
                        'system':platform.system(),'diagnostics':doctor(config),
                        'excluded':['configuration values','paths','host/user names','environment','logs','audio','weights','messages']}
                with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr('diagnostics.json',json.dumps(result,ensure_ascii=False,indent=2))
                result={'status':'completed','bundle':str(target),'files':['diagnostics.json'],'upload_performed':False}
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if args.action=='doctor' and not result['ok']:return 2
        return 0
    except Exception as error:
        print(json.dumps({'ok':False,'error_type':type(error).__name__,'message':str(error)},ensure_ascii=False),file=sys.stderr)
        return 1
