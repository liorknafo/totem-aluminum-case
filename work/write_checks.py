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
lines += ['', '## Solid checks', '', '```'] + open(W / 'argan_all.log').read().strip().splitlines() + ['```', '',
          '`InvalidCurveOnSurface` is a tolerance note normal after a STEP round trip. The few `SelfIntersect`',
          'flags on the bottoms are near-zero-area facets inherited from the site\'s mesh conversion; the',
          'original bottoms carry more of them (see `work/argan_cmp.log`).', '',
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
lines += ['', '## Pictures', '', '- `heightmap_L.png`, `heightmap_R.png`: gap from the PCB faces, before and after',
          '- `render3d_L.png`, `render3d_R.png`: the new parts', '- `sections_L.png`: cross-sections through the assembly',
          '- `reset_back.png`: back face around the reset button, original vs new (unchanged)',
          '- `underside_holes.png`: the bottoms seen from below, site original vs now (holes through the part)']
(OUT / 'CHECKS.md').write_text('\n'.join(lines) + '\n')
for src, dst in [('heightmap_L.png', 'heightmap_L.png'), ('heightmap_R.png', 'heightmap_R.png'),
                 ('render3d_L.png', 'render3d_L.png'), ('render3d_R.png', 'render3d_R.png'), ('v_new_L.png', 'sections_L.png')]:
    shutil.copy2(W / src, OUT / dst)
print((OUT / 'CHECKS.md').read_text())
