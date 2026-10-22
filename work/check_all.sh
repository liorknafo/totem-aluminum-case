#!/bin/bash
set -euo pipefail
# Re-run every check on the files in ../outputs and rewrite ../outputs/CHECKS.md.
# PYTHON: an interpreter with cadquery, trimesh, shapely, contourpy, matplotlib, scipy, rtree.
cd "$(dirname "$0")"
P=${PYTHON:-python3}
$P -E -s argan_all.py > argan_all.log 2>&1
$P -E -s verify.py L R > verify.log 2>&1
for s in L R; do $P -E -s heightmaps.py $s > /dev/null 2>&1; $P -E -s render3d.py $s > /dev/null 2>&1; done
$P -E -s render_v.py ../outputs/TOTEM_alu_top_L.step ../outputs/TOTEM_alu_bottom_L.step v_new_L.png 'y-62.6,y-112,y-52.7,x103.1,x57,x45' > /dev/null 2>&1
$P -E -s reset_back.py > /dev/null 2>&1; cp reset_back.png ../outputs/reset_back.png
for s in L R; do for p in top bottom otop obottom; do $P -E -s thin.py $s $p 2>/dev/null | grep -v Warn > thin_${p}_$s.txt; done; done
(for s in L R; do $P -E -s through.py $s 2>&1 | grep -v Warn | sed -n '/^new/,$p'; done) > through.txt
$P -E -s under_cmp.py > /dev/null 2>&1
# 3-axis, Ø2 mm flat end mill, from above and below (screw holes are drilled)
(for s in L R; do for p in top bottom; do $P -E -s machinable.py ../outputs/TOTEM_alu_${p}_$s.step 2 --drill $s --png mach_${p}_$s.png 2>&1 | grep -v Warn; done
  $P -E -s machinable.py ../outputs/TOTEM_wood_window_insert_$s.step 2 2>&1 | grep -v Warn; done) > machinable.txt
$P -E -s fit_check.py L R > fit_check.log 2>&1
$P -E -s seam_machined.py L R 2>&1 | grep -v Warn > seam_machined.txt
$P -E -s write_checks.py > write_checks.log 2>&1
$P -E -s export_view.py > /dev/null 2>&1 && $P -E -s pack_png.py > /dev/null 2>&1
echo checks done
