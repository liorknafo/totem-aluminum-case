#!/bin/bash
set -euo pipefail
# Re-run every check on the files in ../outputs and rewrite ../outputs/CHECKS.md (about 50 min).
# PYTHON: an interpreter with cadquery, trimesh, shapely, contourpy, matplotlib, scipy, rtree.
# The parts themselves: build.py L/R -> clean.py --all.
# Each step's time goes to check_timing.log (and the terminal).
cd "$(dirname "$0")"
P=${PYTHON:-python3}
: > check_timing.log
step() { local name=$1; shift; local t0=$SECONDS
  echo "$name ..." >&2
  bash -c "$*"
  echo "$name $(( SECONDS - t0 ))s" | tee -a check_timing.log >&2; }
step argan_all "$P -E -s argan_all.py > argan_all.log 2>&1"
step verify "$P -E -s verify.py L R > verify.log 2>&1"
step heightmaps_render3d "for s in L R; do $P -E -s heightmaps.py \$s > /dev/null 2>&1; $P -E -s render3d.py \$s > /dev/null 2>&1; done"
step render_v "$P -E -s render_v.py ../outputs/TOTEM_alu_top_L.step ../outputs/TOTEM_alu_bottom_L.step v_new_L.png 'y-62.6,y-112,y-52.7,x103.1,x57,x45' > /dev/null 2>&1"
step reset_back "$P -E -s reset_back.py > /dev/null 2>&1; cp reset_back.png ../outputs/reset_back.png"
step thin "for s in L R; do for p in top bottom otop obottom; do $P -E -s thin.py \$s \$p 2>/dev/null | grep -v Warn > thin_\${p}_\$s.txt; done; done"
step walls "(for s in L R; do for p in top bottom; do $P -E -s walls.py ../outputs/TOTEM_alu_\${p}_\$s.step 2>&1 | grep -v Warn; done; done) > walls.txt"
step through "(for s in L R; do $P -E -s through.py \$s 2>&1 | grep -v Warn | sed -n '/^new/,\$p'; done) > through.txt"
step under_cmp "$P -E -s under_cmp.py > /dev/null 2>&1"
# 3-axis, Ø2 mm flat end mill (3D toolpaths), from above and below (screw holes are drilled)
step machinable "(for s in L R; do for p in top bottom; do $P -E -s machinable.py ../outputs/TOTEM_alu_\${p}_\$s.step 2 --drill \$s --png mach_\${p}_\$s.png 2>&1 | grep -v Warn; done
  $P -E -s machinable.py ../outputs/TOTEM_wood_window_insert_\$s.step 2 2>&1 | grep -v Warn; done) > machinable.txt"
# the published parts against the build's (before the clean CAD rebuild), column by column
step clean_diff "(for s in L R; do for p in top bottom; do $P -E -s diff_mesh.py final_\${p}_\$s.brep ../outputs/TOTEM_alu_\${p}_\$s.step 0.05 2>&1 | grep -v Warn | sed \"s/^/\$p \$s: /\"; done; done) > clean_diff.txt"
step fit_check "$P -E -s fit_check.py L R > fit_check.log 2>&1"
step seam_machined "$P -E -s seam_machined.py L R 2>&1 | grep -v Warn > seam_machined.txt"
step write_checks "$P -E -s write_checks.py > write_checks.log 2>&1"
step export_view "$P -E -s export_view.py > /dev/null 2>&1 && $P -E -s pack_png.py > /dev/null 2>&1"
echo checks done
