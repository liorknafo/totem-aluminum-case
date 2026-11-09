"""Read the TOTEM KiCad board: outline (lines and arcs), footprints and pads.

Case frame (used everywhere in work/): x = KiCad x, y = -KiCad y, z = 0 at the board's bottom face.
KiCad angles are counter-clockwise in this frame, so a footprint-local point (u, v) (KiCad, y down)
maps to  centre + R(angle) @ (u, -v).

The board outline is drawn with Bezier curves. Straight ones become lines, curved ones are replaced
by tangent-continuous arcs (biarcs) within ARC_TOL, so everything built from it stays analytic.
"""
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PCB_FILE = ROOT / 'src' / 'totem_0_3.kicad_pcb'
ARC_TOL = 0.005          # max deviation of the arc fit from the Bezier outline (mm)
SPLIT_X = 150.0          # the panel holds both halves; left half x < 150
TAB_X = (143.3, 156.6)   # mouse-bite tabs between the halves span this x range
THUMB_Y = -121.5         # below this (case y) the halves come closest; tabs are above it


# ----------------------------------------------------------------------------- s-expressions
def parse_sexp(text):
    tok = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')
    stack = [[]]
    for m in tok.finditer(text):
        t = m.group()
        if t == '(':
            stack.append([])
        elif t == ')':
            x = stack.pop()
            stack[-1].append(x)
        else:
            stack[-1].append(t[1:-1] if t[0] == '"' else t)
    return stack[0][0]


def sub(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def one(node, key, default=None):
    s = sub(node, key)
    return s[0] if s else default


def nums(node):
    return [float(v) for v in node[1:] if not isinstance(v, list)]


# ----------------------------------------------------------------------------- geometry helpers
def rot(p, a_deg):
    a = math.radians(a_deg)
    return (p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a))


def kpt(x, y):
    """KiCad board point -> case frame."""
    return (x, -y)


@dataclass
class Footprint:
    lib: str
    ref: str
    at: tuple            # case frame
    angle: float         # degrees, CCW in the case frame
    pads: list = field(default_factory=list)
    edge: list = field(default_factory=list)   # Edge.Cuts segments inside the footprint (case frame)

    def to_case(self, u, v):
        """Footprint-local KiCad point -> case frame."""
        dx, dy = rot((u, -v), self.angle)
        return (self.at[0] + dx, self.at[1] + dy)

    @property
    def side(self):
        return 'L' if self.at[0] < SPLIT_X else 'R'


@dataclass
class Pad:
    number: str
    kind: str            # thru_hole, np_thru_hole, smd
    shape: str           # circle, rect, oval, roundrect
    at: tuple            # case frame centre
    angle: float         # absolute, CCW in the case frame
    size: tuple          # along the pad's own x and y
    drill: float
    layers: list
    net: str

    @property
    def top(self):
        return any(l in ('F.Cu', '*.Cu', 'F&B.Cu') for l in self.layers)

    @property
    def bottom(self):
        return any(l in ('B.Cu', '*.Cu', 'F&B.Cu') for l in self.layers)

    @property
    def copper(self):
        return self.top or self.bottom


# ----------------------------------------------------------------------------- Bezier -> lines/arcs
def bez(p, t):
    a = (1 - t) ** 3; b = 3 * (1 - t) ** 2 * t; c = 3 * (1 - t) * t ** 2; d = t ** 3
    return (a * p[0][0] + b * p[1][0] + c * p[2][0] + d * p[3][0], a * p[0][1] + b * p[1][1] + c * p[2][1] + d * p[3][1])


def bez_split(p, t=0.5):
    def lerp(a, b):
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    p01, p12, p23 = lerp(p[0], p[1]), lerp(p[1], p[2]), lerp(p[2], p[3])
    p012, p123 = lerp(p01, p12), lerp(p12, p23)
    m = lerp(p012, p123)
    return [p[0], p01, p012, m], [m, p123, p23, p[3]]


def unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n) if n > 1e-12 else (0.0, 0.0)


def bez_tangents(p):
    t0 = unit((p[1][0] - p[0][0], p[1][1] - p[0][1]))
    if t0 == (0.0, 0.0):
        t0 = unit((p[2][0] - p[0][0], p[2][1] - p[0][1]))
    t1 = unit((p[3][0] - p[2][0], p[3][1] - p[2][1]))
    if t1 == (0.0, 0.0):
        t1 = unit((p[3][0] - p[1][0], p[3][1] - p[1][1]))
    return t0, t1


def line_dev(p):
    """Largest distance of the Bezier from its chord."""
    a, b = p[0], p[3]
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    worst = 0.0
    for i in range(1, 16):
        q = bez(p, i / 16)
        worst = max(worst, abs((b[0] - a[0]) * (a[1] - q[1]) - (a[0] - q[0]) * (b[1] - a[1])) / L)
    return worst


def arc_through(a, m, b):
    """Centre and radius of the circle through three points (None if collinear)."""
    ax, ay = a; bx, by = m; cx, cy = b
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return (ux, uy), math.hypot(ax - ux, ay - uy)


def tangent_arc(p0, t0, p1):
    """Arc from p0 with start tangent t0 ending at p1: returns its mid point."""
    ch = (p1[0] - p0[0], p1[1] - p0[1])
    n = (-t0[1], t0[0])
    d = ch[0] * n[0] + ch[1] * n[1]
    if abs(d) < 1e-12:
        return ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    r = (ch[0] ** 2 + ch[1] ** 2) / (2 * d)
    c = (p0[0] + n[0] * r, p0[1] + n[1] * r)
    a0 = math.atan2(p0[1] - c[1], p0[0] - c[0])
    a1 = math.atan2(p1[1] - c[1], p1[0] - c[0])
    da = a1 - a0
    # sweep direction follows the tangent
    if r > 0:
        while da <= 0:
            da += 2 * math.pi
    else:
        while da >= 0:
            da -= 2 * math.pi
    am = a0 + da / 2
    return (c[0] + abs(r) * math.cos(am), c[1] + abs(r) * math.sin(am))


def biarc(p0, t0, p1, t1):
    """Two tangent arcs p0 -> j -> p1 (equal-tangent-length biarc)."""
    v = (p1[0] - p0[0], p1[1] - p0[1])
    t = (t0[0] + t1[0], t0[1] + t1[1])
    vt = v[0] * t[0] + v[1] * t[1]
    tt = t0[0] * t1[0] + t0[1] * t1[1]
    vv = v[0] ** 2 + v[1] ** 2
    denom = 2 * (1 - tt)
    if abs(denom) < 1e-9:
        d = vv / (4 * (v[0] * t1[0] + v[1] * t1[1]))
    else:
        d = (-vt + math.sqrt(vt * vt + denom * vv)) / denom
    q0 = (p0[0] + d * t0[0], p0[1] + d * t0[1])
    q1 = (p1[0] - d * t1[0], p1[1] - d * t1[1])
    j = ((q0[0] + q1[0]) / 2, (q0[1] + q1[1]) / 2)
    return [('arc', p0, tangent_arc(p0, t0, j), j),
            ('arc', j, tangent_arc(p1, (-t1[0], -t1[1]), j), p1)]


def seg_dev(seg, p):
    """Largest distance from Bezier samples to the fitted segment's circle."""
    _, a, m, b = seg
    cr = arc_through(a, m, b)
    if cr is None:
        return 0.0
    (cx, cy), r = cr
    return max(abs(math.hypot(q[0] - cx, q[1] - cy) - r) for q in (bez(p, i / 24) for i in range(25)))


def bezier_to_segments(p, depth=0):
    if line_dev(p) < 1e-4:
        return [('line', p[0], p[3])]
    t0, t1 = bez_tangents(p)
    segs = biarc(p[0], t0, p[3], t1)
    # every sample must lie within ARC_TOL of one of the two arcs
    samples = [bez(p, i / 32) for i in range(33)]
    def d_to(seg, q):
        cr = arc_through(seg[1], seg[2], seg[3])
        if cr is None:
            return 0.0
        (cx, cy), r = cr
        return abs(math.hypot(q[0] - cx, q[1] - cy) - r)
    j = segs[0][3]
    worst = 0.0
    for q in samples:
        # pick the arc on the same side of the junction (by distance along the chord)
        worst = max(worst, min(d_to(segs[0], q), d_to(segs[1], q)))
    if worst > ARC_TOL and depth < 6:
        a, b = bez_split(p)
        return bezier_to_segments(a, depth + 1) + bezier_to_segments(b, depth + 1)
    return segs


# ----------------------------------------------------------------------------- board
class Board:
    def __init__(self, path=PCB_FILE):
        self.tree = parse_sexp(Path(path).read_text())
        self.thickness = float(one(one(self.tree, 'general'), 'thickness')[1])
        self.footprints = [self._footprint(f) for f in sub(self.tree, 'footprint')]
        self.edge = self._edge_segments()

    # .................................................................. footprints and pads
    def _footprint(self, f):
        at = nums(one(f, 'at'))
        ang = at[2] if len(at) > 2 else 0.0
        ref = next((x[2] for x in sub(f, 'fp_text') if x[1] == 'reference'), '?')
        fp = Footprint(lib=f[1], ref=ref, at=kpt(at[0], at[1]), angle=ang)
        for p in sub(f, 'pad'):
            pat = nums(one(p, 'at'))
            pang = pat[2] if len(pat) > 2 else 0.0
            size = tuple(nums(one(p, 'size')))
            dr = one(p, 'drill')
            drill = 0.0
            if dr:
                vals = [v for v in dr[1:] if not isinstance(v, list) and v != 'oval']
                drill = float(vals[0]) if vals else 0.0
            net = one(p, 'net')
            fp.pads.append(Pad(number=p[1], kind=p[2], shape=p[3], at=fp.to_case(pat[0], pat[1]), angle=pang,
                               size=size, drill=drill, layers=list(one(p, 'layers')[1:]),
                               net=net[2] if net and len(net) > 2 else ''))
        for g in f:
            if isinstance(g, list) and g and g[0] in ('fp_line', 'fp_arc', 'fp_curve') and one(g, 'layer') and one(g, 'layer')[1] == 'Edge.Cuts':
                for s in self._graphic(g, fp.to_case):
                    fp.edge.append(s)
        return fp

    def by_lib(self, key, side=None):
        return [f for f in self.footprints if key in f.lib and (side is None or f.side == side)]

    # .................................................................. outline
    @staticmethod
    def _graphic(g, xf):
        kind = g[0]
        if kind.endswith('line'):
            return [('line', xf(*nums(one(g, 'start'))), xf(*nums(one(g, 'end'))))]
        if kind.endswith('arc'):
            return [('arc', xf(*nums(one(g, 'start'))), xf(*nums(one(g, 'mid'))), xf(*nums(one(g, 'end'))))]
        if kind.endswith('curve'):
            pts = [xf(*nums(x)) for x in sub(one(g, 'pts'), 'xy')]
            return bezier_to_segments(pts)
        raise ValueError(kind)

    def _edge_segments(self):
        segs = []
        for g in self.tree:
            if isinstance(g, list) and g and g[0] in ('gr_line', 'gr_arc', 'gr_curve') and one(g, 'layer')[1] == 'Edge.Cuts':
                segs += self._graphic(g, kpt)
        for f in self.footprints:
            segs += f.edge
        return segs

    def outline(self, side):
        """Closed loops (lists of segments) of one half: the outer outline first, then the cut-outs.
        The mouse-bite tabs between the halves are dropped and each opening is closed with a
        straight line along the board edge (the tabs are sanded flush)."""
        def keep(s):
            xs = [p[0] for p in s[1:]]
            ys = [p[1] for p in s[1:]]
            if side == 'L':
                return max(xs) <= TAB_X[0] or (min(ys) <= THUMB_Y and max(xs) < SPLIT_X)
            return min(xs) >= TAB_X[1] or (min(ys) <= THUMB_Y and min(xs) > SPLIT_X)
        segs = [s for s in self.edge if keep(s)]
        return chain(segs)

    def tab_openings(self, side):
        """The straight lines that replace the mouse-bite tabs on this half's outline."""
        out = []
        def keep(s):
            xs = [p[0] for p in s[1:]]
            ys = [p[1] for p in s[1:]]
            if side == 'L':
                return max(xs) <= TAB_X[0] or (min(ys) <= THUMB_Y and max(xs) < SPLIT_X)
            return min(xs) >= TAB_X[1] or (min(ys) <= THUMB_Y and min(xs) > SPLIT_X)
        chain([s for s in self.edge if keep(s)], bridges=out)
        return [b for b in out if math.dist(*b) > 1.0]


def chain(segs, tol=2e-3, bridges=None):
    """Order segments into closed loops; bridge the open ends left by removed tabs (the bridging
    lines are also appended to `bridges` when given)."""
    segs = list(segs)
    loops = []
    def ends(s):
        return s[1], s[-1]
    def rev(s):
        return (s[0],) + tuple(reversed(s[1:]))
    def close(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1]) < tol
    while segs:
        loop = [segs.pop(0)]
        while True:
            head, tail = loop[0][1], loop[-1][-1]
            if close(head, tail) and len(loop) > 1:
                break
            nxt = None
            for i, s in enumerate(segs):
                a, b = ends(s)
                if close(a, tail):
                    nxt = (i, s); break
                if close(b, tail):
                    nxt = (i, rev(s)); break
            if nxt is None:
                # open end: bridge to the nearest free segment end (a removed tab)
                best = None
                for i, s in enumerate(segs):
                    for rv, p in ((False, ends(s)[0]), (True, ends(s)[1])):
                        d = math.hypot(p[0] - tail[0], p[1] - tail[1])
                        if best is None or d < best[0]:
                            best = (d, i, rv, p)
                dh = math.hypot(head[0] - tail[0], head[1] - tail[1])
                if best is None or dh <= best[0]:
                    loop.append(('line', tail, head))
                    break
                d, i, rv, p = best
                assert d < 8.0, f'outline gap of {d:.2f} mm at {tail}'
                loop.append(('line', tail, p))
                if bridges is not None:
                    bridges.append((tail, p))
                s = segs[i]
                nxt = (i, rev(s) if rv else s)
            segs.pop(nxt[0])
            loop.append(nxt[1])
        loops.append(loop)
    def area(loop):
        pts = [s[1] for s in loop]
        return abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts))) / 2)
    loops.sort(key=area, reverse=True)
    return loops


if __name__ == '__main__':
    b = Board()
    print('thickness', b.thickness, 'footprints', len(b.footprints))
    for side in 'LR':
        loops = b.outline(side)
        print(side, 'loops', [len(l) for l in loops],
              'arcs', sum(s[0] == 'arc' for l in loops for s in l), 'lines', sum(s[0] == 'line' for l in loops for s in l))
        xs = [p[0] for s in loops[0] for p in s[1:]]; ys = [p[1] for s in loops[0] for p in s[1:]]
        print('   bbox', round(min(xs), 3), round(max(xs), 3), round(min(ys), 3), round(max(ys), 3))
