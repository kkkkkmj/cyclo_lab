"""Read-only, same-recorded-frame CPU comparison. No Isaac Sim/Quest connection."""
import argparse
import io
import json
from pathlib import Path
import statistics
import sys
import time
import h5py
import numpy as np
from PIL import Image, JpegImagePlugin
from preview_encoding import encode_native_preview
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from toast_overview import compose_live


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--episode',default='demo_0')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    names=['head_cam','left_wrist_cam','right_wrist_cam']
    rows=[];old_ms=[];new_ms=[];old_bytes=[];new_bytes=[]
    def psnr(a,b):
        mse=float(np.mean((np.asarray(a,dtype=float)-np.asarray(b,dtype=float))**2))
        return 10*np.log10(255**2/mse) if mse else None
    with h5py.File(args.dataset,'r') as dataset:
        obs=dataset['data/'+args.episode+'/obs'];n=len(obs[names[0]])
        for frame in range(n):
            cameras=[Image.fromarray(obs[name][frame]) for name in names]
            start=time.perf_counter()
            legacy=compose_live(Image.new('RGB',(1152,648)),cameras,'audit')
            buf=io.BytesIO();legacy.save(buf,format='JPEG',quality=75)
            old_ms.append((time.perf_counter()-start)*1000);old_bytes.append(len(buf.getvalue()))
            encoded,meta=encode_native_preview(cameras);new_ms.append(meta['encode_ms']);new_bytes.append(len(encoded))
            old=Image.open(io.BytesIO(buf.getvalue()));new=Image.open(io.BytesIO(encoded))
            for i,(name,original) in enumerate(zip(names,cameras)):
                previous=old.crop((i*320+10,612,i*320+310,912))
                current=new.crop((i*256+6,6,i*256+250,250))
                target=480 if i==0 else 328
                reference=original.resize((target,target),Image.Resampling.BILINEAR)
                rows.append(dict(frame=frame,camera=name,
                    legacy_display_psnr_db=psnr(reference,previous.resize((target,target),Image.Resampling.BILINEAR)),
                    native_display_psnr_db=psnr(reference,current.resize((target,target),Image.Resampling.BILINEAR)),
                    native_pixel_psnr_db=psnr(original,current)))
                if frame==0:
                    original.save(args.output/(name+'_original.png'))
                    previous.save(args.output/(name+'_legacy.png'))
                    current.save(args.output/(name+'_native.png'))
            if frame==0:old_sampling=JpegImagePlugin.get_sampling(old);new_sampling=JpegImagePlugin.get_sampling(new)
    report=dict(dataset=str(args.dataset),episode=args.episode,frames=n,
      methodology='Same recorded raw RGB frames. Display PSNR uses bilinear scaling as a CPU model, not Quest optics. Legacy overview is black: total bytes/timing are NOT full live-stream benchmarks.',
      source_size=[244,244],legacy_tile=[300,300],native_tile=[244,244],
      legacy_jpeg_sampling=old_sampling,native_jpeg_sampling=new_sampling,
      legacy_cpu_ms_median=statistics.median(old_ms),native_cpu_ms_median=statistics.median(new_ms),
      legacy_placeholder_bytes_median=statistics.median(old_bytes),native_bytes_median=statistics.median(new_bytes),
      cameras={name:{key:statistics.mean(r[key] for r in rows if r['camera']==name) for key in
       ['legacy_display_psnr_db','native_display_psnr_db','native_pixel_psnr_db']} for name in names},rows=rows)
    (args.output/'report.json').write_text(json.dumps(report,indent=2))
    html='<meta charset="utf-8"><title>Same frame preview comparison</title><style>body{background:#182330;color:white;font:18px sans-serif} img{width:328px;height:328px}td{text-align:center}</style><p>B001_test_002/demo_0 frame 0 · 원본 / 기존 전송 / 새 전송 · 동일 프레임 CPU 비교 (Quest 실기 아님)</p><table><tr><th>카메라</th><th>원본 244</th><th>기존 300 Q75</th><th>새 원본 크기 Q90 4:4:4</th></tr>'
    for name in names:html+='<tr><td>'+name+'</td>'+''.join('<td><img src="'+name+'_'+suffix+'.png"></td>' for suffix in ['original','legacy','native'])+'</tr>'
    (args.output/'comparison.html').write_text(html+'</table>')
    print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))

if __name__=='__main__':main()
