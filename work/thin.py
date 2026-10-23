"""Thinnest vertical layer of material at each XY (a skin over a pocket, a thin web, ...)."""
import sys
sys.path.insert(0, '.')
from geo import *
import trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

side, part = sys.argv[1], sys.argv[2]
path = {'top': f'../outputs/TOTEM_alu_top_{side}.step', 'bottom': f'../outputs/TOTEM_alu_bottom_{side}.step',
        'otop': f'orig/TOTEM_case_ble_top_{side}_V.08.step', 'obottom': f'orig/TOTEM_tenting_live_bottom_{side}.step'}[part]
s = load(path)
v, f = s.tessellate(0.01, 0.1)
m = trimesh.Trimesh(np.array([p.toTuple() for p in v]), np.array(f))
bb = s.BoundingBox()
xs = np.arange(bb.xmin, bb.xmax, 0.25); ys = np.arange(bb.ymin, bb.ymax, 0.25)
X, Y = np.meshgrid(xs, ys)
o = np.c_[X.ravel(), Y.ravel(), np.full(X.size, bb.zmin - 1)]
loc, idx, _ = m.ray.intersects_location(o, np.tile([0, 0, 1.0], (len(o), 1)), multiple_hits=True)
hits = [[] for _ in range(X.size)]
for (x, y, z), i in zip(loc, idx):
    hits[i].append(z)
T = np.full(X.size, np.nan)
for i, h in enumerate(hits):
    h = sorted(set(np.round(h, 4)))
    if len(h) >= 2 and len(h) % 2 == 0:
        T[i] = min(h[k + 1] - h[k] for k in range(0, len(h), 2))
T = T.reshape(X.shape)
thin = (T < 0.8)
print(part, side, 'grid points with a layer < 0.8 mm:', int(np.nansum(thin)), 'min layer', np.nanmin(T).round(3))
ys_, xs_ = np.where(thin)
pts = np.c_[xs[xs_], ys[ys_], T[ys_, xs_]]
# cluster the thin spots for a readable list
from scipy.cluster.hierarchy import fcluster, linkage
if len(pts) > 1:
    cl = fcluster(linkage(pts[:, :2], 'single'), 1.0, 'distance')
    for c in np.unique(cl):
        q = pts[cl == c]
        print(f'  thin spot around ({q[:,0].mean():.1f},{q[:,1].mean():.1f}) span {np.ptp(q[:,0]):.1f}x{np.ptp(q[:,1]):.1f} min {q[:,2].min():.2f} mm  n={len(q)}')
fig, ax = plt.subplots(figsize=(16, 12))
im = ax.imshow(T, origin='lower', extent=[xs[0], xs[-1], ys[0], ys[-1]], cmap='RdYlGn', vmin=0, vmax=1.5)
ax.set_title(f'{part} {side}: thinnest material layer (red < 0.8 mm)'); ax.set_aspect('equal')
plt.colorbar(im, ax=ax, fraction=0.03)
plt.tight_layout(); plt.savefig(f'thin_{part}_{side}.png', dpi=50)
