"""Things the keep-outs don't cover but must still fit: the switch bodies in the top plate (plastic,
they clip in), the keycaps pressed all the way down and the battery in the bottom. Overlap volumes,
new parts vs the original ones."""
import sys, json, os
sys.path.insert(0, '.')
from build import *
import mill
from common import placed


def bvol(a, b):
    i = a.intersect(b)
    return round(i.Volume(), 4) if i.Solids() else 0.0


parts = kicad_parts()
out = {}
for side in sys.argv[1:] or ['L', 'R']:
    top, otop = load(f'../outputs/TOTEM_alu_top_{side}.step'), load(f'orig/TOTEM_case_ble_top_{side}_V.08.step')
    bot, obot = load(f'../outputs/TOTEM_alu_bottom_{side}.step'), load(f'orig/TOTEM_tenting_live_bottom_{side}.step')
    sw = []
    for name, shp in parts:
        bb = shp.BoundingBox()
        if bb.zmax <= 8 or (side == 'L') != ((bb.xmin + bb.xmax) / 2 < 150):
            continue
        for s in shp.Solids():
            if s.BoundingBox().zmin >= 0:
                sw.append(place(lift(s), side))
    sw = cq.Compound.makeCompound(sw)
    # Case tessellation can have gaps; intersect the original solids instead.
    # the site's keycaps, pressed down the Choc switches' full 3 mm travel
    caps = cq.Compound.makeCompound([mill.mesh_to_solid(m).translate(cq.Vector(0, 0, -3.0)) for m in placed({'keycap'}, side)])
    bat = cq.Compound.makeCompound([mill.mesh_to_solid(m) for m in placed({'battery'}, side)])
    r = {'switch bodies in the top, new / original (mm^3)': (bvol(top, sw), bvol(otop, sw)),
         'keycaps pressed down (3 mm) in the top, new / original (mm^3)': (bvol(top, caps), bvol(otop, caps)),
         'battery in the bottom, new / original (mm^3)': (bvol(bot, bat), bvol(obot, bat))}
    out[side] = r
    for k, v in r.items():
        print(side, k, v, flush=True)
    # (one file per half, so the halves can run at once; fit_check.json joins them)
    json.dump(r, open(f'fit_check_{side}.json', 'w'), indent=1)
json.dump({h: json.load(open(f'fit_check_{h}.json')) for h in 'LR' if os.path.exists(f'fit_check_{h}.json')},
          open('fit_check.json', 'w'), indent=1)
