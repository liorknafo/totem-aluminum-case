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


if __name__ == '__main__':
    unittest.main()
