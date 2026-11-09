"""Regression test: editing one footprint on the board changes only that footprint's pocket.

    ~/.venvs/totem-cad/bin/python -E -s test_variants.py      # several minutes (two builds per variant)

For each variant, a scratch copy of src/ and work/ gets one edit in the board file (a footprint's
position, its 3D model offset, or its model file: a different file with the same name in another
folder) and is built twice, first with an empty part cache, then with the warm cache; both builds
must give the same parts. Then:
  - the half that was not edited must come out identical to outputs/ (zero symmetric difference);
  - every diode on both halves keeps its clearance (checker, epoxy 0.3 / leads 0.5);
  - each edited footprint is also measured against its model file loaded directly and placed by
    separate code from the edited board text (not through parts.py and its cache).
Run it after build.py, with outputs/ up to date.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable
ALT = '${KIPRJMOD}/TOTEM3D/alt/D_SOD-123.step'     # same file name, other folder, model moved 2 mm

VARIANTS = [
    # (name, half that must not change, [(ref, old text, new text)])
    ('DR10 moved +2 mm in x (first diode in the file)', 'L', [('DR10', '(at 162.872435 68.894348 -90)', '(at 164.872435 68.894348 -90)')]),
    ('DR10 model offset +2 mm', 'L', [('DR10', '(offset (xyz 0 0 -0.1))', '(offset (xyz 2 0 -0.1))')]),
    ('DR5 model offset +1.5 mm (not the first diode)', 'L', [('DR5', '(offset (xyz 0 0 -0.1))', '(offset (xyz 1.5 0 -0.1))')]),
    ('DL2 model offset -1.5 mm in y', 'R', [('DL2', '(offset (xyz 0 0 -0.1))', '(offset (xyz 0 -1.5 -0.1))')]),
    ('DR5 model file: same name, other folder (not the first diode)', 'L', [('DR5', '${KIPRJMOD}/TOTEM3D/D_SOD-123.step', ALT)]),
    ('DR9 model file: same name, other folder (the last diode)', 'L', [('DR9', '${KIPRJMOD}/TOTEM3D/D_SOD-123.step', ALT)]),
]

PROBE = r'''
import sys, re, json, math, cadquery as cq
sys.path.insert(0, '.')
import check
from pcb import Board
D, repo, other, refs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(',')
out = {'other_half': {}, 'edited': [], 'closest_diode': {}, 'independent': []}
for n in ('TOTEM_alu_top', 'TOTEM_alu_bottom', 'TOTEM_wood_window_insert'):
    a = cq.importers.importStep(f'{repo}/outputs/{n}_{other}.step').val()
    b = cq.importers.importStep(f'{D}/outputs/{n}_{other}.step').val()
    out['other_half'][n] = round(a.cut(b).Volume() + b.cut(a).Volume(), 6)
board = Board()
tops = {s: cq.importers.importStep(f'{D}/outputs/TOTEM_alu_top_{s}.step').val() for s in 'LR'}
for side in 'LR':
    T = check.Part(tops[side])
    rows = [(T.dist(s)[0], cat, ref) for cat, ref, s in check.classify(board, side) if cat.startswith('diode')]
    out['closest_diode'][side] = min(r for r in rows if 'whole' in r[1])[0], min(r for r in rows if 'leads' in r[1])[0]
    out['edited'] += [(ref, cat, round(d, 3)) for d, cat, ref in rows if ref in refs]
# independent: read the edited footprint straight from the board text, load its model file, place it
text = open(f'{D}/src/totem_0_3.kicad_pcb').read()
for ref in refs:
    i = text.index(f'(fp_text reference "{ref}"'); j = text.rfind('(footprint ', 0, i); k = text.find('(footprint ', i)
    seg = text[j:k if k > 0 else len(text)]
    x, y, *ang = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', seg).groups()
    ang = float(ang[0]) if ang and ang[0] else 0.0
    for m in re.finditer(r'\(model "([^"]+)"\s*\(offset \(xyz ([-\d.]+) ([-\d.]+) ([-\d.]+)\)\)\s*\(scale [^)]*\)\)\s*\(rotate \(xyz ([-\d.]+) ([-\d.]+) ([-\d.]+)\)\)', seg):
        path = m.group(1).replace('${KIPRJMOD}', f'{D}/src')
        off = [float(m.group(k)) for k in (2, 3, 4)]; rot = [float(m.group(k)) for k in (5, 6, 7)]
        s = cq.importers.importStep(path).val()
        for axis, a in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), rot):          # KiCad: negated, X then Y then Z
            s = s.rotate(cq.Vector(), cq.Vector(*axis), -a)
        s = s.translate(cq.Vector(off[0], off[1], off[2] + 1.6))
        s = s.rotate(cq.Vector(), cq.Vector(0, 0, 1), ang).translate(cq.Vector(float(x), -float(y), 0))
        side = 'L' if float(x) < 150 else 'R'
        top = tops[side]
        ov = top.intersect(s)
        d = check.BRepExtrema_DistShapeShape_value(top, s)
        bb = s.BoundingBox()
        low = s.intersect(check.box(-50, 450, -300, 50, -10, bb.zmax - 0.25))
        dl = check.BRepExtrema_DistShapeShape_value(top, low) if low.Solids() else 99
        out['independent'].append((ref, round(d, 3), round(dl, 3), round(ov.Volume(), 6) if ov.Solids() else 0.0))
print(json.dumps(out))
'''


def build(D):
    r = subprocess.run([PY, '-E', '-s', 'build.py'], cwd=D / 'work', capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]


def same_outputs(a, b):
    code = ('import sys, cadquery as cq\n'
            'a, b = sys.argv[1], sys.argv[2]\n'
            'import glob, os\n'
            'worst = 0.0\n'
            'for f in sorted(glob.glob(a + "/*.step")):\n'
            '    x = cq.importers.importStep(f).val(); y = cq.importers.importStep(os.path.join(b, os.path.basename(f))).val()\n'
            '    worst = max(worst, x.cut(y).Volume() + y.cut(x).Volume())\n'
            'print(worst)\n')
    r = subprocess.run([PY, '-E', '-s', '-c', code, str(a), str(b)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return float(r.stdout.strip().splitlines()[-1])


def run(name, other, edits):
    D = Path(tempfile.mkdtemp(prefix='totem-variant-'))
    try:
        for d in ('src', 'work'):
            shutil.copytree(REPO / d, D / d, ignore=shutil.ignore_patterns('cache', '__pycache__', 'orig', '*.json'))
        (D / 'outputs').mkdir()
        # the alternate model: the SOD-123 model moved 2 mm along its own x, same file name, other folder
        alt = D / 'src' / 'TOTEM3D' / 'alt'
        alt.mkdir()
        code = ('import sys, cadquery as cq\n'
                's = cq.importers.importStep(sys.argv[1]).val().translate(cq.Vector(2, 0, 0))\n'
                'cq.exporters.export(s, sys.argv[2])\n')
        subprocess.run([PY, '-E', '-s', '-c', code, str(D / 'src' / 'TOTEM3D' / 'D_SOD-123.step'), str(alt / 'D_SOD-123.step')], check=True)
        p = D / 'src' / 'totem_0_3.kicad_pcb'
        t = p.read_text()
        for ref, old, new in edits:
            i = t.index(f'(fp_text reference "{ref}"')
            j = t.rfind('(footprint ', 0, i)
            k = t.find('(footprint ', i)
            k = len(t) if k < 0 else k
            seg = t[j:k]
            assert old in seg, (ref, old)
            t = t[:j] + seg.replace(old, new, 1) + t[k:]
        p.write_text(t)
        build(D)                                    # empty part cache
        shutil.copytree(D / 'outputs', D / 'outputs_fresh')
        build(D)                                    # warm part cache
        warm_vs_fresh = same_outputs(D / 'outputs_fresh', D / 'outputs')
        (D / 'work' / 'probe_variant.py').write_text(PROBE)
        r = subprocess.run([PY, '-E', '-s', 'probe_variant.py', str(D), str(REPO), other, ','.join(e[0] for e in edits)],
                           cwd=D / 'work', capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-2000:]
        res = json.loads(r.stdout.strip().splitlines()[-1])
        res['warm_vs_fresh'] = warm_vs_fresh
        return res
    finally:
        shutil.rmtree(D, ignore_errors=True)


if __name__ == '__main__':
    ok = True
    for name, other, edits in VARIANTS:
        res = run(name, other, edits)
        same = all(v < 1e-6 for v in res['other_half'].values())
        clear = all(res['closest_diode'][s][0] >= 0.3 - 1e-6 and res['closest_diode'][s][1] >= 0.5 - 1e-6 for s in 'LR')
        indep = all(d >= 0.3 - 1e-6 and dl >= 0.5 - 1e-6 and ov == 0 for _, d, dl, ov in res['independent'])
        cache = res['warm_vs_fresh'] < 1e-6
        good = same and clear and indep and cache
        ok &= good
        print(f"{'PASS' if good else 'FAIL'}  {name}: other half ({other}) {'identical' if same else res['other_half']}; "
              f"closest diode epoxy/leads L {res['closest_diode']['L'][0]:.3f}/{res['closest_diode']['L'][1]:.3f} "
              f"R {res['closest_diode']['R'][0]:.3f}/{res['closest_diode']['R'][1]:.3f}; "
              f"edited, model loaded directly (ref, epoxy, leads, overlap mm3): {res['independent']}; "
              f"warm vs fresh cache {res['warm_vs_fresh']:.6f} mm3", flush=True)
    sys.exit(0 if ok else 1)
