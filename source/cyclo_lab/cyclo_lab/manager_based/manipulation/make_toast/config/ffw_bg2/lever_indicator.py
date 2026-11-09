"""Visual-only, per-environment indication of the active automatic toast cycle."""

LED_RADIUS = .004
LED_DEPTH = .0012
# +X is the lever face. Viewed from +X with +Z up, screen-left is -Y.
# Shell face x=.1021983: lens embeds .098 mm and protrudes 1.102 mm.
LED_POSITION = (.1027, -.045, .050)
OFF_COLOR = (.025, .025, .025)
ON_COLOR = (.01, .8, .025)
ON_EMISSION = (.01, 1.2, .025)


def press_fraction(q_actual, q_up, q_down):
    """Unclamped measured fraction; preserve existing cycle/success semantics."""
    return (q_actual - q_up) / (q_down - q_up)


def indicator_on(phase):
    """ToastCycle phases: 0 idle, 1 lowering, 2 heating, 3 rising, 4 complete.

    Observe the real state machine; do not replicate its start predicate.
    """
    return (phase == 1) | (phase == 2)


class LeverIndicators:
    """Author private materials after cloning, then update only changed colors."""

    def __init__(self, stage, toaster_paths):
        from pxr import Gf, Sdf, UsdGeom, UsdShade

        self._colors = []
        self._states = [None] * len(toaster_paths)
        for path in toaster_paths:
            base = stage.GetPrimAtPath(f'{path}/base')
            if not base or base.IsInstanceProxy():
                raise RuntimeError(f'Expected writable toaster base: {path}/base')
            led_path = f'{path}/base/LeverPressLED'
            UsdGeom.Xform.Define(stage, led_path)
            lens = UsdGeom.Cylinder.Define(stage, f'{led_path}/Lens')
            lens.CreateRadiusAttr(LED_RADIUS)
            lens.CreateHeightAttr(LED_DEPTH)
            lens.CreateAxisAttr('X')
            # Idempotent authoring, including when the stage is reused.
            lens.MakeMatrixXform().Set(Gf.Matrix4d().SetTranslate(Gf.Vec3d(*LED_POSITION)))
            material = UsdShade.Material.Define(stage, f'{led_path}/Material')
            shader = UsdShade.Shader.Define(stage, f'{led_path}/Material/Shader')
            shader.CreateIdAttr('UsdPreviewSurface')
            diffuse = shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f)
            emission = shader.CreateInput('emissiveColor', Sdf.ValueTypeNames.Color3f)
            shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(.4)
            shader.CreateInput('metallic', Sdf.ValueTypeNames.Float).Set(0.0)
            material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'surface')
            UsdShade.MaterialBindingAPI.Apply(lens.GetPrim()).Bind(material)
            self._colors.append((diffuse, emission))
            # No physics API or light is added anywhere under this prim.
            diffuse.Set(Gf.Vec3f(*OFF_COLOR))
            emission.Set(Gf.Vec3f(0))

    def update(self, phase, force=False):
        from pxr import Gf

        states = indicator_on(phase).detach().cpu().tolist()
        if len(states) != len(self._colors):
            raise ValueError('LED count must match the number of environments')
        for i, on in enumerate(states):
            if force or on != self._states[i]:
                diffuse, emission = self._colors[i]
                diffuse.Set(Gf.Vec3f(*(ON_COLOR if on else OFF_COLOR)))
                emission.Set(Gf.Vec3f(*(ON_EMISSION if on else (0., 0., 0.))))
                self._states[i] = on
