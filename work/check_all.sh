#!/bin/bash
set -euo pipefail
# Re-run every check on the files in ../outputs and rewrite ../outputs/CHECKS.md (about 30 min with
# 8 jobs; JOBS=1 runs them one by one, about 70 min).
# PYTHON: an interpreter with cadquery, trimesh, shapely, contourpy, matplotlib, scipy, rtree.
# The parts themselves: ref_extract.py (once) -> model.py all L, model.py all R.
# Each check runs per half (or per part) as its own job; the outputs are joined in the old order
# (left before right, top / bottom / insert). Each job's time goes to check_timing.log.
cd "$(dirname "$0")"
P=${PYTHON:-python3}
J=${JOBS:-8}
: > check_timing.log
mkdir -p check_parts
O=check_parts
step() { local name=$1; shift
  while [ "$(jobs -rp | wc -l)" -ge "$J" ]; do wait -n || true; done
  ( t0=$SECONDS; echo "$name ..." >&2
    if bash -c "$*"; then echo "$name $(( SECONDS - t0 ))s" | tee -a check_timing.log >&2
    else echo "$name FAILED after $(( SECONDS - t0 ))s" | tee -a check_timing.log >&2; fi ) & }
# the longest first
for s in L R; do
  step verify_$s "$P -E -s verify.py $s > $O/verify_$s.log 2>&1"
  step fit_check_$s "$P -E -s fit_check.py $s > $O/fit_check_$s.log 2>&1"
  step seam_machined_$s "$P -E -s seam_machined.py $s 2>&1 | grep -v Warn > $O/seam_machined_$s.txt"
done
# 3-axis, Ø2 mm flat end mill (3D toolpaths), from above and below (screw holes are drilled)
for s in L R; do
  for p in top bottom; do
    step machinable_${p}_$s "$P -E -s machinable.py ../outputs/TOTEM_alu_${p}_$s.step 2 --drill $s --png mach_${p}_$s.png 2>&1 | grep -v Warn > $O/machinable_${p}_$s.txt"
  done
  step machinable_insert_$s "$P -E -s machinable.py ../outputs/TOTEM_wood_window_insert_$s.step 2 2>&1 | grep -v Warn > $O/machinable_insert_$s.txt"
done
# the parts against the previous accepted ones (prev_*.step: the clean 2.5D rebuild), column by column
for s in L R; do for p in top bottom; do
  step clean_diff_${p}_$s "$P -E -s diff_mesh.py prev_${p}_$s.step ../outputs/TOTEM_alu_${p}_$s.step 0.05 2>&1 | grep -v Warn | sed 's/^/$p $s: /' > $O/clean_diff_${p}_$s.txt"
  step walls_${p}_$s "$P -E -s walls.py ../outputs/TOTEM_alu_${p}_$s.step 2>&1 | grep -v Warn > $O/walls_${p}_$s.txt"
done; done
for s in L R; do
  step heightmaps_render3d_$s "$P -E -s heightmaps.py $s > /dev/null 2>&1; $P -E -s render3d.py $s > /dev/null 2>&1"
  step thin_$s "for p in top bottom otop obottom; do $P -E -s thin.py $s \$p 2>/dev/null | grep -v Warn > thin_\${p}_$s.txt; done"
  step through_$s "$P -E -s through.py $s 2>&1 | grep -v Warn | sed -n '/^new/,\$p' > $O/through_$s.txt"
done
step argan_all "$P -E -s argan_all.py > argan_all.log 2>&1"
step render_v "$P -E -s render_v.py ../outputs/TOTEM_alu_top_L.step ../outputs/TOTEM_alu_bottom_L.step v_new_L.png 'y-62.6,y-112,y-52.7,x103.1,x57,x45' > /dev/null 2>&1"
step reset_back "$P -E -s reset_back.py > /dev/null 2>&1; cp reset_back.png ../outputs/reset_back.png"
step under_cmp "$P -E -s under_cmp.py > /dev/null 2>&1"
step export_view "$P -E -s export_view.py > /dev/null 2>&1 && $P -E -s pack_png.py > /dev/null 2>&1"
wait
cat $O/verify_L.log $O/verify_R.log > verify.log
cat $O/fit_check_L.log $O/fit_check_R.log > fit_check.log
cat $O/seam_machined_L.txt $O/seam_machined_R.txt > seam_machined.txt
cat $O/machinable_{top,bottom,insert}_L.txt $O/machinable_{top,bottom,insert}_R.txt > machinable.txt
cat $O/clean_diff_{top,bottom}_L.txt $O/clean_diff_{top,bottom}_R.txt > clean_diff.txt
cat $O/walls_{top,bottom}_L.txt $O/walls_{top,bottom}_R.txt > walls.txt
cat $O/through_L.txt $O/through_R.txt > through.txt
J=1 step write_checks "$P -E -s write_checks.py > write_checks.log 2>&1"
wait
if grep -q FAILED check_timing.log; then grep FAILED check_timing.log >&2; exit 1; fi
echo checks done
