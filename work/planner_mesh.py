"""Each part meshed as the CAM planner (axis-cam's axis-step) meshes a STEP: Open CASCADE
BRepMesh_IncrementalMesh, deflection 0.05 mm, angle 0.3, parallel. Prints the faces it can't
tessellate and the open edges (mesh edges used by one triangle) the planner refuses a part for.

Usage: planner_mesh.py PART.step ...
"""
import sys
sys.path.insert(0, '.')
from geo import *
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.TopLoc import TopLoc_Location
from OCP.TopAbs import TopAbs_REVERSED


def planner_mesh(shape):
    """-> (untessellated faces, open edges [(p, q)])."""
    BRepMesh_IncrementalMesh(shape.wrapped, 0.05, False, 0.3, True)
    tris, bad = [], []
    for f in shape.Faces():
        loc = TopLoc_Location()
        t = BRep_Tool.Triangulation_s(f.wrapped, loc)
        if t is None:
            bad.append(f)
            continue
        tr = loc.Transformation()
        nodes = np.array([[p.X(), p.Y(), p.Z()] for p in (t.Node(i).Transformed(tr) for i in range(1, t.NbNodes() + 1))])
        for i in range(1, t.NbTriangles() + 1):
            a, b, c = t.Triangle(i).Get()
            tris.append(nodes[[a - 1, b - 1, c - 1]])
    T = np.array(tris, dtype=np.float32).astype(np.float64)   # (the planner reads float32 STL)
    tol = 1e-4
    V = np.round(T.reshape(-1, 3) / tol).astype(np.int64)
    u, inv = np.unique(V, axis=0, return_inverse=True)
    F = inv.reshape(-1, 3)
    F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
    E = np.sort(np.r_[F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], axis=1)
    e, c = np.unique(E, axis=0, return_counts=True)
    P = u * tol
    return bad, [(P[a], P[b]) for a, b in e[c % 2 == 1]]


if __name__ == '__main__':
    for path in sys.argv[1:]:
        bad, op = planner_mesh(load(path))
        print(f'{path}: planner mesh: {len(bad)} faces not tessellated, {len(op)} open edges')
        for f in bad:
            b = f.BoundingBox()
            print(f'   face not tessellated: area {f.Area():.5f} at ({b.xmin:.2f}..{b.xmax:.2f}, {b.ymin:.2f}..{b.ymax:.2f}, z {b.zmin:.3f})')
        for p, q in op[:10]:
            print('   open edge', np.round(p, 3), np.round(q, 3))
