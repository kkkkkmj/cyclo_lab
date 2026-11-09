"""Read-only bridge sampler. No network, simulator start, or process termination."""
import argparse,json,time,statistics
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--bridge-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=float,default=10);a=p.parse_args()
 frames={};packets={};start=time.monotonic()
 while time.monotonic()-start<a.seconds:
  try:
   f=json.loads((a.bridge_dir/'preview.json').read_text());s=json.loads((a.bridge_dir/'input.json').read_text());packet=s.get('packet') or {}
   frames[(f.get('run_id'),f.get('frame_id'))]=f;packets[(packet.get('session'),packet.get('seq'))]=s
  except (OSError,ValueError):pass
  time.sleep(.02)
 def metrics(values):
  v=sorted(float(x) for x in values if isinstance(x,(float,int)))
  return dict(n=len(v),median=statistics.median(v),p95=v[min(len(v)-1,int(len(v)*.95))]) if v else None
 rows=list(frames.values());pr=[x.get('packet') or {} for x in packets.values()]
 report=dict(sample_wall_s=time.monotonic()-start,unique_frames=len(rows),unique_input_packets=len(pr),
  frame_interval_ms=metrics(f.get('timings',{}).get('frame_interval_ms') for f in rows),
  step_ms=metrics(f.get('timings',{}).get('step_ms') for f in rows),
  encode_ms=metrics(f.get('timings',{}).get('encoding',{}).get('encode_ms') for f in rows),
  input_age_at_loop_ms=metrics(f.get('timings',{}).get('teleop',{}).get('input_age_ms') for f in rows),
  quest_fetch_decode_ms=metrics(x.get('preview_status',{}).get('fetch_decode_ms') for x in pr),
  quest_decode_ms=metrics(x.get('preview_status',{}).get('decode_ms') for x in pr),
  quest_frame_age_ms=metrics(x.get('preview_status',{}).get('frame_age_ms') for x in pr),
  phases=sorted(set(f.get('timings',{}).get('episode_state','unknown') for f in rows)),
  receive_to_process_ms=metrics(f.get('timings',{}).get('performance',{}).get('receive_to_process_ms') for f in rows),
  receive_to_first_apply_ms=metrics(f.get('timings',{}).get('performance',{}).get('receive_to_first_apply_ms') for f in rows),
  receive_to_first_physics_ms=metrics(f.get('timings',{}).get('performance',{}).get('receive_to_first_physics_ms') for f in rows),
  stages={stage:metrics(f.get('timings',{}).get('performance',{}).get('wall_call_ms',{}).get(stage) for f in rows)
          for stage in ['physics_call','render_call','observations','scene_update']},
  camera_readback_ms=metrics(f.get('timings',{}).get('performance',{}).get('camera_readback_ms') for f in rows),
  final_status=rows[-1].get('status') if rows else None,frames=rows,packets=list(packets.values()))
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('x') as f:json.dump(report,f,indent=2)
 print(json.dumps({k:v for k,v in report.items() if k not in ('frames','packets')},indent=2))
if __name__=='__main__':main()
