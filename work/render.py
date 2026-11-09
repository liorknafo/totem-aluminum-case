"""Offscreen VTK renders of the case parts (and the board and its parts) to PNG.

    python -E -s render.py            # all pictures for docs/images and outputs/
"""
import math
import sys
from pathlib import Path

import cadquery as cq
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray

W = Path(__file__).resolve().parent
ROOT = W.parent
OUT = ROOT / 'outputs'
DOCS = ROOT / 'docs' / 'images'

ALU = (0.80, 0.82, 0.85)
ALU_DARK = (0.62, 0.64, 0.68)
WOOD = (0.80, 0.58, 0.34)
PCB = (0.10, 0.42, 0.20)
PART = (0.18, 0.18, 0.20)
KEYCAP = (0.93, 0.93, 0.90)
COPPER = (0.85, 0.62, 0.25)
BATTERY = (0.88, 0.80, 0.55)


def mesh(shape, tol=0.03, ang=0.2):
    v, f = shape.tessellate(tol, ang)
    return np.array([p.toTuple() for p in v], float), np.array(f, np.int64).reshape(-1, 3)


def polydata(V, F):
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(np.ascontiguousarray(V), deep=True))
    cells = np.hstack([np.full((len(F), 1), 3, np.int64), F]).ravel()
    ca = vtk.vtkCellArray()
    ca.SetCells(len(F), numpy_to_vtkIdTypeArray(cells, deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(ca)
    n = vtk.vtkPolyDataNormals()
    n.SetInputData(pd)
    n.SetFeatureAngle(35)
    n.SplittingOn()
    n.ConsistencyOn()
    n.Update()
    return n.GetOutput()


def actor(shape_or_mesh, color, opacity=1.0, tol=0.03, edges=False, specular=0.25):
    V, F = shape_or_mesh if isinstance(shape_or_mesh, tuple) else mesh(shape_or_mesh, tol)
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(polydata(V, F))
    a = vtk.vtkActor()
    a.SetMapper(m)
    p = a.GetProperty()
    p.SetColor(*color)
    p.SetOpacity(opacity)
    p.SetSpecular(specular)
    p.SetSpecularPower(30)
    p.SetDiffuse(0.85)
    p.SetAmbient(0.18)
    if edges:
        fe = vtk.vtkFeatureEdges()
        fe.SetInputData(polydata(V, F))
        fe.BoundaryEdgesOff(); fe.FeatureEdgesOn(); fe.ManifoldEdgesOff(); fe.NonManifoldEdgesOff()
        fe.SetFeatureAngle(30)
        fm = vtk.vtkPolyDataMapper(); fm.SetInputConnection(fe.GetOutputPort()); fm.ScalarVisibilityOff()
        ea = vtk.vtkActor(); ea.SetMapper(fm); ea.GetProperty().SetColor(0.25, 0.27, 0.3); ea.GetProperty().SetLineWidth(1.0)
        ea.GetProperty().SetOpacity(min(1.0, opacity * 0.8))
        return [a, ea]
    return [a]


def render(actors, path, view=(0.3, -1.0, 0.9), up=(0, 0, 1), size=(1600, 1000), zoom=1.0, focus=None,
           bg=(0.96, 0.96, 0.97), parallel=False):
    ren = vtk.vtkRenderer()
    ren.SetBackground(*bg)
    for a in actors:
        ren.AddActor(a)
    ren.SetUseDepthPeeling(True)
    ren.SetMaximumNumberOfPeels(8)
    lk = vtk.vtkLightKit()
    lk.SetKeyLightIntensity(0.85)
    lk.AddLightsToRenderer(ren)
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetMultiSamples(8)
    win.SetAlphaBitPlanes(1)
    win.AddRenderer(ren)
    win.SetSize(*size)
    cam = ren.GetActiveCamera()
    ren.ResetCamera()
    b = ren.ComputeVisiblePropBounds()
    c = focus or ((b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2)
    r = math.dist((b[0], b[2], b[4]), (b[1], b[3], b[5])) / 2
    d = np.array(view, float); d /= np.linalg.norm(d)
    cam.SetFocalPoint(*c)
    cam.SetPosition(*(np.array(c) + d * r * 4.2))
    cam.SetViewUp(*up)
    cam.SetViewAngle(28)
    if parallel:
        cam.ParallelProjectionOn()
        cam.SetParallelScale(r * 0.62 / zoom)
    else:
        cam.Zoom(zoom)
    ren.ResetCameraClippingRange()
    win.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(win)
    w2i.SetInputBufferTypeToRGB()
    w2i.ReadFrontBufferOff()
    w2i.Update()
    wr = vtk.vtkPNGWriter()
    wr.SetFileName(str(path))
    wr.SetInputConnection(w2i.GetOutputPort())
    wr.Write()
    return path


def load(p):
    return cq.importers.importStep(str(p)).val()


COLORS = dict(top=ALU, bottom=ALU_DARK, insert=WOOD, pcb=PCB, switches=(0.36, 0.38, 0.41), parts=PART,
              xiao=(0.20, 0.40, 0.69), battery=BATTERY, screws=(0.35, 0.36, 0.38), caps=KEYCAP)
EDGES = {'top', 'bottom', 'insert'}


def scene_actors(layers, sides=('L', 'R'), dz=None, opacity=None):
    """Actors for the chosen layers of the chosen halves; dz moves layers up or down (explode)."""
    import scene
    dz = dz or {}
    opacity = opacity or {}
    acts = []
    for side in sides:
        L = scene.layers(side)
        for name in layers:
            v, f = scene.shifted(side, L[name])
            if not len(v):
                continue
            v = v + np.array((0, 0, dz.get(name, 0.0)))
            acts += actor((v, f), COLORS[name], opacity=opacity.get(name, 1.0), edges=name in EDGES)
    return acts


def pictures():
    import scene
    from PIL import Image
    DOCS.mkdir(parents=True, exist_ok=True)
    allp = ['top', 'insert', 'bottom', 'pcb', 'switches', 'parts', 'xiao', 'battery', 'screws']
    iso = (0.3, -0.85, 1.05)
    render(scene_actors(allp + ['caps']), DOCS / 'case_assembled.png', view=iso, zoom=1.35)
    render(scene_actors(allp), DOCS / 'case_no_keycaps.png', view=iso, zoom=1.35)
    ex = dict(top=24, insert=24, screws=-16, bottom=-16, battery=-16, caps=40)
    render(scene_actors(allp + ['caps'], ('L',), dz=ex), DOCS / 'case_exploded.png', view=(0.45, -0.9, 0.55), zoom=1.25)
    render(scene_actors(allp, ('L',), opacity={'top': 0.28}), DOCS / 'case_see_through.png', view=iso, zoom=1.3)
    render(scene_actors(allp, ('L',), dz=dict(top=10, insert=10, bottom=-8, battery=-8, screws=-8)),
           DOCS / 'case_side.png', view=(0.05, -1, 0.12), zoom=1.3)
    render(scene_actors(['top', 'bottom', 'screws']), DOCS / 'case_underside.png', view=(0.3, -0.85, -1.05), zoom=1.35)
    # per half: the parts on their own, 2 x 2
    for side in 'LR':
        tiles = []
        for layers_, view, nm in ((['top', 'insert'], (0.25, -0.9, 1.1), 'a'), (['top'], (0.25, -0.9, -1.1), 'b'),
                                  (['bottom'], (0.25, -0.9, 1.1), 'c'), (['bottom'], (0.25, -0.9, -1.1), 'd')):
            p = render(scene_actors(layers_, (side,)), f'/tmp/render_{side}_{nm}.png', view=view, size=(1000, 700), zoom=1.45)
            tiles.append(Image.open(p))
        im = Image.new('RGB', (2000, 1400), 'white')
        for i, t in enumerate(tiles):
            im.paste(t, ((i % 2) * 1000, (i // 2) * 700))
        im.save(OUT / f'render3d_{side}.png')
    # the side openings: USB-C, power slider and reset slot (left half)
    d = scene.design('L')
    render(scene_actors(['top', 'bottom', 'pcb', 'parts', 'xiao', 'switches'], ('L',)), OUT / 'openings_L.png',
           view=(-0.2, 1.0, 0.25), zoom=2.2, size=(1800, 800))
    print('pictures written')


if __name__ == '__main__':
    pictures()
