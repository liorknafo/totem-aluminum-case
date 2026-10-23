# TOTEM BLE case in aluminum

All four aluminum parts are clean 2.5D CAD — every face exactly vertical or flat, outlines in
lines and true arcs, only the 90° screw countersinks conical — and the checks in
`outputs/CHECKS.md` find no spot a Ø2 mm flat end mill can't reach from above or below, no
undercut, and no aluminum within 0.5 mm of the board, its pads or its metal parts.

The [TOTEM](https://github.com/GEIGEIGEIST/TOTEM) split keyboard's BLE case (tenting bottom + top),
reworked so it can be machined from aluminum without shorting the PCB: every aluminum surface keeps
at least 0.5 mm from the board, its pads and the metal parts on it, and a wood window over each
XIAO BLE lets Bluetooth out. The parts fit 105 × 140 mm stock: 1/2" plate for the tops, 7/8" plate
for the bottoms. The machining target is a 3-axis mill, two setups, and flat end mills of Ø2 mm or
larger: inside corners at least R1.05, pockets and slots at least 2.1 mm wide, and no overhangs
(screw holes are drilled and countersunk in the top, drilled and tapped M2 in the bottom).

![Both halves assembled, with keycaps](docs/images/case_assembled.png)

| | |
|---|---|
| ![Without keycaps](docs/images/case_no_keycaps.png) | ![Exploded: top, PCB with switches, bottom](docs/images/case_exploded.png) |
| Without keycaps: the aluminum top and the wood windows over the XIAO | Exploded: top, PCB with switches and parts, bottom |
| ![Left half with the top see-through](docs/images/case_see_through.png) | ![Underside](docs/images/case_underside.png) |
| Left half, top made see-through: the PCB, switches, XIAO and wood window inside | From below: the tenting-leg recesses, no holes at all (the screws thread in from above) |
| ![Side view, slightly exploded](docs/images/case_side.png) | |
| Side view, slightly exploded: top, PCB, and the bottom with the battery in its pocket | |

The renders come from the current STEP files (`work/stills_template.html`, the same scene as the
interactive `outputs/TOTEM_3d_view.html`).

## Files

- `outputs/`: the result
  - `TOTEM_alu_top_L/R.step`, `TOTEM_alu_bottom_L/R.step`, `TOTEM_wood_window_insert_L/R.step`
  - `README.md`: what changed and machining notes
  - `CHECKS.md`: measured clearances, solid checks and pictures
  - `TOTEM_3d_view.html`: interactive 3D view of the whole build (open in a browser; loads three.js
    from unpkg.com)
- `work/`: the scripts that make and check the outputs
  - `build.py L` / `build.py R` makes the parts (`--reuse-top` rebuilds only the bottom)
  - `mill.py`: makes the parts cuttable with a Ø2 mm end mill (fill what it can't reach, cut the
    keep-outs as it can make them); `machinable.py PART.step 2` checks a part
  - `clean.py --all` rebuilds the build's four aluminum parts as clean CAD (flat and vertical
    faces only, lines and true arcs, exact drilled holes) and writes them to `outputs/`;
    `diff_mesh.py OLD NEW` shows where two versions of a part differ; `walls.py PART.step` lists
    walls thinner than 0.8 mm (in plan; `thin.py` measures floors and roofs)
  - `check_all.sh` re-runs the checks and rewrites `CHECKS.md`
  - `orig/`: the input case files (copies; never modified)
- `docs/images/`: the renders above
- `src/`: the TOTEM PCB (`totem_0_3.kicad_pcb`), its STEP exports (board, parts, pads) and the part
  models, used to measure clearances

## Rebuilding

Python 3.12 with cadquery, numpy, trimesh, shapely, contourpy, rtree, networkx, manifold3d,
matplotlib and scipy. From `work/`:

```sh
python -E -s build.py L
python -E -s build.py R
python -E -s clean.py --all
PYTHON=python ./check_all.sh
```

## License

Original design: TOTEM, Copyright (c) 2022 GEIST, CERN-OHL-P v2 (`LICENSE.md`). This modified
version is shared under the same licence.
