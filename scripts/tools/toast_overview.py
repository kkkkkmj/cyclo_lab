"""Shared observation-only camera used by replay export and live Quest view."""
EYE = (3.1, 0., 2.)
TARGET = (.35, 0., 1.)
WIDTH, HEIGHT = 1152, 648


def overview_cfg():
    import isaaclab.sim as sim_utils
    from isaaclab.sensors import CameraCfg
    return CameraCfg(prim_path='{ENV_REGEX_NS}/ReplayOverview',width=WIDTH,height=HEIGHT,
                     update_period=0,data_types=['rgb'],spawn=sim_utils.PinholeCameraCfg(
                         focal_length=20.,horizontal_aperture=24.,clipping_range=(.05,100.)))


def position_overview(env, eye=EYE, target=TARGET):
    import torch
    origin=env.scene.env_origins[:1]
    env.scene['replay_overview'].set_world_poses_from_view(
        torch.tensor([eye],device=env.device)+origin,torch.tensor([target],device=env.device)+origin)


def compose_live(overview, cameras, status):
    """16:9 overview and square original camera tiles, all aspect-preserving."""
    from PIL import Image, ImageDraw, ImageFont
    panel=Image.new('RGB',(960,936),'#101c2b')
    draw=ImageDraw.Draw(panel)
    try:font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    except OSError:font=ImageFont.load_default()
    draw.text((16,8),'FRONT OVERVIEW',fill='white',font=font)
    panel.paste(overview.resize((960,540)),(0,36))
    for i,(name,picture) in enumerate(zip(('HEAD','LEFT WRIST','RIGHT WRIST'),cameras)):
        draw.text((i*320+12,584),name,fill='white',font=font)
        panel.paste(picture.resize((300,300)),(i*320+10,612))
    draw.text((12,915),status[:100],fill='white',font=font)
    return panel
