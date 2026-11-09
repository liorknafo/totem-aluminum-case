"""TOTEM BLE case in aluminum: a parametric 2.5D model generated from the KiCad board.

    ~/.venvs/totem-cad/bin/python -E -s build.py          # both halves
    ~/.venvs/totem-cad/bin/python -E -s build.py L        # one half

Writes outputs/TOTEM_alu_top_{L,R}.step, TOTEM_alu_bottom_{L,R}.step and
TOTEM_wood_window_insert_{L,R}.step, and work/build_{L,R}.json (design data for the checks).

Everything is read from src/totem_0_3.kicad_pcb (outline, footprint positions, pads) and the KiCad 3D
part models (src/comp_all.step). Each part is a block of the case outline with a few extruded
2D regions cut from it: pockets from below, wells from above, holes through. Regions are built from
exact lines and arcs (geom2d.py), so the STEP files hold only planes and cylinders.

Frame: x = KiCad x, y = -KiCad y, z = 0 at the board's bottom face (board 1.6 mm thick, from the board
file; the build stops for any other thickness, see parts.assert_thickness).
"""
import json
import math
import sys
import time
from pathlib import Path

import cadquery as cq

import geom2d as g
import parts as P
from pcb import Board, rot

W = Path(__file__).resolve().parent
OUT = W.parent / 'outputs'

# ===================================================================================== parameters
# --- the rule
C = 0.5                 # aluminum to the board, its copper and every metal part on it
TAB_NUB = 0.3           # what may stay of a snapped mouse-bite tab, proud of the board edge
FIT_MARGIN = 0.02       # the outline's Bezier curves are replaced by arcs within 0.005 mm
COPPER = 0.05           # copper + mask on each face, on top of the 1.6 mm board
SOLDER_SMD = 1.0        # solder fillet height above an SMD pad
SOLDER_DIODE = 0.6      # SOD-123 terminals are ~0.15 thick; their fillets stay under 0.6
SOLDER_THT_FAR = 1.0    # solder on the soldered side of a through-hole pad
SOLDER_THT_NEAR = 0.3   # solder pushed through to the component side of a through-hole pad
FILLET_SPREAD = 0.3     # a fillet spreads this far beyond its pad
DIODE_TOP_GAP = 0.3     # above the diodes' epoxy bodies (an insulator; their metal keeps C)

# --- machining
R_MILL = 1.0            # smallest end mill: Ø2 flat (pockets, slots, corner reliefs)
R_WELL = 1.5            # key wells: Ø3 end mill (6.25 deep)
R_OUTLINE = 3.0         # inside corners of the outer outline (profile with a Ø6 end mill or smaller)
T_MIN = 1.0             # thinnest floor, roof or web designed in (aluminum)

# --- heights (z)
Z_TOP = 10.5            # top surface (top part from 1/2" plate: 9.9 tall)
PLATE_TOP = 3.60        # switch plate top: the shoulder of the choc top housing rests here (the build
                        # checks it against the switch model, and that the latches catch under the plate)
PLATE_T = 1.2           # choc clip ledge
PLATE_BOT = PLATE_TOP - PLATE_T   # 2.40: the top's whole underside, 0.80 above the board
WELL_FLOOR = 4.25       # keycap wells around each switch zone (keycap skirt pressed ~5.0)
Z_SEAM = 0.6            # top/bottom joint, under the power switch (its lowest metal is at 1.13)
FLOOR = -2.6            # bottom cavity floor (sockets reach -2.04)
Z_BOT = -11.4           # underside of the bottom (bottom from 7/8" plate: 12.0 tall)

# --- outline
WALL = 1.8              # side wall outside the 0.5 mm gap; outline = board grown by C + WALL
BULGE_WALL = 1.8        # wall in front of a part that overhangs the board edge (reset button)

# --- keys (Kailh choc)
KEYCAP = (17.5, 16.5)   # choc keycap
KEYCAP_GAP = 1.0        # keycap to well wall
KEYCAP_MIN_GAP = 0.3    # where a well has to give way to a pocket or a screw
SWITCH_ZONE = 15.7      # square around the 15 mm top housing, down to the plate
SWITCH_ZONE_R = 1.05
SWITCH_HOLE = 13.8      # plate cut-out
TBONE_R = 1.05          # corner reliefs for the Ø2 end mill, pushed sideways into the 4.2 mm webs
TBONE_OFF = (0.25, -1.0)  # relief centre from each corner: outward along the row, inward along the column
DECK_MIN = 3.0          # deck strips between wells narrower than this are removed
RIM = 1.5               # deck rim kept along the outline
POCKET_MERGE = 3.0      # pockets of the same height closer than this are merged
ISLAND_MAX = 150.0      # deck islands (mm²) surrounded by wells are removed

# --- XIAO, window and wood insert (footprint frame a, b; +b toward the USB-C end)
XIAO_BOXES = [(-8.8, 8.8, -10.6, 10.6, 1.66, 5.93),   # module, 17.5 x 21 (no KiCad model), 4.27 tall
              (-4.5, 4.5, 4.5, 11.9, 2.6, 5.93)]      # USB-C receptacle, overhanging the board edge
WINDOW = (-7.0, 7.0, -10.3, 8.0)   # through the roof, from the far end to just short of the USB-C end
WINDOW_R = 2.0
WOOD_T = 3.0            # wood insert: 1.5 plug in the roof + 1.5 flange under it
ROOF_T = 1.5
FLANGE = 1.5            # flange overhang around the window
FLANGE_GAP = 0.2        # flange recess around the flange
PLUG_GAP = 0.1          # plug to window, each side
ROOF_Z = Z_TOP - ROOF_T

# --- openings through the side wall, cut from below (footprint frame a, b; z = top of the opening)
NOTCHES = {
    'MSK12C02': dict(a=(-9.0, 0.0), b=(-7.5, -1.5), z=3.4),     # power slider, 6 mm wide for its travel
    'SKHLLCA010': dict(a=(-2.0, 2.0), b=(3.5, 9.0), z=None),    # reset plunger: 4.0 mm slot for a pin
    'xiao': dict(a=(-6.5, 6.5), b=(8.0, 16.0), z=8.2),          # USB-C plug, 13 mm wide
}
FRONT = {'MSK12C02': ('a', -0.1, -1), 'SKHLLCA010': ('b', 4.05, +1)}   # plastic actuators ahead of the body
TRAVEL = {'MSK12C02': ('b', 1.5)}   # the slider knob moves up to 1.5 mm either way along the switch
# (z=None: the top of the opening is C above the actuator. Every actuator keeps C over its travel.)

# --- screws: M2 socket head from below, through the no-net mounting pads, into M2 threads in the top
CLEAR_D = 2.4
CBORE_D = 4.4           # counterbore for the M2 head (Ø3.8)
CBORE_SEAT = -5.2       # head seat; the head (2.0) stays inside even in a leg recess (roof -7.3)
TAP_D = 1.6             # M2 tap drill
TAP_DEPTH = 5.5         # thread from the upper spacer seat (2.75 .. 8.25; M2x12 screws end at 6.8)
# spacers at the no-net mounting pads (insulating, e.g. nylon, OD <= SPACER_D): they stop SPACER_GAP
# from the pad copper above and below the board and sit in shallow seats in the roof and the floor
SPACER_D = 5.0
SEAT_D = 5.4
SPACER_GAP = 0.1
UPPER_SPACER = 1.0      # between the board and the top
LOWER_SPACER = 3.0      # between the bottom and the board
UPPER_SEAT = P.PCB_T + COPPER + SPACER_GAP + UPPER_SPACER      # 2.75
LOWER_SEAT = -COPPER - SPACER_GAP - LOWER_SPACER               # -3.15
SCREW_KEEP = 2.5        # wells keep this far from a screw axis

# --- bottom: battery, tenting legs, feet (left-half positions; the right half is mirrored)
MIRROR_X = 150.0
BATTERY = (16.0, 23.0)  # pocket for a 15 x 22 x 7.5 LiPo
BATTERY_R = 1.5
BATTERY_AT = (-19.0, -1.0)   # from the midpoint of the battery pads
BATTERY_TOP = -2.2      # the battery's top may sit just under the sockets (-2.04)
BATTERY_FLOOR = BATTERY_TOP - 7.5
LEGS = [((112.4, -58.6), 0.0), ((115.13, -117.1), -30.0)]   # adhesive tenting feet
LEG = (57.4, 19.2)
LEG_R = 3.5
LEG_ROOF = -7.3         # 4.1 deep
LEG_WALL = 1.6          # side wall next to a leg recess (the recess is moved inward if needed)
FEET = [(35.62, -54.64), (42.12, -118.65), (77.58, -118.65), (136.85, -76.34), (136.85, -101.73)]
FOOT_D = 9.0            # 8.5 mm rubber feet
FOOT_DEPTH = 0.4

# ===================================================================================== helpers
T0 = time.monotonic()


def log(*a):
    print(f'[{time.monotonic() - T0:5.1f}s]', *a, flush=True)


def kind(fp):
    for key in ('Kailh_socket', 'Diode_SOD123', 'xiao', 'MSK12C02', 'SKHLLCA010', 'BatteryPad', 'MJ-4PP-9',
                'MountingHole', 'mousebites'):
        if key in fp.lib:
            return key
    return 'other'


def mirror(p, side):
    return p if side == 'L' else (2 * MIRROR_X - p[0], p[1])


def local_rect(fp, a0, a1, b0, b1, grow=0.0):
    """Footprint-frame box grown by `grow` (a rounded rectangle = box + disc of radius grow)."""
    c = fp.to_case(0, 0)
    ca = ((a0 + a1) / 2, (b0 + b1) / 2)
    off = rot(ca, fp.angle)
    return g.rrect((c[0] + off[0], c[1] + off[1]), a1 - a0 + 2 * grow, b1 - b0 + 2 * grow, fp.angle, grow)


def pad_region(p, grow):
    w, h = p.size
    if p.shape == 'circle':
        return g.circle(p.at, w / 2 + grow)
    if p.shape == 'oval':
        return g.stadium(p.at, w + 2 * grow, h + 2 * grow, p.angle)
    return g.rrect(p.at, w + 2 * grow, h + 2 * grow, p.angle, grow)


def solder(fp, pad):
    """(solder above the top face, solder below the bottom face) for a copper pad."""
    k = kind(fp)
    if k == 'MJ-4PP-9':
        return 0.0, 0.0                                  # TRRS jack: not fitted in the BLE build
    if k == 'Kailh_socket':
        if pad.kind == 'smd':
            return 0.0, SOLDER_SMD                       # socket contacts, soldered under the board
        return 0.0, 0.0                                  # switch-pin rings: hot-swap, never soldered
    if pad.kind == 'smd':
        s = SOLDER_DIODE if k == 'Diode_SOD123' else SOLDER_SMD
        return (s, 0.0) if pad.top else (0.0, s)
    if k in ('xiao', 'BatteryPad'):
        return SOLDER_THT_FAR, SOLDER_THT_FAR            # castellations / battery wires: soldered on top
    return SOLDER_THT_NEAR, SOLDER_THT_FAR               # through-hole parts soldered from below


# ===================================================================================== keep-outs
R_POCKET = R_MILL + 0.05   # pockets are drawn as shapes rounded with at least this radius


def keepouts(board, side):
    """Everything on one half of the board, as dicts:
       region  the keep-out in plan (outline grown by its side clearance),
       mill    the same grown to at least R_POCKET and rounded, so a Ø2 end mill can cut it,
       z       for things above the board: the lowest the top may come; below it: the highest the
               bottom may come,
       ref, what."""
    above, below = [], []

    def add(lst, fp, what, make, grow, z):
        lst.append(dict(ref=fp.ref, what=what, region=make(grow), mill=make(max(grow, R_POCKET)), z=z))

    for fp in board.footprints:
        if fp.side != side:
            continue
        k = kind(fp)
        if k in ('MountingHole', 'mousebites'):
            continue
        # copper pads
        for pad in fp.pads:
            if pad.kind == 'np_thru_hole' or not pad.copper:
                continue
            st, sb = solder(fp, pad)
            make = lambda gr, pad=pad: pad_region(pad, gr)
            if pad.top:
                add(above, fp, f'pad {pad.number}', make, C + (FILLET_SPREAD if st else 0), P.PCB_T + COPPER + st + C)
            if pad.bottom:
                add(below, fp, f'pad {pad.number}', make, C + (FILLET_SPREAD if sb else 0), -COPPER - sb - C)
        # part bodies
        if k == 'MJ-4PP-9':
            continue                                     # TRRS jack: not fitted in the BLE build
        if k == 'xiao':
            for a0, a1, b0, b1, z0, z1 in XIAO_BOXES:
                add(above, fp, 'body', lambda gr, r=(a0, a1, b0, b1): local_rect(fp, *r, gr), C, z1 + C)
            continue
        fr = FRONT.get(k)
        for bx in P.boxes_for(board, fp):
            if k == 'Kailh_socket' and not bx['below']:
                continue                                 # plastic switch bodies clip into the plate
            if bx['below']:
                add(below, fp, 'body', lambda gr, bx=bx: local_rect(fp, bx['a0'], bx['a1'], bx['b0'], bx['b1'], gr),
                    C, bx['z0'] - C)
                continue
            if fr:
                # the plastic actuator ahead of the body gets an opening instead (NOTCHES)
                axis, val, sgn = fr
                bx = dict(bx)
                if sgn < 0:
                    bx[axis + '0'] = max(bx[axis + '0'], val)
                else:
                    bx[axis + '1'] = min(bx[axis + '1'], val)
            gap = DIODE_TOP_GAP if k == 'Diode_SOD123' else C
            add(above, fp, 'body', lambda gr, bx=bx: local_rect(fp, bx['a0'], bx['a1'], bx['b0'], bx['b1'], gr),
                C, bx['z1'] + gap)
    return above, below


def front_boxes(board, side):
    """The plastic actuators (power slider knob, reset plunger) as boxes in their footprint frame."""
    out = []
    for fp in board.footprints:
        if fp.side != side or kind(fp) not in FRONT:
            continue
        bx = P.front_box(fp, *FRONT[kind(fp)])
        if bx:
            out.append((fp, bx))
    return out


# ===================================================================================== design
SHOULDER_HALF = 7.3     # the top housing (15 mm) is wider than this from the switch centre; the latches are not


def switch_seat(fp):
    """(shoulder z, latch top z) of a switch footprint's model: where its 15 mm top housing starts, and
    the highest point of the latches below it."""
    import numpy as np
    pts = []
    for s in P.template(fp):
        if s.BoundingBox().zmax < P.PCB_T + 0.4:
            continue                                   # the hot-swap socket
        v, _ = s.tessellate(0.01, 0.2)
        pts.append(np.array([p.toTuple() for p in v] + [p.toTuple() for p in s.Vertices()]))
    Q = np.concatenate(pts)
    r = np.maximum(abs(Q[:, 0]), abs(Q[:, 1]))
    shoulder = Q[r > SHOULDER_HALF, 2].min()
    latch = Q[(r > SWITCH_HOLE / 2 + 0.05) & (r <= SHOULDER_HALF) & (Q[:, 2] < shoulder) & (Q[:, 2] > P.PCB_T + 0.1), 2].max()
    return float(shoulder), float(latch)


def design(board, side):
    """All 2D regions and heights of one half."""
    P.assert_thickness()
    d = {}
    loops = board.outline(side)
    d['board'] = g.from_loops(loops)
    board_outer = g.from_loops(loops[:1])
    above, below = keepouts(board, side)
    d['above'], d['below'] = above, below
    fps = [f for f in board.footprints if f.side == side]
    keys = [f for f in fps if kind(f) == 'Kailh_socket']
    # the plate must carry every switch on its shoulder, with the latches catching under it
    for key in {P.model_key(k): k for k in keys}.values():
        shoulder, latch = switch_seat(key)
        assert abs(shoulder - PLATE_TOP) < 0.005, f'{key.ref}: switch shoulder at z {shoulder:.3f}, PLATE_TOP is {PLATE_TOP}'
        assert latch <= PLATE_BOT - 0.05, f'{key.ref}: latch top at z {latch:.3f} does not clear the plate underside {PLATE_BOT}'
        d['switch_seat'] = (round(shoulder, 3), round(latch, 3))
    holes = [f.at for f in fps if kind(f) == 'MountingHole']
    xiao = next(f for f in fps if kind(f) == 'xiao')
    d['keys'], d['holes'], d['xiao'] = keys, holes, xiao

    # cavity: the board grown by C, every corner cuttable with the Ø2 mill. Where the panel tabs were
    # snapped off, the board may keep nubs up to TAB_NUB proud of its edge: the cavity allows for them.
    nubs = []
    for p0, p1 in board.tab_openings(side):
        mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
        out = (1.0 if side == 'L' else -1.0, 0.0)          # the tabs point toward the other half
        L = math.dist(p0, p1)
        nubs.append(g.rrect((mid[0] + out[0] * (TAB_NUB / 2 - 0.05), mid[1]), TAB_NUB + 0.1, L, 0))   # overlaps the edge by 0.1
    d['nubs'] = nubs
    cav = g.mill_fix(g.offset(g.union(board_outer, *nubs), C + FIT_MARGIN), R_MILL)
    d['cavity'] = cav

    # outer outline: board grown by C + WALL, grown around parts that overhang the board edge
    # (the reset button) and smoothed; notches handle the actuators and the USB-C plug
    grow = [g.offset(board_outer, C + WALL)]
    for it in above:
        fp = next(f for f in fps if f.ref == it['ref'])
        if kind(fp) == 'SKHLLCA010' and it['what'] == 'body':
            grow.append(g.offset(it['region'], BULGE_WALL))
    d['outline'] = outline = g.closing(g.union(*grow), R_OUTLINE)

    # ---- top: pockets from below, one per part at the height of its tallest item, merged per height
    # Each item (pad with its solder, body) is pocketed only as high as it needs; the pocket at a
    # height covers every item at least that tall (so each level is one machinable region), items of
    # the same height closer than POCKET_MERGE are merged, corners get reliefs for the Ø2 mill.
    tall = [dict(it) for it in above if it['z'] > PLATE_BOT + 1e-6]
    # notches through the wall (open at the seam) and the wood flange recess under the roof take
    # part in the same merge, so no thin fins stand between neighbouring pockets
    acts = front_boxes(board, side)
    for fp in fps:
        n = NOTCHES.get(kind(fp))
        if n:
            z = n['z']
            if z is None:
                z = max(bx['z1'] for f2, bx in acts if f2.ref == fp.ref) + C
            tall.append(dict(ref=fp.ref + ' opening', what='opening', region=local_rect(fp, *n['a'], *n['b']), z=z))
    # seats for the upper spacers in the roof
    for h in holes:
        tall.append(dict(ref='spacer seat', what='seat', region=g.circle(h, SEAT_D / 2), z=UPPER_SEAT))
    wa0, wa1, wb0, wb1 = WINDOW
    R = WINDOW_R
    fl = local_rect(xiao, wa0 - FLANGE + R, wa1 + FLANGE - R, wb0 - FLANGE + R, wb1 + FLANGE - R, R + FLANGE_GAP)
    tall.append(dict(ref=xiao.ref + ' wood flange', what='flange', region=fl, z=ROOF_Z))
    pockets = []
    for z in sorted({round(it['z'], 3) for it in tall}):
        items = [it for it in tall if it['z'] >= z - 1e-6]
        reg = g.closing(g.union(*[it['region'] for it in items]), POCKET_MERGE / 2)
        reg = g.mill_fix(reg, R_MILL, keep_out=outline)
        pockets.append(dict(region=reg, z=z, what=sorted({it['ref'] for it in items if abs(it['z'] - z) < 1e-6})))
    d['pockets'] = pockets
    # every plastic actuator, over its travel and grown by C, lies in openings at least C above it
    for fp, bx in acts:
        ax, t = TRAVEL.get(kind(fp), ('b', 0.0))
        a0, a1, b0, b1 = bx['a0'] - C, bx['a1'] + C, bx['b0'] - C, bx['b1'] + C
        if ax == 'a':
            a0, a1 = a0 - t, a1 + t
        else:
            b0, b1 = b0 - t, b1 + t
        need = g.inter(local_rect(fp, a0, a1, b0, b1), outline)
        room = g.union(*[p['region'] for p in pockets if p['z'] >= bx['z1'] + C - 1e-6])
        short = g.area(g.diff(need, room))
        assert short < 1e-3 and bx['z0'] - C >= Z_SEAM, f'{fp.ref}: actuator closer than {C} mm ({short:.3f} mm²)'
    d['window'] = g.union(local_rect(xiao, wa0 + R, wa1 - R, wb0 + R, wb1 - R, R))

    # ---- top: wells from above. Keycap wells, then the deck is kept around tall pockets (T_MIN
    # over them), around the screws and along the rim; deck bits narrower than DECK_MIN go.
    zones = g.union(*[g.rrect(k.at, SWITCH_ZONE, SWITCH_ZONE, k.angle, SWITCH_ZONE_R) for k in keys])
    wells = g.union(*[g.rrect(k.at, KEYCAP[0] + 2 * KEYCAP_GAP, KEYCAP[1] + 2 * KEYCAP_GAP, k.angle, R_WELL) for k in keys])
    wells = g.closing(wells, DECK_MIN / 2)
    high = [p['region'] for p in pockets if p['z'] > WELL_FLOOR - T_MIN]
    stay = [g.offset(g.union(*high), T_MIN + 0.05)] if high else []
    stay += [g.circle(h, SCREW_KEEP) for h in holes]
    stay.append(g.diff(g.offset(outline, 10), g.offset(outline, -RIM)))
    wells = g.diff(wells, *stay)
    # deck islands surrounded by wells (posts between key groups) go too
    deck = sorted(g.faces(g.diff(outline, wells)), key=lambda f: -f.Area())
    stay_all = g.union(*stay)
    islands = [f for f in deck[1:] if f.Area() < ISLAND_MAX and g.area(g.inter(f, stay_all)) < 1e-6]
    wells = g.mill_fix(g.union(wells, zones, *islands), R_WELL)
    d['zones'], d['wells'] = zones, wells
    for k in keys:
        cap = g.rrect(k.at, KEYCAP[0] + 2 * KEYCAP_MIN_GAP, KEYCAP[1] + 2 * KEYCAP_MIN_GAP, k.angle)
        short = g.area(g.diff(cap, wells))
        assert short < 1e-3, f'{k.ref}: keycap closer than {KEYCAP_MIN_GAP} mm to the deck ({short:.3f} mm²)'

    # switch cut-outs with corner reliefs
    holes_sw = []
    for k in keys:
        sq = g.rrect(k.at, SWITCH_HOLE, SWITCH_HOLE, k.angle)
        discs = []
        h = SWITCH_HOLE / 2
        for sa in (-1, 1):
            for sb in (-1, 1):
                off = rot((sa * (h + TBONE_OFF[0]), sb * (h + TBONE_OFF[1])), k.angle)
                discs.append(g.circle((k.at[0] + off[0], k.at[1] + off[1]), TBONE_R))
        holes_sw.append(g.union(sq, *discs))
    d['switch_holes'] = g.union(*holes_sw)
    # the corner reliefs reach past the switch zone: open them up through the well floor too, so no
    # skin is left over them
    d['zones'] = g.union(d['zones'], d['switch_holes'])

    # ---- bottom
    bat_pads = [f.at for f in fps if kind(f) == 'BatteryPad']
    mid = (sum(p[0] for p in bat_pads) / len(bat_pads), sum(p[1] for p in bat_pads) / len(bat_pads))
    off = BATTERY_AT if side == 'L' else (-BATTERY_AT[0], BATTERY_AT[1])
    d['battery'] = g.rrect((mid[0] + off[0], mid[1] + off[1]), BATTERY[0], BATTERY[1], 0, BATTERY_R)
    d['legs'], d['leg_places'] = place_legs(side, outline)
    d['feet'] = g.union(*[g.circle(mirror(c, side), FOOT_D / 2) for c in FEET])
    # anything below the board reaching under the floor, or overhanging the board edge
    low = [f"{it['ref']} {it['what']}" for it in below if it['z'] < FLOOR + 1e-6]
    assert not low, ('parts below the floor', low)
    # bottom-side items overhanging the board edge: cut into the rim only as deep as each needs
    out_of_cav = g.diff(g.union(*[it['region'] for it in below]), cav)
    over = [it for it in below if g.area(out_of_cav) > 1e-3 and g.distance(it['region'], out_of_cav) < 1e-6]
    d['bottom_cavity'] = cav
    d['bottom_over'] = []
    for z in sorted({round(it['z'], 3) for it in over}, reverse=True):
        items = [it for it in over if it['z'] <= z + 1e-6]
        reg = g.mill_fix(g.union(cav, *[it['region'] for it in items]), R_MILL, keep_out=outline)
        d['bottom_over'].append(dict(region=g.diff(reg, cav), z=z))
    return d


def place_legs(side, outline):
    """Tenting-leg recesses at their nominal places, moved inward across their width where needed
    so the side wall next to them stays LEG_WALL thick."""
    outside = g.diff(g.offset(outline, 20), outline)
    regs, places = [], []
    for c, a in LEGS:
        c, a = mirror(c, side), (a if side == 'L' else -a)
        n = rot((0, 1), a)
        for _ in range(6):
            r = g.rrect(c, LEG[0], LEG[1], a, LEG_R)
            dd = g.distance(r, outside)
            if dd >= LEG_WALL - 1e-3:
                break
            step = LEG_WALL - dd + 0.02
            # move along the leg's short axis, away from the outline
            cands = [(c[0] + s * step * n[0], c[1] + s * step * n[1]) for s in (1, -1)]
            c = max(cands, key=lambda q: g.distance(g.rrect(q, LEG[0], LEG[1], a, LEG_R), outside))
        assert dd >= LEG_WALL - 1e-3, ('leg recess too close to the side', c)
        regs.append(r)
        places.append((round(c[0], 2), round(c[1], 2), a, round(dd, 2)))
    return g.union(*regs), places


# ===================================================================================== solids
def prisms(region, z0, z1):
    return g.extrude(region, z0, z1)


def cut(blank, tools):
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.TopTools import TopTools_ListOfShape
    args, tl = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(blank.wrapped)
    for t in tools:
        tl.Append(t.wrapped)
    op = BRepAlgoAPI_Cut()
    op.SetArguments(args); op.SetTools(tl)
    op.SetRunParallel(True)
    op.Build()
    assert op.IsDone(), 'cut failed'
    res = cq.Shape.cast(op.Shape())
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    u = ShapeUpgrade_UnifySameDomain(res.wrapped, True, True, True)
    u.Build()
    res = cq.Shape.cast(u.Shape())
    sols = sorted(res.Solids(), key=lambda s: -s.Volume())
    return sols


def hole(c, d, z0, z1):
    return cq.Solid.makeCylinder(d / 2, z1 - z0, cq.Vector(c[0], c[1], z0))


def make_top(d):
    tools = []
    tools += prisms(d['cavity'], Z_SEAM - 1, PLATE_BOT)
    for p in d['pockets']:
        tools += prisms(p['region'], Z_SEAM - 1, p['z'])
    tools += prisms(d['switch_holes'], PLATE_BOT - 0.5, PLATE_TOP + 0.5)
    tools += prisms(d['zones'], PLATE_TOP, Z_TOP + 1)
    tools += prisms(d['wells'], WELL_FLOOR, Z_TOP + 1)
    tools += prisms(d['window'], ROOF_Z - 0.5, Z_TOP + 1)
    for h in d['holes']:
        tools.append(hole(h, TAP_D, UPPER_SEAT - 0.5, UPPER_SEAT + TAP_DEPTH))
    blank = prisms(d['outline'], Z_SEAM, Z_TOP)[0]
    sols = cut(blank, tools)
    return sols, len(tools)


def make_bottom(d):
    tools = []
    tools += prisms(d['bottom_cavity'], FLOOR, Z_SEAM + 1)
    for p in d['bottom_over']:
        tools += prisms(p['region'], p['z'], Z_SEAM + 1)
    tools += prisms(d['battery'], BATTERY_FLOOR, FLOOR + 0.5)
    tools += prisms(d['legs'], Z_BOT - 1, LEG_ROOF)
    tools += prisms(d['feet'], Z_BOT - 1, Z_BOT + FOOT_DEPTH)
    for h in d['holes']:
        tools.append(hole(h, CLEAR_D, Z_BOT - 1, FLOOR + 0.5))
        tools.append(hole(h, SEAT_D, LOWER_SEAT, FLOOR + 0.5))
        tools.append(hole(h, CBORE_D, Z_BOT - 1, CBORE_SEAT))
    blank = prisms(d['outline'], Z_BOT, Z_SEAM)[0]
    sols = cut(blank, tools)
    return sols, len(tools)


def make_insert(d):
    xiao = d['xiao']
    wa0, wa1, wb0, wb1 = WINDOW
    plug = local_rect(xiao, wa0 + WINDOW_R, wa1 - WINDOW_R, wb0 + WINDOW_R, wb1 - WINDOW_R, WINDOW_R - PLUG_GAP)
    fl = local_rect(xiao, wa0 - FLANGE + WINDOW_R, wa1 + FLANGE - WINDOW_R, wb0 - FLANGE + WINDOW_R, wb1 + FLANGE - WINDOW_R, WINDOW_R)
    s = prisms(g.union(plug), ROOF_Z, Z_TOP)[0].fuse(prisms(g.union(fl), Z_TOP - WOOD_T, ROOF_Z)[0]).clean()
    return s


def export(shape, path):
    cq.exporters.export(shape, str(path))
    back = cq.importers.importStep(str(path)).val()
    assert back.isValid() and len(back.Solids()) == 1, (path.name, back.isValid(), len(back.Solids()))
    assert abs(back.Volume() - shape.Volume()) < 1e-6 * shape.Volume() + 1e-3, path.name
    return back


def face_types(shape):
    out = {}
    for f in shape.Faces():
        out[f.geomType()] = out.get(f.geomType(), 0) + 1
    return out


def build(board, side):
    t = time.monotonic()
    timing = {}
    log(side, 'design')
    d = design(board, side)
    timing['2D design'] = time.monotonic() - t; t = time.monotonic()
    log(side, 'regions ready:', len(d['pockets']), 'pocket levels,', len(d['keys']), 'keys,', len(d['holes']), 'screws')
    top, nt = make_top(d)
    log(side, 'top:', len(top), 'solid(s) from', nt, 'tools, volume', round(top[0].Volume(), 1))
    bot, nb = make_bottom(d)
    log(side, 'bottom:', len(bot), 'solid(s) from', nb, 'tools, volume', round(bot[0].Volume(), 1))
    ins = make_insert(d)
    timing['solids'] = time.monotonic() - t; t = time.monotonic()
    assert len(top) == 1 and len(bot) == 1, 'a part fell apart'
    OUT.mkdir(exist_ok=True)
    res = {}
    for name, s in (('top', top[0]), ('bottom', bot[0]), ('insert', ins)):
        fn = {'top': f'TOTEM_alu_top_{side}.step', 'bottom': f'TOTEM_alu_bottom_{side}.step',
              'insert': f'TOTEM_wood_window_insert_{side}.step'}[name]
        back = export(s, OUT / fn)
        bb = back.BoundingBox()
        res[name] = dict(file=fn, valid=back.isValid(), volume=round(back.Volume(), 1), faces=face_types(back),
                         size=[round(bb.xlen, 2), round(bb.ylen, 2), round(bb.zlen, 2)], z=[round(bb.zmin, 2), round(bb.zmax, 2)])
        log(side, name, res[name])
    timing['STEP write and read-back'] = time.monotonic() - t
    res['timing'] = {k: round(v, 2) for k, v in timing.items()}
    return d, res


if __name__ == '__main__':
    sides = [a for a in sys.argv[1:] if a in ('L', 'R')] or ['L', 'R']
    board = Board()
    P.part_boxes(board)
    t_load = time.monotonic() - T0
    log('board and part boxes loaded')
    for side in sides:
        d, res = build(board, side)
        res['timing'] = {'start, board and part boxes': round(t_load, 2), **res['timing']}
        (W / f'build_{side}.json').write_text(json.dumps(res, indent=1))
    log('done')
