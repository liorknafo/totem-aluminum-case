"""Meshes of the final parts, the PCB and its parts, packed for the 3D viewer (view_data.json).

Case parts: vertices quantized to uint16 over the scene box (byte planes), indices delta/zigzag
(byte planes), zlib, base64. Switches and diodes: one model each plus a placement per footprint.
PCB: outline and larger holes, extruded in the viewer."""
import sys, json, base64, zlib, re
sys.path.insert(0, '.')
from geo import *
import build
from common import placed

Z_SCALE = build.PCB_TOP / build.KICAD_TOP


def tess(shape, tol=0.05):
    v, f = shape.tessellate(tol, 0.5)
    return np.array([p.toTuple() for p in v], float), np.array(f, np.int64).reshape(-1, 3)


def merge(meshes):
    V, F, n = [], [], 0
    for v, f in meshes:
        V.append(v); F.append(f + n); n += len(v)
    return np.concatenate(V), np.concatenate(F)


def footprints():
    t = open(W / '../src/totem_0_3.kicad_pcb').read()
    out = {}
    for b in t.split('\n  (footprint ')[1:]:
        r = re.search(r'reference "([^"]+)"', b)
        x, y, *a = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', b).groups()
        out[r.group(1)] = (float(x), -float(y), float(a[0] or 0))
    return out


def model(parts, ref, fp):
    """The part's solids moved to its footprint's own frame."""
    x, y, a = fp[ref]
    meshes = []
    for s in [s for n, shp in parts if n == ref for s in shp.Solids()]:
        if s.BoundingBox().zmin > 0.75:
            s = build.lift(s)
        s = s.translate(cq.Vector(-x, -y, 0)).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), -a)
        meshes.append(tess(s, 0.08))
    return merge(meshes)


def placements(parts, fp, prefix, ref_mesh):
    """[x, y, angle] per footprint of this kind, checked against the part's own box."""
    v0 = ref_mesh[0]
    out = {'L': [], 'R': []}
    for name in sorted({n for n, _ in parts if n.startswith(prefix)}):
        shp = cq.Compound.makeCompound([s for n, sh in parts if n == name for s in sh.Solids()])
        x, y, a = fp[name]
        side = 'L' if x < 150 else 'R'
        c, s_ = np.cos(np.radians(a)), np.sin(np.radians(a))
        p = v0[:, :2] @ np.array([[c, s_], [-s_, c]]) + (x, y)
        bb = shp.BoundingBox()
        err = max(abs(p[:, 0].min() - bb.xmin), abs(p[:, 0].max() - bb.xmax), abs(p[:, 1].min() - bb.ymin), abs(p[:, 1].max() - bb.ymax))
        assert err < 0.05, (name, err)
        dx = build.R_SHIFT if side == 'R' else 0
        out[side].append([round(x + dx, 4), round(y, 4), a])
    return out


def board_outline(side):
    """Board bottom face: outline ring, round holes as [x, y, r], other holes as rings (holes under
    2 mm² dropped)."""
    pcb = build.pcb_solid(side)
    f = max((f for f in pcb.Faces() if f.geomType() == 'PLANE' and abs(f.Center().z) < 1e-3), key=lambda f: f.Area())
    g = build.face_region(f).simplify(0.01)
    circles, rings = [], []
    for r in g.interiors:
        p = np.array(r.coords)[:-1]
        if sg_area(p) < 2:
            continue
        c = p.mean(0); d = np.linalg.norm(p - c, axis=1)
        if d.std() < 0.02:
            circles.append(np.round([*c, d.mean()], 3).tolist())
        else:
            rings.append(np.round(p, 2).ravel().tolist())
    return {'outline': np.round(np.array(g.exterior.coords)[:-1], 2).ravel().tolist(), 'circles': circles, 'rings': rings}


def sg_area(ring):
    import shapely.geometry as sg
    return sg.Polygon(ring).area


def pack(v, f, lo, scale):
    q = np.round((v - lo) / scale).astype('<u2')
    qs = np.concatenate([np.frombuffer(q[:, i].copy().tobytes(), np.uint8).reshape(-1, 2).T.ravel() for i in range(3)])
    d = np.diff(np.concatenate([[0], f.ravel()]))
    z = ((d << 1) ^ (d >> 63)).astype('<u4')
    zs = np.frombuffer(z.tobytes(), np.uint8).reshape(-1, 4).T.ravel()
    blob = zlib.compress(qs.tobytes() + zs.tobytes(), 9)
    return {'nv': len(v), 'nf': len(f), 'b64': base64.b64encode(blob).decode()}


parts = build.kicad_parts()
fp = footprints()
sw = model(parts, 'SWL11', fp)
di = model(parts, 'DL9', fp)
other = {}
for side in 'LR':
    meshes = []
    for name, shp in parts:
        bb = shp.BoundingBox()
        if (side == 'L') != ((bb.xmin + bb.xmax) / 2 < 150) or not name.startswith(('PWR', 'RST', 'RSW')):
            continue
        for s in shp.Solids():
            if s.BoundingBox().zmin > 0.75:
                s = build.lift(s)
            meshes.append(tess(build.place(s, side), 0.08))
    other[side] = merge(meshes)

groups = {}
for side in 'LR':
    groups[f'top_{side}'] = tess(load(f'../outputs/TOTEM_alu_top_{side}.step'))
    groups[f'bottom_{side}'] = tess(load(f'../outputs/TOTEM_alu_bottom_{side}.step'))
    groups[f'insert_{side}'] = tess(load(f'../outputs/TOTEM_wood_window_insert_{side}.step'))
    groups[f'parts_{side}'] = other[side]
    for key, kind, mesh in (('xiao', 'electronics', 'component3'), ('battery', 'battery', None),
                            ('screws', 'hardware', 'illustrative_screw'), ('caps', 'keycap', 'illustrative_cap')):
        ts = [t for t in placed({kind}, side) if mesh is None or t.metadata['mesh'] == mesh]
        groups[f'{key}_{side}'] = merge([(np.asarray(t.vertices, float), np.asarray(t.faces, np.int64)) for t in ts])
groups['switch'] = sw
groups['diode'] = di

lo = np.min([v.min(0) for v, _ in groups.values()], 0) - 1
hi = np.max([v.max(0) for v, _ in groups.values()], 0) + 1
scale = (hi - lo) / 65535
data = {'lo': lo.tolist(), 'scale': scale.tolist(), 'meshes': {},
        'switches': placements(parts, fp, 'SW', sw), 'diodes': placements(parts, fp, 'D', di),
        'pcb': {s: board_outline(s) for s in 'LR'}, 'pcb_top': build.PCB_TOP}
for k, (v, f) in groups.items():
    data['meshes'][k] = pack(v, f, lo, scale)
    print(k, len(v), len(f), len(data['meshes'][k]['b64']))
json.dump(data, open(W / 'view_data.json', 'w'), separators=(',', ':'))
print('switches', {k: len(v) for k, v in data['switches'].items()}, 'diodes', {k: len(v) for k, v in data['diodes'].items()})
print('pcb', {s: (len(r['circles']), len(r['rings'])) for s, r in data['pcb'].items()}, len(json.dumps(data['pcb'])))
print('json bytes', (W / 'view_data.json').stat().st_size)
