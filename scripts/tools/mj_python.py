"""Fail closed on checkout/asset resolution before launching a requested script."""
import importlib.util
from pathlib import Path
import runpy
import sys

root = Path(__file__).resolve().parents[2]
# Prepend paths to override editable installs baked into the shared image.
paths = [root/'source/cyclo_lab'] + list((root/'third_party/IsaacLab/source').glob('isaaclab*'))
sys.path[:0] = [str(p) for p in paths if p.is_dir()]
spec = importlib.util.find_spec('cyclo_lab')
assert spec and Path(spec.origin).resolve().is_relative_to(root/'source/cyclo_lab'), spec
asset = root/'source/cyclo_lab/data/objects/bread_slot/rack.usda'
assert asset.is_file(), asset
print(f'MJ_CHECKOUT={root}\nMJ_CODE={spec.origin}\nMJ_RACK={asset}', flush=True)
if len(sys.argv) < 2:
    raise SystemExit('Usage: scripts/run_mj.sh scripts/<script>.py [arguments]')
script = (root/sys.argv[1]).resolve()
assert script.is_relative_to(root), script
sys.argv = [str(script), *sys.argv[2:]]
sys.path.insert(0, str(script.parent))
runpy.run_path(str(script), run_name='__main__')
