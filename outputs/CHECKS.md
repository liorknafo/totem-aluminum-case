# Checks (measured on the final STEP files)

Distances are exact (OpenCASCADE BRepExtrema) between each case part and the KiCad board
(1.6 mm, true outline), every KiCad 3D part on that half, and every exposed copper pad.

| | Left | Right | Original (left) |
|---|---|---|---|
| Top to PCB (outside the 4 floating pads) | 0.53 mm | 0.52 mm | 0.10 mm |
| Bottom to PCB | 0.54 mm | 0.53 mm | 0.35 mm |
| Top to nearest part (switch bodies and diodes aside) | 0.50 mm | 0.50 mm |  |
| Top to diode epoxy (insulator) | 0.37 mm | 0.37 mm |  |
| Bottom to nearest part (sockets, contacts, pins) | 0.51 mm | 0.51 mm |  |
| Top to XIAO | 0.50 mm | 0.50 mm |  |
| Bottom to XIAO | 0.50 mm | 0.50 mm |  |
| Wood insert to XIAO | 1.57 mm | 1.57 mm |  |
| Top to exposed pads | 0.80 mm | 0.80 mm |  |
| Bottom to exposed pads | 0.51 mm | 0.51 mm |  |
| Top/bottom seam gap | 0.20 mm | 0.20 mm |  |

Reset switch: its metal body keeps 0.5 mm; its plastic plunger sits in the original round hole (plunger to top/bottom [0.2, 0.137] mm, as designed).

Top/bottom overlap: 0.0 / 0.0 mm³.
The top never touches the floating mounting pads either: it stays 0.1 mm above them, as in the original.

## Sizes

- L top: [133.11, 99.01, 12.0, 'z', -1.5, 10.5], valid/solids/volume [True, 1, 17434.8]
- L bottom: [133.11, 99.01, 15.39, 'z', -11.4, 3.99], valid/solids/volume [True, 1, 69741.1]
- L insert: [21.5, 17.0, 3.0, 'z', 7.5, 10.5], valid/solids/volume [True, 1, 916.8]
- R top: [133.1, 99.01, 12.0, 'z', -1.5, 10.5], valid/solids/volume [True, 1, 17439.6]
- R bottom: [133.1, 99.01, 15.39, 'z', -11.4, 3.99], valid/solids/volume [True, 1, 69729.9]
- R insert: [21.5, 17.0, 3.0, 'z', 7.5, 10.5], valid/solids/volume [True, 1, 919.2]

## Solid checks

```
TOTEM_alu_top_L valid True solids 1 shells 1 closed True analyzer: {'BOPAlgo_SelfIntersect': 10, 'BOPAlgo_TooSmallEdge': 8, 'BOPAlgo_InvalidCurveOnSurface': 3}
TOTEM_alu_top_R valid True solids 1 shells 1 closed True analyzer: {'BOPAlgo_TooSmallEdge': 6, 'BOPAlgo_InvalidCurveOnSurface': 3}
TOTEM_alu_bottom_L valid True solids 1 shells 1 closed True analyzer: {'BOPAlgo_SelfIntersect': 116}
TOTEM_alu_bottom_R valid True solids 1 shells 1 closed True analyzer: {'BOPAlgo_SelfIntersect': 63}
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
  (  56.98,  -52.70)  2.00x 2.00 area   2.8  underside around: -1.41..-0.54
  ( 131.16,  -52.74)  2.00x 1.75 area   2.8  underside around: -1.43..-0.50
  ( 139.49, -112.00)  2.00x 1.75 area   2.7  underside around: -1.41..-0.55
  (  34.31, -121.01)  1.75x 1.75 area   2.8  underside around: -1.41..-0.68
new R through-openings: 5
  ( 176.77,  -52.74)  2.00x 1.75 area   2.7  underside around: -1.41..-0.50
  ( 250.97,  -52.75)  1.75x 1.75 area   2.8  underside around: -1.44..-0.54
  ( 286.45, -106.76)  0.25x 1.75 area   0.4  underside around: -3.66..-3.20
  ( 168.45, -112.01)  1.75x 1.75 area   2.8  underside around: -1.41..-0.69
  ( 273.63, -121.03)  2.00x 1.75 area   2.7  underside around: -1.40..-0.53
```

## Thin walls compared with the original

- L top: (49.4,-69.9) 0.52 mm (new); (87.1,-96.8) 0.52 mm (new); (93.1,-98.0) 0.52 mm (new)
- L bottom: (133.0,-138.1) 0.55 mm (new)
- R top: (221.0,-96.8) 0.52 mm (new); (214.8,-98.0) 0.52 mm (new); (258.4,-69.9) 0.52 mm (new)
- R bottom: no new or thinner spots (clusters of 5+ samples, 0.25 mm grid)

## 3-axis machining with a Ø2 mm flat end mill

Every part was projected on a 0.05 mm grid from above and from below (two setups), using exact
triangles for planar faces and closed tessellation for curved faces, with balanced crossings.
On each side the
surface a Ø2 mm flat end mill leaves is the grey-level closing of the part's height map by a 1 mm
disc; any spot where the part lies deeper than that (material the mill can't remove: a slot
narrower than 2 mm, an inside corner sharper than R1, a pocket hidden under an overhang) is
counted if it is more than 0.03 mm deep. The screw holes are drilled (Ø2.0 neck in the top, Ø2.16 in
the bottom) and not counted. Tilted faces outside the countersinks are reported separately;
they must be horizontal or vertical for a strict 2.5D result. On the tops they are hairline curved
transitions (≈0.9 mm²); on the bottoms they are facets tilted by less than 0.01° (rounding in the mesh
booleans, under 0.002 mm across a wall) apart from 0.02 mm² of microscopic facets. Pictures: `work/mach_*.png`.

```
../outputs/TOTEM_alu_top_L.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, sloped faces outside the countersinks: 0.93 mm²
../outputs/TOTEM_alu_bottom_L.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, sloped faces outside the countersinks: 20.23 mm²
../outputs/TOTEM_wood_window_insert_L.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, sloped faces outside the countersinks: 0.00 mm²
../outputs/TOTEM_alu_top_R.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, sloped faces outside the countersinks: 0.94 mm²
../outputs/TOTEM_alu_bottom_R.step: tool Ø2: 0 spots the mill cannot cut, undercut columns: 0, sloped faces outside the countersinks: 32.86 mm²
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
