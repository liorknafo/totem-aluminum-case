"""Shaded 3D views of the new parts (matplotlib, flat shading)."""
import sys
sys.path.insert(0, '.')
from geo import *
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

side = sys.argv[1] if len(sys.argv) > 1 else 'L'


def mesh(path, tol=0.08):
    s = load(path)
    v, f = s.tessellate(tol, 0.5)
    return np.array([p.toTuple() for p in v]), np.array(f)


def draw(ax, V, F, color, elev, azim, light=(0.4, -0.5, 0.8)):
    tri = V[F]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    L = np.array(light) / np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(np.abs(n @ L), 0, 1)
    col = np.clip(np.outer(shade, color), 0, 1)
    pc = Poly3DCollection(tri, facecolors=col, edgecolors='none')
    ax.add_collection3d(pc)
    ax.view_init(elev=elev, azim=azim)


views = [
    (f'../outputs/TOTEM_alu_top_{side}.step', (0.75, 0.77, 0.8), 60, -70, 'aluminum top - from above (wood window opening)'),
    (f'../outputs/TOTEM_alu_top_{side}.step', (0.75, 0.77, 0.8), -60, -70, 'aluminum top - underside (faces the PCB)'),
    (f'../outputs/TOTEM_alu_bottom_{side}.step', (0.72, 0.74, 0.78), 60, -70, 'aluminum bottom - from above (faces the PCB)'),
    (f'../outputs/TOTEM_wood_window_insert_{side}.step', (0.75, 0.55, 0.32), 35, -60, 'wood insert (plug + flange)'),
]
fig = plt.figure(figsize=(20, 15))
for i, (p, c, el, az, title) in enumerate(views):
    ax = fig.add_subplot(2, 2, i + 1, projection='3d')
    V, F = mesh(p, 0.05 if 'insert' in p else 0.08)
    draw(ax, V, F, c, el, az)
    lo, hi = V.min(0), V.max(0)
    ctr = (lo + hi) / 2; r = (hi - lo).max() / 2
    ax.set_xlim(ctr[0] - r, ctr[0] + r); ax.set_ylim(ctr[1] - r, ctr[1] + r); ax.set_zlim(ctr[2] - r, ctr[2] + r)
    ax.set_box_aspect((1, 1, 1)); ax.set_axis_off(); ax.set_title(title)
plt.tight_layout(); plt.savefig(f'render3d_{side}.png', dpi=60)
print('saved')
