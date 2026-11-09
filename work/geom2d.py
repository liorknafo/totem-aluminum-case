"""Planar regions (faces in z = 0) built from exact lines and arcs, and 2.5D solids made from them.

A region is a cq.Shape holding one or more planar faces. Booleans and offsets run on OpenCASCADE
directly, so straight edges stay lines and every rounded edge is a true circular arc: extruded, they
give planes and cylinders.
"""
import math

import cadquery as cq
from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse, BRepAlgoAPI_Common
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffset
from OCP.BRepTools import BRepTools_WireExplorer
from OCP.GeomAbs import GeomAbs_Arc, GeomAbs_Circle, GeomAbs_Line
from OCP.gp import gp_Pnt, gp_Pnt2d, gp_Pln, gp_Vec
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.TopAbs import TopAbs_IN, TopAbs_ON, TopAbs_REVERSED
from OCP.TopTools import TopTools_ListOfShape

V = cq.Vector
EMPTY = cq.Compound.makeCompound([])


# ----------------------------------------------------------------------------- construction
def _edge(seg):
    if seg[0] == 'line':
        return cq.Edge.makeLine(V(*seg[1], 0), V(*seg[2], 0))
    return cq.Edge.makeThreePointArc(V(*seg[1], 0), V(*seg[2], 0), V(*seg[3], 0))


def from_loops(loops):
    """Face from segment loops (pcb.py format): the first loop is the outline, the rest are holes."""
    wires = [cq.Wire.assembleEdges([_edge(s) for s in loop]) for loop in loops]
    return cq.Face.makeFromWires(wires[0], wires[1:])


def polygon(pts):
    return cq.Face.makeFromWires(cq.Wire.makePolygon([V(x, y, 0) for x, y in pts], close=True))


def circle(c, r):
    return cq.Face.makeFromWires(cq.Wire.makeCircle(r, V(c[0], c[1], 0), V(0, 0, 1)))


def rrect(c, w, h, ang=0.0, r=0.0):
    """Rectangle w x h centred at c, turned by ang degrees (CCW), corners rounded with r."""
    r = min(r, w / 2 - 1e-6, h / 2 - 1e-6) if r > 0 else 0.0
    if r <= 0:
        f = polygon([(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)])
    else:
        x, y = w / 2, h / 2
        k = r * (1 - math.sqrt(0.5))
        segs = [('line', (-x + r, -y), (x - r, -y)), ('arc', (x - r, -y), (x - k, -y + k), (x, -y + r)),
                ('line', (x, -y + r), (x, y - r)), ('arc', (x, y - r), (x - k, y - k), (x - r, y)),
                ('line', (x - r, y), (-x + r, y)), ('arc', (-x + r, y), (-x + k, y - k), (-x, y - r)),
                ('line', (-x, y - r), (-x, -y + r)), ('arc', (-x, -y + r), (-x + k, -y + k), (-x + r, -y))]
        f = from_loops([segs])
    return place(f, c, ang)


def stadium(c, w, h, ang=0.0):
    """Oval pad: w x h with fully rounded ends."""
    if abs(w - h) < 1e-6:
        return circle(c, w / 2)
    if w < h:
        return stadium(c, h, w, ang + 90)
    r, x = h / 2, w / 2 - h / 2
    segs = [('line', (-x, -r), (x, -r)), ('arc', (x, -r), (x + r, 0), (x, r)),
            ('line', (x, r), (-x, r)), ('arc', (-x, r), (-x - r, 0), (-x, -r))]
    return place(from_loops([segs]), c, ang)


def place(shape, c, ang):
    if ang:
        shape = shape.rotate(V(0, 0, 0), V(0, 0, 1), ang)
    return shape.translate(V(c[0], c[1], 0))


# ----------------------------------------------------------------------------- booleans
def faces(region):
    return [] if region is None else region.Faces()


def _unify(shape):
    u = ShapeUpgrade_UnifySameDomain(shape, True, True, True)
    u.AllowInternalEdges(False)
    u.Build()
    return cq.Shape.cast(u.Shape())


def _bop(op, a, b):
    args, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    for f in faces(a):
        args.Append(f.wrapped)
    for f in faces(b):
        tools.Append(f.wrapped)
    op.SetArguments(args)
    op.SetTools(tools)
    op.SetFuzzyValue(1e-6)
    op.SetRunParallel(True)
    op.Build()
    assert op.IsDone(), 'boolean failed'
    return _clean(cq.Shape.cast(op.Shape()))


def _clean(shape):
    fs = [f for f in _unify(shape.wrapped).Faces() if f.Area() > 1e-6]
    return cq.Compound.makeCompound(fs)


def union(*regions):
    fs = [f for r in regions for f in faces(r)]
    if not fs:
        return EMPTY
    if len(fs) == 1:
        return cq.Compound.makeCompound(fs)
    return _bop(BRepAlgoAPI_Fuse(), cq.Compound.makeCompound(fs[:1]), cq.Compound.makeCompound(fs[1:]))


def diff(a, *b):
    fb = [f for r in b for f in faces(r)]
    if not fb or not faces(a):
        return a
    return _bop(BRepAlgoAPI_Cut(), a, cq.Compound.makeCompound(fb))


def inter(a, b):
    if not faces(a) or not faces(b):
        return EMPTY
    return _bop(BRepAlgoAPI_Common(), a, b)


def area(region):
    return sum(f.Area() for f in faces(region))


# ----------------------------------------------------------------------------- offsets
def _wires_to_faces(wires):
    """Nest closed planar wires into faces (even depth = outline, odd = hole)."""
    items = []
    for w in wires:
        f = cq.Face.makeFromWires(w)
        items.append((abs(f.Area()), w, f))
    items.sort(key=lambda t: -t[0])

    def inside(f, w):
        p = w.Edges()[0].positionAt(0.5)
        c = BRepClass_FaceClassifier(f.wrapped, gp_Pnt(p.x, p.y, p.z), 1e-7)
        return c.State() == TopAbs_IN

    parent = []
    for i, (a, w, f) in enumerate(items):
        par = None
        for j in range(i - 1, -1, -1):
            if inside(items[j][2], w):
                par = j
                break
        parent.append(par)
    depth = []
    for i in range(len(items)):
        d, p = 0, parent[i]
        while p is not None:
            d += 1
            p = parent[p]
        depth.append(d)
    out = []
    for i, (a, w, f) in enumerate(items):
        if depth[i] % 2:
            continue
        holes = [items[j][1] for j in range(len(items)) if parent[j] == i]
        out.append(cq.Face.makeFromWires(w, holes))
    return out


def _fix(face, small=2e-3):
    """Merge edges shorter than `small` into their neighbours and repair the face (offsets can
    leave slivers of edges that make the next offset fail)."""
    from OCP.ShapeFix import ShapeFix_Wireframe, ShapeFix_Face
    if face.isValid() and min(e.Length() for e in face.Edges()) > small:
        return face
    wf = ShapeFix_Wireframe(face.wrapped)
    wf.SetPrecision(small)
    wf.ModeDropSmallEdges = True
    wf.FixSmallEdges()
    wf.FixWireGaps()
    fx = ShapeFix_Face(cq.Shape.cast(wf.Shape()).Faces()[0].wrapped)
    fx.Perform()
    out = cq.Face(fx.Face())
    return out


def _offset_face_raw(face, d):
    mk = BRepOffsetAPI_MakeOffset(face.wrapped, GeomAbs_Arc, False)
    mk.Perform(d)
    if not mk.IsDone():
        raise RuntimeError('offset failed')
    shp = cq.Shape.cast(mk.Shape())
    wires = [w for w in shp.Wires() if w.IsClosed()]
    return _wires_to_faces(wires)


def _offset_face(face, d):
    """Offset one face; if OpenCASCADE fails, repair the face (tiny edges) and try again."""
    try:
        out = _offset_face_raw(face, d)
        if all(f.isValid() for f in out):
            return out
    except RuntimeError:
        pass
    out = _offset_face_raw(_fix(face), d)
    return [_fix(f) for f in out]


def offset(region, d):
    """Grow (d > 0) or shrink (d < 0) every face of a region by d, rounding with true arcs."""
    if abs(d) < 1e-9:
        return region
    out = []
    for f in faces(region):
        try:
            out += _offset_face(f, d)
        except RuntimeError:
            # a face may vanish when shrunk; anything bigger than that is a real failure
            if d > 0 or f.Area() > 4 * d * d:
                raise
    return union(*out) if out else EMPTY


def closing(region, r):
    """Fill notches narrower than 2r and round inside corners with r."""
    return offset(offset(region, r), -r)


def opening(region, r):
    """Drop bits narrower than 2r and round outside corners with r."""
    return offset(offset(region, -r), r)


# ----------------------------------------------------------------------------- corner analysis
def _edge_info(edge, rev):
    c = BRepAdaptor_Curve(edge.wrapped)
    t0, t1 = c.FirstParameter(), c.LastParameter()
    p, v = gp_Pnt(), gp_Vec()
    c.D1(t0, p, v); s = (p.X(), p.Y(), v.X(), v.Y())
    c.D1(t1, p, v); e = (p.X(), p.Y(), v.X(), v.Y())
    if rev:
        s, e = (e[0], e[1], -e[2], -e[3]), (s[0], s[1], -s[2], -s[3])
    kind = c.GetType()
    centre = radius = None
    if kind == GeomAbs_Circle:
        circ = c.Circle()
        centre = (circ.Location().X(), circ.Location().Y())
        radius = circ.Radius()
    return s, e, kind, centre, radius


def _angle(a, b):
    la, lb = math.hypot(*a), math.hypot(*b)
    if la < 1e-12 or lb < 1e-12:
        return 0.0, 0.0
    a = (a[0] / la, a[1] / la); b = (b[0] / lb, b[1] / lb)
    return math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1]), 1.0


def convex_corners(region, rmin, min_leftover=0.005):
    """Places where an end mill of radius rmin cannot follow a pocket of this shape: outward
    (convex) arcs tighter than rmin and sharp outward corners. Only corners where the mill would
    leave more than min_leftover of material count. Returns dicts with the corner centre `o`, its
    radius `rho`, the outward direction `n` and the material left `left`."""
    bad = []
    for f in faces(region):
        nz = 1.0 if f.normalAt().z > 0 else -1.0
        for w in [f.outerWire()] + f.innerWires():
            ex = BRepTools_WireExplorer(w.wrapped, f.wrapped)
            infos = []
            while ex.More():
                e = cq.Edge(ex.Current())
                infos.append((e, _edge_info(e, ex.Orientation() == TopAbs_REVERSED)))
                ex.Next()
            n = len(infos)
            for i, (edge, (s, e, kind, centre, radius)) in enumerate(infos):
                if kind == GeomAbs_Circle:
                    sweep, _ = _angle(s[2:], e[2:])
                    if sweep * nz > 0 and radius < rmin:        # turns toward the region: outward arc
                        sweep = abs(sweep)
                        left = (rmin - radius) * (1 / max(math.cos(sweep / 2), 1e-6) - 1)
                        if left > min_leftover:
                            m = edge.positionAt(0.5)
                            d = (m.x - centre[0], m.y - centre[1]); L = math.hypot(*d)
                            bad.append(dict(o=centre, rho=radius, n=(d[0] / L, d[1] / L), left=left))
                nxt = infos[(i + 1) % n][1][0]
                turn, ok = _angle(e[2:], nxt[2:])
                if ok and turn * nz > 0:
                    turn = abs(turn)
                    left = rmin * (1 / max(math.cos(turn / 2), 1e-6) - 1)
                    if left > min_leftover:
                        a = (e[2], e[3]); b = (nxt[2], nxt[3])
                        la, lb = math.hypot(*a), math.hypot(*b)
                        d = (a[0] / la - b[0] / lb, a[1] / la - b[1] / lb); L = math.hypot(*d)
                        bad.append(dict(o=(e[0], e[1]), rho=0.0, n=(d[0] / L, d[1] / L), left=left))
    return bad


def mill_fix(region, r, keep_out=None):
    """Make a pocket region cuttable by an end mill of radius r without losing any of it: every
    corner the mill cannot reach gets a relief disc of radius r + 0.02 that contains the corner
    (a dogbone pushed as far into the pocket as possible). Corners outside `keep_out` (for example
    beyond the part's outline) are left alone."""
    rd = r + 0.02
    for _ in range(3):
        bad = convex_corners(region, r)
        if keep_out is not None:
            bad = [b for b in bad if inside(keep_out, b['o'], tol=0.05)]
        if not bad:
            return region
        discs = []
        for b in bad:
            k = rd - b['rho'] - 0.01
            discs.append(circle((b['o'][0] - k * b['n'][0], b['o'][1] - k * b['n'][1]), rd))
        region = union(region, *discs)
    assert not convex_corners(region, r), 'mill_fix did not converge'
    return region


def inside(region, p, tol=0.0):
    for f in faces(region):
        c = BRepClass_FaceClassifier(f.wrapped, gp_Pnt(p[0], p[1], f.Center().z), 1e-7)
        if c.State() in (TopAbs_IN, TopAbs_ON):
            return True
    if tol > 0:
        v = cq.Vertex.makeVertex(p[0], p[1], 0)
        return any(f.distance(v) <= tol for f in faces(region))
    return False


def distance(a, b):
    """Smallest distance between two regions (0 if they touch or overlap)."""
    if not faces(a) or not faces(b):
        return float('inf')
    return a.distance(b)


# ----------------------------------------------------------------------------- solids
def extrude(region, z0, z1):
    """Prisms of every face of a region between z0 and z1 (list of solids)."""
    out = []
    for f in faces(region):
        out.append(cq.Solid.extrudeLinear(f.translate(V(0, 0, z0)), V(0, 0, z1 - z0)))
    return out