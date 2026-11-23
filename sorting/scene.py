"""只供 Supervisor 與本機生成測試使用，不匯入視覺／手臂控制器。"""
import random,math
from .settings import C

def sample_scene(seed,count):
    if not 3<=count<=6:raise ValueError('object_count must be 3..6')
    rng=random.Random(seed)
    colors=['RED','GREEN','BLUE']+[rng.choice(['RED','GREEN','BLUE']) for _ in range(count-3)]
    rng.shuffle(colors)
    xmin,xmax,ymin,ymax=C['spawn_bounds']
    for scene_attempt in range(100):
        positions=[]
        for i in range(count):
            for attempt in range(1500):
                x=rng.uniform(xmin,xmax);y=rng.uniform(ymin,ymax)
                if all(math.hypot(x-p[0],y-p[1])>.105 for p in positions):positions.append((x,y));break
            else:break
        if len(positions)==count:return colors,positions
    raise RuntimeError('Could not sample separated blocks')
