"""Take the reference shapes out of the original 3D-print parts (orig/) once, as curves (lines and
arcs, curves.py), into model_ref.json. model.py builds the aluminum parts from that file only.

Usage: ref_extract.py          (both halves; ~5 min)
"""
import sys, json, time
sys.path.insert(0, '.')
from geo import *
import shapely.geometry as sg
from shapely.ops import unary_union
import mill, build, feat, curves
from feat import pieces, outer

T0 = time.monotonic()


def log(*a):
    print(f'[{time.monotonic() - T0:6.1f}s]', *a, flush=True)


def region(g, mesh=False):
    """A shapely region -> curves. From a mesh section (the original bottom is a triangle mesh),
    the arcs' facets sag up to 0.1 mm from their chords."""
    return curves.from_shapely(feat.snap(g), 0.01 if mesh else curves.FIT_TOL, 0.1 if mesh else 0.012)


def exact_region(faces):
    return [curves.from_occ_face(f) for f in faces]


def bottom_refs(side, outline):
    ref = feat.Ref(f'orig/TOTEM_tenting_live_bottom_{side}.step')
    out = {}
    # the outline is the top's (exact; the bottom's mesh follows it within 0.4 mm, less 0.4 mm at
    # the back where the original made room for the top's tongue: the walls are now stacked), and
    # the plateau the board sits over
    out['outline'] = outline
    full = curves.to_shapely(outline)
    out['plateau'] = region(outer(ref.section(-1.0)), mesh=True)
    # the main block's flat side face: beyond it hangs the leg-ramp wing
    s10 = ref.section(-10.0)
    x_face = s10.bounds[0] if side == 'L' else s10.bounds[2]
    out['side_face_x'] = round(x_face, 4)
    beyond = sg.box(-100, -300, x_face, 100) if side == 'L' else sg.box(x_face, -300, 500, 100)
    # under the recess roofs: leg recesses (open to the underside) and the battery pocket (floor)
    recess, battery = [], []
    for p in pieces(full.difference(beyond).difference(ref.section(-9.0))):
        q = p.representative_point()
        col = ref.column(q.x, q.y)
        if p.area > 100:   # the old screw counterbores and outline slivers stay solid
            (battery if col and min(col) < -9.0 else recess).append(p)
    out['leg_recesses'] = region(feat.clean2d(unary_union(recess), 0.05, 5.0), mesh=True)
    out['battery_pocket'] = region(feat.clean2d(unary_union(battery), 0.05, 5.0), mesh=True)
    # feet: the round pockets in the underside
    feet = []
    for p in pieces(full.difference(ref.section(-11.2))):
        d = p.minimum_rotated_rectangle.length / 4
        if 50 < p.area < 80 and p.area / (np.pi * (d / 2) ** 2) > 0.8:
            c = p.centroid
            feet.append({'c': [round(c.x, 4), round(c.y, 4)], 'r': round(float(np.sqrt(p.area / np.pi)), 4)})
    out['feet'] = feet
    # the leg ramp: the wing's underside, one plane (fitted away from its 0.32 mm side rails)
    core = full.intersection(beyond).buffer(-1.6)
    xs, ys = np.meshgrid(np.arange(*core.bounds[0::2], 0.5), np.arange(*core.bounds[1::2], 0.5))
    pts = []
    for x, y in zip(xs.ravel(), ys.ravel()):
        if core.contains(sg.Point(x, y)):
            col = ref.column(x, y)
            if col:
                pts.append((x, y, col[-1]))
    c, n, rms = feat.fit_plane(np.array(pts))
    out['leg_ramp'] = {'point': c.tolist(), 'normal': n.tolist(), 'rms': rms, 'points': len(pts)}
    log(side, 'bottom: outline', round(full.area, 1), 'recesses', len(recess), 'feet', len(feet),
        'ramp', np.round(n, 4), f'{np.degrees(np.arccos(n[2])):.2f}°, rms {rms:.4f}')
    return out


def top_refs(side):
    ref = feat.Ref(f'orig/TOTEM_case_ble_top_{side}_V.08.step')
    out = {}
    # the outline over all heights, exact (lines, arcs and the front's B-splines)
    of = curves.exact_outline(ref.shape, (-1.0, 0.5, 2.0, 3.0, 5.0, 9.5, 10.2))
    out['outline'] = exact_region([of])
    outline = curves.to_shapely(out['outline'])
    z_seam = build.SEAM_Z0 + build.SEAM_RAISE
    L = [z_seam] + [float(z) for z in mill.levels(ref.mesh) if z_seam + 0.01 < z < 10.49] + [10.5]
    out['levels'] = L
    # the air in each band between the original's flat faces: the outline less its exact section
    bands = []
    for a, b in zip(L[:-1], L[1:]):
        air = curves.face_cut(of, curves.exact_sections(ref.shape, (a + b) / 2))
        bands.append({'z0': a, 'z1': b, 'air': exact_region(air)})
    out['air_bands'] = bands
    # the switch cut-outs through the clip ledge (13.8 mm squares) and the window's heights
    orig = ref.shape
    squares = []
    for q in build.switch_cutouts(orig.intersect(build.box(-50, 450, -300, 50, z_seam, 50))):
        base = min(q.Faces(), key=lambda f: f.Center().z)
        squares.append([[round(v.X, 5), round(v.Y, 5)] for v in base.outerWire().Vertices()])
    out['switch_cutouts'] = squares
    _, _, _, roof_z0, top_z = build.window_parts(side, orig)
    out['window'] = {'roof_z0': roof_z0, 'top_z': top_z}
    log(side, 'top: outline', round(outline.area, 1), 'bands', len(bands), 'switch cut-outs', len(out['switch_cutouts']),
        'window roof', round(roof_z0, 3))
    return out


if __name__ == '__main__':
    refs = {'about': 'Reference shapes of the original TOTEM 3D-print case (work/orig/), taken by ref_extract.py as curves '
                     '(curves.py): from the original top (an exact B-rep) its own lines, arcs and B-splines; from the '
                     'original bottom (a triangle mesh) lines and arcs fitted to its facets. Units mm; the PCB bottom '
                     'face is z = 0.'}
    for side in 'LR':
        t = top_refs(side)
        refs[side] = {'bottom': bottom_refs(side, t['outline']), 'top': t}
    (W / 'model_ref.json').write_text(json.dumps(curves.round_floats(refs), indent=1) + '\n')
    log('written model_ref.json', round((W / 'model_ref.json').stat().st_size / 1e6, 2), 'MB')
