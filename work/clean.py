"""Rebuild a 2.5D part as clean CAD: every face exactly horizontal or vertical, walls drawn with
lines and circular arcs, screw holes as exact drilled holes.

A part a 3-axis mill cuts in two setups (no undercuts) is, at every (x, y), one column of material
from zb(x, y) to zt(x, y), with zb and zt constant on regions of the plane. The regions are found
from the part's horizontal sections between its flat faces (snapped together so a wall shared by
several height bands is one wall), the hairline slivers left between near-identical walls are
merged into a neighbour (to the side with less material when there is one), each boundary chain
between two regions is fitted once with lines and arcs, and every region becomes one prism from zb
to zt; the prisms are fused and their coplanar faces merged. The screw holes are filled first (a
disc around each screw takes the column of its surroundings) and cut afterwards as exact
cylinders and 82° cones."""
import sys, time
sys.path.insert(0, '.')
from geo import *
import shapely, shapely.ops, shapely.geometry as sg
from shapely.ops import unary_union, polygonize
from shapely.strtree import STRtree
import mill, fit2d

SNAP = 0.003      # band outlines within this of each other are snapped together
SLIVER = 0.005    # regions narrower than 2x this are merged into a neighbour
SMALL_AREA = 0.05  # regions smaller than this (mm^2) too: micro-ledges, not features
SMALL_W = 0.02    # ... or narrower than 2x this
FIT_TOL = 0.002   # lines and arcs stay this close to the region outlines
DISC_R = 2.3      # screw holes: inside this radius the column is filled, then drilled exactly
OPEN_MAX = 5.0    # through-openings smaller than this (mm^2) are accidents and get closed
SKIN = 0.8        # thinnest floor between a pocket and the underside
TAN41 = np.tan(np.radians(41.0))   # the build's (the originals') 82° countersinks: semi-angle 41°
# Screw holes (aluminum: the M2 threads are tapped in the bottom, no standoffs). Top: 90° metric
# countersink, Ø4.30 at the top face (TOP_FACE), and a Ø2.4 pass-through hole (TOP_NECK) down
# through the boss. Bottom: a blind Ø1.6 tap-drill hole (BOT_TAP) from the boss top down to
# BOT_DRILL (0.8 mm over the leg recess under the 131.2 / 176.8 screws), tapped M2 x 0.4 5.5 mm
# deep (an M2 x 16 countersunk screw engages 5.2 mm); the underside stays solid.
TOP_FACE, TOP_CS_R, TOP_NECK = 10.5, 2.15, 1.2
BOT_TAP, BOT_DRILL = 0.8, -6.5


T0 = time.monotonic()


EVENTS = []   # every log line of the current part (written to clean_<kind>_<side>.log by --all)


def log(*a):
    EVENTS.append(' '.join(str(x) for x in a))
    print(f'[{time.monotonic() - T0:7.1f}s]', *a, flush=True)


# ------------------------------------------------------------------ regions
def band_sections(m):
    L = mill.levels(m)
    S = [mill.section(m, (a + b) / 2) for a, b in zip(L[:-1], L[1:])]
    return L, S


def hole_radius(kind, z):
    """Radius of the screw hole's void at height z (see hole_profiles); 0 where there is none."""
    if kind == 'top':
        return max(TOP_NECK, TOP_CS_R + (z - TOP_FACE))   # 90°: the cone's radius grows 1:1
    return BOT_TAP if z > BOT_DRILL else 0.0


def build_hole_radius(kind, z):
    """The holes as the build (and the originals) has them: top Ø3.2 standoff bore to 9.0, Ø2.0
    neck, 82° countersink (r 1.575 at 9.8385); bottom Ø4.30 counterbore up to -2.0, 82°
    countersink (r 1.575 at -1.3385), Ø2.0 neck."""
    if kind == 'top':
        return 1.6 if z < 9.0 else max(1.0, 1.575 + (z - 9.8385) * TAN41)
    return 2.15 if z < -2.0 else max(1.0, 1.575 + (-1.3385 - z) * TAN41)


def plug_screws(S, L, screws, kind):
    """Fill each screw hole in every band where metal (mostly) surrounds it, a hair over the hole's
    largest radius in the band (as built or as it is cut now, whichever is larger): the hole and
    its countersink are cut again exactly at the end,
    through the whole part, so what was there is restored. Metal under 0.2 mm thick right at the
    hole (a pocket that nearly touches it, a ring a few hundredths wide) goes: removal only."""
    out, discs = [], []
    for k, g in enumerate(S):
        a, b = L[k], L[k + 1]
        r = max(max(hole_radius(kind, z), build_hole_radius(kind, z)) for z in np.linspace(a, b, 9))
        for x, y in screws:
            d = sg.Point(x, y).buffer(r, quad_segs=64)
            ring = d.buffer(0.1, quad_segs=64).difference(d)
            if g.intersection(ring).area / ring.area <= 0.5:
                continue
            M = g.intersection(d.buffer(0.5, quad_segs=64)).difference(d)
            sliver = M.difference(M.buffer(-0.1, quad_segs=16).buffer(0.1, quad_segs=16)).intersection(
                d.buffer(0.2, quad_segs=64))
            if sliver.area > 1e-4:
                g = g.difference(sliver.buffer(0.01))
            if g.intersection(ring).area / ring.area > 0.5:   # still a hole in metal: plug it
                dp = sg.Point(x, y).buffer(r + 0.01, quad_segs=64)
                g = g.union(dp)
                discs.append(dp)
        out.append(mill.tidy(g))
    return out, discs


def snap_bands(S, ref_geoms=(), d=SNAP):
    """Snap each band's outline onto the vertices of the bands already done (largest first)."""
    ref = shapely.MultiPoint(np.vstack([shapely.get_coordinates(g.boundary) for g in ref_geoms])) if ref_geoms else None
    out = [None] * len(S)
    for k in sorted(range(len(S)), key=lambda k: -S[k].area):
        g = S[k]
        if ref is not None and not g.is_empty:
            g = shapely.make_valid(shapely.snap(g, ref, d)).buffer(0)
        out[k] = g
        if not g.is_empty:
            pts = shapely.MultiPoint(shapely.get_coordinates(g.boundary))
            ref = pts if ref is None else shapely.union(ref, pts)
    return out


def overlay(S):
    """Faces of the arrangement of all band outlines, each with its column (first, last band) or
    None (no material)."""
    faces = list(polygonize(unary_union([g.boundary for g in S if not g.is_empty])))
    rp = np.array([f.representative_point().coords[0] for f in faces])
    M = np.array([shapely.contains_xy(g, rp[:, 0], rp[:, 1]) for g in S]).T
    lab = []
    for row in M:
        idx = np.where(row)[0]
        lab.append((int(idx[0]), int(idx[-1])) if len(idx) else None)
    return faces, lab, M


AIR = (-1, -1)    # label of a speck given to the air around the part (no material)


def merge_small(polys, labels, is_small, L, prefer_less=True, log=log, what='slivers', air=None):
    """Give each small polygon the label of a neighbour: preferably one whose column lies inside
    its own (removing material), then the one sharing the longest border. Repeats until stable."""
    tree = STRtree(polys)
    nbrs = []
    for i, p in enumerate(polys):
        cand = [j for j in tree.query(p) if j != i]
        sh = []
        for j in cand:
            l = p.boundary.intersection(polys[j].boundary).length
            if l > 1e-9:
                sh.append((j, l))
        if air is not None:   # the outline of the whole part: a speck lying along it may go to the
            l = p.boundary.intersection(air).length       # air (not one that cuts into a wall)
            if l > 0.4 * p.length:
                sh.append((-1, l))
        nbrs.append(sh)
    labels = list(labels) + [AIR]   # index -1: the air
    small = np.array(is_small)
    changed = 0
    def thickness(i):   # thinnest columns first: a staircase then goes the same way everywhere
        l = labels[i]
        return 0.0 if l is None or l == AIR or l[0] < 0 or l[1] + 1 >= len(L) else float(L[l[1] + 1] - L[l[0]])
    for _ in range(50):
        moved = 0
        for i in sorted(np.where(small)[0], key=thickness):
            opts = [(j, l) for j, l in nbrs[i] if (j == -1 or not small[j]) and labels[j] is not None]
            if not opts:
                continue
            def inside(j):
                a, b = labels[j], labels[i]
                return b is not None and (a == AIR or (a[0] >= b[0] and a[1] <= b[1]))
            if prefer_less:   # less material first; the air only when no region will do
                opts.sort(key=lambda t: (not inside(t[0]), t[0] == -1, -t[1]))
            else:
                opts.sort(key=lambda t: -t[1])
            labels[i] = labels[opts[0][0]]
            small[i] = False
            moved += 1
        changed += moved
        if moved == 0:
            break
    left = int(small.sum())
    log(f'{what}: {changed} merged into a neighbour, {left} left alone')
    return labels[:-1]


def dissolve(polys, labels):
    by = {}
    for p, l in zip(polys, labels):
        by.setdefault(l, []).append(p)
    out_p, out_l = [], []
    for l, ps in by.items():
        for q in mill.pieces(unary_union(ps)):
            out_p.append(q)
            out_l.append(l)
    return out_p, out_l


def regions(m, screws, kind, log=log, name=''):
    L, S = band_sections(m)
    log(name, len(L), 'levels')
    S, discs = plug_screws(S, L, screws, kind)
    S = snap_bands(S, discs)
    faces, lab, M = overlay(S)
    log(name, len(faces), 'arrangement faces')
    # columns must be single intervals (no undercut): faces that are not are slivers
    bad = [i for i, l in enumerate(lab) if l is not None and M[i].sum() != l[1] - l[0] + 1]
    # a gap of a few microns inside a column is a hairline crack, not an undercut: fill it
    dz = np.diff(L)
    cracks = [i for i in bad if (dz[lab[i][0]:lab[i][1] + 1] * ~M[i][lab[i][0]:lab[i][1] + 1]).sum() < 0.05]
    for i in cracks:
        if faces[i].area > 0.01:
            log(name, 'hairline crack filled at', np.round(faces[i].representative_point().coords[0], 2), f'({faces[i].area:.3f} mm^2)')
    bad = [i for i in bad if i not in cracks]
    foot = unary_union(faces)
    outside = foot.exterior if foot.geom_type == 'Polygon' else None
    sliver = [f.buffer(-SLIVER).is_empty or f.area < 2e-3 for f in faces]
    for i in bad:
        if not sliver[i] and faces[i].area >= SMALL_AREA:
            import pickle; pickle.dump((faces[i], M[i], L), open('/tmp/clean_undercut.pkl', 'wb'))
            raise RuntimeError(f'{name}: undercut column at {faces[i].representative_point()} area {faces[i].area:.3f}')
    holes = [i for i, l in enumerate(lab) if l is None and not sliver[i] and faces[i].area < OPEN_MAX]
    for i in holes:
        log(name, 'opening through the part closed at', np.round(faces[i].representative_point().coords[0], 2),
            f'{faces[i].area:.3f} mm^2')
    small = [sliver[i] or i in bad or (lab[i] is None and faces[i].area < OPEN_MAX) for i in range(len(faces))]
    lab = merge_small(faces, lab, small, L, what=f'{name} slivers / openings', air=foot.boundary)
    gone = sum(faces[i].area for i, l in enumerate(lab) if l == AIR)
    log(name, f'specks on the outline given to the air: {gone:.3f} mm^2')
    keep_ = [i for i, l in enumerate(lab) if l is not None and l != AIR]   # real openings (switch cut-outs, window) stay open
    P, Lb = dissolve([faces[i] for i in keep_], [lab[i] for i in keep_])
    for _ in range(5):
        small = [(q.area < SMALL_AREA or q.buffer(-SMALL_W).is_empty) for q in P]
        if not any(small):
            break
        Lb = merge_small(P, Lb, small, L, what=f'{name} micro-features', air=unary_union(P).boundary)
        P, Lb = dissolve(P, Lb)
        P, Lb = [q for q, l in zip(P, Lb) if l not in (None, AIR)], [l for l in Lb if l not in (None, AIR)]
    log(name, len(P), 'regions,', len(set(Lb)), 'distinct columns')
    return L, P, Lb


FLUSH = 0.012     # neighbouring floors (or undersides) closer than this in height are made one


def flush_microsteps(L, P, Lb, d=FLUSH, log=log, name=''):
    """Steps of a few microns between neighbouring regions (left by rebuilding tilted faces) are
    levelled to the lower top / the higher underside: removes material only."""
    cols = [[float(L[b]), float(L[t + 1])] for b, t in Lb]
    tree = STRtree(P)
    nbr = [[j for j in tree.query(q) if j != i and q.boundary.intersection(P[j].boundary).length > 1e-6]
           for i, q in enumerate(P)]
    n, vol = 0, 0.0
    for _ in range(10):
        moved = 0
        for i in range(len(P)):
            for j in nbr[i]:
                for e, sign in ((1, 1), (0, -1)):    # tops: down to the lower; undersides: up to the higher
                    dzv = (cols[i][e] - cols[j][e]) * sign
                    if 1e-9 < dzv < d and cols[i][1] - cols[i][0] > dzv + 0.1:
                        vol += P[i].area * dzv
                        cols[i][e] = cols[j][e]
                        moved += 1
        n += moved
        if not moved:
            break
    log(name, f'{n} micro-steps under {d} mm levelled, {vol:.3f} mm^3 removed')
    L2 = np.unique(np.r_[[z for c in cols for z in c]])
    idx = {float(z): k for k, z in enumerate(L2)}
    return L2, [(idx[float(zb)], idx[float(zt)] - 1) for zb, zt in cols]


def thicken_skins(L, P, Lb, skin=SKIN, keep=None, log=log, name=''):
    """Where the column is thinner than `skin` (a pocket floor over the underside): raise the
    floor to the lowest top of its neighbours that makes it `skin` thick, if that block stays out
    of every keep-out (`keep`: solids); otherwise extend it downward to `skin` (a pad underneath:
    to an existing level up to 0.1 mm further down, else to exactly `skin`)."""
    cols = [[L[b], L[t + 1]] for b, t in Lb]
    tree = STRtree(P)
    n, area = 0, 0.0
    for i, (p, c) in enumerate(zip(P, cols)):
        zb, zt = c
        if zt - zb >= skin - 1e-6:
            continue
        tops = sorted({cols[j][1] for j in tree.query(p) if j != i and cols[j][1] > zt + 1e-6
                       and p.boundary.intersection(P[j].boundary).length > 1e-6})
        up = next((z for z in tops if z - zb >= skin - 1e-6), None)
        if up is not None and keep is not None:
            block = mill.prism(p, zt, up)
            bb = block.BoundingBox()
            for k in keep:
                kb = k.BoundingBox()
                if kb.xmin > bb.xmax or kb.xmax < bb.xmin or kb.ymin > bb.ymax or kb.ymax < bb.ymin or \
                        kb.zmin > bb.zmax or kb.zmax < bb.zmin:
                    continue
                inter = block.intersect(k)
                if inter.Solids() and inter.Volume() > 1e-6:
                    up = None
                    break
        if up is not None and keep is not None:
            c[1] = up
            how = f'floor {zt:.3f} -> {up:.3f}'
        else:
            want = zt - skin
            near = [z for z in L if want - 0.1 <= z <= want + 1e-6]
            c[0] = max(near) if near else want
            how = f'underside {zb:.3f} -> {c[0]:.3f}'
        log(name, f'skin {zt - zb:.2f} mm at', np.round(p.representative_point().coords[0], 2), f'({p.area:.2f} mm^2): {how}')
        n += 1; area += p.area
    log(name, n, 'thin floors thickened,', round(area, 2), 'mm^2')
    L2 = np.unique(np.r_[L, [z for c in cols for z in c]])
    idx = {float(z): k for k, z in enumerate(L2)}
    return L2, [(idx[float(zb)], idx[float(zt)] - 1) for zb, zt in cols]


def thicken_joints(L, P, Lb, skin=SKIN, joint=0.3, log=log, name=''):
    """Two neighbouring columns that overlap by less than `joint` (down to touching along a line:
    a knife edge) are joined properly: the smaller one, when it sits on top of the other, is
    extended down to overlap it by `skin`."""
    cols = [[L[b], L[t + 1]] for b, t in Lb]
    tree = STRtree(P)
    n = 0
    for _ in range(3):
        moved = 0
        for i, q in enumerate(P):
            for j in tree.query(q):
                if j == i:
                    continue
                l = q.boundary.intersection(P[j].boundary).length
                if l < 0.1:
                    continue
                (zb1, zt1), (zb2, zt2) = cols[i], cols[j]
                ov = min(zt1, zt2) - max(zb1, zb2)
                if -1e-6 < ov < joint and zb1 > zb2 + 1e-6 and (q.area <= P[j].area or q.area < 25.0):
                    new = min(zb2, zt2 - skin)
                    log(name, f'joint {ov:.2f} mm over {l:.2f} mm at', np.round(q.representative_point().coords[0], 2),
                        f'({q.area:.2f} mm^2): underside {zb1:.3f} -> {new:.3f}')
                    cols[i][0] = new
                    moved += 1
        n += moved
        if not moved:
            break
    L2 = np.unique(np.r_[L, [z for c in cols for z in c]])
    idx = {float(z): k for k, z in enumerate(L2)}
    return L2, [(idx[float(zb)], idx[float(zt)] - 1) for zb, zt in cols]


XIAO_C = 0.52     # room round the XIAO module in the tops (the build's 0.5 measured 0.4999)


def widen_pocket(L, P, Lb, foot, z0, z1, log=log, name=''):
    """A part cut from below keeps no material in the box `foot` x [z0, z1]: inside `foot`, a
    column that reaches into it starts at z1 (or goes, if it ends below z1)."""
    cols = [[float(L[b]), float(L[t + 1])] for b, t in Lb]
    nP, ncols, gone = [], [], 0.0
    for q, c in zip(P, cols):
        if not q.intersects(foot) or c[1] <= z0 or c[0] >= z1:
            nP.append(q); ncols.append(c); continue
        inside = unary_union(mill.pieces(q.intersection(foot)))
        for g in mill.pieces(q.difference(foot)):
            nP.append(g); ncols.append(c)
        for g in mill.pieces(inside):
            if c[1] > z1:
                nP.append(g); ncols.append([max(c[0], z1), c[1]])
            gone += g.area * (min(c[1], z1) - max(c[0], z0))
    log(name, f'pocket widened: {gone:.2f} mm^3 removed')
    L2 = np.unique(np.r_[L, [z for c in ncols for z in c]])
    idx = {float(z): k for k, z in enumerate(L2)}
    return L2, nP, [(idx[float(zb)], idx[float(zt)] - 1) for zb, zt in ncols]


def xiao_box(side, c=XIAO_C):
    """The XIAO module (as in build.xiao_keepout) grown by c: footprint and z range."""
    import build, shapely.affinity as sa
    (x, y), a = build.XIAO[side]
    f = sa.translate(sa.rotate(sg.box(-8.9 - c, -10.6 - c, 8.9 + c, 11.9 + c), a, origin=(0, 0)), x, y)
    return f, 1.66 - c, 5.93 + c


LEDGE = 1.0       # metal left over a pocket cut from below, where a well floor is open above (tops)
LEDGE_GROW = 1.2  # a ledge covers its thin spot grown by this (bumps along a wall merge into one ledge)
LEDGE_GAP = 0.5   # ... and keeps this far from every part above the floor (SWITCH_GAP from the
SWITCH_GAP = 0.3  # switch housings: plastic, they clip into the plate)


def raise_floors(L, P, Lb, keep, foot=None, skin=SKIN, ledge=LEDGE, grow=LEDGE_GROW, gap=LEDGE_GAP,
                 log=log, name=''):
    """Tops: where a floor open above (the keycap-well floor) is thinner than `skin` over a pocket
    cut from below (the rounded ends of the diode pockets poke out from under the webs), put a
    ledge on the floor: the thin spot grown by `grow` within that floor, clear of every part above
    it (`keep`: (gap, solid) pairs; `foot`: a footprint kept out as it is, the XIAO's with its room), raised to
    the pocket roof + `ledge` (rounded up to 0.05 mm)."""
    import build
    cols = [[float(L[b]), float(L[t + 1])] for b, t in Lb]
    zmax = max(c[1] for c in cols)
    thin = [i for i, c in enumerate(cols) if c[1] - c[0] < skin - 1e-6 and c[1] < zmax - 1e-6 and P[i].area > 1e-3]
    spots = []
    for zt in sorted({cols[i][1] for i in thin}):
        ids = [i for i in thin if cols[i][1] == zt]
        floor = unary_union([q for q, c in zip(P, cols) if abs(c[1] - zt) < 1e-6])
        th = unary_union([P[i] for i in ids])
        for piece in mill.pieces(th.buffer(grow).intersection(floor)):
            mine = [i for i in ids if P[i].intersects(piece)]
            if not mine:
                continue
            h = np.ceil((max(cols[i][0] for i in mine) + ledge) / 0.05 - 1e-6) * 0.05
            x0, y0, x1, y1 = piece.buffer(gap + 1).bounds
            out = [foot] if foot is not None and foot.intersects(piece.buffer(gap + 1)) else []
            for g, s in keep:
                b = s.BoundingBox()
                if b.xmin > x1 or b.xmax < x0 or b.ymin > y1 or b.ymax < y0 or b.zmin > h + g or b.zmax < zt:
                    continue
                cut = s.intersect(build.box(x0, x1, y0, y1, zt, h + g))
                vs = [v.toTuple()[:2] for v in cut.Vertices()]
                if len(vs) >= 3:
                    out.append(sg.MultiPoint(vs).convex_hull.buffer(g))
            left = piece.difference(unary_union(out)) if out else piece
            for g in mill.pieces(left):
                if any(P[i].intersects(g) for i in mine):
                    spots.append((g, 'top', h))
            bare = th.intersection(piece).difference(left).area
            log(name, f'ledge at', np.round(piece.centroid.coords[0], 2), f'{left.area:.2f} mm^2 raised {zt:.3f} -> {h:.3f}'
                + (f'; {bare:.3f} mm^2 of the thin spot too close to a part' if bare > 1e-3 else ''))
    if not spots:
        return L, P, Lb
    return fill_spots(L, P, Lb, spots, name=name, what='ledge')


WELL_WALL = 0.8   # walls beside a keycap well thinner than this get the well's edge moved in
CAP_GAP = 0.3     # ... as far as the keycaps (pressed or not) and switch housings allow, keeping this


def thin_pieces(sec, w, min_area=2e-3):
    """Bits of the section narrower than w (the opening by a w/2 disc, less what it rounds off
    plain corners: see walls.py)."""
    opened = sec.buffer(-w / 2, quad_segs=16).buffer(w / 2 + 1e-4, quad_segs=16)
    thin = sec.difference(opened).difference(opened.buffer(0.3 * w))
    return [g for g in mill.pieces(thin) if g.area > min_area]


def widen_well_walls(L, P, Lb, side, w=WELL_WALL, grow=1.0, gap=CAP_GAP, log=log, name=''):
    """Tops: a wall thinner than `w` between a keycap well and something else (the XIAO pocket,
    a part's pocket) is thickened into the well: the well's floor beside it comes up to the top
    face, within `grow` of the wall, `gap` clear of the keycaps (at rest and pressed down their
    3 mm travel) and the switch housings. The keycaps' room is all that limits a well's edge."""
    import build
    from common import placed
    caps = [sg.MultiPoint(t.vertices[:, :2]).convex_hull for t in placed({'keycap'}, side)]
    hous = []
    for nm, shp in build.kicad_parts():
        bb = shp.BoundingBox()
        if bb.zmax <= 8 or (side == 'L') != ((bb.xmin + bb.xmax) / 2 < 150):
            continue
        for s in shp.Solids():
            if s.BoundingBox().zmin >= 0:   # above the board: the housing and stem
                vs = [v.toTuple()[:2] for v in build.place(s, side).Vertices()]
                hous.append(sg.MultiPoint(vs).convex_hull)
    room = unary_union(caps + hous).buffer(gap)
    cols = [[float(L[b]), float(L[t + 1])] for b, t in Lb]
    zmax = max(c[1] for c in cols)
    wells = unary_union([q for q, c in zip(P, cols) if 3.6 < c[1] < 4.3])   # the wells' floors
    spots = []
    for a, b in zip(L[:-1], L[1:]):
        if b - a < 0.02 or a < 3.6 - 1e-6:
            continue   # beside the wells: above their floors
        sec = unary_union([q for q, c in zip(P, cols) if c[0] <= a + 1e-9 and c[1] >= b - 1e-9])
        for t in thin_pieces(sec, w):
            g = t.buffer(grow, quad_segs=8).intersection(wells).difference(room)
            g = g.buffer(-0.1, quad_segs=8).buffer(0.1, quad_segs=8).intersection(wells)
            for piece in mill.pieces(g):
                if piece.area > 1e-3 and piece.buffer(0.02).intersects(t):
                    spots.append((piece, 'top', zmax))
    if not spots:
        log(name, 'no thin walls beside the keycap wells')
        return L, P, Lb
    # and whatever of the well beside them a Ø2 mill can't reach any more (a corner sharper
    # than R1 between a fill and the wall next to it): filled too, no nearer the keycaps than
    # the walls round it
    walls = unary_union([q for q, c in zip(P, cols) if c[1] >= zmax - 1e-6])
    filled = unary_union([g for g, _, _ in spots])
    near = filled.buffer(4.0)   # far enough that cutting the void off here makes no false corners
    void = near.difference(walls.union(filled))
    reach = void.buffer(-1.05, quad_segs=16).buffer(1.05 + 1e-4, quad_segs=16)   # the checker's R1, with its grid
    left = void.difference(reach).intersection(wells).intersection(filled.buffer(1.2))
    spots += [(g, 'top', zmax) for g in mill.pieces(left) if g.area > 1e-5]
    return fill_spots(L, P, Lb, spots, name=name, what='keycap-well wall')


SEAM_FLAT_GAP = 0.4   # the back seam made plain: the top's back wall stops this far over the bottom's


def back_seam_runs(side, y_out=-47.8, y_in=-48.6, y_lip=-48.8, step=0.05, min_len=2.0):
    """Where the back seam is a tongue and groove whose bottom half is castellated (the original's
    arches, cut as 2.5D steps): runs along x with the bottom's flat ledge inside at h, its outer
    lip at most 0.75 mm above that, the top's underside over the lip about 1.1 mm up and its inner
    lip 0.4 mm up. [(x0, x1, h)] from the build's parts (both parts use the same runs)."""
    import build
    def mesh(kind):
        s = cq.Shape.importBrep(f'final_{kind}_{side}.brep')
        return mill.mesh_of(max(s.Solids(), key=lambda x: x.Volume()), 0.002)
    B, T = mesh('bottom'), mesh('top')
    x0, x1 = (B.bounds[0][0], B.bounds[1][0])
    xs = np.arange(x0, x1, step)
    def heights(m, y, up):
        o = np.c_[xs, np.full(len(xs), y), np.full(len(xs), -30.0)]
        loc, idx, _ = m.ray.intersects_location(o, np.tile([0, 0, 1.0], (len(o), 1)), multiple_hits=True)
        v = np.full(len(xs), np.nan)
        for (_, _, z), i in zip(loc, idx):
            v[i] = z if np.isnan(v[i]) else (max(v[i], z) if up else min(v[i], z))
        return v
    h, b = heights(B, y_in, True), heights(B, y_out, True)
    t, u = heights(T, y_out, False), heights(T, y_lip, False)
    # the bottom's lip comes down where the top is at least 0.5 mm over the ledge; the top comes
    # down where it is about 1.1 mm over it, its (also castellated) inner lip 0.3-1.2 mm over it
    flat = np.abs(np.r_[0, np.diff(h)]) < 1e-6
    lip = (b >= h - 1e-6) & (b <= h + 0.75) & (t - h >= 0.5) & flat
    top = (np.abs(t - h - 1.1) < 0.15) & (u >= h + SEAM_FLAT_GAP - 0.1) & (u <= h + 1.2) & lip   # only over a lip that goes
    def runs_of(ok):
        out, start = [], None
        for i, o in enumerate(np.r_[ok, False]):
            if o and start is None:
                start = i
            elif not o and start is not None:
                if xs[i - 1] - xs[start] >= min_len and np.ptp(h[start:i]) < 1e-6:
                    out.append((float(xs[start]), float(xs[i - 1]), float(h[start])))
                start = None
        return out
    # the top's runs stop 1.2 mm short of the bottom's: where the top's lowered face ends, the
    # mill leaves its R1 corner past the end, which must still be over the lowered lip
    tops = [(a + 1.2, b - 1.2, h_) for a, b, h_ in runs_of(top) if b - a > 2.4 + min_len]
    return dict(bottom=runs_of(lip), top=tops)


def flat_back_seam(L, P, Lb, kind, runs, log=log, name=''):
    """The back seam made plain over `runs` (back_seam_runs, per part): the bottom's castellated
    outer lip comes down to the ledge inside it (h), the top's back wall over it comes down to
    h + SEAM_FLAT_GAP: the seam is one straight line 0.4 mm wide, no 0.2 mm lip."""
    cols = [[float(L[b]), float(L[t + 1])] for b, t in Lb]
    nP, ncols, moved = [], [], 0.0
    runs = runs[kind]
    y0 = -48.35 if kind == 'bottom' else -48.6    # the bottom's outer lip; the top over it (its inner lip,
    # hidden, stays: lowering it too would leave a pocket over the board too narrow for the mill)
    zones = [(sg.box(x0, y0, x1, -40.0), h) for x0, x1, h in runs]
    for q, c in zip(P, cols):
        rest = q
        for zone, h in zones:
            if not rest.intersects(zone):
                continue
            if kind == 'bottom':
                change, nc = h + 1e-6 < c[1] <= h + 0.8 and c[0] < h - 1e-6, [c[0], h]
            else:
                g = h + SEAM_FLAT_GAP
                change, nc = g + 1e-6 < c[0] <= h + 1.2 and c[1] > g + 1e-6, [g, c[1]]
            if not change:
                continue
            for piece in mill.pieces(mill.tidy(rest.intersection(zone))):
                nP.append(piece); ncols.append(nc)
                moved += piece.area * abs((c[1] - h) if kind == 'bottom' else (c[0] - nc[0]))
            rest = mill.tidy(rest.difference(zone))
        for piece in mill.pieces(rest):
            nP.append(piece); ncols.append(c)
    log(name, f'back seam made plain over {len(runs)} runs ({sum(r[1] - r[0] for r in runs):.1f} mm): '
              f'{moved:.2f} mm^3 {"removed" if kind == "bottom" else "added"}')
    L2 = np.unique(np.r_[L, [z for c in ncols for z in c]])
    idx = {float(z): k for k, z in enumerate(L2)}
    return L2, nP, [(idx[float(zb)], idx[float(zt)] - 1) for zb, zt in ncols]


def snap_regions(P, Lb, grid=1e-5):
    """Regions on a fine grid (many splits leave nearly coincident vertices)."""
    nP, nLb = [], []
    for q, lb in zip(P, Lb):
        for g in mill.pieces(shapely.make_valid(shapely.set_precision(q, grid))):
            if g.area > 1e-8:
                nP.append(g); nLb.append(lb)
    return nP, nLb


def open_xiao_end(L, P, Lb, side, kind, strip=0.6, log=log, name=''):
    """The XIAO's USB end sits 0.64 mm inside the outer face; with its 0.5 mm of room the wall in
    front of it is 0.14 mm. That wall is opened, over the module's end, between the floor (bottom)
    and roof (top) of its pocket: the side opening round the USB-C port becomes the module's end."""
    foot, z0, z1 = xiao_box(side)
    cols = [[float(L[b]), float(L[t + 1])] for b, t in Lb]
    # only at the outer face: the part's outline without its openings (switch cut-outs, window)
    outer = unary_union([sg.Polygon(g.exterior) for g in mill.pieces(unary_union(P))])
    zone = foot.buffer(strip).intersection(outer.difference(outer.buffer(-strip))).difference(foot)
    # the pocket's floor (bottom) or roof (top): the level under (over) most of the module
    area = {}
    for q, c in zip(P, cols):
        z = c[1] if kind == 'bottom' else c[0]
        if (kind == 'bottom' and z0 - 0.6 < z < z0 + 0.1) or (kind == 'top' and z1 - 0.1 < z < z1 + 0.6):
            area[z] = area.get(z, 0.0) + q.intersection(foot).area
    h = max(area, key=area.get)
    nP, ncols, gone = [], [], 0.0
    for q, c in zip(P, cols):
        cut = q.intersection(zone) if q.intersects(zone) else sg.Polygon()
        change = (kind == 'bottom' and c[1] > h + 1e-6 and c[0] < h - 1e-6) or \
                 (kind == 'top' and c[0] < h - 1e-6 and c[1] > h + 1e-6)
        if cut.area < 1e-4 or not change:
            nP.append(q); ncols.append(c); continue
        for g in mill.pieces(mill.tidy(cut)):
            nP.append(g); ncols.append([c[0], h] if kind == 'bottom' else [h, c[1]])
            gone += g.area * ((c[1] - h) if kind == 'bottom' else (h - c[0]))
        for g in mill.pieces(mill.tidy(q.difference(zone))):
            nP.append(g); ncols.append(c)
    log(name, f'XIAO end opened down/up to {h:.3f}: {gone:.2f} mm^3 removed')
    L2 = np.unique(np.r_[L, [z for c in ncols for z in c]])
    idx = {float(z): k for k, z in enumerate(L2)}
    return L2, nP, [(idx[float(zb)], idx[float(zt)] - 1) for zb, zt in ncols]


R_REPAIR = 0.97   # a Ø2 mm end mill must reach every void (machinable.py: R1 less its 0.03 tolerance)
DEPTH_TOL = 0.03  # ... and leaves less than this (machinable.py ignores shallower spots)
SPOT_W = 0.03     # unreachable bits narrower than 2x this are slivers of the polygonal arcs, not spots


def mill_repair(L, P, Lb, r=R_REPAIR, min_area=2e-3, log=log, name='', sides=('top', 'bottom')):
    """Where a Ø2r flat end mill can't reach a void (from above, at each level, the void is the
    union of the regions whose top is below that level, plus the air around the part; from below
    likewise), fill it: the region's top (or underside) moves to the next level. Adds material
    only there, so pockets the mill does reach are left exactly as they are."""
    cols = [[float(L[b]), float(L[t + 1])] for b, t in Lb]
    P = list(P)
    foot = unary_union(P)
    stock = sg.box(*np.add(foot.bounds, [-5, -5, 5, 5]))
    added, fills = 0.0, []
    for side in sides:
        zs = sorted({c[1] if side == 'top' else c[0] for c in cols}, reverse=(side == 'bottom'))
        for k, z in enumerate(zs[:-1]):
            znext = zs[k + 1]
            if abs(znext - z) < DEPTH_TOL:
                continue
            # the void is everything that is not metal just above (below) z: the air round the
            # part and hairline gaps between pieces count as void too
            if side == 'top':
                void = stock.difference(unary_union([q for q, c in zip(P, cols) if c[1] > z + 1e-9]))
            else:
                void = stock.difference(unary_union([q for q, c in zip(P, cols) if c[0] < z - 1e-9]))
            reach = void.buffer(-r, quad_segs=32).buffer(r, quad_segs=32)
            miss = unary_union(mill.pieces(void.difference(reach).intersection(foot))).buffer(0)
            core = miss.buffer(-SPOT_W, quad_segs=4).buffer(SPOT_W, quad_segs=4)
            bad = [g for g in mill.pieces(miss.intersection(core.buffer(0.05, quad_segs=4)))
                   if g.area > min_area and g.intersects(core)]
            # what the mill leaves in a corner reaches up (down) only as far as the walls that
            # make the corner: fill a spot to the next level only where such a wall borders it
            tall = unary_union([q for q, c in zip(P, cols)
                                if (c[1] >= znext - 1e-9 if side == 'top' else c[0] <= znext + 1e-9)])
            bad = unary_union([g for g in bad if g.buffer(1e-4).intersection(tall).area > 1e-8])
            if bad.is_empty:
                continue
            nP, ncols = [], []
            for q, c in zip(P, cols):
                hit = (c[1] <= z + 1e-9) if side == 'top' else (c[0] >= z - 1e-9)
                inter = q.intersection(bad) if hit and q.intersects(bad) else sg.Polygon()
                if inter.area < 1e-9:
                    nP.append(q); ncols.append(c); continue
                for g in mill.pieces(inter):
                    nc = [c[0], znext] if side == 'top' else [znext, c[1]]
                    nP.append(g); ncols.append(nc)
                    added += g.area * abs(znext - z)
                    fills.append(g)
                for g in mill.pieces(q.difference(bad)):
                    nP.append(g); ncols.append(c)
            log(name, f'{side}: void the mill cannot reach at z {z:.3f}: {bad.area:.3f} mm^2 filled to {znext:.3f}',
                [tuple(np.round(g.centroid.coords[0], 2)) for g in mill.pieces(bad)][:4])
            P, cols = nP, ncols
    log(name, f'mill reach repairs: {added:.2f} mm^3 added')
    L2 = np.unique(np.r_[L, [z for c in cols for z in c]])
    idx = {float(z): k for k, z in enumerate(L2)}
    return L2, P, [(idx[float(zb)], idx[float(zt)] - 1) for zb, zt in cols], unary_union(fills) if fills else sg.Polygon()


GRID = 1e-3   # region outlines are snap-rounded together on this grid


def snap_round(P, Lb, L, grid=GRID, log=log, name=''):
    """All region outlines snap-rounded together on one grid (consistent noding: no needle
    spikes, near-touching edges or edges shorter than the grid), re-polygonized; each face goes to
    the region it overlaps most, specks and gaps to a neighbouring region. Regions keep their
    identity (a region cut in two stays two)."""
    lines = shapely.union_all([q.boundary for q in P], grid_size=grid)   # snap-rounded noding
    faces = list(polygonize(lines))
    tree = STRtree(P)
    owner = []
    for f in faces:
        # the region it overlaps most (a representative point can land on a needle tip)
        cand = [(P[i].intersection(f).area, i) for i in tree.query(f)]
        cand = [c for c in cand if c[0] > 0.5 * f.area]
        owner.append((max(cand)[1],) * 2 if cand else None)   # merge_small wants (b, t)-like labels
    # specks and hairline gaps go to a neighbour; openings (no region there before) stay open
    small = [(o is None and f.area < OPEN_MAX and f.buffer(-SLIVER).is_empty) or
             (o is not None and (f.area < 10 * grid * grid or f.buffer(-grid).is_empty)) for f, o in zip(faces, owner)]
    if any(small):
        owner = merge_small(faces, owner, small, L, prefer_less=False, log=lambda *a: None)
    keep_ = [i for i, o in enumerate(owner) if o is not None]
    Q, O = dissolve([faces[i] for i in keep_], [owner[i] for i in keep_])
    return Q, [Lb[o[0]] for o in O]


def touching_holes(P, gap=GRID * 3):
    """Vertical cut lines through every hole that touches (or nearly touches) its region's outer
    edge or another hole: such a face is not valid CAD."""
    cuts = []
    for q in P:
        ex = q.exterior
        hs = list(q.interiors)
        for k, h in enumerate(hs):
            if ex.distance(h) < gap or any(h.distance(o) < gap for o in hs[:k] + hs[k + 1:]):
                x = round(sg.Polygon(h).centroid.x / GRID) * GRID
                x0, y0, x1, y1 = q.bounds
                # a hair past the outline at both ends, so the cut is noded with it
                cuts.append(sg.LineString([(x, y0 - 1), (x, y1 + 1)]).intersection(sg.Polygon(ex).buffer(1e-6)))
    return cuts


def split_regions(P, Lb, cuts):
    """Cut regions along lines, re-noding every outline so the neighbours get the same vertices."""
    faces = list(polygonize(unary_union([q.boundary for q in P] + cuts)))
    tree = STRtree(P)
    outP, outL = [], []
    for f in faces:
        cand = [(P[i].intersection(f).area, i) for i in tree.query(f)]
        cand = [c for c in cand if c[0] > 0.5 * f.area]
        if cand:
            outP.append(f); outL.append(Lb[max(cand)[1]])
    return outP, outL


def absorb_small(P, Lb, L, fills=None):
    """Specks left after the repairs and cuts (under SMALL_AREA, or narrower than 2 SMALL_W) are
    joined to a neighbour region: one with less material if there is one (removal), else the one
    they share the longest border with; a speck the mill repair filled goes to a neighbour with more
    material instead (the corner stays filled). The neighbour keeps its identity."""
    P, Lb = list(P), list(Lb)
    n = 0
    while True:
        small = [i for i, q in enumerate(P) if q.area < SMALL_AREA or q.buffer(-SMALL_W).is_empty]
        if not small:
            return P, Lb, n
        tree = STRtree(P)
        done = set()
        for i in small:
            if i in done:
                continue
            q, (b, t) = P[i], Lb[i]
            filled = fills is not None and not fills.is_empty and q.intersection(fills).area > 0.5 * q.area
            opts = []
            for j in tree.query(q):
                if j == i or j in done:
                    continue
                l = q.boundary.intersection(P[j].boundary).length
                if l > 1e-9:
                    bj, tj = Lb[j]
                    if filled:   # prefer a column that holds this one
                        opts.append((not (L[bj] <= L[b] and L[tj + 1] >= L[t + 1]), -l, j))
                    else:
                        opts.append((not (L[bj] >= L[b] and L[tj + 1] <= L[t + 1]), -l, j))
            if not opts:
                done.add(i); continue
            j = min(opts)[2]
            P[j] = unary_union([P[j], q])
            done.add(i); n += 1
        keep_ = [k for k in range(len(P)) if k not in done or k not in small]
        P = [P[k] for k in keep_]; Lb = [Lb[k] for k in keep_]
        P2, L2 = [], []
        for q, l in zip(P, Lb):
            for g in mill.pieces(q):
                P2.append(g); L2.append(l)
        P, Lb = P2, L2


def tidy_regions(P, Lb, L, log=log, name='', fills=None):
    """Regions ready for CAD: snap-rounded together, and where a hole touches its region's outer
    edge or another hole, the region is cut through the hole."""
    n0 = len(P)
    for it in range(4):
        P, Lb = snap_round(P, Lb, L, name=name)
        P, Lb, nsmall = absorb_small(P, Lb, L, fills)
        if nsmall:
            P, Lb = snap_round(P, Lb, L, name=name)
        cuts = touching_holes(P)
        if not cuts:
            break
        P, Lb = split_regions(P, Lb, cuts)
    else:
        import pickle
        pickle.dump((P, Lb, cuts), open(f'/tmp/clean_touch_{name.replace(" ", "_")}.pkl', 'wb'))
        raise RuntimeError(f'{name}: holes still touch after {it + 1} rounds: {[c.centroid for c in cuts][:5]}')
    short = min(np.sqrt((np.diff(np.asarray(r.coords), axis=0) ** 2).sum(1)).min()
                for q in P for r in [q.exterior] + list(q.interiors))
    log(name, f'outlines snap-rounded on a {GRID} grid ({it} rounds of cuts at touching holes): '
        f'{n0} -> {len(P)} regions, shortest edge {short:.4f}')
    return P, Lb


# ------------------------------------------------------------------ chains and fitting
def key(p):
    return (float(p[0]), float(p[1]))


def chains(P):
    """Boundary chains between regions: maximal runs of vertices of degree 2 in the graph of all
    region outlines. Returns list of (n,2) arrays and a map segment -> (chain, index)."""
    adj = {}
    rings = []
    for q in P:
        for r in [q.exterior] + list(q.interiors):
            c = np.asarray(r.coords)[:-1]
            rings.append(c)
            n = len(c)
            for i in range(n):
                a, b = key(c[i]), key(c[(i + 1) % n])
                adj.setdefault(a, set()).add(b)
                adj.setdefault(b, set()).add(a)
    node = {v for v, s in adj.items() if len(s) != 2}
    seen = set()
    out, seg = [], {}

    def walk(start, nxt):
        pts = [start, nxt]
        prev, cur = start, nxt
        while cur not in node and cur != start:
            a, b = adj[cur]
            n2 = b if a == prev else a
            prev, cur = cur, n2
            pts.append(cur)
        return pts
    for v in list(node):
        for w in adj[v]:
            if (v, w) in seen:
                continue
            pts = walk(v, w)
            for a, b in zip(pts[:-1], pts[1:]):
                seen.add((a, b)); seen.add((b, a))
            out.append(np.array(pts))
    # closed loops without any node
    for v in adj:
        for w in adj[v]:
            if (v, w) in seen:
                continue
            pts = walk(v, w)
            for a, b in zip(pts[:-1], pts[1:]):
                seen.add((a, b)); seen.add((b, a))
            out.append(np.array(pts))
    for ci, pts in enumerate(out):
        for i in range(len(pts) - 1):
            seg[(key(pts[i]), key(pts[i + 1]))] = (ci, i, 1)
            seg[(key(pts[i + 1]), key(pts[i]))] = (ci, i, -1)
    return out, seg


def fit_chains(C, tol=FIT_TOL, modes=None):
    """modes per chain: 'fit' (lines and arcs), 'lines' (straight runs merged), 'raw' (every
    vertex kept)."""
    F = []
    for ci, pts in enumerate(C):
        mode = modes[ci] if modes else 'fit'
        if mode == 'raw':
            pr = [('line', i, i + 1) for i in range(len(pts) - 1)]
        else:
            pr = fit2d.fit(pts, tol, rmax=500.0 if mode == 'fit' else 0.0)
        # a chain closed on itself as a single arc can't be drawn with one 3-point arc: split it
        out = []
        for p in pr:
            if p[0] == 'arc' and np.allclose(pts[p[1]], pts[p[2]]):
                k = (p[1] + p[2]) // 2
                out += [('arc', p[1], k, p[3], p[4]), ('arc', k, p[2], p[3], p[4])]
            else:
                out.append(p)
        F.append(out)
    return F


def ring_chains(q, seg):
    out = set()
    for r in [q.exterior] + list(q.interiors):
        c = np.asarray(r.coords)
        for i in range(len(c) - 1):
            out.add(seg[(key(c[i]), key(c[i + 1]))][0])
    return out


def checked_faces(P, C, seg, log=log, name=''):
    """Fit every chain, then make each region's face; a chain used by a face that comes out
    invalid (an arc crossing a neighbouring edge in a narrow wedge) is drawn more plainly:
    lines only, then its own vertices. Returns faces (at z = 0) and the fitted chains."""
    from OCP.BRepCheck import BRepCheck_Analyzer
    modes = ['fit'] * len(C)
    users = [ring_chains(q, seg) for q in P]
    for rnd in range(3):
        F = fit_chains(C, modes=modes)
        faces, bad = [], []
        for qi, q in enumerate(P):
            f = region_face(q, C, F, seg, 0.0)
            ok = BRepCheck_Analyzer(f).IsValid() and abs(cq.Face(f).Area() - q.area) < 0.01 + 0.005 * q.area
            faces.append(f)
            if not ok:
                bad.append(qi)
        log(name, f'faces: {len(bad)} invalid in round {rnd}')
        if not bad:
            return faces, F
        nxt = {'fit': 'lines', 'lines': 'raw', 'raw': 'raw'}
        for qi in bad:
            for ci in users[qi]:
                modes[ci] = nxt[modes[ci]]
    import pickle
    pickle.dump([P[i] for i in bad], open(f'/tmp/clean_bad_{name.replace(" ", "_")}.pkl', 'wb'))
    raise BadFaces(bad)


class BadFaces(RuntimeError):
    """Regions whose face stays invalid however plainly its outline is drawn."""
    def __init__(self, bad):
        super().__init__(f'faces still invalid: {bad[:10]}')
        self.bad = bad


def merge_bad(P, Lb, L, bad, log=log, name=''):
    """Each region in `bad` (BadFaces) joins the neighbour it shares the longest border with, one
    whose column holds it if there is one (metal is only added)."""
    P, Lb = list(P), list(Lb)
    tree = STRtree(P)
    gone = set()
    for i in bad:
        b, t = Lb[i]
        opts = []
        for j in tree.query(P[i]):
            if j == i or j in gone or j in bad:
                continue
            l = P[i].boundary.intersection(P[j].boundary).length
            if l > 1e-6:
                bj, tj = Lb[j]
                opts.append((not (L[bj] <= L[b] and L[tj + 1] >= L[t + 1]), -l, j))
        if not opts:
            continue
        j = min(opts)[2]
        log(name, f'region {P[i].area:.3f} mm^2 at', np.round(P[i].representative_point().coords[0], 2),
            f'(no valid face) joined to its neighbour ({L[Lb[j][0]]:.3f}..{L[Lb[j][1] + 1]:.3f})')
        P[j] = P[j].union(P[i]); gone.add(i)
    keep = [k for k in range(len(P)) if k not in gone]
    return [P[k] for k in keep], [Lb[k] for k in keep]


# ------------------------------------------------------------------ OCC construction
from OCP.gp import gp_Pnt, gp_Vec
from OCP.GC import GC_MakeArcOfCircle
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.TopTools import TopTools_ListOfShape
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain


def ring_edges(coords, C, F, seg, z):
    """OCC edges of a region outline at height z, drawn with the fitted primitives of its chains."""
    c = np.asarray(coords)[:-1]
    n = len(c)
    ids = []   # per ring segment: (chain, primitive, direction, segment index in the chain)
    for i in range(n):
        ci, k, d = seg[(key(c[i]), key(c[(i + 1) % n]))]
        pi = next(j for j, p in enumerate(F[ci]) if p[1] <= k < p[2])
        ids.append((ci, pi, d, k))
    same = lambda a, b: a[:3] == b[:3]
    # start the walk at a primitive boundary
    s = next((i for i in range(n) if not same(ids[i], ids[i - 1])), 0)
    edges = []
    i = 0
    while i < n:
        j = i
        while j + 1 < n and same(ids[(s + j + 1) % n], ids[(s + i) % n]):
            j += 1
        a, b = c[(s + i) % n], c[(s + j + 1) % n]
        ci, pi, d, k0 = ids[(s + i) % n]
        k1 = ids[(s + j) % n][3]
        p = F[ci][pi]
        A, B = gp_Pnt(a[0], a[1], z), gp_Pnt(b[0], b[1], z)
        if p[0] == 'line':
            e = BRepBuilderAPI_MakeEdge(A, B).Edge()
        else:
            # chain vertex indices of this run's ends (a ring may use only part of a primitive)
            ka, kb = (k0, k1 + 1) if d == 1 else (k1, k0 + 1)
            mid = arc_mid(p, C[ci], ka, kb)
            arc = GC_MakeArcOfCircle(A, gp_Pnt(mid[0], mid[1], z), B)
            if arc.IsDone() and A.Distance(B) > 1e-7:
                e = BRepBuilderAPI_MakeEdge(arc.Value()).Edge()
            else:   # too short or too flat for an arc: the run's own segments
                run = [c[(s + q) % n] for q in range(i, j + 2)]
                for u, v in zip(run[:-1], run[1:]):
                    edges.append(BRepBuilderAPI_MakeEdge(gp_Pnt(u[0], u[1], z), gp_Pnt(v[0], v[1], z)).Edge())
                i = j + 1
                continue
        edges.append(e)
        i = j + 1
    return edges


def arc_mid(p, pts, ka, kb):
    _, i, j, cen, r = p
    ang = np.unwrap(np.arctan2(pts[i:j + 1, 1] - cen[1], pts[i:j + 1, 0] - cen[0]))
    t = (ang[ka - i] + ang[kb - i]) / 2
    return cen + r * np.array([np.cos(t), np.sin(t)])


def region_face(q, C, F, seg, z):
    from shapely.geometry.polygon import orient
    q = orient(q, 1.0)
    def wire(r):
        w = BRepBuilderAPI_MakeWire()
        for e in ring_edges(r.coords, C, F, seg, z):
            w.Add(e)
        assert w.IsDone(), 'wire'
        return w.Wire()
    mf = BRepBuilderAPI_MakeFace(wire(q.exterior), True)
    for h in q.interiors:
        mf.Add(wire(h))
    assert mf.IsDone(), 'face'
    return mf.Face()


def blocks(L, Lb, faces):
    from OCP.gp import gp_Trsf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    out = []
    for f, (b, t) in zip(faces, Lb):
        z0, z1 = float(L[b]), float(L[t + 1])
        tr = gp_Trsf(); tr.SetTranslation(gp_Vec(0, 0, z0))
        f = BRepBuilderAPI_Transform(f, tr, True).Shape()
        out.append(BRepPrimAPI_MakePrism(f, gp_Vec(0, 0, z1 - z0)).Shape())
    return out


def fuse_all(shapes, fuzzy=1e-6):
    args, tools = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(shapes[0])
    for s in shapes[1:]:
        tools.Append(s)
    op = BRepAlgoAPI_Fuse()
    op.SetArguments(args); op.SetTools(tools)
    op.SetRunParallel(True); op.SetFuzzyValue(fuzzy)
    op.Build()
    assert op.IsDone(), 'fuse failed'
    u = ShapeUpgrade_UnifySameDomain(op.Shape(), True, True, True)
    u.Build()
    return cq.Shape.cast(u.Shape())


def revolve_cutter(profile, cx, cy):
    """Solid of revolution of an (r, z) polygon (r >= 0) about the vertical axis at (cx, cy)."""
    pts = [cq.Vector(cx + r, cy, z) for r, z in profile]
    w = cq.Wire.makePolygon(pts, close=True)
    f = cq.Face.makeFromWires(w)
    return cq.Solid.revolve(f, 360, cq.Vector(cx, cy, 0), cq.Vector(cx, cy, 1))


def hole_profiles(kind, zb, zt):
    """(r, z) outline of the void of one screw hole (see TOP_FACE, BOT_TAP)."""
    if kind == 'top':
        top = zt + 0.3
        zc = TOP_FACE - (TOP_CS_R - TOP_NECK)          # where the 90° cone meets the neck
        return [(0, zb - 0.3), (TOP_NECK, zb - 0.3), (TOP_NECK, zc), (TOP_CS_R + (top - TOP_FACE), top), (0, top)]
    return [(0, zt + 0.3), (BOT_TAP, zt + 0.3), (BOT_TAP, BOT_DRILL), (0, BOT_DRILL)]


def checker_spots(solid, drill_r=None, screws=()):
    """The spots machinable.py finds on a solid (same grid, tool and tolerances), each as
    (polygon, side, height the mill leaves there)."""
    import machinable, scipy.ndimage as nd
    zt, zb, Lm, cnt, xs, ys, bb = machinable.columns(solid)
    top, bot, top_m, bot_m, lo, hi = machinable.machined(zt, zb, 1.0)
    full = ~np.isnan(zt)
    ex_top = np.where(full & (top_m > top + 1e-6), top_m - top, 0)
    ex_bot = np.where(full & (bot_m < bot - 1e-6), bot - bot_m, 0)
    X, Y = np.meshgrid(xs, ys)
    out = []
    away = np.ones(X.shape, bool)
    for x, y in screws:
        away &= (X - x) ** 2 + (Y - y) ** 2 > 2.4 ** 2
    # as machinable.py: grid noise is dropped from both sides together, then split by side
    both = nd.binary_opening(away & ((ex_top > DEPTH_TOL) | (ex_bot > DEPTH_TOL)), structure=np.ones((2, 2)))
    for side, ex, m in (('top', ex_top, top_m), ('bottom', ex_bot, bot_m)):
        bad = both & (ex > DEPTH_TOL)
        lab, n = nd.label(bad)
        for i in range(1, n + 1):
            sel = lab == i
            yy, xx = np.where(sel)
            cells = unary_union([sg.box(xs[c] - 0.026, ys[r] - 0.026, xs[c] + 0.026, ys[r] + 0.026) for r, c in zip(yy, xx)])
            h = float(m[sel].max()) if side == 'top' else float(m[sel].min())
            out.append((cells.convex_hull.buffer(0.02, quad_segs=4), side, h))
    return out


def fill_spots(L, P, Lb, spots, log=log, name='', what='checker spot'):
    """Raise (lower) the columns in each checker spot to the height the mill leaves there."""
    cols = [[float(L[b]), float(L[t + 1])] for b, t in Lb]
    nP, ncols, added = [], [], 0.0
    for q, c in zip(P, cols):
        rest = q
        for poly, side, h in spots:
            if not rest.intersects(poly):
                continue
            need = (c[1] < h - 1e-6 and c[0] < h) if side == 'top' else (c[0] > h + 1e-6 and c[1] > h)
            if not need:
                continue
            inter = mill.tidy(rest.intersection(poly))
            for g in mill.pieces(inter):
                nc = [c[0], h] if side == 'top' else [h, c[1]]
                nP.append(g); ncols.append(nc)
                added += g.area * abs(h - (c[1] if side == 'top' else c[0]))
            rest = mill.tidy(rest.difference(poly))
        for g in mill.pieces(rest):
            nP.append(g); ncols.append(c)
    for poly, side, h in spots:
        log(name, f'{what} ({side}) at', np.round(poly.centroid.coords[0], 2), f'{poly.area:.3f} mm^2 filled to {h:.3f}')
    log(name, f'{what}s filled: {added:.3f} mm^3 added')
    L2 = np.unique(np.r_[L, [z for c in ncols for z in c]])
    idx = {float(z): k for k, z in enumerate(L2)}
    return L2, nP, [(idx[float(zb)], idx[float(zt)] - 1) for zb, zt in ncols]


def rebuild(shape, screws, kind, name='', mesh_tol=0.0005, keep=None, side=None):
    cache = W / f'clean_mesh_{name.replace(" ", "_")}.npz'
    if cache.exists() and abs(float(np.load(cache)['vol']) - shape.Volume()) < 1e-6:
        z = np.load(cache)
        import trimesh
        m = trimesh.Trimesh(z['v'], z['f'], process=False)
    else:
        m = mill.planar_mesh(shape)
        if m is None:
            m = mill.mesh_of(shape, mesh_tol)
        np.savez(cache, v=m.vertices, f=m.faces, vol=shape.Volume())
    log(name, 'mesh', len(m.faces), 'triangles, volume', round(m.volume, 2), 'part', round(shape.Volume(), 2))
    assert abs(m.volume - shape.Volume()) < 0.05 + 1e-4 * shape.Volume(), 'mesh volume'
    L, P, Lb = regions(m, screws, kind, name=name)
    L, Lb = flush_microsteps(L, P, Lb, name=name)
    if kind == 'bottom':
        L, Lb = thicken_skins(L, P, Lb, keep=keep, name=name)
        L, Lb = thicken_joints(L, P, Lb, name=name)
    if kind == 'top' and side is not None:
        foot, z0, z1 = xiao_box(side)
        L, P, Lb = widen_pocket(L, P, Lb, foot, z0, z1, name=name)
        L, P, Lb = raise_floors(L, P, Lb, keep or [], foot=foot, name=name)
        L, P, Lb = widen_well_walls(L, P, Lb, side, name=name)
    if side is not None:
        L, P, Lb = open_xiao_end(L, P, Lb, side, kind, name=name)
        L, P, Lb = flat_back_seam(L, P, Lb, kind, back_seam_runs(side), name=name)
        P, Lb = snap_regions(P, Lb)
    L, P, Lb, fills = mill_repair(L, P, Lb, name=name)
    vol = sum(q.area * (L[t + 1] - L[b]) for q, (b, t) in zip(P, Lb))
    log(name, f'regions volume (holes filled) {vol:.2f}')
    P, Lb = tidy_regions(P, Lb, L, name=name, fills=fills)
    for rnd in range(6):
        for _ in range(3):
            try:
                solid = make_solid(L, P, Lb, screws, kind, name=name)
                break
            except BadFaces as e:
                P, Lb = merge_bad(P, Lb, L, e.bad, name=name)
                P, Lb = tidy_regions(P, Lb, L, name=name)
        else:
            solid = make_solid(L, P, Lb, screws, kind, name=name)
        # the checker itself, on the finished part: what a Ø2 mill still can't reach is filled to
        # the height the mill leaves there, and the part made again
        spots = checker_spots(solid, screws=screws)
        if not spots:
            break
        L, P, Lb = fill_spots(L, P, Lb, spots, name=name)
        P, Lb = tidy_regions(P, Lb, L, name=name, fills=unary_union([sp[0] for sp in spots]))
    else:
        log(name, 'checker spots left after 6 rounds:', len(spots))
    log(name, 'final: valid', solid.isValid(), 'faces', len(solid.Faces()), 'volume', round(solid.Volume(), 2),
        '(was', round(shape.Volume(), 2), ')')
    return solid, dict(levels=L, regions=P, labels=Lb)


def top_parts(side):
    """Every KiCad part solid on this half, placed as the case sees it (as verify.py does), with
    the room a ledge keeps from it: (gap, solid)."""
    import build
    out = []
    for nm, shp in build.kicad_parts():
        bb = shp.BoundingBox()
        if (side == 'L') != ((bb.xmin + bb.xmax) / 2 < 150) or nm.startswith('J'):
            continue
        g = SWITCH_GAP if nm.startswith('SW') else LEDGE_GAP
        out += [(g, build.place(build.lift(s) if s.BoundingBox().zmin > 0.75 else s, side)) for s in shp.Solids()]
    return out


def make_solid(L, P, Lb, screws, kind, name=''):
    C, seg = chains(P)
    faces, F = checked_faces(P, C, seg, name=name)
    npts = sum(len(c) for c in C)
    nprim = sum(len(f) for f in F)
    narc = sum(1 for f in F for p in f if p[0] == 'arc')
    log(name, f'{len(C)} chains, {npts} vertices -> {nprim} primitives ({narc} arcs)')
    B = blocks(L, Lb, faces)
    log(name, len(B), 'prisms')
    solid = fuse_all(B)
    log(name, 'fused:', len(solid.Solids()), 'solids,', len(solid.Faces()), 'faces, volume', round(solid.Volume(), 2))
    # the screw holes, exact
    bb = solid.BoundingBox()
    for (x, y) in screws:
        # through the whole part: the bore / counterbore and the neck are void wherever they pass
        cut = revolve_cutter(hole_profiles(kind, bb.zmin - 1, bb.zmax + 1), x, y)
        solid = solid.cut(cut)
    u = ShapeUpgrade_UnifySameDomain(solid.wrapped, True, True, True); u.Build()
    solid = cq.Shape.cast(u.Shape())
    sols = sorted(solid.Solids(), key=lambda s: -s.Volume())
    for f in sols[1:]:
        b = f.BoundingBox()
        log(name, f'fragment dropped: {f.Volume():.4f} mm^3 at ({(b.xmin + b.xmax) / 2:.2f}, {(b.ymin + b.ymax) / 2:.2f}, '
            f'{(b.zmin + b.zmax) / 2:.2f}) size {b.xlen:.3f} x {b.ylen:.3f} x {b.zlen:.3f}')
    log(name, 'holes cut:', len(sols), 'solids, valid', sols[0].isValid(), 'faces', len(sols[0].Faces()),
        'volume', round(sols[0].Volume(), 2))
    return sols[0]


if __name__ == '__main__':
    # clean.py --all: the build's four aluminum parts (final_*.brep) -> ../outputs/*.step
    # clean.py SRC KIND SIDE DST: one part (DST .step is published checked, else a .brep)
    import build
    from pathlib import Path
    jobs = ([(f'final_{k}_{s}.brep', k, s, str(build.OUT / f'TOTEM_alu_{k}_{s}.step')) for s in 'LR' for k in ('top', 'bottom')]
            if sys.argv[1:] == ['--all'] else [tuple(sys.argv[1:5])])
    for src, kind, side, dst in jobs:
        EVENTS.clear()
        s = cq.Shape.importBrep(src) if src.endswith('.brep') else load(src)
        s = max(s.Solids(), key=lambda x: x.Volume())
        keep = load(f'keepout_{side}.step').Solids() if kind == 'bottom' else top_parts(side)
        out, _ = rebuild(s, build.SCREWS[side], kind, name=f'{side} {kind}', keep=keep, side=side)
        if dst.endswith('.step'):
            out.exportBrep(str(W / f'clean_{kind}_{side}.brep'))
            back = build.validate_step(out, Path(dst))
            log('written', dst, 'valid', back.isValid(), 'volume', round(back.Volume(), 2))
            (W / f'clean_{kind}_{side}.log').write_text('\n'.join(EVENTS) + '\n')
        else:
            out.exportBrep(dst)
            log('written', dst)
