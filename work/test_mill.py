"""Regression checks for mesh topology and closely spaced surface crossings."""
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import cadquery as cq
import numpy as np
import trimesh

import machinable
import mill
import fit2d
import clean
import build
import verify


class MeshTests(unittest.TestCase):
    def round_trip(self, mesh):
        solid = mill.mesh_to_solid(mesh)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'part.step'
            solid.exportStep(str(path), write_pcurves=False)
            back = cq.importers.importStep(str(path)).val()
        self.assertTrue(back.isValid())
        self.assertEqual(len(back.Solids()), 1)
        self.assertAlmostEqual(back.Volume(), mesh.volume, places=7)
        return back

    def test_line_contact_preserves_geometry(self):
        bounds = [[[0, 0, 0], [4, 4, 1]], [[0, 0, 1], [2, 2, 3]], [[2, 2, 1], [4, 4, 3]]]
        boxes = [trimesh.creation.box(bounds=b) for b in bounds]
        mesh = mill.mf_bool(boxes[0], boxes[1:], 'union')
        self.round_trip(mesh)

    def test_coplanar_patch_with_hole(self):
        outer = trimesh.creation.box(bounds=[[0, 0, 0], [10, 10, 4]])
        hole = trimesh.creation.box(bounds=[[2, 2, -1], [8, 8, 5]])
        mesh = mill.mf_bool(outer, [hole], 'difference')
        vertices, faces = trimesh.remesh.subdivide(mesh.vertices, mesh.faces)
        solid = self.round_trip(trimesh.Trimesh(vertices, faces, process=False))
        exact = mill.planar_mesh(solid)
        self.assertAlmostEqual(exact.volume, 256, places=7)
        self.assertAlmostEqual(exact.area, solid.Area(), places=7)

    def test_close_crossings_are_not_skipped(self):
        gap = 0.000044444
        boxes = [trimesh.creation.box(bounds=b) for b in
                 [[[0, 0, 0], [2, 2, 1]], [[0, 0, 1 + gap], [2, 2, 3]]]]
        mesh = trimesh.util.concatenate(boxes)
        top, bottom, length, count = machinable.projected_columns(mesh, np.array([0.3, 1.3]), np.array([0.4, 1.4]))
        np.testing.assert_allclose(top - bottom - length, gap, atol=1e-12)
        np.testing.assert_array_equal(count, 4)

    def test_missing_surface_is_rejected(self):
        mesh = trimesh.creation.box(bounds=[[0, 0, 0], [2, 2, 1]])
        mesh.update_faces(mesh.face_normals[:, 2] < 0.5)
        with self.assertRaisesRegex(AssertionError, 'unbalanced surface crossings'):
            machinable.projected_columns(mesh, np.array([0.3]), np.array([0.4]))

    def test_empty_column_can_be_cleared_from_two_sides(self):
        boxes = [cq.Solid.makeBox(1.75, 4, 1, cq.Vector(-2, -2, 0)),
                 cq.Solid.makeBox(1.75, 4, 1, cq.Vector(0.25, -2, 2)),
                 cq.Solid.makeBox(4, 0.5, 3, cq.Vector(-2, 1.5, 0))]
        solid = boxes[0].fuse(*boxes[1:]).clean()
        spots, undercuts = machinable.analyse(solid, quiet=True)
        self.assertEqual(undercuts, 0)
        self.assertTrue(all(spot['y'] > 1 for spot in spots))

    def test_slope_check_uses_true_surface_normals(self):
        cylinder = cq.Solid.makeCylinder(3, 4)
        notch = cq.Solid.makeBox(3, 2, 3, cq.Vector(1, -1, 1))
        self.assertAlmostEqual(machinable.sloped_area(cylinder.cut(notch)), 0, places=8)
        tilted = cq.Workplane().box(1, 1, 1).val().rotate((0, 0, 0), (1, 0, 0), 10)
        self.assertAlmostEqual(machinable.sloped_area(tilted), 4, places=8)

    def test_countersink_slope_is_exempt(self):
        cone = cq.Solid.makeCone(2, 1, 1)
        self.assertAlmostEqual(machinable.sloped_area(cone), 3 * np.pi * np.sqrt(2), delta=0.01)
        self.assertAlmostEqual(machinable.sloped_area(cone, [(0, 0, 2.4)]), 0, places=8)

    def test_clearance_distance_checks_solid_interior(self):
        small = cq.Workplane().box(1, 1, 1).val()
        apart = small.translate(cq.Vector(2, 0, 0))
        enclosing = cq.Workplane().box(4, 4, 4).val()
        self.assertAlmostEqual(verify.dist(small, apart)[0], 1, places=8)
        self.assertAlmostEqual(verify.dist(small, enclosing)[0], 0, places=8)

    def test_failed_validation_preserves_previous_file(self):
        solid = cq.Workplane().box(1, 1, 1).val()
        empty = cq.Compound.makeCompound([])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'part.step'
            path.write_text('previous checked file')
            with patch.object(build, 'heal_candidates', return_value=iter([('empty', empty)])):
                with self.assertRaises(AssertionError):
                    build.validate_step(solid, path, volume_tol=0.02, write_pcurves=False)
            self.assertEqual(path.read_text(), 'previous checked file')
            self.assertFalse(path.with_name('part.pending.step').exists())


class CleanTests(unittest.TestCase):
    def test_fit_recovers_lines_and_arcs(self):
        t = np.linspace(0, np.pi, 13)
        P = np.r_[np.c_[np.linspace(0, 10, 5), np.zeros(5)][:-1],
                  np.c_[10 + 1.05 * np.sin(t), 1.05 - 1.05 * np.cos(t)][:-1],
                  np.c_[np.linspace(10, 0, 5), np.full(5, 2.1)]]
        pr = fit2d.fit(P, 0.002)
        self.assertEqual([p[0] for p in pr], ['line', 'arc', 'line'])
        self.assertAlmostEqual(pr[1][4], 1.05, places=6)

    def test_no_arc_across_a_long_gap(self):
        # four points on a big circle, three of them bunched: an arc through them would bulge
        # far from the long chord
        a = np.radians([0, 1, 2, 60])
        P = 20 * np.c_[np.cos(a), np.sin(a)]
        self.assertTrue(all(p[0] == 'line' for p in fit2d.fit(P, 0.002)))

    def test_hole_radius_tapped_bottom_and_90_degree_countersinks(self):
        self.assertAlmostEqual(clean.hole_radius('top', 10.5), 2.15)      # Ø4.30 at the top face
        self.assertAlmostEqual(clean.hole_radius('top', 10.0), 1.65)      # 90°: 1:1
        self.assertAlmostEqual(clean.hole_radius('top', 5.0), 1.2)        # Ø2.4 pass-through
        self.assertAlmostEqual(clean.hole_radius('bottom', -3.0), 0.8)    # Ø1.6 tap drill
        self.assertEqual(clean.hole_radius('bottom', -9.0), 0.0)          # blind: solid underneath
        self.assertAlmostEqual(clean.build_hole_radius('bottom', -5.0), 2.15)

    def test_region_prisms_fuse_to_one_clean_solid(self):
        # two columns side by side sharing a wall, one with a round pocket from above
        import shapely.geometry as sg
        L = np.array([0.0, 1.0, 2.0])
        P = [sg.box(0, 0, 4, 4).difference(sg.Point(2, 2).buffer(1.2, quad_segs=32)), sg.Point(2, 2).buffer(1.2, quad_segs=32),
             sg.box(4, 0, 6, 4)]
        Lb = [(0, 1), (0, 0), (0, 0)]
        P, Lb = clean.tidy_regions(P, Lb, L, log=lambda *a: None)
        C, seg = clean.chains(P)
        faces, F = clean.checked_faces(P, C, seg, log=lambda *a: None)
        s = clean.fuse_all(clean.blocks(L, Lb, faces))
        self.assertTrue(s.isValid())
        self.assertEqual(len(s.Solids()), 1)
        self.assertAlmostEqual(s.Volume(), 16 * 2 - np.pi * 1.2 ** 2 + 8, delta=1e-3)
        self.assertTrue(any(f.geomType() == 'CYLINDER' for f in s.Faces()))

    def test_ledge_over_a_thin_well_floor_keeps_clear_of_parts(self):
        # a web (top 10.5) with a well floor beside it (plate 2.45..3.65); the round end of a
        # pocket from below pokes out from under the web, leaving 0.515 mm of floor over it
        import shapely.geometry as sg
        from shapely.ops import unary_union
        import build
        quiet = lambda *a: None
        disc = sg.Point(2, 2).buffer(1.0, quad_segs=32).intersection(sg.box(0, 2, 4, 10))
        P = [sg.box(0, 0, 4, 2), disc, sg.box(0, 2, 4, 10).difference(disc)]
        L = np.array([2.45, 3.135, 3.65, 10.5])
        Lb = [(1, 2), (1, 1), (0, 1)]
        part = build.box(0, 4, 3.5, 10, 3.65, 5.0)   # a switch housing standing on the floor
        L2, P2, Lb2 = clean.raise_floors(L, P, Lb, [(0.5, part)], log=quiet)
        cols = [(L2[b], L2[t + 1]) for b, t in Lb2]
        over = [c for q, c in zip(P2, cols) if q.intersection(disc).area > 1e-6]
        self.assertTrue(over and all(zt - zb >= 1.0 - 1e-6 for zb, zt in over))
        ledge = unary_union([q for q, (zb, zt) in zip(P2, cols) if 3.66 < zt < 10])
        self.assertAlmostEqual(max(zt for zb, zt in cols if 3.66 < zt < 10), 4.15)
        self.assertLessEqual(ledge.bounds[3], 3.0 + 1e-6)   # 0.5 mm from the part
        self.assertGreater(ledge.area, disc.area)


if __name__ == '__main__':
    unittest.main()
