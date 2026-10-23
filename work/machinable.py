"""3-axis machinability with a flat end mill, cut from above and from below (two setups).

For every column (x, y) on a fine grid the part must be one interval [zb, zt] (no undercut).
From above, a flat end mill of radius R can lower its tip at p down to the highest material
under its disc, so the surface it leaves is the grey-level closing of zt by a disc of radius R;
from below, likewise for zb. Wherever the part's surface lies deeper than what the tool can
reach (uncut corners, slots narrower than 2R, ...) the machined part keeps extra material.

Usage: machinable.py PART.step [DIAMETER] [--png out.png] [--drill L|R] [--json out.json]
Prints the extra material the end mill would leave and any undercut columns. --drill: the screw
holes of that half are drilled and countersunk (Ø2.0/2.16 necks, 90° countersinks up to Ø3.5 in
the top and Ø4.25 in the bottom: a countersink or chamfer tool), so they are not counted.
"""
import sys
sys.path.insert(0, '.')
from geo import *
import trimesh
from scipy import ndimage

STEP = 0.05


def disc(r, step=STEP):
    n = int(np.floor(r / step))
    yy, xx = np.mgrid[-n:n + 1, -n:n + 1]
    return (xx ** 2 + yy ** 2) * step ** 2 <= r ** 2


def projected_columns(m, xs, ys):
    """Intersect vertical columns with every triangle, including arbitrarily close surfaces."""
    sh = (len(ys), len(xs))
    zt = np.full(sh, -np.inf); zb = np.full(sh, np.inf)
    length = np.zeros(sh); count = np.zeros(sh, int); winding = np.zeros(sh, int)
    for tri, normal in zip(m.triangles, m.face_normals):
        if abs(normal[2]) < 1e-10:
            continue
        lo = tri[:, :2].min(axis=0); hi = tri[:, :2].max(axis=0)
        x0, x1 = np.searchsorted(xs, lo[0]), np.searchsorted(xs, hi[0], side='right')
        y0, y1 = np.searchsorted(ys, lo[1]), np.searchsorted(ys, hi[1], side='right')
        if x0 == x1 or y0 == y1:
            continue
        t = tri if normal[2] > 0 else tri[::-1]
        X, Y = np.meshgrid(xs[x0:x1], ys[y0:y1])
        inside = np.ones(X.shape, bool)
        for a, b in zip(t, np.roll(t, -1, axis=0)):
            dx, dy = b[:2] - a[:2]
            cross = dx * (Y - a[1]) - dy * (X - a[0])
            # Half-open edges count a shared diagonal once, independent of triangulation.
            inside &= (cross > 0) | ((cross == 0) & ((dy > 0) or (dy == 0 and dx < 0)))
        z = tri[0, 2] - (normal[0] * (X - tri[0, 0]) + normal[1] * (Y - tri[0, 1])) / normal[2]
        area = np.s_[y0:y1, x0:x1]
        zt[area] = np.maximum(zt[area], np.where(inside, z, -np.inf))
        zb[area] = np.minimum(zb[area], np.where(inside, z, np.inf))
        sign = 1 if normal[2] > 0 else -1
        length[area] += np.where(inside, sign * z, 0)
        count[area] += inside
        winding[area] += inside * sign
    bad = winding != 0
    if bad.any():
        yy, xx = np.where(bad)
        raise AssertionError(('unbalanced surface crossings', int(bad.sum()),
                              list(zip(xs[xx[:5]], ys[yy[:5]]))))
    full = count > 0
    assert np.all(length[full] >= -1e-6) and np.all(length[full] <= (zt - zb)[full] + 1e-6), 'overlapping surface crossings'
    zt[count == 0] = np.nan; zb[count == 0] = np.nan
    return zt, zb, length, count


def surface_mesh(shape):
    """Exact planar triangles, or a checked closed tessellation for curved faces."""
    import mill
    m = mill.planar_mesh(shape)
    return mill.closed_mesh(shape) if m is None else m


def columns(shape, step=STEP, margin=2.5, mesh=None):
    """zt, zb (nan where empty), material length per column and the grid."""
    m = mesh if mesh is not None else surface_mesh(shape)
    bb = shape.BoundingBox()
    xs = np.arange(bb.xmin - margin, bb.xmax + margin, step) + 1.234e-4
    ys = np.arange(bb.ymin - margin, bb.ymax + margin, step) + 2.345e-4
    zt, zb, length, count = projected_columns(m, xs, ys)
    return zt, zb, length, count, xs, ys, bb


def machined(zt, zb, R, step=STEP, tol=None):
    """Surfaces a flat end mill of radius R leaves from above (zt') and from below (zb')."""
    fp = disc(R - (tol if tol is not None else 0.6 * step), step)
    lo = np.nanmin(zb) - 10
    hi = np.nanmax(zt) + 10
    top = np.where(np.isnan(zt), lo, zt)
    bot = np.where(np.isnan(zb), hi, zb)
    # tip of the tool centred at p stops on the highest material under its disc; the surface left
    # at q is the lowest tip among tools covering q
    top_m = ndimage.minimum_filter(ndimage.maximum_filter(top, footprint=fp, mode='nearest'), footprint=fp, mode='nearest')
    bot_m = ndimage.maximum_filter(ndimage.minimum_filter(bot, footprint=fp, mode='nearest'), footprint=fp, mode='nearest')
    return top, bot, top_m, bot_m, lo, hi


def sloped_area(shape, drill=()):
    """Tilted surface area using B-rep normals, not normals of curved-face tessellation."""
    import shapely.geometry as sg
    from shapely.ops import unary_union
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    exempt = unary_union([sg.Point(x, y).buffer(r, quad_segs=128) for x, y, r in drill])
    area = 0.0
    for face in shape.Faces():
        kind = face.geomType()
        if kind == 'PLANE':
            nz = abs(face.normalAt().z)
            if nz <= 1e-6 or nz >= 1 - 1e-6:
                continue
        else:
            surface = BRepAdaptor_Surface(face.wrapped)
            if kind == 'CYLINDER' and abs(surface.Cylinder().Axis().Direction().Z()) > 1 - 1e-12:
                continue
            if kind == 'EXTRUSION' and abs(surface.Direction().Z()) > 1 - 1e-12:
                continue
            if kind == 'BSPLINE':
                spline = surface.BSpline()
                poles = np.array([[spline.Pole(i, j).Coord() for j in range(1, spline.NbVPoles() + 1)]
                                  for i in range(1, spline.NbUPoles() + 1)])
                weights = np.array([[spline.Weight(i, j) for j in range(1, spline.NbVPoles() + 1)]
                                    for i in range(1, spline.NbUPoles() + 1)])
                separable = np.allclose(weights, weights[:, :1] * weights[:1, :] / weights[0, 0], rtol=1e-12, atol=1e-12)
                if separable and any(np.max(np.abs(np.diff(poles[:, :, :2], axis=k))) < 1e-9 for k in (0, 1)):
                    continue
        bb = face.BoundingBox()
        near_drill = any(max(bb.xmin - x, 0, x - bb.xmax) ** 2 +
                         max(bb.ymin - y, 0, y - bb.ymax) ** 2 <= r ** 2 for x, y, r in drill)
        if kind == 'PLANE' and not near_drill:
            area += face.Area()
            continue
        vertices, faces = face.tessellate(0.001, 0.05)
        triangles = np.array([p.toTuple() for p in vertices])[np.asarray(faces)]
        for triangle in triangles:
            if kind != 'PLANE':
                nz = abs(face.normalAt(cq.Vector(*triangle.mean(axis=0))).z)
                if nz <= 1e-6 or nz >= 1 - 1e-6:
                    continue
            a = np.linalg.norm(np.cross(triangle[1] - triangle[0], triangle[2] - triangle[0])) / 2
            if near_drill:
                if any(np.all(np.sum((triangle[:, :2] - [x, y]) ** 2, axis=1) <= r ** 2) for x, y, r in drill):
                    continue
                footprint = sg.Polygon(triangle[:, :2])
                if footprint.area > 0:
                    a *= footprint.difference(exempt).area / footprint.area
            area += a
    return float(area)


def mesh_spots(m, R=1.0, drill=(), step=STEP, margin=2.5):
    """The checker's spots (see analyse) for a closed mesh: [dict(x, y, w, h, area, kind, ztop,
    cells)], cells the (x, y) points of the spot."""
    lo_b, hi_b = m.bounds
    xs = np.arange(lo_b[0] - margin, hi_b[0] + margin, step) + 1.234e-4
    ys = np.arange(lo_b[1] - margin, hi_b[1] + margin, step) + 2.345e-4
    zt, zb, L, cnt = projected_columns(m, xs, ys)
    out, _, sel, _ = find_spots(zt, zb, L, xs, ys, R, drill)
    X, Y = np.meshgrid(xs, ys)
    for o, s in zip(out, sel):
        o['cells'] = np.c_[X[s], Y[s]]
    return out


def find_spots(zt, zb, L, xs, ys, R, drill=()):
    """Spots a flat end mill of radius R can't cut from above or below (3D toolpaths: grey-level
    closing of the height field by its disc), and undercut columns. -> (spots, undercut cells,
    per-spot cell masks)."""
    import scipy.ndimage as nd
    top, bot, top_m, bot_m, lo, hi = machined(zt, zb, R)
    full = ~np.isnan(zt)
    # undercut: the column holds less material than zt - zb (a void inside it)
    under = full & ((zt - zb) - L > 0.05)
    # extra material: where the mill can't get down to the model's surface
    ex_top = np.where(top_m > top + 1e-6, top_m - np.maximum(top, lo), 0)
    ex_bot = np.where(bot_m < bot - 1e-6, np.minimum(bot, hi) - bot_m, 0)
    # a column that is empty in the model but the tool can't empty from either side
    empty_left = ~full & (top_m > lo + 1e-6) & (bot_m < hi - 1e-6) & (top_m > bot_m)
    ex = np.where(full, np.maximum(ex_top, ex_bot), np.where(empty_left, np.inf, 0))
    # An empty column may be cleared by either setup; lo/hi are padding, not cutting depths.
    ex_top = np.where(full, ex_top, 0)
    ex_bot = np.where(full, ex_bot, 0)
    bad = ex > 0.03   # below a typical CAM tolerance; curved overhangs are filled in 0.025 mm slices
    X, Y = np.meshgrid(xs, ys)
    for x, y, r in drill:
        drilled = (X - x) ** 2 + (Y - y) ** 2 <= r ** 2
        bad &= ~drilled
        under &= ~drilled
    # drop single-cell grid noise along walls (rays grazing a wall, facets of the mesh-derived
    # bottoms): a spot must be at least 2 cells (0.1 mm) across both ways
    bad = nd.binary_opening(bad, structure=np.ones((2, 2)))
    under = nd.binary_opening(under, structure=np.ones((2, 2)))
    lab, n = nd.label(bad | under)
    out, sels = [], []
    for i in range(1, n + 1):
        sel = lab == i
        a = sel.sum() * STEP ** 2
        if a < 0.01:
            continue
        sels.append(sel)
        yy, xx = np.where(sel)
        e = ex[sel]
        kind = []
        if under[sel].any():
            kind.append('undercut')
        if empty_left[sel].any():
            kind.append('opening <2R')
        if ex_top[sel].max() > 0.03:
            kind.append(f'from top {ex_top[sel].max():.2f}')
        if ex_bot[sel].max() > 0.03:
            kind.append(f'from below {ex_bot[sel].max():.2f}')
        out.append(dict(x=round(xs[xx].mean(), 2), y=round(ys[yy].mean(), 2), w=round(np.ptp(xs[xx]) + STEP, 2),
                        h=round(np.ptp(ys[yy]) + STEP, 2), area=round(a, 3), kind=', '.join(kind),
                        ztop=round(float(np.nanmax(np.where(sel & full, zt, np.nan))) if (sel & full).any() else 0, 2)))
    return out, under, sels, (full, bad)


def analyse(path, R=1.0, png=None, label=None, quiet=False, drill=(), json_path=None):
    s = load(path) if isinstance(path, str) else path
    assert s.isValid() and len(s.Solids()) == 1, "checker requires one valid solid"
    mesh = surface_mesh(s)
    zt, zb, L, cnt, xs, ys, bb = columns(s, mesh=mesh)
    out, under, _, (full, bad) = find_spots(zt, zb, L, xs, ys, R, drill)
    # Sloped and curved faces (3D toolpaths with the flat end mill): reported, not a failure; the
    # spot test above is what the flat end mill can cut on 3D toolpaths.
    sloped = sloped_area(s, drill)
    if json_path:
        import json
        report = dict(spots=out, undercut_columns=int(under.sum()), sloped_area=sloped,
                      diameter=2 * R, grid=STEP, reach_tolerance=0.03, undercut_tolerance=0.05,
                      slope_normal_tolerance=1e-6, slope_normals='B-rep')
        with open(json_path, 'w') as f:
            json.dump(report, f, indent=2)
            f.write('\n')
    if not quiet:
        print(f'{label or path}: tool Ø{2 * R:g}: {len(out)} spots the mill cannot cut, undercut columns: {int(under.sum())}, '
              f'3D surfaces outside the countersinks (3D toolpaths): {sloped:.2f} mm²')
        for o in sorted(out, key=lambda o: -o['area']):
            print(f"  ({o['x']:7.2f},{o['y']:8.2f}) {o['w']:5.2f}x{o['h']:5.2f} area {o['area']:6.3f}  {o['kind']}")
    if png:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(16, 12))
        base = np.where(full, zt, np.nan)
        ax.imshow(base, origin='lower', extent=[xs[0], xs[-1], ys[0], ys[-1]], cmap='Greys', alpha=0.6)
        ov = np.where(bad | under, 1.0, np.nan)
        ax.imshow(ov, origin='lower', extent=[xs[0], xs[-1], ys[0], ys[-1]], cmap='autumn', vmin=0, vmax=1)
        for o in out:
            ax.add_patch(plt.Circle((o['x'], o['y']), max(o['w'], o['h']) / 2 + 1.5, fill=False, color='red', lw=1.5))
        ax.set_title(f'{label or path}: red = cannot be cut with a Ø{2 * R:g} flat end mill from above or below')
        ax.set_aspect('equal'); plt.tight_layout(); plt.savefig(png, dpi=60); plt.close(fig)
    return out, int(under.sum())


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('part')
    parser.add_argument('diameter', type=float, nargs='?', default=2.0)
    parser.add_argument('--png')
    parser.add_argument('--drill', choices=['L', 'R'])
    parser.add_argument('--json')
    args = parser.parse_args()
    drill = ()
    if args.drill:
        from build import SCREWS
        drill = [(x, y, 2.4) for x, y in SCREWS[args.drill]]
    analyse(args.part, args.diameter / 2, args.png, drill=drill, json_path=args.json)
