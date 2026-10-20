# Checks (measured on the final STEP files)

Distances are exact (OpenCASCADE BRepExtrema) between each case part and the KiCad board
(1.6 mm, true outline), every KiCad 3D part on that half, and every exposed copper pad.

| | Left | Right | Original (left) |
|---|---|---|---|
| Top to PCB (outside the 4 floating pads) | 0.53 mm | 0.50 mm | 0.10 mm |
| Bottom to PCB | 0.53 mm | 0.53 mm | 0.35 mm |
| Top to nearest part (switch bodies and diodes aside) | 0.50 mm | 0.50 mm |  |
| Top to diode epoxy (insulator) | 0.37 mm | 0.37 mm |  |
| Bottom to nearest part (sockets, contacts, pins) | 0.50 mm | 0.50 mm |  |
| Top to XIAO | 0.50 mm | 0.50 mm |  |
| Bottom to XIAO | 0.50 mm | 0.50 mm |  |
| Wood insert to XIAO | 1.57 mm | 1.57 mm |  |
| Top to exposed pads | 0.80 mm | 0.80 mm |  |
| Bottom to exposed pads | 0.51 mm | 0.51 mm |  |
| Top/bottom seam gap | 0.15 mm | 0.15 mm |  |

Reset switch: its metal body keeps 0.5 mm; its plastic plunger sits in the original round hole (plunger to top/bottom [0.2, 0.122] mm, as designed).

Top/bottom overlap: 0.0 / 0.0 mm³.
The top never touches the floating mounting pads either: it stays 0.1 mm above them, as in the original.

## Sizes

- L top: [133.11, 99.01, 12.0, 'z', -1.5, 10.5], valid/solids/volume [True, 1, 17136.2]
- L bottom: [133.13, 99.02, 15.6, 'z', -11.4, 4.2], valid/solids/volume [True, 1, 69885.8]
- L insert: [21.5, 17.0, 3.0, 'z', 7.5, 10.5], valid/solids/volume [True, 1, 917.4]
- R top: [133.1, 99.01, 12.0, 'z', -1.5, 10.5], valid/solids/volume [True, 1, 17146.4]
- R bottom: [133.12, 99.02, 15.59, 'z', -11.4, 4.19], valid/solids/volume [True, 1, 69876.6]
- R insert: [21.5, 17.0, 3.0, 'z', 7.5, 10.5], valid/solids/volume [True, 1, 919.7]

## Solid checks

```
TOTEM_alu_top_L valid True solids 1 shells 1 closed True analyzer: {'BOPAlgo_InvalidCurveOnSurface': 8}
TOTEM_alu_top_R valid True solids 1 shells 1 closed True analyzer: {'BOPAlgo_InvalidCurveOnSurface': 8}
TOTEM_alu_bottom_L valid True solids 1 shells 1 closed True analyzer: {'BOPAlgo_InvalidCurveOnSurface': 9}
TOTEM_alu_bottom_R valid True solids 1 shells 1 closed True analyzer: {'BOPAlgo_SelfIntersect': 3, 'BOPAlgo_InvalidCurveOnSurface': 8}
TOTEM_wood_window_insert_L valid True solids 1 shells 1 closed True analyzer: {}
TOTEM_wood_window_insert_R valid True solids 1 shells 1 closed True analyzer: {}
```

`InvalidCurveOnSurface` is a tolerance note normal after a STEP round trip. The few `SelfIntersect`
flags on the bottoms are near-zero-area facets inherited from the site's mesh conversion; the
original bottoms carry more of them (see `work/argan_cmp.log`).

## Holes through the bottom

Every vertical line through each bottom was ray-cast (0.25 mm grid). The only openings through
the part are the screw holes; no socket pocket breaks through into the leg recesses any more
(see `underside_holes.png`):

```
new L through-openings: 4
  (  56.99,  -52.71)  2.00x 2.00 area   2.7  underside around: -1.40..-0.51
  ( 131.22,  -52.75)  2.00x 1.75 area   2.7  underside around: -1.40..-0.50
  ( 139.48, -112.02)  2.00x 1.75 area   2.8  underside around: -1.45..-0.53
  (  34.29, -121.02)  1.75x 1.75 area   2.8  underside around: -1.40..-0.69
new R through-openings: 4
  ( 176.79,  -52.75)  2.00x 1.75 area   2.8  underside around: -1.41..-0.56
  ( 250.96,  -52.76)  1.75x 1.75 area   2.8  underside around: -1.44..-0.52
  ( 168.45, -112.02)  1.75x 1.75 area   2.8  underside around: -1.42..-0.68
  ( 273.66, -121.02)  1.75x 1.75 area   2.7  underside around: -1.40..-0.50
```

## Thin walls compared with the original

- L top: (49.7,-69.8) 0.55 mm (new); (87.1,-97.0) 0.55 mm (new); (93.1,-98.2) 0.55 mm (new)
- L bottom: no new or thinner spots (clusters of 5+ samples, 0.25 mm grid)
- R top: (220.9,-97.0) 0.55 mm (new); (214.8,-98.2) 0.55 mm (new); (258.0,-69.7) 0.55 mm (new)
- R bottom: no new or thinner spots (clusters of 5+ samples, 0.25 mm grid)

## Pictures

- `heightmap_L.png`, `heightmap_R.png`: gap from the PCB faces, before and after
- `render3d_L.png`, `render3d_R.png`: the new parts
- `sections_L.png`: cross-sections through the assembly
- `reset_back.png`: back face around the reset button, original vs new (unchanged)
- `underside_holes.png`: the bottoms seen from below, site original vs now (holes through the part)
