# Checks (measured on the final STEP files)

Distances are exact (OpenCASCADE BRepExtrema) between each case part and the KiCad board
(1.6 mm, true outline), every KiCad 3D part on that half, and every exposed copper pad.

| | Left | Right | Original (left) |
|---|---|---|---|
| Top to PCB (outside the 4 floating pads) | 0.52 mm | 0.52 mm | 0.10 mm |
| Bottom to PCB | 0.52 mm | 0.53 mm | 0.35 mm |
| Top to nearest part (switch bodies and diodes aside) | 0.50 mm | 0.50 mm |  |
| Top to diode epoxy (insulator) | 0.37 mm | 0.37 mm |  |
| Bottom to nearest part (sockets, contacts, pins) | 0.50 mm | 0.50 mm |  |
| Top to XIAO | 0.52 mm | 0.52 mm |  |
| Bottom to XIAO | 0.57 mm | 0.55 mm |  |
| Wood insert to XIAO | 1.57 mm | 1.57 mm |  |
| Top to exposed pads | 0.80 mm | 0.80 mm |  |
| Bottom to exposed pads | 0.51 mm | 0.51 mm |  |
| Top/bottom seam gap | 0.20 mm | 0.20 mm |  |

Reset switch: its metal body keeps 0.5 mm; its plastic plunger runs out through a 3.4 x 2.0 mm slot in the back seam, 0.2 mm clear all round (plunger to top/bottom [0.2, 0.2] mm left, [0.2, 0.2] mm right).

Top/bottom overlap: 0.0 / 0.0 mm³.
The top never touches the floating mounting pads either: it stays 0.1 mm above them, as in the original.

## Sizes

- L top: [133.1, 99.01, 12.0, 'z', -1.5, 10.5], valid/solids/volume [True, 1, 17564.7]
- L bottom: [133.11, 99.01, 15.6, 'z', -11.4, 4.2], valid/solids/volume [True, 1, 70715.6]
- L insert: [21.5, 17.0, 3.0, 'z', 7.5, 10.5], valid/solids/volume [True, 1, 916.8]
- R top: [133.1, 99.01, 12.0, 'z', -1.5, 10.5], valid/solids/volume [True, 1, 17579.9]
- R bottom: [133.1, 99.01, 15.6, 'z', -11.4, 4.2], valid/solids/volume [True, 1, 70755.1]
- R insert: [21.5, 17.0, 3.0, 'z', 7.5, 10.5], valid/solids/volume [True, 1, 919.2]

## Parametric model

The parts are built by `work/model.py` (CadQuery features). It never opens the original 3D-print
parts: their reference shapes are curves in `work/model_ref.json` (lines, arcs and the outline's
B-splines, taken once by `work/ref_extract.py`). The outline keeps the original's own curves, its
inside corners rounded R1.05; the bottom is designed feature by feature (block, plateau, walls and
their seam, the 21° leg ramp as one exact plane, leg recesses, battery pocket, feet, notches, foot
chamfers, tapped screw holes); the top takes the original's air band by band, reached from below or
from above as a Ø2 mill cuts it, as one column model (`clean.make_solid`), then the designed seams
and notches. Both get every keep-out (PCB, parts, pads, XIAO) cut as the mill makes it; the top
then makes room for the bottom as milled (0.2 mm), and a last check fills any speck the mill
leaves. Every stage must be one valid solid that survives a STEP round trip.

| Part | Faces | Volume (mm³) |
|---|---|---|
| L top | 5985 | 17564.8 |
| L bottom | 1773 | 70715.6 |
| R top | 4595 | 17579.9 |
| R bottom | 1764 | 70755.1 |

The parts against the previous ones (the clean 2.5D rebuild of the 3D-print parts), column by column
on a 0.05 mm grid (metal only in the previous part = removed, only in the new one = added; spots over
0.05 mm³): the leg ramp is now a plane instead of steps, the walls and seams are designed:

```
top L: volume old 17745.73 new 17564.93
top L: removed: 240.772 mm^3 in total (columns differing by more than 0.005 mm); 23 spots over 0.05 mm^3
top L:     60.424 mm^3, 11.343 mm^2, up to 6.850 mm deep, at ( 123.37,  -56.65) 12.45 x 1.35
top L:     37.372 mm^3, 10.295 mm^2, up to 8.350 mm deep, at (  49.62,  -70.33) 8.75 x 2.50
top L:     27.708 mm^3,  4.045 mm^2, up to 6.850 mm deep, at (  67.57,  -55.36) 5.85 x 1.20
top L:     25.946 mm^3, 15.085 mm^2, up to 7.400 mm deep, at (  34.45,  -99.70) 9.95 x 4.80
top L:     21.483 mm^3, 15.408 mm^2, up to 4.050 mm deep, at (  66.29,  -48.48) 12.30 x 1.50
top L:     16.269 mm^3,  2.375 mm^2, up to 6.850 mm deep, at (  60.63, -119.79) 1.65 x 3.35
top L:     14.760 mm^3,  3.398 mm^2, up to 8.000 mm deep, at ( 144.80, -120.98) 2.30 x 2.90
top L:     12.582 mm^3, 25.140 mm^2, up to 1.485 mm deep, at (  91.47,  -97.59) 11.80 x 7.35
top L:      6.363 mm^3,  5.360 mm^2, up to 6.100 mm deep, at (  29.49,  -71.02) 1.95 x 3.55
top L:      5.049 mm^3,  4.595 mm^2, up to 5.850 mm deep, at ( 142.42,  -48.41) 3.10 x 1.80
top L:      3.832 mm^3,  5.963 mm^2, up to 7.400 mm deep, at (  30.40,  -48.62) 3.85 x 2.40
top L:      2.030 mm^3,  4.765 mm^2, up to 5.650 mm deep, at (  99.86,  -48.38) 3.35 x 1.50
top L:      0.831 mm^3,  0.723 mm^2, up to 1.150 mm deep, at ( 116.28, -129.39) 2.90 x 1.05
top L:      0.681 mm^3,  0.593 mm^2, up to 1.150 mm deep, at (  21.54, -111.93) 0.60 x 1.90
top L:      0.592 mm^3,  0.515 mm^2, up to 1.150 mm deep, at ( 143.97, -134.68) 0.95 x 1.45
top L:      0.561 mm^3,  0.488 mm^2, up to 1.150 mm deep, at (  98.63, -126.80) 1.70 x 0.40
top L:      0.520 mm^3,  0.453 mm^2, up to 1.150 mm deep, at ( 132.04, -136.09) 1.45 x 0.90
top L:      0.355 mm^3,  1.590 mm^2, up to 2.280 mm deep, at ( 127.02,  -48.06) 3.65 x 1.50
top L:      0.315 mm^3,  1.488 mm^2, up to 2.280 mm deep, at ( 119.05,  -48.04) 3.55 x 1.45
top L:      0.288 mm^3,  0.250 mm^2, up to 1.150 mm deep, at (  96.38, -126.74) 1.35 x 0.25
top L: added: 70.308 mm^3 in total (columns differing by more than 0.005 mm); 40 spots over 0.05 mm^3
top L:     16.690 mm^3,  2.715 mm^2, up to 6.850 mm deep, at ( 132.31,  -83.44) 0.10 x 54.05
top L:     11.035 mm^3,  4.328 mm^2, up to 2.550 mm deep, at (  28.88,  -59.60) 0.50 x 9.45
top L:      6.881 mm^3,  2.995 mm^2, up to 4.650 mm deep, at ( 123.00,  -47.89) 7.75 x 0.60
top L:      3.048 mm^3,  0.445 mm^2, up to 6.850 mm deep, at (  31.21,  -75.76) 1.95 x 0.75
top L:      2.946 mm^3,  0.430 mm^2, up to 6.850 mm deep, at (  86.84, -127.24) 1.65 x 1.50
top L:      2.539 mm^3,  3.470 mm^2, up to 6.850 mm deep, at ( 131.37,  -49.61) 5.50 x 1.55
top L:      1.838 mm^3,  2.828 mm^2, up to 0.650 mm deep, at (  65.15,  -47.86) 7.25 x 0.50
top L:      1.362 mm^3,  0.200 mm^2, up to 6.850 mm deep, at (  20.37, -102.03) 0.90 x 1.30
top L:      1.344 mm^3,  0.193 mm^2, up to 12.000 mm deep, at ( 140.73, -142.32) 1.20 x 0.55
top L:      1.275 mm^3, 12.123 mm^2, up to 0.550 mm deep, at ( 139.54, -112.01) 4.80 x 4.60
top L:      1.246 mm^3,  0.180 mm^2, up to 12.000 mm deep, at ( 151.23, -124.16) 0.60 x 1.10
top L:      1.193 mm^3, 11.933 mm^2, up to 0.100 mm deep, at (  34.30, -121.02) 4.65 x 4.70
top L:      1.088 mm^3, 10.873 mm^2, up to 0.550 mm deep, at (  57.00,  -52.88) 4.60 x 4.45
top L:      1.088 mm^3, 10.870 mm^2, up to 0.550 mm deep, at ( 131.20,  -52.88) 4.60 x 4.45
top L:      1.079 mm^3,  0.158 mm^2, up to 6.850 mm deep, at (  75.68,  -45.45) 0.85 x 1.00
top L:      1.034 mm^3,  1.478 mm^2, up to 0.700 mm deep, at ( 117.28,  -48.41) 1.20 x 1.50
top L:      0.991 mm^3,  1.483 mm^2, up to 6.850 mm deep, at (  59.44,  -48.62) 1.00 x 2.95
top L:      0.898 mm^3,  1.250 mm^2, up to 5.550 mm deep, at ( 128.76,  -48.46) 1.00 x 1.75
top L:      0.870 mm^3,  1.243 mm^2, up to 0.700 mm deep, at ( 140.35,  -48.40) 1.00 x 1.50
top L:      0.849 mm^3,  1.213 mm^2, up to 0.700 mm deep, at ( 101.98,  -48.40) 0.95 x 1.50
bottom L: volume old 70198.27 new 70716.24
bottom L: removed: 44.192 mm^3 in total (columns differing by more than 0.005 mm); 35 spots over 0.05 mm^3
bottom L:      4.137 mm^3,  0.468 mm^2, up to 8.850 mm deep, at (  40.39, -114.70) 1.65 x 1.55
bottom L:      3.806 mm^3,  0.430 mm^2, up to 8.850 mm deep, at (  40.32,  -58.36) 1.50 x 1.60
bottom L:      3.385 mm^3,  0.383 mm^2, up to 8.850 mm deep, at (  79.66, -114.60) 1.55 x 1.65
bottom L:      3.353 mm^3,  0.470 mm^2, up to 8.850 mm deep, at (  75.70,  -58.39) 1.55 x 1.65
bottom L:      3.289 mm^3,  0.358 mm^2, up to 9.200 mm deep, at ( 111.11, -129.50) 5.15 x 1.15
bottom L:      3.230 mm^3,  0.365 mm^2, up to 8.850 mm deep, at (  79.70, -103.41) 1.45 x 1.55
bottom L:      2.901 mm^3, 17.865 mm^2, up to 0.309 mm deep, at (  28.24, -109.66) 0.80 x 23.35
bottom L:      2.727 mm^3,  0.665 mm^2, up to 4.100 mm deep, at ( 141.82,  -48.42) 0.60 x 1.55
bottom L:      2.665 mm^3,  0.653 mm^2, up to 4.800 mm deep, at ( 128.25,  -48.46) 0.65 x 1.50
bottom L:      2.645 mm^3,  0.645 mm^2, up to 4.100 mm deep, at ( 124.47, -132.71) 1.10 x 1.20
bottom L:      2.531 mm^3,  0.610 mm^2, up to 4.795 mm deep, at ( 136.29, -139.23) 1.00 x 1.65
bottom L:      1.679 mm^3,  0.183 mm^2, up to 9.200 mm deep, at ( 105.06, -128.45) 3.05 x 0.35
bottom L:      1.189 mm^3,  7.935 mm^2, up to 0.329 mm deep, at (  20.03, -105.48) 0.85 x 12.40
bottom L:      0.887 mm^3,  6.312 mm^2, up to 0.321 mm deep, at (  21.23, -113.34) 0.85 x 10.45
bottom L:      0.714 mm^3,  4.360 mm^2, up to 0.313 mm deep, at (  22.35, -118.72) 0.80 x 5.95
bottom L:      0.560 mm^3,  4.062 mm^2, up to 0.323 mm deep, at (  19.14, -102.94) 0.85 x 7.15
bottom L:      0.554 mm^3,  1.208 mm^2, up to 1.185 mm deep, at (  65.51,  -48.87) 6.55 x 0.85
bottom L:      0.161 mm^3,  0.018 mm^2, up to 9.200 mm deep, at ( 103.26, -128.26) 0.35 x 0.05
bottom L:      0.153 mm^3,  1.010 mm^2, up to 0.312 mm deep, at (  22.38, -100.37) 0.80 x 1.75
bottom L:      0.151 mm^3,  1.038 mm^2, up to 0.306 mm deep, at (  25.93,  -99.75) 0.80 x 1.80
bottom L: added: 582.298 mm^3 in total (columns differing by more than 0.005 mm); 37 spots over 0.05 mm^3
bottom L:     77.524 mm^3, 73.725 mm^2, up to 5.150 mm deep, at (  92.47, -106.52) 26.05 x 3.25
bottom L:     73.076 mm^3, 195.095 mm^2, up to 4.341 mm deep, at (  27.27, -107.85) 19.35 x 22.75
bottom L:     52.710 mm^3, 14.208 mm^2, up to 15.350 mm deep, at ( 122.11,  -48.11) 46.50 x 1.85
bottom L:     44.175 mm^3, 21.018 mm^2, up to 15.600 mm deep, at (  55.07,  -48.36) 44.50 x 2.55
bottom L:     44.086 mm^3, 68.297 mm^2, up to 0.646 mm deep, at ( 123.57,  -77.57) 13.95 x 7.95
bottom L:     44.068 mm^3, 68.270 mm^2, up to 0.646 mm deep, at ( 123.57,  -94.57) 13.95 x 7.90
bottom L:     44.068 mm^3, 68.270 mm^2, up to 0.646 mm deep, at (  87.57,  -83.41) 13.95 x 7.90
bottom L:     44.055 mm^3, 68.250 mm^2, up to 0.646 mm deep, at ( 105.58,  -74.80) 13.95 x 7.95
bottom L:     43.996 mm^3, 68.158 mm^2, up to 0.646 mm deep, at ( 105.58,  -91.80) 13.95 x 7.90
bottom L:     36.940 mm^3, 57.227 mm^2, up to 0.646 mm deep, at (  87.09,  -48.85) 13.95 x 6.05
bottom L:     11.777 mm^3,  4.475 mm^2, up to 5.900 mm deep, at (  29.42,  -70.77) 2.10 x 4.10
bottom L:     10.073 mm^3, 15.605 mm^2, up to 0.646 mm deep, at ( 144.42, -128.00) 4.65 x 5.20
bottom L:      9.800 mm^3, 15.183 mm^2, up to 0.646 mm deep, at (  64.60,  -57.06) 12.10 x 2.45
bottom L:      7.925 mm^3, 12.278 mm^2, up to 0.646 mm deep, at (  89.84,  -69.14) 6.00 x 2.25
bottom L:      6.130 mm^3, 12.235 mm^2, up to 0.854 mm deep, at (  92.08,  -46.01) 8.05 x 3.00
bottom L:      4.264 mm^3,  6.605 mm^2, up to 0.646 mm deep, at (  81.96,  -65.29) 2.85 x 2.75
bottom L:      3.337 mm^3,  0.693 mm^2, up to 5.600 mm deep, at ( 132.47, -137.81) 6.85 x 3.95
bottom L:      1.777 mm^3,  2.753 mm^2, up to 0.646 mm deep, at (  39.46,  -74.68) 1.25 x 2.80
bottom L:      1.003 mm^3,  0.205 mm^2, up to 5.600 mm deep, at ( 125.79, -134.18) 2.60 x 1.25
bottom L:      0.646 mm^3,  0.553 mm^2, up to 2.004 mm deep, at (  96.64,  -50.66) 1.10 x 1.60
top R: volume old 17732.61 new 17580.07
top R: removed: 219.045 mm^3 in total (columns differing by more than 0.005 mm); 26 spots over 0.05 mm^3
top R:     60.433 mm^3, 11.410 mm^2, up to 7.835 mm deep, at ( 185.33,  -56.66) 12.40 x 1.40
top R:     36.215 mm^3, 10.073 mm^2, up to 7.835 mm deep, at ( 258.31,  -70.34) 8.70 x 2.50
top R:     26.235 mm^3,  3.830 mm^2, up to 6.850 mm deep, at ( 240.36,  -55.37) 5.50 x 1.15
top R:     21.511 mm^3, 15.530 mm^2, up to 4.050 mm deep, at ( 241.58,  -48.48) 12.55 x 1.50
top R:     15.960 mm^3,  2.330 mm^2, up to 6.850 mm deep, at ( 247.15, -119.81) 1.60 x 3.20
top R:     12.749 mm^3,  1.863 mm^2, up to 12.000 mm deep, at ( 162.94, -120.70) 2.30 x 1.85
top R:     12.250 mm^3, 24.478 mm^2, up to 1.485 mm deep, at ( 216.52,  -97.55) 11.90 x 7.15
top R:      7.059 mm^3, 12.775 mm^2, up to 1.100 mm deep, at ( 274.02,  -99.97) 9.15 x 3.25
top R:      6.392 mm^3,  5.273 mm^2, up to 6.100 mm deep, at ( 278.38,  -71.01) 1.85 x 3.60
top R:      5.182 mm^3,  4.615 mm^2, up to 5.850 mm deep, at ( 165.43,  -48.41) 3.10 x 1.80
top R:      3.866 mm^3,  6.070 mm^2, up to 2.150 mm deep, at ( 277.45,  -48.62) 4.00 x 2.50
top R:      2.016 mm^3,  4.798 mm^2, up to 5.650 mm deep, at ( 208.02,  -48.38) 3.40 x 1.50
top R:      1.118 mm^3,  0.973 mm^2, up to 1.150 mm deep, at ( 209.93, -126.83) 3.05 x 0.50
top R:      0.779 mm^3,  0.678 mm^2, up to 1.150 mm deep, at ( 163.31, -133.69) 1.15 x 1.90
top R:      0.690 mm^3,  0.600 mm^2, up to 1.150 mm deep, at ( 191.96, -129.27) 2.45 x 0.75
top R:      0.529 mm^3,  0.410 mm^2, up to 6.850 mm deep, at ( 286.06, -112.95) 0.50 x 1.65
top R:      0.515 mm^3,  0.448 mm^2, up to 1.150 mm deep, at ( 176.39, -135.76) 1.40 x 0.85
top R:      0.407 mm^3,  0.268 mm^2, up to 6.850 mm deep, at ( 285.53, -115.54) 0.45 x 1.90
top R:      0.380 mm^3,  1.740 mm^2, up to 2.280 mm deep, at ( 180.83,  -48.09) 3.75 x 1.55
top R:      0.322 mm^3,  0.280 mm^2, up to 1.150 mm deep, at ( 174.43, -136.83) 1.30 x 0.80
top R: added: 63.467 mm^3 in total (columns differing by more than 0.005 mm); 35 spots over 0.05 mm^3
top R:     11.832 mm^3,  4.150 mm^2, up to 3.650 mm deep, at ( 276.60, -123.97) 2.35 x 2.30
top R:     11.003 mm^3,  4.315 mm^2, up to 2.550 mm deep, at ( 278.98,  -59.60) 0.50 x 9.40
top R:      6.869 mm^3,  2.995 mm^2, up to 4.650 mm deep, at ( 184.97,  -47.89) 7.70 x 0.60
top R:      5.189 mm^3,  0.758 mm^2, up to 6.850 mm deep, at ( 250.36, -124.16) 1.10 x 2.05
top R:      2.911 mm^3,  0.425 mm^2, up to 6.850 mm deep, at ( 221.03, -127.22) 1.65 x 1.50
top R:      2.743 mm^3,  3.443 mm^2, up to 6.850 mm deep, at ( 176.57,  -49.61) 5.50 x 1.55
top R:      1.835 mm^3,  2.823 mm^2, up to 0.650 mm deep, at ( 242.91,  -47.86) 7.20 x 0.50
top R:      1.602 mm^3,  1.188 mm^2, up to 6.850 mm deep, at ( 275.52,  -48.60) 3.35 x 1.65
top R:      1.284 mm^3,  0.188 mm^2, up to 6.850 mm deep, at ( 156.64, -124.16) 0.55 x 1.10
top R:      1.280 mm^3,  0.185 mm^2, up to 12.000 mm deep, at ( 167.11, -142.32) 1.10 x 0.55
top R:      1.194 mm^3, 11.938 mm^2, up to 0.100 mm deep, at ( 168.46, -112.00) 4.65 x 4.60
top R:      1.179 mm^3, 11.780 mm^2, up to 0.550 mm deep, at ( 273.62, -121.01) 4.55 x 4.75
top R:      1.144 mm^3,  1.635 mm^2, up to 0.700 mm deep, at ( 190.63,  -48.40) 1.20 x 1.50
top R:      1.137 mm^3,  1.818 mm^2, up to 6.850 mm deep, at ( 248.60,  -48.61) 1.25 x 2.95
top R:      1.090 mm^3, 10.900 mm^2, up to 0.100 mm deep, at ( 176.76,  -52.88) 4.60 x 4.45
top R:      1.089 mm^3, 10.890 mm^2, up to 0.100 mm deep, at ( 250.96,  -52.88) 4.60 x 4.45
top R:      1.058 mm^3,  0.615 mm^2, up to 6.850 mm deep, at ( 277.04,  -71.64) 1.10 x 1.05
top R:      1.020 mm^3,  1.458 mm^2, up to 0.700 mm deep, at ( 167.58,  -48.40) 1.10 x 1.50
top R:      0.824 mm^3,  1.177 mm^2, up to 0.700 mm deep, at ( 205.87,  -48.37) 0.90 x 1.50
top R:      0.797 mm^3,  1.105 mm^2, up to 5.550 mm deep, at ( 179.15,  -48.45) 0.90 x 1.80
bottom R: volume old 70187.04 new 70755.72
bottom R: removed: 43.357 mm^3 in total (columns differing by more than 0.005 mm); 40 spots over 0.05 mm^3
bottom R:      3.960 mm^3,  0.448 mm^2, up to 8.850 mm deep, at ( 232.16,  -58.41) 1.55 x 1.65
bottom R:      3.938 mm^3,  0.445 mm^2, up to 8.850 mm deep, at ( 267.54,  -58.35) 1.55 x 1.60
bottom R:      3.552 mm^3,  0.463 mm^2, up to 8.850 mm deep, at ( 267.51, -114.65) 1.60 x 1.60
bottom R:      3.274 mm^3,  0.370 mm^2, up to 8.850 mm deep, at ( 228.27, -114.67) 1.60 x 1.50
bottom R:      3.224 mm^3,  0.355 mm^2, up to 9.200 mm deep, at ( 196.73, -129.50) 5.15 x 1.15
bottom R:      3.208 mm^3,  0.363 mm^2, up to 8.850 mm deep, at ( 228.23, -103.35) 1.55 x 1.60
bottom R:      2.823 mm^3, 17.865 mm^2, up to 0.309 mm deep, at ( 279.62, -109.66) 0.80 x 23.35
bottom R:      2.645 mm^3,  0.645 mm^2, up to 4.100 mm deep, at ( 183.40, -132.71) 1.10 x 1.20
bottom R:      2.450 mm^3,  0.598 mm^2, up to 4.100 mm deep, at ( 166.07,  -48.44) 0.55 x 1.50
bottom R:      2.440 mm^3,  0.595 mm^2, up to 4.100 mm deep, at ( 179.58,  -48.45) 0.55 x 1.50
bottom R:      2.337 mm^3,  0.570 mm^2, up to 4.100 mm deep, at ( 171.53, -139.18) 0.70 x 1.45
bottom R:      1.679 mm^3,  0.183 mm^2, up to 9.200 mm deep, at ( 202.81, -128.45) 3.05 x 0.35
bottom R:      1.131 mm^3,  8.335 mm^2, up to 0.322 mm deep, at ( 287.80, -105.47) 1.25 x 12.40
bottom R:      0.945 mm^3,  6.645 mm^2, up to 0.317 mm deep, at ( 286.65, -113.25) 0.85 x 10.60
bottom R:      0.709 mm^3,  4.388 mm^2, up to 0.312 mm deep, at ( 285.51, -118.71) 0.80 x 6.00
bottom R:      0.579 mm^3,  1.285 mm^2, up to 0.505 mm deep, at ( 242.28,  -48.86) 6.60 x 0.90
bottom R:      0.517 mm^3,  3.993 mm^2, up to 0.317 mm deep, at ( 288.71, -102.96) 0.85 x 7.15
bottom R:      0.216 mm^3,  0.045 mm^2, up to 4.795 mm deep, at ( 171.98, -139.86) 0.55 x 0.35
bottom R:      0.204 mm^3,  0.043 mm^2, up to 4.795 mm deep, at ( 183.77, -133.49) 0.50 x 0.25
bottom R:      0.199 mm^3,  0.288 mm^2, up to 0.691 mm deep, at ( 247.75,  -48.22) 0.30 x 1.20
bottom R: added: 630.029 mm^3 in total (columns differing by more than 0.005 mm); 33 spots over 0.05 mm^3
bottom R:     76.248 mm^3, 168.843 mm^2, up to 4.351 mm deep, at ( 282.14, -108.35) 14.50 x 22.70
bottom R:     72.077 mm^3, 68.483 mm^2, up to 5.150 mm deep, at ( 216.37, -106.58) 26.05 x 3.25
bottom R:     51.948 mm^3, 14.273 mm^2, up to 15.350 mm deep, at ( 185.69,  -48.11) 46.55 x 1.85
bottom R:     44.329 mm^3, 21.283 mm^2, up to 15.600 mm deep, at ( 253.24,  -48.37) 44.45 x 2.55
bottom R:     44.088 mm^3, 68.300 mm^2, up to 0.646 mm deep, at ( 207.23,  -74.86) 13.95 x 7.90
bottom R:     44.083 mm^3, 68.293 mm^2, up to 0.646 mm deep, at ( 225.23,  -49.36) 13.95 x 7.90
bottom R:     44.015 mm^3, 68.188 mm^2, up to 0.646 mm deep, at ( 189.23,  -94.60) 13.95 x 7.90
bottom R:     43.997 mm^3, 68.160 mm^2, up to 0.646 mm deep, at ( 207.22,  -91.86) 13.95 x 7.90
bottom R:     43.996 mm^3, 68.158 mm^2, up to 0.646 mm deep, at ( 189.23,  -77.60) 13.95 x 7.90
bottom R:     43.883 mm^3, 67.983 mm^2, up to 0.646 mm deep, at ( 225.19,  -83.41) 13.65 x 7.90
bottom R:     25.392 mm^3, 39.338 mm^2, up to 0.646 mm deep, at ( 227.59,  -67.42) 8.60 x 5.85
bottom R:     16.925 mm^3, 26.220 mm^2, up to 0.646 mm deep, at ( 215.43, -114.20) 7.75 x 4.90
bottom R:     16.839 mm^3, 26.088 mm^2, up to 0.646 mm deep, at ( 270.24,  -77.27) 5.70 x 6.20
bottom R:     11.664 mm^3,  4.505 mm^2, up to 5.900 mm deep, at ( 278.42,  -70.79) 2.10 x 4.15
bottom R:      8.863 mm^3, 13.730 mm^2, up to 0.646 mm deep, at ( 243.33,  -56.97) 7.70 x 2.45
bottom R:      6.128 mm^3, 12.230 mm^2, up to 0.854 mm deep, at ( 229.67,  -46.01) 8.05 x 3.00
bottom R:      5.919 mm^3,  9.170 mm^2, up to 0.646 mm deep, at ( 268.94,  -94.19) 2.70 x 5.45
bottom R:      5.641 mm^3,  1.158 mm^2, up to 5.600 mm deep, at ( 177.60, -136.58) 10.95 x 6.00
bottom R:      4.713 mm^3,  0.378 mm^2, up to 12.485 mm deep, at ( 279.20,  -59.61) 0.05 x 7.55
bottom R:      0.666 mm^3,  0.570 mm^2, up to 2.004 mm deep, at ( 234.21,  -50.69) 1.10 x 1.50
```

## Solid checks

```
TOTEM_alu_top_L valid True solids 1 shells 1 closed True analyzer: {}
TOTEM_alu_top_R valid True solids 1 shells 1 closed True analyzer: {}
TOTEM_alu_bottom_L valid True solids 1 shells 1 closed True analyzer: {'BOPAlgo_InvalidCurveOnSurface': 1}
TOTEM_alu_bottom_R valid True solids 1 shells 1 closed True analyzer: {'BOPAlgo_InvalidCurveOnSurface': 1}
TOTEM_wood_window_insert_L valid True solids 1 shells 1 closed True analyzer: {}
TOTEM_wood_window_insert_R valid True solids 1 shells 1 closed True analyzer: {}
```

`InvalidCurveOnSurface` is a tolerance note normal after a STEP round trip.

## Holes through the bottom

Every vertical line through each bottom was ray-cast (0.25 mm grid). Nothing goes through the
bottom any more (the screw holes are blind tapped holes from above), and no socket pocket breaks
through into the leg recesses
(see `underside_holes.png`):

```
new L through-openings: 0
new R through-openings: 0
```

## Thin walls compared with the original

- L top: (87.1,-96.8) 0.52 mm (new); (93.2,-98.1) 0.52 mm (new); (49.4,-69.9) 0.52 mm (new)
- L bottom: no new or thinner spots (clusters of 5+ samples, 0.25 mm grid)
- R top: (258.4,-69.9) 0.52 mm (new); (221.0,-96.8) 0.52 mm (new); (214.8,-98.0) 0.52 mm (new)
- R bottom: (287.2,-105.3) 0.65 mm (new)

## Walls thinner than 0.8 mm

Every band between the parts' flat faces, cut in plan: metal narrower than 0.8 mm (what an
opening by a 0.4 mm disc removes, less the bits it rounds off plain corners; width = twice the
largest distance to the outline). Thin layers in z (floors, roofs) are listed below from
`thin.py` (0.25 mm grid, all spots under 0.8 mm, screw-hole rings included):

```
../outputs/TOTEM_alu_top_L.step: 43 walls thinner than 0.8 mm
  0.02 mm at (  30.16, -70.46) z   4.400..  4.600,  0.005 mm^2 in plan, 0.08 x 0.33
  0.07 mm at (  98.69, -49.10) z   4.150..  4.350,  0.006 mm^2 in plan, 0.13 x 0.10
  0.07 mm at (  30.07, -72.46) z  -0.350..  2.150,  0.006 mm^2 in plan, 0.10 x 0.14
  0.08 mm at ( 141.06, -49.11) z   4.150..  4.350,  0.008 mm^2 in plan, 0.16 x 0.10
  0.08 mm at ( 117.95, -49.11) z   3.450..  4.350,  0.007 mm^2 in plan, 0.13 x 0.10
  0.08 mm at ( 101.31, -49.11) z   4.150..  4.350,  0.008 mm^2 in plan, 0.15 x 0.10
  0.08 mm at (  28.68, -72.46) z  -1.500..  4.400,  0.007 mm^2 in plan, 0.10 x 0.15
  0.08 mm at (  71.91, -49.11) z   2.350..  2.550,  0.008 mm^2 in plan, 0.16 x 0.10
  0.09 mm at (  30.45, -71.07) z   4.400..  4.600,  0.010 mm^2 in plan, 0.16 x 0.22
  0.10 mm at ( 128.83, -49.67) z   2.150..  2.860,  0.010 mm^2 in plan, 0.16 x 0.13
  0.10 mm at (  28.68, -69.08) z   4.600..  6.430,  0.009 mm^2 in plan, 0.18 x 0.11
  0.10 mm at (  30.25, -47.71) z   4.400..  4.600,  0.008 mm^2 in plan, 0.16 x 0.11
  0.10 mm at (  32.21, -49.06) z   2.350..  2.550,  0.011 mm^2 in plan, 0.21 x 0.18
  0.10 mm at (  30.60, -47.72) z   2.550..  4.400,  0.010 mm^2 in plan, 0.18 x 0.12
  0.10 mm at (  32.50, -47.71) z   1.650..  2.350,  0.007 mm^2 in plan, 0.11 x 0.11
  0.12 mm at (  28.68, -50.13) z   4.600..  6.430,  0.009 mm^2 in plan, 0.18 x 0.11
  0.14 mm at ( 143.81, -47.74) z  -1.500..  4.150,  0.020 mm^2 in plan, 0.23 x 0.17
  0.18 mm at (  87.78, -96.31) z   2.150..  2.450,  0.030 mm^2 in plan, 0.36 x 0.19
  0.18 mm at (  91.35, -96.31) z   2.150..  2.450,  0.030 mm^2 in plan, 0.36 x 0.19
  0.18 mm at (  86.35, -96.31) z   2.150..  2.450,  0.030 mm^2 in plan, 0.36 x 0.19
  0.22 mm at (  52.36, -69.07) z   3.650..  6.430,  0.051 mm^2 in plan, 0.54 x 0.30
  0.23 mm at ( 141.10,-142.14) z   3.650.. 10.500,  0.191 mm^2 in plan, 1.43 x 0.73
  0.23 mm at ( 151.31,-124.27) z   3.650.. 10.500,  0.186 mm^2 in plan, 0.73 x 1.43
  0.23 mm at ( 145.38,-120.42) z   3.650.. 10.500,  0.065 mm^2 in plan, 0.68 x 0.54
  0.23 mm at (  86.93,-127.51) z   3.650.. 10.500,  0.256 mm^2 in plan, 1.29 x 1.25
  0.23 mm at (  30.26, -49.58) z   2.550..  4.600,  0.190 mm^2 in plan, 0.63 x 1.04
  0.24 mm at ( 133.90, -49.29) z   3.295..  3.450,  0.061 mm^2 in plan, 0.73 x 0.24
  0.31 mm at (  57.02, -51.36) z   1.600..  2.150,  0.141 mm^2 in plan, 0.50 x 0.34
  0.31 mm at ( 131.22, -51.36) z   1.600..  2.150,  0.141 mm^2 in plan, 0.50 x 0.34
  0.31 mm at (  34.19,-100.35) z   2.150..  2.450,  0.961 mm^2 in plan, 6.13 x 1.25
  0.31 mm at (  59.89, -48.92) z   1.650..  2.150,  0.063 mm^2 in plan, 0.39 x 0.38
  0.31 mm at (  94.99, -99.06) z   2.150..  2.450,  0.276 mm^2 in plan, 0.33 x 1.41
  0.34 mm at (  83.87, -43.67) z  -1.500..  1.600,  0.301 mm^2 in plan, 1.35 x 0.35
  0.39 mm at (  27.84, -98.92) z  -1.500..  1.600,  0.184 mm^2 in plan, 0.71 x 0.52
  0.49 mm at ( 119.06, -55.90) z   3.650..  6.430,  0.322 mm^2 in plan, 0.88 x 0.52
  0.57 mm at ( 123.00, -47.95) z   4.350..  6.430,  4.711 mm^2 in plan, 9.14 x 0.60
  0.58 mm at ( 125.81, -47.95) z   4.350..  5.095,  1.186 mm^2 in plan, 2.87 x 0.59
  0.60 mm at ( 148.66,-128.82) z  -1.500..  2.150,  0.145 mm^2 in plan, 0.70 x 0.61
  0.60 mm at ( 147.24,-131.25) z  -1.500..  2.150,  0.152 mm^2 in plan, 0.71 x 0.62
  0.68 mm at (  50.44, -69.27) z   3.650..  9.000,  1.413 mm^2 in plan, 3.24 x 0.92
  0.68 mm at (  61.53,-119.81) z   3.650..  9.000,  0.433 mm^2 in plan, 0.71 x 0.88
  0.74 mm at (  67.54, -54.68) z   3.650..  3.700,  1.444 mm^2 in plan, 2.85 x 0.76
  0.77 mm at ( 123.93, -55.76) z   3.650..  6.430,  4.979 mm^2 in plan, 6.91 x 0.78
../outputs/TOTEM_alu_bottom_L.step: 38 walls thinner than 0.8 mm
  0.00 mm at ( 138.62, -47.66) z -11.400.. -7.300,  0.076 mm^2 in plan, 10.39 x 0.01
  0.07 mm at (  92.98,-101.07) z  -1.500.. -0.550,  0.007 mm^2 in plan, 0.10 x 0.17
  0.10 mm at (  28.68, -69.07) z   1.085..  4.200,  0.009 mm^2 in plan, 0.17 x 0.11
  0.11 mm at (  65.40, -52.07) z  -1.500.. -0.550,  0.013 mm^2 in plan, 0.12 x 0.25
  0.11 mm at (  60.90, -48.80) z   1.250..  2.150,  0.015 mm^2 in plan, 0.24 x 0.16
  0.12 mm at (  89.02, -97.99) z  -1.500.. -0.550,  0.073 mm^2 in plan, 0.82 x 0.39
  0.12 mm at (  68.94, -47.76) z   0.635..  1.350,  0.040 mm^2 in plan, 0.44 x 0.21
  0.12 mm at (  28.68, -50.13) z   1.085..  4.200,  0.009 mm^2 in plan, 0.17 x 0.11
  0.12 mm at (  65.09, -50.66) z  -1.500.. -0.550,  0.018 mm^2 in plan, 0.15 x 0.23
  0.13 mm at (  95.12, -48.99) z  -2.554.. -1.710,  0.022 mm^2 in plan, 0.20 x 0.26
  0.14 mm at (  61.36, -47.77) z   0.635..  1.850,  0.040 mm^2 in plan, 0.44 x 0.21
  0.15 mm at (  60.32, -48.75) z   1.250..  2.150,  0.015 mm^2 in plan, 0.23 x 0.16
  0.23 mm at (  39.89, -69.76) z  -2.554.. -1.710,  0.032 mm^2 in plan, 0.28 x 0.22
  0.23 mm at (  39.89, -69.76) z  -1.700.. -1.500,  0.032 mm^2 in plan, 0.28 x 0.22
  0.34 mm at (  83.87, -43.67) z  -2.554.. -1.710,  0.302 mm^2 in plan, 1.34 x 0.35
  0.39 mm at (  27.84, -98.92) z  -2.554.. -1.710,  0.185 mm^2 in plan, 0.71 x 0.53
  0.40 mm at (  39.91,-112.47) z  -2.554.. -1.710,  0.699 mm^2 in plan, 0.56 x 2.97
  0.40 mm at (  39.91,-112.47) z  -1.700.. -0.550,  0.699 mm^2 in plan, 0.56 x 2.97
  0.55 mm at ( 132.68,-135.55) z  -1.700.. -0.550,  0.441 mm^2 in plan, 1.40 x 1.24
  0.55 mm at ( 143.96,-122.13) z  -1.700.. -0.550,  0.646 mm^2 in plan, 1.77 x 1.82
  0.56 mm at ( 121.85, -55.69) z  -1.500.. -0.550,  0.406 mm^2 in plan, 1.12 x 0.60
  0.56 mm at (  76.15, -89.26) z  -2.554.. -1.710,  0.475 mm^2 in plan, 0.60 x 1.69
  0.56 mm at (  76.15, -89.26) z  -1.700.. -0.550,  0.475 mm^2 in plan, 0.60 x 1.69
  0.56 mm at (  76.15, -72.26) z  -2.554.. -1.710,  0.475 mm^2 in plan, 0.60 x 1.69
  0.56 mm at (  76.15, -72.26) z  -1.700.. -0.550,  0.475 mm^2 in plan, 0.60 x 1.69
  0.56 mm at (  22.45,-111.97) z  -1.700.. -0.550,  0.475 mm^2 in plan, 0.61 x 1.67
  0.56 mm at ( 143.33,-134.10) z  -1.700.. -0.550,  0.476 mm^2 in plan, 1.31 x 1.47
  0.57 mm at ( 116.52,-128.64) z  -1.700.. -0.550,  0.557 mm^2 in plan, 1.84 x 1.13
  0.58 mm at ( 125.39,-125.84) z  -1.700.. -0.550,  0.205 mm^2 in plan, 0.74 x 0.71
  0.58 mm at ( 125.39,-125.84) z  -2.554.. -1.710,  0.205 mm^2 in plan, 0.74 x 0.71
  0.58 mm at (  98.25,-125.82) z  -1.700.. -0.550,  0.519 mm^2 in plan, 1.81 x 0.64
  0.58 mm at ( 127.86, -48.27) z  -1.500..  3.950,  5.311 mm^2 in plan, 9.94 x 1.22
  0.79 mm at ( 112.96, -80.54) z  -2.554.. -1.710,  9.126 mm^2 in plan, 5.13 x 11.50
  0.79 mm at ( 112.96, -80.54) z  -1.700.. -0.550,  9.126 mm^2 in plan, 5.13 x 11.50
  0.79 mm at ( 112.96, -63.54) z  -2.554.. -1.710,  9.127 mm^2 in plan, 5.13 x 11.50
  0.79 mm at ( 112.96, -63.54) z  -1.700.. -0.550,  9.127 mm^2 in plan, 5.13 x 11.50
  0.79 mm at ( 112.96, -97.54) z  -2.554.. -1.710,  9.127 mm^2 in plan, 5.13 x 11.50
  0.79 mm at ( 112.96, -97.54) z  -1.700.. -0.550,  9.127 mm^2 in plan, 5.13 x 11.50
../outputs/TOTEM_alu_top_R.step: 50 walls thinner than 0.8 mm
  0.07 mm at ( 277.22, -49.19) z   2.550..  4.400,  0.025 mm^2 in plan, 0.20 x 0.28
  0.07 mm at ( 209.17, -49.10) z   4.150..  4.350,  0.006 mm^2 in plan, 0.13 x 0.09
  0.07 mm at ( 277.37, -71.14) z   2.350..  4.600,  0.016 mm^2 in plan, 0.18 x 0.25
  0.08 mm at ( 235.95, -49.11) z   2.350..  2.550,  0.008 mm^2 in plan, 0.15 x 0.10
  0.08 mm at ( 166.81, -49.11) z   4.150..  4.350,  0.008 mm^2 in plan, 0.16 x 0.10
  0.08 mm at ( 277.77, -69.12) z   4.600..  6.430,  0.006 mm^2 in plan, 0.09 x 0.14
  0.08 mm at ( 206.56, -49.11) z   4.150..  4.350,  0.008 mm^2 in plan, 0.16 x 0.10
  0.08 mm at ( 277.79, -72.47) z  -0.350..  2.150,  0.006 mm^2 in plan, 0.09 x 0.14
  0.08 mm at ( 277.32, -71.18) z   2.150..  2.341,  0.008 mm^2 in plan, 0.12 x 0.15
  0.08 mm at ( 279.18, -72.45) z   2.350..  4.400,  0.007 mm^2 in plan, 0.11 x 0.15
  0.09 mm at ( 279.18, -72.45) z  -1.500..  2.341,  0.007 mm^2 in plan, 0.11 x 0.14
  0.10 mm at ( 277.27, -47.71) z   2.550..  4.400,  0.010 mm^2 in plan, 0.18 x 0.12
  0.10 mm at ( 277.62, -47.71) z   4.400..  4.600,  0.009 mm^2 in plan, 0.17 x 0.11
  0.10 mm at ( 275.36, -47.71) z   1.650..  2.341,  0.007 mm^2 in plan, 0.12 x 0.11
  0.11 mm at ( 279.16, -50.11) z   4.600..  6.430,  0.011 mm^2 in plan, 0.13 x 0.14
  0.11 mm at ( 179.21, -49.55) z   2.350..  3.295,  0.017 mm^2 in plan, 0.24 x 0.16
  0.11 mm at ( 279.16, -69.09) z   4.600..  6.430,  0.011 mm^2 in plan, 0.13 x 0.14
  0.13 mm at ( 179.21, -49.54) z   2.150..  2.341,  0.017 mm^2 in plan, 0.24 x 0.16
  0.17 mm at ( 164.01, -47.74) z   2.350..  4.150,  0.021 mm^2 in plan, 0.25 x 0.17
  0.17 mm at ( 164.01, -47.74) z  -1.500..  2.341,  0.021 mm^2 in plan, 0.25 x 0.17
  0.17 mm at ( 216.70, -96.32) z   2.350..  2.450,  0.029 mm^2 in plan, 0.35 x 0.19
  0.17 mm at ( 221.70, -96.32) z   2.350..  2.450,  0.029 mm^2 in plan, 0.35 x 0.19
  0.17 mm at ( 216.70, -96.31) z   2.150..  2.341,  0.029 mm^2 in plan, 0.35 x 0.19
  0.17 mm at ( 221.70, -96.31) z   2.150..  2.341,  0.029 mm^2 in plan, 0.35 x 0.19
  0.17 mm at ( 220.26, -96.31) z   2.150..  2.341,  0.029 mm^2 in plan, 0.35 x 0.19
  0.17 mm at ( 220.26, -96.32) z   2.350..  2.450,  0.029 mm^2 in plan, 0.35 x 0.19
  0.20 mm at ( 248.00, -48.90) z   1.650..  2.150,  0.034 mm^2 in plan, 0.34 x 0.29
  0.22 mm at ( 220.95,-127.48) z   3.650.. 10.500,  0.250 mm^2 in plan, 1.30 x 1.25
  0.22 mm at ( 174.28, -49.39) z   2.350..  3.450,  0.108 mm^2 in plan, 0.97 x 0.45
  0.23 mm at ( 156.56,-124.27) z   3.650.. 10.500,  0.186 mm^2 in plan, 0.73 x 1.43
  0.23 mm at ( 166.76,-142.14) z   3.650.. 10.500,  0.186 mm^2 in plan, 1.43 x 0.73
  0.23 mm at ( 255.62, -69.11) z   3.650..  6.430,  0.062 mm^2 in plan, 0.68 x 0.34
  0.24 mm at ( 162.46,-120.45) z   3.650.. 10.500,  0.065 mm^2 in plan, 0.69 x 0.55
  0.30 mm at ( 176.78, -51.36) z   1.600..  2.150,  0.140 mm^2 in plan, 0.50 x 0.34
  0.30 mm at ( 250.98, -51.36) z   1.600..  2.150,  0.140 mm^2 in plan, 0.50 x 0.34
  0.33 mm at ( 273.71,-100.36) z   2.150..  2.341,  1.121 mm^2 in plan, 6.21 x 1.28
  0.33 mm at ( 273.71,-100.36) z   2.350..  2.450,  1.121 mm^2 in plan, 6.21 x 1.28
  0.35 mm at ( 221.45, -43.67) z  -1.500..  1.600,  0.304 mm^2 in plan, 1.35 x 0.36
  0.40 mm at ( 212.89, -98.97) z   2.150..  2.341,  0.345 mm^2 in plan, 0.42 x 1.14
  0.40 mm at ( 212.89, -98.97) z   2.350..  2.450,  0.345 mm^2 in plan, 0.42 x 1.14
  0.40 mm at ( 277.62, -49.60) z   4.400..  4.600,  0.147 mm^2 in plan, 0.38 x 1.06
  0.49 mm at ( 181.02, -55.90) z   3.650..  6.430,  0.321 mm^2 in plan, 0.88 x 0.51
  0.53 mm at ( 188.13, -47.95) z   4.350..  5.095,  0.834 mm^2 in plan, 2.60 x 0.59
  0.57 mm at ( 184.96, -47.95) z   4.350..  6.430,  4.704 mm^2 in plan, 9.14 x 0.59
  0.62 mm at ( 287.97,-108.73) z  -1.500..  2.150,  0.119 mm^2 in plan, 0.67 x 0.41
  0.62 mm at ( 288.47,-105.96) z  -1.500..  2.150,  0.119 mm^2 in plan, 0.68 x 0.41
  0.68 mm at ( 257.35, -69.27) z   3.650..  9.000,  1.363 mm^2 in plan, 3.07 x 0.90
  0.68 mm at ( 246.27,-119.68) z   3.650..  9.000,  0.413 mm^2 in plan, 0.71 x 0.85
  0.74 mm at ( 240.39, -54.68) z   3.650..  3.700,  1.280 mm^2 in plan, 2.56 x 0.76
  0.77 mm at ( 185.89, -55.76) z   3.650..  6.430,  4.979 mm^2 in plan, 6.91 x 0.78
../outputs/TOTEM_alu_bottom_R.step: 37 walls thinner than 0.8 mm
  0.08 mm at ( 242.87, -52.13) z  -1.310.. -0.550,  0.010 mm^2 in plan, 0.11 x 0.23
  0.08 mm at ( 277.77, -50.08) z   2.150..  4.200,  0.006 mm^2 in plan, 0.09 x 0.13
  0.08 mm at ( 243.15, -50.62) z  -1.310.. -0.550,  0.010 mm^2 in plan, 0.11 x 0.23
  0.11 mm at ( 279.17, -50.11) z   1.085..  4.200,  0.011 mm^2 in plan, 0.13 x 0.14
  0.11 mm at ( 279.16, -69.09) z   1.085..  4.200,  0.011 mm^2 in plan, 0.13 x 0.14
  0.12 mm at ( 239.12, -47.76) z   0.635..  1.167,  0.039 mm^2 in plan, 0.38 x 0.21
  0.14 mm at ( 232.70, -48.99) z  -2.554.. -1.710,  0.026 mm^2 in plan, 0.21 x 0.26
  0.19 mm at ( 247.30, -48.25) z   0.635..  2.150,  0.781 mm^2 in plan, 1.19 x 1.20
  0.24 mm at ( 260.85,-124.47) z  -1.700.. -0.550,  0.154 mm^2 in plan, 1.57 x 0.26
  0.28 mm at ( 188.11, -55.97) z  -1.500.. -0.550,  0.449 mm^2 in plan, 3.23 x 1.22
  0.30 mm at ( 198.99,-121.02) z  -2.554.. -1.710,  0.015 mm^2 in plan, 0.18 x 0.19
  0.30 mm at ( 198.99,-121.02) z  -1.700.. -0.550,  0.015 mm^2 in plan, 0.18 x 0.19
  0.34 mm at ( 221.45, -43.67) z  -2.554.. -1.710,  0.302 mm^2 in plan, 1.34 x 0.35
  0.42 mm at ( 231.48,-102.76) z  -2.554.. -1.710,  0.288 mm^2 in plan, 0.86 x 0.44
  0.42 mm at ( 231.48,-102.76) z  -1.700.. -0.550,  0.288 mm^2 in plan, 0.86 x 0.44
  0.43 mm at ( 221.49, -95.99) z  -1.500.. -0.550,  0.344 mm^2 in plan, 1.01 x 0.74
  0.44 mm at ( 267.98,-108.08) z  -2.554.. -1.710,  0.217 mm^2 in plan, 0.49 x 0.96
  0.44 mm at ( 267.98,-108.08) z  -1.700.. -1.500,  0.217 mm^2 in plan, 0.49 x 0.96
  0.44 mm at ( 267.98,-108.08) z  -1.310.. -0.550,  0.217 mm^2 in plan, 0.49 x 0.96
  0.53 mm at ( 241.29, -53.06) z  -1.310.. -0.550,  0.413 mm^2 in plan, 1.35 x 1.04
  0.53 mm at ( 180.74,-126.77) z  -2.554.. -1.710,  0.277 mm^2 in plan, 0.63 x 0.74
  0.53 mm at ( 180.74,-126.77) z  -1.700.. -0.550,  0.277 mm^2 in plan, 0.63 x 0.74
  0.54 mm at ( 191.88,-128.48) z  -1.700.. -0.550,  0.412 mm^2 in plan, 1.59 x 0.59
  0.56 mm at ( 210.37,-125.79) z  -1.700.. -0.550,  0.443 mm^2 in plan, 1.61 x 0.59
  0.56 mm at ( 231.71, -90.59) z  -2.554.. -1.710,  0.476 mm^2 in plan, 0.60 x 1.70
  0.56 mm at ( 231.71, -90.59) z  -1.700.. -0.550,  0.476 mm^2 in plan, 0.60 x 1.70
  0.56 mm at ( 231.71, -73.59) z  -2.554.. -1.710,  0.476 mm^2 in plan, 0.60 x 1.70
  0.56 mm at ( 231.71, -73.59) z  -1.700.. -0.550,  0.476 mm^2 in plan, 0.60 x 1.70
  0.56 mm at ( 164.20,-133.54) z  -1.700.. -0.550,  0.476 mm^2 in plan, 0.85 x 1.67
  0.56 mm at ( 285.28,-112.72) z  -1.700.. -0.550,  0.477 mm^2 in plan, 0.87 x 1.67
  0.57 mm at ( 206.52,-105.65) z  -2.554.. -1.710,  0.209 mm^2 in plan, 0.64 x 0.71
  0.57 mm at ( 206.52,-105.65) z  -1.700.. -0.550,  0.209 mm^2 in plan, 0.64 x 0.71
  0.57 mm at ( 180.00, -48.39) z  -1.500..  3.950,  5.371 mm^2 in plan, 9.94 x 1.47
  0.57 mm at ( 209.67,-107.23) z  -1.700.. -0.550,  0.209 mm^2 in plan, 0.64 x 0.71
  0.57 mm at ( 209.66,-107.24) z  -2.554.. -1.710,  0.209 mm^2 in plan, 0.64 x 0.71
  0.58 mm at ( 175.57,-135.21) z  -1.700.. -0.550,  0.515 mm^2 in plan, 1.78 x 0.88
  0.59 mm at ( 214.60, -97.12) z  -1.500.. -0.550,  0.713 mm^2 in plan, 1.11 x 1.65
```

```
top L grid points with a layer < 0.8 mm: 209 min layer 0.45
  thin spot around (120.2,-56.3) span 0.2x0.0 min 0.52 mm  n=2
  thin spot around (127.2,-56.3) span 0.2x0.0 min 0.52 mm  n=2
  thin spot around (87.1,-96.8) span 2.0x1.0 min 0.52 mm  n=37
  thin spot around (93.2,-98.1) span 3.8x4.0 min 0.52 mm  n=82
  thin spot around (33.8,-99.6) span 5.7x1.5 min 0.45 mm  n=69
  thin spot around (49.4,-69.9) span 3.0x0.5 min 0.52 mm  n=17
bottom L grid points with a layer < 0.8 mm: 46 min layer 0.004
  thin spot around (18.6,-101.4) span 0.0x1.8 min 0.78 mm  n=8
  thin spot around (131.2,-52.6) span 1.2x1.2 min 0.80 mm  n=32
  thin spot around (119.9,-131.9) span 0.8x0.2 min 0.00 mm  n=2
  thin spot around (130.6,-136.8) span 0.0x0.0 min 0.01 mm  n=1
  thin spot around (128.8,-135.8) span 0.0x0.0 min 0.28 mm  n=1
  thin spot around (124.8,-133.8) span 0.0x0.0 min 0.23 mm  n=1
  thin spot around (107.6,-128.8) span 0.0x0.0 min 0.01 mm  n=1
top R grid points with a layer < 0.8 mm: 216 min layer 0.45
  thin spot around (189.2,-56.3) span 0.5x0.0 min 0.52 mm  n=3
  thin spot around (182.2,-56.3) span 0.5x0.0 min 0.52 mm  n=3
  thin spot around (274.1,-99.6) span 6.0x1.5 min 0.45 mm  n=69
  thin spot around (258.4,-69.9) span 3.0x0.5 min 0.52 mm  n=16
  thin spot around (221.0,-96.8) span 2.0x1.0 min 0.52 mm  n=38
  thin spot around (214.8,-98.0) span 3.8x4.0 min 0.52 mm  n=86
  thin spot around (191.4,-129.3) span 0.0x0.0 min 0.52 mm  n=1
bottom R grid points with a layer < 0.8 mm: 37 min layer 0.653
  thin spot around (287.2,-105.3) span 0.2x1.0 min 0.65 mm  n=6
  thin spot around (176.8,-52.7) span 1.2x1.2 min 0.80 mm  n=31
```

## 3-axis machining with a Ø2 mm flat end mill

Every part was projected on a 0.05 mm grid from above and from below (two setups), using exact
triangles for planar faces and closed tessellation for curved faces, with balanced crossings.
On each side the
surface a Ø2 mm flat end mill leaves is the grey-level closing of the part's height map by a 1 mm
disc; any spot where the part lies deeper than that (material the mill can't remove: a slot
narrower than 2 mm, an inside corner sharper than R1, a pocket hidden under an overhang) is
counted if it is more than 0.03 mm deep. The screw holes are drilled (Ø2.4 in the top, Ø1.6 tap drill in the bottom) and not counted. Tilted and curved faces outside the countersinks (cut
with the same flat end mill on 3D toolpaths) are reported as their area; the test above already
covers them. Pictures: `work/mach_*.png`.

```
../outputs/TOTEM_alu_top_L.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, 3D surfaces outside the countersinks (3D toolpaths): 0.00 mm²
../outputs/TOTEM_alu_bottom_L.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, 3D surfaces outside the countersinks (3D toolpaths): 202.74 mm²
../outputs/TOTEM_wood_window_insert_L.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, 3D surfaces outside the countersinks (3D toolpaths): 0.00 mm²
../outputs/TOTEM_alu_top_R.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, 3D surfaces outside the countersinks (3D toolpaths): 0.00 mm²
../outputs/TOTEM_alu_bottom_R.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, 3D surfaces outside the countersinks (3D toolpaths): 203.05 mm²
../outputs/TOTEM_wood_window_insert_R.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, 3D surfaces outside the countersinks (3D toolpaths): 0.00 mm²
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
