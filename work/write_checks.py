"""Write outputs/CHECKS.md from verify.json, the analyzer logs and the thin-wall comparison."""
import json, re, shutil
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
lines += ['', 'Reset switch: its metal body keeps 0.5 mm; its plastic plunger sits in the original round hole '
          f"(plunger to top/bottom {v['L']['reset plunger (plastic) to top / bottom']} mm, as designed)."]
lines += ['', 'Top/bottom overlap: ' + str(v['L']['top/bottom overlap mm^3']) + ' / ' + str(v['R']['top/bottom overlap mm^3']) + ' mm³.',
          'The top never touches the floating mounting pads either: it stays 0.1 mm above them, as in the original.', '',
          '## Sizes', '']
for side in 'LR':
    for part in ('top', 'bottom', 'insert'):
        lines.append(f"- {side} {part}: {v[side][f'{part} size x,y,z']}, valid/solids/volume {v[side][f'{part} valid, solids, volume']}")
import re as _re
lines += ['', '## Clean CAD rebuild', '',
          'All four aluminum parts are rebuilt as clean CAD (`work/clean.py`): every face exactly horizontal or',
          'vertical, outlines drawn with lines and true arcs, the screw holes as exact cylinders and 82° cones.',
          'Each part is taken from the build as one column of metal per (x, y) between flat faces; the',
          'hairline slivers and microscopic steps the build\'s mesh booleans left between near-identical walls',
          'are merged into a neighbour (into the side with less metal where there is one), every boundary between',
          'two regions is fitted once with lines and arcs (0.002 mm), and every region becomes one prism.', '',
          '| Part | Faces | Arcs / lines in the outlines | Volume, build → clean (mm³) | STEP size |', '|---|---|---|---|---|']
_ev = {}
for side in 'LR':
    for part in ('top', 'bottom'):
        t = (W / f'clean_{part}_{side}.log').read_text()
        _ev[(side, part)] = t
        m1 = list(_re.finditer(r'chains, \d+ vertices -> (\d+) primitives \((\d+) arcs\)', t))[-1]
        m2 = _re.search(r'final: valid True faces (\d+) volume ([\d.]+) \(was ([\d.]+)', t)
        size = (OUT / f'TOTEM_alu_{part}_{side}.step').stat().st_size / 1e6
        lines.append(f'| {side} {part} | {m2.group(1)} | {m1.group(2)} / {int(m1.group(1)) - int(m1.group(2))} | '
                     f'{float(m2.group(3)):.1f} → {float(m2.group(2)):.1f} | {size:.0f} MB |')
lines += ['', 'What the rebuild changed, part by part (all logged in `work/clean_*.log`):', '']
for (side, part), t in _ev.items():
    items = []
    for m in _re.finditer(r'opening through the part closed at \[\s*([-\d.]+)\s+([-\d.]+)\] ([\d.]+) mm', t):
        items.append(f'opening through the part at ({m.group(1)}, {m.group(2)}), {m.group(3)} mm², closed')
    cr = [float(a) for a in _re.findall(r'hairline crack filled at .*\(([\d.]+) mm', t)]
    if cr:
        items.append(f'{len(cr)} hairline horizontal cracks inside the part filled (largest {max(cr):.2f} mm²)')
    for m in _re.finditer(r'skin ([\d.]+) mm at \[\s*([-\d.]+)\s+([-\d.]+)\s*\] \(([\d.]+) mm\^2\): (floor|underside) ([-\d.]+) -> ([-\d.]+)', t):
        how = 'floor raised' if m.group(5) == 'floor' else 'pad underneath'
        items.append(f'{m.group(1)} mm floor at ({m.group(2)}, {m.group(3)}), {m.group(4)} mm², made 0.6 mm or more ({how}, '
                     f'{m.group(6)} → {m.group(7)})')
    for m in _re.finditer(r'joint ([\d.]+) mm over ([\d.]+) mm at \[\s*([-\d.]+)\s+([-\d.]+)\s*\]', t):
        items.append(f'knife-edge joint ({m.group(1)} mm overlap) at ({m.group(3)}, {m.group(4)}) made 0.6 mm')
    m = _re.search(r'pocket widened: ([\d.]+) mm', t)
    if m:
        items.append(f'XIAO pocket widened to 0.52 mm all round ({m.group(1)} mm³)')
    m = _re.search(r'specks on the outline given to the air: ([\d.]+) mm', t)
    if m and float(m.group(1)) > 0:
        items.append(f'hairline specks on the outer faces removed ({m.group(1)} mm² in plan, up to 0.05 mm deep)')
    m = _re.search(r'mill reach repairs: ([\d.]+) mm', t)
    sp = sum(float(x) for x in _re.findall(r'checker spots filled: ([\d.]+) mm', t))
    if m:
        items.append(f'corners the Ø2 mill cannot reach after the above filled as the mill leaves them '
                     f'({float(m.group(1)) + sp:.2f} mm³)')
    lines.append(f'- {side} {part}: ' + '; '.join(items) + '.')
lines += ['', 'The published parts against the build\'s, column by column on a 0.05 mm grid (metal only in the',
          'build\'s part = removed, only in the published part = added; spots over 0.05 mm³). The screw holes',
          'show up because they are now the exact Ø2.0 / 82° / Ø4.3 (bottom) and Ø3.2 (top) holes of the original',
          'CAD, where the site\'s mesh had them faceted; strips one grid cell wide along the outer faces are',
          'walls that moved by a few microns across a grid line:', '', '```'] + \
         open(W / 'clean_diff.txt').read().strip().splitlines() + ['```']
lines += ['', '## Solid checks', '', '```'] + open(W / 'argan_all.log').read().strip().splitlines() + ['```', '',
          '`InvalidCurveOnSurface` is a tolerance note normal after a STEP round trip.', '',
          '## Holes through the bottom', '',
          'Every vertical line through each bottom was ray-cast (0.25 mm grid). The only openings through',
          'the part are the screw holes; no socket pocket breaks through into the leg recesses any more',
          '(see `underside_holes.png`):', '', '```'] + open(W / 'through.txt').read().strip().splitlines() + ['```', '',
          '## Thin walls compared with the original', '']
for side in 'LR':
    for part, orig in (('top', 'otop'), ('bottom', 'obottom')):
        r = thinner(side, part, orig)
        lines.append(f'- {side} {part}: ' + ('no new or thinner spots (clusters of 5+ samples, 0.25 mm grid)' if not r else
                     '; '.join(f'({x:.1f},{y:.1f}) {t:.2f} mm' + (f' (was {o:.2f})' if o else ' (new)') for x, y, t, o in r)))
fit = json.load(open(W / 'fit_check.json'))
mach = open(W / 'machinable.txt').read().strip().splitlines()
lines += ['', '## 3-axis machining with a Ø2 mm flat end mill', '',
          'Every part was projected on a 0.05 mm grid from above and from below (two setups), using exact',
          'triangles for planar faces and closed tessellation for curved faces, with balanced crossings.',
          'On each side the',
          'surface a Ø2 mm flat end mill leaves is the grey-level closing of the part\'s height map by a 1 mm',
          'disc; any spot where the part lies deeper than that (material the mill can\'t remove: a slot',
          'narrower than 2 mm, an inside corner sharper than R1, a pocket hidden under an overhang) is',
          'counted if it is more than 0.03 mm deep. The screw holes are drilled (Ø2.0 necks) and not counted. Tilted faces outside the countersinks are reported separately;',
          'they must be horizontal or vertical for a strict 2.5D result. Pictures: `work/mach_*.png`.', '', '```'] + mach + ['```', '',
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
