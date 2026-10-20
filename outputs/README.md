# TOTEM BLE case — aluminum version (no contact with the PCB)

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
- corner reliefs (Ø1.04 mm, in the 1.2 mm clip ledge only) at the four corners of every 13.8 mm
  switch cut-out, so a 1 mm end mill leaves room for the switches' square corners. Bigger reliefs
  would meet across the 3.2 mm web between neighbouring switches.

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

## Machining notes

- Fits the stock: parts are 133.1 × 99.0 in 140 × 105 (≈3.5 / 3 mm per side). Top 12.0 in 12.7;
  bottom 15.6 in 22.2.
- Two-sided work (inside/underside, then flip). Switch cut-outs: finish the 13.8 mm squares and
  their corner reliefs with a 1 mm end mill (the ledge is 1.2 mm thick). Small pockets: 2 mm end
  mill or smaller; the uncut corner fillet then still leaves ≥ 0.29 mm at a pocket's very corner.
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
Modified 2026-10-20 for an aluminum case as described above.

## 3D view

Open `TOTEM_3d_view.html` in a browser (it loads three.js from the internet) to turn the whole build
around: both halves with the aluminum parts, wood windows, PCB, switches and sockets, diodes, XIAO,
power and reset switches, battery, screws and keycaps, each layer switchable, with an explode slider
and a see-through top.
