"""Read visual vertices, including composed transforms and scale; no physics writes."""
import numpy as np
from pxr import Gf, Usd, UsdGeom

RIM_SUFFIX = '/visuals/base_body_30/World/mesh'
RIM_FACES = tuple(range(14))


def rotation(q):
    w, x, y, z = np.asarray(q, dtype=float)
    norm = np.linalg.norm([w, x, y, z])
    w, x, y, z = np.array([w, x, y, z]) / norm
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def rigid_frame(prim):
    matrix = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    transform = Gf.Transform(matrix)
    result = np.eye(4)
    result[:3, :3] = np.asarray(Gf.Matrix3d(transform.GetRotation()))
    result[3, :3] = np.asarray(transform.GetTranslation())
    return result


def visual_meshes(root):
    # Instance proxies retain their composed ancestor transforms.
    for prim in Usd.PrimRange(root, Usd.TraverseInstanceProxies()):
        if not prim.IsA(UsdGeom.Mesh):
            continue
        mesh = UsdGeom.Mesh(prim)
        if 'collision' in str(prim.GetPath()).lower():
            continue
        if mesh.ComputeVisibility() == 'invisible' or mesh.ComputePurpose() in ('guide', 'proxy'):
            continue
        yield mesh


def bake_mesh(mesh, frame):
    matrix = np.asarray(mesh.ComputeLocalToWorldTransform(Usd.TimeCode.Default())) @ np.linalg.inv(frame)
    points = np.asarray(mesh.GetPointsAttr().Get(), dtype=float)
    return points @ matrix[:3, :3] + matrix[3, :3], matrix


def bake_bread(root):
    frame = rigid_frame(root)
    arrays, evidence = [], []
    for mesh in visual_meshes(root):
        points, matrix = bake_mesh(mesh, frame)
        if mesh.GetSubdivisionSchemeAttr().Get() != 'none':
            raise RuntimeError('Non-polygonal render surface requires tessellation: ' + str(mesh.GetPath()))
        arrays.append(points)
        evidence.append(dict(prim=str(mesh.GetPath()), vertices=len(points),
                             mesh_to_rigid_matrix=matrix.tolist()))
    if not arrays:
        raise RuntimeError('No visible bread meshes')
    return np.concatenate(arrays), evidence


def bake_rim(base):
    prim = base.GetStage().GetPrimAtPath(str(base.GetPath()) + RIM_SUFFIX)
    if not prim or not prim.IsA(UsdGeom.Mesh):
        raise RuntimeError('Reviewed rim mesh is missing; do not substitute an AABB')
    mesh = UsdGeom.Mesh(prim)
    points, matrix = bake_mesh(mesh, rigid_frame(base))
    counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get())
    indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get())
    offsets = np.r_[0, np.cumsum(counts)]
    faces = [points[indices[offsets[i]:offsets[i+1]]] for i in RIM_FACES]
    vertices = np.concatenate(faces)
    plane = fit_plane(vertices)
    # These reviewed faces must remain a broad top deck, never the lever or walls.
    if abs(plane[2]) < .999 or not (.079 < vertices[:, 2].mean() < .082):
        raise RuntimeError('Rim geometry changed; review face selection')
    evidence = dict(prim=str(prim.GetPath()), faces=list(RIM_FACES),
                    face_vertices_body_m=[p.tolist() for p in faces],
                    mesh_to_body_matrix=matrix.tolist(), plane_body=plane.tolist(),
                    fit_max_residual_m=float(np.max(np.abs(vertices @ plane[:3] + plane[3]))),
                    definition='Least-squares plane of reviewed slot-surrounding deck faces 0..13; extended across slot opening at current bread visual AABB center XY')
    return vertices, evidence


def fit_plane(points):
    center = points.mean(0)
    _, _, vh = np.linalg.svd(points - center, full_matrices=False)
    normal = vh[-1]
    if normal[2] < 0:
        normal = -normal
    plane = np.r_[normal, -normal @ center]
    if np.max(np.abs(points @ normal + plane[3])) > 1e-5:
        raise RuntimeError('Selected rim is not planar within 0.01 mm')
    return plane


def world(points, position, quaternion):
    return points @ rotation(quaternion).T + np.asarray(position)


def measure(bread_world, rim_world):
    plane = fit_plane(rim_world)
    if abs(plane[2]) < .1:
        raise RuntimeError('Rim plane is too steep for Z-at-XY measurement')
    center = (bread_world.min(0) + bread_world.max(0)) / 2
    top, bottom = bread_world[:, 2].max(), bread_world[:, 2].min()
    rim = -(plane[0]*center[0] + plane[1]*center[1] + plane[3]) / plane[2]
    height = top - bottom
    if height <= 0:
        raise RuntimeError('Degenerate bread visual height')
    exposed = np.clip(top-rim, 0, height)
    return dict(z_top=float(top), z_bottom=float(bottom), z_rim=float(rim),
                height_mm=float(height*1000), exposed_mm=float(exposed*1000),
                exposed_pct=float(exposed/height*100)), center, plane
