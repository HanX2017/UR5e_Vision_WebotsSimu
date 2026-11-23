import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from portable_support import record_runtime
record_runtime(__file__)
import json
from controller import Robot
from common import CONFIG, ROOT, JOINTS, BaseControl, decode_packet

def main():
    robot=Robot();step=int(robot.getBasicTimeStep());dt=step/1000
    motors=[];sensors=[]
    for name,angle in zip(JOINTS,CONFIG['initial_pose']):
        motor=robot.getDevice(name)
        if motor is None:
            raise RuntimeError('Missing motor: '+name)
        motor.setVelocity(min(CONFIG['max_speed'],motor.getMaxVelocity()))
        motor.setPosition(max(motor.getMinPosition(),min(motor.getMaxPosition(),angle)))
        sensor=robot.getDevice(name+'_sensor');sensor.enable(step)
        motors.append(motor);sensors.append(sensor)
    receiver=robot.getDevice('vision_receiver');receiver.enable(step);receiver.setChannel(CONFIG['channel'])
    control=BaseControl();last=None;last_seq=-1;tick=0
    with (ROOT/'results/logs/arm.jsonl').open('w',encoding='utf-8') as log:
        while robot.step(step)!=-1:
            now=robot.getTime()
            # 每回合清空佇列，只保留最新有效封包，絕不無限等待。
            while receiver.getQueueLength()>0:
                packet=decode_packet(receiver.getBytes(),now,last_seq)
                receiver.nextPacket()
                if packet:
                    last=packet;last_seq=packet['seq']
            active=last if last and now-last['time']<=CONFIG['timeout'] else None
            angle=control.update(active,dt)
            motors[0].setPosition(max(motors[0].getMinPosition(),min(motors[0].getMaxPosition(),angle)))
            tick+=1
            if tick%16==0:
                log.write(json.dumps(dict(time=now,status=active['status'] if active else 'STALE',seq=last_seq,target=angle,actual=sensors[0].getValue(),joints=[s.getValue() for s in sensors]))+'\n');log.flush()
if __name__=='__main__':
    main()
