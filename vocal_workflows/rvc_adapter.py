"""Adapter for the legacy RVC VC.vc_single API; upstream code is not vendored."""
import argparse,json,os,sys
from pathlib import Path

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--request',required=True)
    request=json.loads(Path(parser.parse_args().request).read_text(encoding='utf-8'))
    root=Path(request['root']);model=Path(request['model']);output=Path(request['output'])
    if output.exists():raise FileExistsError('Refusing to overwrite converted audio')
    os.chdir(root);sys.path.insert(0,str(root));sys.argv=sys.argv[:1]
    os.environ.update(weight_root=str(model.parent),index_root=str(Path(request['index']).parent) if request['index'] else str(output.parent),
                      rmvpe_root=str(root/'assets/rmvpe'),NUMBA_CACHE_DIR=str(output.parent/'numba-cache'))
    import numpy as np,torch,soundfile as sf
    from types import SimpleNamespace,MethodType
    from infer.modules.vc.modules import VC
    profile=request['profile'];device=request['device']
    if device=='cuda' and not torch.cuda.is_available():raise RuntimeError('CUDA unavailable; explicitly choose CPU')
    if device=='cpu' and profile['half']:raise ValueError('CPU requires half=false')
    cfg=SimpleNamespace(device='cuda:0' if device=='cuda' else 'cpu',is_half=profile['half'],use_jit=False,
                        x_pad=1,x_query=6,x_center=38,x_max=41)
    torch.set_num_threads(2);torch.manual_seed(1234);np.random.seed(1234)
    vc=VC(cfg);vc.get_vc(model.name)
    shift=profile['semitones']
    if request['frozen_pitch']:
        from scipy.signal import filtfilt
        from infer.lib.audio import load_audio
        from infer.modules.vc.pipeline import bh,ah
        audio=np.ascontiguousarray(filtfilt(bh,ah,load_audio(request['input'],16000)),dtype=np.float32)
        pitch=np.zeros(int(np.ceil(len(audio)/160))+1,dtype=np.float32)
        for lo in range(0,len(audio),20*16000):
            hi=min(len(audio),lo+20*16000);a=max(0,lo-16000);b=min(len(audio),hi+16000)
            _,f=vc.pipeline.get_f0(request['input'],audio[a:b],(b-a)//160+1,0,'rmvpe',3)
            first=lo//160;last=min(len(pitch),int(np.ceil(hi/160)))
            indices=np.arange(first,last)-a//160;pitch[first:last]=f[np.minimum(indices,len(f)-1)]
        if len(pitch)<2 or not np.isfinite(pitch).all() or not np.any(pitch>0):raise ValueError('Invalid pitch track')
        pitch[-1]=pitch[-2]
        if abs((len(pitch)-1)/100-sf.info(request['input']).duration)>.03:raise ValueError('Pitch timeline mismatch')
        np.save(output.parent/'pitch-100hz.npy',pitch)
        work=pitch*2**(shift/12)
        def frozen(self,input_audio_path,x,p_len,f0_up_key,f0_method,filter_radius,inp_f0=None):
            if f0_up_key!=0:raise ValueError('Pitch shift would be applied twice')
            i=np.arange(p_len)-round(self.x_pad*100);i=np.where(i<0,-i,i)
            i=np.where(i>=len(work),2*(len(work)-1)-i,i);f=work[np.clip(i,0,len(work)-1)].copy()
            mel=1127*np.log1p(f/700);v=mel>0
            mel[v]=(mel[v]-1127*np.log1p(50/700))*254/(1127*np.log1p(1100/700)-1127*np.log1p(50/700))+1
            return np.rint(np.clip(mel,1,255)).astype(np.int32),f
        vc.pipeline.get_f0=MethodType(frozen,vc.pipeline);shift=0
    info,(sr,audio)=vc.vc_single(0,request['input'],shift,None,'rmvpe',request['index'],'',
                               profile['index_rate'],3,0,profile['rms_mix_rate'],profile['protect'])
    if sr is None or audio is None:raise RuntimeError('RVC inference failed; inspect the local adapter log')
    sf.write(output,audio,sr)
    print(json.dumps({'ok':True,'sample_rate':sr,'frozen_pitch':request['frozen_pitch']}))

if __name__=='__main__':main()
