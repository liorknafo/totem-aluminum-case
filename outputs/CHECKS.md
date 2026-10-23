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
| Bottom to XIAO | 0.57 mm | 0.56 mm |  |
| Wood insert to XIAO | 1.57 mm | 1.57 mm |  |
| Top to exposed pads | 0.80 mm | 0.80 mm |  |
| Bottom to exposed pads | 0.51 mm | 0.51 mm |  |
| Top/bottom seam gap | 0.20 mm | 0.20 mm |  |

Reset switch: its metal body keeps 0.5 mm; its plastic plunger sits in the original round hole (plunger to top/bottom [0.2, 0.137] mm, as designed).

Top/bottom overlap: 0.0 / 0.0 mm³.
The top never touches the floating mounting pads either: it stays 0.1 mm above them, as in the original.

## Sizes

- L top: [133.11, 99.01, 12.0, 'z', -1.5, 10.5], valid/solids/volume [True, 1, 17631.8]
- L bottom: [133.08, 98.99, 15.39, 'z', -11.4, 3.99], valid/solids/volume [True, 1, 69760.7]
- L insert: [21.5, 17.0, 3.0, 'z', 7.5, 10.5], valid/solids/volume [True, 1, 916.8]
- R top: [133.1, 99.01, 12.0, 'z', -1.5, 10.5], valid/solids/volume [True, 1, 17619.1]
- R bottom: [133.09, 98.99, 15.39, 'z', -11.4, 3.99], valid/solids/volume [True, 1, 69749.4]
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
| L top | 2991 | 807 / 2326 | 17435.4 → 17631.8 | 12 MB |
| L bottom | 3941 | 1069 / 2942 | 69741.1 → 69760.7 | 17 MB |
| R top | 3181 | 711 / 2557 | 17439.6 → 17619.2 | 13 MB |
| R bottom | 3624 | 1000 / 2586 | 69729.9 → 69749.4 | 15 MB |

What the rebuild changed, part by part (all logged in `work/clean_*.log`):

- L top: opening through the part at (51.77, -69.27), 0.010 mm², closed; keycap-well floor at (127.24, -56.72) over a diode-pocket end raised 3.650 → 4.150 (3.63 mm² ledge; the plate there was 0.45–0.52 mm, now 1.0 mm or more); keycap-well floor at (120.24, -56.72) over a diode-pocket end raised 3.650 → 4.150 (3.63 mm² ledge; the plate there was 0.45–0.52 mm, now 1.0 mm or more); keycap-well floor at (91.26, -97.42) over a diode-pocket end raised 3.650 → 4.150 (24.51 mm² ledge; the plate there was 0.45–0.52 mm, now 1.0 mm or more); keycap-well floor at (49.08, -70.47) over a diode-pocket end raised 3.650 → 4.150 (8.57 mm² ledge; the plate there was 0.45–0.52 mm, now 1.0 mm or more); keycap-well floor at (33.92, -100.11) over a diode-pocket end raised 3.650 → 4.200 (13.13 mm² ledge; the plate there was 0.45–0.52 mm, now 1.0 mm or more); walls under 0.8 mm beside the keycap wells thickened into the wells, 0.3 mm clear of the keycaps and switch housings (163.087 mm³); the 0.14 mm wall in front of the XIAO's USB end opened (3.01 mm³); XIAO pocket widened to 0.52 mm all round (1.13 mm³); hairline specks on the outer faces removed (0.172 mm² in plan, up to 0.05 mm deep); corners the Ø2 mill cannot reach after the above filled as the mill leaves them (1.22 mm³).
- L bottom: 11 hairline horizontal cracks inside the part filled (largest 0.24 mm²); 0.55 mm floor at (130.36, -136.58), 0.79 mm², made 0.6 mm or more (pad underneath, -2.250 → -2.505); 0.78 mm floor at (18.57, -101.83), 0.46 mm², made 0.6 mm or more (pad underneath, -2.482 → -2.505); the 0.14 mm wall in front of the XIAO's USB end opened (5.06 mm³); hairline specks on the outer faces removed (0.574 mm² in plan, up to 0.05 mm deep); corners the Ø2 mill cannot reach after the above filled as the mill leaves them (1.13 mm³).
- R top: keycap-well floor at (274.02, -100.14) over a diode-pocket end raised 3.650 → 4.200 (12.67 mm² ledge; the plate there was 0.45–0.52 mm, now 1.0 mm or more); keycap-well floor at (258.85, -70.48) over a diode-pocket end raised 3.650 → 4.150 (8.33 mm² ledge; the plate there was 0.45–0.52 mm, now 1.0 mm or more); keycap-well floor at (216.81, -97.34) over a diode-pocket end raised 3.650 → 4.150 (23.80 mm² ledge; the plate there was 0.45–0.52 mm, now 1.0 mm or more); keycap-well floor at (189.16, -56.73) over a diode-pocket end raised 3.650 → 4.150 (3.74 mm² ledge; the plate there was 0.45–0.52 mm, now 1.0 mm or more); keycap-well floor at (182.16, -56.73) over a diode-pocket end raised 3.650 → 4.150 (3.74 mm² ledge; the plate there was 0.45–0.52 mm, now 1.0 mm or more); walls under 0.8 mm beside the keycap wells thickened into the wells, 0.3 mm clear of the keycaps and switch housings (141.602 mm³); the 0.14 mm wall in front of the XIAO's USB end opened (1.63 mm³); XIAO pocket widened to 0.52 mm all round (1.12 mm³); hairline specks on the outer faces removed (0.167 mm² in plan, up to 0.05 mm deep); corners the Ø2 mill cannot reach after the above filled as the mill leaves them (1.09 mm³).
- R bottom: opening through the part at (286.45, -107.01), 0.653 mm², closed; 2 hairline horizontal cracks inside the part filled (largest 0.01 mm²); 0.55 mm floor at (177.45, -136.6), 0.98 mm², made 0.6 mm or more (pad underneath, -2.250 → -2.505); 0.46 mm floor at (285.68, -106.9), 3.30 mm², made 0.6 mm or more (floor raised, -3.200 → -2.554); 0.65 mm floor at (286.62, -106.97), 3.67 mm², made 0.6 mm or more (pad underneath, -3.200 → -3.354); 0.74 mm floor at (289.28, -101.87), 0.47 mm², made 0.6 mm or more (pad underneath, -2.436 → -2.505); the 0.14 mm wall in front of the XIAO's USB end opened (1.87 mm³); hairline specks on the outer faces removed (0.999 mm² in plan, up to 0.05 mm deep); corners the Ø2 mill cannot reach after the above filled as the mill leaves them (1.01 mm³).

The published parts against the build's, column by column on a 0.05 mm grid (metal only in the
build's part = removed, only in the published part = added; spots over 0.05 mm³). The screw holes
show up because they are now the exact Ø2.0 / 82° / Ø4.3 (bottom) and Ø3.2 (top) holes of the original
CAD, where the site's mesh had them faceted; strips one grid cell wide along the outer faces are
walls that moved by a few microns across a grid line:

```
top L: volume old 17435.41 new 17632.03
top L: removed: 14.517 mm^3 in total (columns differing by more than 0.005 mm); 3 spots over 0.05 mm^3
top L:      3.276 mm^3, 24.515 mm^2, up to 2.820 mm deep, at (  29.46,  -59.61) 1.50 x 20.05
top L:      1.870 mm^3,  1.633 mm^2, up to 5.865 mm deep, at (  50.95,  -68.63) 7.80 x 1.40
top L:      0.069 mm^3,  0.010 mm^2, up to 6.850 mm deep, at (  53.96,  -53.44) 0.05 x 0.20
top L: added: 214.053 mm^3 in total (columns differing by more than 0.005 mm); 11 spots over 0.05 mm^3
top L:     60.424 mm^3, 11.343 mm^2, up to 6.850 mm deep, at ( 123.37,  -56.65) 12.45 x 1.35
top L:     37.372 mm^3, 10.295 mm^2, up to 8.350 mm deep, at (  49.62,  -70.33) 8.75 x 2.50
top L:     27.725 mm^3,  4.048 mm^2, up to 6.850 mm deep, at (  67.57,  -55.36) 5.85 x 1.20
top L:     25.951 mm^3, 15.123 mm^2, up to 6.850 mm deep, at (  34.44,  -99.71) 9.95 x 4.80
top L:     16.269 mm^3,  2.375 mm^2, up to 6.850 mm deep, at (  60.63, -119.79) 1.65 x 3.35
top L:     12.998 mm^3,  1.898 mm^2, up to 6.850 mm deep, at ( 144.95, -120.70) 2.30 x 1.85
top L:     12.575 mm^3, 25.140 mm^2, up to 1.485 mm deep, at (  91.47,  -97.59) 11.80 x 7.35
top L:      4.921 mm^3,  4.940 mm^2, up to 1.000 mm deep, at (  57.00,  -52.69) 3.20 x 3.25
top L:      4.921 mm^3,  4.940 mm^2, up to 1.000 mm deep, at ( 131.20,  -52.69) 3.20 x 3.25
top L:      4.905 mm^3,  4.905 mm^2, up to 1.000 mm deep, at ( 139.50, -112.00) 3.20 x 3.20
top L:      4.893 mm^3,  4.893 mm^2, up to 1.000 mm deep, at (  34.30, -121.02) 3.20 x 3.20
bottom L: volume old 69741.12 new 69760.83
bottom L: removed: 20.181 mm^3 in total (columns differing by more than 0.005 mm); 42 spots over 0.05 mm^3
bottom L:      4.108 mm^3,  2.405 mm^2, up to 2.910 mm deep, at (  28.70,  -59.59) 0.15 x 16.20
bottom L:      0.849 mm^3,  0.228 mm^2, up to 9.700 mm deep, at ( 117.98, -131.29) 3.70 x 1.15
bottom L:      0.542 mm^3,  0.088 mm^2, up to 6.200 mm deep, at (  76.02,  -94.78) 0.10 x 1.35
bottom L:      0.458 mm^3,  0.080 mm^2, up to 9.295 mm deep, at (  99.68, -128.11) 1.60 x 0.05
bottom L:      0.306 mm^3,  0.105 mm^2, up to 2.910 mm deep, at (  28.82,  -69.17) 0.45 x 0.65
bottom L:      0.301 mm^3,  0.060 mm^2, up to 9.700 mm deep, at ( 124.15, -133.51) 0.65 x 0.30
bottom L:      0.262 mm^3,  0.090 mm^2, up to 2.910 mm deep, at (  28.69,  -50.00) 0.15 x 0.80
bottom L:      0.213 mm^3,  0.025 mm^2, up to 8.517 mm deep, at ( 139.48, -109.86) 0.50 x 0.05
bottom L:      0.169 mm^3,  0.023 mm^2, up to 8.523 mm deep, at (  55.51,  -54.21) 0.45 x 0.45
bottom L:      0.149 mm^3,  0.018 mm^2, up to 9.200 mm deep, at ( 122.36, -132.76) 0.35 x 0.15
bottom L:      0.148 mm^3,  0.018 mm^2, up to 8.532 mm deep, at (  33.31, -119.13) 0.35 x 0.20
bottom L:      0.144 mm^3,  0.018 mm^2, up to 9.200 mm deep, at ( 121.96, -132.61) 0.35 x 0.15
bottom L:      0.137 mm^3,  0.018 mm^2, up to 9.200 mm deep, at ( 121.56, -132.46) 0.35 x 0.15
bottom L:      0.133 mm^3,  0.033 mm^2, up to 4.100 mm deep, at (  96.21,  -95.66) 0.65 x 0.05
bottom L:      0.128 mm^3,  0.015 mm^2, up to 8.506 mm deep, at ( 137.36, -111.99) 0.05 x 0.30
bottom L:      0.128 mm^3,  0.015 mm^2, up to 8.506 mm deep, at (  54.86,  -52.69) 0.05 x 0.30
bottom L:      0.116 mm^3,  0.020 mm^2, up to 9.300 mm deep, at ( 101.88, -128.16) 0.40 x 0.05
bottom L:      0.110 mm^3,  0.025 mm^2, up to 4.417 mm deep, at ( 131.18,  -50.56) 0.50 x 0.05
bottom L:      0.106 mm^3,  0.013 mm^2, up to 8.527 mm deep, at (  35.26, -119.10) 0.25 x 0.15
bottom L:      0.106 mm^3,  0.013 mm^2, up to 8.506 mm deep, at (  32.16, -121.01) 0.05 x 0.25
bottom L: added: 40.966 mm^3 in total (columns differing by more than 0.005 mm); 10 spots over 0.05 mm^3
bottom L:      9.905 mm^3, 11.148 mm^2, up to 1.049 mm deep, at ( 131.20,  -52.70) 4.25 x 4.25
bottom L:      9.892 mm^3, 11.148 mm^2, up to 1.038 mm deep, at (  34.30, -121.02) 4.25 x 4.25
bottom L:      9.872 mm^3, 11.143 mm^2, up to 1.031 mm deep, at ( 139.50, -112.00) 4.25 x 4.25
bottom L:      9.848 mm^3, 11.130 mm^2, up to 1.049 mm deep, at (  57.01,  -52.70) 4.25 x 4.30
bottom L:      0.206 mm^3,  0.023 mm^2, up to 9.150 mm deep, at (  72.66,  -47.66) 0.45 x 0.05
bottom L:      0.174 mm^3,  0.548 mm^2, up to 4.795 mm deep, at ( 132.99, -138.10) 5.45 x 3.20
bottom L:      0.136 mm^3,  0.023 mm^2, up to 6.255 mm deep, at ( 128.41,  -47.66) 0.45 x 0.05
bottom L:      0.103 mm^3,  0.025 mm^2, up to 4.100 mm deep, at ( 141.86,  -47.76) 0.20 x 0.20
bottom L:      0.074 mm^3,  0.115 mm^2, up to 0.646 mm deep, at ( 107.33,  -95.66) 2.30 x 0.05
bottom L:      0.056 mm^3,  0.010 mm^2, up to 5.600 mm deep, at ( 140.08,  -47.71) 0.20 x 0.05
top R: volume old 17439.98 new 17619.21
top R: removed: 10.703 mm^3 in total (columns differing by more than 0.005 mm); 7 spots over 0.05 mm^3
top R:      1.899 mm^3, 24.535 mm^2, up to 2.055 mm deep, at ( 278.39,  -59.61) 1.50 x 20.05
top R:      1.826 mm^3,  1.618 mm^2, up to 5.865 mm deep, at ( 256.99,  -68.64) 7.65 x 1.35
top R:      0.073 mm^3,  0.020 mm^2, up to 3.650 mm deep, at ( 163.93, -119.84) 0.25 x 0.40
top R:      0.052 mm^3,  0.020 mm^2, up to 5.350 mm deep, at ( 164.11,  -49.94) 0.10 x 0.35
top R:      0.051 mm^3,  0.008 mm^2, up to 6.850 mm deep, at ( 269.05, -118.66) 0.15 x 0.05
top R:      0.051 mm^3,  0.008 mm^2, up to 6.850 mm deep, at ( 229.50,  -99.96) 0.05 x 0.15
top R:      0.051 mm^3,  0.008 mm^2, up to 6.850 mm deep, at ( 254.35,  -54.21) 0.15 x 0.15
top R: added: 192.253 mm^3 in total (columns differing by more than 0.005 mm); 12 spots over 0.05 mm^3
top R:     60.424 mm^3, 11.405 mm^2, up to 6.850 mm deep, at ( 185.33,  -56.66) 12.40 x 1.35
top R:     36.162 mm^3, 10.062 mm^2, up to 6.850 mm deep, at ( 258.31,  -70.34) 8.70 x 2.50
top R:     26.235 mm^3,  3.830 mm^2, up to 6.850 mm deep, at ( 240.36,  -55.37) 5.50 x 1.15
top R:     15.960 mm^3,  2.330 mm^2, up to 6.850 mm deep, at ( 247.15, -119.81) 1.60 x 3.20
top R:     13.067 mm^3,  1.905 mm^2, up to 10.500 mm deep, at ( 162.92, -120.70) 2.30 x 1.85
top R:     12.241 mm^3, 24.478 mm^2, up to 1.485 mm deep, at ( 216.52,  -97.55) 11.90 x 7.15
top R:      7.026 mm^3, 12.770 mm^2, up to 0.985 mm deep, at ( 274.02,  -99.97) 9.15 x 3.25
top R:      4.934 mm^3,  4.958 mm^2, up to 1.000 mm deep, at ( 176.76,  -52.68) 3.20 x 3.30
top R:      4.932 mm^3,  4.953 mm^2, up to 1.000 mm deep, at ( 250.96,  -52.69) 3.20 x 3.30
top R:      4.915 mm^3,  4.915 mm^2, up to 1.000 mm deep, at ( 273.66, -121.00) 3.20 x 3.20
top R:      4.915 mm^3,  4.915 mm^2, up to 1.000 mm deep, at ( 168.46, -112.00) 3.20 x 3.20
top R:      0.066 mm^3,  0.015 mm^2, up to 5.150 mm deep, at ( 207.92, -128.11) 0.30 x 0.05
bottom R: volume old 69729.95 new 69749.57
bottom R: removed: 19.923 mm^3 in total (columns differing by more than 0.005 mm); 36 spots over 0.05 mm^3
bottom R:      5.970 mm^3,  0.795 mm^2, up to 13.195 mm deep, at ( 279.20,  -59.59) 0.05 x 15.90
bottom R:      0.700 mm^3,  0.198 mm^2, up to 9.700 mm deep, at ( 189.65, -131.36) 3.20 x 1.00
bottom R:      0.383 mm^3,  0.068 mm^2, up to 7.200 mm deep, at ( 208.30, -128.11) 1.35 x 0.05
bottom R:      0.325 mm^3,  0.085 mm^2, up to 5.450 mm deep, at ( 170.11,  -47.74) 1.40 x 0.20
bottom R:      0.271 mm^3,  0.038 mm^2, up to 9.200 mm deep, at ( 185.85, -132.64) 0.75 x 0.30
bottom R:      0.223 mm^3,  0.043 mm^2, up to 5.250 mm deep, at ( 173.30,  -47.71) 0.85 x 0.05
bottom R:      0.196 mm^3,  0.068 mm^2, up to 2.910 mm deep, at ( 279.04,  -69.22) 0.45 x 0.50
bottom R:      0.149 mm^3,  0.018 mm^2, up to 8.509 mm deep, at ( 170.60, -112.01) 0.05 x 0.35
bottom R:      0.149 mm^3,  0.018 mm^2, up to 8.509 mm deep, at ( 253.10,  -52.71) 0.05 x 0.35
bottom R:      0.149 mm^3,  0.018 mm^2, up to 8.509 mm deep, at ( 275.80, -121.01) 0.05 x 0.35
bottom R:      0.147 mm^3,  0.050 mm^2, up to 3.010 mm deep, at ( 164.88,  -48.89) 0.10 x 0.55
bottom R:      0.130 mm^3,  0.245 mm^2, up to 2.910 mm deep, at ( 279.02,  -49.83) 0.55 x 0.80
bottom R:      0.127 mm^3,  0.015 mm^2, up to 8.510 mm deep, at ( 169.98, -110.49) 0.30 x 0.30
bottom R:      0.127 mm^3,  0.015 mm^2, up to 8.510 mm deep, at ( 275.18, -119.49) 0.30 x 0.30
bottom R:      0.127 mm^3,  0.015 mm^2, up to 8.510 mm deep, at ( 252.48,  -51.19) 0.30 x 0.30
bottom R:      0.124 mm^3,  0.018 mm^2, up to 9.200 mm deep, at ( 186.45, -132.41) 0.35 x 0.15
bottom R:      0.119 mm^3,  0.018 mm^2, up to 9.200 mm deep, at ( 186.85, -132.26) 0.35 x 0.15
bottom R:      0.116 mm^3,  0.020 mm^2, up to 9.300 mm deep, at ( 205.98, -128.16) 0.40 x 0.05
bottom R:      0.106 mm^3,  0.013 mm^2, up to 8.516 mm deep, at ( 273.80, -118.86) 0.25 x 0.05
bottom R:      0.106 mm^3,  0.013 mm^2, up to 8.516 mm deep, at ( 168.60, -109.86) 0.25 x 0.05
bottom R: added: 45.276 mm^3 in total (columns differing by more than 0.005 mm); 9 spots over 0.05 mm^3
bottom R:      9.984 mm^3, 11.213 mm^2, up to 1.051 mm deep, at ( 176.76,  -52.70) 4.25 x 4.30
bottom R:      9.967 mm^3, 11.213 mm^2, up to 0.985 mm deep, at ( 273.66, -121.00) 4.25 x 4.30
bottom R:      9.967 mm^3, 11.213 mm^2, up to 0.972 mm deep, at ( 168.46, -112.00) 4.25 x 4.30
bottom R:      9.967 mm^3, 11.213 mm^2, up to 1.029 mm deep, at ( 250.96,  -52.70) 4.25 x 4.30
bottom R:      3.238 mm^3,  7.317 mm^2, up to 0.800 mm deep, at ( 286.19, -106.45) 2.70 x 5.80
bottom R:      0.944 mm^3,  0.100 mm^2, up to 9.700 mm deep, at ( 209.43,  -47.66) 2.00 x 0.05
bottom R:      0.247 mm^3,  0.965 mm^2, up to 0.755 mm deep, at ( 177.21, -136.79) 10.15 x 5.65
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
  ( 131.19,  -52.66)  2.00x 2.00 area   3.1  underside around: -2.36..-1.59
  (  56.99,  -52.69)  2.00x 2.00 area   3.2  underside around: -2.37..-1.58
  ( 139.50, -112.00)  2.00x 1.75 area   3.0  underside around: -2.33..-1.58
  (  34.29, -121.02)  2.00x 2.00 area   2.9  underside around: -2.30..-1.59
new R through-openings: 4
  ( 176.78,  -52.68)  2.00x 2.00 area   3.2  underside around: -2.38..-1.63
  ( 250.98,  -52.69)  2.00x 2.00 area   3.1  underside around: -2.32..-1.58
  ( 168.48, -112.02)  2.00x 2.00 area   2.9  underside around: -2.28..-1.58
  ( 273.64, -121.02)  2.00x 2.00 area   3.1  underside around: -2.31..-1.58
```

## Thin walls compared with the original

- L top: no new or thinner spots (clusters of 5+ samples, 0.25 mm grid)
- L bottom: no new or thinner spots (clusters of 5+ samples, 0.25 mm grid)
- R top: no new or thinner spots (clusters of 5+ samples, 0.25 mm grid)
- R bottom: no new or thinner spots (clusters of 5+ samples, 0.25 mm grid)

## Walls thinner than 0.8 mm

Every band between the parts' flat faces, cut in plan: metal narrower than 0.8 mm (what an
opening by a 0.4 mm disc removes, less the bits it rounds off plain corners; width = twice the
largest distance to the outline). Thin layers in z (floors, roofs) are listed below from
`thin.py` (0.25 mm grid, all spots under 0.8 mm, screw-hole rings included):

```
../outputs/TOTEM_alu_top_L.step: 21 walls thinner than 0.8 mm
  0.12 mm at (  29.36, -47.91) z   3.100..  3.200,  0.008 mm^2 in plan, 0.13 x 0.16
  0.17 mm at (  86.36, -96.31) z   2.150..  2.450,  0.030 mm^2 in plan, 0.37 x 0.19
  0.17 mm at (  91.36, -96.31) z   2.150..  2.450,  0.030 mm^2 in plan, 0.37 x 0.19
  0.18 mm at (  87.78, -96.31) z   2.150..  2.450,  0.031 mm^2 in plan, 0.37 x 0.19
  0.23 mm at ( 128.01, -48.86) z   3.450..  4.150,  0.039 mm^2 in plan, 0.24 x 0.60
  0.30 mm at (  30.35, -47.81) z   2.350..  3.100,  0.110 mm^2 in plan, 0.61 x 0.33
  0.31 mm at (  34.15,-100.36) z   2.150..  2.450,  0.986 mm^2 in plan, 6.13 x 1.25
  0.31 mm at (  94.99, -99.08) z   2.150..  2.450,  0.276 mm^2 in plan, 0.33 x 1.41
  0.35 mm at (  83.87, -43.68) z  -1.500..  1.600,  0.308 mm^2 in plan, 1.34 x 0.36
  0.39 mm at (  27.84, -98.93) z  -1.500..  1.600,  0.185 mm^2 in plan, 0.71 x 0.53
  0.41 mm at ( 125.99, -47.95) z   4.150..  5.150,  0.835 mm^2 in plan, 2.87 x 0.59
  0.42 mm at ( 123.00, -47.95) z   4.150..  6.430,  3.595 mm^2 in plan, 9.13 x 0.59
  0.54 mm at (  65.15, -48.79) z   3.700..  5.150,  3.193 mm^2 in plan, 5.30 x 0.70
  0.55 mm at (  43.55, -48.86) z   1.650..  2.350, 13.314 mm^2 in plan, 27.27 x 0.61
  0.57 mm at (  34.08,-122.87) z   1.700..  2.150,  0.043 mm^2 in plan, 0.24 x 0.59
  0.59 mm at ( 137.56, -48.85) z   3.450..  4.150,  3.787 mm^2 in plan, 6.42 x 0.61
  0.60 mm at ( 148.66,-128.82) z  -1.500..  2.150,  0.146 mm^2 in plan, 0.70 x 0.61
  0.60 mm at ( 109.60, -48.99) z   3.450..  4.150, 10.094 mm^2 in plan, 16.89 x 0.60
  0.60 mm at ( 147.24,-131.25) z  -1.500..  2.150,  0.154 mm^2 in plan, 0.71 x 0.62
  0.73 mm at (  56.06, -50.98) z   1.700..  2.150,  0.397 mm^2 in plan, 2.04 x 0.88
  0.73 mm at ( 130.26, -50.97) z   1.700..  2.150,  0.399 mm^2 in plan, 2.04 x 0.89
../outputs/TOTEM_alu_bottom_L.step: 53 walls thinner than 0.8 mm
  0.07 mm at (  92.98,-101.08) z  -1.500.. -0.550,  0.006 mm^2 in plan, 0.09 x 0.16
  0.11 mm at (  65.39, -52.10) z  -1.500.. -0.550,  0.011 mm^2 in plan, 0.12 x 0.24
  0.11 mm at (  89.01, -97.98) z  -1.500.. -0.550,  0.066 mm^2 in plan, 0.79 x 0.38
  0.11 mm at ( 143.23, -49.40) z  -0.550.. -0.500,  0.010 mm^2 in plan, 0.12 x 0.18
  0.11 mm at (  71.18, -47.79) z  -0.400..  1.250,  0.038 mm^2 in plan, 0.43 x 0.26
  0.11 mm at (  65.09, -50.64) z  -1.500.. -0.550,  0.017 mm^2 in plan, 0.14 x 0.22
  0.12 mm at (  99.36, -47.90) z  -0.400..  3.250,  0.079 mm^2 in plan, 0.65 x 0.47
  0.13 mm at (  28.79, -71.16) z   2.660..  3.598,  0.073 mm^2 in plan, 0.36 x 0.48
  0.13 mm at (  95.13, -48.98) z  -2.554.. -1.700,  0.021 mm^2 in plan, 0.20 x 0.26
  0.15 mm at (  39.42, -62.26) z  -0.550.. -0.500,  0.073 mm^2 in plan, 0.74 x 0.18
  0.16 mm at (  51.31, -47.79) z   1.250..  1.750,  0.259 mm^2 in plan, 1.55 x 0.29
  0.16 mm at (  29.08, -69.26) z   1.085..  3.995,  0.025 mm^2 in plan, 0.26 x 0.26
  0.17 mm at (  37.49, -47.82) z   1.250..  1.950,  0.213 mm^2 in plan, 1.46 x 0.29
  0.18 mm at (  33.40, -47.84) z   1.250..  1.950,  0.508 mm^2 in plan, 2.68 x 0.35
  0.18 mm at (  54.05, -47.76) z   1.250..  1.750,  0.076 mm^2 in plan, 0.87 x 0.20
  0.22 mm at (  30.75, -49.07) z   1.950..  2.150,  0.033 mm^2 in plan, 0.25 x 0.29
  0.22 mm at (  40.30, -47.80) z   1.250..  1.750,  0.129 mm^2 in plan, 1.16 x 0.27
  0.23 mm at (  39.89, -69.76) z  -2.554.. -1.500,  0.033 mm^2 in plan, 0.27 x 0.23
  0.23 mm at (  57.67, -47.84) z   1.250..  1.950,  0.204 mm^2 in plan, 1.01 x 0.34
  0.24 mm at (  29.08, -49.31) z   2.660..  3.995,  1.072 mm^2 in plan, 1.49 x 1.74
  0.25 mm at ( 141.27, -48.06) z   3.050..  3.750,  1.037 mm^2 in plan, 4.14 x 0.80
  0.25 mm at (  60.01, -47.79) z   1.250..  1.950,  0.053 mm^2 in plan, 0.47 x 0.25
  0.28 mm at ( 100.46, -48.39) z   3.050..  3.750,  0.892 mm^2 in plan, 2.86 x 1.45
  0.32 mm at ( 112.95, -47.91) z   3.050..  3.750,  0.308 mm^2 in plan, 1.39 x 0.48
  0.32 mm at (  46.10, -47.86) z   1.250..  1.545,  0.430 mm^2 in plan, 2.04 x 0.40
  0.33 mm at (  83.87, -43.68) z  -2.554.. -1.700,  0.297 mm^2 in plan, 1.36 x 0.34
  0.35 mm at ( 104.47, -47.88) z   3.050..  3.750,  0.355 mm^2 in plan, 2.02 x 0.43
  0.37 mm at ( 110.13, -47.87) z   3.050..  3.750,  0.263 mm^2 in plan, 1.18 x 0.41
  0.38 mm at ( 107.43, -47.90) z   3.050..  3.750,  0.340 mm^2 in plan, 1.68 x 0.47
  0.38 mm at (  43.20, -47.87) z   1.250..  1.950,  0.240 mm^2 in plan, 1.16 x 0.41
  0.38 mm at (  27.84, -98.93) z  -2.554.. -1.700,  0.188 mm^2 in plan, 0.72 x 0.53
  0.39 mm at ( 123.02, -47.95) z  -1.500..  3.750,  7.817 mm^2 in plan, 18.37 x 0.58
  0.39 mm at (  39.86,-103.72) z  -3.200.. -2.554,  0.460 mm^2 in plan, 0.40 x 1.90
  0.42 mm at (  65.16, -48.71) z  -0.500..  0.635,  3.097 mm^2 in plan, 6.71 x 0.79
  0.42 mm at (  30.03, -49.70) z   2.660..  3.050,  0.137 mm^2 in plan, 0.34 x 0.75
  0.43 mm at ( 115.66, -47.88) z   3.050..  3.750,  0.396 mm^2 in plan, 1.38 x 0.48
  0.48 mm at (  39.88,-112.75) z  -2.554.. -0.550,  0.615 mm^2 in plan, 0.51 x 2.61
  0.55 mm at ( 132.32,-135.27) z  -1.700.. -0.550,  0.448 mm^2 in plan, 1.42 x 1.27
  0.55 mm at (  70.05, -48.53) z   0.635..  1.950,  1.132 mm^2 in plan, 1.77 x 1.18
  0.56 mm at ( 121.87, -55.69) z  -1.500.. -0.550,  0.412 mm^2 in plan, 1.14 x 0.60
  0.56 mm at ( 101.08,-108.52) z  -1.600.. -0.550,  0.476 mm^2 in plan, 1.70 x 0.60
  0.56 mm at ( 116.36,-128.55) z  -1.700.. -0.550,  0.520 mm^2 in plan, 1.78 x 1.09
  0.56 mm at (  98.23,-125.81) z  -1.700.. -0.550,  0.475 mm^2 in plan, 1.73 x 0.61
  0.56 mm at (  22.45,-111.95) z  -1.700.. -0.550,  0.476 mm^2 in plan, 0.61 x 1.67
  0.56 mm at (  76.15, -89.24) z  -2.554.. -0.550,  0.475 mm^2 in plan, 0.60 x 1.70
  0.56 mm at (  76.15, -72.24) z  -2.554.. -0.550,  0.475 mm^2 in plan, 0.60 x 1.69
  0.56 mm at ( 102.18,-104.68) z  -1.600.. -0.550,  0.475 mm^2 in plan, 1.70 x 0.60
  0.56 mm at ( 143.31,-134.12) z  -1.700.. -0.550,  0.476 mm^2 in plan, 1.31 x 1.47
  0.57 mm at ( 143.96,-122.14) z  -1.700.. -0.550,  0.649 mm^2 in plan, 1.80 x 1.85
  0.57 mm at ( 125.41,-125.85) z  -2.554.. -0.550,  0.222 mm^2 in plan, 0.75 x 0.73
  0.78 mm at ( 112.96, -97.54) z  -2.554.. -0.550,  9.008 mm^2 in plan, 5.13 x 11.52
  0.78 mm at ( 112.96, -80.54) z  -2.554.. -0.550,  9.013 mm^2 in plan, 5.13 x 11.52
  0.78 mm at ( 113.05, -63.31) z  -2.554.. -0.550,  9.015 mm^2 in plan, 5.13 x 11.52
../outputs/TOTEM_alu_top_R.step: 21 walls thinner than 0.8 mm
  0.08 mm at ( 277.77, -69.12) z   4.395..  6.430,  0.006 mm^2 in plan, 0.09 x 0.13
  0.09 mm at ( 278.50, -47.91) z   3.100..  3.200,  0.007 mm^2 in plan, 0.12 x 0.15
  0.17 mm at ( 221.70, -96.31) z   2.150..  2.450,  0.030 mm^2 in plan, 0.37 x 0.19
  0.17 mm at ( 216.70, -96.31) z   2.150..  2.450,  0.030 mm^2 in plan, 0.37 x 0.19
  0.17 mm at ( 220.26, -96.32) z   2.150..  2.450,  0.030 mm^2 in plan, 0.37 x 0.19
  0.23 mm at ( 179.95, -48.87) z   3.450..  4.150,  0.039 mm^2 in plan, 0.24 x 0.60
  0.29 mm at ( 277.52, -47.81) z   2.341..  3.100,  0.111 mm^2 in plan, 0.61 x 0.33
  0.33 mm at ( 273.73,-100.36) z   2.150..  2.450,  1.144 mm^2 in plan, 6.20 x 1.28
  0.34 mm at ( 221.45, -43.67) z  -1.500..  1.600,  0.301 mm^2 in plan, 1.35 x 0.35
  0.40 mm at ( 212.89, -98.97) z   2.150..  2.450,  0.345 mm^2 in plan, 0.42 x 1.14
  0.41 mm at ( 187.96, -47.95) z   4.150..  5.150,  0.830 mm^2 in plan, 2.87 x 0.59
  0.42 mm at ( 184.96, -47.95) z   4.150..  6.430,  3.596 mm^2 in plan, 9.13 x 0.59
  0.54 mm at ( 242.91, -48.79) z   3.700..  5.150,  3.193 mm^2 in plan, 5.30 x 0.70
  0.56 mm at ( 264.45, -48.86) z   1.650..  2.341, 13.271 mm^2 in plan, 27.07 x 0.61
  0.59 mm at ( 170.40, -48.86) z   3.450..  4.150,  3.788 mm^2 in plan, 6.42 x 0.61
  0.60 mm at ( 198.31, -48.99) z   3.450..  4.150, 10.037 mm^2 in plan, 16.80 x 0.60
  0.61 mm at ( 275.47,-121.38) z   1.700..  2.150,  0.428 mm^2 in plan, 0.85 x 1.17
  0.62 mm at ( 288.46,-105.96) z  -1.500..  2.150,  0.120 mm^2 in plan, 0.67 x 0.41
  0.62 mm at ( 287.97,-108.73) z  -1.500..  2.150,  0.119 mm^2 in plan, 0.67 x 0.41
  0.68 mm at ( 250.03, -50.96) z   1.700..  2.150,  0.383 mm^2 in plan, 2.03 x 0.87
  0.73 mm at ( 175.82, -50.98) z   1.700..  2.150,  0.399 mm^2 in plan, 2.04 x 0.89
../outputs/TOTEM_alu_bottom_R.step: 60 walls thinner than 0.8 mm
  0.07 mm at ( 242.87, -52.13) z  -1.500.. -0.550,  0.009 mm^2 in plan, 0.10 x 0.22
  0.07 mm at ( 243.15, -50.62) z  -1.500.. -0.550,  0.009 mm^2 in plan, 0.10 x 0.22
  0.07 mm at ( 279.13, -50.12) z   1.085..  2.140,  0.005 mm^2 in plan, 0.10 x 0.11
  0.07 mm at ( 278.70, -49.43) z   2.150..  3.947,  1.061 mm^2 in plan, 1.49 x 1.50
  0.08 mm at ( 277.86, -49.72) z   2.150..  3.050,  0.172 mm^2 in plan, 0.39 x 0.83
  0.08 mm at ( 237.10, -48.05) z   1.250..  1.545,  0.008 mm^2 in plan, 0.10 x 0.16
  0.09 mm at ( 278.39, -47.87) z   1.941..  2.140,  0.005 mm^2 in plan, 0.18 x 0.09
  0.09 mm at ( 278.39, -47.87) z   2.150..  2.610,  0.005 mm^2 in plan, 0.18 x 0.09
  0.10 mm at ( 208.73, -47.78) z  -0.400..  2.140,  0.013 mm^2 in plan, 0.39 x 0.21
  0.10 mm at ( 208.48, -47.93) z   2.150..  3.250,  0.082 mm^2 in plan, 0.67 x 0.48
  0.11 mm at ( 164.63, -49.40) z  -0.550.. -0.500,  0.010 mm^2 in plan, 0.12 x 0.17
  0.12 mm at ( 256.46, -47.85) z   1.250..  1.941,  0.400 mm^2 in plan, 2.51 x 0.36
  0.13 mm at ( 261.15, -47.75) z   1.250..  1.941,  0.074 mm^2 in plan, 0.88 x 0.17
  0.13 mm at ( 267.74, -56.92) z  -0.550.. -0.500,  0.056 mm^2 in plan, 0.63 x 0.16
  0.14 mm at ( 232.70, -48.98) z  -2.554.. -1.700,  0.024 mm^2 in plan, 0.21 x 0.26
  0.14 mm at ( 278.81, -69.29) z   2.150..  3.995,  0.020 mm^2 in plan, 0.24 x 0.23
  0.14 mm at ( 278.81, -69.29) z   1.085..  2.140,  0.020 mm^2 in plan, 0.24 x 0.23
  0.14 mm at ( 279.09, -71.13) z   2.660..  3.750,  0.097 mm^2 in plan, 0.47 x 0.57
  0.16 mm at ( 252.37, -47.77) z   1.250..  1.941,  0.175 mm^2 in plan, 1.39 x 0.22
  0.16 mm at ( 273.89, -47.87) z   1.250..  1.941,  0.516 mm^2 in plan, 2.54 x 0.40
  0.20 mm at ( 277.11, -49.10) z   1.941..  2.140,  0.025 mm^2 in plan, 0.21 x 0.25
  0.22 mm at ( 248.07, -47.78) z   1.250..  1.941,  0.046 mm^2 in plan, 0.44 x 0.23
  0.23 mm at ( 264.68, -47.78) z   1.250..  1.941,  0.275 mm^2 in plan, 1.38 x 0.36
  0.24 mm at ( 279.04, -48.63) z   2.660..  3.050,  0.046 mm^2 in plan, 0.28 x 0.39
  0.24 mm at ( 260.84,-124.47) z  -1.700.. -0.550,  0.146 mm^2 in plan, 1.58 x 0.25
  0.27 mm at ( 188.17, -56.00) z  -1.500.. -0.550,  0.426 mm^2 in plan, 2.76 x 1.04
  0.27 mm at ( 267.62, -47.81) z   1.250..  1.941,  0.210 mm^2 in plan, 1.26 x 0.30
  0.28 mm at ( 207.43, -48.40) z   3.050..  3.750,  0.915 mm^2 in plan, 2.91 x 1.45
  0.28 mm at ( 236.63, -47.80) z  -0.400..  0.000,  0.048 mm^2 in plan, 0.44 x 0.23
  0.29 mm at ( 270.53, -47.83) z   1.250..  1.941,  0.187 mm^2 in plan, 1.14 x 0.33
  0.33 mm at ( 221.45, -43.68) z  -2.554.. -1.700,  0.297 mm^2 in plan, 1.36 x 0.34
  0.33 mm at ( 200.50, -47.91) z   3.050..  3.750,  0.373 mm^2 in plan, 1.66 x 0.48
  0.35 mm at ( 203.27, -47.95) z   3.050..  3.750,  0.407 mm^2 in plan, 2.01 x 0.49
  0.35 mm at ( 166.53, -48.40) z   3.050..  3.750,  1.340 mm^2 in plan, 3.50 x 1.45
  0.35 mm at ( 171.54, -47.91) z   3.050..  3.750,  0.372 mm^2 in plan, 2.10 x 0.44
  0.36 mm at ( 197.57, -47.86) z   3.050..  3.750,  0.273 mm^2 in plan, 1.26 x 0.40
  0.38 mm at ( 176.47, -47.95) z   2.150..  3.750,  5.401 mm^2 in plan, 16.14 x 0.58
  0.39 mm at ( 194.75, -47.91) z   3.050..  3.750,  0.325 mm^2 in plan, 1.33 x 0.48
  0.40 mm at ( 192.10, -47.90) z   3.050..  3.750,  0.372 mm^2 in plan, 1.43 x 0.48
  0.42 mm at ( 231.48,-102.76) z  -2.554.. -0.550,  0.290 mm^2 in plan, 0.87 x 0.44
  0.42 mm at ( 242.91, -48.73) z  -0.500..  0.635,  3.069 mm^2 in plan, 6.73 x 0.79
  0.44 mm at ( 221.48, -96.00) z  -1.500.. -0.550,  0.347 mm^2 in plan, 1.03 x 0.75
  0.44 mm at ( 267.99,-108.06) z  -2.554.. -0.550,  0.217 mm^2 in plan, 0.49 x 0.96
  0.46 mm at ( 199.03,-121.03) z  -2.554.. -0.550,  0.025 mm^2 in plan, 0.26 x 0.24
  0.51 mm at ( 241.30, -53.07) z  -1.500.. -0.550,  0.408 mm^2 in plan, 1.37 x 1.04
  0.52 mm at ( 180.74,-126.77) z  -2.554.. -0.550,  0.287 mm^2 in plan, 0.63 x 0.76
  0.52 mm at ( 184.94, -47.96) z  -1.500..  2.140,  4.595 mm^2 in plan, 9.16 x 0.58
  0.54 mm at ( 191.87,-128.47) z  -1.700.. -0.550,  0.406 mm^2 in plan, 1.57 x 0.58
  0.55 mm at ( 210.36,-125.79) z  -1.700.. -0.550,  0.452 mm^2 in plan, 1.65 x 0.59
  0.56 mm at ( 231.71, -90.61) z  -2.554.. -0.550,  0.475 mm^2 in plan, 0.60 x 1.69
  0.56 mm at ( 231.71, -73.61) z  -2.554.. -0.550,  0.475 mm^2 in plan, 0.60 x 1.69
  0.56 mm at ( 212.71,-108.52) z  -1.600.. -0.550,  0.475 mm^2 in plan, 1.70 x 0.60
  0.56 mm at ( 175.55,-135.21) z  -1.700.. -0.550,  0.470 mm^2 in plan, 1.68 x 0.85
  0.56 mm at ( 204.27,-104.68) z  -1.600.. -0.550,  0.473 mm^2 in plan, 1.69 x 0.60
  0.56 mm at ( 164.20,-133.53) z  -1.700.. -0.550,  0.475 mm^2 in plan, 0.85 x 1.67
  0.56 mm at ( 285.12,-113.13) z  -1.700.. -0.550,  0.474 mm^2 in plan, 0.86 x 1.67
  0.56 mm at ( 209.67,-107.23) z  -2.554.. -1.600,  0.226 mm^2 in plan, 0.67 x 0.71
  0.57 mm at ( 206.51,-105.67) z  -2.554.. -1.600,  0.226 mm^2 in plan, 0.67 x 0.71
  0.58 mm at ( 214.61, -97.10) z  -1.500.. -0.550,  0.706 mm^2 in plan, 1.11 x 1.66
  0.62 mm at ( 238.10, -48.50) z   0.635..  1.941,  0.957 mm^2 in plan, 1.56 x 1.23
```

```
top L grid points with a layer < 0.8 mm: 0 min layer 1.0
bottom L grid points with a layer < 0.8 mm: 0 min layer 0.805
top R grid points with a layer < 0.8 mm: 0 min layer 1.0
bottom R grid points with a layer < 0.8 mm: 55 min layer 0.8
  thin spot around (286.7,-106.2) span 1.0x4.8 min 0.80 mm  n=55
```

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
- L keycaps pressed down (3 mm) in the top, new / original (mm^3): [0.0, 0.0]
- L battery in the bottom, new / original (mm^3): [0.0, 0.0]
- R switch bodies in the top, new / original (mm^3): [0.0, 0.0]
- R keycaps pressed down (3 mm) in the top, new / original (mm^3): [0.0, 0.0]
- R battery in the bottom, new / original (mm^3): [0.0, 0.0]

## Pictures

- `heightmap_L.png`, `heightmap_R.png`: gap from the PCB faces, before and after
- `render3d_L.png`, `render3d_R.png`: the new parts
- `sections_L.png`: cross-sections through the assembly
- `reset_back.png`: back face around the reset button, original vs new (unchanged)
- `underside_holes.png`: the bottoms seen from below, site original vs now (holes through the part)
