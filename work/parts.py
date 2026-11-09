"""The KiCad 3D parts (src/comp_all.step, exported from the board with x, -y coordinates) and the
copper pads (src/pads.step), named by footprint reference.

KiCad exports the board core as 1.51 mm thick with the top-side parts sitting on it; the real
board is 1.6 mm over copper and mask. Top-side geometry is lifted by PCB_T - KICAD_TOP so it sits
on the 1.6 mm board the case is built around.
"""
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path

import cadquery as cq
import numpy as np
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_LabelSequence
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool

from pcb import SPLIT_X

ROOT = Path(__file__).resolve().parent.parent
KICAD_TOP = 1.51
PCB_T = 1.6
LIFT = PCB_T - KICAD_TOP
ABOVE = 0.75          # geometry above this z (KiCad frame) sits on the top face


@lru_cache(maxsize=None)
def load_parts():
    """[(ref, side, shape)] for every part model in comp_all.step (KiCad frame, not lifted)."""
    doc = TDocStd_Document(TCollection_ExtendedString('d'))
    r = STEPCAFControl_Reader()
    r.SetNameMode(True)
    r.ReadFile(str(ROOT / 'src' / 'comp_all.step'))
    r.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    free = TDF_LabelSequence()
    st.GetFreeShapes(free)
    out = []
    for i in range(1, free.Length() + 1):
        comps = TDF_LabelSequence()
        st.GetComponents_s(free.Value(i), comps)
        for j in range(1, comps.Length() + 1):
            lab = comps.Value(j)
            n = TDataStd_Name()
            name = n.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), n) else '?'
            if name.startswith('=>') or name.endswith('_PCB'):
                continue
            shp = cq.Shape.cast(st.GetShape_s(lab))
            b = shp.BoundingBox()
            out.append((name, 'L' if (b.xmin + b.xmax) / 2 < SPLIT_X else 'R', shp))
    return out


def lifted(shape):
    """Top-side geometry on the 1.6 mm board."""
    return shape.translate(cq.Vector(0, 0, LIFT))


@lru_cache(maxsize=None)
def solids_of(ref, side):
    return tuple(s for n, sd, shp in load_parts() if n == ref and sd == side for s in shp.Solids())


def local_boxes(fp):
    """Boxes around the part's solids in the footprint frame (case-local a, b; z in the case frame,
    top-side portions lifted). Each solid is split into its portion below the board and its portion
    above it. Returns [dict(a0, a1, b0, b1, z0, z1, below, solid)]."""
    out = []
    for k, s in enumerate(solids_of(fp.ref, fp.side)):
        a, b, z = _local_points(fp, k, s)
        for below, m in ((True, z < ABOVE), (False, z >= ABOVE)):
            if m.sum() < 2:
                continue
            zz = z[m] + (0.0 if below else LIFT)
            e = TESS_TOL   # tessellation points lie on the surface; chords may cut inside by up to this
            out.append(dict(a0=a[m].min() - e, a1=a[m].max() + e, b0=b[m].min() - e, b1=b[m].max() + e,
                            z0=zz.min() - e, z1=zz.max() + e, below=below, solid=k))
    return out


TESS_TOL = 0.02
_LOCAL = {}


def _local_points(fp, k, s):
    """Surface points of a part solid in its footprint frame. Every instance of a footprint carries
    the same model, so the points are computed once per footprint type and solid."""
    key = (fp.lib, k, round(s.Volume(), 3))
    if key not in _LOCAL:
        v, _ = s.tessellate(TESS_TOL, 0.3)
        Pt = np.array([p.toTuple() for p in v] + [p.toTuple() for p in s.Vertices()])
        ang = -math.radians(fp.angle)
        ca, sa = math.cos(ang), math.sin(ang)
        d = Pt[:, :2] - np.array(fp.at)
        _LOCAL[key] = (d[:, 0] * ca - d[:, 1] * sa, d[:, 0] * sa + d[:, 1] * ca, Pt[:, 2])
    return _LOCAL[key]


CACHE = Path(__file__).resolve().parent / 'cache' / 'part_boxes.json'


def _sha(*paths):
    h = hashlib.sha256()
    for p in paths:
        h.update(Path(p).read_bytes())
    return h.hexdigest()


def lib_boxes(board):
    """local_boxes() for one footprint of every type (all instances of a footprint carry the same
    model in their own frame). Cached in work/cache/part_boxes.json, keyed by the hash of the board
    and the part models, so a build only reads the 3D models when they change."""
    key = _sha(ROOT / 'src' / 'comp_all.step', ROOT / 'src' / 'totem_0_3.kicad_pcb') + f'-{TESS_TOL}-{LIFT}'
    if CACHE.exists():
        c = json.loads(CACHE.read_text())
        if c.get('key') == key:
            return c['boxes']
    boxes = {}
    for fp in board.footprints:
        if fp.lib not in boxes:
            boxes[fp.lib] = [{k: (float(v) if not isinstance(v, bool) else v) for k, v in bx.items()}
                             for bx in local_boxes(fp)]
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(dict(key=key, boxes=boxes)))
    return boxes


@lru_cache(maxsize=None)
def load_pads():
    """Copper pad solids (KiCad frame)."""
    return cq.importers.importStep(str(ROOT / 'src' / 'pads.step')).val().Solids()
