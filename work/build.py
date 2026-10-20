"""Aluminum TOTEM case: keep every aluminum surface clear of the PCB and its parts.

Inputs are copies (work/orig, src/); originals in ~/Downloads are never touched.
Units mm. Case coordinates = the original STEP coordinates (KiCad x, -y for the left half).
"""
import sys, json, time
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
DOGBONE_R = 0.52   # corner reliefs in the 13.8 mm switch cut-outs, for a 1 mm end mill (2 mm ones meet across the 3.2 mm webs)
LEDGE = (2.4, 3.7) # z span of the 1.2 mm switch clip ledge (2.45..3.65); the relief stays over the 16 mm recess below
R_SHIFT = 7.96     # KiCad right half -> right case (matches the right top's screw bores)
SCREWS = {'L': [(57, -52.7), (34.3, -121.014348), (139.5, -112), (131.2, -52.7)]}
SCREWS['R'] = [(168.46, -112.0), (176.76, -52.7), (250.96, -52.7), (273.66, -121.0)]
XIAO = {'L': ((41.2, -59.6), 90.0), 'R': ((258.8 + R_SHIFT, -59.6), -90.0)}
OUT = W.parent / 'outputs'
OUT.mkdir(exist_ok=True)
T0 = time.monotonic()


def log(*a):
    print(f'[{time.monotonic() - T0:6.1f}s]', *a, flush=True)


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


def thicken_thin_floors(tools, bot, skin):
    """A pocket floor must be at least `skin` thick. Where the underside below a pocket comes
    within `skin` of its floor (leftover bits of the old leg-recess roof, sloped edges), add a pad
    underneath so the floor stays `skin` thick. Through-openings (no material at all) stay open."""
    import trimesh, shapely.geometry as sg
    from shapely.ops import unary_union
    v, f = bot.tessellate(0.005, 0.05)
    m = trimesh.Trimesh(np.array([p.toTuple() for p in v]), np.array(f))
    pads, where = [], []
    for t in tools:
        b = t.BoundingBox()
        if b.zmin > -C - 0.05:
            continue
        foot = sg.MultiPoint([v.toTuple()[:2] for v in t.Vertices()]).convex_hull
        xs = np.arange(b.xmin, b.xmax, 0.1); ys = np.arange(b.ymin, b.ymax, 0.1)
        P = np.array([(x, y) for x in xs for y in ys if foot.contains(sg.Point(x, y))])
        if len(P) == 0:
            continue
        loc, idx, _ = m.ray.intersects_location(np.c_[P, np.full(len(P), -20.0)], np.tile([0, 0, 1.0], (len(P), 1)),
                                                multiple_hits=False)
        U = np.full(len(P), -99.0); U[idx] = np.asarray(loc).reshape(-1, 3)[:, 2]
        thin = P[(U < b.zmin) & (U > b.zmin - skin)]
        if len(thin) == 0:
            continue
        region = unary_union([sg.Point(x, y).buffer(0.12, quad_segs=4) for x, y in thin]).buffer(0.05).simplify(0.02)
        for g in (region.geoms if region.geom_type == 'MultiPolygon' else [region]):
            if g.area > 0.01:
                pads.append(cq.Solid.extrudeLinear(poly_face(g, b.zmin - skin - 0.05), cq.Vector(0, 0, skin + 0.05)))
        where.append((round((b.xmin + b.xmax) / 2, 1), round((b.ymin + b.ymax) / 2, 1), len(thin)))
    return pads, where


def xiao_keepout(side):
    """The XIAO module has no KiCad model; use the site's model extents (local frame)."""
    (x, y), a = XIAO[side]
    loc = box(-8.9, 8.9, -10.6, 11.9, 1.66, 5.93)
    s = obb_box(loc, C).rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), a).translate(cq.Vector(x, y, 0))
    return s


# ------------------------------------------------------------ wood window
def window_parts(side, top):
    """Opening in the roof above the XIAO plus a matching wood insert (plug + flange under the roof)."""
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
    flange_t = 1.5
    flange_box = local(W_X[0] - 1.5, W_X[1] + 1.5, W_Y[0] - 1.5, W_Y[1] + 1.5, roof_z0 - flange_t, roof_z0, 1.0)
    # flange must clear the cavity walls by 0.2: subtract the top grown sideways
    walls = top.intersect(box(x - 20, x + 20, y - 20, y + 20, roof_z0 - flange_t - 0.01, roof_z0 + 0.01))
    flange = flange_box
    for dx, dy in [(0.2, 0), (-0.2, 0), (0, 0.2), (0, -0.2), (0.14, 0.14), (-0.14, 0.14), (0.14, -0.14), (-0.14, -0.14), (0, 0)]:
        flange = flange.cut(walls.translate(cq.Vector(dx, dy, 0)))
    sols = sorted(flange.Solids(), key=lambda s: -s.Volume())
    insert = plug.fuse(sols[0]).clean()
    insert = sorted(insert.cut(top.cut(hole)).Solids(), key=lambda s: -s.Volume())[0]  # never overlap the aluminum
    assert insert.BoundingBox().zmax > top_z - 1e-3, 'insert lost its plug'
    return hole, insert, roof_z0, top_z


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


def dogbones(top):
    """Corner reliefs for every ~13.8 mm square switch cut-out in the clip ledge, so a round
    end mill leaves room for the switch's square corners."""
    sec = top.intersect(box(-50, 450, -300, 50, 2.99, 3.01))
    face = [f for f in sec.Faces() if f.normalAt().z > 0.99 and f.Center().z > 3.005]
    cyl = []
    for f in face:
        for w in f.innerWires():
            vs = [v.toTuple()[:2] for v in w.Vertices()]
            if len(vs) != 4:
                continue
            c = np.mean(vs, axis=0)
            sides = [np.hypot(*(np.subtract(vs[i], vs[(i + 1) % 4]))) for i in range(4)]
            if not all(13.6 < L < 14.1 for L in sides):
                continue
            for v in vs:
                d = np.subtract(v, c); d /= np.linalg.norm(d)
                o = np.add(v, d * (DOGBONE_R - 0.05))  # circle on the diagonal, covering the corner
                cyl.append(cq.Solid.makeCylinder(DOGBONE_R, LEDGE[1] - LEDGE[0], cq.Vector(o[0], o[1], LEDGE[0])))
    return cyl


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


def validate_step(shape, path):
    """Write, read back; if the STEP round trip leaves the solid invalid, heal and try again."""
    vol = shape.Volume()
    tried = []
    for src in (shape, None):
        base = shape if src is not None else back
        for how, cand in heal_candidates(base):
            sols = cand.Solids()
            if len(sols) != 1 or abs(sols[0].Volume() - vol) > 1e-5 * abs(vol) + 0.05:
                tried.append((how, 'changed')); continue
            cq.exporters.export(sols[0], str(path))
            back = cq.importers.importStep(str(path)).val()
            ok = back.isValid() and len(back.Solids()) == 1 and abs(back.Volume() - vol) < 1e-5 * abs(vol) + 0.05
            tried.append((how, ok))
            if ok:
                if how != 'as is':
                    log(path.name, 'healed by', how)
                return back
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
    pads, where = thicken_thin_floors(tools, bot, SKIN)
    if pads:
        bot = bot.fuse(*pads).clean()
    log(side, 'thin pocket floors padded from below at', where)
    tools = [k_pcb, k_xiao] + tools
    log(side, 'keep-outs: parts', len(k_parts), 'pads', len(k_pads), '-> merged under', n_merged, 'switches; total', len(tools))
    keep = cq.Compound.makeCompound(tools)

    seam = SEAM_Z0 + SEAM_RAISE
    top_hi = top.intersect(box(-50, 450, -300, 50, seam, 50))
    # the bottom rim grows up by SEAM_RAISE under the old skirt footprint (old gap filled, new gap kept)
    ring = top.intersect(box(-50, 450, -300, 50, SEAM_Z0, seam - SEAM_GAP))
    skirt = ring.fuse(ring.translate(cq.Vector(0, 0, -SEAM_GAP - 0.05))).clean()
    bosses = [top.intersect(cq.Solid.makeCylinder(PAD_R, PCB_TOP + C + 0.2, cq.Vector(sx, sy, PCB_TOP)))
              for sx, sy in SCREWS[side]]
    new_top = fast_cut(top_hi, tools)
    log(side, 'top cut')
    new_top = new_top.fuse(*[b for b in bosses if b.Solids()]).clean()
    hole, insert, roof_z0, top_z = window_parts(side, top)
    new_top = new_top.cut(hole).clean()
    bones = dogbones(new_top)
    new_top = new_top.cut(*bones).clean()
    log(side, 'switch cut-outs with corner reliefs:', len(bones) // 4)
    log(side, 'top done; roof underside', round(roof_z0, 3), 'top', round(top_z, 3))

    new_bot = bot.fuse(skirt).clean()
    new_bot = fast_cut(new_bot, tools).clean()
    log(side, 'bottom done')

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
    b = validate_step(new_bot, OUT / f'TOTEM_alu_bottom_{side}.step')
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
