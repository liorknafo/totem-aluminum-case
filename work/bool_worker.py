"""One boolean in its own process, so the build can give up on it after a time limit
(OpenCASCADE now and then spends an hour on a cut it does in two minutes on a retry).
Usage: bool_worker.py fuse|cut FUZZY PART.brep TOOLS.brep OUT.brep"""
import sys
import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Cut
from OCP.TopTools import TopTools_ListOfShape

kind, fuzzy, part, tools, out = sys.argv[1], float(sys.argv[2]), *sys.argv[3:6]
p = cq.Shape.importBrep(part)
args, tl = TopTools_ListOfShape(), TopTools_ListOfShape()
args.Append(p.wrapped)
for t in cq.Shape.importBrep(tools).Solids():
    tl.Append(t.wrapped)
op = BRepAlgoAPI_Fuse() if kind == 'fuse' else BRepAlgoAPI_Cut()
op.SetArguments(args); op.SetTools(tl)
op.SetRunParallel(True); op.SetUseOBB(True); op.SetFuzzyValue(fuzzy)
op.Build()
if op.IsDone():
    cq.Shape.cast(op.Shape()).exportBrep(out)
