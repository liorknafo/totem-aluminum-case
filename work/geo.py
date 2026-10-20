import sys as _s; _s.path.append(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)),"..","pylib"))
import cadquery as cq, numpy as np
from pathlib import Path
W=Path(__file__).resolve().parent
MIRROR_X_SUM=307.86189
SCREWS_L=[(57,-52.7),(34.3,-121.014348),(139.5,-112),(131.2,-52.7)]
def load(p): return cq.importers.importStep(str(W/p)).val()
def pcb_L():
    b=load('../src/pcb_board.step').Solids()[0]
    clip=cq.Solid.makeBox(140,120,10,cq.Vector(15,-150,-5))
    s=b.intersect(clip)
    sols=sorted(s.Solids(),key=lambda x:-x.Volume())
    return sols[0]
def section(shape,z):
    """list of polylines (Nx2) of the shape's cut at height z"""
    pl=cq.Face.makePlane(600,600,basePnt=(150,-100,z))
    try:
        cut=shape.intersect(pl)
    except Exception: return []
    out=[]
    for e in cut.Edges():
        pts=[e.positionAt(t).toTuple() for t in np.linspace(0,1,max(2,int(e.Length()/0.3)+2))]
        out.append(np.array(pts)[:,:2])
    return out

def vsection(shape, axis, val):
    """vertical cut: axis 'y' => plane y=val, returns (x,z) polylines; axis 'x' => plane x=val, returns (y,z)"""
    if axis=='y': pl=cq.Face.makePlane(600,600,basePnt=(150,val,0),dir=(0,1,0))
    else: pl=cq.Face.makePlane(600,600,basePnt=(val,-100,0),dir=(1,0,0))
    try: cut=shape.intersect(pl)
    except Exception: return []
    out=[]
    for e in cut.Edges():
        p=np.array([e.positionAt(t).toTuple() for t in np.linspace(0,1,max(2,int(e.Length()/0.1)+2))])
        out.append(p[:,[0,2]] if axis=='y' else p[:,[1,2]])
    return out

def comp_solids(side='L', kinds=('switch','socket','electronics','battery')):
    """site component meshes -> list of (kind, trimesh) placed"""
    import sys; sys.path.insert(0,str(W))
    from common import placed
    return placed(set(kinds), side)
