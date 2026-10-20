import sys
import os; W=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,W)
import os; os.chdir(W)
from build import *
import trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
def mesh(s):
    v,t=s.tessellate(0.01,0.1); return trimesh.Trimesh(np.array([p.toTuple() for p in v]),np.array(t))
parts=kicad_parts()
fig,axs=plt.subplots(2,2,figsize=(16,7))
for r,side in enumerate('LR'):
    x0,x1=(105,145) if side=='L' else (165,205)
    pcb=mesh(pcb_solid(side))
    rs=[place(s,side) for n,s in parts if n in ('RSW1','RST') and (s.BoundingBox().xmin<150)==(side=='L')]
    sw=trimesh.util.concatenate([mesh(s) for s in rs[0].Solids()])
    for c,(lab,files) in enumerate([('ORIGINAL',[f'orig/TOTEM_case_ble_top_{side}_V.08.step',f'orig/TOTEM_tenting_live_bottom_{side}.step']),('NEW',[f'../outputs/TOTEM_alu_top_{side}.step',f'../outputs/TOTEM_alu_bottom_{side}.step'])]):
        case=trimesh.util.concatenate([mesh(load(f)) for f in files])
        xs=np.arange(x0,x1,0.1); zs=np.arange(-12,11,0.1); X,Z=np.meshgrid(xs,zs)
        P=np.c_[X.ravel(),np.full(X.size,-30.0),Z.ravel()]; dv=np.tile([0,-1.0,0],(X.size,1))
        img=np.ones(X.shape+(3,))
        dist={}
        for nm,m in (('case',case),('pcb',pcb),('sw',sw)):
            loc,ri,_=m.ray.intersects_location(P,dv,multiple_hits=False)
            d=np.full(X.size,np.inf); d[ri]=-30-loc[:,1]; dist[nm]=d
        which=np.argmin(np.c_[dist['case'],dist['pcb'],dist['sw']],axis=1); dmin=np.min(np.c_[dist['case'],dist['pcb'],dist['sw']],axis=1)
        cols=np.array([[0.7,0.72,0.75],[0.1,0.5,0.1],[0.15,0.15,0.15]])
        im=cols[which].copy()
        shade=np.clip(1-(dmin-17.5)/6,0.35,1)[:,None]; im=im*shade; im[np.isinf(dmin)]=1
        axs[r,c].imshow(im.reshape(X.shape+(3,)),origin='lower',extent=(x0,x1,-12,11)); axs[r,c].set_title(f'{lab} {side}: back face seen from outside (grey case, green PCB, dark = reset switch)')
plt.tight_layout(); plt.savefig(os.path.join(W, 'reset_back.png'),dpi=70)
