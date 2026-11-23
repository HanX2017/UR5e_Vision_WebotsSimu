"""由 R2023b 官方 UR5e PROTO 的零姿態、軸與位移建立 FK；不依賴 Supervisor。"""
import numpy as np
import cv2
from scipy.optimize import least_squares
from .settings import C

def rot(axis,angle):
    axis=np.asarray(axis,dtype=float)
    return cv2.Rodrigues(axis*angle)[0]
RX=rot([1,0,0],-np.pi/2)
DOWN=np.diag([1.,-1.,-1.])@rot([0,0,1],np.pi/4)
OFFSETS=[(0,0,.163),(0,.138,0),(0,-.131,.425),(0,0,.392),(0,.127,0),(0,0,.1)]
AXES=[(0,0,1),(0,1,0),(0,1,0),(0,1,0),(0,0,1),(0,1,0)]
ZERO=[0,np.pi/2,0,np.pi/2,0,0]
LIMITS=np.array([[-6.28,6.28],[-3.1,1.5],[-3.14,3.14],[-6.28,6.28],[-6.28,6.28],[-6.28,6.28]])

def fk(q,details=False):
    p=np.array(C['base'],float);R=np.eye(3);points=[]
    for offset,axis,z,angle in zip(OFFSETS,AXES,ZERO,q):
        p=p+R@offset
        R=R@rot(axis,angle+z)
        points.append(p.copy())
    p=p+R@np.array([0,.1,0])
    R=R@RX
    p=p+R@np.array([0,0,.105])
    return (p,R,points) if details else (p,R)

def residual(q,target):
    p,R=fk(q)
    angular=cv2.Rodrigues(DOWN@R.T)[0][:,0]
    return np.r_[p-target,.25*angular]

def solve(target,seed=None):
    target=np.asarray(target,float)
    if not np.isfinite(target).all() or np.linalg.norm(target-np.array(C['base']))>1.03 or target[2]<.72:
        raise ValueError('Target outside safe workspace')
    starts=[]
    if seed is not None:starts.append(np.asarray(seed))
    angle=np.arctan2(target[1],target[0])
    starts.extend([np.array([angle,-1.2,-1.5,-1.5,1.57,0]),np.array([angle,-1.5,1.5,-1.5,-1.57,0]),np.array([angle-1,-1,-1.5,-2,1.57,0])])
    best=None
    for start in starts:
        fit=least_squares(residual,np.clip(start,LIMITS[:,0]+1e-6,LIMITS[:,1]-1e-6),args=(target,),bounds=(LIMITS[:,0],LIMITS[:,1]),max_nfev=110,ftol=1e-8,xtol=1e-8,gtol=1e-8)
        err=np.linalg.norm(residual(fit.x,target))
        _,_,pts=fk(fit.x,True)
        # 除基座／肩部外的關節中心必須高於工作台，排除穿台 IK 分支。
        clearance=all(p[2]>.76 for p in pts[2:]) and fit.x[2]>.15
        if err<.0006 and clearance:
            best=fit.x.copy()
            if seed is not None:
                for j in (0,3,4,5):
                    candidates=[best[j]+k*2*np.pi for k in (-1,0,1)]
                    best[j]=min((v for v in candidates if LIMITS[j,0]<=v<=LIMITS[j,1]),key=lambda v:abs(v-seed[j]))
            break
    if best is None:raise ValueError(f'IK failed at {target.tolist()}')
    return best
