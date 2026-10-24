"""Static-gain mixing only. No learned model or network access."""
import json,re,subprocess
from pathlib import Path

def measure(ffmpeg,file):
    r=subprocess.run([ffmpeg,'-hide_banner','-nostats','-i',str(file),'-af',
                      'loudnorm=I=-20:TP=-1:LRA=11:print_format=json','-f','null','-'],
                     capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
    data=json.loads(re.findall(r'\{\s*"input_i".*?\}',r.stderr,re.S)[-1])
    return float(data['input_i']),float(data['input_tp'])

def mix(ffmpeg,lead,converted,instrumental,background,out,settings):
    import numpy as np,soundfile as sf
    from scipy.ndimage import maximum_filter1d,gaussian_filter1d
    out=Path(out);resampled=out/'converted-44k.wav'
    subprocess.run([ffmpeg,'-nostdin','-v','error','-n','-i',str(converted),'-af',
                    'aresample=44100:resampler=soxr:precision=28','-ac','1','-c:a','pcm_f32le',str(resampled)],check=True)
    voice,sr=sf.read(resampled,dtype='float64');original,rate=sf.read(lead,dtype='float64',always_2d=True)
    if rate!=44100 or sr!=44100 or abs(len(voice)-len(original))>=4410:raise ValueError('Converted-lead timeline mismatch')
    voice=np.pad(voice,(0,max(0,len(original)-len(voice))))[:len(original)]
    mono=original.mean(axis=1);hop=441
    energy=np.array([np.sqrt(np.mean(mono[i:i+hop]**2)) for i in range(0,len(mono),hop)])
    active=gaussian_filter1d(maximum_filter1d((energy>10**(-50/20)).astype(float),size=25),sigma=2)
    gate=np.interp(np.arange(len(mono)),np.arange(len(active))*hop,active)
    masked=out/'converted-masked.wav';sf.write(masked,voice*gate,sr,subtype='FLOAT')
    backing,bsr=sf.read(instrumental,dtype='float64',always_2d=True)
    if bsr!=sr or len(backing)!=len(mono):raise ValueError('Instrumental timeline mismatch')
    if background:
        bg,gsr=sf.read(background,dtype='float64',always_2d=True)
        if gsr!=sr or bg.shape!=backing.shape:raise ValueError('Background timeline mismatch')
        backing+=bg
    if not np.isfinite(backing).all() or not np.isfinite(voice).all():raise ValueError('Non-finite samples')
    backing_file=out/'original-backing.wav';sf.write(backing_file,backing,sr,subtype='FLOAT')
    vl,_=measure(ffmpeg,masked);bl,_=measure(ffmpeg,backing_file)
    if not np.isfinite([vl,bl]).all():raise ValueError('Silent lead or backing cannot be normalized')
    vg=settings['lead_lufs']-vl;bgain=settings['backing_lufs']-bl
    mixed=backing*10**(bgain/20)+(voice*gate*10**(vg/20))[:,None]
    premix=out/'premix.wav';sf.write(premix,mixed,sr,subtype='FLOAT')
    pl,_=measure(ffmpeg,premix);gain=settings['final_lufs']-pl;mixed*=10**(gain/20)
    cap=settings['true_peak_db'];peak=float(np.max(np.abs(mixed)))
    capgain=min(0.,cap-20*np.log10(max(peak,1e-12)));mixed*=10**(capgain/20)
    final=out/'final.wav';sf.write(final,mixed,sr,subtype='PCM_24');lufs,tp=measure(ffmpeg,final)
    if tp>cap:
        extra=cap-.05-tp;mixed*=10**(extra/20);capgain+=extra
        sf.write(final,mixed,sr,subtype='PCM_24');lufs,tp=measure(ffmpeg,final)
    if not np.isfinite(mixed).all() or np.max(np.abs(mixed))>=1 or tp>cap+.01:raise ValueError('Final peak check failed')
    return {'master':str(final),'duration_sec':len(mixed)/sr,'sample_rate':sr,'lufs':lufs,'true_peak_db':tp,
            'lead_gain_db':vg,'backing_gain_db':bgain,'mix_gain_db':gain,'peak_gain_db':capgain,
            'background_preserved':bool(background),'background_relative_gain_db':0,
            'effects':'activity mask on converted lead; static gains only; no EQ/compression/reverb'}
