"""The KiCad 3D parts and copper pads of the board.

Each footprint's models come straight from its `(model ...)` entries in the board file: the model
file (src/TOTEM3D), its offset, rotation and scale, placed the way KiCad places them (rotations
negated and applied about X, then Y, then Z; offset in mm with +y up). Every model sits on the top
face of the 1.6 mm board (z = PCB_T in the case frame, where the board spans 0..1.6). Moving a
footprint on the board moves its part and nothing else.

src/comp_all.step (KiCad's own STEP export of the parts) is only used to cross-check this placement:
`crosscheck()` reports how far the export is from the parts placed from the board file, and calls it
stale when they disagree.
"""
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path

import cadquery as cq
import numpy as np

from pcb import SPLIT_X

ROOT = Path(__file__).resolve().parent.parent
PCB_T = 1.6
ABOVE = 0.8           # geometry above the middle of the board belongs to the top side
TESS_TOL = 0.02
CACHE = Path(__file__).resolve().parent / 'cache' / 'part_boxes.json'


# ----------------------------------------------------------------------------- models
def model_path(name):
    """The model file a `(model ...)` entry refers to, resolved the way KiCad does: ${KIPRJMOD} is the
    board's folder, and relative paths are relative to it."""
    p = Path(name.replace('${KIPRJMOD}', str(ROOT / 'src')))
    if not p.is_absolute():
        p = ROOT / 'src' / p
    return p.resolve()


def _ident(name):
    """A model file's identity: its full normalized path (relative to the repo when inside it)."""
    p = model_path(name)
    try:
        return str(p.relative_to(ROOT.resolve()))
    except ValueError:
        return str(p)


def model_key(fp):
    """The footprint's own model entries (full model path, offset, rotation, scale) as a string:
    only footprints with the same key share geometry, whatever their library."""
    return json.dumps([[_ident(p), list(o), list(r), list(sc)] for p, o, r, sc in fp.models])


def _matrix(rot):
    """KiCad model rotation: angles negated, applied about X, then Y, then Z."""
    def R(axis, deg):
        a = math.radians(-deg)
        c, s = math.cos(a), math.sin(a)
        return {'x': np.array([[1, 0, 0], [0, c, -s], [0, s, c]]),
                'y': np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
                'z': np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])}[axis]
    return R('z', rot[2]) @ R('y', rot[1]) @ R('x', rot[0])


def _transform(shape, M, t):
    from OCP.gp import gp_Trsf
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    tr = gp_Trsf()
    tr.SetValues(*M[0], t[0], *M[1], t[1], *M[2], t[2])
    return cq.Shape.cast(BRepBuilderAPI_Transform(shape.wrapped, tr, True).Shape())


@lru_cache(maxsize=None)
def _model_file(path):
    return cq.importers.importStep(str(path)).val()


_TEMPLATES = {}


def template(fp):
    """The footprint's model solids in its own frame: x, y = footprint-local (KiCad x, -y),
    z in the case frame (the board's top face at PCB_T). Built from the footprint's own model
    entries and shared only with footprints whose entries are identical."""
    key = model_key(fp)
    if key not in _TEMPLATES:
        sols = []
        for name, off, rot, scale in fp.models:
            path = model_path(name)
            assert all(abs(s - 1) < 1e-9 for s in scale), (fp.ref, 'scaled models are not handled')
            s = _transform(_model_file(path), _matrix(rot), (off[0], off[1], off[2] + PCB_T))
            sols += s.Solids()
        _TEMPLATES[key] = sols
    return _TEMPLATES[key]


def place(shape, fp):
    return shape.rotate(cq.Vector(), cq.Vector(0, 0, 1), fp.angle).translate(cq.Vector(fp.at[0], fp.at[1], 0))


def placed(board, fp):
    """The footprint's part solids where the board file puts them (case frame)."""
    return [place(s, fp) for s in template(fp)]


# ----------------------------------------------------------------------------- boxes for the build
def _points(solids):
    pts = []
    for s in solids:
        v, _ = s.tessellate(TESS_TOL, 0.3)
        pts.append(np.array([p.toTuple() for p in v] + [p.toTuple() for p in s.Vertices()]))
    return pts


def _boxes_of(solids):
    out = []
    for k, P in enumerate(_points(solids)):
        a, b, z = P[:, 0], P[:, 1], P[:, 2]
        for below, m in ((True, z < ABOVE), (False, z >= ABOVE)):
            if m.sum() < 2:
                continue
            e = TESS_TOL   # tessellation points lie on the surface; chords may cut inside by up to this
            out.append(dict(a0=float(a[m].min() - e), a1=float(a[m].max() + e), b0=float(b[m].min() - e),
                            b1=float(b[m].max() + e), z0=float(z[m].min() - e), z1=float(z[m].max() + e),
                            below=below, solid=k))
    return out


def _sha(*paths):
    h = hashlib.sha256()
    for p in paths:
        h.update(Path(p).read_bytes())
    return h.hexdigest()


_BOXES = {}


def part_boxes(board):
    """{model key: boxes around the model solids, split at the middle of the board} for every
    distinct set of model entries on the board, in the footprint frame. Cached in
    work/cache/part_boxes.json, keyed by the model files' contents and the model entries."""
    keys = sorted({model_key(f) for f in board.footprints})
    files = sorted({str(model_path(n)) for f in board.footprints for n, *_ in f.models if model_path(n).exists()})
    ck = hashlib.sha256((_sha(*files) + json.dumps(keys) + f'-{TESS_TOL}-{PCB_T}-{ABOVE}').encode()).hexdigest()
    if not _BOXES.get('key') == ck:
        boxes = None
        if CACHE.exists():
            c = json.loads(CACHE.read_text())
            if c.get('key') == ck:
                boxes = c['boxes']
        if boxes is None:
            rep = {model_key(f): f for f in board.footprints}
            boxes = {k: _boxes_of(template(rep[k])) for k in keys}
            CACHE.parent.mkdir(exist_ok=True)
            CACHE.write_text(json.dumps(dict(key=ck, boxes=boxes)))
        _BOXES.clear()
        _BOXES.update(key=ck, boxes=boxes)
    return _BOXES['boxes']


def boxes_for(board, fp):
    return part_boxes(board)[model_key(fp)]


def front_box(fp, axis, val, sgn):
    """Box (in the footprint frame) around the part of the footprint's models beyond `axis` = `val`
    on the side `sgn` (an actuator ahead of the body), from the models' surface points; it reaches
    back to the split plane."""
    pts = _points(template(fp))
    if not pts:
        return None
    P = np.concatenate(pts)
    c = P[:, 0] if axis == 'a' else P[:, 1]
    m = ((c - val) * sgn > 1e-9) & (P[:, 2] >= ABOVE)
    if not m.any():
        return None
    e = TESS_TOL
    bx = dict(a0=float(P[m, 0].min() - e), a1=float(P[m, 0].max() + e), b0=float(P[m, 1].min() - e),
              b1=float(P[m, 1].max() + e), z0=float(P[m, 2].min() - e), z1=float(P[m, 2].max() + e), below=False)
    if sgn > 0:
        bx[axis + '0'] = min(bx[axis + '0'], val)
    else:
        bx[axis + '1'] = max(bx[axis + '1'], val)
    return bx


# ----------------------------------------------------------------------------- KiCad's export, pads
@lru_cache(maxsize=None)
def load_export():
    """[(ref, side, shape)] from src/comp_all.step (KiCad's STEP export of the parts)."""
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDF import TDF_LabelSequence
    from OCP.TDocStd import TDocStd_Document
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
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


def crosscheck(board):
    """Compare the parts placed from the board file with KiCad's export: the largest sideways
    difference of any part's box, the export's z offsets, and the parts that differ by more than
    0.05 mm sideways (a stale export)."""
    exp = {}
    for ref, side, shp in load_export():
        exp.setdefault((ref, side), []).append(shp)
    worst, dz, stale = 0.0, set(), []
    for fp in board.footprints:
        sols = placed(board, fp)
        if not sols:
            continue
        bb = cq.Compound.makeCompound(sols).BoundingBox()
        shapes = exp.get((fp.ref, fp.side), [])
        if not shapes:
            stale.append(f'{fp.ref} ({fp.side}, missing)')
            continue
        x = cq.Compound.makeCompound(shapes).BoundingBox()
        e = max(abs(bb.xmin - x.xmin), abs(bb.xmax - x.xmax), abs(bb.ymin - x.ymin), abs(bb.ymax - x.ymax))
        dz.add(round(bb.zmin - x.zmin, 3))
        worst = max(worst, e)
        if e > 0.05:
            stale.append(f'{fp.ref} ({fp.side}, {e:.2f} mm)')
    return dict(max_xy=round(worst, 4), z_offsets=sorted(dz), stale=stale)


@lru_cache(maxsize=None)
def load_pads():
    """Copper pad solids from src/pads.step (KiCad frame: top copper on a 1.51 mm core)."""
    return cq.importers.importStep(str(ROOT / 'src' / 'pads.step')).val().Solids()
