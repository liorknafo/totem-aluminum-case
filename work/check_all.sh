#!/bin/sh
# Re-run every check on the STEP files in ../outputs, rewrite ../outputs/CHECKS.md, and remake the
# pictures (docs/images, outputs/*.png) and the 3D view.
# PYTHON: an interpreter with cadquery, numpy, shapely, scipy, trimesh, embreex, matplotlib, pillow, vtk.
set -e
cd "$(dirname "$0")"
P=${PYTHON:-python3}
$P -E -s check.py L R
$P -E -s report.py > /dev/null
$P -E -s render.py
$P -E -s maps.py
$P -E -s export_view.py
echo checks done
