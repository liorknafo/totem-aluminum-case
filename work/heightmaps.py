"""Height maps of the faces that look at the PCB: underside of the top, upper side of the bottom.
Before/after, with the PCB outline, so removed material is visible at a glance."""
import sys
sys.path.insert(0, '.')
from geo import *
import trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

side = sys.argv[1] if len(sys.argv) > 1 else 'L'
PCB = 1.6  # board top face the case was designed around


def tm(shape):
    v, f = shape.tessellate(0.02, 0.2)
    return trimesh.Trimesh(np.array([p.toTuple() for p in v]), np.array(f))


def first_surface_toward_pcb(mesh, xs, ys, top_part):
    """Top part: lowest material above z=1.0 seen from below the board plane.
    Bottom part: highest material below z=0.6 seen from above."""
    X, Y = np.meshgrid(xs, ys)
    z0 = 1.0 if top_part else 0.6
    o = np.c_[X.ravel(), Y.ravel(), np.full(X.size, z0)]
    d = np.tile([0, 0, 1.0 if top_part else -1.0], (len(o), 1))
    loc, idx, _ = mesh.ray.intersects_location(o, d, multiple_hits=True)
    Z = np.full(X.size, np.nan)
    for (x, y, z), i in zip(loc, idx):
        if top_part:
            Z[i] = z if np.isnan(Z[i]) else min(Z[i], z)
        else:
            Z[i] = z if np.isnan(Z[i]) else max(Z[i], z)
    return Z.reshape(X.shape)


pcb = load(f'pcb_{side}.step')
pl = section(pcb, 0.75)
o = {'top': load(f'orig/TOTEM_case_ble_top_{side}_V.08.step'), 'bottom': load(f'orig/TOTEM_tenting_live_bottom_{side}.step')}
n = {'top': load(f'../outputs/TOTEM_alu_top_{side}.step'), 'bottom': load(f'../outputs/TOTEM_alu_bottom_{side}.step')}
bb = o['top'].BoundingBox()
xs = np.arange(bb.xmin - 1, bb.xmax + 1, 0.25); ys = np.arange(bb.ymin - 1, bb.ymax + 1, 0.25)
fig, axs = plt.subplots(2, 3, figsize=(30, 15))
for row, part in enumerate(['top', 'bottom']):
    top_part = part == 'top'
    Zo = first_surface_toward_pcb(tm(o[part]), xs, ys, top_part)
    Zn = first_surface_toward_pcb(tm(n[part]), xs, ys, top_part)
    if top_part:
        gap_o, gap_n = Zo - PCB, Zn - PCB
    else:
        gap_o, gap_n = 0 - Zo, 0 - Zn
    for col, (title, G) in enumerate([(f'ORIGINAL {part}: gap to PCB face', gap_o), (f'NEW {part}: gap to PCB face', gap_n)]):
        ax = axs[row, col]
        im = ax.imshow(G, origin='lower', extent=[xs[0], xs[-1], ys[0], ys[-1]], cmap='RdYlGn', vmin=0, vmax=1.0)
        for l in pl: ax.plot(l[:, 0], l[:, 1], 'k', lw=0.5)
        ax.set_title(title + '  (red = touching, green >= 1 mm)'); ax.set_aspect('equal')
        plt.colorbar(im, ax=ax, fraction=0.03)
    ax = axs[row, 2]
    D = np.where(np.isnan(Zo) | np.isnan(Zn), np.nan, np.abs(Zn - Zo))
    im = ax.imshow(D, origin='lower', extent=[xs[0], xs[-1], ys[0], ys[-1]], cmap='magma_r', vmin=0, vmax=2)
    for l in pl: ax.plot(l[:, 0], l[:, 1], 'c', lw=0.5)
    ax.set_title(f'{part}: material removed (mm of depth)'); ax.set_aspect('equal')
    plt.colorbar(im, ax=ax, fraction=0.03)
plt.tight_layout(); plt.savefig(f'heightmap_{side}.png', dpi=45)
print('saved')
