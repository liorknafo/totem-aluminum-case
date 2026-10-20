import sys; sys.path.insert(0, '.')
from geo import *
import trimesh, shapely.geometry as sg
from shapely.ops import unary_union
side = sys.argv[1]
def mesh(p):
    s = load(p); v, f = s.tessellate(0.01, 0.1)
    return s, trimesh.Trimesh(np.array([q.toTuple() for q in v]), np.array(f))
for name, p in [('orig', f'orig/TOTEM_tenting_live_bottom_{side}.step'), ('new', f'../outputs/TOTEM_alu_bottom_{side}.step')]:
    s, m = mesh(p)
    bb = s.BoundingBox(); step = 0.25
    xs = np.arange(bb.xmin, bb.xmax, step); ys = np.arange(bb.ymin, bb.ymax, step)
    X, Y = np.meshgrid(xs, ys); P = np.c_[X.ravel(), Y.ravel()]
    up = m.ray.intersects_location(np.c_[P, np.full(len(P), -30.0)], np.tile([0, 0, 1.0], (len(P), 1)), multiple_hits=False)
    dn = m.ray.intersects_location(np.c_[P, np.full(len(P), 30.0)], np.tile([0, 0, -1.0], (len(P), 1)), multiple_hits=False)
    hit = np.zeros(len(P), bool); hit[up[1]] = True
    U = np.full(len(P), np.nan); U[up[1]] = up[0][:, 2]
    T = np.full(len(P), np.nan); T[dn[1]] = dn[0][:, 2]
    outline = sg.Polygon(sg.MultiPoint(P[hit]).convex_hull.exterior)  # rough
    # through = no material on a vertical line, inside the solid's footprint
    foot = unary_union([sg.box(x - step/2, y - step/2, x + step/2, y + step/2) for x, y in P[hit]]).buffer(0)
    holes = []
    for g in (foot.geoms if foot.geom_type == 'MultiPolygon' else [foot]):
        holes += [sg.Polygon(r) for r in g.interiors]
    holes = [h for h in holes if h.area > 0.3]
    print(name, side, 'through-openings:', len(holes))
    for h in sorted(holes, key=lambda h: (-h.centroid.y, h.centroid.x)):
        c = h.centroid; b = h.bounds
        # roof height under the recess around the opening and pocket floor above
        ring = h.buffer(0.6).difference(h.buffer(0.1))
        sel = [i for i, (x, y) in enumerate(P) if ring.contains(sg.Point(x, y))]
        print(f'  ({c.x:7.2f},{c.y:8.2f}) {b[2]-b[0]:5.2f}x{b[3]-b[1]:5.2f} area {h.area:5.1f}  underside around: {np.nanmin(U[sel]):.2f}..{np.nanmax(U[sel]):.2f}')
