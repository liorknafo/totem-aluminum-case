# TOTEM BLE case — aluminum version (no contact with the PCB)

Machining: all four aluminum parts can be cut on a 3-axis mill in two setups with flat end mills
of Ø2 mm or bigger — no ball-nose tool. Every face is vertical or flat except the 90° screw
countersinks (countersink bit). The checks are in `CHECKS.md`.

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
- where a pocket floor would still be thinner than 0.6 mm, a small pad underneath keeps it 0.6 mm
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
- the screw holes are drilled, not milled: Ø2.0 neck in the top (with its 90° countersink above
  and the Ø3.2 bore below) and Ø2.16 in the bottom (Ø4.25 counterbore and countersink below). The
  countersinks want a countersink or chamfer tool: a flat end mill can't finish their narrow end.

- strict 2.5D (no ball-nose mill): every sloped face became vertical walls and flat floors. The
  power-switch and reset bevels are straight openings at their outer size, the arches at the back
  wall are square, the 22° leg-recess ramps are 0.5 mm flat steps, and the bottoms' slightly drafted
  walls (from the site's mesh) are rebuilt exactly vertical. This only removes material
  (≈190 mm³ per bottom, mostly the stepped leg ramps; ≈20 mm³ per top), so no clearance gets smaller;
- R1.05 reliefs where the steps left a corner the Ø2 mill couldn't reach (3 per bottom, ≈15 mm³
  each half), also removal only.

The bottoms come from the site's triangle mesh, so their STEP faces are flat facets (as before);
the few curved faces on the bottom rim are facets within 0.001 mm. Facets tilted by less than
0.01° (rounding in the mesh booleans, under 0.002 mm across a wall) are reported in `CHECKS.md`
but are not slopes a mill can see.

## Machining notes

- Fits the stock: parts are 133.1 × 99.0 in 140 × 105 (≈3.5 / 3 mm per side). Top 12.0 in 12.7;
  bottom 15.6 in 22.2.
- Two-sided work (inside/underside, then flip). The smallest tool needed is a Ø2 mm flat end mill;
  use bigger ones for roughing. Deepest Ø2 mm work: the switch-cut-out dogbones through the 1.2 mm
  ledge (reached from below through the 16 mm recesses, ~4 mm below the top's underside face) and
  the keycap-well corners (6.85 mm deep from the top face).
- All 2.5D: pockets and contours only, vertical walls and flat floors, flat end mills of Ø2 mm or
  larger. Only the 90° screw countersinks are conical (countersink bit); screw holes are drilled.
- Behind the reset button's round hole the wall is 0.59 mm thick over a small area (in front of
  the switch-body pocket): take a light finishing pass there.
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
setups with Ø2 mm flat end mills, strictly 2.5D.

## 3D view

Open `TOTEM_3d_view.html` in a browser (it loads three.js from the internet) to turn the whole build
around: both halves with the aluminum parts, wood windows, PCB, switches and sockets, diodes, XIAO,
power and reset switches, battery, screws and keycaps, each layer switchable, with an explode slider
and a see-through top.
