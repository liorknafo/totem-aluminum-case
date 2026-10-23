# TOTEM BLE case — aluminum version (no contact with the PCB)

Machining: all four aluminum parts can be cut on a 3-axis mill in two setups with flat end mills
of Ø2 mm or bigger — no ball-nose tool. They are clean CAD: every face exactly vertical or flat,
outlines drawn with lines and true arcs, except the **82°** screw countersinks (an 82° countersink
bit, as in the original design; a 90° one would not seat the screw heads flush). The checks are
in `CHECKS.md`.

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
and by the four standoffs through the floating (no-net) mounting pads.

## What changed (outside: only the seam line, the wood window and the recess mouth noted below)

Top:
- plate underside lifted from the board (it used to rest on it) — 0.5 mm clear everywhere;
- pockets around the diodes, the XIAO, the power switch and the reset button grown to 0.5 mm;
- seam moved up 0.5 mm: the top is now 12.0 mm tall (was 12.5) so the 1/2" (12.7 mm) plate
  can be faced on both sides; the bottom rim grew 0.5 mm; total height unchanged;
- window through the roof above each XIAO (14 × 18.5 mm, from the far end of the module up to just
  short of the USB-C end) for Bluetooth, closed by the wood insert;
- the reset button keeps its original round access hole; only the switch's metal body got room;
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
  mouths. The only holes through the bottom are the 4 screw holes per half (see
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
- the screw holes are drilled, not milled: in the top a Ø2.0 neck with an 82° countersink above
  (Ø4.30 at the top face) and a Ø3.2 bore below for the 6 mm round standoff; in the bottom a Ø2.0
  neck with an 82° countersink below, down to a Ø4.30 counterbore. The countersinks want an 82°
  countersink bit: a flat end mill can't finish their narrow end. Unlike the original, both necks
  are about 1 mm long (see "Screw holes" below).

- strict 2.5D (no ball-nose mill): every sloped face became vertical walls and flat floors. The
  power-switch and reset bevels are straight openings at their outer size, the arches at the back
  wall are square, the 22° leg-recess ramps are 0.5 mm flat steps, and the bottoms' slightly drafted
  walls (from the site's mesh) are rebuilt exactly vertical. This only removes material
  (≈190 mm³ per bottom, mostly the stepped leg ramps; ≈20 mm³ per top), so no clearance gets smaller;
- R1.05 reliefs where the steps left a corner the Ø2 mill couldn't reach (3 per bottom, ≈15 mm³
  each half), also removal only.

## Clean CAD (2026-10-22)

The four aluminum parts were then rebuilt as clean CAD (`work/clean.py`), keeping the overall
size and everything that works (fit, clearances, screws, switch clips, leg recesses):

- every face is exactly vertical or flat: no more facets tilted by hundredths of a degree, and no
  more hairline micro-ledges (steps of a few microns between nearly identical walls, left by the
  mesh booleans). Outlines are lines and true arcs — the R1.05 dogbones, the bosses and the rounded
  corners are single arcs a CAM program can follow in one move;
- the bottoms are no longer the site's triangle mesh: the STEP files are now 11–17 MB (were
  25–82 MB) and every part passes the OpenCASCADE checks with no warnings at all;
- the screw holes are the exact cylinders and 82° cones of the original CAD (the site's mesh had
  them faceted, off by up to 0.03 mm);
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

- **Screw holes.** In the original, the Ø3.2 standoff bore in the top reached z 9.0, so the Ø2.0
  neck under the countersink was only 0.18 mm long; in the bottom the countersink came within
  0.13 mm of the boss top. Both would tear when drilled. Now the top's bore stops at z 8.0 (the
  6 mm standoff sits 1 mm lower, z 2.0–8.0, still 0.4 mm clear of the board) and the bottom's
  countersink and counterbore sit 0.9 mm deeper: both necks are 1.0–1.2 mm long. Same screws
  (M2 × 6 countersunk) and standoffs: the top screw engages the standoff 3.8 mm, the bottom screw
  1.4 mm (was 1.3), and the two tips stay 0.8 mm apart inside it.
- **XIAO end.** The XIAO's USB-C end sits 0.64 mm inside the outer face, so with its 0.5 mm of room
  the wall in front of it was a 0.14 mm skin with the USB-C hole in it. That skin is now open over
  the module's end, from the bottom's pocket floor (z 1.1) to the top's pocket roof (z 6.45): the
  side opening is the module's end, about 19 × 5.4 mm, split by the seam. The USB-C port is easier
  to reach (a plug's overmould can come right up to it).
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
- All 2.5D: pockets and contours only, vertical walls and flat floors, flat end mills of Ø2 mm or
  larger. Only the 82° screw countersinks are conical (82° countersink bit); screw holes are
  drilled Ø2.0 as in the original — open them to Ø2.2 if your M2 screws bind.
- Walls still under 0.8 mm (all listed in `CHECKS.md`, "Walls thinner than 0.8 mm"); take light
  finishing passes there:
  - the bottom's back-wall lip, the outer half of the back seam's tongue and groove: 0.12–0.25 mm
    wide, 0.5–0.7 mm tall, along about 30 mm of each back wall (x 30–60 left);
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
setups with Ø2 mm flat end mills, strictly 2.5D, and rebuilt as clean CAD.

## 3D view

Open `TOTEM_3d_view.html` in a browser (it loads three.js from the internet) to turn the whole build
around: both halves with the aluminum parts, wood windows, PCB, switches and sockets, diodes, XIAO,
power and reset switches, battery, screws and keycaps, each layer switchable, with an explode slider
and a see-through top.
