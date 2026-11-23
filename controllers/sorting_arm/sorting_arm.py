import sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from portable_support import record_runtime
record_runtime(__file__)
import numpy as np
from controller import Robot
from sorting.settings import C,RUN,JOINTS
from sorting.kinematics import solve,fk,DOWN
from sorting.vision import pixel_to_world
from sorting.comms import read_latest,send

class Motion:
    def __init__(self,motors,sensors):self.motors=motors;self.sensors=sensors;self.queue=[]
    def q(self):return np.array([s.getValue() for s in self.sensors])
    def joint(self,q):self.queue=[np.array(q)]
    def cartesian(self,points):
        q=self.q();start=fk(q)[0];queue=[]
        # 事先驗證整條笛卡兒路徑，不可解即不執行，移動過程逐點等待回授。
        for end in points:
            end=np.asarray(end,float);n=max(1,int(np.ceil(np.linalg.norm(end-start)/.028)))
            for i in range(1,n+1):
                q=solve(start+(end-start)*i/n,q);queue.append(q)
            start=end
        self.queue=queue
    def tick(self):
        if not self.queue:return True
        q=self.queue[0]
        for m,a in zip(self.motors,q):m.setPosition(float(a))
        if max(abs(self.q()-q))<.009:self.queue.pop(0)
        return not self.queue
    def stop(self):
        self.queue=[]
        for m,a in zip(self.motors,self.q()):m.setPosition(float(a))

def main():
    r=Robot();step=int(r.getBasicTimeStep());motors=[];sensors=[]
    for name in JOINTS:
        m=r.getDevice(name);m.setVelocity(min(C['max_joint_speed'],m.getMaxVelocity()));s=r.getDevice(name+'_sensor');s.enable(step);motors.append(m);sensors.append(s)
    fingers=[r.getDevice('panda_finger::'+side) for side in ('right','left')]
    finger_sensors=[r.getDevice('panda_finger::'+side+'_sensor') for side in ('right','left')]
    for m,s in zip(fingers,finger_sensors):m.setVelocity(.06);m.setAvailableForce(35);m.setPosition(.04);s.enable(step)
    vr=r.getDevice('vision_receiver');mr=r.getDevice('manager_receiver');out=r.getDevice('arm_status')
    for rec in (vr,mr):rec.enable(step)
    motion=Motion(motors,sensors);state='BOOT';entered=0;target=None;manager={};vision=None;last_manager=-1;failed=0;reason='';tick=0;baseline=0;slots={c:0 for c in C['bins']};holding=False;assist_used=False;place=None
    events=(RUN/'arm_events.jsonl').open('w',encoding='utf-8');telemetry=(RUN/'arm.jsonl').open('w',encoding='utf-8')
    def transition(name):
        nonlocal state,entered
        state=name;entered=r.getTime();events.write(json.dumps(dict(time=entered,state=name,target=target))+'\n');events.flush()
    def fail(message):
        nonlocal failed,reason
        failed+=1;reason=message;motion.stop();transition('FAULT')
    if r.step(step)==-1:return
    motion.joint(solve(C['home']));transition('BOOT')
    try:
      while r.step(step)!=-1:
        now=r.getTime();elapsed=now-entered;tick+=1
        d=read_latest(vr,now,C['packet_timeout'])
        if d:vision=d
        d=read_latest(mr,now,.7)
        if d:manager=d;last_manager=now
        completed=motion.tick()
        try:
            if state not in ('BOOT','DONE','FAULT') and now-last_manager>.8:raise RuntimeError('Supervisor heartbeat lost')
            if state not in ('BOOT','DONE','FAULT','DETECT') and elapsed>C['motion_timeout']*2:raise RuntimeError('State timeout: '+state)
            if state=='BOOT' and completed and manager.get('ready'):
                transition('DETECT')
            elif state=='BOOT' and elapsed>20:raise RuntimeError('Home initialization timeout')
            elif state=='DETECT':
                if manager.get('correct')==manager.get('total') and manager.get('total',0)>0:transition('DONE')
                elif vision and now-vision['time']<C['packet_timeout'] and vision.get('usable'):
                    candidates=[]
                    for v in vision.get('detections',[]):
                        if not isinstance(v,dict) or v.get('color') not in C['bins']:continue
                        if not all(type(v.get(k)) in (int,float) and math.isfinite(v[k]) for k in ('cx','cy')):continue
                        if not (0<=v['cx']<C['width'] and 0<=v['cy']<C['height']):continue
                        xyz=pixel_to_world(v['cx'],v['cy']);xmin,xmax,ymin,ymax=C['initial_bounds']
                        if xmin<xyz[0]<xmax and ymin<xyz[1]<ymax:candidates.append(dict(v,xyz=xyz))
                    if candidates:
                        target=min(candidates,key=lambda v:np.linalg.norm(v['xyz'][:2]));color=target['color']
                        if slots[color]>=4:raise RuntimeError('Bin capacity exceeded')
                        slot=[(-.042,-.042),(.042,-.042),(-.042,.042),(.042,.042)][slots[color]]
                        bx,by=C['bins'][color];place=[bx+slot[0],by+slot[1],C['place_z']]
                        baseline=manager.get('correct',0);holding=False;assist_used=False
                        motion.cartesian([[target['xyz'][0],target['xyz'][1],C['safe_z']]]);transition('MOVE_TO_PRE_GRASP')
                if state=='DETECT' and elapsed>6:raise RuntimeError('No reliable ROI target while objects remain')
            elif state=='MOVE_TO_PRE_GRASP' and completed:
                motion.cartesian([target['xyz']]);transition('MOVE_TO_GRASP')
            elif state=='MOVE_TO_GRASP' and completed:
                for m in fingers:m.setPosition(0)
                transition('CLOSE_GRIPPER')
            elif state=='CLOSE_GRIPPER' and elapsed>.65:
                positions=[s.getValue() for s in finger_sensors]
                if not all(0<=q<.035 for q in positions):raise RuntimeError('Fingers did not close onto object')
                motion.cartesian([[target['xyz'][0],target['xyz'][1],C['safe_z']]]);transition('LIFT_OBJECT')
            elif state=='LIFT_OBJECT' and completed:transition('VERIFY_GRASP')
            elif state=='VERIFY_GRASP':
                if manager.get('held'):
                    holding=True
                    motion.cartesian([[C['home'][0],C['home'][1],C['safe_z']],[place[0],place[1],C['safe_z']]])
                    transition('MOVE_TO_BIN')
                elif elapsed>1:raise RuntimeError('Grasp verification failed: block did not follow lift')
            elif state=='MOVE_TO_BIN':
                if holding and not manager.get('held') and elapsed>.4:raise RuntimeError('Object dropped during transport')
                if completed:motion.cartesian([place]);transition('PLACE_OBJECT')
            elif state=='PLACE_OBJECT' and completed:
                for m in fingers:m.setPosition(.04)
                holding=False;transition('OPEN_GRIPPER')
            elif state=='OPEN_GRIPPER' and elapsed>.45:
                motion.cartesian([[place[0],place[1],C['safe_z']]]);transition('VERIFY_PLACEMENT')
            elif state=='VERIFY_PLACEMENT':
                if completed and manager.get('correct',0)>baseline:
                    slots[target['color']]+=1
                    motion.cartesian([C['home']]);transition('RETURN_HOME')
                elif elapsed>8:raise RuntimeError('Released object not stable inside matching bin')
            elif state=='RETURN_HOME' and completed:target=None;transition('DETECT')
        except Exception as exc:
            if state!='FAULT':fail(str(exc))
        if tick%4==0:
            tcp,R=fk(motion.q())
            report=dict(state=state,target=target,sorted=manager.get('correct',0),total=manager.get('total',0),remaining=manager.get('total',0)-manager.get('correct',0),failed=failed,reason=reason,tcp_fk=tcp.tolist(),q=motion.q().tolist(),fingers=[s.getValue() for s in finger_sensors],assist=assist_used,connector_locked=False)
            send(out,now,**report)
            telemetry.write(json.dumps(dict(time=now,**report))+'\n')
            if tick%32==0:telemetry.flush()
    finally:events.close();telemetry.close()
if __name__=='__main__':main()
