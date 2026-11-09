"""Pictures for outputs/: cross-sections through the assembly and clearance maps over the board.

    python -E -s maps.py
"""
from pathlib import Path

import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import build as B
import scene

OUT = Path(__file__).resolve().parent.parent / 'outputs'
COL = dict(top='#8d939c', bottom='#5f656e', insert='#b5793f', pcb='#1d6e45', switches='#3c4047', parts='#111111',
           xiao='#3466b0', battery='#c9a94f', screws='#777777', caps='#d8d4c8')


def tm(mesh):
    v, f = mesh
    return trimesh.Trimesh(v, f, process=False)


def section_lines(m, origin, normal):
    try:
        s = m.section(plane_origin=origin, plane_normal=normal)
    except Exception:
        return []
    if s is None:
        return []
    return [d for d in s.discrete]


def sections(side='L'):
    L = scene.layers(side)
    d = scene.design(side)
    xiao = d['xiao']
    pwr = next(f for f in scene.board().footprints if f.side == side and B.kind(f) == 'MSK12C02')
    rst = next(f for f in scene.board().footprints if f.side == side and B.kind(f) == 'SKHLLCA010')
    k5 = next(f for f in d['keys'] if f.ref.endswith('5'))
    dio = next(f for f in scene.board().footprints if f.side == side and f.ref.endswith('L10' if side == 'L' else 'R10'))
    cuts = [('y', xiao.at[1], f'y = {xiao.at[1]:.1f}: through the XIAO, its window and the USB-C opening'),
            ('x', pwr.at[0] - 4.5, f'x = {pwr.at[0] - 4.5:.1f}: through the power slider opening'),
            ('x', rst.at[0], f'x = {rst.at[0]:.1f}: through the reset button and its slot'),
            ('y', k5.at[1], f'y = {k5.at[1]:.1f}: through a key row and the diode column'),
            ('x', dio.at[0], f'x = {dio.at[0]:.1f}: along the diode column'),
            ('y', d['holes'][0][1], f'y = {d["holes"][0][1]:.1f}: through a screw')]
    meshes = {k: tm(L[k]) for k in ('top', 'bottom', 'insert', 'pcb', 'switches', 'parts', 'xiao', 'battery', 'screws')}
    fig, axes = plt.subplots(len(cuts), 1, figsize=(18, 3.2 * len(cuts)))
    for ax, (axis, val, title) in zip(axes, cuts):
        normal = (0, 1, 0) if axis == 'y' else (1, 0, 0)
        origin = (0, val, 0) if axis == 'y' else (val, 0, 0)
        for k, m in meshes.items():
            for seg in section_lines(m, origin, normal):
                h = seg[:, 0] if axis == 'y' else seg[:, 1]
                ax.fill(h, seg[:, 2], color=COL[k], alpha=0.85 if k in ('top', 'bottom') else 1.0, lw=0)
                ax.plot(h, seg[:, 2], color='k', lw=0.3)
        ax.set_title(title, fontsize=10, loc='left')
        ax.set_aspect('equal'); ax.grid(True, lw=0.2)
        ax.set_ylim(B.Z_BOT - 1, B.Z_TOP + 2)
        ax.set_xlabel('x (mm)' if axis == 'y' else 'y (mm)')
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in COL.values() if c]
    fig.legend(handles, list(COL.keys()), loc='upper right', ncol=5, fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(OUT / f'sections_{side}.png', dpi=80)
    plt.close(fig)


def clearance(side):
    """Gap from the board's top face up to the top part, and from its bottom face down to the bottom."""
    L = scene.layers(side)
    top, bot = tm(L['top']), tm(L['bottom'])
    d = scene.design(side)
    bb = d['board'].BoundingBox()
    step = 0.25
    xs = np.arange(bb.xmin, bb.xmax, step); ys = np.arange(bb.ymin, bb.ymax, step)
    X, Y = np.meshgrid(xs, ys)
    pts = np.c_[X.ravel(), Y.ravel()]
    import shapely.geometry as sg
    from shapely import contains_xy
    f = d['board'].Faces()[0]
    def ring(w):
        return [(e.positionAt(t).x, e.positionAt(t).y) for e in w.Edges() for t in np.linspace(0, 1, 16)]
    poly = sg.Polygon(ring(f.outerWire()), [ring(w) for w in f.innerWires()]).buffer(0)
    inside = contains_xy(poly, pts[:, 0], pts[:, 1])
    fig, axes = plt.subplots(1, 2, figsize=(22, 8.5))
    for ax, m, z0, sgn, title in ((axes[0], top, 1.6 + B.COPPER, 1, 'top part above the board (from the copper)'),
                                  (axes[1], bot, -B.COPPER, -1, 'bottom part below the board (from the copper)')):
        o = np.c_[pts, np.full(len(pts), z0)]
        loc, idx, _ = m.ray.intersects_location(o, np.tile((0, 0, sgn), (len(o), 1)), multiple_hits=False)
        G = np.full(len(pts), np.nan)
        G[idx] = np.abs(loc[:, 2] - z0)
        G[~inside] = np.nan
        G = G.reshape(X.shape)
        im = ax.imshow(G, origin='lower', extent=(xs[0], xs[-1], ys[0], ys[-1]), cmap='viridis', vmin=0.5, vmax=4.0)
        ax.set_title(f'{side}: gap from the {title}; min {np.nanmin(G):.2f} mm (white: no aluminum above / below)', fontsize=10)
        ax.set_aspect('equal')
        fig.colorbar(im, ax=ax, shrink=0.7, label='mm')
    fig.tight_layout()
    fig.savefig(OUT / f'clearance_{side}.png', dpi=75)
    plt.close(fig)


if __name__ == '__main__':
    sections('L')
    for s in 'LR':
        clearance(s)
    print('maps written')
