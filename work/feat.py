"""Small feature library for the parametric case model (model.py): exact faces with lines and
arcs from 2D outlines, prisms, planes, and reference sections of the original parts."""
import sys
sys.path.insert(0, '.')
from geo import *
import shapely
import shapely.geometry as sg
from shapely.ops import unary_union
import mill

R = mill.R_CUT          # every inside corner the Ø2 mill cuts is at least this radius


# ------------------------------------------------------------------ 2D
def pieces(g):
    return mill.pieces(g)


GRID = 1e-4            # every outline is snapped to this grid: edges two features share coincide


def snap(g):
    return shapely.make_valid(shapely.set_precision(g, GRID)) if not g.is_empty else g


def outer(g):
    """The region with its holes filled."""
    return snap(unary_union([sg.Polygon(p.exterior) for p in pieces(g)]))


def clean2d(g, tol=0.01, min_area=0.05):
    """Drop the mesh's noise: specks, slivers, near-collinear vertices."""
    g = g.buffer(-tol, quad_segs=2).buffer(tol, quad_segs=2)
    return snap(unary_union([p.simplify(tol / 2) for p in pieces(g) if p.area > min_area]))


def mill_material(g, r=R):
    """Material outline the mill can make from outside: concave corners at least r."""
    return snap(mill.no_pinholes(g.buffer(r, quad_segs=mill.QS)).buffer(-r, quad_segs=mill.QS))


def mill_pocket(g, r=R):
    """Pocket the mill can make, containing g: dogbones at its corners (mill.open_superset)."""
    return snap(unary_union([mill.open_superset(p, r) for p in pieces(g)]))


# ------------------------------------------------------------------ 3D
def face(poly, z=0.0):
    """Exact planar face of a polygon at height z: its outline fitted with lines and true arcs
    within 0.002 mm (clean.py's fitter)."""
    import clean
    from shapely.geometry.polygon import orient
    poly = orient(shapely.remove_repeated_points(poly, 3 * GRID), 1.0)
    C, seg = clean.chains([poly])
    F = clean.fit_chains(C)
    f = clean.region_face(poly, C, F, seg, z)
    out = cq.Face(f)
    for mode in ('lines', 'raw'):
        if out.isValid() and abs(out.Area() - poly.area) < 0.01 + 0.005 * poly.area:
            break
        F = clean.fit_chains(C, modes=[mode] * len(C))
        out = cq.Face(clean.region_face(poly, C, F, seg, z))
    assert out.isValid(), ('face', poly.bounds, poly.area)
    return out


def prism(g, z0, z1):
    """Exact prism(s) of a region between two heights. An outline that touches itself (a hole
    meeting the outside at a point) is first split there (or closed) by 2 grid steps."""
    out = []
    for p in pieces(snap(g)):
        if p.area < 1e-4:
            continue
        for q in (p, p.buffer(-2 * GRID, join_style=2).buffer(2 * GRID, join_style=2),
                  p.buffer(2 * GRID, join_style=2).buffer(-2 * GRID, join_style=2)):
            try:
                fs = [face(r, z0) for r in pieces(snap(q)) if r.area > 1e-4]
                break
            except (AssertionError, Exception):
                fs = None
        assert fs is not None, ('prism', p.bounds, p.area)
        out += [cq.Solid.extrudeLinear(f, cq.Vector(0, 0, z1 - z0)) for f in fs]
    return out


def prisms(items):
    """Prisms of several related regions [(region, z0, z1)], their outlines fitted together: a
    stretch of outline two regions share (nested pocket layers, stacked bands) is fitted once, so
    both get the very same lines and arcs (no hairline slivers where they meet). An outline that
    touches itself (a hole meeting the outside at a point) is split there by 2 grid steps."""
    import clean
    from shapely.geometry.polygon import orient
    P, Z = [], []
    for g, z0, z1 in items:
        for q in pieces(snap(g)):
            q = orient(shapely.remove_repeated_points(q, 3 * GRID), 1.0)
            if q.area > 1e-4:
                P.append(q); Z.append((z0, z1))
    if not P:
        return []
    for attempt in range(3):
        C, seg = clean.chains(P)
        modes = ['fit'] * len(C)
        users = [clean.ring_chains(q, seg) for q in P]
        for rnd in range(3):
            F = clean.fit_chains(C, modes=modes)
            faces, bad = [], []
            for i, q in enumerate(P):
                try:
                    f = cq.Face(clean.region_face(q, C, F, seg, Z[i][0]))
                    ok = f.isValid() and abs(f.Area() - q.area) < 0.01 + 0.005 * q.area
                except Exception:
                    f, ok = None, False
                if not ok:
                    bad.append(i)
                faces.append(f)
            if not bad:
                return [cq.Solid.extrudeLinear(f, cq.Vector(0, 0, z1 - z0)) for f, (z0, z1) in zip(faces, Z)]
            nxt = {'fit': 'lines', 'lines': 'raw', 'raw': 'raw'}
            for i in bad:
                for ci in users[i]:
                    modes[ci] = nxt[modes[ci]]
        # split the outlines that still fail where they touch themselves (an opening by 2 grid
        # steps, then a closing), and fit everything again
        e = 2 * GRID * (attempt + 1)
        nP, nZ = [], []
        for i, (q, z) in enumerate(zip(P, Z)):
            if i in bad:
                r = q.buffer(-e, join_style=2).buffer(e, join_style=2) if attempt % 2 == 0 else \
                    q.buffer(e, join_style=2).buffer(-e, join_style=2)
                for t in pieces(snap(r)):
                    t = orient(shapely.remove_repeated_points(t, 3 * GRID), 1.0)
                    if t.area > 1e-4:
                        nP.append(t); nZ.append(z)
            else:
                nP.append(q); nZ.append(z)
        P, Z = nP, nZ
    raise AssertionError(('prisms: faces still invalid', [P[i].bounds for i in bad[:5]]))


def compound(solids):
    return cq.Compound.makeCompound(solids)


def _bop(kind, base, tools, fuzzy):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut
    from OCP.TopTools import TopTools_ListOfShape
    args, tl = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(base.wrapped)
    for t in tools:
        tl.Append(t.wrapped)
    op = BRepAlgoAPI_Fuse() if kind == 'fuse' else BRepAlgoAPI_Cut()
    op.SetArguments(args); op.SetTools(tl)
    op.SetRunParallel(True); op.SetUseOBB(True)
    if fuzzy:
        op.SetFuzzyValue(fuzzy)
    op.Build()
    if not op.IsDone():
        return None
    r = cq.Shape.cast(op.Shape())
    sols = sorted([x for x in r.Solids() if x.Volume() > 0], key=lambda x: -x.Volume())
    if not sols:
        return None
    if kind == 'fuse':
        from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
        u = ShapeUpgrade_UnifySameDomain(sols[0].wrapped if len(sols) == 1 else r.wrapped, True, True, True)
        u.Build()
        r = cq.Shape.cast(u.Shape())
        sols = sorted([x for x in r.Solids() if x.Volume() > 0], key=lambda x: -x.Volume())
    return sols


LOOSE = []   # (what, volume, bounding box) of loose pieces a cut left and the model dropped


def _checked(kind, base, tools, fuzzy, what, loose_max=0.0, overlapping=False):
    """One boolean of all tools at once; the result must be one valid solid: a fuse keeps at least
    the base and the biggest tool, a cut never grows. Retried with a small fuzzy value, then an
    error (a model feature is never dropped silently)."""
    v0 = base.Volume()
    big = max((t.Volume() for t in tools), default=0.0)
    tried = []
    need = None
    if kind == 'fuse' and not overlapping:   # each tool's part outside the base
        need = 0.0
        for t in tools:
            r = _bop('cut', t, [base], 0.0)
            need = None if r is None or need is None else need + sum(x.Volume() for x in r)
    for fz in (fuzzy, 1e-5, 1e-4):
        sols = _bop(kind, base, tools, fz)
        tried.append((fz, None if sols is None else [(round(x.Volume(), 3), x.isValid()) for x in sols[:6]]))
        if sols and len(sols) > 1 and loose_max > 0 and sum(x.Volume() for x in sols[1:]) <= loose_max:
            for x in sols[1:]:
                b = x.BoundingBox()
                LOOSE.append((what, round(x.Volume(), 4), [round(v, 2) for v in (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)]))
            sols = sols[:1]
        if not sols or len(sols) != 1 or not sols[0].isValid():
            continue
        v = sols[0].Volume()
        if kind == 'fuse' and v < max(v0, big) - 1e-3:
            continue
        if kind == 'fuse' and need is not None and v < v0 + 0.9 * need - 0.01:
            continue   # a tool was dropped (tools overlapping each other count once: 0.9)
        if kind == 'cut' and v > v0 + 1e-3:
            continue
        return sols[0]
    raise AssertionError((what, kind, 'failed', len(tools), 'tools', 'base', round(v0, 2), 'tried', tried))


def fuse(base, tools, fuzzy=0.0, what='fuse', overlapping=False):
    """overlapping: the tools overlap each other (the check that every tool added its own volume
    is left out; the result must still be one valid solid holding the base)."""
    return _checked('fuse', base, tools, fuzzy, what, overlapping=overlapping) if tools else base


def cut(base, tools, fuzzy=0.0, what='cut', loose_max=0.0):
    """loose_max: a cut may leave loose specks up to this volume in total (dropped, listed in
    LOOSE); otherwise the result must be one solid."""
    return _checked('cut', base, tools, fuzzy, what, loose_max) if tools else base


def half_space(point, normal, size=400.0):
    """A big box on the side of the plane (point, normal) the normal points to."""
    n = cq.Vector(*normal).normalized()
    x = n.cross(cq.Vector(0, 0, 1)) if abs(n.z) < 0.99 else cq.Vector(1, 0, 0)
    pl = cq.Plane(origin=cq.Vector(*point), xDir=x, normal=n)
    return cq.Workplane(pl).rect(size, size).extrude(size).val()


def fit_plane(pts):
    """Least-squares plane through points: (centroid, unit normal with nz > 0), rms."""
    c = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - c)
    n = vt[-1]
    if n[2] < 0:
        n = -n
    rms = float(np.sqrt(np.mean(((pts - c) @ n) ** 2)))
    return c, n, rms


# ------------------------------------------------------------------ reference
class Ref:
    """The original part as a reference: sections and vertical rays."""
    def __init__(self, path):
        self.shape = load(path)
        self.mesh = mill.closed_mesh(self.shape)

    def section(self, z):
        return clean2d(mill.section(self.mesh, z))

    def column(self, x, y):
        """Heights where a vertical line at (x, y) crosses the part, from the top down."""
        loc, idx, _ = self.mesh.ray.intersects_location([[x, y, 50.0]], [[0, 0, -1.0]], multiple_hits=True)
        return sorted(set(np.round(loc[:, 2], 4)), reverse=True)
