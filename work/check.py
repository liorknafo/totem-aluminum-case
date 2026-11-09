"""Checks of the case parts in outputs/ against the KiCad board, its parts and pads.

    ~/.venvs/totem-cad/bin/python -E -s check.py [L] [R]     # writes work/checks_{side}.json
    ~/.venvs/totem-cad/bin/python -E -s report.py            # writes outputs/CHECKS.md

Everything is measured on the STEP files as written (read back), not on the build's regions:
exact distances (OpenCASCADE BRepExtrema) to the board from src/pcb_board.step, to every KiCad 3D
part (src/comp_all.step) and to every copper pad (src/pads.step); thicknesses between opposing faces;
inside corners against the end mill; reachability of every horizontal face from above or below;
vertical lines through the bottom; solid validity; face types.
"""
import json
import math
import sys
import time
from pathlib import Path

import cadquery as cq
import numpy as np
from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN

import build as B
import geom2d as g
import parts as P
from pcb import Board, rot, SPLIT_X

W = Path(__file__).resolve().parent
OUT = W.parent / 'outputs'
T0 = time.monotonic()
NEAR = 3.0     # distances above this are reported as "> NEAR"


def log(*a):
    print(f'[{time.monotonic() - T0:6.1f}s]', *a, flush=True)


def load(p):
    return cq.importers.importStep(str(p)).val()


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


# ----------------------------------------------------------------------------- distances
class Part:
    """A case part with its faces indexed by bounding box, for fast exact distances."""

    def __init__(self, shape):
        self.shape = shape
        self.faces = shape.Faces()
        bb = [f.BoundingBox() for f in self.faces]
        self.lo = np.array([(b.xmin, b.ymin, b.zmin) for b in bb])
        self.hi = np.array([(b.xmax, b.ymax, b.zmax) for b in bb])

    def near(self, bb, grow):
        lo = np.array((bb.xmin, bb.ymin, bb.zmin)) - grow
        hi = np.array((bb.xmax, bb.ymax, bb.zmax)) + grow
        m = np.all(self.hi >= lo, axis=1) & np.all(self.lo <= hi, axis=1)
        return [self.faces[i] for i in np.nonzero(m)[0]]

    def inside(self, p):
        c = BRepClass3d_SolidClassifier(self.shape.wrapped, gp_Pnt(*p), 1e-7)
        return c.State() == TopAbs_IN

    def dist(self, obj, grow=NEAR):
        """(distance, point on the case) from a shape; 0 if they touch, -1 if it is inside."""
        fs = self.near(obj.BoundingBox(), grow)
        if not fs:
            return grow, None
        d = BRepExtrema_DistShapeShape(cq.Compound.makeCompound(fs).wrapped, obj.wrapped)
        d.Perform()
        val = d.Value()
        p = d.PointOnShape1(1)
        pt = (round(p.X(), 2), round(p.Y(), 2), round(p.Z(), 2))
        if val > 1e-6:
            v = obj.Vertices()[0].toTuple() if obj.Vertices() else obj.Center().toTuple()
            if self.inside(v):
                return -1.0, pt
        return min(val, grow), pt


def worst(rows):
    """Smallest distance among [(d, pt, label)]."""
    rows = [r for r in rows if r[0] is not None]
    return min(rows, key=lambda r: r[0]) if rows else (None, None, '')


def fmt(r):
    d, pt, lab = r
    return dict(d=None if d is None else round(d, 3), at=pt, what=lab)


def BRepExtrema_DistShapeShape_value(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value()


# ----------------------------------------------------------------------------- the board
def board_solid(board, side, nubs=False):
    """The half board as the case sees it: its outline from the board file (tabs removed; with
    nubs=True plus the TAB_NUB allowance where they were), from -COPPER to PCB_T + COPPER (PCB_T from
    the board file)."""
    loops = board.outline(side)
    f = g.from_loops(loops)
    if nubs:
        d = B.design(board, side)
        f = g.union(f, *d['nubs'])
    return cq.Compound.makeCompound(g.extrude(f, -B.COPPER, P.PCB_T + B.COPPER))


def exports_crosscheck(board):
    """How far KiCad's STEP exports in src/ are from the board file (they are only used here)."""
    out = {'parts (comp_all.step)': P.crosscheck(board)}
    # board outline: every point of each half's outline (tabs removed) lies on the export's outline,
    # except along the tab openings
    import shapely.geometry as sg
    pcb = load(W.parent / 'src' / 'pcb_board.step').Solids()[0]
    sec = pcb.intersect(box(-50, 450, -300, 50, 0.74, 0.76))
    rings = []
    for f in sec.Faces():
        if f.normalAt().z > 0.99:
            for w in [f.outerWire()] + f.innerWires():
                pts = [(e.positionAt(t).x, e.positionAt(t).y) for e in w.Edges() for t in np.linspace(0, 1, 40)]
                rings.append(sg.LineString(pts))
    from shapely.ops import unary_union
    bnd = unary_union(rings)
    tabs = unary_union([sg.LineString(o).buffer(0.05) for s in 'LR' for o in board.tab_openings(s)])
    worst = 0.0
    for s in 'LR':
        f = g.from_loops(board.outline(s))
        for w in [f.outerWire()]:          # cut-outs differ by the drilled holes the export also removes
            for e in w.Edges():
                for t in np.linspace(0, 1, 12):
                    q = e.positionAt(t)
                    pt = sg.Point(q.x, q.y)
                    if not tabs.contains(pt):
                        worst = max(worst, bnd.distance(pt))
    out['board outline (pcb_board.step)'] = dict(max_distance=round(worst, 4))
    # pads: every copper pad of the board file has an exported pad at its centre
    cent = np.array([((s.BoundingBox().xmin + s.BoundingBox().xmax) / 2, (s.BoundingBox().ymin + s.BoundingBox().ymax) / 2)
                     for s in P.load_pads()])
    allp = [p.at for f in board.footprints for p in f.pads if p.copper and p.kind != 'np_thru_hole']
    worst = max(float(np.min(np.hypot(cent[:, 0] - q[0], cent[:, 1] - q[1]))) for q in allp)
    out['pads (pads.step)'] = dict(n_export=len(cent), n_board=len(allp), max_centre_offset=round(worst, 4))
    return out


# ----------------------------------------------------------------------------- KiCad parts
def classify(board, side):
    """Every part solid on this half, placed from the board file, with its category.
    Returns [(category, ref, solid)]."""
    out = []
    for fp in board.footprints:
        if fp.side != side:
            continue
        k = B.kind(fp)
        if k == 'MJ-4PP-9':
            continue                                            # TRRS jack: not fitted
        for v in P.placed(board, fp):
            bb = v.BoundingBox()
            if k == 'Kailh_socket':
                if bb.zmax > P.PCB_T + 0.4:
                    # switch: only its pins under the board must keep the rule (the plastic body
                    # clips into the plate)
                    if bb.zmin < 0:
                        below = v.intersect(box(-50, 450, -300, 50, -10, 0))
                        if below.Solids():
                            out.append(('switch pins under the board', fp.ref, below))
                else:
                    out.append(('hot-swap socket and contacts', fp.ref, v))
            elif k == 'Diode_SOD123':
                out.append(('diode (whole part; epoxy top may come to 0.3)', fp.ref, v))
                low = v.intersect(box(-50, 450, -300, 50, -10, bb.zmax - 0.25))
                if low.Solids():
                    out.append(('diode leads and body sides', fp.ref, low))
            elif k in B.FRONT:
                axis, val, sgn = B.FRONT[k]
                big = 50
                a0, a1, b0, b1 = -big, big, -big, big
                if axis == 'a':
                    a0, a1 = (-big, val) if sgn < 0 else (val, big)
                else:
                    b0, b1 = (-big, val) if sgn < 0 else (val, big)
                zone = B.local_rect(fp, a0, a1, b0, b1)
                zs = cq.Solid.extrudeLinear(zone.translate(cq.Vector(0, 0, -10)), cq.Vector(0, 0, 30))
                act = v.intersect(zs)
                body = v.cut(zs)
                name = 'power switch' if k == 'MSK12C02' else 'reset button'
                if body.Solids():
                    out.append((f'{name} body (metal)', fp.ref, body))
                if act.Solids():
                    # the actuator over its whole travel
                    ax, travel = B.TRAVEL.get(k, ('b', 0.0))
                    steps = [0.0] if not travel else list(np.linspace(-travel, travel, 5))
                    for t in steps:
                        dv = rot((t, 0) if ax == 'a' else (0, t), fp.angle)
                        out.append((f'{name} actuator (plastic), over its travel', fp.ref, act.translate(cq.Vector(dv[0], dv[1], 0))))
            else:
                out.append((f'other part ({k})', fp.ref, v))
    # the XIAO has no KiCad model: the module and USB-C boxes used by the build
    for fp in board.footprints:
        if fp.side == side and B.kind(fp) == 'xiao':
            for a0, a1, b0, b1, z0, z1 in B.XIAO_BOXES:
                r = B.local_rect(fp, a0, a1, b0, b1)
                out.append(('XIAO (module and USB-C, Seeed model extents)', fp.ref,
                            cq.Solid.extrudeLinear(r.translate(cq.Vector(0, 0, z0)), cq.Vector(0, 0, z1 - z0))))
    return out


def pad_list(board, side):
    """Copper pads from the board file (0.05 mm proud of each face they are on) with the solder
    fillet envelope the build allows for."""
    out = []
    for f in board.footprints:
        if f.side != side:
            continue
        for p in f.pads:
            if not p.copper or p.kind == 'np_thru_hole':
                continue
            nonet = B.kind(f) == 'MountingHole'
            st, sb = (0.0, 0.0) if nonet else B.solder(f, p)
            lab = f'{f.ref} pad {p.number}'
            reg = B.pad_region(p, 0)

            def env(allow, top, p=p):
                if not allow:
                    return None
                r = B.pad_region(p, B.FILLET_SPREAD)
                z0 = P.PCB_T + B.COPPER if top else -B.COPPER - allow
                return cq.Solid.extrudeLinear(r.translate(cq.Vector(0, 0, z0)), cq.Vector(0, 0, allow))
            if p.top:
                cu = cq.Solid.extrudeLinear(reg.translate(cq.Vector(0, 0, P.PCB_T)), cq.Vector(0, 0, B.COPPER))
                out.append((cu, 'top', env(st, True), lab, nonet))
            if p.bottom:
                cu = cq.Solid.extrudeLinear(reg.translate(cq.Vector(0, 0, -B.COPPER)), cq.Vector(0, 0, B.COPPER))
                out.append((cu, 'bottom', env(sb, False), lab, nonet))
    return out


# ----------------------------------------------------------------------------- thickness
def thickness(shape, limit=2.0):
    """Thinnest material between opposing faces (a wall, floor, roof or neck): for every pair of
    faces within `limit` that do not share an edge, the closest points count when the faces look at
    each other through material (normals opposed, the segment leaving one face inward and reaching
    the other from inside, its midpoint inside the solid). Returns [(t, point)] sorted."""
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape, TopTools_IndexedMapOfShape
    from OCP.TopExp import TopExp
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopoDS import TopoDS
    fmap = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape.wrapped, TopAbs_FACE, fmap)
    faces = [cq.Face(TopoDS.Face_s(fmap.FindKey(i))) for i in range(1, fmap.Extent() + 1)]
    bbs = [f.BoundingBox() for f in faces]
    lo = np.array([(b.xmin, b.ymin, b.zmin) for b in bbs]); hi = np.array([(b.xmax, b.ymax, b.zmax) for b in bbs])
    emap = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shape.wrapped, TopAbs_EDGE, TopAbs_FACE, emap)
    adj = [set() for _ in faces]
    for i in range(1, emap.Extent() + 1):
        ids = [fmap.FindIndex(fsh) - 1 for fsh in emap.FindFromIndex(i)]
        for x in ids:
            adj[x].update(y for y in ids if y != x)
    cls = BRepClass3d_SolidClassifier(shape.wrapped)
    # cheap geometric filter: which face pairs could look at each other through material
    kind, nrm, ctr = [], [], []
    for f in faces:
        t = f.geomType()
        if t == 'PLANE':
            n = np.array(f.normalAt().toTuple())
            kind.append('H' if abs(n[2]) > 0.999 else 'P')
            nrm.append(n)
        else:
            vert = t == 'CYLINDER' and abs(abs(f._geomAdaptor().Cylinder().Axis().Direction().Z()) - 1) < 1e-6
            kind.append('C' if vert else 'X')
            nrm.append(None)
        ctr.append(np.array(f.Center().toTuple()))

    def corners(j):
        return np.array([(x, y, z) for x in (lo[j][0], hi[j][0]) for y in (lo[j][1], hi[j][1]) for z in (lo[j][2], hi[j][2])])

    def may_face(i, j):
        ki, kj = kind[i], kind[j]
        if {ki, kj} == {'H', 'C'}:
            return False                       # horizontal plane vs vertical cylinder: normals perpendicular
        if ki in 'HP' and kj in 'HP':
            if np.dot(nrm[i], nrm[j]) > -0.5:
                return False
            # some of B must lie behind A (inside A's material side) and vice versa
            if np.min((corners(j) - ctr[i]) @ nrm[i]) >= -1e-9:
                return False
            if np.min((corners(i) - ctr[j]) @ nrm[j]) >= -1e-9:
                return False
        return True

    out = []
    for i in range(len(faces)):
        cand = np.nonzero(np.all(hi >= lo[i] - limit, axis=1) & np.all(lo <= hi[i] + limit, axis=1))[0]
        for j in cand:
            if j <= i or j in adj[i] or not may_face(i, j):
                continue
            d = BRepExtrema_DistShapeShape(faces[i].wrapped, faces[j].wrapped)
            d.Perform()
            if not d.IsDone() or d.Value() > limit or d.Value() < 1e-6:
                continue
            for k in range(1, d.NbSolution() + 1):
                p, q = d.PointOnShape1(k), d.PointOnShape2(k)
                p = np.array((p.X(), p.Y(), p.Z())); q = np.array((q.X(), q.Y(), q.Z()))
                u = (q - p) / d.Value()
                na = faces[i].normalAt(cq.Vector(*p)).toTuple(); nb = faces[j].normalAt(cq.Vector(*q)).toTuple()
                if np.dot(na, nb) > -0.5 or -np.dot(na, u) < 0.5 or np.dot(nb, u) < 0.5:
                    continue
                m = (p + q) / 2
                cls.Perform(gp_Pnt(*m), 1e-7)
                if cls.State() != TopAbs_IN:
                    # the closest points often sit on an edge of a face: look just inside it
                    ok = False
                    for c0 in (ctr[i], ctr[j]):
                        t = c0 - m
                        t = t - u * np.dot(t, u)
                        if np.linalg.norm(t) > 1e-9:
                            m2 = m + 0.02 * t / np.linalg.norm(t)
                            cls.Perform(gp_Pnt(*m2), 1e-7)
                            if cls.State() == TopAbs_IN:
                                ok = True
                                break
                    if not ok:
                        continue
                out.append((round(d.Value(), 3), tuple(np.round(m, 2))))
                break
    out.sort()
    return out


# ----------------------------------------------------------------------------- machinability
def sections(shape):
    """(z, material face) at the middle of every slab between horizontal faces."""
    zs = sorted({round(f.Center().z, 4) for f in shape.Faces() if f.geomType() == 'PLANE' and abs(f.normalAt().z) > 0.999})
    bb = shape.BoundingBox()
    out = []
    for z0, z1 in zip(zs, zs[1:]):
        z = (z0 + z1) / 2
        pl = cq.Face.makePlane(600, 600, basePnt=(bb.center.x, bb.center.y, z))
        sec = shape.intersect(pl)
        fs = [f.translate(cq.Vector(0, 0, -z)) for f in sec.Faces()]
        if fs:
            out.append((round(z0, 3), round(z1, 3), g.union(*fs)))
    return out


def mill_corners(shape, r):
    """Inside corners of the material the end mill cannot reach, per slab: convex corners of the
    air around each section (a big rectangle minus the material)."""
    bb = shape.BoundingBox()
    frame = g.rrect((bb.center.x, bb.center.y), bb.xlen + 20, bb.ylen + 20)
    bad = []
    for z0, z1, mat in sections(shape):
        air = g.diff(frame, mat)
        for c in g.convex_corners(air, r):
            o = c['o']
            if abs(abs(o[0] - bb.center.x) - (bb.xlen + 20) / 2) < 0.1 or abs(abs(o[1] - bb.center.y) - (bb.ylen + 20) / 2) < 0.1:
                continue
            bad.append(dict(z=(z0, z1), at=(round(o[0], 2), round(o[1], 2)), radius=round(c['rho'], 3), left=round(c['left'], 3)))
    return bad


def mesh(shape, tol=0.01):
    import trimesh
    v, f = shape.tessellate(tol, 0.1)
    return trimesh.Trimesh(np.array([p.toTuple() for p in v]), np.array(f), process=False)


def reach(shape):
    """Every horizontal face must be reachable by a vertical tool from the side it faces; every
    other face must be vertical (2.5D). Returns (non-vertical side faces, blocked horizontal faces)."""
    m = mesh(shape)
    tilted, blocked = [], []
    origins, dirs, owner = [], [], []
    for i, f in enumerate(shape.Faces()):
        t = f.geomType()
        if t == 'PLANE':
            n = f.normalAt().toTuple()
            if abs(n[2]) > 0.999:
                v, tri = f.tessellate(0.05, 0.2)
                V = np.array([p.toTuple() for p in v])
                for tr in tri[:: max(1, len(tri) // 25)]:
                    c = V[list(tr)].mean(axis=0)
                    origins.append(c + np.array((0, 0, 1e-3 * np.sign(n[2]))))
                    dirs.append((0, 0, np.sign(n[2])))
                    owner.append(i)
            elif abs(n[2]) > 1e-6:
                tilted.append((i, t, tuple(np.round(f.Center().toTuple(), 2))))
        elif t == 'CYLINDER':
            ax = f._geomAdaptor().Cylinder().Axis().Direction()
            if abs(abs(ax.Z()) - 1) > 1e-6:
                tilted.append((i, t, tuple(np.round(f.Center().toTuple(), 2))))
        else:
            tilted.append((i, t, tuple(np.round(f.Center().toTuple(), 2))))
    hit = m.ray.intersects_any(np.array(origins), np.array(dirs, float))
    for k in np.nonzero(hit)[0]:
        blocked.append((owner[k], tuple(np.round(origins[k], 2))))
    return tilted, sorted(set(blocked))


def through(shape, step=0.2):
    """Places where a vertical line passes through the part without meeting material."""
    m = mesh(shape, 0.02)
    bb = shape.BoundingBox()
    xs = np.arange(bb.xmin + step / 2, bb.xmax, step); ys = np.arange(bb.ymin + step / 2, bb.ymax, step)
    X, Y = np.meshgrid(xs, ys)
    o = np.c_[X.ravel(), Y.ravel(), np.full(X.size, bb.zmin - 1)]
    hit = m.ray.intersects_any(o, np.tile((0, 0, 1.0), (len(o), 1)))
    # inside the outline only: the outer wire of the underside, 0.3 mm in
    down = [f for f in shape.Faces() if f.geomType() == 'PLANE' and f.normalAt().z < -0.999]
    zlow = min(f.Center().z for f in down)
    under = max((f for f in down if abs(f.Center().z - zlow) < 1e-4), key=lambda f: f.Area())
    outer = g.offset(cq.Face.makeFromWires(under.outerWire()).translate(cq.Vector(0, 0, -zlow)), -0.3)
    keep = [g.inside(outer, (x, y)) for (x, y, _), h in zip(o, hit) if not h]
    open_pts = [(x, y) for ((x, y, _), k) in zip([p for p, h in zip(o, hit) if not h], keep) if k]
    # cluster
    from scipy.cluster.hierarchy import fcluster, linkage
    res = []
    if len(open_pts) > 1:
        A = np.array(open_pts)
        cl = fcluster(linkage(A, 'single'), step * 1.6, 'distance')
        for c in np.unique(cl):
            q = A[cl == c]
            res.append(dict(at=(round(q[:, 0].mean(), 2), round(q[:, 1].mean(), 2)), size=(round(np.ptp(q[:, 0]) + step, 2), round(np.ptp(q[:, 1]) + step, 2)), points=len(q)))
    elif open_pts:
        res.append(dict(at=open_pts[0], size=(step, step), points=1))
    return res


# ----------------------------------------------------------------------------- solids
def analyze(shape):
    an = BRepCheck_Analyzer(shape.wrapped)
    aa = BOPAlgo_ArgumentAnalyzer()
    aa.SetShape1(shape.wrapped)
    for flag in ('ArgumentTypeMode', 'SelfInterMode', 'SmallEdgeMode', 'RebuildFaceMode', 'TangentMode',
                 'MergeVertexMode', 'MergeEdgeMode', 'ContinuityMode', 'CurveOnSurfaceMode'):
        setattr(aa, flag, True) if hasattr(aa, flag) else None
    try:
        aa.SelfInterMode = True
        aa.CurveOnSurfaceMode = True
        aa.SmallEdgeMode = True
    except Exception:
        pass
    aa.Perform()
    shells = shape.Shells()
    return dict(valid=an.IsValid(), solids=len(shape.Solids()), shells=len(shells),
                closed=all(s.Closed() for s in shells), analyzer_faulty=bool(aa.HasFaulty()))


def face_types(shape):
    out = {}
    for f in shape.Faces():
        out[f.geomType()] = out.get(f.geomType(), 0) + 1
    return out


# ----------------------------------------------------------------------------- main
def check(board, side):
    P.assert_thickness()
    rep = dict(side=side)
    top = load(OUT / f'TOTEM_alu_top_{side}.step')
    bot = load(OUT / f'TOTEM_alu_bottom_{side}.step')
    ins = load(OUT / f'TOTEM_wood_window_insert_{side}.step')
    T, Bo = Part(top), Part(bot)
    log(side, 'loaded')

    # solids, sizes, faces
    for name, s in (('top', top), ('bottom', bot), ('insert', ins)):
        bb = s.BoundingBox()
        rep[name] = dict(analysis=analyze(s), faces=face_types(s), volume=round(s.Volume(), 1),
                         size=(round(bb.xlen, 2), round(bb.ylen, 2), round(bb.zlen, 2)), z=(round(bb.zmin, 2), round(bb.zmax, 2)))
    log(side, 'solid analysis done')

    # the board
    brd = board_solid(board, side)
    rep['board'] = {'top': fmt((*T.dist(brd), 'board')), 'bottom': fmt((*Bo.dist(brd), 'board'))}
    brn = board_solid(board, side, nubs=True)
    rep['board_nubs'] = {'top': fmt((*T.dist(brn), 'board with tab nubs')), 'bottom': fmt((*Bo.dist(brn), 'board with tab nubs'))}
    log(side, 'board', rep['board'])

    # parts, by category
    cats = {}
    parts_list = classify(board, side)
    # spacers at the no-net mounting pads: where they sit, how close they come to the board, and that
    # no part is in their way
    fps = [f for f in board.footprints if f.side == side and B.kind(f) == 'MountingHole']
    sp = []
    for f in fps:
        h = f.at
        pad_r = max(p.size[0] for p in f.pads) / 2
        lo = cq.Solid.makeCylinder(B.SPACER_D / 2, B.LOWER_SPACER, cq.Vector(h[0], h[1], B.LOWER_SEAT))
        up = cq.Solid.makeCylinder(B.SPACER_D / 2, B.UPPER_SPACER, cq.Vector(h[0], h[1], B.UPPER_SEAT - B.UPPER_SPACER))
        brd_ = board_solid(board, side)
        gaps = [round(BRepExtrema_DistShapeShape_value(s_, brd_), 3) for s_ in (lo, up)]
        near = []
        for cat, ref, s in parts_list:
            for s_ in (lo, up):
                bb, bs = s.BoundingBox(), s_.BoundingBox()
                if bb.xmax < bs.xmin - 3 or bb.xmin > bs.xmax + 3 or bb.ymax < bs.ymin - 3 or bb.ymin > bs.ymax + 3:
                    continue
                near.append((BRepExtrema_DistShapeShape_value(s_, s), ref))
        seat = (round(T.dist(up, 0.5)[0], 3), round(Bo.dist(lo, 0.5)[0], 3))
        sp.append(dict(at=(round(h[0], 2), round(h[1], 2)), gap_to_board_lower_upper=gaps,
                       spacer_within_pad=B.SPACER_D / 2 <= pad_r, pad_d=round(2 * pad_r, 2),
                       nearest_part=(round(min(near)[0], 3), min(near)[1]) if near else None,
                       seat_contact_top_bottom=seat))
    rep['spacers'] = sp
    log(side, 'spacers', sp)
    for cat, ref, s in parts_list:
        dt, pt = T.dist(s)
        db, pb = Bo.dist(s)
        c = cats.setdefault(cat, {'top': [], 'bottom': [], 'insert': []})
        c['top'].append((dt, pt, ref)); c['bottom'].append((db, pb, ref))
        if 'XIAO' in cat:
            di = Part(ins).dist(s, 20.0)
            c['insert'].append((di[0], di[1], ref))
    rep['parts'] = {cat: {k: fmt(worst(v)) for k, v in c.items() if v} for cat, c in cats.items()}
    log(side, 'parts done')

    # pads (and their solder allowance)
    pads = pad_list(board, side)
    rows = {'top': [], 'bottom': []}
    sold = {'top': [], 'bottom': []}
    for s, face, fillet, lab, nonet in pads:
        part = T if face == 'top' else Bo
        d, pt = part.dist(s)
        rows[face].append((d, pt, lab + (' (no-net mounting pad)' if nonet else '')))
        if fillet is not None:
            df, pf = part.dist(fillet)
            sold[face].append((df, pf, lab))
    rep['pads'] = {f: fmt(worst(rows[f])) for f in rows}
    rep['pads_solder_margin'] = {f: fmt(worst(sold[f])) for f in sold}
    log(side, 'pads done', rep['pads'])

    # assembly
    ov = top.intersect(bot)
    rep['assembly'] = dict(top_bottom_overlap=round(ov.Volume(), 6) if ov.Solids() else 0.0,
                           top_bottom_gap=round(T.dist(bot, 1.0)[0], 3),
                           insert_top_overlap=round(top.intersect(ins).Volume(), 6) if top.intersect(ins).Solids() else 0.0,
                           insert_top_gap=round(T.dist(ins, 1.0)[0], 3))
    # seam contact area
    seam = top.intersect(box(-50, 450, -300, 50, B.Z_SEAM - 1e-3, B.Z_SEAM + 1e-3))
    rep['assembly']['seam_contact_mm2'] = round(seam.Volume() / 2e-3, 1) if seam.Solids() else 0.0

    # keycaps (pressed: skirt down to 5.0) and switch bodies
    d = B.design(board, side)
    kc = []
    for k in d['keys']:
        r = g.rrect(k.at, *B.KEYCAP, k.angle)
        prism = cq.Solid.extrudeLinear(r.translate(cq.Vector(0, 0, 5.0)), cq.Vector(0, 0, 8.0))
        kc.append((T.dist(prism)[0], k.ref))
    rep['keycaps'] = dict(min_gap=round(min(kc)[0], 3), key=min(kc)[1], pressed_skirt_z=5.0)
    # switches: the plastic bodies must sit in the plate without overlapping the aluminum, their
    # shoulder on the plate top and their latches under the plate
    sw_worst = (0.0, None)
    for k in d['keys']:
        for s in P.placed(board, k):
            if s.BoundingBox().zmax < P.PCB_T + 0.4:
                continue
            ov = top.intersect(s)
            v = ov.Volume() if ov.Solids() else 0.0
            if v > sw_worst[0]:
                sw_worst = (v, k.ref)
    sh, la = d['switch_seat']
    rep['switches'] = dict(max_overlap_mm3=round(sw_worst[0], 6), where=sw_worst[1], shoulder_z=sh, plate_top=round(B.PLATE_TOP, 3),
                           latch_top_z=la, plate_bottom=round(B.PLATE_BOT, 3), latch_play=round(B.PLATE_BOT - la, 3))
    log(side, 'switches', rep['switches'])
    log(side, 'keycaps', rep['keycaps'])

    # thickness
    for name, s in (('top', top), ('bottom', bot)):
        th = thickness(s)
        rep[name]['thinnest'] = th[:12]
        log(side, name, 'thinnest', th[:4])

    # machinability
    for name, s in (('top', top), ('bottom', bot), ('insert', ins)):
        tilted, blocked = reach(s)
        corners = mill_corners(s, B.R_MILL)
        rep[name]['mill'] = dict(non_vertical_side_faces=tilted[:10], blocked_horizontal_faces=blocked[:10],
                                 corners_tighter_than_mill=corners[:10], n_corners=len(corners),
                                 n_blocked=len(blocked), n_tilted=len(tilted))
        log(side, name, 'mill', len(tilted), len(blocked), len(corners))
    rep['bottom']['through'] = through(bot)
    log(side, 'through', rep['bottom']['through'])
    return rep


def mirror_report(board):
    """How far the right half is from a mirror image of the left (mirror line x = 150)."""
    out = {}
    L = [f for f in board.footprints if f.side == 'L']
    R = [f for f in board.footprints if f.side == 'R']
    for f in L:
        k = B.kind(f)
        if k in ('mousebites',):
            continue
        mx = (2 * B.MIRROR_X - f.at[0], f.at[1])
        cands = [r for r in R if B.kind(r) == k]
        if not cands:
            continue
        r = min(cands, key=lambda r: math.dist(r.at, mx))
        o = out.setdefault(k, dict(n=0, max_pos=0.0, angle_mirrored=0, angle_same=0))
        o['n'] += 1
        o['max_pos'] = round(max(o['max_pos'], math.dist(r.at, mx)), 3)
        if abs(((r.angle + f.angle) + 180) % 360 - 180) < 0.01:
            o['angle_mirrored'] += 1
        elif abs(((r.angle - f.angle) + 180) % 360 - 180) < 0.01:
            o['angle_same'] += 1
    # outline
    import shapely.geometry as sg
    def poly(side):
        loops = board.outline(side)
        f = g.from_loops(loops[:1])
        pts = [(e.positionAt(t).x, e.positionAt(t).y) for e in f.outerWire().Edges() for t in np.linspace(0, 1, 20)]
        return sg.Polygon(pts).buffer(0)
    pl = poly('L'); pr = poly('R')
    from shapely.affinity import scale
    plm = scale(pl, xfact=-1, yfact=1, origin=(B.MIRROR_X, 0))
    out['outline'] = dict(sym_diff_mm2=round(plm.symmetric_difference(pr).area, 3),
                          hausdorff_mm=round(plm.hausdorff_distance(pr), 3))
    return out


if __name__ == '__main__':
    sides = [a for a in sys.argv[1:] if a in ('L', 'R')] or ['L', 'R']
    board = Board()
    for side in sides:
        rep = check(board, side)
        (W / f'checks_{side}.json').write_text(json.dumps(rep, indent=1, default=str))
    (W / 'checks_mirror.json').write_text(json.dumps(mirror_report(board), indent=1))
    (W / 'checks_exports.json').write_text(json.dumps(exports_crosscheck(board), indent=1))
    log('done')
