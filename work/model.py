"""Parametric model of the TOTEM aluminum case (CadQuery features), made for a 3-axis mill with a
Ø2 mm flat end mill on 3D toolpaths. It never opens the original 3D-print parts: their reference
shapes are curves in model_ref.json (lines, arcs and B-splines, taken once by ref_extract.py);
every other shape is designed here. Clearances come from the build's keep-outs (build.py: the
KiCad board, parts and pads, and the XIAO, each grown by its clearance) cut as the mill makes them
(mill.open_tools). Every face is drawn with lines and arcs (and the outline's B-splines).

Usage: model.py bottom|top|insert|all L|R [--dev]   (--dev: write work/model_KIND_SIDE.step only)
"""
import sys, time, faulthandler, signal
faulthandler.register(signal.SIGUSR1)
sys.path.insert(0, '.')
from geo import *
import shapely.geometry as sg
from shapely.ops import unary_union
import json
import mill, build, feat, clean, curves
from feat import pieces, outer, prism

REF = json.loads((W / 'model_ref.json').read_text())

T0 = time.monotonic()
EVENTS = []


def log(*a):
    s = ' '.join(str(x) for x in a)
    EVENTS.append(s)
    print(f'[{time.monotonic() - T0:7.1f}s] {s}', flush=True)


# ---------------------------------------------------------------------------- parameters
Z_UNDER = -11.4        # bottom's underside
Z_FOOT = -11.0         # feet pockets: 0.4 deep
Z_ROOF = -7.3          # leg-recess roofs
Z_BATT = -9.4          # battery pocket floor
Z_SEAM = build.SEAM_Z0 + build.SEAM_RAISE   # top's skirt: -1.5 (top 12.0 mm: 1/2" plate)
Z_RIM = Z_SEAM - build.SEAM_GAP             # bottom's rim under it: -1.7
Z_PLAT = -(build.C + build.COPPER)   # board plateau: the PCB keep-out's floor (-0.55)
Z_WALL = 4.2           # highest wall top
WALL_GAP = build.NEST_GAP   # top over the bottom's walls (above the board): 0.4
CHAMFER = 0.5          # 45° fillet-chamfer at the foot of the walls, inside
MX = MIRROR_X_SUM      # the right half's outline is the left's mirrored about x = MX / 2

# Back wall (y -49.16..-47.66) of the left bottom: (x0, x1, top). The plain seam runs sit at the
# ledge h; elsewhere the original's wall tops. The top's back wall stops WALL_GAP above.
BACK_WALL_Y = (-49.16, -47.66)
BACK_TOPS_L = [(30.14, 32.06, 2.15), (32.06, 60.26, 1.25), (60.26, 71.8, 2.15),
               (98.8, 101.2, 3.95), (101.2, 118.06, 3.05), (118.06, 128.0, 3.95),
               (128.0, 141.16, 3.05), (141.16, 143.48, 3.95)]
# notches through the back wall, cut from above: (x0, x1, bottom, flank angle from vertical °)
NOTCHES_L = [(62.3, 68.3, 0.13, 30.0),    # power switch
             (121.3, 124.7, 3.095, 0.0)]  # reset button: its plunger (x 121.5..124.5, z 3.295..4.895) 0.2 clear
# Left wall (x 28.64..30.14): (y0, y1, top); the XIAO's USB end is opened (open_xiao_end).
LEFT_WALL_X = (28.64, 30.14)
LEFT_TOPS = [(-72.1, -47.66, Z_WALL)]


def stage(part, what, side):
    """Log a construction stage; a part that is not one valid solid stops the build there."""
    ok = part.isValid() and len(part.Solids()) == 1
    rt = ''
    if '--roundtrip' in sys.argv:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            part.exportStep(f'{d}/p.step')
            back = cq.importers.importStep(f'{d}/p.step').val()
            rt = f', STEP round trip valid {back.isValid()}'
    if '--meshcheck' in sys.argv:     # (debug: meshed as the CAM planner meshes a STEP)
        import planner_mesh
        bad, op = planner_mesh.planner_mesh(part.copy())
        rt += f', planner mesh: {len(bad)} faces not tessellated, {len(op)} open edges' + \
              (f' (first at {np.round(op[0][0], 3)})' if op else '')
    log(side, f'{what}: volume {part.Volume():.2f} mm^3, faces {len(part.Faces())}, valid {ok}{rt}')
    assert ok, (side, what, 'not one valid solid')
    return part


_OUTLINE = {}


def outline(side):
    """The case's outline (the top's and the bottom's), the original's own curves, its inside
    corners rounded R1.05 for the mill (cq fillet2D: lines, arcs and B-splines stay exact).
    -> (curves region, shapely polygon)"""
    if side in _OUTLINE:
        return _OUTLINE[side]
    f = curves.to_face(REF[side]['top']['outline'][0], 0.0)
    poly = curves.to_shapely(REF[side]['top']['outline'])
    concave = []
    for v in f.outerWire().Vertices():
        p = np.array(v.toTuple()[:2])
        near = [e for e in f.outerWire().Edges() if min(np.linalg.norm(np.array(e.startPoint().toTuple()[:2]) - p),
                                                        np.linalg.norm(np.array(e.endPoint().toTuple()[:2]) - p)) < 1e-6]
        q = []
        for e in near:
            t = 0.02 / max(e.Length(), 1e-9)
            a = np.array(e.positionAt(min(t, 0.5)).toTuple()[:2])
            b = np.array(e.positionAt(max(1 - t, 0.5)).toTuple()[:2])
            q.append(a if np.linalg.norm(a - p) < np.linalg.norm(b - p) else b)
        if len(q) == 2 and not poly.contains(sg.Point(*(q[0] + q[1]) / 2)):
            concave.append(v)
    if concave:
        f = f.fillet2D(feat.R, concave)
    # a corner with no room for the fillet (the 1.0 mm front step running into an R0.5 arc): where
    # the outline still differs from what the mill leaves outside it (its closing), a small patch
    # (lines and arcs) is added there
    # a corner with no room for the fillet (the 1.0 mm front step running into an R0.5 arc): where
    # the outline still differs from what the mill leaves outside it (its closing), a small patch
    # (lines and arcs) is added to the prisms there
    region = [curves.from_occ_face(f)]
    pf = curves.to_shapely(region)
    fine = lambda g: g.buffer(feat.R, quad_segs=64).buffer(-feat.R, quad_segs=64)
    patches = [feat.snap(q.buffer(0.05, join_style=2).intersection(fine(pf)))
               for q in pieces(fine(pf).difference(pf)) if q.area > 0.05]
    poly = feat.snap(unary_union([pf] + patches))
    _OUTLINE[side] = (region, poly, patches)
    log(side, f'outline: {len(f.Edges())} edges, {len(concave)} inside corners rounded R{feat.R}, '
              f'{len(patches)} more without room for a fillet rounded by a patch')
    return _OUTLINE[side]


def outline_prism(side, z0, z1):
    """The outline's prism: its own curves (B-splines too), with the corner patches."""
    region, _, patches = outline(side)
    f = curves.to_face(region[0], z0)
    s = cq.Solid.extrudeLinear(f, cq.Vector(0, 0, z1 - z0))
    return feat.fuse(s, prism(unary_union(patches), z0, z1), what='outline patches') if patches else s


def exact_prism(region, z0, z1):
    """A prism of a reference region drawn with its own curves (the outline's B-splines too)."""
    f = curves.to_face(region[0], z0)
    return cq.Solid.extrudeLinear(f, cq.Vector(0, 0, z1 - z0))


def mirror_x(g, side, axis=None):
    import shapely.affinity as sa
    return g if side == 'L' else sa.scale(g, -1, 1, origin=((axis or MX) / 2, 0))


def mx(x, side, axis=None):
    return x if side == 'L' else (axis or MX) - x


# ---------------------------------------------------------------------------- bottom
def bottom(side, top=None):
    ref = REF[side]['bottom']
    _, full, _ = outline(side)
    # the ramp wing: everything beyond the main block's flat side face (x 28.64 on the left)
    x_face = ref['side_face_x']
    beyond = sg.box(-100, -300, x_face, 100) if side == 'L' else sg.box(x_face, -300, 500, 100)
    wing = feat.snap(full.intersection(beyond))
    main = feat.snap(full.difference(beyond))
    # the walls' footprint (back and left walls), inside corners R1.05, on the main block; their
    # outer sides run out past the outline (the walls are cut to the outline's own faces in 3D below)
    boxes = [(mirror_x(sg.box(x0, BACK_WALL_Y[0], x1, BACK_WALL_Y[1] + 1.0), side), zt) for x0, x1, zt in BACK_TOPS_L]
    boxes += [(mirror_x(sg.box(LEFT_WALL_X[0] - 1.0, y0, LEFT_WALL_X[1], y1), side), zt) for y0, y1, zt in LEFT_TOPS]
    wall_out = feat.snap(feat.mill_material(unary_union([b for b, _ in boxes])))
    wall_fp = feat.snap(wall_out.intersection(main))
    # the plateau runs into the walls' ends without a corner the mill can't reach
    plat = feat.snap(feat.mill_material(curves.to_shapely(ref['plateau']).union(wall_fp)).intersection(full))
    recess = curves.to_shapely(ref['leg_recesses'])
    # (fitted to the original's mesh, a leg recess stops a hair short of the outline where the
    # original's is open at the back: a skin under 0.1 mm no mill leaves, so the recess opens through it)
    band = full.difference(recess)
    skin = unary_union([p for p in pieces(band.difference(mill.opening(band, 0.05))) if p.distance(recess) < 1e-3])
    if not skin.is_empty:
        log(side, f'bottom: leg recesses opened through {len(pieces(skin))} skins under 0.1 mm ({skin.area:.3f} mm^2)')
        recess = feat.snap(unary_union([recess, skin, skin.buffer(0.5, quad_segs=8).difference(full)]))
    battery = curves.to_shapely(ref['battery_pocket'])
    feet = [sg.Point(*f['c']).buffer(f['r'], quad_segs=64) for f in ref['feet']]
    log(side, f'bottom outlines: main {main.area:.1f}, wing {wing.area:.1f}, plateau {plat.area:.1f}, '
              f'leg recesses {len(pieces(recess))} ({recess.area:.1f}), battery {battery.area:.1f}, feet {len(feet)} mm^2')
    # one prism over the whole outline and the plateau on it; under the wing (beyond the main
    # block's side face) only above z -8 (the ramp cuts it further)
    # (the plateau's prism starts 0.01 under the rim, so the two overlap; clipped to the exact
    # outline, so no hair of it pokes out past the outline's curves: a 0.01 mm sliver face there
    # breaks meshing, the CAM planner's included)
    clip = outline_prism(side, Z_RIM - 0.02, Z_PLAT + 1)
    plat_s = [s for p in prism(plat, Z_RIM - 0.01, Z_PLAT) for s in p.intersect(clip).Solids()]
    part = feat.fuse(outline_prism(side, Z_UNDER, Z_RIM), plat_s, what='body')
    part = stage(feat.cut(part, prism(beyond, Z_UNDER - 1, -8.0), what='under the wing'), 'body', side)
    part = feat.cut(part, prism(feat.mill_pocket(recess), Z_UNDER - 1, Z_ROOF) +
                    prism(feat.mill_pocket(battery), Z_BATT, 10) +
                    [s for f in feet for s in prism(f, Z_UNDER - 1, Z_FOOT)])
    stage(part, 'leg recesses, battery pocket, feet', side)
    # the leg ramp: the wing's underside is one plane (the original's, fitted away from its
    # 0.32 mm side rails, left out: a flat mill can't run a ramp up beside a wall)
    c, n, rms = np.array(ref['leg_ramp']['point']), np.array(ref['leg_ramp']['normal']), ref['leg_ramp']['rms']
    log(side, f'leg ramp: plane through {np.round(c, 3)} normal {np.round(n, 4)} '
              f'({np.degrees(np.arccos(n[2])):.2f}° from flat; fits the original within {rms:.4f} mm)')
    below = feat.half_space(c, -n).intersect(prism(wing.buffer(0.5).intersection(beyond), -12, 0)[0])
    part = stage(feat.cut(part, [below]), 'leg ramp', side)
    # walls above the plateau (the back and left walls): one block up to the highest top, inside
    # corners R1.05, standing on the main block (no overhang); each lower stretch is then cut down
    # from above to its own top (the left wall owns the corner)
    # (cut to the exact outline in 3D: their outer faces are the outline's own surfaces)
    clip = outline_prism(side, Z_RIM - 0.4, Z_WALL + 0.1)
    walls = [w for p in prism(wall_out.intersection(main.buffer(1.5)), Z_RIM - 0.3, Z_WALL) for w in p.intersect(clip).Solids()]
    # 45° fillet-chamfers at the walls' feet, inside (on the plateau)
    # (each run stops 2 mm short of the inner corner and of the walls' ends, where two chamfers
    # would meet in a corner the mill can't reach, and stays on the plateau)
    ch = []
    runs = [(x0, x1) for x0, x1, _ in BACK_TOPS_L]
    merged = []
    for a, b in sorted(runs):
        if merged and abs(a - merged[-1][1]) < 1e-6:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    for x0, x1 in merged:
        y = BACK_WALL_Y[0]
        tri = sg.Polygon([(y, Z_PLAT - 0.01), (y - CHAMFER, Z_PLAT - 0.01), (y, Z_PLAT + CHAMFER)])
        ch.append(along_x(tri, x0 + 2.0, x1 - 2.0, side))
    for y0, y1, zt in LEFT_TOPS:
        x = LEFT_WALL_X[1]
        tri = sg.Polygon([(x, Z_PLAT - 0.01), (x + CHAMFER, Z_PLAT - 0.01), (x, Z_PLAT + CHAMFER)])
        ch.append(along_y(tri, y0 + 2.0, min(y1, BACK_WALL_Y[0]) - 2.0, side))
    on_plat = prism(plat.buffer(-0.01), Z_PLAT - 1, Z_PLAT + 1)
    ch = [c.intersect(feat.compound(on_plat)) for c in ch]
    ch = [x for c in ch for x in c.Solids() if x.Volume() > 1e-3]
    part = stage(feat.fuse(part, walls + ch), 'walls and chamfers', side)
    lower = []
    for (x0, x1, zt) in BACK_TOPS_L:
        if zt < Z_WALL - 1e-9:
            lower += prism(mirror_x(sg.box(x0, BACK_WALL_Y[0] - 3, x1, BACK_WALL_Y[1] + 3), side), zt, 30)
    part = stage(feat.cut(part, lower), 'wall tops', side)
    # notches through the back wall (power switch, reset button), cut from above
    nt = []
    for x0, x1, zb, ang in NOTCHES_L:
        t = np.tan(np.radians(ang)) * (Z_WALL + 1 - zb)
        prof = sg.Polygon([(x0, zb), (x1, zb), (x1 + t, Z_WALL + 1), (x0 - t, Z_WALL + 1)])
        nt.append(along_y(prof, BACK_WALL_Y[0] - CHAMFER - 0.1, BACK_WALL_Y[1] + 0.1, side, MX_PARTS))
    part = stage(feat.cut(part, nt), 'notches', side)
    log(side, 'bottom: body, ramp, walls, chamfers, notches', round(part.Volume(), 1), 'mm^3')
    # every keep-out (PCB, parts, pads, XIAO) as the mill cuts it from above
    pockets = keepout_pockets('bottom', side, top)
    part = stage(feat.cut(part, pockets), 'keep-out pockets', side)
    # the XIAO's USB end: the left wall in front of the module is opened down to its pocket's floor
    part = stage(feat.cut(part, xiao_end('bottom', side, pockets)), 'XIAO end opened', side)
    # screws: blind Ø1.6 tap-drill holes from the boss top, tapped M2
    holes = []
    for x, y in build.SCREWS[side]:
        holes.append(clean.revolve_cutter(clean.hole_profiles('bottom', Z_UNDER - 1, 10), x, y))
    part = stage(feat.cut(part, holes), 'screw holes', side)
    return stage(as_milled(part, side, 'bottom'), 'as milled', side)


# ---------------------------------------------------------------------------- top
Z_TOP = 10.5           # top face
TOP_NOTCHES_L = [(60.6, 70.0, 5.5),     # power switch: (x0, x1, roof): over the bottom's V-notch
                 (121.3, 124.7, 5.095)]  # reset button: its plunger runs out through it, 0.2 clear
MX_PARTS = 307.96      # the parts (and the notches for them) mirror about the board's axis (the screws')


def top(side, bottom_part=None):
    """The top: the original's air in each band between its flat faces, reached from below or
    from above (nested: what neither side reaches stays metal, the logo's strokes too), the walls
    over the bottom's designed, the build's keep-outs as the mill cuts them from below, the XIAO
    pocket and its opened end, countersunk screw holes."""
    ref = REF[side]['top']
    if '--from-regions' in sys.argv:   # (rerun from the column regions)
        import pickle
        return top_from_regions(side, *pickle.loads((W / f'regions_top_{side}.pkl').read_bytes()))
    if '--from-columns' in sys.argv:   # (rerun the steps after the column model alone)
        return top_after_columns(side, cq.Shape.importBrep(str(W / f'columns_top_{side}.brep')))
    # the walls over the bottom's back and left walls are designed (below): kept out of the air
    walls = [mirror_x(sg.box(x0, BACK_WALL_Y[0], x1, BACK_WALL_Y[1] + 1.0), side) for x0, x1, _ in BACK_TOPS_L]
    walls += [mirror_x(sg.box(LEFT_WALL_X[0] - 1.0, y0, LEFT_WALL_X[1], y1), side) for y0, y1, _ in LEFT_TOPS]
    walls = unary_union(walls)
    screws = unary_union([sg.Point(x, y).buffer(clean.DISC_R, quad_segs=mill.QS) for x, y in build.SCREWS[side]])
    # the air of each band joined to the outside (where the original's air is open to it, the mill
    # cuts round the corner from outside: no fin left in the outline's corners), then clipped back
    _, out_poly0, _ = outline(side)
    # (outside the original's outline: the outline's corner fillets are only kept where metal
    # reaches the corner)
    orig_poly = feat.snap(curves.to_shapely(ref['outline']))
    outside = sg.box(*out_poly0.buffer(5).bounds).difference(orig_poly)
    bands = [(b['z0'], b['z1'], feat.snap(curves.to_shapely(b['air']).union(outside).difference(walls).difference(screws)))
             for b in ref['air_bands']]
    # more air reached from below, designed: the walls over the bottom's (the top stops WALL_GAP over
    # the bottom's wall tops), the notches, and the room the bottom needs as the mill makes it (the
    # bottom grown by the seam gap: the R1.05 corners it can't cut leave small fillets where its walls
    # meet). Each as the mill cuts a pocket (dogbones, into the top only), joined to the original's
    # air in the column model below, so no sliver is left between them.
    extra = []
    for x0, x1, zt in BACK_TOPS_L:
        extra.append((mirror_x(sg.box(x0, BACK_WALL_Y[0] - 0.01, x1, BACK_WALL_Y[1] + 1.0), side), zt + WALL_GAP))
    for y0, y1, zt in LEFT_TOPS:
        extra.append((mirror_x(sg.box(LEFT_WALL_X[0] - 1.0, y0, LEFT_WALL_X[1] + 0.01, y1), side), zt + WALL_GAP))
    for x0, x1, zr in TOP_NOTCHES_L:
        extra.append((mirror_x(sg.box(x0, BACK_WALL_Y[0] - 0.6, x1, BACK_WALL_Y[1] + 1.0), side, MX_PARTS), zr))
    # where a wall ends free (the left wall's front end, the back wall's end by the right edge), the
    # room round it wraps a sharp corner a Ø2 mill can't reach from below: a pocket of the mill's
    # own size (R1.05) round the wall's inner end corner, up to the room's height, lets it
    ends = [((LEFT_WALL_X[1], LEFT_TOPS[0][0]), LEFT_TOPS[0][2]), ((BACK_TOPS_L[-1][1], BACK_WALL_Y[0]), BACK_TOPS_L[-1][2])]
    extra += [(mirror_x(sg.Point(*p).buffer(1.05, quad_segs=mill.QS), side), zt + build.SEAM_GAP) for p, zt in ends]
    extra = [(feat.mill_pocket(g), z) for g, z in extra]
    if bottom_part is not None:
        entries = mill.grown_entries(bottom_part, build.SEAM_GAP, 'below', Z_RIM - 0.01, Z_WALL + 0.01)
        _, layers = mill.open_tools([], 'below', -30.0, log=lambda *a: log(side, 'top: room for the bottom:', *a),
                                    extra_entries=entries)
        extra += [(feat.snap(poly), z) for z, poly in layers]
    cuts = sorted(set(round(z, 6) for _, z in extra if Z_SEAM + 1e-6 < z < Z_TOP - 1e-6))
    split = []
    for z0, z1, g in bands:
        zs = [z0] + [z for z in cuts if z0 + 1e-6 < z < z1 - 1e-6] + [z1]
        split += [(a, b, g) for a, b in zip(zs[:-1], zs[1:])]
    log(side, f'top: {len(bands)} bands of the original, {len(extra)} designed pockets from below -> {len(split)} bands')
    bands = split
    # reached from below: the air of every band under it too; from above: of every band over it
    def opened(g):
        return feat.snap(mill.opening(g, feat.R))
    below, A = [], None
    for z0, z1, g in bands:
        A = g if A is None else A.intersection(g)
        A = opened(A)
        below.append(A)
    above, A = [], None
    for z0, z1, g in reversed(bands):
        A = g if A is None else A.intersection(g)
        A = opened(A)
        above.append(A)
    above = above[::-1]
    for g, zt in extra:              # a pocket from below reaches every band under its top
        for k, (z0, z1, _) in enumerate(bands):
            if z1 <= zt + 1e-6:
                below[k] = feat.snap(below[k].union(g))
    below = [feat.snap(g.intersection(out_poly0)) for g in below]
    above = [feat.snap(g.intersection(out_poly0)) for g in above]
    # every column of metal is one interval: from the highest band reached from below to the
    # lowest band reached from above. The plan splits into regions of constant (bottom, top):
    # clean.py's column model, made into one solid by clean.make_solid (outlines fitted together
    # with lines and arcs, one prism per region)
    z0s = [b0 for b0, _, _ in bands]
    z1s = [b1 for _, b1, _ in bands]
    _, out_poly, _ = outline(side)
    parts_b = [(out_poly.difference(below[0]), Z_SEAM)]                # no air from below
    for k in range(len(bands)):
        nxt = below[k + 1] if k + 1 < len(bands) else sg.Polygon()
        parts_b.append((below[k].difference(nxt), z1s[k]))
    parts_t = [(out_poly.difference(above[-1]), Z_TOP)]               # no air from above
    for k in range(len(bands)):
        prv = above[k - 1] if k > 0 else sg.Polygon()
        parts_t.append((above[k].difference(prv), z0s[k]))
    L = sorted(set([Z_SEAM, Z_TOP] + z0s + z1s))
    idx = {round(z, 6): i for i, z in enumerate(L)}
    P, Lb = [], []
    for gb, zb in parts_b:
        if gb.is_empty:
            continue
        for gt, zt in parts_t:
            if zt <= zb + 1e-6 or gt.is_empty:
                continue
            for q in pieces(feat.snap(gb.intersection(gt))):
                if q.area > 1e-6:
                    P.append(q); Lb.append((idx[round(zb, 6)], idx[round(zt, 6)] - 1))
    log(side, f'top: {len(bands)} bands of the original -> {len(P)} regions of constant bottom and top')
    L = np.array(L)
    P, Lb = clean.tidy_regions(P, Lb, L, log=log, name=f'{side} top')
    return top_from_regions(side, L, P, Lb, screws)


def mill_fills(L, P, Lb, spots):
    """Spots to fill in the column model (clean.fill_spots), grown to what the mill really leaves:
    at each spot's height, from the side the mill comes, the air (with the spots filled) less what a
    Ø2 tool sweeps of it (opening by R1.02); each spot takes the pieces of that next to it. Filling
    a spot alone leaves a hair beside it, found again the next round."""
    cols = [[float(L[b]), float(L[t + 1])] for b, t in Lb]
    allp = unary_union(P)
    frame = sg.box(*allp.buffer(5).bounds)
    out = []
    groups = {}
    for sp in spots:
        groups.setdefault((sp[1], round(sp[2], 6)), []).append(sp)
    for (kind, h), sps in groups.items():
        if kind == 'top':     # from above: blocked by any metal at or over the height
            z = h - 1e-4
            metal = unary_union([q for q, c in zip(P, cols) if c[1] >= z])
        else:                 # from below: by any metal at or under it
            z = h + 1e-4
            metal = unary_union([q for q, c in zip(P, cols) if c[0] <= z])
        air = frame.difference(metal).difference(unary_union([p for p, _, _ in sps]))
        left = air.difference(air.buffer(-1.02, quad_segs=32).buffer(1.02, quad_segs=32))
        lp = [g for g in pieces(left) if g.area > 1e-6]
        for poly, _, hh in sps:
            near = [g for g in lp if g.intersects(poly.buffer(0.1))]
            out.append((feat.snap(unary_union(near + [poly])), kind, hh))
    return out


def top_from_regions(side, L, P, Lb, screws):
    """The top from its column regions (cached in regions_top_SIDE.pkl: model.py top SIDE
    --from-regions starts here): ledges, the mill's fills, the solid, then top_after_columns."""
    import pickle
    (W / f'regions_top_{side}.pkl').write_bytes(pickle.dumps((L, P, Lb, screws)))
    # the floors the keep-outs would leave too thin (as clean.py does them: ledges where the diode
    # pockets' rounded ends come within 1 mm of a keycap-well floor): found on the columns with the
    # keep-out pockets and the XIAO pocket cut from below, filled here, before they are cut. (Not
    # clean.py's keycap-well walls: raised to the top face over the plate, with a switch pocket cut
    # under it from below, a fill leaves hairs neither side's mill reaches.)
    foot, _, xz1 = clean.xiao_box(side)
    L2, P2, Lb2 = cut_from_below(L, P, Lb, keepout_layers('top', side) + [(xz1, foot)])
    nm = f'{side} top'
    spots = clean.raise_floors(L2, P2, Lb2, clean.top_parts(side), foot=foot, log=log, name=nm, spots_only=True)
    if spots:
        spots = mill_fills(L, P, Lb, spots)
        L, P, Lb = clean.fill_spots(L, P, Lb, spots, log=log, name=nm, what='ledge')
        P, Lb = clean.tidy_regions(P, Lb, L, log=log, name=nm, fills=unary_union([sp[0] for sp in spots]))
    # what the mill can't reach (where a region merge left a hair of metal hanging into a pocket) is
    # filled to the height the mill leaves there, as clean.py does (the keep-outs are cut after)
    for rnd in range(8):
        part = clean.make_solid(L, P, Lb, [], 'top', name=f'{side} top')
        spots = clean.checker_spots(part.copy(), screws=build.SCREWS[side])
        log(side, f'top column model, round {rnd + 1}: {len(spots)} spots the mill cannot cut')
        if not spots:
            break
        spots = mill_fills(L, P, Lb, spots)
        L, P, Lb = clean.fill_spots(L, P, Lb, spots, log=log, name=f'{side} top')
        P, Lb = clean.tidy_regions(P, Lb, L, log=log, name=f'{side} top', fills=unary_union([sp[0] for sp in spots]))
    part = stage(part, 'original air and designed pockets, from below and above (column model)', side)
    part.exportBrep(str(W / f'columns_top_{side}.brep'))
    if '--columns' in sys.argv:          # (debug: the column model alone)
        part.exportStep(f'/tmp/columns_top_{side}.step')
        import pickle
        pickle.dump((L, P, Lb), open(f'/tmp/columns_top_{side}.pkl', 'wb'))
        raise SystemExit(0)
    return top_after_columns(side, part)


def top_after_columns(side, part):
    """The top's steps after its column model: keep-outs, the XIAO pocket and end, the holes, as milled."""
    # keep-outs (PCB, parts, pads, XIAO, switch cut-outs, window) as the mill cuts them from below
    pockets = keepout_pockets('top', side, None)
    part = stage(feat.cut(part, pockets, what='keep-outs'), 'keep-out pockets', side)
    # the XIAO pocket 0.52 mm all round (the insert's glue gap under the roof) and its opened end
    foot, z0, z1 = clean.xiao_box(side)
    xp = prism(foot, Z_SEAM - 1, z1)
    part = stage(feat.cut(part, xp, what='XIAO pocket'), 'XIAO pocket', side)
    part = stage(feat.cut(part, xiao_end('top', side, pockets + xp)), 'XIAO end opened', side)
    holes = [clean.revolve_cutter(clean.hole_profiles('top', Z_SEAM - 1, Z_TOP), x, y) for x, y in build.SCREWS[side]]
    part = stage(feat.cut(part, holes, what='screw holes'), 'countersunk screw holes', side)
    # (kept, so the last step can be rerun alone: model.py milled-top SIDE)
    part.exportBrep(str(W / f'pre_milled_top_{side}.brep'))
    return stage(as_milled(part, side, 'top'), 'as milled', side)


def as_milled(part, side, what):
    """The last step of each part: where the checker (machinable.py, Ø2 flat end mill) still finds a
    speck the mill can't cut (a hair where two outlines nearly meet), the metal is filled up to the
    height the mill leaves there: the model is what the machine makes. At the speck's height, the
    air the tool can't sweep (the air less its opening by the tool's radius) is filled whole near the
    speck, up to the metal over it (under it, from above): the fill's edges are the tool's own arcs,
    so it leaves no new hair beside it."""
    bb = part.BoundingBox()
    frame = sg.box(bb.xmin - 5, bb.ymin - 5, bb.xmax + 5, bb.ymax + 5)
    for rnd in range(7):
        # (checked on a copy: meshing a shape stores the mesh on it and can loosen its tolerances)
        spots = clean.checker_spots(part.copy(), screws=build.SCREWS[side])
        if not spots:
            return part
        if rnd == 6:
            part.exportBrep(f'/tmp/asmilled_fail_{what}_{side}.brep')
            raise AssertionError(f'{side} {what}: specks left after 6 rounds of filling '
                                 f'(part in /tmp/asmilled_fail_{what}_{side}.brep)')
        m = mill.mesh_of(part.copy(), 0.002)
        fills, done = [], sg.Polygon()
        for poly, kind, h in spots:
            if done.contains(poly):
                continue
            # the air at the speck's height, just inside the side the mill comes from, and what the
            # tool (R1.0, the checker's, and 0.02 to spare) can't sweep of it near the speck
            z = h + 0.005 if kind == 'bottom' else h - 0.005
            air = frame.difference(mill.section(m, z))
            reach = air.buffer(-1.02, quad_segs=32).buffer(1.02, quad_segs=32)
            left = air.difference(reach)
            near = unary_union([g for g in pieces(left) if g.intersects(poly.buffer(0.1))] + [poly])
            near = near.buffer(0.01, quad_segs=4)
            done = done.union(near)
            # up to the first metal over the fill (down to the last under it), never past the part
            x0, y0, x1, y1 = near.bounds
            X, Y = np.meshgrid(np.arange(x0, x1 + 0.025, 0.025), np.arange(y0, y1 + 0.025, 0.025))
            inside = [(x, y) for x, y in zip(X.ravel(), Y.ravel()) if near.contains(sg.Point(x, y))] or \
                     [tuple(near.representative_point().coords[0])]
            o = np.array([[x, y, -50.0] for x, y in inside])
            loc, idx, _ = m.ray.intersects_location(o, np.tile([0, 0, 1.0], (len(o), 1)), multiple_hits=True)
            cols = [sorted(loc[idx == i, 2]) for i in range(len(o))]
            if kind == 'bottom':
                firsts = [z for z in (next((z for z in c if z > h + 1e-6), None) for c in cols) if z is not None]
                if firsts:
                    fills += prism(near, h, min(max(firsts) + 0.05, bb.zmax))
            else:
                lasts = [z for z in (next((z for z in reversed(c) if z < h - 1e-6), None) for c in cols) if z is not None]
                if lasts:
                    fills += prism(near, max(min(lasts) - 0.05, bb.zmin), h)
            log(side, f'{what}: speck ({kind}) at {np.round(poly.centroid.coords[0], 2)}, {poly.area:.3f} mm^2: '
                      f'{near.area:.3f} mm^2 the tool can\'t sweep there filled from {h:.3f}')
        part = feat.fuse(part, fills, what='specks filled', overlapping=True)
        part = stage(part, f'{what}: specks filled, round {rnd + 1}', side)
    return part


def window_parts(side):
    """The window over the XIAO and the wood insert's plug and flange (build.window_parts), from
    the roof's heights in model_ref.json."""
    w = REF[side]['top']['window']
    roof_z0, top_z = w['roof_z0'], w['top_z']
    (x, y), a = build.XIAO[side]
    def local(x0, x1, y0, y1, z0, z1, r):
        b = cq.Workplane().box(x1 - x0, y1 - y0, z1 - z0).edges('|Z').fillet(r) \
            .translate(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)).val()
        return b.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), a).translate(cq.Vector(x, y, 0))
    W_X, W_Y = (-7.0, 7.0), (-10.3, 8.2)       # to the far end; the USB-C end (+y) stays closed
    hole = local(*W_X, *W_Y, roof_z0 - 1, top_z + 1, 1.5)
    plug = local(W_X[0] + 0.1, W_X[1] - 0.1, W_Y[0] + 0.1, W_Y[1] - 0.1, roof_z0, top_z, 1.4)
    flange_box = local(W_X[0] - 1.5, W_X[1] + 1.5, W_Y[0] - 1.5, W_Y[1] + 1.5, roof_z0 - 1.5, roof_z0, 1.0)
    return hole, plug, flange_box, roof_z0, top_z


def insert(side, top_part):
    """The wood window insert over the XIAO, for this top (build.window_insert)."""
    hole, plug, flange_box, roof_z0, top_z = window_parts(side)
    return build.window_insert(side, top_part, plug, flange_box, roof_z0, top_z)


def xiao_end(kind, side, pockets):
    """The wall in front of the XIAO's USB end, opened over the module's end: in the bottom from
    the XIAO pocket's floor up, in the top from its roof down (the side opening is the module's
    end, split by the seam)."""
    import clean
    foot, z0, z1 = clean.xiao_box(side)
    (cx, cy), _ = build.XIAO[side]
    fx0, fy0, fx1, fy1 = foot.bounds
    wall = mirror_x(sg.box(LEFT_WALL_X[0] - 1, fy0, LEFT_WALL_X[1] + 0.01, fy1), side)
    zone = sg.box(min(wall.bounds[0], fx0), fy0, max(wall.bounds[2], fx1), fy1).intersection(
        sg.box(wall.bounds[0], -300, wall.bounds[2], 100))
    if kind == 'bottom':
        floors = [q.BoundingBox().zmin for q in pockets if (lambda b: b.xmin < cx < b.xmax and b.ymin < cy < b.ymax
                  and z0 - 0.2 < b.zmin < z0 + 0.1)(q.BoundingBox())]
        zb = min(floors) if floors else z0
        log(side, f'XIAO end: bottom opened from its pocket floor z {zb:.3f}')
        return prism(zone, zb, 20)
    roofs = [q.BoundingBox().zmax for q in pockets if (lambda b: b.xmin < cx < b.xmax and b.ymin < cy < b.ymax
             and z1 - 0.1 < b.zmax < z1 + 0.2)(q.BoundingBox())]
    zt = max(roofs) if roofs else z1
    log(side, f'XIAO end: top opened up to its pocket roof z {zt:.3f}')
    return prism(zone, -20, zt)


def along_x(prof_yz, x0, x1, side):
    """A (y, z) profile swept along x from x0 to x1 (mirrored for the right half)."""
    a, b = sorted((mx(x0, side), mx(x1, side)))
    f = cq.Face.makeFromWires(cq.Wire.makePolygon([cq.Vector(a, y, z) for y, z in prof_yz.exterior.coords[:-1]], close=True))
    return cq.Solid.extrudeLinear(f, cq.Vector(b - a, 0, 0))


def along_y(prof_xz, y0, y1, side, axis=None):
    """An (x, z) profile (left-half x) swept along y from y0 to y1."""
    f = cq.Face.makeFromWires(cq.Wire.makePolygon([cq.Vector(mx(x, side, axis), y0, z) for x, z in prof_xz.exterior.coords[:-1]], close=True))
    return cq.Solid.extrudeLinear(f, cq.Vector(0, y1 - y0, 0))


def along_y_xz(prof_xz, y0, y1, side):
    return along_y(prof_xz, y0, y1, side)


def keepout_layers(kind, side):
    """The build's keep-outs as the Ø2 mill cuts them (mill.open_tools: dogbones, run out to the
    side they are cut from): [(z, region)], the region cut from that side up to (down to) z,
    cached per side in pockets_KIND_SIDE.pkl."""
    import pickle
    cache = W / f'pockets_{kind}_{side}.pkl'
    if cache.exists() and '--fresh' not in sys.argv:
        return pickle.loads(cache.read_bytes())
    tools = load(f'keepout_{side}.step').Solids()
    lg = lambda *a: log(side, kind, *a)
    if kind == 'bottom':
        # (the top's room over the bottom is designed: wall seams WALL_GAP, skirt seam SEAM_GAP;
        # verify.py and seam_machined.py check it)
        _, layers = mill.open_tools(tools, 'above', 30.0, log=lg)
    else:
        hole = window_parts(side)[0]
        squares = [mill.prism(sg.Polygon(q), build.LEDGE[0], build.LEDGE[1]) for q in REF[side]['top']['switch_cutouts']]
        k_pcb = tools[0]
        boss = unary_union([sg.Point(x, y).buffer(build.PAD_R, quad_segs=mill.QS) for x, y in build.SCREWS[side]])
        under = [k_pcb.intersect(cq.Solid.makeCylinder(build.PAD_R + 0.01, 30 + build.PCB_TOP, cq.Vector(x, y, -30)))
                 for x, y in build.SCREWS[side]]
        under = [b for b in under if b.Solids()]
        _, layers = mill.open_tools(tools + under + squares + [hole], 'below', -30.0, log=lg,
                                    exclude=lambda z: boss if z > build.PCB_TOP + 1e-3 else sg.Polygon())
    cache.write_bytes(pickle.dumps(layers))
    return layers


def keepout_pockets(kind, side, other):
    """The keep-out layers (keepout_layers) as prisms drawn with lines and arcs, cached per side in
    pockets_KIND_SIDE.brep."""
    cache = W / f'pockets_{kind}_{side}.brep'
    if cache.exists() and '--fresh' not in sys.argv:
        return cq.Shape.importBrep(str(cache)).Solids()
    layers = keepout_layers(kind, side)
    cut_side, zfar = ('above', 30.0) if kind == 'bottom' else ('below', -30.0)
    items = []
    for k, (z, poly) in enumerate(layers):
        z_next = layers[k + 1][0] if k + 1 < len(layers) else zfar
        lo, hi = (z_next, z) if cut_side == 'below' else (z, z_next)
        items.append((poly, lo, hi))
    prisms = feat.prisms(items)
    cq.Compound.makeCompound(prisms).exportBrep(str(cache))
    return prisms


def cut_from_below(L, P, Lb, layers):
    """The columns (L, P, Lb) with pockets cut from below: [(z, region)], each region cut up to z."""
    cols = [[float(L[b]), float(L[t + 1])] for b, t in Lb]
    layers = sorted(layers, key=lambda l: -l[0])
    nP, nc = [], []
    for q, (b, t) in zip(P, cols):
        rest = q
        for z, poly in layers:
            if z <= b + 1e-6 or rest.is_empty:
                break
            if not rest.intersects(poly):
                continue
            if z < t - 1e-6:
                nP += [g for g in pieces(rest.intersection(poly)) if g.area > 1e-6]
                nc += [[z, t]] * (len(nP) - len(nc))
            rest = rest.difference(poly)
        for g in pieces(rest):
            if g.area > 1e-6:
                nP.append(g); nc.append([b, t])
    L2 = np.unique(np.r_[L, [z for c in nc for z in c]])
    idx = {float(z): k for k, z in enumerate(L2)}
    return L2, nP, [(idx[float(zb)], idx[float(zt)] - 1) for zb, zt in nc]


def unified(part, name):
    """The part with its coplanar (and co-cylindrical) neighbouring faces merged into one: no seam
    left where two features' faces meet in one plane (a CAM program picks a face to drill the holes
    in it: a seam ring round a hole hides it). Checked: one valid solid, the same volume."""
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    u = ShapeUpgrade_UnifySameDomain(part.wrapped, True, True, True)
    u.SetLinearTolerance(1e-5); u.SetAngularTolerance(1e-7)
    u.Build()
    out = cq.Shape.cast(u.Shape())
    sols = out.Solids()
    assert len(sols) == 1 and sols[0].isValid() and abs(sols[0].Volume() - part.Volume()) < 1e-3, (name, 'unify')
    log(name, f'faces merged where coplanar: {len(part.Faces())} -> {len(sols[0].Faces())}')
    return sols[0]


def publish(part, name):
    part = unified(part, name)
    back = build.validate_step(part, W / name) if '--dev' in sys.argv else build.validate_step(part, build.OUT / name)
    log('written', name, 'valid', back.isValid(), 'volume', round(back.Volume(), 2))
    return back


if __name__ == '__main__':
    # model.py top|bottom|all L|R|LR [--dev]: --dev writes work/model_*.step, else ../outputs/
    kind, sides = sys.argv[1], sys.argv[2]
    dev = '--dev' in sys.argv
    if kind == 'milled-top':   # the top's last step alone, from pre_milled_top_SIDE.brep
        for side in sides:
            part = cq.Shape.importBrep(str(W / f'pre_milled_top_{side}.brep'))
            t = publish(stage(as_milled(part, side, 'top'), 'as milled', side),
                        f'model_top_{side}.step' if dev else f'TOTEM_alu_top_{side}.step')
            publish(insert(side, t), f'model_insert_{side}.step' if dev else f'TOTEM_wood_window_insert_{side}.step')
        raise SystemExit(0)
    for side in sides:
        EVENTS.clear()
        # the bottom first: the top makes room for it
        b = None
        if kind in ('bottom', 'all'):
            b = publish(bottom(side), f'model_bottom_{side}.step' if dev else f'TOTEM_alu_bottom_{side}.step')
        if kind in ('top', 'all'):
            if b is None:
                b = load(f'model_bottom_{side}.step' if dev else f'../outputs/TOTEM_alu_bottom_{side}.step')
            t = publish(top(side, b), f'model_top_{side}.step' if dev else f'TOTEM_alu_top_{side}.step')
            publish(insert(side, t), f'model_insert_{side}.step' if dev else f'TOTEM_wood_window_insert_{side}.step')
        (W / f'model_{kind}_{side}.log').write_text('\n'.join(EVENTS) + '\n')
