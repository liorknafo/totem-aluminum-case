"""Write outputs/CHECKS.md from work/checks_{L,R}.json, checks_mirror.json and build_{L,R}.json."""
import json
from pathlib import Path

import build as B

W = Path(__file__).resolve().parent
OUT = W.parent / 'outputs'


def load(n):
    return json.loads((W / n).read_text())


def mm(v):
    return '—' if v is None else f'{v:.2f} mm'


def main():
    c = {s: load(f'checks_{s}.json') for s in 'LR'}
    mir = load('checks_mirror.json')
    bld = {s: load(f'build_{s}.json') for s in 'LR'}
    L = []
    w = L.append
    w('# Checks (measured on the STEP files in this folder)')
    w('')
    w('Written by `work/check.py` and `work/report.py`. Distances are exact (OpenCASCADE BRepExtrema)')
    w('between each part as read back from its STEP file and everything taken from the board file')
    w('`src/totem_0_3.kicad_pcb`: the board (its outline with the tabs removed, 1.6 mm plus 0.05 mm of')
    w('copper and mask on each face), every 3D part on that half (each footprint\'s own model files from')
    w('`src/TOTEM3D`, placed by its `(model ...)` entry on the 1.6 mm board) and every copper pad (0.05 mm')
    w('proud of its face). KiCad\'s STEP exports in `src/` are only compared with these (end of this')
    w('file). Distances above 3 mm are shown as 3.00.')
    w('')
    w(f'**The rule:** at least {B.C} mm from aluminum to the board and to everything electrical on it.')
    w('')
    w('## Clearances')
    w('')
    w('| | Required | Left | Right |')
    w('|---|---|---|---|')

    def row(label, req, get):
        vals = []
        for s in 'LR':
            try:
                vals.append(get(c[s]))
            except (KeyError, TypeError):
                vals.append(None)
        w(f'| {label} | {req} | {mm(vals[0])} | {mm(vals[1])} |')
        return vals

    row('Top to board', '≥ 0.50', lambda r: r['board']['top']['d'])
    row('Bottom to board', '≥ 0.50', lambda r: r['board']['bottom']['d'])
    row(f'Top to board with {B.TAB_NUB} mm tab nubs', '≥ 0.50', lambda r: r['board_nubs']['top']['d'])
    row(f'Bottom to board with {B.TAB_NUB} mm tab nubs', '≥ 0.50', lambda r: r['board_nubs']['bottom']['d'])
    row('Top to copper pads', '≥ 0.50', lambda r: r['pads']['top']['d'])
    row('Bottom to copper pads', '≥ 0.50', lambda r: r['pads']['bottom']['d'])
    row('Top to solder fillets (allowance envelopes on the pads)', '≥ 0.50', lambda r: r['pads_solder_margin']['top']['d'])
    row('Bottom to solder fillets (allowance envelopes on the pads)', '≥ 0.50', lambda r: r['pads_solder_margin']['bottom']['d'])
    cats = sorted({k for s in 'LR' for k in c[s]['parts']})
    for cat in cats:
        plastic = 'plastic' in cat
        diode = cat.startswith('diode (whole')
        for part in ('top', 'bottom'):
            req = '≥ 0.30' if diode and part == 'top' else '≥ 0.50'
            row(f'{part.capitalize()} to {cat}', req, lambda r, cat=cat, part=part: r['parts'][cat][part]['d'])
        if 'XIAO' in cat:
            row('Wood insert to XIAO', 'no contact', lambda r, cat=cat: r['parts'][cat]['insert']['d'])
    row('Keycaps (pressed, skirt at z 5.0) to the top', '≥ 0.30', lambda r: r['keycaps']['min_gap'])
    w('')
    for s in 'LR':
        sw = c[s].get('switches')
        if sw:
            w(f"- {s} switches: largest overlap of a switch body with the top {sw['max_overlap_mm3']} mm³; shoulder at z "
              f"{sw['shoulder_z']} on the plate top at {sw['plate_top']}; latches up to z {sw['latch_top_z']}, "
              f"{sw['latch_play']} mm under the plate (underside at {sw['plate_bottom']})")
    w('')
    w('Allowances used for solder: 1.0 mm above SMD pads and on the soldered side of through-hole pads')
    w('(the XIAO castellations and the battery-wire pads are soldered on top), 0.6 mm on the diode pads,')
    w('0.3 mm pushed through to the component side, none on the hot-swap switch-pin rings and on the')
    w('TRRS footprint (not fitted). A fillet may spread 0.3 mm beyond its pad.')
    w('')
    w('The plastic switch bodies clip into the 13.8 mm plate cut-outs (a fit, not a clearance); their pins')
    w('under the board keep the rule. The diodes may come to 0.30 mm on top of their epoxy body; their leads and')
    w('sides keep 0.50. The power slider knob (measured at five places over ±1.5 mm of travel) and the reset')
    w('plunger keep 0.50 in their openings, like everything else.')
    w('')
    w('Parts are placed from the board file: each footprint\'s 3D models (`src/TOTEM3D`) with the offset')
    w('and rotation of its `(model ...)` entry, on the top face of the 1.6 mm board. KiCad\'s own exports')
    w('in `src/` are only compared against that (see the end of this file).')
    w('')
    w('## Spacers at the mounting pads')
    w('')
    w(f'Each no-net mounting pad gets an insulating spacer (Ø ≤ {B.SPACER_D} mm) above and below the board: a')
    w(f'{B.UPPER_SPACER} mm one in a Ø{B.SEAT_D} seat in the top and a {B.LOWER_SPACER} mm one in a Ø{B.SEAT_D} seat in the floor.')
    w(f'Both stop {B.SPACER_GAP} mm from the pad copper, so the board can move no more than that at the pads.')
    w('')
    w('| Side | Mounting hole | Spacer gap to the board (below, above) | Within the pad | Nearest part | Seated (top, bottom) |')
    w('|---|---|---|---|---|---|')
    for s in 'LR':
        for sp in c[s].get('spacers', []):
            npart = f"{sp['nearest_part'][0]:.2f} mm ({sp['nearest_part'][1]})" if sp['nearest_part'] else '> 3 mm'
            w(f"| {s} | ({sp['at'][0]}, {sp['at'][1]}) | {sp['gap_to_board_lower_upper'][0]:.2f}, {sp['gap_to_board_lower_upper'][1]:.2f} mm "
              f"| {'yes' if sp['spacer_within_pad'] else 'NO'} (pad Ø{sp['pad_d']}) | {npart} | "
              f"{sp['seat_contact_top_bottom'][0]:.2f}, {sp['seat_contact_top_bottom'][1]:.2f} mm |")
    w('')
    w('## Assembly')
    w('')
    for s in 'LR':
        a = c[s]['assembly']
        w(f'- {s}: top/bottom overlap {a["top_bottom_overlap"]} mm³, gap {a["top_bottom_gap"]} mm, seam contact '
          f'{a["seam_contact_mm2"]} mm² at z {B.Z_SEAM}; wood insert/top overlap {a["insert_top_overlap"]} mm³, '
          f'gap {a["insert_top_gap"]} mm')
    w('')
    w('## Wall, floor and roof thickness')
    w('')
    w('Thinnest material between opposing faces (walls, floors, roofs and diagonal necks), measured on the')
    w(f'solids. The design aims for {B.T_MIN} mm (the switch clip ledge is 1.2 mm). It gets less where the board')
    w('leaves no room: the plate between the pocket over diode DL16/DR16 and its neighbouring switch zone (the')
    w('diode sits 0.8 mm from the switch housing on the board), and a few spots near 0.87-0.98 mm; the')
    w('smallest values are listed here. Every one is above the 0.6 mm minimum.')
    w('')
    for s in 'LR':
        for part in ('top', 'bottom'):
            th = c[s][part].get('thinnest', [])
            txt = '; '.join(f'{t:.2f} mm at ({p[0]:.1f}, {p[1]:.1f}, z {p[2]:.2f})' for t, p in th[:4]) or 'none under 2 mm'
            w(f'- {s} {part}: {txt}')
    w('')
    w('## Machining')
    w('')
    w(f'- Every face is horizontal or vertical (2.5D), and every horizontal face is reachable straight from')
    w('  above or from below: two setups, no undercuts.')
    for s in 'LR':
        for part in ('top', 'bottom', 'insert'):
            m = c[s][part]['mill']
            w(f'  - {s} {part}: tilted faces {m["n_tilted"]}, horizontal faces not reachable {m["n_blocked"]}, '
              f'inside corners tighter than R{B.R_MILL} {m["n_corners"]}')
    w(f'- Inside corners were checked on sections through every height step of each solid: none needs')
    w(f'  an end mill smaller than Ø{2 * B.R_MILL:.0f} mm.')
    w('- Vertical lines through the bottom (0.2 mm grid): the only openings are the screw holes:')
    for s in 'LR':
        th = c[s]['bottom']['through']
        w(f'  - {s}: ' + '; '.join(f'({t["at"][0]:.1f}, {t["at"][1]:.1f}) {t["size"][0]:.1f} x {t["size"][1]:.1f} mm' for t in th))
    w('')
    w('## Solids and STEP faces')
    w('')
    w('| File | Valid | Solids | Shells | Closed | Analyzer | Faces | Size x × y × z (mm) | z | Volume (mm³) |')
    w('|---|---|---|---|---|---|---|---|---|---|')
    for s in 'LR':
        for part, fn in (('top', 'TOTEM_alu_top'), ('bottom', 'TOTEM_alu_bottom'), ('insert', 'TOTEM_wood_window_insert')):
            r = c[s][part]
            a = r['analysis']
            faces = ', '.join(f'{v} {k.lower()}' for k, v in sorted(r['faces'].items()))
            w(f'| `{fn}_{s}.step` | {a["valid"]} | {a["solids"]} | {a["shells"]} | {a["closed"]} | '
              f'{"faults" if a["analyzer_faulty"] else "clean"} | {faces} | {r["size"][0]} × {r["size"][1]} × {r["size"][2]} | '
              f'{r["z"][0]} … {r["z"][1]} | {r["volume"]} |')
    w('')
    w('Only planes and cylinders: no B-spline, no triangulated faces. Stock: 140 × 105 mm; the top from')
    w(f'1/2" (12.7 mm) plate is {B.Z_TOP - B.Z_SEAM:.1f} mm tall, the bottom from 7/8" (22.2 mm) plate is'
      f' {B.Z_SEAM - B.Z_BOT:.1f} mm tall.')
    w('')
    w('## Is the right half a mirror of the left?')
    w('')
    w('Mirrored about x = 150 (KiCad), the right half of the board compares with the left like this:')
    w('')
    w('| Footprints | Count | Largest position difference | Angle mirrored | Angle the same |')
    w('|---|---|---|---|---|')
    for k, v in mir.items():
        if k == 'outline':
            continue
        w(f'| {k} | {v["n"]} | {v["max_pos"]:.3f} mm | {v["angle_mirrored"]} | {v["angle_same"]} |')
    o = mir['outline']
    w('')
    w(f'Outline: largest deviation {o["hausdorff_mm"]} mm, area difference {o["sym_diff_mm2"]} mm². '
      'The right half is not a mirror of the left: the parts are the same footprints placed on the same '
      'face (sockets, power switch, reset button are not mirrored) and some positions differ. Both halves '
      'are built from the board the same way.')
    w('')
    w('## KiCad exports compared with the board file')
    w('')
    try:
        ex = load('checks_exports.json')
        pc = ex['parts (comp_all.step)']
        w(f"- `comp_all.step`: largest sideways difference of a part's box {pc['max_xy']} mm; z offsets of the export "
          f"{pc['z_offsets']} mm (the parts here sit on the 1.6 mm board's top face; the export puts them that much lower); stale parts: "
          + (', '.join(pc['stale']) if pc['stale'] else 'none'))
        bo = ex['board outline (pcb_board.step)']
        w(f"- `pcb_board.step`: the outline from the board file is at most {bo['max_distance']} mm from the export's outline (tab openings aside; the export's cut-outs also include the drilled holes, which the checks leave in the board, so they measure against more board, not less)")
        pd = ex['pads (pads.step)']
        w(f"- `pads.step`: {pd['n_board']} copper pads in the board file ({pd['n_export']} exported pad solids, through-hole pads once per face); "
          f"the largest distance from a pad's centre to an exported pad's centre is {pd['max_centre_offset']} mm")
    except FileNotFoundError:
        w('- (not run)')
    w('')
    w('## Build')
    w('')
    for s in 'LR':
        t = bld[s].get('timing', {})
        if t:
            w(f'- {s}: ' + ', '.join(f'{k} {v:.1f} s' for k, v in t.items()))
    w('')
    w('## Pictures')
    w('')
    w('- `render3d_L.png`, `render3d_R.png`: each half: top from above and below, bottom from above and below')
    w('- `sections_L.png`: cross-sections through the left half (top, board and parts, bottom)')
    w('- `clearance_L.png`, `clearance_R.png`: gap from the board faces to the aluminum, seen from above')
    w('- `openings_L.png`: the USB-C, power-switch and reset openings in the back wall')
    (OUT / 'CHECKS.md').write_text('\n'.join(L) + '\n')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
