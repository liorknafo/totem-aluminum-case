# Handoff (2026-10-23): continue on the ROG laptop

Branch `t3/cases-machinable-2mm-endmill`, last commit is a **WIP**: its checks are not complete.

## Where things stand

The four aluminum parts in `outputs/` were rebuilt (`work/clean.py --all`) with:

- **Tapped M2 holes in the bottoms** (Ø1.6 tap drill from the boss top to z −6.5, tap M2 × 0.4
  5.5 mm; 0.8 mm left over the leg recess under the 131.2 / 176.8 screws). No standoffs; the
  bottom's underside is solid at the screws.
- **Tops: 90° countersinks** (Ø4.30 at the face) over Ø2.4 pass-through holes. Screws: M2 × 16
  countersunk (ISO 7046 / DIN 965), 5.2 mm of thread engaged.
- **Plain back seam**: the castellated tongue and groove along the back wall (the original's
  arches as 2.5D steps, a toothed seam line on the back face) is flat over its straight runs
  (`back_seam_runs` / `flat_back_seam` in `clean.py`): the bottom's outer lip comes down to its
  ledge, the top stops 0.4 mm over it. The top's runs stop 1.2 mm short of the bottom's at each
  end (the mill's R1 corner), so the last 1.2 mm of each run shows a 1.1 mm seam.
- Earlier today: ledges over the diode pockets, 1 mm screw necks, the wall in front of the XIAO
  opened, keycap-well walls thickened, floors ≥ 0.8 mm, `walls.py` check.

Each part was valid and converged (0 checker spots) in the rebuild. `verify.py` had passed for the
**left** half (top to PCB 0.52, parts ≥ 0.50, seam gap 0.20, no overlap) when the work moved.

## Next steps

1. Run the full checks: `cd work && PYTHON=~/.venvs/totem-cad/bin/python ./check_all.sh`
   (about 40 min). The previous attempt on the Mac hung somewhere after `argan_all.py` and was
   killed by a 2 h time limit: run the steps one by one (as in `check_all.sh`) with timing to find
   which one hangs. `verify.py L R` alone works (prints progress line by line).
2. Look at the results: `machinable.txt` (must be 0 spots), `fit_check.log` (0 overlaps),
   `seam_machined.txt` (gap ≥ 0.2 as machined; the run before the last fixes had −0.30 / −0.10 at
   the seam-run ends — the 1.2 mm shrink of the top's runs is meant to fix it), `verify.log`
   (right half), `through.txt` (should show **no** through-openings in the bottoms), `walls.txt`.
3. Re-render the README images (`work/stills_template.html`, see git history of
   `docs/images/`) and commit with a real message.
4. Still under 0.8 mm (see `outputs/README.md`, machining notes): corners by the XIAO's back
   corner, walls between socket pockets, short bits in the tops.

## Environment

- Python: `~/.venvs/totem-cad` (uv, Python 3.12; cadquery 2.8.0, cadquery-ocp 7.9.3.1.1, numpy
  2.5.4, trimesh 5.1.1, shapely 2.2.0, contourpy 1.4.0, rtree 1.4.1, networkx 3.7, manifold3d
  3.5.4, matplotlib 3.11.2, scipy 1.18.1, scikit-image 0.26.0, embreex 4.4.0, mapbox_earcut
  2.1.0, pillow 13.0.0). Run scripts from `work/` as `~/.venvs/totem-cad/bin/python -E -s …`.
- Git-ignored build files copied from the Mac into `work/`: `final_*.brep` (the build's parts,
  input to `clean.py`), `keepout_*.step`, `pcb_*.step`, `clean_mesh_*.npz`, `clean_*.brep`,
  `view_data.*`. Rebuilding them from scratch is `build.py L` / `build.py R` (15–20 min each).
- Timings: `clean.py --all` ≈ 20 min, `check_all.sh` ≈ 40 min. The two halves can be rebuilt in
  parallel: `clean.py final_KIND_SIDE.brep KIND SIDE ../outputs/TOTEM_alu_KIND_SIDE.step`.
- Nothing is pushed to GitHub (`origin`); the Mac has the same commits.
