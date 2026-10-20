"""Inline-preview variant of the viewer: mesh blobs moved into a lossless RGB PNG (view_data.png)."""
import json, base64
import numpy as np
from pathlib import Path
from PIL import Image

W = Path(__file__).resolve().parent
d = json.load(open(W / 'view_data.json'))
buf, off = bytearray(), 0
for k, m in d['meshes'].items():
    b = base64.b64decode(m.pop('b64'))
    m['off'], m['len'] = len(buf), len(b)
    buf += b
meta = json.dumps(d, separators=(',', ':')).encode()
buf = len(meta).to_bytes(4, 'little') + meta + buf
width = 1024
n = -(-len(buf) // (width * 3)) * width * 3
a = np.frombuffer(bytes(buf) + bytes(n - len(buf)), np.uint8).reshape(-1, width, 3)
Image.fromarray(a, 'RGB').save(W / 'view_data.png', optimize=True)
t = open(W / 'viewer_template.html').read()
(W / 'view_inline.html').write_text(t.replace('__DATA__', '{}').replace('__PNG__', str(W / 'view_data.png')))
t2 = open(W / 'view_data.json').read()
(W.parent / 'outputs' / 'TOTEM_3d_view.html').write_text(t.replace('__DATA__', t2))
print(len(buf), (W / 'view_data.png').stat().st_size, (W / 'view_inline.html').stat().st_size)
