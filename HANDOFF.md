# Handoff (2026-10-24)

Branch `t3/cases-machinable-2mm-endmill` (pushed to `origin`).

## Where things stand

The six parts in `outputs/` are built by the parametric CadQuery model `work/model.py`, which never
opens the original 3D-print parts: `work/ref_extract.py` took their reference curves once into
`work/model_ref.json`. `outputs/README.md` ("Parametric model") describes it; `outputs/CHECKS.md`
has the results of `work/check_all.sh`.

- Machinable with a Ø2 mm flat end mill (3-axis, two setups, 3D toolpaths for the bottoms' leg ramps
  and foot chamfers): 0 spots, 0 undercuts on all six parts.
- Clearances (verify.py): top/bottom to PCB ≥ 0.51, parts ≥ 0.50, diode epoxy 0.365, XIAO 0.52,
  reset plunger 0.2; no overlaps; fit check 0 (switches, pressed keycaps, battery).
- Each part meshes closed in the CAM planner (axis-cam's STEP converter; `work/planner_mesh.py`
  does the same meshing and is a step of `check_all.sh`).
- Drilling the bottoms' tap holes in the CAM planner: the four Ø1.6 holes open into two separate
  plateau faces (3 holes + 1); select both faces (or click the fourth hole).

## Open points

- Walls under 0.8 mm are listed in `CHECKS.md`; the clean parts' keycap-well wall thickening was
  not carried into the parametric model.
- The left half's seam: the tops were last rebuilt with an R1.05 pocket at each free wall end so
  the 0.2 mm room round the bottom's wall ends can be milled (verify had 0.14 mm at the left wall's
  front end before it). Check `verify.log` "gap at seam" after any rebuild.

## Working on it

- Python: `~/.venvs/totem-cad` (run from `work/` as `~/.venvs/totem-cad/bin/python -E -s …`).
- Rebuild: `model.py all L` / `R` (≈30 min per half, both halves can run at once; `--dev` writes
  `work/model_*.step` instead of `outputs/`). Stage caches for quicker reruns of a top:
  `model.py top L --from-regions` (≈10 min), `--from-columns`, `model.py milled-top L`.
  `--meshcheck` meshes every stage as the CAM planner does.
- Checks: `cd work && PYTHON=~/.venvs/totem-cad/bin/python ./check_all.sh` (≈25 min, 8 jobs at a
  time; `JOBS=1` runs them one by one).
- README stills: `work/stills_template.html` with `view_data.json` embedded, rendered with headless
  Firefox (see git history of `docs/images/`).
