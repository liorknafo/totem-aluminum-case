# Checks (measured on the STEP files in this folder)

Written by `work/check.py` and `work/report.py`. Distances are exact (OpenCASCADE BRepExtrema)
between each part as read back from its STEP file and: the board (true outline from
`src/pcb_board.step`, 1.6 mm plus 0.05 mm of copper and mask on each face), every KiCad 3D part on
that half (`src/comp_all.step`, top-side parts on the 1.6 mm board) and every copper pad
(`src/pads.step`). Distances above 3 mm are shown as 3.00.

**The rule:** at least 0.5 mm from aluminum to the board and to everything electrical on it.

## Clearances

| | Required | Left | Right |
|---|---|---|---|
| Top to board | ≥ 0.50 | 0.51 mm | 0.51 mm |
| Bottom to board | ≥ 0.50 | 0.51 mm | 0.51 mm |
| Top to copper pads | ≥ 0.50 | 0.77 mm | 0.77 mm |
| Bottom to copper pads | ≥ 0.50 | 0.77 mm | 0.77 mm |
| Top to solder fillets (allowance envelopes on the pads) | ≥ 0.50 | 0.50 mm | 0.50 mm |
| Bottom to solder fillets (allowance envelopes on the pads) | ≥ 0.50 | 0.50 mm | 0.50 mm |
| Top to XIAO (module and USB-C, Seeed model extents) | ≥ 0.50 | 0.50 mm | 0.50 mm |
| Bottom to XIAO (module and USB-C, Seeed model extents) | ≥ 0.50 | 1.17 mm | 1.13 mm |
| Wood insert to XIAO | no contact | 1.57 mm | 1.57 mm |
| Top to diode (whole part; epoxy top may come to 0.3) | ≥ 0.30 | 0.32 mm | 0.32 mm |
| Bottom to diode (whole part; epoxy top may come to 0.3) | ≥ 0.50 | 2.19 mm | 2.10 mm |
| Top to diode leads and body sides | ≥ 0.50 | 0.57 mm | 0.57 mm |
| Bottom to diode leads and body sides | ≥ 0.50 | 2.19 mm | 2.10 mm |
| Top to hot-swap socket and contacts | ≥ 0.50 | 1.04 mm | 1.05 mm |
| Bottom to hot-swap socket and contacts | ≥ 0.50 | 0.56 mm | 0.56 mm |
| Top to power switch actuator (plastic, in its opening) | ≥ 0.30 | 0.52 mm | 0.52 mm |
| Bottom to power switch actuator (plastic, in its opening) | ≥ 0.30 | 1.28 mm | 1.28 mm |
| Top to power switch body (metal) | ≥ 0.50 | 0.52 mm | 0.52 mm |
| Bottom to power switch body (metal) | ≥ 0.50 | 1.33 mm | 1.33 mm |
| Top to reset button actuator (plastic, in its opening) | ≥ 0.30 | 0.32 mm | 0.32 mm |
| Bottom to reset button actuator (plastic, in its opening) | ≥ 0.30 | 2.69 mm | 2.69 mm |
| Top to reset button body (metal) | ≥ 0.50 | 0.52 mm | 0.52 mm |
| Bottom to reset button body (metal) | ≥ 0.50 | 0.99 mm | 0.99 mm |
| Top to switch pins under the board | ≥ 0.50 | 2.52 mm | 2.52 mm |
| Bottom to switch pins under the board | ≥ 0.50 | 1.00 mm | 1.00 mm |
| Keycaps (pressed, skirt at z 5.0) to the top | ≥ 0.30 | 0.33 mm | 0.34 mm |

Allowances used for solder: 1.0 mm above SMD pads and on the soldered side of through-hole pads
(the XIAO castellations and the battery-wire pads are soldered on top), 0.6 mm on the diode pads,
0.3 mm pushed through to the component side, none on the hot-swap switch-pin rings and on the
TRRS footprint (not fitted). A fillet may spread 0.3 mm beyond its pad.

The plastic switch bodies clip into the 13.8 mm plate cut-outs (a fit, not a clearance); their pins
under the board keep the rule. The diodes may come to 0.30 mm on top of their epoxy body; their leads and sides
keep 0.50. The power slider knob and the reset plunger are plastic and sit in their openings.

## Assembly

- L: top/bottom overlap 0.0 mm³, gap 0.0 mm, seam contact 359.7 mm² at z 0.6; wood insert/top overlap 0.0 mm³, gap 0.0 mm
- R: top/bottom overlap 0.0 mm³, gap 0.0 mm, seam contact 359.4 mm² at z 0.6; wood insert/top overlap 0.0 mm³, gap 0.0 mm

## Wall, floor and roof thickness

Thinnest material between opposing faces (walls, floors, roofs and diagonal necks), measured on the
solids. Designed minimum 1.0 mm, except the 1.2 mm switch clip ledge.

- L top: 0.78 mm at (32.8, -100.5, z 3.40); 0.78 mm at (32.8, -100.5, z 3.40); 0.78 mm at (35.9, -100.0, z 3.40); 0.87 mm at (36.3, -99.9, z 3.40)
- L bottom: 1.11 mm at (147.3, -131.0, z 0.60); 1.11 mm at (148.4, -129.0, z 0.60); 1.17 mm at (147.4, -130.7, z 0.60); 1.39 mm at (144.9, -112.0, z 0.60)
- R top: 0.80 mm at (264.1, -100.0, z 3.40); 0.80 mm at (267.2, -100.5, z 3.40); 0.80 mm at (267.2, -100.5, z 3.40); 0.88 mm at (248.3, -69.5, z 6.43)
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
| `TOTEM_alu_top_L.step` | True | 1 | 1 | True | clean | 541 cylinder, 496 plane | 132.76 × 98.95 × 9.9 | 0.6 … 10.5 | 30100.9 |
| `TOTEM_alu_bottom_L.step` | True | 1 | 1 | True | clean | 119 cylinder, 68 plane | 132.76 × 98.95 × 12.0 | -11.4 … 0.6 | 78546.0 |
| `TOTEM_wood_window_insert_L.step` | True | 1 | 1 | True | clean | 8 cylinder, 11 plane | 21.3 × 17.0 × 3.0 | 7.5 … 10.5 | 908.0 |
| `TOTEM_alu_top_R.step` | True | 1 | 1 | True | clean | 545 cylinder, 496 plane | 132.76 × 98.95 × 9.9 | 0.6 … 10.5 | 30098.7 |
| `TOTEM_alu_bottom_R.step` | True | 1 | 1 | True | clean | 123 cylinder, 68 plane | 132.76 × 98.95 × 12.0 | -11.4 … 0.6 | 78542.4 |
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

## Build

- L: start, board and part boxes 0.4 s, 2D design 7.0 s, solids 6.7 s, STEP write and read-back 1.3 s
- R: start, board and part boxes 0.4 s, 2D design 6.8 s, solids 6.9 s, STEP write and read-back 1.6 s

## Pictures

- `render3d_L.png`, `render3d_R.png`: each half: top from above and below, bottom from above and below
- `sections_L.png`: cross-sections through the left half (top, board and parts, bottom)
- `clearance_L.png`, `clearance_R.png`: gap from the board faces to the aluminum, seen from above
- `openings_L.png`: the USB-C, power-switch and reset openings in the back wall
