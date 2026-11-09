# Checks (measured on the STEP files in this folder)

Written by `work/check.py` and `work/report.py`. Distances are exact (OpenCASCADE BRepExtrema)
between each part as read back from its STEP file and everything taken from the board file
`src/totem_0_3.kicad_pcb`: the board (its outline with the tabs removed, 1.6 mm plus 0.05 mm of
copper and mask on each face), every 3D part on that half (each footprint's own model files from
`src/TOTEM3D`, placed by its `(model ...)` entry on the 1.6 mm board) and every copper pad (0.05 mm
proud of its face). KiCad's STEP exports in `src/` are only compared with these (end of this
file). Distances above 3 mm are shown as 3.00.

**The rule:** at least 0.5 mm from aluminum to the board and to everything electrical on it.

## Clearances

| | Required | Left | Right |
|---|---|---|---|
| Top to board | ≥ 0.50 | 0.52 mm | 0.52 mm |
| Bottom to board | ≥ 0.50 | 0.52 mm | 0.52 mm |
| Top to board with 0.3 mm tab nubs | ≥ 0.50 | 0.52 mm | 0.52 mm |
| Bottom to board with 0.3 mm tab nubs | ≥ 0.50 | 0.52 mm | 0.52 mm |
| Top to copper pads | ≥ 0.50 | 0.77 mm | 0.77 mm |
| Bottom to copper pads | ≥ 0.50 | 0.77 mm | 0.77 mm |
| Top to solder fillets (allowance envelopes on the pads) | ≥ 0.50 | 0.50 mm | 0.50 mm |
| Bottom to solder fillets (allowance envelopes on the pads) | ≥ 0.50 | 0.50 mm | 0.50 mm |
| Top to XIAO (module and USB-C, Seeed model extents) | ≥ 0.50 | 0.50 mm | 0.50 mm |
| Bottom to XIAO (module and USB-C, Seeed model extents) | ≥ 0.50 | 1.17 mm | 1.13 mm |
| Wood insert to XIAO | no contact | 1.57 mm | 1.57 mm |
| Top to diode (whole part; epoxy top may come to 0.3) | ≥ 0.30 | 0.32 mm | 0.32 mm |
| Bottom to diode (whole part; epoxy top may come to 0.3) | ≥ 0.50 | 2.16 mm | 2.06 mm |
| Top to diode leads and body sides | ≥ 0.50 | 0.57 mm | 0.57 mm |
| Bottom to diode leads and body sides | ≥ 0.50 | 2.16 mm | 2.06 mm |
| Top to hot-swap socket and contacts | ≥ 0.50 | 1.04 mm | 1.05 mm |
| Bottom to hot-swap socket and contacts | ≥ 0.50 | 0.56 mm | 0.56 mm |
| Top to power switch actuator (plastic), over its travel | ≥ 0.50 | 0.60 mm | 0.60 mm |
| Bottom to power switch actuator (plastic), over its travel | ≥ 0.50 | 1.20 mm | 1.20 mm |
| Top to power switch body (metal) | ≥ 0.50 | 0.52 mm | 0.52 mm |
| Bottom to power switch body (metal) | ≥ 0.50 | 1.26 mm | 1.26 mm |
| Top to reset button actuator (plastic), over its travel | ≥ 0.50 | 0.52 mm | 0.52 mm |
| Bottom to reset button actuator (plastic), over its travel | ≥ 0.50 | 2.70 mm | 2.70 mm |
| Top to reset button body (metal) | ≥ 0.50 | 0.52 mm | 0.52 mm |
| Bottom to reset button body (metal) | ≥ 0.50 | 1.00 mm | 1.00 mm |
| Top to switch pins under the board | ≥ 0.50 | 2.52 mm | 2.52 mm |
| Bottom to switch pins under the board | ≥ 0.50 | 1.00 mm | 1.00 mm |
| Keycaps (pressed, skirt at z 5.0) to the top | ≥ 0.30 | 0.33 mm | 0.34 mm |

Allowances used for solder: 1.0 mm above SMD pads and on the soldered side of through-hole pads
(the XIAO castellations and the battery-wire pads are soldered on top), 0.6 mm on the diode pads,
0.3 mm pushed through to the component side, none on the hot-swap switch-pin rings and on the
TRRS footprint (not fitted). A fillet may spread 0.3 mm beyond its pad.

The plastic switch bodies clip into the 13.8 mm plate cut-outs (a fit, not a clearance); their pins
under the board keep the rule. The diodes may come to 0.30 mm on top of their epoxy body; their leads and
sides keep 0.50. The power slider knob (measured at five places over ±1.5 mm of travel) and the reset
plunger keep 0.50 in their openings, like everything else.

Parts are placed from the board file: each footprint's 3D models (`src/TOTEM3D`) with the offset
and rotation of its `(model ...)` entry, on the top face of the 1.6 mm board. KiCad's own exports
in `src/` are only compared against that (see the end of this file).

## Spacers at the mounting pads

Each no-net mounting pad gets an insulating spacer (Ø ≤ 5.0 mm) above and below the board: a
1.0 mm one in a Ø5.4 seat in the top and a 3.0 mm one in a Ø5.4 seat in the floor.
Both stop 0.1 mm from the pad copper, so the board can move no more than that at the pads.

| Side | Mounting hole | Spacer gap to the board (below, above) | Within the pad | Nearest part | Seated (top, bottom) |
|---|---|---|---|---|---|
| L | (139.5, -112.0) | 0.10, 0.10 mm | yes (pad Ø5.6) | 2.77 mm (DL19) | 0.00, 0.00 mm |
| L | (34.3, -121.01) | 0.10, 0.10 mm | yes (pad Ø5.6) | > 3 mm | 0.00, 0.00 mm |
| L | (57.0, -52.7) | 0.10, 0.10 mm | yes (pad Ø5.6) | 1.70 mm (PWR) | 0.00, 0.00 mm |
| L | (131.2, -52.7) | 0.10, 0.10 mm | yes (pad Ø5.6) | 1.65 mm (RSW1) | 0.00, 0.00 mm |
| R | (265.7, -121.0) | 0.10, 0.10 mm | yes (pad Ø5.6) | > 3 mm | 0.00, 0.00 mm |
| R | (243.0, -52.7) | 0.10, 0.10 mm | yes (pad Ø5.6) | 1.60 mm (PWR) | 0.00, 0.00 mm |
| R | (160.5, -112.0) | 0.10, 0.10 mm | yes (pad Ø5.6) | 2.77 mm (DR19) | 0.00, 0.00 mm |
| R | (168.8, -52.7) | 0.10, 0.10 mm | yes (pad Ø5.6) | 1.65 mm (RST) | 0.00, 0.00 mm |

## Assembly

- L: top/bottom overlap 0.0 mm³, gap 0.0 mm, seam contact 359.4 mm² at z 0.6; wood insert/top overlap 0.0 mm³, gap 0.0 mm
- R: top/bottom overlap 0.0 mm³, gap 0.0 mm, seam contact 359.0 mm² at z 0.6; wood insert/top overlap 0.0 mm³, gap 0.0 mm

## Wall, floor and roof thickness

Thinnest material between opposing faces (walls, floors, roofs and diagonal necks), measured on the
solids. Designed minimum 1.0 mm, except the 1.2 mm switch clip ledge.

- L top: 0.84 mm at (32.8, -100.5, z 3.36); 0.84 mm at (32.8, -100.5, z 3.36); 0.84 mm at (35.9, -100.0, z 3.36); 0.87 mm at (51.6, -69.5, z 6.43)
- L bottom: 1.11 mm at (147.3, -131.0, z 0.60); 1.11 mm at (148.4, -129.0, z 0.60); 1.17 mm at (147.4, -130.7, z 0.60); 1.39 mm at (144.9, -112.0, z 0.60)
- R top: 0.86 mm at (264.1, -100.0, z 3.36); 0.86 mm at (267.2, -100.5, z 3.36); 0.86 mm at (267.2, -100.5, z 3.36); 0.88 mm at (248.3, -69.5, z 6.43)
- R bottom: 1.13 mm at (280.0, -108.5, z 0.60); 1.13 mm at (280.4, -106.2, z 0.60); 1.18 mm at (280.3, -106.5, z 0.60); 1.39 mm at (155.0, -106.5, z 0.60)

## Machining

- Every face is horizontal or vertical (2.5D), and every horizontal face is reachable straight from
  above or from below: two setups, no undercuts.
  - L top: tilted faces 0, horizontal faces not reachable 0, inside corners tighter than R1.0 0
  - L bottom: tilted faces 0, horizontal faces not reachable 0, inside corners tighter than R1.0 0
  - L insert: tilted faces 0, horizontal faces not reachable 0, inside corners tighter than R1.0 0
  - R top: tilted faces 0, horizontal faces not reachable 0, inside corners tighter than R1.0 0
  - R bottom: tilted faces 0, horizontal faces not reachable 0, inside corners tighter than R1.0 0
  - R insert: tilted faces 0, horizontal faces not reachable 0, inside corners tighter than R1.0 0
- Inside corners were checked on sections through every height step of each solid: none needs
  an end mill smaller than Ø2 mm.
- Vertical lines through the bottom (0.2 mm grid): the only openings are the screw holes:
  - L: (131.2, -52.7) 2.4 x 2.4 mm; (139.5, -112.0) 2.4 x 2.4 mm; (34.3, -121.0) 2.4 x 2.4 mm; (57.0, -52.7) 2.4 x 2.4 mm
  - R: (168.8, -52.7) 2.4 x 2.4 mm; (160.5, -112.0) 2.4 x 2.4 mm; (243.0, -52.7) 2.4 x 2.4 mm; (265.7, -121.0) 2.4 x 2.4 mm

## Solids and STEP faces

| File | Valid | Solids | Shells | Closed | Analyzer | Faces | Size x × y × z (mm) | z | Volume (mm³) |
|---|---|---|---|---|---|---|---|---|---|
| `TOTEM_alu_top_L.step` | True | 1 | 1 | True | clean | 555 cylinder, 498 plane | 132.76 × 98.95 × 9.9 | 0.6 … 10.5 | 30106.0 |
| `TOTEM_alu_bottom_L.step` | True | 1 | 1 | True | clean | 123 cylinder, 72 plane | 132.76 × 98.95 × 12.0 | -11.4 … 0.6 | 78505.6 |
| `TOTEM_wood_window_insert_L.step` | True | 1 | 1 | True | clean | 8 cylinder, 11 plane | 21.3 × 17.0 × 3.0 | 7.5 … 10.5 | 908.0 |
| `TOTEM_alu_top_R.step` | True | 1 | 1 | True | clean | 559 cylinder, 498 plane | 132.76 × 98.95 × 9.9 | 0.6 … 10.5 | 30103.9 |
| `TOTEM_alu_bottom_R.step` | True | 1 | 1 | True | clean | 127 cylinder, 72 plane | 132.76 × 98.95 × 12.0 | -11.4 … 0.6 | 78502.0 |
| `TOTEM_wood_window_insert_R.step` | True | 1 | 1 | True | clean | 8 cylinder, 11 plane | 21.3 × 17.0 × 3.0 | 7.5 … 10.5 | 908.0 |

Only planes and cylinders: no B-spline, no triangulated faces. Stock: 140 × 105 mm; the top from
1/2" (12.7 mm) plate is 9.9 mm tall, the bottom from 7/8" (22.2 mm) plate is 12.0 mm tall.

## Is the right half a mirror of the left?

Mirrored about x = 150 (KiCad), the right half of the board compares with the left like this:

| Footprints | Count | Largest position difference | Angle mirrored | Angle the same |
|---|---|---|---|---|
| Kailh_socket | 19 | 0.181 mm | 19 | 0 |
| Diode_SOD123 | 19 | 0.005 mm | 0 | 18 |
| MountingHole | 4 | 0.014 mm | 4 | 0 |
| BatteryPad | 2 | 0.000 mm | 2 | 0 |
| MSK12C02 | 1 | 7.800 mm | 0 | 1 |
| SKHLLCA010 | 1 | 0.000 mm | 1 | 0 |
| MJ-4PP-9 | 1 | 0.000 mm | 1 | 0 |
| xiao | 1 | 0.000 mm | 1 | 0 |

Outline: largest deviation 0.115 mm, area difference 20.838 mm². The right half is not a mirror of the left: the parts are the same footprints placed on the same face (sockets, power switch, reset button are not mirrored) and some positions differ. Both halves are built from the board the same way.

## KiCad exports compared with the board file

- `comp_all.step`: largest sideways difference of a part's box 0.0 mm; z offsets of the export [0.005] mm (the parts here sit on the 1.6 mm board's top face; the export puts them that much lower); stale parts: none
- `pcb_board.step`: the outline from the board file is at most 0.009 mm from the export's outline (tab openings aside; the export's cut-outs also include the drilled holes, which the checks leave in the board, so they measure against more board, not less)
- `pads.step`: 306 copper pads in the board file (602 exported pad solids, through-hole pads once per face); the largest distance from a pad's centre to an exported pad's centre is 0.0 mm

## Build

- L: start, board and part boxes 3.3 s, 2D design 6.5 s, solids 5.0 s, STEP write and read-back 1.0 s
- R: start, board and part boxes 3.3 s, 2D design 6.7 s, solids 5.1 s, STEP write and read-back 1.0 s

## Pictures

- `render3d_L.png`, `render3d_R.png`: each half: top from above and below, bottom from above and below
- `sections_L.png`: cross-sections through the left half (top, board and parts, bottom)
- `clearance_L.png`, `clearance_R.png`: gap from the board faces to the aluminum, seen from above
- `openings_L.png`: the USB-C, power-switch and reset openings in the back wall
