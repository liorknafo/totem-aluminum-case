"""Regression test: editing one footprint on the board changes only that footprint's pocket.

    ~/.venvs/totem-cad/bin/python -E -s test_variants.py      # several minutes (four rebuilds)

For each variant, a scratch copy of src/ and work/ gets one edit in the board file (a footprint's
position or its 3D model entry) and is rebuilt. The other half must come out identical to
outputs/ (zero symmetric difference), and the edited parts must keep their clearances.
Run it after build.py, with outputs/ up to date.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable

VARIANTS = [
    # (name, other half, [(ref, old text, new text)])
    ('DR10 moved +2 mm in x (first diode in the file)', 'L', [('DR10', '(at 162.872435 68.894348 -90)', '(at 164.872435 68.894348 -90)')]),
    ('DR10 model offset +2 mm', 'L', [('DR10', '(offset (xyz 0 0 -0.1))', '(offset (xyz 2 0 -0.1))')]),
    ('DR5 model offset +1.5 mm (not the first diode)', 'L', [('DR5', '(offset (xyz 0 0 -0.1))', '(offset (xyz 1.5 0 -0.1))')]),
    ('DL2 model offset -1.5 mm in y', 'R', [('DL2', '(offset (xyz 0 0 -0.1))', '(offset (xyz 0 -1.5 -0.1))')]),
]

PROBE = r'''
import sys, json, cadquery as cq
sys.path.insert(0, '.')
import check
from pcb import Board
D, repo, other, refs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(',')
out = {'other_half': {}, 'edited': [], 'closest_diode': {}}
for n in ('TOTEM_alu_top', 'TOTEM_alu_bottom', 'TOTEM_wood_window_insert'):
    a = cq.importers.importStep(f'{repo}/outputs/{n}_{other}.step').val()
    b = cq.importers.importStep(f'{D}/outputs/{n}_{other}.step').val()
    out['other_half'][n] = round(a.cut(b).Volume() + b.cut(a).Volume(), 6)
board = Board()
for side in 'LR':
    T = check.Part(cq.importers.importStep(f'{D}/outputs/TOTEM_alu_top_{side}.step').val())
    rows = [(T.dist(s)[0], cat, ref) for cat, ref, s in check.classify(board, side) if cat.startswith('diode')]
    out['closest_diode'][side] = min(r for r in rows if 'whole' in r[1])[0], min(r for r in rows if 'leads' in r[1])[0]
    out['edited'] += [(ref, cat, round(d, 3)) for d, cat, ref in rows if ref in refs]
print(json.dumps(out))
'''


def run(name, other, edits):
    D = Path(tempfile.mkdtemp(prefix='totem-variant-'))
    try:
        for d in ('src', 'work'):
            shutil.copytree(REPO / d, D / d, ignore=shutil.ignore_patterns('cache', '__pycache__', 'orig', '*.json'))
        (D / 'outputs').mkdir()
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
        r = subprocess.run([PY, '-E', '-s', 'build.py'], cwd=D / 'work', capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-2000:]
        (D / 'work' / 'probe_variant.py').write_text(PROBE)
        r = subprocess.run([PY, '-E', '-s', 'probe_variant.py', str(D), str(REPO), other, ','.join(e[0] for e in edits)],
                           cwd=D / 'work', capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-2000:]
        import json
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(D, ignore_errors=True)


if __name__ == '__main__':
    ok = True
    for name, other, edits in VARIANTS:
        res = run(name, other, edits)
        same = all(v < 1e-6 for v in res['other_half'].values())
        clear = all(res['closest_diode'][s][0] >= 0.3 - 1e-6 and res['closest_diode'][s][1] >= 0.5 - 1e-6 for s in 'LR')
        ok &= same and clear
        print(f"{'PASS' if same and clear else 'FAIL'}  {name}: other half ({other}) "
              f"{'identical' if same else res['other_half']}; closest diode epoxy/leads "
              f"L {res['closest_diode']['L'][0]:.3f}/{res['closest_diode']['L'][1]:.3f} "
              f"R {res['closest_diode']['R'][0]:.3f}/{res['closest_diode']['R'][1]:.3f}; edited {res['edited']}", flush=True)
    sys.exit(0 if ok else 1)
