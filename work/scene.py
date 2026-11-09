"""Triangle meshes of the whole build, per half, for the renders and the 3D viewer.

Layers: top, bottom, insert (the STEP files in outputs/), pcb (true outline), switches (switches
and hot-swap sockets), parts (diodes, power switch, reset button), xiao (module and USB-C boxes),
battery (15 x 22 x 7.5 in its pocket), screws (M2 x 12 socket head), caps (plain choc keycaps).
One mesh per part type is placed at every footprint (all instances share the same model).
"""
import math
from functools import lru_cache
from pathlib import Path

import cadquery as cq
import numpy as np

import build as B
import geom2d as g
import parts as P
from pcb import Board

W = Path(__file__).resolve().parent
OUT = W.parent / 'outputs'
VIEW_SHIFT = 12.0          # the right half is moved this far right in pictures (the cases would touch)
CAP = (7.9, 11.0)          # keycap z range (illustrative)


def tess(shape, tol=0.05, ang=0.3):
    v, f = shape.tessellate(tol, ang)
    if not v:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64)
    return np.array([p.toTuple() for p in v], float), np.array(f, np.int64).reshape(-1, 3)


def merge(meshes):
    meshes = [m for m in meshes if len(m[0])]
    if not meshes:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64)
    V, F, n = [], [], 0
    for v, f in meshes:
        V.append(v); F.append(f + n); n += len(v)
    return np.concatenate(V), np.concatenate(F)


def place(mesh, at, angle, dz=0.0):
    v, f = mesh
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    R = np.array([[c, -s], [s, c]])
    out = v.copy()
    out[:, :2] = v[:, :2] @ R.T + np.array(at)
    out[:, 2] += dz
    return out, f


@lru_cache(maxsize=None)
def board():
    return Board()


@lru_cache(maxsize=None)
def local_model(lib, select):
    """Mesh of one footprint type's model in its footprint frame (top-side solids lifted).
    select: 'switch' (switch body), 'socket', or 'all'."""
    fp = next(f for f in board().footprints if f.lib == lib)
    meshes = []
    for s in P.solids_of(fp.ref, fp.side):
        bb = s.BoundingBox()
        is_switch = 'Kailh_socket' in lib and bb.zmax > 1.2      # the sockets end inside the board
        if select == 'switch' and not is_switch or select == 'socket' and is_switch:
            continue
        if bb.zmax > P.KICAD_TOP + 0.01:
            s = P.lifted(s)
        s = s.translate(cq.Vector(-fp.at[0], -fp.at[1], 0)).rotate(cq.Vector(), cq.Vector(0, 0, 1), -fp.angle)
        meshes.append(tess(s, 0.06))
    return merge(meshes)


def pcb_shape(side):
    loops = board().outline(side)
    f = g.from_loops(loops)
    holes = [g.circle(fp.at, 1.6) for fp in board().footprints if fp.side == side and B.kind(fp) == 'MountingHole']
    f = g.diff(f, *holes)
    return cq.Compound.makeCompound(g.extrude(f, 0, P.PCB_T))


@lru_cache(maxsize=None)
def layers(side):
    """{layer: (V, F)} in the case frame (no view shift)."""
    fps = [f for f in board().footprints if f.side == side]
    L = {}
    L['top'] = tess(cq.importers.importStep(str(OUT / f'TOTEM_alu_top_{side}.step')).val(), 0.02, 0.2)
    L['bottom'] = tess(cq.importers.importStep(str(OUT / f'TOTEM_alu_bottom_{side}.step')).val(), 0.02, 0.2)
    L['insert'] = tess(cq.importers.importStep(str(OUT / f'TOTEM_wood_window_insert_{side}.step')).val(), 0.02, 0.2)
    L['pcb'] = tess(pcb_shape(side), 0.05)
    sw, so = [], []
    pr, caps = [], []
    cap = tess(cq.Workplane().box(17.5, 16.5, CAP[1] - CAP[0]).edges('|Z').fillet(1.2).faces('>Z').edges().fillet(0.6)
               .translate((0, 0, sum(CAP) / 2)).val(), 0.05)
    for fp in fps:
        k = B.kind(fp)
        if k == 'Kailh_socket':
            sw.append(place(local_model(fp.lib, 'switch'), fp.at, fp.angle))
            so.append(place(local_model(fp.lib, 'socket'), fp.at, fp.angle))
            caps.append(place(cap, fp.at, fp.angle))
        elif k in ('Diode_SOD123', 'MSK12C02', 'SKHLLCA010'):
            pr.append(place(local_model(fp.lib, 'all'), fp.at, fp.angle))
    L['switches'] = merge(sw + so)
    L['parts'] = merge(pr)
    L['caps'] = merge(caps)
    xi = next(f for f in fps if B.kind(f) == 'xiao')
    L['xiao'] = merge([tess(cq.Solid.extrudeLinear(B.local_rect(xi, a0, a1, b0, b1).translate(cq.Vector(0, 0, z0)),
                                                   cq.Vector(0, 0, z1 - z0))) for a0, a1, b0, b1, z0, z1 in B.XIAO_BOXES])
    d = design(side)
    bat = d['battery'].Faces()[0].Center()
    L['battery'] = tess(cq.Solid.makeBox(15, 22, 7.5, cq.Vector(bat.x - 7.5, bat.y - 11, B.BATTERY_TOP - 7.5)))
    scr = []
    for h in d['holes']:
        head = cq.Solid.makeCylinder(1.9, 2.0, cq.Vector(h[0], h[1], B.CBORE_SEAT - 2.0))
        shank = cq.Solid.makeCylinder(1.0, 12.0, cq.Vector(h[0], h[1], B.CBORE_SEAT))
        scr += [tess(head), tess(shank)]
    L['screws'] = merge(scr)
    return L


@lru_cache(maxsize=None)
def design(side):
    return B.design(board(), side)


def shifted(side, mesh):
    v, f = mesh
    if side == 'R':
        v = v + np.array((VIEW_SHIFT, 0, 0))
    return v, f
