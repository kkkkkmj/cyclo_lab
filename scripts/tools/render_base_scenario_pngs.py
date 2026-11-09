"""Render fixed-base schematic PNGs using the shared current-asset card geometry."""
import argparse
import csv
import json
import re
import shutil
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin

from build_toast_overview_cards import build

ROOT = Path(__file__).resolve().parents[2]
GROUPS = ('operator_A_1', 'operator_A_2', 'operator_B_1', 'operator_B_2')
WIDTH, HEIGHT = 1600, 680
# Bound Pillow decoding to the known, locally generated 100-card canvas.
Image.MAX_IMAGE_PIXELS = WIDTH*10*(HEIGHT*10+120)


def embedded(html, name):
    return json.loads(re.search(r'<script id="'+name+r'"[^>]*>(.*?)</script>', html, re.S).group(1))


def patch(ax, data, color, edge, linewidth=.7, **kwargs):
    """Shared SVG paths contain only M/L/Z rings; preserve winding and holes."""
    vertices, codes = [], []
    for ring in re.findall(r'M([^MZ]+)Z', data):
        points = [tuple(map(float, p.split(','))) for p in ring.split(' L')]
        vertices.extend(points + [points[0]])
        codes.extend([MplPath.MOVETO] + [MplPath.LINETO]*(len(points)-1) + [MplPath.CLOSEPOLY])
    ax.add_patch(PathPatch(MplPath(vertices, codes), facecolor=color, edgecolor=edge,
                           linewidth=linewidth, **kwargs))


def render(card, meta, frame, support, path):
    fig = plt.figure(figsize=(10, 4.25), dpi=160, facecolor='white')
    fig.text(.025, .94, f"{card['group']}   |   group_index {card['index']:02d} / 25",
             fontsize=14, weight='bold', color='#357456')
    fig.text(.025, .87, card['id'], fontsize=16, weight='bold', color='#203431')
    ax = fig.add_axes([.025, .22, .95, .59])
    x, y, width, height = map(float, meta['viewBox'].split())
    ax.set_xlim(x, x+width); ax.set_ylim(y+height, y)
    ax.set_aspect('equal'); ax.axis('off')
    patch(ax, frame, '#f3f5f1', '#9ca99f', 1, linestyle='--')
    patch(ax, support, '#e8ede4', '#5b7062', 1)
    for name, color, edge in [('toaster','#e69348','#b96827'),('plate','#4c95ca','#286491'),
                               ('bread_shelf','#acd1b3','#4f8964')]:
        patch(ax, card['shapes'][name], color, edge)
    patch(ax, card['rack_top'], '#559f77', '#3d7756', .5)
    for i in range(4): patch(ax, card['shapes'][f'bread_{i}'], '#edcf95', '#9f753b', .5)
    fig.text(.80,.87,'↑ +X   ← +Y',fontsize=13,color='#52655a')
    fig.text(.025,.16,'Toaster',color='#b96827',fontsize=12)
    fig.text(.17,.16,'Plate',color='#286491',fontsize=12)
    fig.text(.28,.16,'Bread rack + 4 slices',color='#357456',fontsize=12)
    fig.text(.025,.095,'Schematic top view — not a simulation screenshot',fontsize=11,color='#526158')
    fig.text(.025,.04,'Same coordinate bounds and scale on every card  |  +X up, +Y left',fontsize=10,color='#526158')
    fig.savefig(path, dpi=160, metadata={'scenario_id':card['id'],
        'scenario_group':card['group'],'group_index':str(card['index']),
        'manifest_sha256':meta['manifest_sha256'],
        'poses':json.dumps(card['poses'],sort_keys=True), 'viewBox':meta['viewBox']})
    plt.close(fig)


def sheet(cards, output, name, columns, meta):
    banner = 120
    result = Image.new('RGB',(columns*WIDTH, ((len(cards)+columns-1)//columns)*HEIGHT+banner),'#edf3ee')
    draw=ImageDraw.Draw(result)
    font_path=matplotlib.font_manager.findfont('DejaVu Sans')
    draw.text((40,15),name,fill='#203431',font=ImageFont.truetype(font_path,42))
    draw.text((40,72),'Schematic top view — not a simulation screenshot | +X up, +Y left',
              fill='#526158',font=ImageFont.truetype(font_path,28))
    for i,card in enumerate(cards):
        with Image.open(output/'individual'/f"{card['id']}.png") as im:
            result.paste(im.convert('RGB'),((i%columns)*WIDTH,banner+(i//columns)*HEIGHT))
    info=PngImagePlugin.PngInfo()
    info.add_text('scenario_ids',json.dumps([c['id'] for c in cards]))
    info.add_text('manifest_sha256',meta['manifest_sha256'])
    info.add_text('viewBox',meta['viewBox'])
    result.save(output/f'{name}.png',pnginfo=info)
    result.close()


def generate(delivery, output):
    manifest=json.loads((delivery/'manifest.json').read_text())
    assert manifest['schema_version']==2 and manifest['generation'].get('reference_poses'), 'Expected a fixed-reference delivery'
    order=manifest['generation']['object_order']
    assert len(order)==3 and set(order)=={'toaster','plate','bread_shelf'}, 'Invalid fixed object order'
    original=(delivery/'overview_cards.html').read_text()
    original_cards=embedded(original,'scenario-data')
    # Build in isolation: no checked-in HTML, poses or assignment files are written.
    with tempfile.TemporaryDirectory(prefix='toast-png-geometry-') as tmp:
        tmp=Path(tmp)
        for name in ('manifest.json','assignments.csv'):shutil.copyfile(delivery/name,tmp/name)
        (tmp/'inputs').mkdir()
        shutil.copyfile(delivery/'inputs/table_frame.json',tmp/'inputs/table_frame.json')
        build(tmp,tmp/'inputs/table_frame.json')
        html=(tmp/'overview_cards.html').read_text()
    cards=embedded(html,'scenario-data');meta=embedded(html,'geometry-meta')
    assert cards==original_cards, 'Current assets/config no longer match saved card geometry'
    assert len(cards)==len({c['id'] for c in cards})==100
    entries={e['id']:e for e in manifest['scenarios']}
    with (delivery/'poses.csv').open() as stream: rows=list(csv.DictReader(stream))
    assert len(rows)==len({(r['scenario_id'],r['object']) for r in rows})==700
    for r in rows:
        p=entries[r['scenario_id']]['poses'][r['object']]
        assert [float(r[k]) for k in ('x','y','z','qw','qx','qy','qz','sx','sy','sz')]==[*p['position_m'],*p['quaternion_wxyz'],*p['scale']]
    for c in cards:
        e=entries[c['id']]
        assert c['poses']==e['poses'] and c['group']==e['scenario_group'] and c['index']==e['group_index']
        assert c['order']==e['order_positive_to_negative_y']==order, 'Card/manifest fixed order mismatch'
    # Reuse the exact frame/support paths inserted by the shared HTML builder.
    frame=re.search(r'<path d="([^"]+)" fill="#f3f5f1"',html).group(1)
    support=re.search(r'<path d="([^"]+)" fill="#e8ede4"',html).group(1)
    output.mkdir(parents=True,exist_ok=True);(output/'individual').mkdir(exist_ok=True)
    expected={c['id']+'.png' for c in cards}
    assert not {p.name for p in (output/'individual').glob('*.png')}-expected, 'Unexpected existing PNGs'
    cards.sort(key=lambda c:(c['group'],c['index']))
    for card in cards:render(card,meta,frame,support,output/'individual'/f"{card['id']}.png")
    for group in GROUPS:
        selected=[c for c in cards if c['group']==group]
        assert [c['index'] for c in selected]==list(range(1,26))
        sheet(selected,output,group,5,meta)
    sheet(cards,output,'overview_100',10,meta)
    for c in cards:
        with Image.open(output/'individual'/f"{c['id']}.png") as im:
            assert im.size==(WIDTH,HEIGHT) and im.info['scenario_id']==c['id']
            assert json.loads(im.info['poses'])==c['poses'];im.verify()
    for group in (*GROUPS,'overview_100'):
        with Image.open(output/f'{group}.png') as im:
            expected_ids=[c['id'] for c in cards if group=='overview_100' or c['group']==group]
            assert json.loads(im.info['scenario_ids'])==expected_ids
            assert im.width>=5000;im.verify()
    print(json.dumps({'output':str(output),'individual_count':100,'group_count':4,
                      'individual_px':[WIDTH,HEIGHT],'group_px':[WIDTH*5,HEIGHT*5+120],
                      'overview_px':[WIDTH*10,HEIGHT*10+120],'manifest_sha256':meta['manifest_sha256']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delivery',type=Path,default=ROOT/'scenario_delivery_base')
    parser.add_argument('--output',type=Path,help='Defaults to DELIVERY/images')
    args=parser.parse_args();generate(args.delivery,args.output or args.delivery/'images')
