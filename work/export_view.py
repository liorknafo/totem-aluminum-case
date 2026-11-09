"""outputs/TOTEM_3d_view.html: the interactive three.js view of the whole build (viewer_template.html).

Meshes come from scene.py. Vertices are quantized to uint16 over the scene box (byte planes),
indices delta/zigzag coded (byte planes), zlib, base64. Switches and diodes are one mesh each plus
a placement per footprint; the board is its outline and holes, extruded in the viewer.
"""
import base64
import json
import zlib
from pathlib import Path

import numpy as np

import build as B
import geom2d as g
import scene

W = Path(__file__).resolve().parent


def pack(v, f, lo, scale):
    q = np.round((v - lo) / scale).astype('<u2')
    qs = np.concatenate([np.frombuffer(q[:, i].copy().tobytes(), np.uint8).reshape(-1, 2).T.ravel() for i in range(3)])
    d = np.diff(np.concatenate([[0], f.ravel()])).astype(np.int64)
    z = ((d << 1) ^ (d >> 63)).astype('<u4')
    zs = np.frombuffer(z.tobytes(), np.uint8).reshape(-1, 4).T.ravel()
    blob = zlib.compress(qs.tobytes() + zs.tobytes(), 9)
    return {'nv': len(v), 'nf': len(f), 'b64': base64.b64encode(blob).decode()}


def ring(wire, shift):
    pts = []
    for e in wire.Edges():
        n = max(2, int(e.Length() / 0.4) + 1)
        pts += [e.positionAt(t).toTuple()[:2] for t in np.linspace(0, 1, n)][:-1]
    a = np.array(pts) + np.array((shift, 0))
    return np.round(a, 3)


def pcb_outline(side):
    shift = scene.VIEW_SHIFT if side == 'R' else 0.0
    f = g.from_loops(scene.board().outline(side))
    out = ring(f.outerWire(), shift)
    # the case viewer wants a counter-clockwise outline and clockwise holes
    def ccw(a, want=True):
        s = np.sum(a[:, 0] * np.roll(a[:, 1], -1) - np.roll(a[:, 0], -1) * a[:, 1])
        return a if (s > 0) == want else a[::-1]
    circles = [[round(fp.at[0] + shift, 3), round(fp.at[1], 3), 1.6] for fp in scene.board().footprints
               if fp.side == side and B.kind(fp) == 'MountingHole']
    rings = [ccw(ring(w, shift), False).ravel().tolist() for w in f.innerWires()]
    return {'outline': ccw(out).ravel().tolist(), 'circles': circles, 'rings': rings}


def instanced(kind):
    """The most common model entries of a footprint kind (drawn as one instanced mesh) and the
    footprints that carry them; footprints of that kind with other entries are drawn as parts."""
    from collections import Counter
    import parts as P
    fps = [f for f in scene.board().footprints if B.kind(f) == kind]
    key = Counter(P.model_key(f) for f in fps).most_common(1)[0][0]
    same = [f for f in fps if P.model_key(f) == key]
    return same[0], same, [f for f in fps if P.model_key(f) != key]


def placements(fps):
    out = {}
    for side in 'LR':
        shift = scene.VIEW_SHIFT if side == 'R' else 0.0
        out[side] = [[round(fp.at[0] + shift, 4), round(fp.at[1], 4), fp.angle] for fp in fps if fp.side == side]
    return out


def main():
    sw_ref, sw_same, sw_other = instanced('Kailh_socket')
    di_ref, di_same, di_other = instanced('Diode_SOD123')
    groups = {}
    for side in 'LR':
        L = scene.layers(side)
        for k in ('top', 'bottom', 'insert', 'xiao', 'battery', 'screws', 'caps'):
            groups[f'{k}_{side}'] = scene.shifted(side, L[k])
        fps = [f for f in scene.board().footprints if f.side == side and B.kind(f) in ('MSK12C02', 'SKHLLCA010')]
        fps += [f for f in sw_other + di_other if f.side == side]
        groups[f'parts_{side}'] = scene.shifted(side, scene.merge([scene.place(scene.local_model(f, 'all'), f.at, f.angle) for f in fps]))
    groups['switch'] = scene.merge([scene.local_model(sw_ref, 'switch'), scene.local_model(sw_ref, 'socket')])
    groups['diode'] = scene.local_model(di_ref, 'all')
    lo = np.min([v.min(0) for v, _ in groups.values() if len(v)], 0) - 1
    hi = np.max([v.max(0) for v, _ in groups.values() if len(v)], 0) + 1
    scale = (hi - lo) / 65535
    data = {'lo': lo.tolist(), 'scale': scale.tolist(), 'meshes': {},
            'switches': placements(sw_same), 'diodes': placements(di_same),
            'pcb': {s: pcb_outline(s) for s in 'LR'}, 'pcb_top': 1.6}
    for k, (v, f) in groups.items():
        data['meshes'][k] = pack(v, f, lo, scale)
    t = (W / 'viewer_template.html').read_text()
    html = t.replace('__DATA__', json.dumps(data, separators=(',', ':')))
    (W.parent / 'outputs' / 'TOTEM_3d_view.html').write_text(html)
    print('3D view written', len(html) // 1024, 'kB')


if __name__ == '__main__':
    main()
