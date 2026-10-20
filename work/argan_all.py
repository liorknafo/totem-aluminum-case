import sys; sys.path.insert(0,'.')
from geo import *
from OCP.BOPAlgo import BOPAlgo_ArgumentAnalyzer
import collections
for f in ['TOTEM_alu_top_L','TOTEM_alu_top_R','TOTEM_alu_bottom_L','TOTEM_alu_bottom_R','TOTEM_wood_window_insert_L','TOTEM_wood_window_insert_R']:
    s=cq.importers.importStep(f'../outputs/{f}.step').val()
    aa=BOPAlgo_ArgumentAnalyzer(); aa.SetShape1(s.wrapped)
    aa.SelfInterMode=True; aa.SmallEdgeMode=True; aa.ArgumentTypeMode=True; aa.CurveOnSurfaceMode=True
    aa.Perform()
    c=collections.Counter(str(r.GetCheckStatus()).split('.')[-1] for r in aa.GetCheckResult())
    print(f,'valid',s.isValid(),'solids',len(s.Solids()),'shells',len(s.Shells()),'closed',all(x.Closed() for x in s.Shells()),'analyzer:',dict(c),flush=True)
