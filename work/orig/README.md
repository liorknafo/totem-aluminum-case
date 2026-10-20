# TOTEM cases — current live site

Four STEP case parts corresponding to the current site:
https://totem-assembled.liorknafo.chatgpt.site/

## Files

- `TOTEM_tenting_live_bottom_L.step` — left tenting bottom from the live site.
- `TOTEM_tenting_live_bottom_R.step` — right tenting bottom from the live site.
- `TOTEM_case_ble_top_L_V.08.step` — original left BLE top.
- `TOTEM_case_ble_top_R_V.08.step` — original right BLE top.

Units: millimetres. Native assembly coordinates are preserved; the viewer's extra left/right display separation is not applied. Case parts only; no batteries, PCB, switches, keycaps or separate tenting legs.

## Geometry and limitations

**The bottoms are faceted CAD solids converted from the live site's triangle meshes.** They retain the current lowered tenting mounts and recessed leg pockets. The site stores reduced mesh geometry with vertex coordinates quantized to 0.01 mm; it does not provide the latest native STEP models or editable feature history. This conversion does not restore the original smooth curves or precision lost when the visualization was made.

The tops are the original smooth STEP models from GEIGEIGEIST/TOTEM, identified by the shared task's assembly script and checked against the live visualization.

The shared task at https://chatgpt.com/s/cx_6aaf117e5cd88191955aa5ca795c0a82 contains an earlier bottom design. Reconstructed files for that earlier version are **not** included here. The exports instead use site version 3, whose final change was “Restore recessed leg pockets at lowered case bottom.”

## Validation and mesh repairs

All four STEP files were reopened and confirmed to contain one valid solid with closed shells. Coplanar triangles were merged, and both bottom solids were successfully tessellated again. Sampled bottom-mesh vertices differ from the exported surfaces by at most 0.0071 mm. Surface comparison results and checksums are in `validation.json`.

For the bottom conversion, degenerate/duplicate triangles and detached negligible-volume seam artifacts were removed. Left-bottom faces were stitched with a 0.00001 mm tolerance. Right-bottom faces were stitched with a 0.015 mm tolerance, and one missing planar triangle with an area of 0.0326 mm² was closed at Z = −2.2 mm. These repairs make the visualization geometry importable as closed CAD solids.

Physical fit and printing have not been tested. The site's nominal battery is 35 × 53 × 5 mm.

## Provenance and attribution

Source site version 3, commit `8647a0adef919b804c4eb7499c17dd67c0e5abae`.
Original top STEP files: https://github.com/GEIGEIGEIST/TOTEM at revision `410e566dd47466c0b69279f0d4b3646998c663d4`.

Original TOTEM design: Copyright (c) 2022 GEIST. The original CERN Open Hardware Licence Version 2 – Permissive is included in `LICENSE.md`.

Modification/export date: 2026-09-20. The bottoms contain the site's battery enlargement, lowered tenting mounts and recessed leg-pocket modifications. This export converts those meshes to faceted boundary-representation solids with the repairs described above. The two top STEP files are unchanged originals.
