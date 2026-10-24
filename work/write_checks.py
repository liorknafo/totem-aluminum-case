"""Write outputs/CHECKS.md from verify.json, the analyzer logs and the thin-wall comparison."""
import json, re, shutil
import re as _re
from pathlib import Path

W = Path(__file__).resolve().parent
OUT = W.parent / 'outputs'
v = json.load(open(W / 'verify.json'))


def d(side, key):
    return float(str(v[side][key]).split(',')[0].strip('([ '))


def spots(f):
    out = []
    for l in open(W / f):
        m = re.search(r'around \(([-\d.]+),([-\d.]+)\) span ([\d.]+)x([\d.]+) min ([\d.]+) mm\s+n=(\d+)', l)
        if m:
            out.append(tuple(float(x) for x in m.groups()))
    return out


def thinner(side, part, orig):
    o, n = spots(f'thin_{orig}_{side}.txt'), spots(f'thin_{part}_{side}.txt')
    rows = []
    for s in n:
        if s[5] < 5:
            continue  # single grid points on sloped facets
        near = [t for t in o if abs(s[0] - t[0]) < 1.5 and abs(s[1] - t[1]) < 1.5]
        if not near or s[4] < min(t[4] for t in near) - 0.02:
            rows.append((s[0], s[1], s[4], min(t[4] for t in near) if near else None))
    return rows


lines = ['# Checks (measured on the final STEP files)', '',
         'Distances are exact (OpenCASCADE BRepExtrema) between each case part and the KiCad board',
         '(1.6 mm, true outline), every KiCad 3D part on that half, and every exposed copper pad.', '',
         '| | Left | Right | Original (left) |', '|---|---|---|---|']
rows = [('Top to PCB (outside the 4 floating pads)', 'top (except the 4 pad bosses) to PCB', 'original top to PCB'),
        ('Bottom to PCB', 'bottom to PCB', 'original bottom to PCB'),
        ('Top to nearest part (switch bodies and diodes aside)', 'top to nearest part (switch bodies, diodes excluded)', None),
        ('Top to diode epoxy (insulator)', 'top to nearest diode (epoxy top may be 0.3)', None),
        ('Bottom to nearest part (sockets, contacts, pins)', 'bottom to nearest part', None),
        ('Top to XIAO', 'top to XIAO', None), ('Bottom to XIAO', 'bottom to XIAO', None),
        ('Wood insert to XIAO', 'wood insert to XIAO', None),
        ('Top to exposed pads', 'top to exposed pads', None), ('Bottom to exposed pads', 'bottom to exposed pads', None),
        ('Top/bottom seam gap', 'top/bottom gap at seam', None)]
for label, key, okey in rows:
    o = f"{d('L', okey):.2f} mm" if okey else ''
    lines.append(f"| {label} | {d('L', key):.2f} mm | {d('R', key):.2f} mm | {o} |")
lines += ['', 'Reset switch: its metal body keeps 0.5 mm; its plastic plunger runs out through a 3.4 x 2.0 mm slot '
          'in the back seam, 0.2 mm clear all round (plunger to top/bottom '
          f"{v['L']['reset plunger (plastic) to top / bottom']} mm left, {v['R']['reset plunger (plastic) to top / bottom']} mm right)."]
lines += ['', 'Top/bottom overlap: ' + str(v['L']['top/bottom overlap mm^3']) + ' / ' + str(v['R']['top/bottom overlap mm^3']) + ' mm³.',
          'The top never touches the floating mounting pads either: it stays 0.1 mm above them, as in the original.', '',
          '## Sizes', '']
for side in 'LR':
    for part in ('top', 'bottom', 'insert'):
        lines.append(f"- {side} {part}: {v[side][f'{part} size x,y,z']}, valid/solids/volume {v[side][f'{part} valid, solids, volume']}")
import re as _re
lines += ['', '## Parametric model', '',
          'The parts are built by `work/model.py` (CadQuery features). It never opens the original 3D-print',
          'parts: their reference shapes are curves in `work/model_ref.json` (lines, arcs and the outline\'s',
          'B-splines, taken once by `work/ref_extract.py`). The outline keeps the original\'s own curves, its',
          'inside corners rounded R1.05; the bottom is designed feature by feature (block, plateau, walls and',
          'their seam, the 21° leg ramp as one exact plane, leg recesses, battery pocket, feet, notches, foot',
          'chamfers, tapped screw holes); the top takes the original\'s air band by band, reached from below or',
          'from above as a Ø2 mill cuts it, as one column model (`clean.make_solid`), then the designed seams',
          'and notches. Both get every keep-out (PCB, parts, pads, XIAO) cut as the mill makes it; the top',
          'then makes room for the bottom as milled (0.2 mm), and a last check fills any speck the mill',
          'leaves. Every stage must be one valid solid that survives a STEP round trip.', '',
          '| Part | Faces | Volume (mm³) |', '|---|---|---|']
for side in 'LR':
    t = (W / f'model_all_{side}.out').read_text()
    for part, name in (('top', f'TOTEM_alu_top_{side}.step'), ('bottom', f'TOTEM_alu_bottom_{side}.step')):
        m = list(_re.finditer(rf'{side} as milled: volume ([\d.]+) mm\^3, faces (\d+), valid True', t))
        m = m[0 if part == 'bottom' else -1]
        lines.append(f'| {side} {part} | {m.group(2)} | {float(m.group(1)):.1f} |')
    sp = _re.findall(r'speck \((\w+)\) at \[([^\]]+)\], ([\d.]+) mm\^2, filled to ([-\d.]+)', t)
    if sp:
        lines.append(f'- {side}: specks filled as the mill leaves them: ' +
                     '; '.join(f'({c.strip()}) {a} mm² from {k}' for k, c, a, h in sp))
lines += ['', 'The parts against the previous ones (the clean 2.5D rebuild of the 3D-print parts), column by column',
          'on a 0.05 mm grid (metal only in the previous part = removed, only in the new one = added; spots over',
          '0.05 mm³): the leg ramp is now a plane instead of steps, the walls and seams are designed:', '', '```'] + \
         open(W / 'clean_diff.txt').read().strip().splitlines() + ['```']
lines += ['', '## Solid checks', '', '```'] + open(W / 'argan_all.log').read().strip().splitlines() + ['```', '',
          '`InvalidCurveOnSurface` is a tolerance note normal after a STEP round trip.', '',
          '## Holes through the bottom', '',
          'Every vertical line through each bottom was ray-cast (0.25 mm grid). Nothing goes through the',
          'bottom any more (the screw holes are blind tapped holes from above), and no socket pocket breaks',
          'through into the leg recesses',
          '(see `underside_holes.png`):', '', '```'] + open(W / 'through.txt').read().strip().splitlines() + ['```', '',
          '## Thin walls compared with the original', '']
for side in 'LR':
    for part, orig in (('top', 'otop'), ('bottom', 'obottom')):
        r = thinner(side, part, orig)
        lines.append(f'- {side} {part}: ' + ('no new or thinner spots (clusters of 5+ samples, 0.25 mm grid)' if not r else
                     '; '.join(f'({x:.1f},{y:.1f}) {t:.2f} mm' + (f' (was {o:.2f})' if o else ' (new)') for x, y, t, o in r)))
lines += ['', '## Walls thinner than 0.8 mm', '',
          'Every band between the parts\' flat faces, cut in plan: metal narrower than 0.8 mm (what an',
          'opening by a 0.4 mm disc removes, less the bits it rounds off plain corners; width = twice the',
          'largest distance to the outline). Thin layers in z (floors, roofs) are listed below from',
          '`thin.py` (0.25 mm grid, all spots under 0.8 mm, screw-hole rings included):', '', '```'] + \
         open(W / 'walls.txt').read().strip().splitlines() + ['```', '', '```']
for side in 'LR':
    for part in ('top', 'bottom'):
        lines += open(W / f'thin_{part}_{side}.txt').read().strip().splitlines()
lines += ['```']
fit = json.load(open(W / 'fit_check.json'))
mach = open(W / 'machinable.txt').read().strip().splitlines()
lines += ['', '## 3-axis machining with a Ø2 mm flat end mill', '',
          'Every part was projected on a 0.05 mm grid from above and from below (two setups), using exact',
          'triangles for planar faces and closed tessellation for curved faces, with balanced crossings.',
          'On each side the',
          'surface a Ø2 mm flat end mill leaves is the grey-level closing of the part\'s height map by a 1 mm',
          'disc; any spot where the part lies deeper than that (material the mill can\'t remove: a slot',
          'narrower than 2 mm, an inside corner sharper than R1, a pocket hidden under an overhang) is',
          'counted if it is more than 0.03 mm deep. The screw holes are drilled (Ø2.4 in the top, Ø1.6 tap drill in the bottom) and not counted. Tilted and curved faces outside the countersinks (cut',
          'with the same flat end mill on 3D toolpaths) are reported as their area; the test above already',
          'covers them. Pictures: `work/mach_*.png`.', '', '```'] + mach + ['```', '',
          'Measured fit after machining (smallest vertical gap between the top\'s underside',
          'and the bottom\'s top face, each as the Ø2 mm end mill leaves it):', '', '```'] + \
         open(W / 'seam_machined.txt').read().strip().splitlines() + ['```', '',
          'Parts that must still fit where no keep-out applies (overlap volume, new / original):', '']
for side in 'LR':
    for k, val in fit[side].items():
        lines.append(f'- {side} {k}: {val}')
lines += ['', '## Pictures', '', '- `heightmap_L.png`, `heightmap_R.png`: gap from the PCB faces, before and after',
          '- `render3d_L.png`, `render3d_R.png`: the new parts', '- `sections_L.png`: cross-sections through the assembly',
          '- `reset_back.png`: back face around the reset button, original vs new (unchanged)',
          '- `underside_holes.png`: the bottoms seen from below, site original vs now (holes through the part)']
(OUT / 'CHECKS.md').write_text('\n'.join(lines) + '\n')
for src, dst in [('heightmap_L.png', 'heightmap_L.png'), ('heightmap_R.png', 'heightmap_R.png'),
                 ('render3d_L.png', 'render3d_L.png'), ('render3d_R.png', 'render3d_R.png'), ('v_new_L.png', 'sections_L.png')]:
    shutil.copy2(W / src, OUT / dst)
print((OUT / 'CHECKS.md').read_text())
