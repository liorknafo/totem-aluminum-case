"""Independent checks of the aluminum case parts against the exact KiCad PCB, parts and pads."""
import sys, json
sys.path.insert(0, '.')
from build import *
from OCP.BRepExtrema import BRepExtrema_DistShapeShape


def dist(a, b, local=None):
    """Exact minimum distance. With `local`, `a` is first clipped to b's box grown by `local` mm
    (distances above `local` are reported as > local)."""
    if local is not None:
        bb = b.BoundingBox()
        a = a.intersect(box(bb.xmin - local, bb.xmax + local, bb.ymin - local, bb.ymax + local,
                            bb.zmin - local, bb.zmax + local))
        if not a.Solids():
            return float(local), None
    d = BRepExtrema_DistShapeShape()
    d.LoadS1(a.wrapped); d.LoadS2(b.wrapped)
    d.Perform()
    assert d.IsDone(), 'distance calculation failed'
    p1, p2 = d.PointOnShape1(1), d.PointOnShape2(1)
    return d.Value(), (round(p1.X(), 2), round(p1.Y(), 2), round(p1.Z(), 2))


def pcb_16(side):
    """The board as the case sees it: KiCad outline, 0..1.6 thick."""
    pcb = pcb_solid(side)
    faces = pcb.intersect(box(-50, 450, -300, 50, 0.74, 0.76)).Faces()
    face = max((f for f in faces if abs(f.normalAt().z) > 0.99 and f.Center().z > 0.755), key=lambda f: f.Area())
    return cq.Solid.extrudeLinear(face.translate(cq.Vector(0, 0, -face.Center().z)), cq.Vector(0, 0, PCB_TOP))


def check(side, parts):
    rep = {}
    top = load(f'../outputs/TOTEM_alu_top_{side}.step')
    bot = load(f'../outputs/TOTEM_alu_bottom_{side}.step')
    ins = load(f'../outputs/TOTEM_wood_window_insert_{side}.step')
    otop = load(f'orig/TOTEM_case_ble_top_{side}_V.08.step')
    obot = load(f'orig/TOTEM_tenting_live_bottom_{side}.step')
    board = pcb_16(side)
    allowed = cq.Compound.makeCompound([cq.Solid.makeCylinder(PAD_R + 0.01, 3, cq.Vector(x, y, PCB_TOP - 0.01)) for x, y in SCREWS[side]])
    top_no_boss = top.cut(allowed)
    for name, a, b in [('top (except the 4 pad bosses) to PCB', top_no_boss, board),
                       ('bottom to PCB', bot, board),
                       ('original top to PCB', otop.cut(allowed), board),
                       ('original bottom to PCB', obot, board)]:
        rep[name] = dist(a, b)
    # bosses only touch inside the floating pad
    for x, y in SCREWS[side]:
        # around the screw only (a ±4 mm box would also catch the outer wall where it passes close by)
        boss = top.intersect(cq.Solid.makeCylinder(PAD_R + 0.5, 0.02, cq.Vector(x, y, PCB_TOP - 0.01)))
        if not boss.Solids():
            rep.setdefault('boss contact outside r=2.5 (mm^3, must be 0)', []).append('no contact at z=1.6')
            continue
        far = boss.cut(cq.Solid.makeCylinder(PAD_R + 0.001, 1, cq.Vector(x, y, PCB_TOP - 0.5)))
        rep.setdefault('boss contact outside r=2.5 (mm^3, must be 0)', []).append(round(far.Volume(), 6) if far.Solids() else 0.0)
    # every KiCad part on this half, exact shapes
    worst_t, worst_b = (99, None, None), (99, None, None)
    worst_d = (99, None, None)
    for name, shp in parts:
        bb = shp.BoundingBox()
        if (side == 'L') != ((bb.xmin + bb.xmax) / 2 < 150):
            continue
        is_switch = bb.zmax > 8
        if name.startswith('J'):
            continue  # TRRS jack not fitted in the BLE build
        for s in shp.Solids():
            sb = s.BoundingBox()
            if is_switch and sb.zmin >= 0:
                continue
            if is_switch:
                s = s.intersect(box(-50, 450, -300, 50, -10, 0))
                if not s.Solids():
                    continue
            if name in ('RSW1', 'RST') and s.Volume() > 1:
                # metal body only; the plastic plunger (last RESET_PLUNGER mm) sits in the original hole
                plunger = place(s.intersect(box(sb.xmin - 1, sb.xmax + 1, sb.ymax - RESET_PLUNGER, sb.ymax + 1, sb.zmin - 1, sb.zmax + 1)), side)
                rep['reset plunger (plastic) to top / bottom'] = (round(dist(top, plunger, 2.0)[0], 3), round(dist(bot, plunger, 2.0)[0], 3))
                s = s.intersect(box(sb.xmin - 1, sb.xmax + 1, sb.ymin - 1, sb.ymax - RESET_PLUNGER, sb.zmin - 1, sb.zmax + 1))
            if sb.zmin > 0.75:
                s = lift(s)
            s = place(s, side)
            dt, pt = dist(top, s, 2.0); db, pb = dist(bot, s, 2.0)
            if name.startswith('D'):  # diode: epoxy body + leads in one solid; leads covered by the pad check
                if dt < worst_d[0]: worst_d = (dt, name, pt)
                dt = 99
            if dt < worst_t[0]: worst_t = (dt, name, pt)
            if db < worst_b[0]: worst_b = (db, name, pb)
    rep['top to nearest part (switch bodies, diodes excluded)'] = worst_t
    rep['top to nearest diode (epoxy top may be 0.3)'] = worst_d
    rep['bottom to nearest part'] = worst_b
    (x, y), a = XIAO[side]
    xiao = box(-8.9, 8.9, -10.6, 11.9, 1.66, 5.93).rotate(cq.Vector(), cq.Vector(0, 0, 1), a).translate(cq.Vector(x, y, 0))
    rep['top to XIAO'] = dist(top, xiao); rep['bottom to XIAO'] = dist(bot, xiao); rep['wood insert to XIAO'] = dist(ins, xiao)
    # exposed copper pads (not the floating mounting pads)
    pads = [place(lift(p) if p.BoundingBox().zmin > 0.75 else p, side) for p in load('../src/pads.step').Solids()
            if (side == 'L') == ((p.BoundingBox().xmin + p.BoundingBox().xmax) / 2 < 150)]
    pads = [p for p in pads if not any(np.hypot(p.Center().x - sx, p.Center().y - sy) < 0.5 for sx, sy in SCREWS[side])]
    wt, wb = (99, None), (99, None)
    for p in pads:
        dt = dist(top, p, 2.0); db = dist(bot, p, 2.0)
        wt = min(wt, dt, key=lambda v: v[0]); wb = min(wb, db, key=lambda v: v[0])
    rep['top to exposed pads'] = wt; rep['bottom to exposed pads'] = wb
    # assembly
    rep['top/bottom overlap mm^3'] = round(top.intersect(bot).Volume(), 6)
    rep['top/bottom gap at seam'] = dist(top, bot)
    rep['insert/top overlap mm^3'] = round(ins.intersect(top).Volume(), 6)
    for nm, s in [('top', top), ('bottom', bot), ('insert', ins)]:
        b = s.BoundingBox()
        rep[f'{nm} size x,y,z'] = (round(b.xlen, 2), round(b.ylen, 2), round(b.zlen, 2), 'z', round(b.zmin, 2), round(b.zmax, 2))
        rep[f'{nm} valid, solids, volume'] = (s.isValid(), len(s.Solids()), round(s.Volume(), 1))
    rep['volume removed from top, mm^3'] = round(otop.Volume() - top.Volume(), 1)
    rep['volume added to bottom, mm^3'] = round(bot.Volume() - obot.Volume(), 1)
    return rep


if __name__ == '__main__':
    parts = kicad_parts()
    out = {}
    for s in sys.argv[1:] or ['L', 'R']:
        out[s] = check(s, parts)
        for k, v in out[s].items():
            print(s, k, ':', v, flush=True)
    json.dump(out, open('verify.json', 'w'), indent=1, default=str)
