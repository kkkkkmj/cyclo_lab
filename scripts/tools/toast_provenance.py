"""Verify generation-time evidence and the explicitly recorded +35 mm migration."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'source/cyclo_lab/cyclo_lab/manager_based/manipulation/make_toast/config/ffw_bg2/'

def verify_fingerprint(path, expected):
    current = (ROOT / path).read_bytes()
    if hashlib.sha256(current).hexdigest() == expected:
        return
    relocation = json.loads((ROOT / 'docs/toast_quest/SCENARIO_RELOCATION.json').read_text())
    if path in relocation['sources']:
        entry = relocation['sources'][path]
        assert expected == entry['generation_sha256'], f'Generation hash mismatch: {path}'
        assert hashlib.sha256(current).hexdigest() == entry['current_sha256'], f'Unrecorded relocation edit: {path}'
        return
    # Other post-generation changes are checked against their archived source.

    replacements = {
        PREFIX + 'bimanual_env_cfg.py': [
            ('from .arm_action import StandbyPostureIKActionCfg\n',
             'from .arm_action import StandbyPostureIKActionCfg\nfrom .toast_parameters import SERVING_POPUP_HEIGHT\n'),
            ('toast_popup_extra_height: float = .015', 'toast_popup_extra_height: float = SERVING_POPUP_HEIGHT'),
        ],
        PREFIX + 'scene.py': [
            ('from isaacsim.core.utils.stage import get_current_stage\n',
             'from isaacsim.core.utils.stage import get_current_stage\nfrom .toast_parameters import SERVING_POPUP_HEIGHT\n'),
            ('Allow a 15 mm high-lift pop-up for the FFW-BG2 fingertip clearance.',
             'Allow the v2 high-lift target within the physical carriage travel limit.'),
            ('joint.CreateUpperLimitAttr(.015)', 'joint.CreateUpperLimitAttr(SERVING_POPUP_HEIGHT)'),
        ],
    }
    assert path in replacements, f'Unrecorded provenance change: {path}'
    before = (ROOT / 'measurements/toast_lift_35mm_20261109/before' / Path(path).name).read_bytes()
    assert hashlib.sha256(before).hexdigest() == expected, f'Historical source mismatch: {path}'
    migrated = before.decode()
    for old, new in replacements[path]:
        assert migrated.count(old) == 1, (path, old)
        migrated = migrated.replace(old, new)
    assert migrated.encode() == current, f'Unexpected change beyond +35 mm migration: {path}'
    params = {}
    exec((ROOT / PREFIX / 'toast_parameters.py').read_text(), params)
    assert params['SERVING_POPUP_HEIGHT'] == .035
