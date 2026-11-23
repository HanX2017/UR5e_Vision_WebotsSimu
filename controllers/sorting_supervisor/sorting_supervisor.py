"""只負責隨機建立、真值評分；對外狀態不含真實座標。"""
import sys,os,json,csv,random,time,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from portable_support import record_runtime
record_runtime(__file__)
import numpy as np
from controller import Supervisor
from sorting.settings import C,RUN
from sorting.comms import read_latest,send
r=Supervisor();step=int(r.getBasicTimeStep());root=r.getRoot().getField('children')
out=r.getDevice('manager_emitter');arm_rec=r.getDevice('arm_receiver');vision_rec=r.getDevice('vision_observer')
for dev in (arm_rec,vision_rec):dev.enable(step)
seed=C['seed'] if C['mode']=='fixed' else random.SystemRandom().randrange(2**31)
from sorting.scene import sample_scene
count=C['object_count']
colors,positions=sample_scene(seed,count)
# 新一輪只移除本專案先前動態產生的方塊，保留場景其他節點。
for index in range(root.getCount()-1,-1,-1):
    node=root.getMFNode(index)
    if node.getDef().startswith('SORT_BLOCK_'):node.remove()
blocks=[]
for i,(color,(x,y)) in enumerate(zip(colors,positions)):
 rgb={'RED':'0.9 0.02 0.02','GREEN':'0.02 0.85 0.03','BLUE':'0.02 0.04 0.9'}[color]
 text=f"""DEF SORT_BLOCK_{i} Solid {{ translation {x} {y} 0.735 name "sort block {i} {color}" contactMaterial "block" children [ Shape {{ appearance PBRAppearance {{ baseColor {rgb} roughness 1 metalness 0 }} geometry Box {{ size 0.06 0.06 0.06 }} }} ] boundingObject Box {{ size 0.06 0.06 0.06 }} physics Physics {{ density -1 mass 0.08 }} }}"""
 root.importMFNodeFromString(-1,text);blocks.append(dict(id=i,color=color,node=r.getFromDef(f'SORT_BLOCK_{i}')))
(RUN/'spawn_truth_validation_only.json').write_text(json.dumps(dict(seed=seed,colors=colors,positions=positions),indent=2))
tcp=r.getFromDef('GRIP_TCP');placed=set();lifted=set();stable={};active=None;status={};last_arm=-1;tick=0;last_state=None;ended=None;fk_errors=[];loc_errors=[];startwall=time.perf_counter();finished=False;pose_history={};last_fk_stamp=-1
truth_log=(RUN/'validation.jsonl').open('w',encoding='utf-8');loclog=(RUN/'localization.csv').open('w',newline='',encoding='utf-8');writer=csv.DictWriter(loclog,fieldnames=['time','color','u','v','estimated_x','estimated_y','true_x','true_y','error_x','error_y','error_xy']);writer.writeheader();loc_logged=set()
def finish(reason):
 global finished
 if finished:return
 finished=True
 duration=r.getTime();success=len(placed)==count and status.get('state')=='DONE'
 result=dict(seed=seed,total=count,correct=len(placed),failed=count-len(placed),grasped=len(lifted),duration_sim=duration,duration_wall=time.perf_counter()-startwall,success=success,state=status.get('state'),reason=reason,assist=False,fk_max_error=max(fk_errors,default=None),localization_max_error=max(loc_errors,default=None),objects=[dict(id=b['id'],color=b['color'],position=b['node'].getPosition(),sorted=b['id'] in placed) for b in blocks])
 (RUN/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 with (RUN/'trial.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['Seed','Total','Grasped','Correct','Failed','Duration','Success','Assist','Reason']);w.writeheader();w.writerow(dict(Seed=seed,Total=count,Grasped=len(lifted),Correct=len(placed),Failed=count-len(placed),Duration=duration,Success=success,Assist=False,Reason=reason))
 r.exportImage(str(RUN/'scene_final.jpg'),90);loclog.flush();truth_log.flush()
 print('SORT_RESULT',json.dumps({k:result[k] for k in ['seed','total','correct','grasped','success','reason']}),flush=True)
 if os.getenv('SORT_AUTO_QUIT')=='1':r.simulationQuit(0 if success else 1)
while r.step(step)!=-1:
 now=r.getTime();tick+=1
 packet=read_latest(arm_rec,now,.7)
 if packet:status=packet;last_arm=now
 detections=read_latest(vision_rec,now,.3)
 xyz=tcp.getPosition()
 pose_history[round(now,6)]=np.array(xyz)
 if packet and status.get('tcp_fk') and status['time']!=last_fk_stamp:
    stamp=round(status['time'],6)
    if stamp in pose_history:fk_errors.append(float(np.linalg.norm(pose_history[stamp]-status['tcp_fk'])))
    last_fk_stamp=status['time']
 if len(pose_history)>100:pose_history.pop(min(pose_history))
 # 定位真值只寫入驗證檔；不會從 manager emitter 發送。
 if detections and detections.get('usable') and status.get('state')=='DETECT':
    for d in detections.get('detections',[]):
        candidates=[b for b in blocks if b['color']==d['color'] and b['id'] not in placed]
        if not candidates:continue
        b=min(candidates,key=lambda b:np.linalg.norm(np.array(b['node'].getPosition()[:2])-d['xyz'][:2]))
        if b['id'] in loc_logged:continue
        p=b['node'].getPosition();ex=d['xyz'][0]-p[0];ey=d['xyz'][1]-p[1];err=math.hypot(ex,ey)
        writer.writerow(dict(time=now,color=d['color'],u=d['cx'],v=d['cy'],estimated_x=d['xyz'][0],estimated_y=d['xyz'][1],true_x=p[0],true_y=p[1],error_x=ex,error_y=ey,error_xy=err));loclog.flush();loc_errors.append(err);loc_logged.add(b['id'])
 held=False
 if status.get('state') in ('CLOSE_GRIPPER','LIFT_OBJECT','VERIFY_GRASP','MOVE_TO_BIN','PLACE_OBJECT'):
    target=status.get('target') or {}
    candidates=[b for b in blocks if b['color']==target.get('color') and b['id'] not in placed]
    if candidates:
        b=min(candidates,key=lambda b:np.linalg.norm(np.array(b['node'].getPosition())-xyz));distance=np.linalg.norm(np.array(b['node'].getPosition())-xyz)
        held=bool(distance<.045 and b['node'].getPosition()[2]>.82)
        if held:lifted.add(b['id']);active=b['id']
 for b in blocks:
    pos=np.array(b['node'].getPosition());R=np.array(b['node'].getOrientation()).reshape(3,3);half=.03*(abs(R[:,0])+abs(R[:,1])+abs(R[:,2]));bx,by=C['bins'][b['color']]
    contained=abs(pos[0]-bx)+half[0]<C['bin_inner']/2 and abs(pos[1]-by)+half[1]<C['bin_inner']/2 and abs(pos[2]-(C['bin_floor']+.03))<.012 and np.linalg.norm(b['node'].getVelocity()[:3])<.025
    if contained and b['id'] in lifted:
        stable.setdefault(b['id'],now)
        if now-stable[b['id']]>.7:placed.add(b['id'])
    else:
        stable.pop(b['id'],None)
        if b['id'] in placed:placed.remove(b['id'])
 if tick%4==0:
    send(out,now,ready=now>1,total=count,correct=len(placed),remaining=count-len(placed),held=held)
 if tick%16==0:
    target=status.get('target') or {}
    label=f"{status.get('state','STARTING')} | Seed {seed}\nSorted: {len(placed)}/{count}   Remaining: {count-len(placed)}   Failed: {status.get('failed',0)}\nTarget: {target.get('color','-')}"
    r.setLabel(0,label,.02,.02,.045,0xffffff,0,'Arial')
    truth_log.write(json.dumps(dict(time=now,state=status.get('state'),tcp=xyz,held=held,correct=len(placed),objects=[dict(id=b['id'],p=b['node'].getPosition()) for b in blocks]))+'\n');truth_log.flush()
 if now>2 and last_arm<0:finish('Arm controller failed to start')
 if status.get('state') in ('DONE','FAULT'):
    if ended is None:ended=now
    if now-ended>1.5:finish(status.get('reason') or 'Completed')
 if now>C['trial_timeout']:finish('Trial timeout')
 if tick==180:r.exportImage(str(RUN/'scene_initial.jpg'),90)
truth_log.close();loclog.close()
