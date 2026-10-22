"""Aluminum TOTEM case: keep every aluminum surface clear of the PCB and its parts.

Inputs are copies (work/orig, src/); originals in ~/Downloads are never touched.
Units mm. Case coordinates = the original STEP coordinates (KiCad x, -y for the left half).
"""
import sys, json, time
from pathlib import Path
sys.path.insert(0, '.')
from geo import *
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.Bnd import Bnd_OBB
from OCP.BRepBndLib import BRepBndLib
from OCP.gp import gp_Pnt
import mill

C = 0.5            # clearance from aluminum to PCB, parts, pads and solder (mm)
SOLDER = 1.0       # allowance for solder fillets above a pad (mm)
COPPER = 0.05      # copper + mask thickness on each face of the board
RESET_PLUNGER = 1.1  # plastic plunger length of the side-push reset switch (metal body ends here)
SOLDER_DIODE = 0.6 # SOD-123 terminals are ~0.15 thick; their fillets stay well under 0.6
DIODE_TOP = 0.3    # clearance above the diode's epoxy body (an insulator); its metal keeps C
PCB_TOP = 1.6      # the case was designed for a 1.6 mm board: bottom face z=0, top face z=1.6
KICAD_TOP = 1.51   # KiCad's board top face; top-side parts are lifted by PCB_TOP-KICAD_TOP
PAD_R = 2.5        # the mounting-hole pads (Ø5.6, no net) may touch the top within this radius
SKIN = 0.6         # thinnest floor left under a bottom pocket; thinner floors are cut through
SEAM_Z0 = -2.0     # original lowest point of the top
SEAM_RAISE = 0.5   # top/bottom seam moved up: top 12.5 -> 12.0 mm so 1/2" plate can be faced both sides
SEAM_GAP = 0.2     # the original leaves 0.2 between top skirt (-2.0) and bottom rim (-2.2); kept
NEST_GAP = 0.4     # bottom to top where they nest above the board (tongues, arches), before machining
LEDGE = (2.4, 3.7) # z span of the 1.2 mm switch clip ledge (2.45..3.65); the cut-out's dogbones stay over the 16 mm recess below
BOOL_TIMEOUT = 150  # s per boolean attempt; a slower one is retried in halves
CSINK_R = 2.3      # countersinks (Ø3.5 top, Ø4.25 bottom) are kept as cones: cut with a countersink bit
DRILL_R = 1.15     # screw holes (Ø2.0 neck in the top, Ø2.16 in the bottom) are drilled: never filled within this radius
R_SHIFT = 7.96     # KiCad right half -> right case (matches the right top's screw bores)
SCREWS = {'L': [(57, -52.7), (34.3, -121.014348), (139.5, -112), (131.2, -52.7)]}
SCREWS['R'] = [(168.46, -112.0), (176.76, -52.7), (250.96, -52.7), (273.66, -121.0)]
XIAO = {'L': ((41.2, -59.6), 90.0), 'R': ((258.8 + R_SHIFT, -59.6), -90.0)}
OUT = W.parent / 'outputs'
OUT.mkdir(exist_ok=True)
T0 = time.monotonic()


def log(*a):
    print(f'[{time.monotonic() - T0:6.1f}s]', *a, flush=True)


def fast_fuse(shape, tools):
    """One multi-tool boolean fuse, run in parallel by the kernel."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
    from OCP.TopTools import TopTools_ListOfShape
    args, tl = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(shape.wrapped)
    for t in tools:
        tl.Append(t.wrapped)
    op = BRepAlgoAPI_Fuse()
    op.SetArguments(args); op.SetTools(tl)
    op.SetRunParallel(True); op.SetUseOBB(True)
    op.SetFuzzyValue(1e-5)  # thin fill slices next to the old faces otherwise make the kernel drop the part
    op.Build()
    assert op.IsDone(), 'fuse failed'
    return cq.Shape.cast(op.Shape())


def fast_cut(shape, tools):
    """One multi-tool boolean cut, run in parallel by the kernel."""
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.TopTools import TopTools_ListOfShape
    args, tl = TopTools_ListOfShape(), TopTools_ListOfShape()
    args.Append(shape.wrapped)
    for t in tools:
        tl.Append(t.wrapped)
    op = BRepAlgoAPI_Cut()
    op.SetArguments(args); op.SetTools(tl)
    op.SetRunParallel(True); op.SetUseOBB(True)
    op.SetFuzzyValue(1e-5)  # thin fill slices next to the old faces otherwise make the kernel drop the part
    op.Build()
    assert op.IsDone(), 'cut failed'
    return cq.Shape.cast(op.Shape())


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def half_space(side):
    """Region belonging to one PCB half in KiCad coordinates (panel tabs removed)."""
    if side == 'L':
        return box(0, 143.35, -300, 0, -50, 50).fuse(box(0, 152, -300, -121.5, -50, 50))
    return box(156.55, 400, -300, 0, -50, 50).fuse(box(148, 400, -300, -121.5, -50, 50))


def place(shape, side):
    return shape if side == 'L' else shape.translate(cq.Vector(R_SHIFT, 0, 0))


def lift(shape):
    """KiCad top-side geometry sits on a 1.51 board; the case expects 1.6."""
    return shape.translate(cq.Vector(0, 0, PCB_TOP - KICAD_TOP))


def obb_box(shape, grow, grow_top=None, z_range=None):
    """Smallest upright box around a solid (parts are only ever rotated about Z), grown by
    `grow` on every side; `grow_top` overrides the growth above the solid, `z_range` sets z."""
    import shapely.geometry as sg
    v, _ = shape.tessellate(0.01, 0.2)
    pts = np.array([p.toTuple() for p in v] + [p.toTuple() for p in shape.Vertices()])
    rect = sg.MultiPoint(pts[:, :2]).convex_hull.minimum_rotated_rectangle
    c = np.array(rect.exterior.coords)[:4]
    e0, e1 = c[1] - c[0], c[2] - c[1]
    ang = np.degrees(np.arctan2(e0[1], e0[0]))
    L0, L1 = np.linalg.norm(e0) + 2 * grow, np.linalg.norm(e1) + 2 * grow
    z0 = pts[:, 2].min() - grow
    z1 = pts[:, 2].max() + (grow if grow_top is None else grow_top)
    if z_range:
        z0, z1 = z_range
    ctr = c.mean(axis=0)
    b = cq.Solid.makeBox(L0, L1, z1 - z0, cq.Vector(-L0 / 2, -L1 / 2, z0))
    return b.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), ang).translate(cq.Vector(ctr[0], ctr[1], 0))


# ---------------------------------------------------------------- PCB keep-out
def pcb_solid(side):
    board = load('../src/pcb_board.step').Solids()[0]
    return place(board.intersect(half_space(side)), side)


def wire_pts(w, step=0.05):
    pts = []
    for e in w.Edges():
        n = max(2, int(e.Length() / step) + 1)
        p = [e.positionAt(t).toTuple()[:2] for t in np.linspace(0, 1, n)]
        pts.extend(p[:-1])
    return pts


def poly_face(poly, z):
    def wire(coords):
        return cq.Wire.makePolygon([cq.Vector(x, y, z) for x, y in coords[:-1]], close=True)
    return cq.Face.makeFromWires(wire(list(poly.exterior.coords)), [wire(list(i.coords)) for i in poly.interiors])


def pcb_keepout(pcb):
    """PCB outline grown by C sideways (holes shrunk by C), from z=-C to PCB_TOP+C."""
    import shapely.geometry as sg
    faces = pcb.intersect(box(-50, 450, -300, 50, 0.74, 0.76)).Faces()
    face = max((f for f in faces if abs(f.normalAt().z) > 0.99 and f.Center().z > 0.755), key=lambda f: f.Area())
    side_c = C + 0.03  # + polyline sampling error on the curved (mouse-bite) edges
    outer = sg.Polygon(wire_pts(face.outerWire())).buffer(side_c, quad_segs=16)
    holes = [sg.Polygon(wire_pts(w)).buffer(-side_c, quad_segs=16) for w in face.innerWires()]
    holes = [h for h in holes if not h.is_empty and h.area > 0.2]
    region = outer
    for h in holes:
        region = region.difference(h)
    polys = list(region.geoms) if region.geom_type == 'MultiPolygon' else [region]
    cu = COPPER  # pads and mask stand proud of the laminate on both faces
    solids = [cq.Solid.extrudeLinear(poly_face(p, -C - cu), cq.Vector(0, 0, PCB_TOP + 2 * (C + cu))) for p in polys]
    k = solids[0] if len(solids) == 1 else cq.Compound.makeCompound(solids)
    return k, len(face.innerWires()), len(holes)


# --------------------------------------------------------- parts and pads
def kicad_parts():
    doc = TDocStd_Document(TCollection_ExtendedString('d'))
    r = STEPCAFControl_Reader(); r.SetNameMode(True)
    r.ReadFile(str(W / '../src/comp_all.step')); r.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    free = TDF_LabelSequence(); st.GetFreeShapes(free)
    parts = []
    for i in range(1, free.Length() + 1):
        comps = TDF_LabelSequence(); st.GetComponents_s(free.Value(i), comps)
        for j in range(1, comps.Length() + 1):
            lab = comps.Value(j); n = TDataStd_Name()
            name = n.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), n) else '?'
            if name.startswith('=>') or name.endswith('_PCB'):
                continue
            parts.append((name, cq.Shape.cast(st.GetShape_s(lab))))
    return parts


def part_keepouts(side, parts):
    """Grown oriented boxes around every solid of every part on this half.
    Switch bodies above the board are plastic and clip into the top plate, so only the
    switch pins below the board are kept out."""
    hs = half_space(side)
    tools, names = [], []
    for name, shp in parts:
        bb = shp.BoundingBox()
        cx = (bb.xmin + bb.xmax) / 2
        if (side == 'L') != (cx < 150):
            continue
        if name.startswith('J'):
            continue  # TRRS jack: not fitted in the BLE build (the BLE bottom fills its space)
        is_switch = bb.zmax > 8
        reset = name in ('RSW1', 'RST')
        for s in shp.Solids():
            if reset and s.Volume() > 1:
                # side-push reset switch: only its metal body needs room; the plastic plunger
                # (last 1.1 mm toward the back wall) keeps using the original round access hole
                sb = s.BoundingBox()
                s = s.intersect(box(sb.xmin - 1, sb.xmax + 1, sb.ymin - 1, sb.ymax - RESET_PLUNGER, sb.zmin - 1, sb.zmax + 1))
            sb = s.BoundingBox()
            if is_switch:
                if sb.zmin >= 0:
                    continue
                s = s.intersect(box(-50, 450, -300, 50, -10, 0))
                if not s.Solids():
                    continue
            if sb.zmin > 0.75:
                s = lift(s)
            top_gap = DIODE_TOP if name.startswith('D') else None
            tools.append(place(obb_box(s, C, top_gap), side)); names.append(name)
    return tools, names


def switch_centres(parts):
    """KiCad-coordinate centres of the switch bodies."""
    out = []
    for name, shp in parts:
        if shp.BoundingBox().zmax > 8:
            body = max(shp.Solids(), key=lambda s: s.Volume())
            b = body.BoundingBox()
            out.append(((b.xmin + b.xmax) / 2, (b.ymin + b.ymax) / 2))
    return out


def pad_keepouts(side, screws, parts):
    """Exposed copper. Solder allowance where solder can be: SMD pads, and THT pads on the
    bottom. The switch-pin rings on the top side sit under the switch body and are never
    soldered from the top (hot-swap sockets; direct soldering is done from below)."""
    pads = load('../src/pads.step').Solids()
    sw = switch_centres(parts)
    diodes, jacks = [], []
    for name, shp in parts:
        if name.startswith('J'):
            b = shp.BoundingBox()
            jacks.append(((b.xmin + b.xmax) / 2, (b.ymin + b.ymax) / 2))
        if name.startswith('D'):
            b = shp.BoundingBox()
            diodes.append(((b.xmin + b.xmax) / 2, (b.ymin + b.ymax) / 2))
    tools = []
    for p in pads:
        b = p.BoundingBox()
        cx, cy = (b.xmin + b.xmax) / 2, (b.ymin + b.ymax) / 2
        if (side == 'L') != (cx < 150):
            continue
        X = cx + (0 if side == 'L' else R_SHIFT)
        if any(np.hypot(X - sx, cy - sy) < 0.5 for sx, sy in screws):
            continue  # floating mounting pad: allowed contact
        top_side = b.zmax > 0.75
        bot_side = b.zmin < 0.75
        unfitted = any(np.hypot(cx - x, cy - y) < 9 for x, y in jacks)  # bare pads, no solder
        z0 = -SOLDER - C if bot_side and not unfitted else -C
        ring = any(f.geomType() == 'CYLINDER' for f in p.Faces())  # copper around a drilled hole
        under_switch = top_side and ring and any(np.hypot(cx - x, cy - y) < 7.6 for x, y in sw)
        diode_pad = any(np.hypot(cx - x, cy - y) < 2.6 for x, y in diodes)
        solder = SOLDER_DIODE if diode_pad else SOLDER
        z1 = PCB_TOP + solder + C if top_side and not under_switch and not unfitted else PCB_TOP + C
        # the pad grown sideways by C (+0.3 fillet spread), spanning [z0, z1]
        prism = obb_box(p, C + 0.3, z_range=(z0, z1))
        tools.append(place(prism, side))
    return tools


def board_prism(k_pcb):
    """The board outline grown by C (holes ignored), as a tall prism."""
    sols = k_pcb.Solids()
    faces = [f for so in sols for f in so.Faces() if f.normalAt().z < -0.99]
    outer = [cq.Face.makeFromWires(f.outerWire()) for f in faces]
    return cq.Compound.makeCompound([cq.Solid.extrudeLinear(f.translate(cq.Vector(0, 0, -20 - f.Center().z)),
                                                             cq.Vector(0, 0, 40)) for f in outer])


def merge_under_switches(tools, side, parts, under_board):
    """Below the board, every switch has a socket, two contacts, pins and pads with their own
    zones; overlapping boxes of different depths leave knife-edge wedges. Replace each switch's
    group with one upright box around all of them (deepest floor)."""
    centres = [place(cq.Vertex.makeVertex(x, y, 0), side).Center() for x, y in switch_centres(parts)]
    groups = {i: [] for i in range(len(centres))}
    rest = []
    for t in tools:
        b = t.BoundingBox()
        c = ((b.xmin + b.xmax) / 2, (b.ymin + b.ymax) / 2)
        near = [i for i, v in enumerate(centres) if np.hypot(c[0] - v.x, c[1] - v.y) < 9.5]
        if b.zmin < -C - 0.05 and near:
            groups[min(near, key=lambda i: np.hypot(c[0] - centres[i].x, c[1] - centres[i].y))].append(t)
        else:
            rest.append(t)
    merged = []
    for i, g in groups.items():
        if not g:
            continue
        comp = cq.Compound.makeCompound(g)
        zb = comp.BoundingBox()
        # 0.01 larger than its contents so no face coincides with a zone inside it
        rect = obb_box(comp, 0.01, z_range=(zb.zmin - 0.01, max(zb.zmax, 0.0) + 0.01)).intersect(under_board)
        outside = [x.cut(under_board) for x in g]
        outside = [x for x in outside if x.Solids() and x.Volume() > 1e-4]
        merged.append(rect.fuse(*outside).clean() if outside else rect)
    return rest + merged, len(merged)


def face_poly(face):
    """Filled shapely polygon of a planar face (holes ignored), from its own triangles."""
    import shapely.geometry as sg
    from shapely.ops import unary_union
    v, tri = face.tessellate(0.01, 0.2)
    pts = np.array([p.toTuple()[:2] for p in v])
    u = unary_union([sg.Polygon(pts[list(t)]) for t in tri if sg.Polygon(pts[list(t)]).area > 1e-9]).buffer(1e-4)
    return unary_union([sg.Polygon(g.exterior) for g in (u.geoms if u.geom_type == 'MultiPolygon' else [u])])


def face_region(face):
    """Shapely polygon of a planar face with its holes, from the face's own triangles."""
    import shapely.geometry as sg
    from shapely.ops import unary_union
    v, tri = face.tessellate(0.01, 0.2)
    pts = np.array([p.toTuple()[:2] for p in v])
    return unary_union([sg.Polygon(pts[list(t)]) for t in tri if sg.Polygon(pts[list(t)]).area > 1e-9]).buffer(1e-4)


def fill_leg_recess_slits(bot, side):
    """The site lowered the GEIST leg-recess roofs from -2.6 to -7.3 (shallower recesses) but
    missed bits: the old rounded wall/roof edge (0.5-0.8 mm slits) and a few corners of the old
    roof. Map every place inside the GEIST recess footprint that is open from below with its
    ceiling still at the old roof height, trace smooth outlines and fill them from -7.3 up, so
    the whole recess has the lowered roof. Through-openings stay open."""
    import trimesh, contourpy, shapely.geometry as sg
    from shapely.ops import unary_union
    roof_faces = [f for f in bot.Faces() if f.normalAt().z < -0.99 and abs(f.Center().z + 7.3) < 0.02 and f.Area() > 200]
    if not roof_faces:
        return bot, 0, 0.0, 0.0
    roof = unary_union([face_region(f) for f in roof_faces])            # the lowered roof (holes open)
    geist = load(f'orig/TOTEMcase_v08_6mm_BLE_Tenting_Bottom_{side}.step')
    if not geist.Solids() or len(geist.Shells()) > 1:
        geist = cq.Solid.makeSolid(max(geist.Shells(), key=lambda sh: sh.Area()))
    # the GEIST recess footprint: every roof face at -2.6, openings filled, plus its rounded edge
    old = unary_union([face_poly(f) for f in geist.Faces()
                       if f.normalAt().z < -0.99 and abs(f.Center().z + 2.6) < 0.02 and f.Area() > 0.5])
    near = old.buffer(0.9).union(unary_union([face_poly(f) for f in roof_faces]).buffer(1.0)).difference(roof.buffer(-0.01))
    v, f = bot.tessellate(0.005, 0.05)
    m = trimesh.Trimesh(np.array([p.toTuple() for p in v]), np.array(f))
    step = 0.05
    polys = []
    for part in (near.geoms if near.geom_type == 'MultiPolygon' else [near]):
        x0, y0, x1, y1 = part.bounds
        xs = np.arange(x0 - 0.2, x1 + 0.2, step); ys = np.arange(y0 - 0.2, y1 + 0.2, step)
        X, Y = np.meshgrid(xs, ys); P = np.c_[X.ravel(), Y.ravel()]
        loc, idx, _ = m.ray.intersects_location(np.c_[P, np.full(len(P), -20.0)], np.tile([0, 0, 1.0], (len(P), 1)),
                                                multiple_hits=False)
        H = np.full(len(P), np.nan); H[idx] = np.asarray(loc).reshape(-1, 3)[:, 2]
        G = ((H > -6.9) & (H < -2.4)).astype(float).reshape(X.shape)  # anything above the lowered roof
        gen = contourpy.contour_generator(xs, ys, G, fill_type=contourpy.FillType.OuterOffset)
        for pts, offs in zip(*gen.filled(0.5, 1.5)):
            rings = [pts[offs[i]:offs[i + 1]] for i in range(len(offs) - 1)]
            if len(rings[0]) >= 4:
                polys.append(sg.Polygon(rings[0], [r for r in rings[1:] if len(r) >= 4]).buffer(0))
    slit = unary_union(polys).intersection(near) if polys else sg.Polygon()
    slit = slit.buffer(-0.05).buffer(0.15).simplify(0.02)   # drop specks, overlap the walls by ~0.1
    pieces = [g for g in (slit.geoms if slit.geom_type == 'MultiPolygon' else [slit]) if g.area > 0.3]
    fill = [cq.Solid.extrudeLinear(poly_face(g, -7.3), cq.Vector(0, 0, 7.3 - 2.5)) for g in pieces]
    vol = sum(x.Volume() for x in fill)
    out = bot.fuse(*fill).clean() if fill else bot
    b0, b1 = bot.BoundingBox(), out.BoundingBox()
    assert max(abs(b0.xmin - b1.xmin), abs(b0.xmax - b1.xmax), abs(b0.ymin - b1.ymin), abs(b0.ymax - b1.ymax)) < 1e-6, \
        'slit fill reached outside the case'
    return out, len(pieces), round(sum(g.area for g in pieces), 1), round(vol, 1)


def close_recess_openings(bot, side, top):
    """The socket pockets of the site's bottom break through the leg-recess roofs, some at the
    recess edge, and bits of the old -2.6 roof are left around a few of them. On an underside
    height map, take each leg recess as seen from below (its -7.3 roof plus every opening and
    raised bit joined to it, so its outline is the original's) and fill everything in it that is
    open or higher than the roof, from -7.3 up. Screw holes and the cavities around them stay.
    The keep-out cuts then carve the pockets again, so each one gets a floor and each recess
    roof is one flat face of the same outline. The fill stays SEAM_GAP clear of the top part and
    inside the case's outer face."""
    import trimesh, contourpy, shapely, shapely.geometry as sg
    from shapely.ops import unary_union
    roof_faces = [f for f in bot.Faces() if f.normalAt().z < -0.99 and abs(f.Center().z + 7.3) < 0.02 and f.Area() > 200]
    roof = unary_union([face_poly(f) for f in roof_faces])
    screws = unary_union([sg.Point(x, y).buffer(3.0) for x, y in SCREWS[side]])
    v, f = bot.tessellate(0.01, 0.1)
    m = trimesh.Trimesh(np.array([p.toTuple() for p in v]), np.array(f))
    step = 0.1
    x0, y0, x1, y1 = roof.buffer(12).bounds
    xs = np.arange(x0, x1, step); ys = np.arange(y0, y1, step)
    X, Y = np.meshgrid(xs, ys); P = np.c_[X.ravel(), Y.ravel()]
    loc, idx, _ = m.ray.intersects_location(np.c_[P, np.full(len(P), -30.0)], np.tile([0, 0, 1.0], (len(P), 1)),
                                            multiple_hits=False)
    U = np.full(len(P), np.nan); U[idx] = np.asarray(loc).reshape(-1, 3)[:, 2]
    solid = ~np.isnan(U)

    def polys(mask, holes=False):
        gen = contourpy.contour_generator(xs, ys, mask.reshape(X.shape).astype(float), fill_type=contourpy.FillType.OuterOffset)
        out = []
        for pts, offs in zip(*gen.filled(0.5, 1.5)):
            rings = [pts[offs[k]:offs[k + 1]] for k in range(len(offs) - 1)]
            if holes:
                out += [sg.Polygon(r).buffer(0) for r in rings[1:] if len(r) >= 4]
            elif len(rings[0]) >= 4:
                out.append(sg.Polygon(rings[0], [r for r in rings[1:] if len(r) >= 4]).buffer(0))
        return unary_union(out) if out else sg.Polygon()

    def pieces(g):
        return [x for x in (g.geoms if g.geom_type in ('MultiPolygon', 'GeometryCollection') else [g]) if x.area > 0]

    through = polys(solid, holes=True)                       # open from below to above, material all around
    cavity = unary_union([polys(solid & (U > -11.3)), through]).buffer(0.15).buffer(-0.15)
    recess = unary_union([g for g in pieces(cavity) if g.intersects(roof)])
    high = unary_union([polys(solid & (U > -7.25)), through]).intersection(recess)
    # where a recess runs out to the edge of the part, the fill ends 0.1 inside the case's outer face
    # (the top part's outline: its walls are vertical, so its flat faces reach them), as the
    # original recess mouths do
    flat = unary_union([face_poly(f) for f in top.Faces() if f.geomType() == 'PLANE' and abs(f.normalAt().z) > 0.99]).buffer(0.001)
    outer = sg.Polygon(max(pieces(flat), key=lambda g: g.area).exterior).buffer(-0.1)
    fill_area = unary_union([g for g in pieces(high.buffer(0.1).intersection(recess.buffer(0.3)).intersection(outer))
                             if g.area > 0.3 and not g.intersects(screws)])  # screw holes and their cavities stay
    fill_area = fill_area.simplify(0.02)
    fill = [cq.Solid.extrudeLinear(poly_face(g, -7.3), cq.Vector(0, 0, 7.3)) for g in pieces(fill_area)]
    if fill:
        g = SEAM_GAP + 0.05
        moves = [(0, 0, -g)] + [(g * np.cos(a), g * np.sin(a), 0) for a in np.radians(np.arange(0, 360, 30))]
        cut = []
        for x in fill:
            fb = x.BoundingBox()
            near = top.intersect(box(fb.xmin - 1, fb.xmax + 1, fb.ymin - 1, fb.ymax + 1, fb.zmin - 1, fb.zmax + 1))
            if near.Solids():
                x = x.cut(near, *[near.translate(cq.Vector(*mv)) for mv in moves])
            cut += [y for y in x.Solids() if y.Volume() > 1e-3]
        fill = cut
    out = bot.fuse(*fill).clean() if fill else bot
    b0, b1 = bot.BoundingBox(), out.BoundingBox()
    assert max(abs(getattr(b0, a) - getattr(b1, a)) for a in ('xmin', 'xmax', 'ymin', 'ymax', 'zmin')) < 1e-6, \
        'opening fill reached outside the case'
    return out, len(fill), round(fill_area.area, 1)


def thicken_thin_floors(layers, bot, skin):
    """A pocket floor must be at least `skin` thick. `layers`: the opened pockets cut from above,
    as (z, region reached at z) from the deepest up. Where the underside below a pocket comes
    within `skin` of its floor (leftover bits of the old leg-recess roof, sloped edges), add a pad
    underneath so the floor stays `skin` thick. Through-openings (no material at all) stay open."""
    import trimesh, shapely.geometry as sg
    from shapely.ops import unary_union
    from shapely import contains_xy
    v, f = bot.tessellate(0.005, 0.05)
    m = trimesh.Trimesh(np.array([p.toTuple() for p in v]), np.array(f))
    pads, where, prev = [], [], sg.Polygon()
    for z, region in layers:
        floor = region.difference(prev)
        prev = region
        if z > -C - 0.05 or floor.is_empty:
            continue
        for part in mill.pieces(floor):
            x0, y0, x1, y1 = part.bounds
            X, Y = np.meshgrid(np.arange(x0, x1, 0.1), np.arange(y0, y1, 0.1))
            inside = contains_xy(part, X.ravel(), Y.ravel())
            P = np.c_[X.ravel(), Y.ravel()][inside]
            if len(P) == 0:
                continue
            loc, idx, _ = m.ray.intersects_location(np.c_[P, np.full(len(P), -20.0)], np.tile([0, 0, 1.0], (len(P), 1)),
                                                    multiple_hits=False)
            U = np.full(len(P), -99.0); U[idx] = np.asarray(loc).reshape(-1, 3)[:, 2]
            thin = P[(U < z) & (U > z - skin)]
            if len(thin) == 0:
                continue
            reg = unary_union([sg.Point(x, y).buffer(0.12, quad_segs=4) for x, y in thin]).buffer(0.05).simplify(0.02)
            for g in mill.pieces(reg):
                if g.area > 0.01:
                    pads.append(cq.Solid.extrudeLinear(poly_face(g, z - skin - 0.05), cq.Vector(0, 0, skin + 0.05)))
            c = part.centroid
            where.append((round(c.x, 1), round(c.y, 1), len(thin)))
    return pads, where


def xiao_keepout(side):
    """The XIAO module has no KiCad model; use the site's model extents (local frame)."""
    (x, y), a = XIAO[side]
    loc = box(-8.9, 8.9, -10.6, 11.9, 1.66, 5.93)
    s = obb_box(loc, C).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), a).translate(cq.Vector(x, y, 0))
    return s


# ------------------------------------------------------------ wood window
def window_parts(side, top):
    """Opening in the roof above the XIAO, and the wood insert's plug and flange outline."""
    (x, y), a = XIAO[side]
    def local(x0, x1, y0, y1, z0, z1, r):
        b = cq.Workplane().box(x1 - x0, y1 - y0, z1 - z0).edges('|Z').fillet(r) \
            .translate(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)).val()
        return b.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), a).translate(cq.Vector(x, y, 0))
    # roof underside straight above the XIAO centre
    col = top.intersect(box(x - 0.05, x + 0.05, y - 0.05, y + 0.05, 6, 20))
    roof_z0 = col.BoundingBox().zmin
    top_z = col.BoundingBox().zmax
    W_X, W_Y = (-7.0, 7.0), (-10.3, 8.2)       # window in XIAO frame: to the far end; USB-C end (+y) closed
    hole = local(*W_X, *W_Y, roof_z0 - 1, top_z + 1, 1.5)
    plug = local(W_X[0] + 0.1, W_X[1] - 0.1, W_Y[0] + 0.1, W_Y[1] - 0.1, roof_z0, top_z, 1.4)
    flange_box = local(W_X[0] - 1.5, W_X[1] + 1.5, W_Y[0] - 1.5, W_Y[1] + 1.5, roof_z0 - 1.5, roof_z0, 1.0)
    return hole, plug, flange_box, roof_z0, top_z


def window_insert(side, top, plug, flange_box, roof_z0, top_z):
    """Wood insert for the final top: plug in the window plus a 1.5 mm flange under the roof that
    clears the cavity walls by 0.2. The flange outline is made cuttable with the Ø2 end mill
    (its inside corners next to the walls get dogbones, cut into the flange, never into the wall)."""
    flange_t = 1.5
    fb = flange_box.BoundingBox()
    m = mill.mesh_of(top.intersect(box(fb.xmin - 3, fb.xmax + 3, fb.ymin - 3, fb.ymax + 3, roof_z0 - flange_t - 0.5, roof_z0 + 0.5)))
    walls = mill.unary_union([mill.section(m, z) for z in np.linspace(roof_z0 - flange_t + 0.002, roof_z0 - 0.002, 7)])
    fl = mill.section(mill.mesh_of(flange_box, 0.002), roof_z0 - flange_t / 2)
    frame = mill.sg.box(fb.xmin - 3, fb.ymin - 3, fb.xmax + 3, fb.ymax + 3)
    void = frame.difference(fl).union(walls.buffer(0.2, quad_segs=mill.QS))
    flange2d = frame.difference(mill.open_superset(void))
    pc = plug.Center()
    flange2d = max(mill.pieces(flange2d), key=lambda g: (g.contains(mill.sg.Point(pc.x, pc.y)), g.area))
    insert = plug.fuse(mill.prism(flange2d, roof_z0 - flange_t, roof_z0)).clean()
    insert = sorted(insert.cut(top).Solids(), key=lambda s: -s.Volume())[0]  # never overlap the aluminum
    assert insert.BoundingBox().zmax > top_z - 1e-3, 'insert lost its plug'
    return insert


def repair(shape):
    """Booleans can leave a zero-area face; re-sew without it (volume must not change)."""
    if shape.isValid():
        return shape
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
    sew = BRepBuilderAPI_Sewing(1e-5)
    for f in shape.Faces():
        if f.Area() > 1e-9:
            sew.Add(f.wrapped)
    sew.Perform()
    from OCP.ShapeFix import ShapeFix_Solid
    shells = sorted(cq.Shape.cast(sew.SewedShape()).Shells(), key=lambda sh: -sh.Area())
    fs = ShapeFix_Solid(cq.Solid.makeSolid(shells[0]).wrapped); fs.Perform()
    fixed = cq.Shape.cast(fs.Solid())
    assert fixed.isValid() and abs(fixed.Volume() - shape.Volume()) < 1e-6 * abs(shape.Volume()) + 1e-2, \
        ('repair failed', len(shells), fixed.isValid(), fixed.Volume(), shape.Volume())
    log('repaired a degenerate face')
    return fixed


def switch_cutouts(top):
    """The ~13.8 mm square switch cut-outs through the clip ledge, as keep-out prisms (the mill
    stage gives them dogbones so the switches' square corners fit)."""
    sec = top.intersect(box(-50, 450, -300, 50, 2.99, 3.01))
    face = [f for f in sec.Faces() if f.normalAt().z > 0.99 and f.Center().z > 3.005]
    out = []
    for f in face:
        for w in f.innerWires():
            vs = [v.toTuple()[:2] for v in w.Vertices()]
            if len(vs) != 4:
                continue
            sides = [np.hypot(*(np.subtract(vs[i], vs[(i + 1) % 4]))) for i in range(4)]
            if not all(13.6 < L < 14.1 for L in sides):
                continue
            out.append(mill.prism(mill.sg.Polygon(vs), LEDGE[0], LEDGE[1]))
    return out


def countersinks(side):
    return mill.unary_union([mill.sg.Point(x, y).buffer(CSINK_R, quad_segs=mill.QS) for x, y in SCREWS[side]])


def drill_holes(side):
    """Screw holes: drilled, so the fill leaves them alone."""
    return mill.unary_union([mill.sg.Point(x, y).buffer(DRILL_R, quad_segs=mill.QS) for x, y in SCREWS[side]])


def safe_bool(kind, part, tools, name, fuzzy=1e-5):
    """fast_fuse / fast_cut whose result is checked: one solid that still holds the part (fuse:
    nothing lost; cut: nothing added). On a bad result the tools are split in halves and applied in
    turn; a single tool the kernel still mishandles is retried with a larger fuzzy value, and
    after that a fill prism is skipped (the machinability check would show the spot) while a
    keep-out never is."""
    import subprocess, tempfile
    def run(ts, fz):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            part.exportBrep(str(d / 'p.brep')); cq.Compound.makeCompound(ts).exportBrep(str(d / 't.brep'))
            try:
                subprocess.run([sys.executable, '-E', '-s', str(W / 'bool_worker.py'), kind, str(fz),
                                str(d / 'p.brep'), str(d / 't.brep'), str(d / 'r.brep')],
                               timeout=BOOL_TIMEOUT, check=False, capture_output=True)
            except subprocess.TimeoutExpired:
                log(name, kind, 'of', len(ts), 'tools timed out')
                return None
            if not (d / 'r.brep').exists():
                return None
            result = cq.Shape.importBrep(str(d / 'r.brep'))
        # the kernel sometimes adds an inside-out copy of the tools (negative volume): not material
        sols = sorted([s for s in result.Solids() if s.Volume() > 0], key=lambda s: -s.Volume())
        if not sols or sum(s.Volume() for s in sols[1:]) > 0.5:
            return None
        v0, v = part.Volume(), sols[0].Volume()
        if (kind == 'fuse' and v < v0 - 0.01) or (kind == 'cut' and (v > v0 + 0.01 or v < 0.5 * v0)):
            return None
        return sols[0]
    # a cut is fast and usually fine without fuzzy; the thin fill slices need it for the fuse
    for fz in ((0.0, fuzzy) if kind == 'cut' else (fuzzy,)):
        r = run(tools, fz)
        if r is not None:
            return r
    if len(tools) == 1:
        for fz in (1e-4, 1e-3):
            r = run(tools, fz)
            if r is not None:
                log(name, kind, 'needed fuzzy', fz, 'for one tool')
                return r
        b = tools[0].BoundingBox()
        where = [round(v, 2) for v in (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)]
        assert kind == 'fuse', (name, 'a keep-out cut fails in the kernel', where)
        log(name, 'skipped a fill prism the kernel cannot fuse at', where, 'vol', round(tools[0].Volume(), 4))
        return part
    h = len(tools) // 2
    log(name, kind, 'of', len(tools), 'tools gave a bad result; applying them in two halves')
    part = safe_bool(kind, part, tools[:h], name, fuzzy)
    return safe_bool(kind, part, tools[h:], name, fuzzy)


def fuse_fills(part, fills, name):
    """All fill prisms in one fuse. Each fuzzy fuse leaves the solid a little harder for the next,
    so if the single fuse fails, every prism is first tried alone against the clean part (in
    parallel) and the few the kernel can't take are left out of the one final fuse."""
    import subprocess, tempfile
    from concurrent.futures import ThreadPoolExecutor
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        part.exportBrep(str(d / 'p.brep'))
        def run(ts, tag, timeout):
            cq.Compound.makeCompound(ts).exportBrep(str(d / f't{tag}.brep'))
            try:
                subprocess.run([sys.executable, '-E', '-s', str(W / 'bool_worker.py'), 'fuse', '1e-5', str(d / 'p.brep'),
                                str(d / f't{tag}.brep'), str(d / f'r{tag}.brep')], timeout=timeout, capture_output=True)
            except subprocess.TimeoutExpired:
                return None
            if not (d / f'r{tag}.brep').exists():
                return None
            sols = sorted([s for s in cq.Shape.importBrep(str(d / f'r{tag}.brep')).Solids() if s.Volume() > 0],
                          key=lambda s: -s.Volume())
            if not sols or sum(s.Volume() for s in sols[1:]) > 0.5 or sols[0].Volume() < part.Volume() - 0.01:
                return None
            return sols[0]
        r = run(fills, 'all', BOOL_TIMEOUT)
        if r is not None:
            return r
        log(name, 'fuse of all', len(fills), 'fill prisms failed; trying each alone')
        with ThreadPoolExecutor(10) as ex:
            good = list(ex.map(lambda it: run([it[1]], it[0], 60) is not None, enumerate(fills)))
        bad = [f for f, g in zip(fills, good) if not g]
        for f in bad:
            b = f.BoundingBox()
            log(name, 'left out a fill prism the kernel cannot fuse at',
                [round(v, 2) for v in (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)], 'vol', round(f.Volume(), 4))
        keep = [f for f, g in zip(fills, good) if g]
        r = run(keep, 'keep', BOOL_TIMEOUT) if keep else part
    return r if r is not None else safe_bool('fuse', part, keep, name)


def mesh_union_checked(part, fills, name):
    v0 = part.Volume()
    r, dv = mill.mesh_union(part, fills, log=lambda *a: log(name, *a))
    # validity is restored when the STEP is written (validate_step heals and checks the volume)
    assert r.Volume() > v0 - 0.01 and abs(r.Volume() - v0 - dv) < 0.05 * dv + 0.05, \
        (name, 'mesh union', r.isValid(), v0, r.Volume(), dv)
    return r, dv


def make_machinable(part, opened, layers, side_cut, drill, name, mesh=False, extra=None):
    """Cut the keep-outs as a Ø2 end mill makes them (dogboned, open toward the side they are cut
    from), then fill whatever that mill still couldn't cut - never inside those keep-outs or the
    drilled holes. The fill goes last: its fuse needs a fuzzy tolerance that slows any later boolean."""
    part = max(part.Solids(), key=lambda s: s.Volume())
    v0 = part.Volume()
    for group in opened:   # one boolean per layer
        if group:
            part = safe_bool('cut', part, group, name)
    part = part.clean()
    part.exportBrep(str(W / f"cut_{name.replace(' ', '_')}.brep"))
    log(name, 'keep-outs cut with dogbones:', round(v0 - part.Volume(), 1), 'mm^3 removed')
    ko = mill.layer_keep_out(layers, side_cut)
    fills = mill.hull_fill(part, keep_out=lambda a, b: mill.unary_union([drill, ko(a, b)] + [e(a, b) for e in extra or []]),
                           log=lambda *a: log(name, *a))
    v1 = part.Volume()
    if fills and mesh:
        # the bottom is the site's triangle mesh: an exact mesh union is quick where the kernel
        # struggles with thousands of thin slices against its facets
        part, _ = mesh_union_checked(part, fills, name)
    elif fills:
        part = fuse_fills(part, fills, name).clean()
        log(name, 'filled:', round(part.Volume() - v1, 1), 'mm^3 added')
    return part


def heal_candidates(shape):
    """Ways to heal a shape the STEP round trip flags as invalid, gentlest first."""
    from OCP.ShapeFix import ShapeFix_Shape
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    yield 'as is', shape
    for prec in (1e-5, 1e-4, 1e-3):
        fx = ShapeFix_Shape(shape.wrapped); fx.SetPrecision(prec); fx.SetMaxTolerance(prec * 10); fx.Perform()
        yield f'ShapeFix {prec}', cq.Shape.cast(fx.Shape())
    u = ShapeUpgrade_UnifySameDomain(shape.wrapped, True, True, False); u.Build()
    yield 'unify faces', cq.Shape.cast(u.Shape())
    try:
        yield 'resew', repair(shape)
    except AssertionError:
        pass


def drop_voids(solid):
    """Fill sealed internal voids (the raster slit fill can trap hair-thin air needles)."""
    shells = solid.Shells()
    if len(shells) == 1:
        return solid
    outer = max(shells, key=lambda sh: sh.Area())
    filled = cq.Solid.makeSolid(outer)
    log('filled', len(shells) - 1, 'sealed voids, volume', round(filled.Volume() - solid.Volume(), 4), 'mm^3')
    return filled


def validate_step(shape, path, volume_tol=None, write_pcurves=True):
    """Publish only a single valid solid that survives a volume-checked STEP round trip."""
    vol = shape.Volume()
    tol = volume_tol if volume_tol is not None else 1e-4 * abs(vol) + 0.05
    tried, back = [], None
    pending = path.with_name(path.stem + '.pending.step')
    try:
        for src in (shape, None):
            base = shape if src is not None else back
            if base is None:
                continue
            for how, cand in heal_candidates(base):
                sols = cand.Solids()
                if len(sols) != 1 or abs(sols[0].Volume() - vol) > tol:
                    tried.append((how, 'changed')); continue
                if not sols[0].isValid():
                    tried.append((how, 'invalid before export')); continue
                sols[0].exportStep(str(pending), write_pcurves=write_pcurves)
                back = cq.importers.importStep(str(pending)).val()
                ok = back.isValid() and len(back.Solids()) == 1 and abs(back.Volume() - vol) <= tol
                tried.append((how, ok))
                if ok:
                    pending.replace(path)
                    if how != 'as is':
                        log(path.name, 'healed by', how)
                    return back
    finally:
        pending.unlink(missing_ok=True)
    raise AssertionError((path.name, tried))


def build(side, parts):
    log(side, 'start')
    top = load(f'orig/TOTEM_case_ble_top_{side}_V.08.step')
    bot = load(f'orig/TOTEM_tenting_live_bottom_{side}.step')
    bot, n_slit, a_slit, v_fill = fill_leg_recess_slits(bot, side)
    log(side, 'leg-recess slits closed:', n_slit, 'pieces,', a_slit, 'mm^2 footprint,', v_fill, 'mm^3')
    bot, n_open, a_open = close_recess_openings(bot, side, top)
    log(side, 'through-openings in the recess roofs closed:', n_open, ',', a_open, 'mm^2')
    pcb = pcb_solid(side)
    k_pcb, n_holes, n_kept = pcb_keepout(pcb)
    log(side, 'pcb keep-out ok; holes', n_holes, 'kept after shrink', n_kept)
    k_parts, part_names = part_keepouts(side, parts)
    k_pads = pad_keepouts(side, SCREWS[side], parts)
    k_xiao = xiao_keepout(side)
    under_board = board_prism(k_pcb)
    tools, n_merged = merge_under_switches(k_parts + k_pads, side, parts, under_board)
    # the bottom is cut from above: every keep-out as a pocket the Ø2 end mill can make
    _, parts_layers = mill.open_tools(tools, 'above', 30.0, log=lambda *a: log(side, 'bottom (parts only)', *a))
    pads, where = thicken_thin_floors(parts_layers, bot, SKIN)
    tools = [k_pcb, k_xiao] + tools
    bot_open, bot_layers = mill.open_tools(tools, 'above', 30.0, log=lambda *a: log(side, 'bottom', *a))
    log(side, 'keep-outs: parts', len(k_parts), 'pads', len(k_pads), '-> merged under', n_merged, 'switches; total', len(tools))
    if pads:
        bot = bot.fuse(*pads).clean()
    log(side, 'thin pocket floors padded from below at', where)
    keep = cq.Compound.makeCompound(tools)

    seam = SEAM_Z0 + SEAM_RAISE
    top_hi = top.intersect(box(-50, 450, -300, 50, seam, 50))
    # the bottom rim grows up by SEAM_RAISE under the old skirt footprint (old gap filled, new gap kept)
    ring = top.intersect(box(-50, 450, -300, 50, SEAM_Z0, seam - SEAM_GAP))
    skirt = ring.fuse(ring.translate(cq.Vector(0, 0, -SEAM_GAP - 0.05))).clean()
    bot_raw = bot.fuse(skirt).clean()
    cached = W / f'final_top_{side}.brep'
    if '--reuse-top' in sys.argv and cached.exists():
        # rebuild only the bottom: the top (and its insert) from the last run
        new_top = cq.Shape.importBrep(str(cached))
        insert = cq.Shape.importBrep(str(W / f'final_insert_{side}.brep'))
        log(side, 'top and insert reused from', cached.name)
    else:
        new_top, insert = build_top(side, top, top_hi, tools, k_pcb, bot_raw)
    new_bot = bot_raw
    # where the top nests into the bottom above the board (the locating tongues and arches at the
    # back wall), the bottom is cut back to NEST_GAP from the top, opened for the mill: the mill
    # leaves up to ~0.22 mm on the top's arches, and the parts must still fit
    bot_open, bot_layers = mill.open_tools(tools, 'above', 30.0, log=lambda *a: log(side, 'bottom', *a),
                                           extra_entries=mill.grown_entries(new_top, NEST_GAP, 'above', 0.0, 5.0))
    # the bottom is the site's triangle mesh: its cuts and fills run on exact meshes, where the
    # kernel stalls on thin layers and thousands of thin fill slices against its facets
    new_bot = mill.mesh_machinable(new_bot, tools, bot_open, bot_layers, 'above', drill_holes(side),
                                   log=lambda *a: log(side, 'bottom', *a),
                                   extra=[mill.solid_keep_out(new_top, SEAM_GAP)],   # stay clear of the top
                                   flat_exempt=countersinks(side))
    log(side, 'bottom done')
    return finish(side, new_top, new_bot, insert, tools, pcb, part_names)


def build_top(side, top, top_hi, tools, k_pcb, bot_raw):
    """The top straight from the original: every keep-out is cut once, already opened for the
    mill (an exact cut first would leave faces at the same heights as the opened layers, and those
    coplanar faces stall the kernel)."""
    hole, plug, flange_box, roof_z0, top_z = window_parts(side, top)
    new_top = top_hi.cut(hole).clean()
    # flat end mills only: every sloped face becomes vertical walls / flat steps (countersinks stay)
    flat = mill.flatten_slopes(new_top, exempt=countersinks(side), log=lambda *a: log(side, 'top', *a))
    if flat:
        new_top = max(safe_bool('cut', max(new_top.Solids(), key=lambda s: s.Volume()), flat, f'{side} top').Solids(),
                      key=lambda s: s.Volume())
    squares = switch_cutouts(new_top)
    log(side, 'switch cut-outs:', len(squares))
    # the 4 pad bosses (r = PAD_R, from the board up) stay; under them, down to the board, the
    # board keep-out still applies
    boss_disc = mill.unary_union([mill.sg.Point(sx, sy).buffer(PAD_R, quad_segs=mill.QS) for sx, sy in SCREWS[side]])
    under_boss = [k_pcb.intersect(cq.Solid.makeCylinder(PAD_R + 0.01, 30 + PCB_TOP, cq.Vector(sx, sy, -30)))
                  for sx, sy in SCREWS[side]]
    under_boss = [b for b in under_boss if b.Solids()]
    top_open, top_layers = mill.open_tools(tools + under_boss + squares + [hole], 'below', -30.0,
                               exclude=lambda z: boss_disc if z > PCB_TOP + 1e-3 else mill.sg.Polygon(),
                               log=lambda *a: log(side, 'top', *a))
    # the fill stays SEAM_GAP clear of the bottom, and off the board keep-out (bosses included)
    new_top = make_machinable(new_top, top_open, top_layers, 'below', drill_holes(side), f'{side} top',
                              extra=[mill.solid_keep_out(bot_raw, SEAM_GAP), mill.solid_keep_out(k_pcb, 0.0)])
    insert = window_insert(side, new_top, plug, flange_box, roof_z0, top_z)
    new_top.exportBrep(str(W / f'final_top_{side}.brep')); insert.exportBrep(str(W / f'final_insert_{side}.brep'))
    log(side, 'top done; roof underside', round(roof_z0, 3), 'top', round(top_z, 3))
    return new_top, insert


def finish(side, new_top, new_bot, insert, tools, pcb, part_names):
    sols_t = sorted(new_top.Solids(), key=lambda s: -s.Volume())
    sols_b = sorted(new_bot.Solids(), key=lambda s: -s.Volume())
    log(side, 'top solids', [round(s.Volume(), 2) for s in sols_t][:5], 'bottom solids', [round(s.Volume(), 2) for s in sols_b][:5])
    for nm, ss in [('top', sols_t[1:]), ('bottom', sols_b[1:])]:
        for f in ss:
            b = f.BoundingBox()
            log(side, nm, 'fragment at', [round(v, 2) for v in (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)], 'vol', round(f.Volume(), 3))
    new_top, new_bot = drop_voids(sols_t[0]), drop_voids(sols_b[0])
    new_top.exportBrep(str(W / f'final_top_{side}.brep')); new_bot.exportBrep(str(W / f'final_bottom_{side}.brep'))
    insert.exportBrep(str(W / f'final_insert_{side}.brep'))
    log(side, 'in-memory valid: top', new_top.isValid(), 'bottom', new_bot.isValid())
    if '--brep-only' in sys.argv:
        return None
    t = validate_step(new_top, OUT / f'TOTEM_alu_top_{side}.step')
    b = validate_step(new_bot, OUT / f'TOTEM_alu_bottom_{side}.step', volume_tol=0.02, write_pcurves=False)
    i = validate_step(insert, OUT / f'TOTEM_wood_window_insert_{side}.step')
    cq.exporters.export(cq.Compound.makeCompound(tools), str(W / f'keepout_{side}.step'))
    cq.exporters.export(pcb, str(W / f'pcb_{side}.step'))
    return dict(top=t, bottom=b, insert=i, pcb=pcb, keep=tools, part_names=part_names,
                dropped_top=[s.Volume() for s in sols_t[1:]], dropped_bottom=[s.Volume() for s in sols_b[1:]])


if __name__ == '__main__':
    parts = kicad_parts()
    log('kicad parts', len(parts))
    sides = [a for a in sys.argv[1:] if not a.startswith('--')] or ['L', 'R']
    for s in sides:
        r = build(s, parts)
        if r:
            log(s, 'dropped fragments top', r['dropped_top'], 'bottom', r['dropped_bottom'])
