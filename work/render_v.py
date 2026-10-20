import sys; sys.path.insert(0,'.')
from geo import *
import trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
top=load(sys.argv[1]); bot=load(sys.argv[2]); pcb=pcb_L(); out=sys.argv[3]
comps=comp_solids('L')
cuts=[(a[0],float(a[1:])) for a in sys.argv[4].split(',')] if len(sys.argv)>4 else [('y',-62.6),('y',-112),('y',-52.7),('x',103.1),('x',57),('x',45)]
fig,axs=plt.subplots(len(cuts),1,figsize=(24,4.2*len(cuts)))
for ax,(a,v) in zip(axs,cuts):
    for s,c in [(top,'tab:blue'),(bot,'tab:red'),(pcb,'green')]:
        for l in vsection(s,a,v): ax.plot(l[:,0],l[:,1],color=c,lw=0.9)
    n=[0,1,0] if a=='y' else [1,0,0]; o=[0,v,0] if a=='y' else [v,0,0]
    for m in comps:
        s=m.section(n,o)
        if s is None: continue
        segs=s.discrete
        col={'switch':'0.5','socket':'purple','electronics':'orange','battery':'brown'}[m.metadata['kind']]
        for sg in segs: ax.plot(sg[:,0] if a=='y' else sg[:,1], sg[:,2], color=col, lw=0.6)
    ax.set_title(f'section {a}={v}  blue=top red=bottom green=PCB grey=switch purple=socket orange=electronics')
    ax.set_aspect('equal'); ax.grid(alpha=.3); ax.set_ylim(-13,12)
plt.tight_layout(); plt.savefig(out,dpi=60)
