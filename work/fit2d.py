"""Polyline -> lines and circular arcs within a tolerance, keeping every primitive's end points on
the polyline's own vertices (so neighbouring chains still meet exactly)."""
import numpy as np


def _seg_dev(P, i, j):
    """Largest distance of P[i..j] from the segment P[i]-P[j]."""
    a, b = P[i], P[j]
    d = b - a
    L2 = d @ d
    Q = P[i:j + 1] - a
    if L2 < 1e-24:
        return np.sqrt((Q ** 2).sum(1)).max()
    t = np.clip(Q @ d / L2, 0, 1)
    return np.sqrt(((Q - np.outer(t, d)) ** 2).sum(1)).max()


def _arc_through(P, i, j):
    """Circle through P[i] and P[j] (centre on their bisector) that best fits P[i..j] (minimax),
    or None. Returns (centre, radius, deviation)."""
    a, b = P[i], P[j]
    m, d = (a + b) / 2, b - a
    h = np.linalg.norm(d)
    if h < 1e-9:
        return None
    n = np.array([-d[1], d[0]]) / h
    Q = P[i:j + 1]
    # least-squares start from the 3-point circle through the middle vertex
    k = (i + j) // 2
    c3 = _circle3(P[i], P[k], P[j])
    if c3 is None:
        return None
    s = (c3 - m) @ n

    def dev(s):
        c = m + s * n
        r = np.hypot(h / 2, s)
        return np.abs(np.sqrt(((Q - c) ** 2).sum(1)) - r).max()
    best = (dev(s), s)
    step = max(abs(s), h) * 0.05 + 1e-6
    for _ in range(60):  # 1D pattern search on the bisector
        improved = False
        for t in (best[1] - step, best[1] + step):
            v = dev(t)
            if v < best[0]:
                best, improved = (v, t), True
        if not improved:
            step /= 2
            if step < 1e-9:
                break
    c = m + best[1] * n
    return c, float(np.hypot(h / 2, best[1])), best[0]


def _circle3(a, b, c):
    d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    if abs(d) < 1e-14:
        return None
    ux = ((a @ a) * (b[1] - c[1]) + (b @ b) * (c[1] - a[1]) + (c @ c) * (a[1] - b[1])) / d
    uy = ((a @ a) * (c[0] - b[0]) + (b @ b) * (a[0] - c[0]) + (c @ c) * (b[0] - a[0])) / d
    return np.array([ux, uy])


def _monotone(P, i, j, c):
    """The vertices go round the centre one way only, through less than a full turn."""
    ang = np.unwrap(np.arctan2(P[i:j + 1, 1] - c[1], P[i:j + 1, 0] - c[0]))
    da = np.diff(ang)
    return (np.all(da > 1e-9) or np.all(da < -1e-9)) and abs(ang[-1] - ang[0]) < 2 * np.pi - 1e-3


def fit(P, tol, rmax=500.0, rmin=0.05, min_pts=4, sag=0.012):
    """P: (n,2) open polyline. Returns primitives covering it in order:
    ('line', i, j) or ('arc', i, j, centre, radius). Greedy longest fit from the start."""
    P = np.asarray(P, float)
    n = len(P)
    out, i = [], 0
    while i < n - 1:
        # longest line
        j = i + 1
        while j + 1 < n and _seg_dev(P, i, j + 1) <= tol:
            j += 1
        best = ('line', i, j)
        # longest arc (at least min_pts vertices), grown by doubling then bisection
        if n - i >= min_pts:
            def ok(jj):
                r = _arc_through(P, i, jj)
                if r is None:
                    return None
                c, rad, dv = r
                if dv > tol or not (rmin <= rad <= rmax) or not _monotone(P, i, jj, c):
                    return None
                # the arc between two vertices must stay close to their chord too
                ch = np.sqrt(((P[i + 1:jj + 1] - P[i:jj]) ** 2).sum(1)).max() / 2
                if ch >= rad or rad - np.sqrt(rad * rad - ch * ch) > sag:
                    return None
                return r
            jj, good = i + min_pts - 1, None
            if ok(jj) is not None:
                good = jj
                hi = jj
                while hi + 1 < n:
                    nxt = min(n - 1, i + 2 * (hi - i))
                    if ok(nxt) is None:
                        break
                    good = hi = nxt
                    if nxt == n - 1:
                        break
                lo, up = good, min(n - 1, i + 2 * (good - i))
                while up - lo > 1:
                    mid = (lo + up) // 2
                    if ok(mid) is not None:
                        lo = mid
                    else:
                        up = mid
                good = lo
                # bisection on a non-monotone predicate: walk on while it still fits
                while good + 1 < n and ok(good + 1) is not None:
                    good += 1
            if good is not None and good > j:
                c, rad, _ = ok(good)
                best = ('arc', i, good, c, rad)
        out.append(best)
        i = best[2]
    return out


def sample(prim, P, step=0.01):
    """Points along a fitted primitive (for checks)."""
    if prim[0] == 'line':
        a, b = P[prim[1]], P[prim[2]]
        k = max(2, int(np.linalg.norm(b - a) / step) + 1)
        return a + np.outer(np.linspace(0, 1, k), b - a)
    _, i, j, c, r = prim
    a0 = np.arctan2(*(P[i] - c)[::-1])
    ang = np.unwrap(np.arctan2(P[i:j + 1, 1] - c[1], P[i:j + 1, 0] - c[0]))
    a1 = a0 + (ang[-1] - ang[0])
    k = max(3, int(abs(a1 - a0) * r / step) + 1)
    t = np.linspace(a0, a1, k)
    return c + r * np.c_[np.cos(t), np.sin(t)]


def mid_point(prim, P):
    _, i, j, c, r = prim
    ang = np.unwrap(np.arctan2(P[i:j + 1, 1] - c[1], P[i:j + 1, 0] - c[0]))
    t = (ang[0] + ang[-1]) / 2
    return c + r * np.array([np.cos(t), np.sin(t)])


if __name__ == '__main__':
    # self-test: a slot outline (two lines + two half circles), chords of 6 per quarter
    t = np.linspace(0, np.pi, 13)
    P = np.r_[np.c_[np.linspace(0, 10, 5), np.zeros(5)][:-1],
              np.c_[10 + 1.05 * np.sin(t), 1.05 - 1.05 * np.cos(t)][:-1],
              np.c_[np.linspace(10, 0, 5), np.full(5, 2.1)][:-1],
              np.c_[-1.05 * np.sin(t), 1.05 + 1.05 * np.cos(t)]]
    pr = fit(P, 0.002)
    print([(p[0], p[1], p[2]) + ((round(p[4], 4),) if p[0] == 'arc' else ()) for p in pr])
    assert [p[0] for p in pr] == ['line', 'arc', 'line', 'arc'], pr
    noisy = P + np.random.default_rng(1).normal(0, 0.003, P.shape)
    print(len(fit(noisy, 0.012)), 'primitives with 0.003 noise at tol 0.012')
