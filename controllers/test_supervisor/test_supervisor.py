"""僅驗收用：搬動物件與讀取真值作評分，不將真值傳給產品控制器。"""
import sys,json,math,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from portable_support import record_runtime
record_runtime(__file__)
from controller import Supervisor
from common import ROOT,CONFIG
robot=Supervisor();step=int(robot.getBasicTimeStep())
block=robot.getFromDef('RED_BLOCK');field=block.getField('translation')
stages=[('center',0,.25,.73),('left',-.3,.25,.73),('right',.3,.25,.73),('absent',2,.25,.73),('return',0,.25,.73)]
records=[]
try:
 for name,x,y,z in stages:
    field.setSFVec3f([x,y,z])
    end=robot.getTime()+7
    while robot.getTime()<end:
        if robot.step(step)==-1:raise RuntimeError('Simulation stopped')
    vision=[json.loads(s) for s in (ROOT/'results/logs/vision.jsonl').read_text().splitlines() if s]
    arm=[json.loads(s) for s in (ROOT/'results/logs/arm.jsonl').read_text().splitlines() if s]
    d=vision[-1];a=arm[-1]
    recent_v=[v for v in vision if v['time']>robot.getTime()-2]
    recent_a=[v for v in arm if v['time']>robot.getTime()-2]
    expected='NO TARGET' if name=='absent' else 'DETECTED'
    checks={'detected':d['status']==expected,'fresh_vision':robot.getTime()-d['time']<.7,'fresh_arm':robot.getTime()-a['time']<.7,'motor_reached':abs(a['target']-a['actual'])<.06,'bounded':CONFIG['base_min']<=a['actual']<=CONFIG['base_max'],'stable':max(v['actual'] for v in recent_a)-min(v['actual'] for v in recent_a)<.04}
    if name=='left':checks['image_side']=d['cx'] is not None and d['cx']<260;checks['arm_direction']=a['actual']>CONFIG['base_center']+.1
    if name=='right':checks['image_side']=d['cx'] is not None and d['cx']>380;checks['arm_direction']=a['actual']<CONFIG['base_center']-.1
    if name in ('center','absent','return'):checks['centered']=abs(a['actual']-CONFIG['base_center'])<.05
    marker=robot.getFromDef('TOOL_MARKER')
    tool=marker.getPosition() if marker else None
    if name=='left' and tool: checks['tool_shifts_left']=tool[0]<records[0]['tool_world_test_only'][0]-.02
    if name=='right' and tool: checks['tool_shifts_right']=tool[0]>records[0]['tool_world_test_only'][0]+.02
    records.append(dict(stage=name,time=robot.getTime(),detection=d,arm=a,tool_world_test_only=tool,checks=checks))
    print('INTEGRATION',name,checks,flush=True)
 end=robot.getTime()+float(os.getenv('VISION_SOAK','0'))
 while robot.getTime()<end:
    if robot.step(step)==-1:raise RuntimeError('Soak interrupted')
 robot.exportImage(str(ROOT/'results/screenshots/integration_scene.jpg'),90)
 latest_v=json.loads((ROOT/'results/logs/vision.jsonl').read_text().splitlines()[-1])
 latest_a=json.loads((ROOT/'results/logs/arm.jsonl').read_text().splitlines()[-1])
 live=robot.getTime()-latest_v['time']<.7 and robot.getTime()-latest_a['time']<.7
 passed=live and all(all(r['checks'].values()) for r in records)
 (ROOT/'results/experiments/integration.json').write_text(json.dumps(dict(passed=passed,stages=records,end_time=robot.getTime(),soak_seconds=float(os.getenv('VISION_SOAK','0'))),indent=2),encoding='utf-8')
 robot.simulationQuit(0 if passed else 1)
except Exception as exc:
 (ROOT/'results/experiments/integration-error.txt').write_text(str(exc),encoding='utf-8');print(exc,flush=True);robot.simulationQuit(2)
