import sys,os,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from portable_support import record_runtime
record_runtime(__file__)
import cv2,numpy as np
from controller import Robot
from sorting.settings import C,RUN
from sorting.vision import detect_all,world_to_pixel
from sorting.comms import read_latest,send
r=Robot();step=int(r.getBasicTimeStep())
cam=r.getDevice('overhead_camera');cam.enable(64)
out=r.getDevice('vision_emitter');incoming=r.getDevice('arm_status_receiver');incoming.enable(step)
show=C['show_window'] and os.getenv('SORT_HEADLESS')!='1'
seq=0;previous=-1;status={};last_status=-1
with (RUN/'vision.jsonl').open('w',encoding='utf-8') as log:
 while r.step(step)!=-1:
    now=r.getTime();packet=read_latest(incoming,now,.6)
    if packet:status=packet;last_status=now
    if now-previous<.0639:continue
    previous=now;raw=cam.getImage()
    if raw is None:continue
    start=time.perf_counter();bgr=np.frombuffer(raw,np.uint8).reshape(C['height'],C['width'],4)[:,:,:3].copy();detections=detect_all(bgr)
    # 只有手臂位於 home 且處於偵測狀態才允許選取，避免遮擋時使用不可靠輪廓。
    usable=status.get('state')=='DETECT' and now-last_status<.6
    send(out,now,seq=seq,width=C['width'],height=C['height'],usable=usable,detections=detections)
    ms=(time.perf_counter()-start)*1000
    if seq%8==0:log.write(json.dumps(dict(time=now,seq=seq,usable=usable,detections=detections,processing_ms=ms))+'\n');log.flush()
    if seq==24:cv2.imwrite(str(RUN/'camera_initial.png'),bgr)
    seq+=1
    if show:
        for d in detections:
            x,y,w,h=d['bbox'];color={'RED':(0,0,255),'GREEN':(0,255,0),'BLUE':(255,80,0)}[d['color']]
            selected=status.get('target',{}) or {}
            if selected and np.hypot(d['cx']-selected.get('cx',-1000),d['cy']-selected.get('cy',-1000))<12:color=(0,255,255)
            cv2.rectangle(bgr,(x,y),(x+w,y+h),color,2);cv2.circle(bgr,(round(d['cx']),round(d['cy'])),3,(255,255,255),-1)
            cv2.putText(bgr,f"{d['color']} ({d['cx']:.0f},{d['cy']:.0f})",(x,max(14,y-5)),cv2.FONT_HERSHEY_SIMPLEX,.43,color,1)
        a=world_to_pixel(C['initial_bounds'][0],C['initial_bounds'][3]);b=world_to_pixel(C['initial_bounds'][1],C['initial_bounds'][2]);cv2.rectangle(bgr,tuple(map(round,a)),tuple(map(round,b)),(200,200,200),1)
        text=f"{status.get('state','WAIT')} | Sorted {status.get('sorted',0)}/{status.get('total',0)} | Fail {status.get('failed',0)}"
        cv2.putText(bgr,text,(8,23),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
        target=status.get('target') or {}
        if target:
            cv2.putText(bgr,f"Target {target['color']} XYZ: {target['xyz'][0]:.3f}, {target['xyz'][1]:.3f}, {target['xyz'][2]:.3f} m",(8,69),cv2.FONT_HERSHEY_SIMPLEX,.43,(0,255,255),1)
        cv2.putText(bgr,f'ROI initial area | {ms:.1f} ms',(8,46),cv2.FONT_HERSHEY_SIMPLEX,.45,(255,255,255),1)
        try:
            cv2.imshow('Vision Robot - Color Sorting',bgr)
            if cv2.waitKey(1)&255==27:show=False;cv2.destroyAllWindows()
        except cv2.error as exc:print('Display disabled:',exc,flush=True);show=False
cv2.destroyAllWindows()
