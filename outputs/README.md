# TOTEM BLE case — aluminum version (no contact with the PCB)

Machining: all four aluminum parts can be cut on a 3-axis mill in two setups with a Ø2 mm flat end
mill (or bigger), on 3D toolpaths where a face slopes — no ball-nose tool. They are a parametric
CadQuery model (`work/model.py`, see "Parametric model" below): outlines are lines, true arcs and
the original's B-splines; the bottoms' leg ramps are real 21° planes (no more steps), with 45° foot
chamfers inside the walls; the tops' screw countersinks are **90°** cones (a 90° countersink bit,
for metric M2 countersunk screws). The M2 threads are tapped in the bottoms. The checks are in
`CHECKS.md`.

Made from copies of the four files in `~/Downloads/TOTEM_cases_STEP` (those originals are untouched;
their SHA-256 still match `validation.json`). Units mm, same coordinates as the originals.

| File | Part | Stock |
|---|---|---|
| `TOTEM_alu_top_L.step`, `TOTEM_alu_top_R.step` | aluminum top | 105 × 140 × 1/2" plate |
| `TOTEM_alu_bottom_L.step`, `TOTEM_alu_bottom_R.step` | aluminum tenting bottom | 105 × 140 × 7/8" plate |
| `TOTEM_wood_window_insert_L.step`, `..._R.step` | wood window over the XIAO | 3 mm wood |

## The rule

No aluminum surface comes closer than **0.5 mm** to the board or to anything electrical on it:
the board edge and both faces (including 0.05 mm of copper/mask), every pad with room for its
solder fillet, the hot-swap sockets and their contacts, the switch pins under the board, the XIAO,
the power switch and the reset button. Two deliberate exceptions, neither electrical:

- the top of each diode's epoxy body keeps 0.3 mm (an insulator; its metal leads keep 0.5 mm);
- the switch bodies above the board are plastic and still clip into the top plate as before.

The board is held exactly as in the original design: by the switches clipped into the top plate
and by the four M2 screws through the floating (no-net) mounting pads, from the top into threads
tapped in the bottom.

## What changed (outside: only the seam line, the wood window and the recess mouth noted below)

Top:
- plate underside lifted from the board (it used to rest on it) — 0.5 mm clear everywhere;
- pockets around the diodes, the XIAO, the power switch and the reset button grown to 0.5 mm;
- seam moved up 0.5 mm: the top is now 12.0 mm tall (was 12.5) so the 1/2" (12.7 mm) plate
  can be faced on both sides; the bottom rim grew 0.5 mm; total height unchanged;
- window through the roof above each XIAO (14 × 18.5 mm, from the far end of the module up to just
  short of the USB-C end) for Bluetooth, closed by the wood insert;
- the reset button's plastic plunger runs out through a 3.4 × 2.0 mm slot in the back seam (0.2 mm
  clear all round); only the switch's metal body got 0.5 mm;
- dogbones (R1.05, in the 1.2 mm clip ledge) at the four corners of every 13.8 mm switch cut-out,
  so a Ø2 mm end mill leaves room for the switches' square corners. They reach 0.33 mm past the
  cut-out's edges, over the 16 mm recess below, so the 3.2 mm webs between switches stay whole.

Bottom:
- floor under the board lowered to 0.5 mm clear; one clean rectangular pocket per switch around
  its socket, contacts, pins and pads;
- the leg recesses: the site lowered their roof from −2.6 to −7.3 but its mesh kept bits of the old
  roof (a 0.5–0.8 mm slit around the edge and a few corners). Those are filled up to the −7.3 roof,
  so each recess has one flat roof;
- no socket pocket goes through the part any more: in the site's bottom the switch-socket pockets
  broke through the leg-recess roofs (7 openings on the left half, 6 on the right). They are filled
  up to the −7.3 roof, so every pocket is blind (at least 4.7 mm of floor between it and the recess)
  and each recess keeps its original outline with one flat roof. Where a recess runs out to the
  edge of the part, the filled roof ends 0.1 mm inside the outer face, like the rest of the recess
  mouths. Nothing goes through the bottom: the screw holes are blind tapped holes from above (see
  `underside_holes.png`);
- where a pocket floor would still be thinner than 0.8 mm, a small pad underneath keeps it 0.8 mm
  thick;
- the TRRS jack is not fitted in the BLE build (the original bottom has a post where it would sit),
  so it gets no pocket.

## Made for a Ø2 mm flat end mill (3-axis, two setups)

The target is to cut every surface from above or below with a flat end mill of Ø2 mm or bigger:
inside corners at least R1.05, slots and pockets at least 2.1 mm wide, and no overhangs.
`CHECKS.md` records the current results and remaining exceptions, using a 0.05 mm projection grid.
The implemented machining changes are:

- every clearance pocket (board, parts, pads, XIAO, sockets, switch cut-outs, wood window) is cut
  as the mill makes it: dogbones (R1.05) at its corners, widened to 2.1 mm where it was narrower,
  and open toward the side it is cut from (the top's from below, the bottom's from above). So the
  0.5 mm clearance holds at the pocket corners too;
- everything else the mill couldn't reach is filled in: the narrow slots and hollow walls of the
  3D-printed design (0.4–0.8 mm gaps inside the top's outer walls and around the screw tubes), the
  engraved TOTEM logo on the top (0.5 mm deep, strokes far below 2 mm wide), inside corners sharper
  than R1.05, small steps under overhangs, the old R0.52 corner reliefs, the arched TRRS opening in
  the back wall (no jack in the BLE build) and the seam groove in the bottom's rim. About 365–375 mm³
  of aluminum per top and 100–110 mm³ per bottom. Nothing is taken off the outside; the outline only
  gains R1.05 fillets in its inside corners (≈1 mm² per top, ≈3 mm² per bottom, at most 0.6 mm at
  the sharpest corner) and the logo is gone. The fill never enters a clearance pocket, the board's
  keep-out, or the 0.20 mm seam gap to the other part;
- where the top nests into the bottom above the board (the two locating tongues and arches and the
  bottom's back wall under the top's), the bottom now stops 0.4 mm short of the top (was 0.15), cut
  so the mill makes it exactly: the mill leaves up to ~0.2 mm on the top's arches, and with this the
  vertical gap is 0.20 mm after machining (exact 3D minimum ≈0.2 mm, more than the original
  design's 0.15 mm). The seam line on the back wall is 0.25 mm wider above the board;
- the screw holes are drilled, not milled (see "Screws" below): in the top a 90° countersink
  (Ø4.30 at the top face) over a Ø2.4 pass-through hole; in the bottom a blind Ø1.6 hole, tapped M2.

- 3D toolpaths with the same Ø2 flat end mill where a face slopes: the bottoms' leg ramps (one 21.1°
  plane each, the original's own; its 0.32 mm side rails are left out, as a flat mill can't run a
  ramp up beside a wall), the 45° foot chamfers inside the walls and the power-switch notch's 30°
  flanks. The back-wall arches are square and the reset bevel straight (2 mm features a Ø2 flat
  mill can't shape), and the walls are exactly vertical (the site's mesh drafted them 0–2°).

## Parametric model (2026-10-24)

All six parts are now built by a parametric CadQuery model, `work/model.py`, instead of repairing
the 3D-print parts. It never opens those originals: `work/ref_extract.py` took their reference
shapes once into `work/model_ref.json` — the outline with the original top's own lines, arcs and
B-splines (the original bottom, a triangle mesh, follows it within 0.4 mm), the plateau, leg
recesses, battery pocket, feet and the leg ramp's plane fitted to the bottom's facets, and the top's
air band by band. Everything else is designed in the code: the walls, seams and notches, chamfers,
screw holes, the XIAO pocket and its open end, the window. The board, parts, pads and XIAO keep-outs
(from KiCad) are cut as the Ø2 mill makes them, drawn with true arcs; the top then makes room for
the bottom as the mill leaves it (0.2 mm), and a last check fills any speck the mill can't reach.
Every stage must be one valid solid that survives a STEP round trip. Rebuild: `cd work &&
python model.py all L` (and `R`), about 25 minutes per half.

Compared with the clean 2.5D parts before it: the leg ramps are planes instead of 0.5 mm steps; the
back and left walls are designed with a flat seam (the bottom's wall top at h, the top's 0.4 mm
above it; no lips and no fins); the outer outline keeps the original's B-splines; the reset slot is
sized to the plunger. Volumes: tops ≈17.56–17.58 cm³ (were 17.73–17.75), bottoms ≈70.72–70.76 cm³
(were 70.19–70.20).

## Clean CAD (2026-10-22, superseded by the parametric model)

The four aluminum parts were then rebuilt as clean CAD (`work/clean.py`), keeping the overall
size and everything that works (fit, clearances, screws, switch clips, leg recesses):

- every face is exactly vertical or flat: no more facets tilted by hundredths of a degree, and no
  more hairline micro-ledges (steps of a few microns between nearly identical walls, left by the
  mesh booleans). Outlines are lines and true arcs — the R1.05 dogbones, the bosses and the rounded
  corners are single arcs a CAM program can follow in one move;
- the bottoms are no longer the site's triangle mesh: the STEP files are now 11–17 MB (were
  25–82 MB) and every part passes the OpenCASCADE checks with no warnings at all;
- the screw holes are exact cylinders and cones (the site's mesh had them faceted, off by up to
  0.03 mm);
- fixed on the way:
  - the right bottom had a **slot through the part** (0.65 mm², at its right edge by the leg
    recess): the 22° ramp's steps had cut through a 0.4 mm floor. Closed, and that floor raised to
    its neighbours' top (1.1 mm thick now; the socket keep-out above allows it);
  - floors thinner than 0.8 mm made 0.8 mm (two small spots per bottom at the front rim: a pad
    up to 0.25 mm deep underneath);
  - hairline cracks inside the bottoms (horizontal gaps thinner than 0.05 mm, the largest 0.24 mm²)
    filled;
  - the XIAO had 0.4999 mm in the tops; its pocket is now 0.52 mm all round (0.02 mm off the
    walls and roof — the wood insert's flange gets a 0.02 mm glue gap under the roof);
  - the plate under the keycap wells was only 0.45–0.52 mm thick in five spots per top, where the
    rounded ends of the diode pockets (cut from below) poke out from under the webs between the
    wells. Each spot now has a 0.5 mm ledge on the well floor (z 3.65 → 4.15, 4.20 at the thumb
    key), so the plate is at least 1.0 mm there. The ledges keep 0.3 mm from the switch housings
    and 0.5 mm from the power switch and the XIAO; the keycaps, even fully
    pressed, stay more than 3 mm above them;
  - metal slivers under 0.05 mm thick next to the four back screw bores (where a keep-out notch
    nearly touches the bore) removed: the notch opens into the bore;
  - the few corners the changes left that a Ø2 mill can't reach filled as the mill leaves them
    (under 1 mm³ per part).

Each part lost 10–21 mm³ of metal, almost all of it hairline specks on the outer faces (at most
0.05 mm deep) and the exact screw holes; `CHECKS.md` lists every spot that differs from the build.

## Screw holes and the wall in front of the XIAO (2026-10-23)

- **Screws.** The original (3D printed) holds the case with 6 mm M2 standoffs in the top and an
  M2 × 6 screw into each end; its screw holes had necks only 0.13–0.18 mm long. In aluminum the
  threads are tapped in the bottom instead: per hole one **M2 × 16 countersunk screw (ISO 7046 /
  DIN 965, 90° head)** goes down through the top (90° countersink, Ø4.30 at the face, so the Ø3.8
  head sits 0.25 mm below it, then a Ø2.4 pass-through hole), the board's Ø3.2 mounting hole, and
  into a blind M2 thread in the bottom's boss (Ø1.6 tap drill 6 mm deep from the boss top, to
  z −6.5, which leaves 0.8 mm over the leg recess under two of the screws; tap 5.5 mm): 5.2 mm of
  thread engaged. No standoffs; the bottom's underside is solid at the
  screws. The top's bosses get more metal (the Ø3.2 bore is gone).
- **XIAO end.** The XIAO's USB-C end sits 0.64 mm inside the outer face, so with its 0.5 mm of room
  the wall in front of it was a 0.14 mm skin with the USB-C hole in it. That skin is now open over
  the module's end, from the bottom's pocket floor (z 1.1) to the top's pocket roof (z 6.45): the
  side opening is the module's end, about 19 × 5.4 mm, split by the seam. The USB-C port is easier
  to reach (a plug's overmould can come right up to it).
- **Back seam** (now designed in the parametric model: a flat seam over every stretch, see above).
  Along the back wall the two parts met in a tongue and groove whose halves were
  castellated: the original's arches, cut as 2.5D steps, left the bottom's outer lip (0.2 mm wide)
  jumping up and down every few tenths of a millimetre under a flat top, a toothed seam line on
  the back face. Over the straight runs of the back wall (x 32–60, 101–118 and 128–141 on the
  left, mirrored on the right; the power-switch and reset openings, the back bump and the XIAO's
  corner left as they are) the seam is now plain: the bottom's lip comes down to its flat ledge
  and the top's back wall stops one flat 0.4 mm above it, so the seam is a straight line 0.4 mm
  wide and the 0.2 mm lip is gone (the last 1.2 mm at each end of a run shows 1.1 mm: there the
  top keeps its old face, as the mill's R1 corner where its lowered face ends must stay over the
  lowered lip).
- **Walls beside the keycap wells.** Where a wall between a keycap well and a pocket was thinner
  than 0.8 mm (the worst, 0.45 mm and 3.3 mm tall, between the SWL1 well and the XIAO), the well's
  edge comes in by up to 1 mm beside it, as far as the keycaps allow: they keep 0.3 mm of room at
  rest and fully pressed, and so do the switch housings. Five spots per top, ≈140–155 mm³.

## Machining notes

- Fits the stock: parts are 133.1 × 99.0 in 140 × 105 (≈3.5 / 3 mm per side). Top 12.0 in 12.7;
  bottom 15.6 in 22.2.
- Two-sided work (inside/underside, then flip). The smallest tool needed is a Ø2 mm flat end mill;
  use bigger ones for roughing. Deepest Ø2 mm work: the switch-cut-out dogbones through the 1.2 mm
  ledge (reached from below through the 16 mm recesses, ~4 mm below the top's underside face) and
  the keycap-well corners (6.85 mm deep from the top face).
- Pockets and contours with flat end mills of Ø2 mm or larger; 3D finishing (same Ø2 flat end mill,
  small step-over) on the bottoms' leg ramps (from below), the foot chamfers inside the walls and
  the power-switch notch flanks (from above). The 90° screw countersinks in the tops are conical
  (90° countersink bit). Drill the
  tops' screw holes Ø2.4 through; drill the bottoms' Ø1.6, 6 mm deep from the boss tops (no
  deeper: two of them are 0.8 mm over a leg recess), and tap them M2 × 0.4 5.5 mm deep (a
  bottoming tap for the last turns).
- Walls still under 0.8 mm (all listed in `CHECKS.md`, "Walls thinner than 0.8 mm"); take light
  finishing passes there:
  - the corner of each bottom by the XIAO's back corner, where its pocket nearly meets both outer
    faces: 0.07–0.24 mm over about 1 mm²;
  - walls between the bottoms' socket and pad pockets: 0.24–0.78 mm, at most 2 mm tall (both
    sides are keep-outs);
  - in the tops: the walls in front of the reset button and power switch (0.4–0.6 mm, as in the
    original), the back seam's lips (0.3–0.6 mm), small steps at the diode pockets (0.3 mm tall)
    and the screw bosses' rings at the board (0.6–0.7 mm), all under 3.6 mm tall;
  - specks under 0.1 mm² in plan where two pocket outlines nearly meet.
  Floors and roofs are all at least 0.8 mm (1.0 mm in the tops).
- The panel tabs on the PCB edge (mouse-bites) must be sanded flush — clearances were measured
  from the true board outline.
- Wood insert: fit it from inside the top before assembly (flange under the roof); check the
  Bluetooth range with it in place before gluing.
- Deburr every edge that faces the board, especially the battery pocket, and wrap the LiPo and its
  protection board in Kapton tape.

## Checks

See `CHECKS.md` (exact distances from the KiCad board, parts and pads; thin-wall comparison with
the original; renders).

Original design: TOTEM, Copyright (c) 2022 GEIST, CERN-OHL-P v2 (see `LICENSE.md`).
Modified 2026-10-20 for an aluminum case as described above; 2026-10-21/22 made cuttable in two
setups with Ø2 mm flat end mills and rebuilt as clean CAD; 2026-10-24 rebuilt as a parametric
model with the original's slopes back (3D toolpaths).

## 3D view

Open `TOTEM_3d_view.html` in a browser (it loads three.js from the internet) to turn the whole build
around: both halves with the aluminum parts, wood windows, PCB, switches and sockets, diodes, XIAO,
power and reset switches, battery, screws and keycaps, each layer switchable, with an explode slider
and a see-through top.
