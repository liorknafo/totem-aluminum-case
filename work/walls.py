"""Thin walls seen in plan: in every band between the part's flat faces, metal narrower than W mm
(what an opening by a W/2 disc removes from the band's section). With thin.py (thin layers in z)
this finds every place where the metal is thinner than W."""
import sys
sys.path.insert(0, '.')
from geo import *
import shapely
from shapely.ops import unary_union
import mill

W_MIN = 0.8


def thin_walls(m, w=W_MIN, min_area=0.005, min_h=0.02, step=0.02):
    """[(piece, z0, z1, width)] for every bit of metal narrower than w, band by band: what an
    opening by a w/2 disc removes from the band's section, less the bits it rounds off plain
    corners (within 0.3 mm of what the opening keeps); width is twice the largest distance from
    the piece to the section's outline (the thickness of the wall there)."""
    L = mill.levels(m)
    out = []
    for a, b in zip(L[:-1], L[1:]):
        if b - a < min_h:
            continue
        sec = mill.section(m, (a + b) / 2)
        if sec.is_empty:
            continue
        opened = sec.buffer(-w / 2, quad_segs=16).buffer(w / 2 + 1e-4, quad_segs=16)
        thin = sec.difference(opened).difference(opened.buffer(0.3 * w))
        for g in mill.pieces(thin):
            if g.area < min_area:
                continue
            x0, y0, x1, y1 = g.bounds
            X, Y = np.meshgrid(np.arange(x0, x1 + step, step), np.arange(y0, y1 + step, step))
            pts = shapely.points(X.ravel(), Y.ravel())
            pts = pts[shapely.contains(g, pts)]
            if not len(pts):
                pts = [g.representative_point()]
            width = 2 * float(np.max(shapely.distance(sec.boundary, pts)))
            out.append((g, a, b, min(width, w)))
    return out


def grouped(tw):
    """The same wall seen in several bands, as one: (piece union, z0, z1, thinnest width)."""
    out = []
    for g, a, b, t in sorted(tw, key=lambda r: r[1]):
        for o in out:
            if o[0].buffer(0.05).intersects(g) and o[2] >= a - 1e-6:
                o[0] = o[0].union(g); o[2] = max(o[2], b); o[3] = min(o[3], t)
                break
        else:
            out.append([g, a, b, t])
    return out


if __name__ == '__main__':
    # walls.py PART.step [W]: list the walls thinner than W (default 0.8 mm)
    s = load(sys.argv[1])
    w = float(sys.argv[2]) if len(sys.argv) > 2 else W_MIN
    rows = grouped(thin_walls(mill.mesh_of(s, 0.002), w))
    print(f'{sys.argv[1]}: {len(rows)} walls thinner than {w} mm')
    for g, a, b, t in sorted(rows, key=lambda r: r[3]):
        c = g.representative_point()
        print(f'  {t:.2f} mm at ({c.x:7.2f},{c.y:7.2f}) z {a:7.3f}..{b:7.3f}, {g.area:6.3f} mm^2 in plan, '
              f'{g.bounds[2] - g.bounds[0]:.2f} x {g.bounds[3] - g.bounds[1]:.2f}')
