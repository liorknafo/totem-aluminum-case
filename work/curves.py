"""Outlines as curves: lines and circular arcs (no polylines), stored as JSON.

A region is a list of faces; a face is {'outer': loop, 'holes': [loop, ...]}; a loop is a list of
segments, each
    {'line': [[x0, y0], [x1, y1]]}
    {'arc': [[x0, y0], [xm, ym], [x1, y1]], 'c': [cx, cy], 'r': r}   (start, a point on it, end)
fitted to the reference outline within FIT_TOL (clean.py's fitter, fit2d.py). Working copies for
2D operations are sampled within SAG of the curves; every face the model makes is fitted back to
lines and arcs, so the CAD only ever has curves."""
import numpy as np
import cadquery as cq
import shapely
import shapely.geometry as sg
from shapely.ops import unary_union

FIT_TOL = 0.002     # curves stay this close to the reference outline (mm)
SAG = 0.0005        # working polygons stay this close to the curves (mm)


def _arc_points(p, m, q, sag=SAG, c=None, r=None):
    """Points along the circle (centre c, radius r, or the one through p, m, q) from p to q via m;
    a vanishing arc (its points in a line) is its chord."""
    p, m, q = map(np.asarray, (p, m, q))
    if c is None or r is None or not np.isfinite(r):
        if abs(np.cross(m - p, q - p)) < 1e-12:
            return np.array([p, q])
        c, r = circle3(p, m, q)
    c = np.asarray(c)
    if r < 1e-9:
        return np.array([p, q])
    a0, am, a1 = (np.arctan2(*(v - c)[::-1]) for v in (p, m, q))
    # sweep from a0 to a1 passing am
    def ccw(a, b):
        return (b - a) % (2 * np.pi)
    if ccw(a0, am) <= ccw(a0, a1):
        sweep = ccw(a0, a1)
    else:
        sweep = -ccw(a1, a0)
    n = max(2, int(np.ceil(abs(sweep) / (2 * np.arccos(max(-1.0, 1 - sag / r))))) + 1)
    t = a0 + np.linspace(0, sweep, n)
    pts = c + r * np.c_[np.cos(t), np.sin(t)]
    pts[0], pts[-1] = p, q
    return pts


def circle3(a, b, c):
    a, b, c = map(np.asarray, (a, b, c))
    d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    ux = ((a @ a) * (b[1] - c[1]) + (b @ b) * (c[1] - a[1]) + (c @ c) * (a[1] - b[1])) / d
    uy = ((a @ a) * (c[0] - b[0]) + (b @ b) * (a[0] - c[0]) + (c @ c) * (b[0] - a[0])) / d
    cen = np.array([ux, uy])
    return cen, float(np.linalg.norm(a - cen))


# ------------------------------------------------------------------ polygon -> curves
def fit_loop(coords, tol=FIT_TOL, sag=0.012):
    """A closed ring of points -> segments (lines and arcs) within tol."""
    import fit2d
    P = np.asarray(coords)[:-1] if np.allclose(coords[0], coords[-1]) else np.asarray(coords)
    # start at the sharpest corner, so no primitive wraps across the start
    v1 = np.roll(P, 1, 0) - P
    v2 = np.roll(P, -1, 0) - P
    cosang = (v1 * v2).sum(1) / (np.linalg.norm(v1, axis=1) * np.linalg.norm(v2, axis=1) + 1e-30)
    k = int(np.argmax(cosang))
    P = np.r_[np.roll(P, -k, 0), np.roll(P, -k, 0)[:1]]
    out = []
    for pr in fit2d.fit(P, tol, sag=sag):
        i, j = pr[1], pr[2]
        if pr[0] == 'line':
            out.append({'line': [P[i].tolist(), P[j].tolist()]})
        else:
            m = fit2d.mid_point(pr, P)
            c, r = circle3(P[i], m, P[j])
            out.append({'arc': [P[i].tolist(), list(map(float, m)), P[j].tolist()], 'c': c.tolist(), 'r': r})
    return out


def from_shapely(g, tol=FIT_TOL, sag=0.012):
    out = []
    for p in (g.geoms if hasattr(g, 'geoms') else [g]):
        if p.is_empty or p.geom_type != 'Polygon':
            continue
        out.append({'outer': fit_loop(list(p.exterior.coords), tol, sag),
                    'holes': [fit_loop(list(h.coords), tol, sag) for h in p.interiors]})
    return out


# ------------------------------------------------------------------ curves -> polygon
def loop_points(loop, sag=SAG):
    pts = []
    for s in loop:
        pts += list(seg_points(s, sag)[:-1])
    return np.asarray(pts)


def to_shapely(region, sag=SAG):
    polys = []
    for f in region:
        o = loop_points(f['outer'], sag)
        if len(o) < 3:
            continue          # a speck with no area
        holes = [h for h in (loop_points(h, sag) for h in f['holes']) if len(h) >= 3]
        polys.append(sg.Polygon(o, holes).buffer(0))
    return unary_union(polys) if polys else sg.Polygon()


def round_floats(o, nd=9):
    """Round for a readable file; B-spline data is kept exact (its knots and parameters)."""
    if isinstance(o, float):
        return round(o, nd)
    if isinstance(o, dict):
        return {k: (v if k == 'bspline' else round_floats(v, nd)) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [round_floats(v, nd) for v in o]
    return o


# ------------------------------------------------------------------ exact B-rep edges
def from_occ_face(face):
    """A planar cq.Face (from an exact section) -> face dict with its edges as they are: lines,
    circular arcs and B-splines (poles, knots, multiplicities, degree, weights, parameter range)."""
    from OCP.BRepTools import BRepTools_WireExplorer
    def loop(w):
        ex = BRepTools_WireExplorer(w.wrapped)
        segs = []
        while ex.More():
            e = cq.Edge(ex.Current())
            p0, p1 = e.startPoint(), e.endPoint()
            ts = (0.0, 0.5, 1.0)
            kind = e.geomType()
            if kind == 'LINE':
                segs.append({'line': [[p0.x, p0.y], [p1.x, p1.y]]})
            elif kind == 'CIRCLE':
                m = e.positionAt(0.5)
                c = e.arcCenter()
                segs.append({'arc': [[p0.x, p0.y], [m.x, m.y], [p1.x, p1.y]], 'c': [c.x, c.y], 'r': e.radius()})
            else:
                from OCP.BRepAdaptor import BRepAdaptor_Curve
                from OCP.GeomAbs import GeomAbs_BSplineCurve
                from OCP.GeomConvert import GeomConvert
                from OCP.Geom import Geom_TrimmedCurve
                ad = BRepAdaptor_Curve(e.wrapped)
                u0, u1 = ad.FirstParameter(), ad.LastParameter()
                if ad.GetType() == GeomAbs_BSplineCurve:
                    bs = ad.BSpline()
                else:
                    bs = GeomConvert.CurveToBSplineCurve_s(Geom_TrimmedCurve(ad.Curve().Curve(), u0, u1))
                    u0, u1 = bs.FirstParameter(), bs.LastParameter()
                poles = [[bs.Pole(i).X(), bs.Pole(i).Y()] for i in range(1, bs.NbPoles() + 1)]
                segs.append({'bspline': {'degree': bs.Degree(), 'poles': poles,
                                         'weights': [bs.Weight(i) for i in range(1, bs.NbPoles() + 1)],
                                         'knots': [bs.Knot(i) for i in range(1, bs.NbKnots() + 1)],
                                         'mults': [bs.Multiplicity(i) for i in range(1, bs.NbKnots() + 1)],
                                         'u': [u0, u1], 'reversed': ts[0] == 1.0},
                             'ends': [[p0.x, p0.y], [p1.x, p1.y]]})
            ex.Next()
        return segs
    return {'outer': chain(loop(face.outerWire())), 'holes': [chain(loop(w)) for w in face.innerWires()]}


def ends(s):
    if 'line' in s:
        return s['line'][0], s['line'][1]
    if 'arc' in s:
        return s['arc'][0], s['arc'][2]
    return s['ends'][0], s['ends'][1]


def reverse(s):
    if 'line' in s:
        return {'line': s['line'][::-1]}
    if 'arc' in s:
        return dict(s, arc=s['arc'][::-1])
    return dict(s, ends=s['ends'][::-1])


def chain(segs, tol=1e-4):
    """Order the segments' directions so each starts where the previous one ends."""
    out = list(segs)
    d = lambda a, b: float(np.hypot(a[0] - b[0], a[1] - b[1]))
    if len(out) > 1:
        a0, a1 = ends(out[0])
        b0, b1 = ends(out[1])
        if min(d(a0, b0), d(a0, b1)) < min(d(a1, b0), d(a1, b1)):
            out[0] = reverse(out[0])
    for i in range(1, len(out)):
        prev = ends(out[i - 1])[1]
        s0, s1 = ends(out[i])
        if d(s1, prev) < d(s0, prev):
            out[i] = reverse(out[i])
        assert d(ends(out[i])[0], prev) < tol, ('loop not closed', i, prev, ends(out[i]))
    return out


def bspline_edge(d, z=0.0):
    from OCP.Geom import Geom_BSplineCurve
    from OCP.TColgp import TColgp_Array1OfPnt
    from OCP.TColStd import TColStd_Array1OfReal, TColStd_Array1OfInteger
    from OCP.gp import gp_Pnt
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    P = TColgp_Array1OfPnt(1, len(d['poles']))
    for i, (x, y) in enumerate(d['poles'], 1):
        P.SetValue(i, gp_Pnt(x, y, z))
    Wt = TColStd_Array1OfReal(1, len(d['weights']))
    for i, w in enumerate(d['weights'], 1):
        Wt.SetValue(i, w)
    K = TColStd_Array1OfReal(1, len(d['knots']))
    for i, k in enumerate(d['knots'], 1):
        K.SetValue(i, k)
    M = TColStd_Array1OfInteger(1, len(d['mults']))
    for i, m in enumerate(d['mults'], 1):
        M.SetValue(i, m)
    crv = Geom_BSplineCurve(P, Wt, K, M, d['degree'])
    e = cq.Edge(BRepBuilderAPI_MakeEdge(crv, d['u'][0], d['u'][1]).Edge())
    return e


def seg_points(s, sag=SAG):
    if 'line' in s:
        return np.asarray(s['line'])
    if 'arc' in s:
        return _arc_points(*s['arc'], sag=sag, c=s.get('c'), r=s.get('r'))
    e = bspline_edge(s['bspline'])
    n = max(20, int(e.Length() / 0.02))
    pts = np.array([e.positionAt(t).toTuple()[:2] for t in np.linspace(0, 1, n + 1)])
    a = np.asarray(s['ends'][0])
    if np.linalg.norm(pts[-1] - a) < np.linalg.norm(pts[0] - a):
        pts = pts[::-1]
    pts[0], pts[-1] = s['ends'][0], s['ends'][1]
    return pts


def seg_edge(s, z=0.0, v0=None, v1=None):
    """OCC edge of a segment; with v0, v1 (TopoDS vertices) it runs between those exactly."""
    from OCP.gp import gp_Pnt
    from OCP.GC import GC_MakeArcOfCircle, GC_MakeSegment
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    if 'line' in s:
        (a, b) = s['line']
        if v0 is not None:
            return cq.Edge(BRepBuilderAPI_MakeEdge(v0, v1).Edge())
        return cq.Edge(BRepBuilderAPI_MakeEdge(gp_Pnt(a[0], a[1], z), gp_Pnt(b[0], b[1], z)).Edge())
    if 'arc' in s:
        p, m, q = s['arc']
        arc = GC_MakeArcOfCircle(gp_Pnt(p[0], p[1], z), gp_Pnt(m[0], m[1], z), gp_Pnt(q[0], q[1], z)).Value()
        if v0 is not None:
            return cq.Edge(BRepBuilderAPI_MakeEdge(arc, v0, v1).Edge())
        return cq.Edge(BRepBuilderAPI_MakeEdge(arc).Edge())
    e = bspline_edge(s['bspline'], z)
    if v0 is None:
        return e
    from OCP.BRep import BRep_Tool
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    ad = BRepAdaptor_Curve(e.wrapped)
    crv = ad.Curve().Curve()
    u0, u1 = ad.FirstParameter(), ad.LastParameter()
    p0 = BRep_Tool.Pnt_s(v0)
    a = crv.Value(u0)
    if a.Distance(p0) > crv.Value(u1).Distance(p0):
        return cq.Edge(BRepBuilderAPI_MakeEdge(crv, v1, v0, u0, u1).Edge().Reversed())
    return cq.Edge(BRepBuilderAPI_MakeEdge(crv, v0, v1, u0, u1).Edge())


def to_face(f, z=0.0):
    """Exact planar face from a face dict (its own curves, no refit); consecutive segments share
    their vertex, so each loop is closed by construction."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeWire
    from OCP.gp import gp_Pnt
    def wire(loop):
        vs = [BRepBuilderAPI_MakeVertex(gp_Pnt(ends(s)[0][0], ends(s)[0][1], z)).Vertex() for s in loop]
        w = BRepBuilderAPI_MakeWire()
        for i, s in enumerate(loop):
            w.Add(seg_edge(s, z, vs[i], vs[(i + 1) % len(loop)]).wrapped)
        assert w.IsDone(), 'wire from curves'
        return cq.Wire(w.Wire())
    face = cq.Face.makeFromWires(wire(f['outer']), [wire(h) for h in f['holes']])
    assert face.isValid(), 'face from curves'
    return face


def exact_outline(shape, zs):
    """The outline (holes filled) of a B-rep part over several heights: exact sections moved to
    z = 0, fused and unified. -> cq.Face"""
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    faces = []
    for z in zs:
        pl = cq.Face.makePlane(1000, 1000, basePnt=(150, -100, z))
        for f in shape.intersect(pl).Faces():
            faces.append(cq.Face.makeFromWires(f.outerWire()).translate(cq.Vector(0, 0, -z)))
    u = faces[0].fuse(*faces[1:]) if len(faces) > 1 else faces[0]
    uf = ShapeUpgrade_UnifySameDomain(u.wrapped, True, True, True)
    uf.Build()
    u = cq.Shape.cast(uf.Shape())
    big = max(u.Faces(), key=lambda f: f.Area())
    return cq.Face.makeFromWires(big.outerWire())


def exact_sections(shape, z):
    """The shape's exact section at height z, as faces at z = 0."""
    pl = cq.Face.makePlane(1000, 1000, basePnt=(150, -100, z))
    return [f.translate(cq.Vector(0, 0, -z)) for f in shape.intersect(pl).Faces()]


def face_cut(face, tools):
    """Planar face less planar faces (all at z = 0), exact. -> [cq.Face]"""
    if not tools:
        return [face]
    r = face.cut(*tools)
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    u = ShapeUpgrade_UnifySameDomain(r.wrapped, True, True, True)
    u.Build()
    return [f for f in cq.Shape.cast(u.Shape()).Faces() if f.Area() > 1e-4]
