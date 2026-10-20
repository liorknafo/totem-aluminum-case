import sys; sys.path.insert(0, '.')
from geo import *
import trimesh, build
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig, axs = plt.subplots(2, 2, figsize=(20, 14))
rows = []
for c, side in enumerate('LR'):
    for r, (name, p) in enumerate([('before (site bottom)', f'orig/TOTEM_tenting_live_bottom_{side}.step'), ('now', f'../outputs/TOTEM_alu_bottom_{side}.step')]):
        s = load(p); v, f = s.tessellate(0.01, 0.1)
        m = trimesh.Trimesh(np.array([q.toTuple() for q in v]), np.array(f))
        bb = s.BoundingBox(); st = 0.2
        xs = np.arange(bb.xmin, bb.xmax, st); ys = np.arange(bb.ymin, bb.ymax, st)
        X, Y = np.meshgrid(xs, ys); P = np.c_[X.ravel(), Y.ravel()]
        up = m.ray.intersects_location(np.c_[P, np.full(len(P), -30.0)], np.tile([0, 0, 1.0], (len(P), 1)), multiple_hits=False)
        U = np.full(len(P), np.nan); U[up[1]] = up[0][:, 2]
        ax = axs[r, c]
        im = ax.pcolormesh(-X, Y, U.reshape(X.shape), cmap='viridis', vmin=-11.5, vmax=0, shading='auto')  # seen from below: mirrored
        ax.set_facecolor('white')
        ax.set_aspect('equal'); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f'{side} bottom from below, {name}', fontsize=14)
        for x, y in build.SCREWS[side]: ax.plot(-x, y, 'o', mfc='none', mec='w', ms=14)
fig.suptitle('Underside height; white inside the part = hole through it (circles: screw holes)', fontsize=15)
cb = fig.colorbar(im, ax=axs, shrink=.6); cb.set_label('height of the underside, mm')
plt.savefig('../outputs/underside_holes.png', dpi=60, bbox_inches='tight')
