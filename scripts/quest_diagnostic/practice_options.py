"""Teleop-only profiles; environment actions, physics and datasets remain unchanged."""
import math


def add_arguments(parser):
    parser.add_argument('--control-profile',choices=('diagnostic','practice'),default='diagnostic')
    for name in ('position-scale','rotation-scale','max-translation','max-rotation-deg','linear-speed','angular-speed'):
        parser.add_argument('--'+name,type=float,default=None)
    parser.add_argument('--preview-hz',type=float,default=15)
    for name in ('no-home-limits','no-speed-limits','no-target-lead'):
        parser.add_argument('--'+name,action='store_true',help='Practice only; removes this teleop constraint, not robot limits')
    parser.add_argument('--workspace',choices=('table','off'),default=None,help='Practice only: fixed box or disabled')
    parser.add_argument('--max-target-lead',type=float,default=None,help='Practice metres, .01.. .5')
    parser.add_argument('--max-angular-lead-deg',type=float,default=None,help='Practice degrees, 1..120')
    parser.add_argument('--tracking-stall-seconds',type=float,default=2.,help='Practice wall seconds without meaningful progress')


def options(args):
    practice=args.control_profile=='practice'
    values=dict(position_scale=1. if practice else .25,rotation_scale=1. if practice else .5,
        max_translation=.55 if practice else .05,max_rotation_deg=120 if practice else 15,
        linear_speed=.10 if practice else .05,angular_speed=.8 if practice else .5)
    bounds=dict(position_scale=(.05,1),rotation_scale=(.05,1.5),max_translation=(.01,.75),
                max_rotation_deg=(1,180),linear_speed=(.01,.15),angular_speed=(.05,1.5))
    for key in values:
        if getattr(args,key,None) is not None:values[key]=getattr(args,key)
        lo,hi=bounds[key]
        if not math.isfinite(values[key]) or not lo<=values[key]<=hi:raise ValueError(f'{key} must be within [{lo},{hi}]')
    if not math.isfinite(args.preview_hz) or not 1<=args.preview_hz<=25:raise ValueError('preview-hz must be in [1,25]')
    special=any(getattr(args,k,False) for k in ('no_home_limits','no_speed_limits','no_target_lead')) or args.workspace is not None or args.max_target_lead is not None or args.max_angular_lead_deg is not None or args.tracking_stall_seconds!=2
    if not practice and special:raise ValueError('New constraint overrides require --control-profile practice')
    lead=.12 if args.max_target_lead is None else args.max_target_lead
    angle=45 if args.max_angular_lead_deg is None else args.max_angular_lead_deg
    for name,v,lo,hi in [('max-target-lead',lead,.01,.5),('max-angular-lead-deg',angle,1,120),('tracking-stall-seconds',args.tracking_stall_seconds,.5,10)]:
        if not math.isfinite(v) or not lo<=v<=hi:raise ValueError(f'{name} must be in [{lo},{hi}]')
    if args.no_home_limits:
        if args.max_translation is not None or args.max_rotation_deg is not None:raise ValueError('Do not combine home-limit values and --no-home-limits')
        values['max_translation']=values['max_rotation_deg']=None
    if args.no_speed_limits:
        if args.linear_speed is not None or args.angular_speed is not None:raise ValueError('Do not combine speed values and --no-speed-limits')
        values['linear_speed']=values['angular_speed']=None
    if args.no_target_lead and (args.max_target_lead is not None or args.max_angular_lead_deg is not None):raise ValueError('Do not combine lead values and --no-target-lead')
    box=practice and args.workspace!='off'
    values.update(profile=args.control_profile,practice=practice,
        max_target_lead=lead if practice and not args.no_target_lead else None,
        max_angular_lead=math.radians(angle) if practice and not args.no_target_lead else None,
        workspace_min=[.1,-.85,1.02] if box else None,workspace_max=[.85,.85,1.8] if box else None,
        tracking_stall_seconds=args.tracking_stall_seconds)
    return values


def configure(controller,values):
    for key in ('practice','position_scale','rotation_scale','max_translation','linear_speed','angular_speed',
                'max_target_lead','max_angular_lead','workspace_min','workspace_max'):
        setattr(controller,key,values[key])
    controller.max_rotation=math.radians(values['max_rotation_deg']) if values['max_rotation_deg'] is not None else None
    return controller
