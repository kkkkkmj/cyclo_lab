"""Build the metre/Z-up static rack wrapper. Run with a pxr-enabled Python."""
from pathlib import Path
from pxr import Usd, UsdGeom, UsdPhysics, Gf

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'source/cyclo_lab/data/objects/bread_slot'

def main():
    source = Usd.Stage.Open(str(DIRECTORY / 'bread_slot.usdz'))
    assert UsdGeom.GetStageMetersPerUnit(source) == .001
    assert UsdGeom.GetStageUpAxis(source) == 'Y'
    stage = Usd.Stage.CreateNew(str(DIRECTORY / 'rack.usda'))
    UsdGeom.SetStageMetersPerUnit(stage, 1)
    UsdGeom.SetStageUpAxis(stage, 'Z')
    root = UsdGeom.Xform.Define(stage, '/BreadSlot')
    stage.SetDefaultPrim(root.GetPrim())
    model = UsdGeom.Xform.Define(stage, '/BreadSlot/Model')
    model.GetPrim().GetReferences().AddReference('bread_slot.usdz')
    # Preserve original pivot; actual extracted tabletop is z=.994051338865205 m.
    model.AddTranslateOp().Set(Gf.Vec3d(0, 0, .994051338865205 - 1.0382))
    model.AddRotateXOp().Set(90)
    model.AddScaleOp().Set(Gf.Vec3f(.001))
    mesh = stage.GetPrimAtPath('/BreadSlot/Model/Body1')
    UsdPhysics.CollisionAPI.Apply(mesh).CreateCollisionEnabledAttr(True)
    # Exact triangles are supported for static (non-rigid-body) PhysX meshes.
    UsdPhysics.MeshCollisionAPI.Apply(mesh).CreateApproximationAttr('none')
    stage.GetRootLayer().Save()

if __name__ == '__main__':
    main()
