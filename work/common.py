import sys, json, base64
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT / 'pylib'))
import numpy as np, trimesh

D = json.loads((ROOT / 'work' / 'meshes.json').read_text())

def raw(name):
    m = D['meshes'][name]
    v = np.frombuffer(base64.b64decode(m['v']), dtype='<i2').reshape(-1, 3).astype(float) / 100
    f = np.frombuffer(base64.b64decode(m['f']), dtype='<u2').reshape(-1, 3)
    t = trimesh.Trimesh(v, f, process=True)
    t.update_faces(t.nondegenerate_faces()); t.update_faces(t.unique_faces()); t.remove_unreferenced_vertices()
    return t

def placed(kind_filter, side):
    out = []
    for i in D['instances']:
        if i['side'] != side or i['kind'] not in kind_filter: continue
        t = raw(i['mesh']).copy()
        a = np.radians(i['a'])
        M = trimesh.transformations.rotation_matrix(a, [0, 0, 1])
        M[:3, 3] = i['p']
        t.apply_transform(M)
        t.metadata['kind'] = i['kind']; t.metadata['pos'] = i['p']; t.metadata['mesh'] = i['mesh']
        out.append(t)
    return out
