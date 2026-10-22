"""Where two versions of a 2.5D part differ, column by column on a fine grid (both are one
interval of material per (x, y)): metal only in the old one (removed) and only in the new one
(added), clustered, with area, depth and volume."""
import sys
sys.path.insert(0, '.')
from geo import *
import machinable
from scipy import ndimage

STEP = 0.05


def mesh(p):
    s = cq.Shape.importBrep(p) if p.endswith('.brep') else load(p)
    return machinable.surface_mesh(max(s.Solids(), key=lambda x: x.Volume()))


def report(name, d, xs, ys, min_vol, depth_tol=0.005):
    m = d > depth_tol
    lab, n = ndimage.label(m, structure=np.ones((3, 3)))
    rows = []
    for k in range(1, n + 1):
        sel = lab == k
        v = d[sel].sum() * STEP * STEP
        if v < min_vol:
            continue
        yy, xx = np.where(sel)
        rows.append((v, sel.sum() * STEP * STEP, d[sel].max(), xs[xx].mean(), ys[yy].mean(),
                     np.ptp(xs[xx]) + STEP, np.ptp(ys[yy]) + STEP))
    rows.sort(key=lambda r: -r[0])
    tot = d[m].sum() * STEP * STEP
    print(f'{name}: {tot:.3f} mm^3 in total (columns differing by more than {depth_tol} mm); '
          f'{len(rows)} spots over {min_vol} mm^3')
    for v, a, dmax, x, y, w, h in rows[:20]:
        print(f'   {v:7.3f} mm^3, {a:6.3f} mm^2, up to {dmax:.3f} mm deep, at ({x:7.2f},{y:8.2f}) {w:.2f} x {h:.2f}')


if __name__ == '__main__':
    old, new = mesh(sys.argv[1]), mesh(sys.argv[2])
    min_vol = float(sys.argv[3]) if len(sys.argv) > 3 else 0.01
    b = np.r_[old.bounds, new.bounds]
    xs = np.arange(b[:, 0].min() - 1, b[:, 0].max() + 1, STEP) + 1.234e-4
    ys = np.arange(b[:, 1].min() - 1, b[:, 1].max() + 1, STEP) + 2.345e-4
    zt0, zb0 = machinable.projected_columns(old, xs, ys)[:2]
    zt1, zb1 = machinable.projected_columns(new, xs, ys)[:2]
    e0, e1 = np.isnan(zt0), np.isnan(zt1)
    lo = np.nanmin(np.r_[zb0[~e0], zb1[~e1]]) - 1
    # empty columns as a zero-length interval far below, so intervals can be compared
    zt0 = np.where(e0, lo, zt0); zb0 = np.where(e0, lo, zb0); zt1 = np.where(e1, lo, zt1); zb1 = np.where(e1, lo, zb1)
    inter = np.clip(np.minimum(zt0, zt1) - np.maximum(zb0, zb1), 0, None)
    removed = (zt0 - zb0) - inter
    added = (zt1 - zb1) - inter
    print(f'volume old {old.volume:.2f} new {new.volume:.2f}')
    report('removed', removed, xs, ys, min_vol)
    report('added', added, xs, ys, min_vol)
