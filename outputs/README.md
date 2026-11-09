# TOTEM BLE case in aluminum: parts, design and machining notes

A parametric case generated from the TOTEM KiCad board (`src/totem_0_3.kicad_pcb`) by
`work/build.py`. It is a new design: the board outline, the footprint positions, the pads and the
KiCad 3D part models drive it. No geometry from the original case files is used. Units mm. The
coordinates are the board's (x = KiCad x, y = −KiCad y), with z = 0 at the board's bottom face.

| File | Part | Stock | Size (x × y × z) |
|---|---|---|---|
| `TOTEM_alu_top_L.step`, `TOTEM_alu_top_R.step` | aluminum top | 140 × 105 × 1/2" (12.7) plate | 132.8 × 99.0 × 9.9 |
| `TOTEM_alu_bottom_L.step`, `TOTEM_alu_bottom_R.step` | aluminum tenting bottom | 140 × 105 × 7/8" (22.2) plate | 132.8 × 99.0 × 12.0 |
| `TOTEM_wood_window_insert_L.step`, `..._R.step` | wood window over the XIAO | 3 mm wood | 21.3 × 17.0 × 3.0 |

Every STEP face is a plane or a cylinder; `CHECKS.md` gives the counts.

## The rule

No aluminum surface comes closer than **0.5 mm** to the board or to anything electrical on it. That
covers:

- the board edge and both faces, including 0.05 mm of copper and mask;
- every pad, with room for its solder fillet (1.0 mm high on SMD pads and on the soldered side of
  through-hole pads, 0.6 mm on the diode pads, 0.3 mm pushed through to the other side, spreading
  0.3 mm beyond the pad);
- the hot-swap sockets and their contacts, the switch pins under the board;
- the XIAO, the power switch and the reset button.

Two exceptions, neither electrical:

- the epoxy top of each diode keeps 0.3 mm (its metal leads keep 0.5 mm);
- the plastic switch bodies clip into the top plate: 13.8 mm cut-outs in a 1.2 mm clip ledge.

The plastic power-slider knob and reset plunger sit in their openings in the back wall.

Where the panel tabs between the halves are snapped off, up to 0.3 mm of tab may stay proud of the
board edge; the case allows for it.

## The design

**Outline.** The board outline grown by 2.3 mm: a 0.5 mm gap plus a 1.8 mm wall. Inside corners of
the outline are rounded to R3. The outline grows around the reset button, which overhangs the board
edge, so 1.8 mm of wall stays in front of it. The board's Bézier edges are replaced by tangent arcs
within 0.005 mm, so the walls stay cylindrical.

**Top** (z 0.6 to 10.5):

- A flat deck at 10.5 with a 1.5 mm rim.
- A well around each key, 1 mm clear of a 17.5 × 16.5 mm choc keycap, with its floor at 4.25. A
  pressed keycap's skirt comes down to about 5.0. Wells of neighbouring keys merge; deck islands
  smaller than 150 mm² between them are removed.
- In each well, a 15.7 mm square zone down to the plate top at 3.65, where the 15 mm top housing of
  the switch sits.
- The clip plate (2.45 to 3.65) has 13.8 mm cut-outs. Each corner gets a Ø2.1 relief, pushed
  sideways along the row into the 4.2 mm web between columns, so a Ø2 mm end mill leaves room for the
  switch's square corners.
- The underside is a single cavity at 2.45, which is 0.85 mm above the board (0.80 mm above its
  copper). Above that, blind pockets from below rise only as high as each item needs:
  - diodes: 3.14 over the epoxy, 2.75 over their pads;
  - solder on SMD pads and on the XIAO and battery-wire pads: 3.15;
  - power switch: 3.6;
  - XIAO: 6.43;
  - reset button: 6.5.
- Openings in the back wall, open at the seam and cut from below:
  - the USB-C port: 13 mm wide, up to 8.2;
  - the power slider: 6 mm wide for its travel, up to 3.4;
  - the reset plunger: a 3.6 mm slot up to 5.3, for a pin or paper clip.
- Window over the XIAO: 14 × 18.3 mm (R2) through the 1.5 mm roof, from the far end of the module
  to just short of the USB-C end. The wood insert closes it: a plug in the roof with a 1.5 mm flange
  under it, 3 mm wood in all. The flange sits in a recess 0.2 mm larger all round. The insert keeps
  1.6 mm from the XIAO.
- Four M2 holes for the screws: Ø1.6 tap drill from the cavity roof, 5.5 mm deep. The wells keep
  2.5 mm away from each screw axis, so there is solid material around the thread.

**Bottom** (z −11.4 to 0.6):

- One cavity under the whole board, its floor at −2.6. The lowest part under the board is a hot-swap
  socket at −2.04, so the floor clears it by 0.56. Where a socket contact overhangs the board edge
  (the outer thumb key), the rim is cut back only as deep as that contact needs.
- A battery pocket of 16 × 23 mm (R1.5) for up to a 15 × 22 × 7.5 mm LiPo, floor at −9.7. It is
  placed next to the battery pads; the battery's top may sit just under the sockets.
- From below:
  - two recesses for the adhesive tenting feet, 57.4 × 19.2 mm (R3.5), 4.1 deep. They are placed as
    on the original tenting bottom, and the thumb one is moved 1.6 mm inward to keep a 1.6 mm side
    wall.
  - five Ø9 × 0.4 mm recesses for 8.5 mm rubber feet;
  - the four screw holes: Ø2.4 through, counterbored Ø4.4 up to z −5.2 for the screw heads, so the
    head stays inside even in a leg recess.
- The screw holes are the only openings through the bottom.

**Assembly.**

- The board hangs from its 19 switches, clipped into the top plate. Nothing else touches it.
- Four M2 × 12 socket-head cap screws (ISO 4762) per half go in from below. Each passes through a
  counterbore, the bottom, the board's Ø3.2 no-net mounting hole (0.6 mm clear all round) and into
  the thread in the top (4.4 mm of thread engaged).
- Top and bottom meet on a flat seam at z 0.6, about 363 mm² of contact.

*Change from the earlier aluminum version:* that version had aluminum bosses that came down to 0.1 mm
from each mounting pad, with M2 standoffs. Every mounting hole is only about 3.5 mm from the board
edge. A Ø2 mm end mill cannot cut the narrow gap between such a boss and the side wall, and what it
leaves would be aluminum within 0.5 mm of the board. So the bosses are gone, and the tapped top does
the job of the standoffs.

**Hardware per half:**

- 4 × M2 × 12 socket-head screws;
- 5 × 8.5 mm rubber feet;
- 2 adhesive tenting feet (as for the original tenting case);
- a LiPo of up to 15 × 22 × 7.5 mm.

**Right half.** The right half is not a mirror of the left. The board places the same footprints on
the same face for both halves: sockets, power switch and reset button are not mirrored, and positions
differ by up to about 8 mm (the power switch). Both halves are built from the board the same way. Only
the leg, feet and battery positions, which do not come from the board, are mirrored. `CHECKS.md` has
the comparison.

## Machining notes

Two setups per part, on a 3-axis mill. Every face is horizontal or vertical, and every horizontal face
can be reached straight from above or from below (checked on the solids). Inside corners and the end
mills they need:

| Feature | Inside corner radius | End mill |
|---|---|---|
| Cavities, pockets, wall openings, switch-zone corners, cut-out reliefs | ≥ 1.05 | Ø2 flat (smallest) |
| Key wells | 1.5 | Ø3 flat |
| Battery pocket | 1.5 | Ø3 |
| Window | 2.0 (plug 1.9) | Ø3 or Ø4 |
| Wood flange recess | 2.2 | Ø4 |
| Leg recesses | 3.5 | Ø6 |
| Inside corners of the outer outline | 3.0 | Ø6 or smaller |

Drills: Ø1.6 (M2 tap drill) and Ø2.4, plus an M2 tap. The Ø4.4 counterbores can be cut by helical
milling with a Ø3 end mill.

Top (1/2" plate, 9.9 mm finished, 0.4 mm to face on each side):

1. **Underside up.** Face to the seam (z 0.6). Pocket the cavity to 2.45 and the blind pockets to
   their heights; the deepest is the wood-flange recess at 9.0, 8.4 mm from the seam face. Cut the
   wall openings. Cut the 13.8 mm switch cut-outs and their reliefs through the plate, Ø2, 3.05 mm
   deep from this side. Drill and tap the four M2 holes.
2. **Top up.** Face to 10.5. Cut the key wells to 4.25 (Ø3, 6.25 deep), then the switch zones to 3.65
   (Ø2: their corners need 6.85 mm of reach, so use a long-reach or reduced-neck end mill). Cut the
   window and the outer profile.

Bottom (7/8" plate, 12.0 mm finished):

1. **Inside up.** Face to the seam (z 0.6). Pocket the cavity to −2.6, the battery pocket to −9.7 and
   the shallow cut for the overhanging socket contact. Drill Ø2.4 through.
2. **Underside up.** Face to −11.4. Cut the leg recesses (4.1 deep), the feet recesses (0.4) and the
   counterbores up to −5.2.

Thinnest walls, floors and roofs (`CHECKS.md` has the full list):

- 0.78 mm (left) and 0.80 mm (right) of plate between the pocket over diode DL16/DR16 and the switch
  zone of SWL16/SWR16: that diode sits 0.8 mm from the switch housing. Take a light finishing pass there.
- Everything else is at least 0.87 mm.
- The switch clip ledge is 1.2 mm.

Wood insert: from 3 mm wood, cut a 1.5 mm rabbet that leaves a 13.8 × 18.1 mm plug (R1.9) on a
17.0 × 21.3 mm flange (R2). Fit it from inside the top before assembly, flange under the roof. Check
the Bluetooth range with it in place before gluing.

Deburr every edge that faces the board, especially the cavity rims and the battery pocket. Wrap the
LiPo and its protection board in Kapton tape. Solder the battery wires with low joints: the build
allows 1.0 mm of solder on top of those pads.

## Checks and pictures

`CHECKS.md` has the measured clearances per category, the assembly, thicknesses, machinability,
the openings through the bottom, solid validity, face types per STEP file, the mirror comparison and
the build times. The pictures:

- `render3d_L.png`, `render3d_R.png`: the parts;
- `sections_L.png`: cross-sections through the assembly;
- `clearance_L.png`, `clearance_R.png`: gap from the board faces;
- `openings_L.png`: the back-wall openings.

## 3D view

Open `TOTEM_3d_view.html` in a browser (it loads three.js from the internet) to turn the whole build
around. It shows both halves with the aluminum parts, wood windows, PCB, switches and sockets, diodes,
power switch, reset button, XIAO, battery, screws and keycaps. Each layer can be switched on and off,
and there is an explode slider and a see-through top.

Design derived from the TOTEM PCB, Copyright (c) 2022 GEIST, CERN-OHL-P v2 (see `LICENSE.md`).
