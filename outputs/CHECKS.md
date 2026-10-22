# Checks (measured on the final STEP files)

Distances are exact (OpenCASCADE BRepExtrema) between each case part and the KiCad board
(1.6 mm, true outline), every KiCad 3D part on that half, and every exposed copper pad.

| | Left | Right | Original (left) |
|---|---|---|---|
| Top to PCB (outside the 4 floating pads) | 0.52 mm | 0.52 mm | 0.10 mm |
| Bottom to PCB | 0.53 mm | 0.53 mm | 0.35 mm |
| Top to nearest part (switch bodies and diodes aside) | 0.50 mm | 0.50 mm |  |
| Top to diode epoxy (insulator) | 0.37 mm | 0.37 mm |  |
| Bottom to nearest part (sockets, contacts, pins) | 0.51 mm | 0.51 mm |  |
| Top to XIAO | 0.52 mm | 0.52 mm |  |
| Bottom to XIAO | 0.50 mm | 0.50 mm |  |
| Wood insert to XIAO | 1.57 mm | 1.57 mm |  |
| Top to exposed pads | 0.80 mm | 0.80 mm |  |
| Bottom to exposed pads | 0.51 mm | 0.51 mm |  |
| Top/bottom seam gap | 0.20 mm | 0.20 mm |  |

Reset switch: its metal body keeps 0.5 mm; its plastic plunger sits in the original round hole (plunger to top/bottom [0.2, 0.137] mm, as designed).

Top/bottom overlap: 0.0 / 0.0 mm³.
The top never touches the floating mounting pads either: it stays 0.1 mm above them, as in the original.

## Sizes

- L top: [133.11, 99.01, 12.0, 'z', -1.5, 10.5], valid/solids/volume [True, 1, 17425.2]
- L bottom: [133.08, 98.99, 15.39, 'z', -11.4, 3.99], valid/solids/volume [True, 1, 69724.0]
- L insert: [21.5, 17.0, 3.0, 'z', 7.5, 10.5], valid/solids/volume [True, 1, 916.8]
- R top: [133.1, 99.01, 12.0, 'z', -1.5, 10.5], valid/solids/volume [True, 1, 17430.0]
- R bottom: [133.09, 98.99, 15.39, 'z', -11.4, 3.99], valid/solids/volume [True, 1, 69709.0]
- R insert: [21.5, 17.0, 3.0, 'z', 7.5, 10.5], valid/solids/volume [True, 1, 919.2]

## Clean CAD rebuild

All four aluminum parts are rebuilt as clean CAD (`work/clean.py`): every face exactly horizontal or
vertical, outlines drawn with lines and true arcs, the screw holes as exact cylinders and 82° cones.
Each part is taken from the build as one column of metal per (x, y) between flat faces; the
hairline slivers and microscopic steps the build's mesh booleans left between near-identical walls
are merged into a neighbour (into the side with less metal where there is one), every boundary between
two regions is fitted once with lines and arcs (0.002 mm), and every region becomes one prism.

| Part | Faces | Arcs / lines in the outlines | Volume, build → clean (mm³) | STEP size |
|---|---|---|---|---|
| L top | 2636 | 689 / 1889 | 17435.4 → 17425.2 | 11 MB |
| L bottom | 3961 | 1072 / 2922 | 69741.1 → 69724.0 | 17 MB |
| R top | 2644 | 621 / 1967 | 17439.6 → 17430.0 | 11 MB |
| R bottom | 3624 | 995 / 2598 | 69729.9 → 69709.0 | 15 MB |

What the rebuild changed, part by part (all logged in `work/clean_*.log`):

- L top: opening through the part at (51.77, -69.27), 0.010 mm², closed; XIAO pocket widened to 0.52 mm all round (1.13 mm³); hairline specks on the outer faces removed (0.172 mm² in plan, up to 0.05 mm deep); corners the Ø2 mill cannot reach after the above filled as the mill leaves them (0.08 mm³).
- L bottom: 11 hairline horizontal cracks inside the part filled (largest 0.24 mm²); 0.55 mm floor at (130.36, -136.58), 0.79 mm², made 0.6 mm or more (pad underneath, -2.250 → -2.300); hairline specks on the outer faces removed (0.574 mm² in plan, up to 0.05 mm deep); corners the Ø2 mill cannot reach after the above filled as the mill leaves them (0.23 mm³).
- R top: XIAO pocket widened to 0.52 mm all round (1.12 mm³); hairline specks on the outer faces removed (0.167 mm² in plan, up to 0.05 mm deep); corners the Ø2 mill cannot reach after the above filled as the mill leaves them (0.05 mm³).
- R bottom: opening through the part at (286.45, -107.01), 0.653 mm², closed; 2 hairline horizontal cracks inside the part filled (largest 0.01 mm²); 0.55 mm floor at (177.45, -136.6), 0.98 mm², made 0.6 mm or more (pad underneath, -2.250 → -2.300); 0.46 mm floor at (285.68, -106.9), 3.30 mm², made 0.6 mm or more (floor raised, -3.200 → -2.554); hairline specks on the outer faces removed (0.999 mm² in plan, up to 0.05 mm deep); corners the Ø2 mill cannot reach after the above filled as the mill leaves them (0.10 mm³).

The published parts against the build's, column by column on a 0.05 mm grid (metal only in the
build's part = removed, only in the published part = added; spots over 0.05 mm³). The screw holes
show up because they are now the exact Ø2.0 / 82° / Ø4.3 (bottom) and Ø3.2 (top) holes of the original
CAD, where the site's mesh had them faceted; strips one grid cell wide along the outer faces are
walls that moved by a few microns across a grid line:

```
top L: volume old 17435.41 new 17425.24
top L: removed: 11.952 mm^3 in total (columns differing by more than 0.005 mm); 3 spots over 0.05 mm^3
top L:      1.870 mm^3,  1.638 mm^2, up to 5.865 mm deep, at (  50.95,  -68.63) 7.80 x 1.40
top L:      0.473 mm^3, 22.525 mm^2, up to 2.820 mm deep, at (  29.53,  -59.61) 1.45 x 18.85
top L:      0.069 mm^3,  0.010 mm^2, up to 6.850 mm deep, at (  53.96,  -53.44) 0.05 x 0.20
top L: added: 1.172 mm^3 in total (columns differing by more than 0.005 mm); 0 spots over 0.05 mm^3
bottom L: volume old 69741.12 new 69724.21
bottom L: removed: 17.157 mm^3 in total (columns differing by more than 0.005 mm); 34 spots over 0.05 mm^3
bottom L:      2.014 mm^3,  7.812 mm^2, up to 9.430 mm deep, at (  56.97,  -52.74) 4.30 x 4.30
bottom L:      1.161 mm^3,  6.625 mm^2, up to 9.420 mm deep, at ( 139.57, -111.95) 4.20 x 4.30
bottom L:      0.945 mm^3,  7.043 mm^2, up to 5.317 mm deep, at ( 131.25,  -52.75) 4.30 x 4.25
bottom L:      0.888 mm^3,  6.198 mm^2, up to 9.422 mm deep, at (  34.20, -121.01) 4.20 x 4.30
bottom L:      0.849 mm^3,  0.228 mm^2, up to 9.700 mm deep, at ( 117.98, -131.29) 3.70 x 1.15
bottom L:      0.542 mm^3,  0.088 mm^2, up to 6.200 mm deep, at (  76.02,  -94.78) 0.10 x 1.35
bottom L:      0.458 mm^3,  0.080 mm^2, up to 9.295 mm deep, at (  99.68, -128.11) 1.60 x 0.05
bottom L:      0.321 mm^3,  0.325 mm^2, up to 9.427 mm deep, at (  35.12, -119.24) 1.20 x 0.70
bottom L:      0.301 mm^3,  0.060 mm^2, up to 9.700 mm deep, at ( 124.15, -133.51) 0.65 x 0.30
bottom L:      0.226 mm^3,  0.208 mm^2, up to 9.422 mm deep, at ( 138.39, -113.68) 0.85 x 0.65
bottom L:      0.164 mm^3,  0.090 mm^2, up to 9.408 mm deep, at (  32.23, -120.96) 0.20 x 0.85
bottom L:      0.164 mm^3,  0.045 mm^2, up to 9.432 mm deep, at (  33.37, -119.16) 0.35 x 0.25
bottom L:      0.149 mm^3,  0.018 mm^2, up to 9.200 mm deep, at ( 122.36, -132.76) 0.35 x 0.15
bottom L:      0.144 mm^3,  0.018 mm^2, up to 9.200 mm deep, at ( 121.96, -132.61) 0.35 x 0.15
bottom L:      0.142 mm^3,  0.113 mm^2, up to 9.406 mm deep, at ( 137.45, -111.92) 0.25 x 0.85
bottom L:      0.137 mm^3,  0.018 mm^2, up to 9.200 mm deep, at ( 121.56, -132.46) 0.35 x 0.15
bottom L:      0.133 mm^3,  0.033 mm^2, up to 4.100 mm deep, at (  96.21,  -95.66) 0.65 x 0.05
bottom L:      0.126 mm^3,  0.278 mm^2, up to 9.407 mm deep, at ( 139.83, -113.90) 0.75 x 0.55
bottom L:      0.116 mm^3,  0.020 mm^2, up to 9.300 mm deep, at ( 101.88, -128.16) 0.40 x 0.05
bottom L:      0.111 mm^3,  0.203 mm^2, up to 9.414 mm deep, at ( 141.31, -112.70) 0.55 x 0.60
bottom L: added: 1.437 mm^3 in total (columns differing by more than 0.005 mm); 6 spots over 0.05 mm^3
bottom L:      0.206 mm^3,  0.023 mm^2, up to 9.150 mm deep, at (  72.66,  -47.66) 0.45 x 0.05
bottom L:      0.136 mm^3,  0.023 mm^2, up to 6.255 mm deep, at ( 128.41,  -47.66) 0.45 x 0.05
bottom L:      0.103 mm^3,  0.025 mm^2, up to 4.100 mm deep, at ( 141.86,  -47.76) 0.20 x 0.20
bottom L:      0.074 mm^3,  0.115 mm^2, up to 0.646 mm deep, at ( 107.33,  -95.66) 2.30 x 0.05
bottom L:      0.063 mm^3,  0.548 mm^2, up to 4.795 mm deep, at ( 132.99, -138.10) 5.45 x 3.20
bottom L:      0.056 mm^3,  0.010 mm^2, up to 5.600 mm deep, at ( 140.08,  -47.71) 0.20 x 0.05
top R: volume old 17439.98 new 17430.04
top R: removed: 9.768 mm^3 in total (columns differing by more than 0.005 mm); 5 spots over 0.05 mm^3
top R:      1.826 mm^3,  1.618 mm^2, up to 5.865 mm deep, at ( 256.99,  -68.64) 7.65 x 1.35
top R:      0.485 mm^3, 23.538 mm^2, up to 0.300 mm deep, at ( 278.37,  -59.61) 1.50 x 18.85
top R:      0.051 mm^3,  0.008 mm^2, up to 6.850 mm deep, at ( 269.05, -118.66) 0.15 x 0.05
top R:      0.051 mm^3,  0.008 mm^2, up to 6.850 mm deep, at ( 214.51,  -97.53) 0.10 x 0.10
top R:      0.051 mm^3,  0.008 mm^2, up to 6.850 mm deep, at ( 254.35,  -54.21) 0.15 x 0.15
top R: added: 1.726 mm^3 in total (columns differing by more than 0.005 mm); 1 spots over 0.05 mm^3
top R:      0.091 mm^3,  0.020 mm^2, up to 5.150 mm deep, at ( 207.97, -128.11) 0.40 x 0.05
bottom R: volume old 69729.95 new 69709.17
bottom R: removed: 19.806 mm^3 in total (columns differing by more than 0.005 mm); 27 spots over 0.05 mm^3
bottom R:      4.981 mm^3,  0.378 mm^2, up to 13.195 mm deep, at ( 279.20,  -59.61) 0.05 x 7.55
bottom R:      1.398 mm^3,  7.095 mm^2, up to 9.416 mm deep, at ( 273.59, -120.97) 4.30 x 4.30
bottom R:      1.397 mm^3,  7.085 mm^2, up to 9.416 mm deep, at ( 168.38, -111.98) 4.30 x 4.30
bottom R:      1.393 mm^3,  7.045 mm^2, up to 9.416 mm deep, at ( 250.88,  -52.68) 4.30 x 4.30
bottom R:      0.700 mm^3,  0.198 mm^2, up to 9.700 mm deep, at ( 189.65, -131.36) 3.20 x 1.00
bottom R:      0.546 mm^3,  4.828 mm^2, up to 5.319 mm deep, at ( 177.11,  -52.75) 4.20 x 4.30
bottom R:      0.383 mm^3,  0.068 mm^2, up to 7.200 mm deep, at ( 208.30, -128.11) 1.35 x 0.05
bottom R:      0.325 mm^3,  0.085 mm^2, up to 5.450 mm deep, at ( 170.11,  -47.74) 1.40 x 0.20
bottom R:      0.271 mm^3,  0.038 mm^2, up to 9.200 mm deep, at ( 185.85, -132.64) 0.75 x 0.30
bottom R:      0.223 mm^3,  0.043 mm^2, up to 5.250 mm deep, at ( 173.30,  -47.71) 0.85 x 0.05
bottom R:      0.147 mm^3,  0.050 mm^2, up to 3.010 mm deep, at ( 164.88,  -48.89) 0.10 x 0.55
bottom R:      0.124 mm^3,  0.018 mm^2, up to 9.200 mm deep, at ( 186.45, -132.41) 0.35 x 0.15
bottom R:      0.119 mm^3,  0.018 mm^2, up to 9.200 mm deep, at ( 186.85, -132.26) 0.35 x 0.15
bottom R:      0.116 mm^3,  0.020 mm^2, up to 9.300 mm deep, at ( 205.98, -128.16) 0.40 x 0.05
bottom R:      0.098 mm^3,  0.010 mm^2, up to 13.195 mm deep, at ( 277.78,  -47.69) 0.10 x 0.10
bottom R:      0.093 mm^3,  0.010 mm^2, up to 9.400 mm deep, at ( 207.48, -128.11) 0.20 x 0.05
bottom R:      0.088 mm^3,  0.010 mm^2, up to 9.200 mm deep, at ( 185.18, -132.89) 0.20 x 0.10
bottom R:      0.076 mm^3,  0.130 mm^2, up to 9.407 mm deep, at ( 274.75, -122.73) 0.75 x 0.55
bottom R:      0.076 mm^3,  0.130 mm^2, up to 9.407 mm deep, at ( 252.05,  -54.43) 0.75 x 0.55
bottom R:      0.076 mm^3,  0.130 mm^2, up to 9.407 mm deep, at ( 169.55, -113.73) 0.75 x 0.55
bottom R: added: 4.648 mm^3 in total (columns differing by more than 0.005 mm); 4 spots over 0.05 mm^3
bottom R:      2.643 mm^3,  4.100 mm^2, up to 0.646 mm deep, at ( 285.74, -106.71) 1.90 x 4.05
bottom R:      0.944 mm^3,  0.100 mm^2, up to 9.700 mm deep, at ( 209.43,  -47.66) 2.00 x 0.05
bottom R:      0.140 mm^3,  0.013 mm^2, up to 14.998 mm deep, at ( 165.70,  -47.66) 0.25 x 0.05
bottom R:      0.138 mm^3,  0.023 mm^2, up to 6.255 mm deep, at ( 179.45,  -47.66) 0.45 x 0.05
```

## Solid checks

```
TOTEM_alu_top_L valid True solids 1 shells 1 closed True analyzer: {}
TOTEM_alu_top_R valid True solids 1 shells 1 closed True analyzer: {}
TOTEM_alu_bottom_L valid True solids 1 shells 1 closed True analyzer: {}
TOTEM_alu_bottom_R valid True solids 1 shells 1 closed True analyzer: {}
TOTEM_wood_window_insert_L valid True solids 1 shells 1 closed True analyzer: {}
TOTEM_wood_window_insert_R valid True solids 1 shells 1 closed True analyzer: {}
```

`InvalidCurveOnSurface` is a tolerance note normal after a STEP round trip.

## Holes through the bottom

Every vertical line through each bottom was ray-cast (0.25 mm grid). The only openings through
the part are the screw holes; no socket pocket breaks through into the leg recesses any more
(see `underside_holes.png`):

```
new L through-openings: 4
  ( 131.19,  -52.66)  2.00x 2.00 area   3.1  underside around: -1.46..-0.69
  (  56.99,  -52.69)  2.00x 2.00 area   3.2  underside around: -1.47..-0.68
  ( 139.50, -112.00)  2.00x 1.75 area   3.0  underside around: -1.43..-0.68
  (  34.29, -121.02)  2.00x 2.00 area   2.9  underside around: -1.40..-0.69
new R through-openings: 4
  ( 176.78,  -52.68)  2.00x 2.00 area   3.2  underside around: -1.48..-0.73
  ( 250.98,  -52.69)  2.00x 2.00 area   3.1  underside around: -1.42..-0.68
  ( 168.48, -112.02)  2.00x 2.00 area   2.9  underside around: -1.38..-0.68
  ( 273.64, -121.02)  2.00x 2.00 area   3.1  underside around: -1.41..-0.68
```

## Thin walls compared with the original

- L top: (87.1,-96.8) 0.52 mm (new); (93.2,-98.1) 0.52 mm (new); (49.4,-69.9) 0.52 mm (new)
- L bottom: (133.1,-138.2) 0.60 mm (new)
- R top: (221.0,-96.8) 0.52 mm (new); (214.8,-98.0) 0.52 mm (new); (258.5,-69.9) 0.52 mm (new)
- R bottom: (174.8,-138.1) 0.60 mm (new); (180.0,-135.2) 0.60 mm (new)

## 3-axis machining with a Ø2 mm flat end mill

Every part was projected on a 0.05 mm grid from above and from below (two setups), using exact
triangles for planar faces and closed tessellation for curved faces, with balanced crossings.
On each side the
surface a Ø2 mm flat end mill leaves is the grey-level closing of the part's height map by a 1 mm
disc; any spot where the part lies deeper than that (material the mill can't remove: a slot
narrower than 2 mm, an inside corner sharper than R1, a pocket hidden under an overhang) is
counted if it is more than 0.03 mm deep. The screw holes are drilled (Ø2.0 necks) and not counted. Tilted faces outside the countersinks are reported separately;
they must be horizontal or vertical for a strict 2.5D result. Pictures: `work/mach_*.png`.

```
../outputs/TOTEM_alu_top_L.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, sloped faces outside the countersinks: 0.00 mm²
../outputs/TOTEM_alu_bottom_L.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, sloped faces outside the countersinks: 0.00 mm²
../outputs/TOTEM_wood_window_insert_L.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, sloped faces outside the countersinks: 0.00 mm²
../outputs/TOTEM_alu_top_R.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, sloped faces outside the countersinks: 0.00 mm²
../outputs/TOTEM_alu_bottom_R.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, sloped faces outside the countersinks: 0.00 mm²
../outputs/TOTEM_wood_window_insert_R.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, sloped faces outside the countersinks: 0.00 mm²
```

Measured fit after machining (smallest vertical gap between the top's underside
and the bottom's top face, each as the Ø2 mm end mill leaves it):

```
L: smallest vertical gap top/bottom: as modelled 0.20 mm, both parts as a Ø2 mm end mill leaves them 0.20 mm
R: smallest vertical gap top/bottom: as modelled 0.20 mm, both parts as a Ø2 mm end mill leaves them 0.20 mm
```

Parts that must still fit where no keep-out applies (overlap volume, new / original):

- L switch bodies in the top, new / original (mm^3): [0.0, 0.0]
- L battery in the bottom, new / original (mm^3): [0.0, 0.0]
- R switch bodies in the top, new / original (mm^3): [0.0, 0.0]
- R battery in the bottom, new / original (mm^3): [0.0, 0.0]

## Pictures

- `heightmap_L.png`, `heightmap_R.png`: gap from the PCB faces, before and after
- `render3d_L.png`, `render3d_R.png`: the new parts
- `sections_L.png`: cross-sections through the assembly
- `reset_back.png`: back face around the reset button, original vs new (unchanged)
- `underside_holes.png`: the bottoms seen from below, site original vs now (holes through the part)
