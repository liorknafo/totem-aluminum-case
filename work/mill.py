"""Make a part cuttable on a 3-axis mill with a flat end mill of radius R_TOOL, from above and from
below (two setups), keeping every needed clearance.

1. hull_fill: add material wherever the end mill could not remove it (slots narrower than the tool,
   inside corners sharper than its radius, engravings, voids hidden under an overhang). Worked out
   as exact 2D closings of the part's horizontal sections, one height band at a time, so the result
   is never more than what the mill would leave, and sloped faces are kept as they are.
2. open_tools: turn every keep-out (pocket that must stay empty) into a prism the end mill can cut
   from the open side: each footprint gets dogbones (radius R_CUT) at its convex corners, and the
   prism runs out to the side the pocket is cut from.

A void that is a union of discs of radius R_CUT at every height, and that only shrinks moving
away from the side it is cut from, is exactly what the mill can make; unions keep both properties,
so the filled part minus the opened keep-outs is machinable as a whole.
"""
import numpy as np
import cadquery as cq
import shapely, shapely.geometry as sg
from shapely.ops import unary_union

R_TOOL = 1.0   # smallest end mill: Ø2 mm flat
R_CUT = 1.05   # inside corners and slots are drawn with this radius (CAM margin over R_TOOL)
QS = 6         # arc segments per quarter circle: chords stay 1.041 mm from the centre, so a Ø2 tool fits
EPS = 0.004    # sections are taken this far inside each height band
MIN_FILL = 0.003  # mm^3: fill prisms smaller than this are dropped
SNAP = 0.15    # keep-out levels closer than this are cut as one (at the deeper level)


def mesh_of(shape, tol=0.004):
    import trimesh
    v, f = shape.tessellate(tol, 0.05)
    m = trimesh.Trimesh(np.array([p.toTuple() for p in v]), np.array(f), process=True)
    return m


def pieces(g):
    if g is None or g.is_empty:
        return []
    if g.geom_type in ('MultiPolygon', 'GeometryCollection'):
        return [x for x in g.geoms if x.geom_type == 'Polygon' and not x.is_empty]
    return [g] if g.geom_type == 'Polygon' else []


def tidy(g):
    """Drop collinear/near-duplicate vertices and snap to 1e-5 mm: keeps unions of near-identical
    sections fast (their coincident edges otherwise pile up)."""
    g = shapely.set_precision(g.simplify(5e-5), 1e-5)
    return shapely.set_precision(g, 0)  # keep the snapped coordinates, drop the fixed grid (it breaks small buffers)


def U(geoms):
    return tidy(shapely.union_all([g for g in geoms if g is not None and not g.is_empty]))


def section(m, z):
    """Shapely region of the mesh's cut at height z."""
    import trimesh
    segs, _ = trimesh.intersections.mesh_plane(m, [0, 0, 1.0], [0, 0, z], return_faces=True)
    if len(segs) == 0:
        return sg.Polygon()
    p = trimesh.load_path(segs[:, :, :2])
    polys = [sg.Polygon(q.exterior, q.interiors).buffer(0) for q in p.polygons_full]
    return U(polys) if polys else sg.Polygon()


def levels(m, extra=()):
    """Heights of the mesh's horizontal faces (where sections change abruptly)."""
    nz = m.face_normals[:, 2]
    zs = m.triangles_center[np.abs(nz) > 0.9999, 2]
    lv = np.unique(np.round(np.r_[zs, m.bounds[:, 2], list(extra)], 4))
    out = [lv[0]]
    for z in lv[1:]:
        if z - out[-1] > 2 * EPS + 1e-4:
            out.append(z)
    return np.array(out)


def no_pinholes(g, min_area=1e-4):
    """Drop holes of (near) zero area: GEOS buffer leaves them where a hole just closes, and the
    next negative buffer would grow each back into a full disc."""
    return unary_union([sg.Polygon(p.exterior, [i for i in p.interiors if sg.Polygon(i).area > min_area])
                        for p in pieces(g)])


def closing(g, r=R_CUT):
    return no_pinholes(g.buffer(r, quad_segs=QS)).buffer(-r, quad_segs=QS)


def opening(g, r=R_CUT):
    return g.buffer(-r, quad_segs=QS).buffer(r, quad_segs=QS)


def poly_face(poly, z):
    def wire(coords):
        return cq.Wire.makePolygon([cq.Vector(x, y, z) for x, y in coords[:-1]], close=True)
    return cq.Face.makeFromWires(wire(list(poly.exterior.coords)), [wire(list(i.coords)) for i in poly.interiors])


def prism(poly, z0, z1):
    from shapely.geometry.polygon import orient
    s = cq.Solid.extrudeLinear(poly_face(orient(poly, 1.0), z0), cq.Vector(0, 0, z1 - z0))
    assert s.Volume() > 0, 'inverted prism'
    return s


def clean_poly(g, tol=0.002, min_area=5e-3):
    """Drop slivers (tessellation noise) and specks."""
    g = g.buffer(-tol, quad_segs=2).buffer(tol, quad_segs=2)
    return unary_union([p.simplify(0.0005) for p in pieces(g) if p.area > min_area])


# ------------------------------------------------------------------ fill what the mill can't cut
def same(p, q, tol=0.005):
    """Two regions differ by less than a 2*tol wide sliver anywhere (mesh-derived walls wobble)."""
    return p.symmetric_difference(q).buffer(-tol, quad_segs=2).is_empty


def hull_fill(shape, keep_out=None, r=R_CUT, log=print, dz=0.025):
    """Prisms of material to add so that the part is exactly what a radius-r flat end mill leaves
    (from above and from below). keep_out: shapely region never filled (e.g. drilled holes), or a
    function (z0, z1) -> region for a height slice (e.g. the keep-out pockets cut before).
    Between horizontal faces the sections are constant (vertical walls) unless faces slope; sloped
    bands are cut into dz thin slices so a curved overhang is filled up to within dz."""
    m = shape if not hasattr(shape, 'wrapped') else mesh_of(shape)   # a solid or an exact mesh
    L = levels(m)
    sub = []           # (z0, z1, section near z0, section near z1)
    for a, b in zip(L[:-1], L[1:]):
        s0, s1 = section(m, a + EPS), section(m, b - EPS)
        sm = section(m, (a + b) / 2)
        if same(s0, s1) and same(s0, sm):
            sub.append((a, b, s0, s1))
            continue
        ts = np.linspace(a, b, max(2, int(np.ceil((b - a) / dz)) + 1))
        ss = [s0] + [section(m, t) for t in ts[1:-1]] + [s1]
        sub += [(ts[i], ts[i + 1], ss[i], ss[i + 1]) for i in range(len(ts) - 1)]
    nb = len(sub)
    # material at or above / at or below each slice (under-estimated on sloped faces)
    above, acc = [None] * nb, sg.Polygon()
    for k in range(nb - 1, -1, -1):
        above[k] = U([acc, sub[k][3]])
        acc = U([acc, sub[k][2], sub[k][3]])
    below, acc = [None] * nb, sg.Polygon()
    for k in range(nb):
        below[k] = U([acc, sub[k][2]])
        acc = U([acc, sub[k][2], sub[k][3]])
    per_band = []
    for k, (a, b, s0, s1) in enumerate(sub):
        hull = closing(above[k], r).intersection(closing(below[k], r))
        core = s0.intersection(s1)
        g = hull.difference(core)
        ko = keep_out(a, b) if callable(keep_out) else keep_out
        if ko is not None:
            g = g.difference(ko)
        g = clean_poly(g, 0.003, 2e-3)
        # overlap the existing material by 0.03 so the fuse is clean
        f = clean_poly(g.buffer(0.03, quad_segs=4).intersection(hull), 0.001, 2e-3) if not g.is_empty else g
        if ko is not None:
            f = f.difference(ko)
        per_band.append((a, b, tidy(f), g.area * (b - a)))
    # stack: a piece that repeats unchanged in the next slices becomes one taller prism
    fills, vol, active = [], sum(v for *_, v in per_band), []
    for a, b, f, _ in per_band:
        nxt = []
        for p in pieces(f):
            for i, (q, z0, z1) in enumerate(active):
                if abs(z1 - a) < 1e-9 and np.allclose(q.bounds, p.bounds, atol=0.01) and same(q, p):
                    # the same piece up to a < 0.01 mm sliver: keep the smaller one (never more than the hull)
                    nxt.append((q.intersection(p) if q.intersection(p).area > 0.9 * p.area else q, z0, b))
                    active.pop(i); break
            else:
                nxt.append((p, a, b))
        fills += [prism(q.simplify(0.003), z0, z1) for q, z0, z1 in active]
        active = nxt
    fills += [prism(q.simplify(0.003), z0, z1) for q, z0, z1 in active]
    # specks (thin slices on the mesh-derived slopes) are below any machining tolerance and the
    # kernel often can't fuse them
    tiny = [f for f in fills if f.Volume() < MIN_FILL]
    fills = [f for f in fills if f.Volume() >= MIN_FILL]
    if tiny:
        log(f'hull fill: dropped {len(tiny)} specks under {MIN_FILL} mm^3 (total {sum(f.Volume() for f in tiny):.3f} mm^3)')
    log(f'hull fill: {len(L) - 1} height bands ({nb} slices), {len(fills)} prisms, ~{vol:.1f} mm^3 of material added')
    return fills


# ------------------------------------------------------------------ keep-outs the mill can cut
def open_superset(fp, r=R_CUT, log=None):
    """Smallest-effort superset of a region that is a union of discs of radius r: dogbones at its
    convex corners (a disc through the corner, centre on the inside), and, where the region is
    narrower than the tool, the region widened. Returns a polygon containing fp."""
    if fp.is_empty:
        return fp
    res = fp
    for it in range(300):
        op = opening(res, r)
        left = clean_poly(fp.difference(op), 1e-4, 1e-5)
        if left.is_empty or left.area < 1e-6:
            return op
        centres = res.buffer(-r, quad_segs=QS)
        add = []
        for piece in pieces(left):
            # the point of the leftover farthest from what the tool can already reach
            pts = np.array(piece.exterior.segmentize(0.02).coords)
            d = shapely.distance(op, shapely.points(pts)) if not op.is_empty else np.ones(len(pts))
            t = sg.Point(pts[int(np.argmax(d))])
            if centres.is_empty or centres.distance(t) > 2 * r:
                c = piece.centroid      # narrower than the tool here: widen toward its middle
            else:
                c = shapely.ops.nearest_points(centres, t)[0]
            v = np.array([c.x - t.x, c.y - t.y]); n = np.linalg.norm(v)
            u = v / n if n > 1e-9 else np.array([0.0, 0.0])
            # slightly larger than r so its polygon survives an erosion by r; covers t by 0.01
            q = np.array([t.x, t.y]) + u * (r + 0.01 - 0.02)
            add.append(sg.Point(q).buffer(r + 0.01, quad_segs=QS))
        res = unary_union([res] + add)
    raise RuntimeError('open_superset did not converge')


def layer_keep_out(layers, side):
    """(z0, z1) -> the opened keep-out region anywhere in that height slice."""
    def f(a, b):
        if side == 'below':   # layer at z covers heights up to z; footprints grow downward
            zs = [(z, g) for z, g in layers if z > a + 1e-6]
            return min(zs, key=lambda e: e[0])[1] if zs else sg.Polygon()
        zs = [(z, g) for z, g in layers if z < b - 1e-6]
        return max(zs, key=lambda e: e[0])[1] if zs else sg.Polygon()
    return f


def grown_entries(shape, grow, side, zmin, zmax):
    """Another part as a keep-out: per height band of its mesh within [zmin, zmax], the union of its
    sections grown by `grow` sideways, reaching `grow` further toward the side it is cut from
    (a cylinder offset: contains the true offset)."""
    m = shape if not hasattr(shape, 'wrapped') else mesh_of(shape)
    L = levels(m)
    out = []
    for a, b in zip(L[:-1], L[1:]):
        if b < zmin or a > zmax:
            continue
        a, b = max(a, zmin), min(b, zmax)   # only the part of the band inside [zmin, zmax]
        g = U([section(m, h) for h in (a + EPS, (a + b) / 2, b - EPS)])
        if not g.is_empty:
            out.append((a - grow if side == 'above' else b + grow, g.buffer(grow, quad_segs=QS)))
    return out


def open_tools(tools, side, zfar, exclude=None, log=print, extra_entries=()):
    """Keep-out solids -> what a radius-R_CUT end mill cuts from the open side. side='below': the
    part is cut from below, so at height z everything under a keep-out whose top is at or above z
    goes; side='above': the same from above. Each keep-out footprint gets dogbones (open_superset),
    the footprints are merged in 2D height by height, and the result is a stack of layers that only
    touch at their top and bottom faces (one cheap boolean instead of hundreds of overlapping tools).
    exclude(z) -> shapely region removed from a footprint whose far end is at z (material that must
    stay, e.g. the pad bosses)."""
    entries = []       # (z, opened footprint): the keep-out reaches z at this footprint
    for t in tools:
        for s in t.Solids():
            m = mesh_of(s, 0.002)
            L = levels(m)
            secs = [(h, section(m, h)) for h in
                    sorted(set([a + EPS for a in L[:-1]] + [b - EPS for b in L[1:]]))]
            if side == 'below':
                steps = [(b, U([g for h, g in secs if h >= b - 2 * EPS])) for b in L[1:]]
            else:
                steps = [(a, U([g for h, g in secs if h <= a + 2 * EPS])) for a in L[:-1]]
            done = sg.Polygon()
            for z, fp in (steps[::-1] if side == 'below' else steps):
                if exclude is not None:
                    fp = fp.difference(exclude(z))
                fp = clean_poly(fp, 1e-4)
                if fp.is_empty:
                    continue
                done = U([open_superset(fp), done])
                entries.append((z, done))
    for z, fp in extra_entries:
        fp = clean_poly(fp, 1e-4)
        if not fp.is_empty:
            entries.append((z, open_superset(fp)))
    # levels closer than SNAP become one, at the deeper cut (more clearance): thin layers in
    # between are more than the kernel can cut reliably
    zs = sorted(set(round(z, 6) for z, _ in entries), reverse=(side == 'below'))
    snap, shift = {}, 0.0
    for z in zs:
        rep = next((r for r in snap.values() if abs(r - z) < SNAP), z)
        snap[z] = rep; shift = max(shift, abs(rep - z))
    entries = [(snap[round(z, 6)], g) for z, g in entries]
    # V(z): union of the footprints that reach z; constant between consecutive entry heights
    entries.sort(key=lambda e: -e[0] if side == 'below' else e[0])
    zs = sorted(set(round(z, 6) for z, _ in entries), reverse=(side == 'below'))
    acc, i, layers = sg.Polygon(), 0, []
    for z in zs:
        while i < len(entries) and round(entries[i][0], 6) == z:
            acc = U([acc, entries[i][1]]); i += 1
        layers.append((z, acc))
    out = []           # one group per layer: neighbouring layers touch face to face, which stalls the kernel
    for k, (z, poly) in enumerate(layers):
        z_next = layers[k + 1][0] if k + 1 < len(layers) else zfar
        lo, hi = (z_next, z) if side == 'below' else (z, z_next)
        out.append([prism(p, lo, hi) for p in pieces(poly)])
    log(f'opened keep-outs: {len(tools)} tools -> {len(layers)} layers (levels moved up to {shift:.2f}), {sum(map(len, out))} prisms cut from {side}')
    return out, layers


# ------------------------------------------------------------------ planar-faced parts as meshes
def mesh_union(part, fills, log=print):
    """Union of a part made of planar faces (the site's bottoms are triangle meshes) with the fill
    prisms, done on exact triangle meshes (manifold3d), then turned back into a solid with one face
    per flat region."""
    import trimesh
    nonplanar = [f for f in part.Faces() if f.geomType() != 'PLANE']
    if nonplanar:   # e.g. the skirt's curved outer faces: faceted within 0.001 mm
        log(f'mesh union: {len(nonplanar)} curved faces become flat facets (within 0.001 mm)')
    pm = closed_mesh(part)
    fm = [mesh_of(f, 0.001) for f in fills]
    u = trimesh.boolean.union([pm] + fm, engine='manifold')
    log(f'mesh union: {len(u.faces)} triangles, watertight {u.is_watertight}, volume +{u.volume - pm.volume:.1f} mm^3')
    return mesh_to_solid(u), u.volume - pm.volume


def fill_loops(m):
    """Close small flat holes (any number of edges): each loop of boundary edges is projected on
    its own plane and triangulated."""
    import trimesh, networkx as nx
    from trimesh.grouping import group_rows
    e = m.edges_sorted
    b = e[group_rows(e, require_count=1)]
    if len(b) == 0:
        return m
    g = nx.Graph(); g.add_edges_from(map(tuple, b))
    new = []
    for cyc in nx.cycle_basis(g):
        if len(cyc) < 3:
            continue
        P = m.vertices[cyc]
        n = np.zeros(3)
        for i in range(len(P)):   # Newell normal
            a, c = P[i], P[(i + 1) % len(P)]
            n += [(a[1] - c[1]) * (a[2] + c[2]), (a[2] - c[2]) * (a[0] + c[0]), (a[0] - c[0]) * (a[1] + c[1])]
        n /= np.linalg.norm(n)
        u = np.cross(n, [1, 0, 0] if abs(n[0]) < 0.9 else [0, 1, 0]); u /= np.linalg.norm(u); v = np.cross(n, u)
        uv = np.c_[(P - P[0]) @ u, (P - P[0]) @ v]
        poly = sg.Polygon(uv).buffer(0)
        if poly.is_empty or poly.geom_type != 'Polygon':
            continue
        for t in shapely.ops.triangulate(sg.MultiPoint(uv)):
            if poly.buffer(1e-9).contains(t.centroid):
                idx = [int(np.argmin(np.linalg.norm(uv - np.array(c), axis=1))) for c in list(t.exterior.coords)[:3]]
                new.append([cyc[i] for i in idx])
    if new:
        m = trimesh.Trimesh(m.vertices, np.vstack([m.faces, new]), process=True)
        trimesh.repair.fix_normals(m)
    return m


def closed_mesh(part):
    """Tessellation of a part as a closed mesh: a boolean result can tessellate with a hairline
    gap here and there, so other tolerances are tried, near-duplicate vertices merged and
    pin-holes filled."""
    import trimesh
    for tol in (0.001, 0.0007, 0.0015, 0.0005, 0.002):
        m = mesh_of(part, tol)
        if m.is_watertight and m.is_volume:
            return m
        for digits in (6, 5, 4, 3):
            m.merge_vertices(digits_vertex=digits)
            m.update_faces(m.nondegenerate_faces()); m.update_faces(m.unique_faces())
            m.remove_unreferenced_vertices()
            # sliver faces on edges shared by more than two faces (a hairline pinch): drop them,
            # then close the hole they leave
            from trimesh.grouping import group_rows
            e = m.edges_sorted
            nm = set(map(tuple, e[[i for g in group_rows(e) if len(g) > 2 for i in g]]))
            if nm:
                fe = m.faces_unique_edges
                es = m.edges_unique
                badf = [f for f in range(len(m.faces)) if m.area_faces[f] < 1e-3 and
                        any(tuple(es[k]) in nm for k in fe[f])]
                keep = np.ones(len(m.faces), bool); keep[badf] = False
                m.update_faces(keep); m.remove_unreferenced_vertices()
            trimesh.repair.fill_holes(m); m = fill_loops(m); trimesh.repair.fix_normals(m)
            if m.is_watertight and m.is_volume:
                return m
    raise AssertionError(('mesh not closed', len(m.faces), m.is_watertight))


def collapse_short_edges(X, F, tol):
    """Merge the two ends of every edge shorter than tol (OpenCASCADE can't build such an edge)
    and drop the triangles that collapse. Only vertices joined by an edge are merged: coincident
    vertices of parts that merely touch stay apart."""
    F = np.asarray(F).copy()
    parent = np.arange(len(X))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    short = E[np.linalg.norm(X[E[:, 0]] - X[E[:, 1]], axis=1) < tol]
    for a, b in short:
        ra, rb = root(a), root(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    if len(short):
        F = np.vectorize(root)(F)
        F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 2] != F[:, 0])]
    return F


def remove_slivers(X, F, eps=1e-10):
    """Zero-area triangles (a vertex lying on the opposite edge) make degenerate faces. Remove
    each by splitting its neighbour across the long edge at that vertex: exact, stays closed."""
    F = [list(f) for f in F]
    for _ in range(20):
        triangles = X[np.asarray(F)]
        areas = 0.5 * np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1)
        sl = np.flatnonzero(areas < eps).tolist()
        if not sl:
            break
        owner = {}
        for i, (a, b, c) in enumerate(F):
            owner[(a, b)] = i; owner[(b, c)] = i; owner[(c, a)] = i
        dead, add, used = set(), [], set()
        for i in sl:
            if i in used:
                continue
            f = F[i]
            # longest edge p->q, r the vertex in between
            k = max(range(3), key=lambda j: np.linalg.norm(X[f[j]] - X[f[(j + 1) % 3]]))
            p, q, r = f[k], f[(k + 1) % 3], f[(k + 2) % 3]
            g = owner.get((q, p))
            if g is None or g in used or g in dead:
                continue
            s_ = [v for v in F[g] if v not in (p, q)][0]
            dead.update((i, g)); used.update((i, g))
            add += [[q, r, s_], [r, p, s_]]
        if not dead:
            break
        F = [f for i, f in enumerate(F) if i not in dead] + add
    return np.array(F)


def mesh_to_solid(m):
    """Build coplanar patches with shared topology; never weld coincident contact edges."""
    import trimesh, manifold3d as mf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
    from OCP.BRep import BRep_Builder
    from OCP.TopoDS import TopoDS_Shell, TopoDS_Solid, TopoDS
    from OCP.gp import gp_Pnt, gp_Pln, gp_Dir
    vol = m.volume
    assert m.is_watertight and m.is_winding_consistent, 'conversion needs a closed oriented mesh'
    vertices = np.array(m.vertices, dtype=np.float64, order='C', copy=True).view(np.ndarray)
    faces = np.array(m.faces, dtype=np.uint64, order='C', copy=True).view(np.ndarray)
    mm = mf.Manifold(mf.Mesh64(vertices, faces))
    assert mm.status() == mf.Error.NoError, mm.status()
    # Remove numerical zero-length edges with a topology-preserving operation, not a vertex weld.
    out = mm.simplify(1e-6).to_mesh64()   # above OpenCASCADE's 1e-7 confusion distance
    X = np.asarray(out.vert_properties)[:, :3]
    F = collapse_short_edges(X, np.asarray(out.tri_verts), 1e-6)
    F = remove_slivers(X, F, eps=1e-12)
    m = trimesh.Trimesh(X, F, process=False)
    # simplify can pinch off a closed speck (a few faces, ~0 volume): drop it
    comps = trimesh.graph.connected_components(m.face_adjacency, nodes=np.arange(len(F)), min_len=1)
    if len(comps) > 1:
        main = max(comps, key=len)
        F = F[np.sort(main)]
        m = trimesh.Trimesh(X, F, process=False)
    assert m.is_watertight and abs(m.volume - vol) < 0.03, 'mesh regularization changed geometry'
    N = m.face_normals
    adjacent = m.face_adjacency
    pairs = adjacent[np.linalg.norm(N[adjacent[:, 0]] - N[adjacent[:, 1]], axis=1) < 1e-7]
    groups = trimesh.graph.connected_components(pairs, nodes=np.arange(len(F)), min_len=1)
    V, E = {}, {}
    builder = BRep_Builder(); shell = TopoDS_Shell(); builder.MakeShell(shell)

    def vertex(i):
        if i not in V:
            V[i] = BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, X[i]))).Vertex()
        return V[i]

    def edge(a, b):
        key = (min(a, b), max(a, b))
        if key not in E:
            mk = BRepBuilderAPI_MakeEdge(vertex(key[0]), vertex(key[1]))
            assert mk.IsDone(), ('edge', key, X[key[0]].tolist(), X[key[1]].tolist(), float(np.linalg.norm(X[key[0]] - X[key[1]])))
            E[key] = mk.Edge()
        return E[key] if a < b else TopoDS.Edge_s(E[key].Reversed())

    def patch(ids):
        triangles = F[ids]
        edges = np.vstack([triangles[:, [0, 1]], triangles[:, [1, 2]], triangles[:, [2, 0]]])
        _, inverse, counts = np.unique(np.sort(edges, axis=1), axis=0, return_inverse=True, return_counts=True)
        boundary = edges[counts[inverse] == 1]
        successor = {int(a): int(b) for a, b in boundary}
        valid = len(successor) == len(boundary) and len(set(successor.values())) == len(boundary)
        loops = []
        if valid:
            while successor:
                start = next(iter(successor)); loop = [start]; i = successor.pop(start)
                while i != start:
                    loop.append(i); i = successor.pop(i)
                loops.append(loop)
            n = N[ids[np.argmax(m.area_faces[ids])]]
            rings = [X[loop] - X[loop[0]] for loop in loops]
            areas = [np.sum(np.cross(ring, np.roll(ring, -1, axis=0)) @ n) / 2 for ring in rings]
            valid = sum(a > 1e-18 for a in areas) == 1 and all(abs(a) > 1e-18 for a in areas)
            valid &= np.max(np.abs((X[triangles.ravel()] - X[triangles[0, 0]]) @ n)) < 1e-7
        if valid:
            face = None
            for k in np.argsort(areas)[::-1]:
                loop = loops[k]; wire = BRepBuilderAPI_MakeWire()
                for a, b in zip(loop, loop[1:] + loop[:1]):
                    wire.Add(edge(a, b))
                if face is None:
                    plane = gp_Pln(gp_Pnt(*map(float, X[loop[0]])), gp_Dir(*map(float, n)))
                    face = BRepBuilderAPI_MakeFace(plane, wire.Wire(), True)
                else:
                    face.Add(wire.Wire())
            result = cq.Face(face.Face())
            valid = result.isValid()
        if valid:
            builder.Add(shell, result.wrapped)
            return
        assert len(ids) > 1, ('invalid mesh triangle', X[F[ids[0]]].tolist())
        # A patch whose hole touches its outline needs separate faces, not a sewn repair.
        centres = m.triangles_center[ids]
        order = np.argsort(centres[:, np.argmax(np.ptp(centres, axis=0))]); middle = len(ids) // 2
        for half in (ids[order[:middle]], ids[order[middle:]]):
            selected = np.zeros(len(F), bool); selected[half] = True
            links = pairs[selected[pairs].all(axis=1)]
            for part in trimesh.graph.connected_components(links, nodes=half, min_len=1):
                patch(part)

    for group in groups:
        patch(group)
    shell.Closed(True)
    solid = TopoDS_Solid(); builder.MakeSolid(solid); builder.Add(solid, shell)
    result = cq.Shape.cast(solid)
    assert result.isValid() and len(result.Solids()) == 1, 'invalid mesh conversion'
    # Reserve 0.02 mm³ of the total 0.05 mm³ budget for the STEP round trip.
    assert abs(result.Volume() - vol) < 0.03, ('mesh to solid', result.Volume(), vol)
    return result


def mf_bool(base, others, op):
    """Exact (float64) manifold3d boolean; the result keeps manifold3d's own vertex indexing
    (where two regions only touch it keeps separate vertices: merging them would make the shell
    non-manifold)."""
    import manifold3d as mf, trimesh
    def M(m):
        V = np.array(np.asarray(m.vertices), dtype=np.float64, order='C').view(np.ndarray)
        F = np.array(np.asarray(m.faces), dtype=np.uint64, order='C').view(np.ndarray)
        mm = mf.Mesh64(vert_properties=V, tri_verts=F)
        mm.merge()
        r = mf.Manifold(mm)
        assert r.status() == mf.Error.NoError, r.status()
        return r
    a = M(base)
    b = mf.Manifold.batch_boolean([M(o) for o in others], mf.OpType.Add) if len(others) > 1 else M(others[0])
    r = {'difference': a - b, 'union': a + b, 'intersection': a ^ b}[op]
    out = r.to_mesh64()
    return trimesh.Trimesh(np.ascontiguousarray(np.asarray(out.vert_properties)[:, :3]), np.ascontiguousarray(out.tri_verts), process=False)


def mesh_machinable(part, exact, opened_groups, layers, side, drill, log=print, extra=None, flat_exempt=None):
    """make_machinable for a part made of flat faces (the site's triangle-mesh bottoms), all on
    exact meshes: cut the exact keep-outs and the opened ones, fill what the mill can't cut
    (outside those pockets and the drilled holes), back to a solid."""
    m = closed_mesh(part)
    flat = flatten_slopes(m, exempt=flat_exempt, log=log)
    if flat:
        m = mf_bool(m, [mesh_of(f, 0.001) for f in flat], 'difference')
    v0 = m.volume
    tools = [closed_mesh(t) for t in exact for t in t.Solids()]
    tools += [mesh_of(p, 0.001) for g in opened_groups for p in g]
    m = mf_bool(m, tools, 'difference')
    log(f'mesh cut: {v0 - m.volume:.1f} mm^3 removed, {len(m.faces)} triangles')
    ko = layer_keep_out(layers, side)
    fills = hull_fill(m, keep_out=lambda a, b: unary_union([drill, ko(a, b)] + [e(a, b) for e in extra or []]), log=log)
    v1 = m.volume
    if fills:
        m = mf_bool(m, [mesh_of(f, 0.001) for f in fills], 'union')
        log(f'mesh fill: {m.volume - v1:.1f} mm^3 added')
    # sealed micro-voids (where a fill meets a wall) are separate inside-out pieces: fill them
    comps = m.split(only_watertight=False)
    if len(comps) > 1:
        main = max(comps, key=lambda c: c.volume)
        log(f'mesh: {len(comps) - 1} sealed micro-voids filled ({sum(c.volume for c in comps if c is not main):.4f} mm^3)')
        m = main
    # strict 2.5D (flat end mills only), then reliefs wherever a Ø2 mill still can't reach
    m = make_25d(m, flat_exempt, log=log)
    m = relieve(m, flat_exempt.buffer(0.1) if flat_exempt is not None else None, log=log)
    s = mesh_to_solid(m)
    log(f'mesh to solid: {len(s.Faces())} faces, volume change {s.Volume() - m.volume:.8f} mm^3')
    return s


def solid_keep_out(shape, grow, zmin=-1e9, zmax=1e9):
    """(z0, z1) -> the shape's sections in that height slice grown by `grow` (for keeping a fill
    clear of another part, or out of a keep-out)."""
    m = shape if not hasattr(shape, 'wrapped') else mesh_of(shape)
    def f(a, b):
        if b < zmin or a > zmax:
            return sg.Polygon()
        # also `grow` above and below the slice: a fill must keep clear diagonally too
        hs = [h for h in (a - grow, a + EPS, (a + b) / 2, b - EPS, b + grow) if m.bounds[0, 2] < h < m.bounds[1, 2]]
        g = U([section(m, h) for h in hs])
        return g.buffer(grow, quad_segs=QS) if not g.is_empty else g
    return f


# ------------------------------------------------------------------ flat end mill only (2.5D)
def flatten_slopes(shape, exempt=None, step=0.5, narrow=1.0, log=print):
    """Prisms of material to remove so that every face is either vertical or flat (no ball-nose
    end mill): in each height band where the part slopes, only the material present at every
    height of the band stays. A steep slope (moving less than `narrow` sideways over the band)
    becomes one vertical wall at its outer size; a shallow one becomes flat-floored steps of
    height `step`. Only removes material. exempt: region left as it is (countersinks)."""
    m = shape if not hasattr(shape, 'wrapped') else mesh_of(shape)
    L = levels(m)
    cuts, vol = [], 0.0
    for a, b in zip(L[:-1], L[1:]):
        s0, s1, sm = section(m, a + EPS), section(m, b - EPS), section(m, (a + b) / 2)
        if same(s0, s1) and same(s0, sm):
            continue
        wide = not s0.symmetric_difference(s1).buffer(-narrow / 2, quad_segs=2).is_empty
        n = max(1, int(np.ceil((b - a) / step))) if wide else 1
        ts = np.linspace(a, b, n + 1)
        for lo, hi in zip(ts[:-1], ts[1:]):
            hs = np.linspace(lo + EPS, hi - EPS, max(3, int(np.ceil((hi - lo) / 0.05)) + 1))
            ss = [section(m, h) for h in hs]
            core = ss[0]
            for x in ss[1:]:
                core = core.intersection(x)
            g = U(ss).difference(core)
            if exempt is not None:
                g = g.difference(exempt)
            g = clean_poly(g, 0.002, 1e-3)
            for p in pieces(g):
                # reach 0.02 past the slice's edges in plan so the cut leaves no hairline skin
                q = p.buffer(0.02, quad_segs=2).difference(exempt) if exempt is not None else p.buffer(0.02, quad_segs=2)
                for r in pieces(q):
                    cuts.append(prism(r, lo, hi))
                vol += p.area * (hi - lo)
    log(f'2.5D: sloped faces turned into vertical walls / flat steps, {len(cuts)} prisms, ~{vol:.1f} mm^3 removed')
    return cuts


def planar_mesh(shape):
    """Triangulate polygonal faces exactly, preserving the B-rep's vertex identities."""
    import trimesh, mapbox_earcut as earcut
    from OCP.BRepTools import BRepTools_WireExplorer
    from OCP.BRep import BRep_Tool
    V, F, idx = [], [], {}
    for f in shape.Faces():
        if f.geomType() != 'PLANE' or any(e.geomType() != 'LINE' for e in f.Edges()):
            return None
        n = np.array(f.normalAt().toTuple())
        a = np.cross(n, [1, 0, 0] if abs(n[0]) < 0.9 else [0, 1, 0]); a /= np.linalg.norm(a); b = np.cross(n, a)
        rings, ids = [], []
        for w in [f.outerWire()] + f.innerWires():
            ex = BRepTools_WireExplorer(w.wrapped)
            ring = []
            while ex.More():
                vertex = cq.Vertex(ex.CurrentVertex())
                if vertex not in idx:
                    p = BRep_Tool.Pnt_s(vertex.wrapped)
                    idx[vertex] = len(V); V.append([p.X(), p.Y(), p.Z()])
                i = idx[vertex]; ids.append(i); ring.append(V[i])
                ex.Next()
            rings.append(np.array(ring))
        P = np.vstack(rings); o = P[0]
        uv = np.c_[(P - o) @ a, (P - o) @ b]
        ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
        tri = earcut.triangulate_float64(uv, ends).reshape(-1, 3)
        area = 0.0
        for t in tri:
            cross = np.cross(P[t[1]] - P[t[0]], P[t[2]] - P[t[0]])
            magnitude = np.linalg.norm(cross)
            area += magnitude / 2
            if magnitude < 1e-14:
                continue
            tr = [ids[i] for i in t]
            if np.dot(cross, n) < 0:
                tr = tr[::-1]
            F.append(tr)
        assert abs(area - f.Area()) < 1e-6 + 1e-8 * area, ('face triangulation area', area, f.Area())
    m = trimesh.Trimesh(np.array(V), np.array(F), process=False)
    assert abs(m.volume - shape.Volume()) < 0.005, ('planar mesh volume', m.volume, shape.Volume())
    return m


def make_25d(m, exempt=None, shrink=0.005, dz=0.25, log=print):
    """Rebuild a mesh as stacked vertical prisms, so every face is vertical or horizontal: per
    height band between horizontal faces, the material present at every height of the band
    (sections every `dz` and at both ends), shrunk by `shrink` so it never exceeds the original
    even between samples. Removal only. Inside `exempt` (countersinks) the original is kept."""
    import trimesh
    L = levels(m)
    prisms, kept = [], 0.0
    for a, b in zip(L[:-1], L[1:]):
        hs = np.unique(np.r_[a + EPS, np.arange(a + dz, b - EPS, dz), b - EPS])
        core = None
        for h in hs:
            g = section(m, h)
            core = g if core is None else core.intersection(g)
            if core.is_empty:
                break
        if core is None or core.is_empty:
            continue
        core = core.buffer(-shrink, quad_segs=2)
        if exempt is not None:
            core = core.difference(exempt)
        for p in pieces(clean_poly(core, 1e-4, 1e-5)):
            t = trimesh.creation.extrude_polygon(p, b - a)
            t.apply_translation([0, 0, a])
            prisms.append(t)
            kept += p.area * (b - a)
    out = mf_bool(prisms[0], prisms[1:], 'union')
    if exempt is not None and not exempt.is_empty:
        lo, hi = m.bounds[0, 2] - 1, m.bounds[1, 2] + 1
        cyl = []
        for p in pieces(exempt):
            t = trimesh.creation.extrude_polygon(p, hi - lo); t.apply_translation([0, 0, lo]); cyl.append(t)
        out = mf_bool(out, [mf_bool(m, cyl, 'intersection')], 'union')
    out = max(out.split(only_watertight=False), key=lambda c: c.volume)
    log(f'2.5D rebuild: {len(L) - 1} height bands, {m.volume - out.volume:.2f} mm^3 of tilted wall removed')
    return out


def relieve(m, exempt=None, r=R_CUT, rounds=3, log=print):
    """Removal-only reliefs where a Ø2r flat end mill still can't reach (inside corners left by
    the 2.5D rebuild, small undercuts): at each such spot, the local void is opened with
    dogbones (open_superset) and cut from the spot's floor up (or from its roof down)."""
    import trimesh, machinable
    from scipy import ndimage as nd
    step = machinable.STEP
    for rnd in range(rounds):
        lo_b, hi_b = m.bounds
        xs = np.arange(lo_b[0] - 2.5, hi_b[0] + 2.5, step) + 1.234e-4
        ys = np.arange(lo_b[1] - 2.5, hi_b[1] + 2.5, step) + 2.345e-4
        zt, zb, length, cnt = machinable.projected_columns(m, xs, ys)
        # exactly the checker's test (machinable.analyse): Ø2 tool, 0.03 mm reach tolerance
        top, bot, top_m, bot_m, lo, hi = machinable.machined(zt, zb, 1.0, step)
        full = ~np.isnan(zt)
        under = full & ((zt - zb) - length > 0.05)
        ex_top = full & (top_m > top + 0.03)
        ex_bot = full & (bot_m < bot - 0.03)
        X, Y = np.meshgrid(xs, ys)
        if exempt is not None:
            from shapely import contains_xy
            ex_cells = contains_xy(exempt, X, Y)
            under &= ~ex_cells; ex_top &= ~ex_cells; ex_bot &= ~ex_cells
        ex_top = nd.binary_opening(ex_top, structure=np.ones((2, 2)))
        ex_bot = nd.binary_opening(ex_bot, structure=np.ones((2, 2)))
        under = nd.binary_opening(under, structure=np.ones((2, 2)))
        lab, n = nd.label(ex_top | ex_bot | under)
        if n > 40:   # a handful of corners is expected; many more means something else is wrong
            log(f'reliefs: {n} spots flagged - too many, left as they are for review')
            return m
        cuts = []
        for i in range(1, n + 1):
            sel = lab == i
            if sel.sum() * step ** 2 < 0.01:
                continue
            spot = unary_union([sg.Point(x, y).buffer(step * 0.75, quad_segs=2) for x, y in zip(X[sel], Y[sel])])
            win = spot.buffer(3.0)
            if ex_top[sel].any() or under[sel].any():
                # cut from above: down to the deepest floor under the spot
                if under[sel].any():
                    zf = cavity_floor(m, spot.centroid, zt[sel].max(), zb[sel].min())
                else:
                    zf = float(np.nanmin(zt[sel]))
                void = win.difference(section(m, zf + 0.02))
                fp = unary_union([g for g in pieces(void) if g.intersects(spot)])
                if fp.is_empty:
                    continue
                try:
                    o = open_superset(unary_union([fp, spot.intersection(void.buffer(0.1))]).intersection(win))
                except RuntimeError:
                    log(f'reliefs: no relief found at {spot.centroid.x:.2f},{spot.centroid.y:.2f}')
                    continue
                for p in pieces(o):
                    t = trimesh.creation.extrude_polygon(p, hi_b[2] + 1 - zf); t.apply_translation([0, 0, zf]); cuts.append(t)
            else:
                zf = float(np.nanmax(zb[sel]))
                void = win.difference(section(m, zf - 0.02))
                fp = unary_union([g for g in pieces(void) if g.intersects(spot)])
                if fp.is_empty:
                    continue
                try:
                    o = open_superset(unary_union([fp, spot.intersection(void.buffer(0.1))]).intersection(win))
                except RuntimeError:
                    log(f'reliefs: no relief found at {spot.centroid.x:.2f},{spot.centroid.y:.2f}')
                    continue
                for p in pieces(o):
                    t = trimesh.creation.extrude_polygon(p, zf - (lo_b[2] - 1)); t.apply_translation([0, 0, lo_b[2] - 1]); cuts.append(t)
        if not cuts:
            return m
        v0 = m.volume
        m = mf_bool(m, cuts, 'difference')
        m = max(m.split(only_watertight=False), key=lambda c: c.volume)
        log(f'reliefs (round {rnd + 1}): {len(cuts)} cuts at {n} spots the Ø2 mill could not reach, {v0 - m.volume:.2f} mm^3 removed')
    return m


def cavity_floor(m, p, ztop, zbot, dz=0.05):
    """Lowest bottom of the void just under the topmost material at point p (an undercut)."""
    zs = np.arange(ztop - dz, zbot, -dz)
    inside = [section(m, z).contains(p) for z in zs]
    k = next((i for i, v in enumerate(inside) if not v), None)       # first void under the roof
    if k is None:
        return zbot
    j = next((i for i in range(k, len(zs)) if inside[i]), len(zs) - 1)  # material again: the floor
    return float(zs[j])
