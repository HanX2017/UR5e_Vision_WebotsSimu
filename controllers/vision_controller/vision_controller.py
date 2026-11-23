import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from portable_support import record_runtime
record_runtime(__file__)
import os, json, time
import cv2
import numpy as np
from controller import Robot
from common import CONFIG, ROOT, detect

def main():
    robot=Robot()
    step=int(robot.getBasicTimeStep())
    camera=robot.getDevice('overhead_camera')
    emitter=robot.getDevice('vision_emitter')
    camera.enable(CONFIG['camera_period_ms'])
    emitter.setChannel(CONFIG['channel'])
    show=CONFIG['show_window'] and os.getenv('VISION_HEADLESS')!='1'
    seq=0
    previous=-1
    log=(ROOT/'results/logs/vision.jsonl').open('w',encoding='utf-8')
    try:
        while robot.step(step)!=-1:
            now=robot.getTime()
            if now-previous+1e-8 < CONFIG['camera_period_ms']/1000:
                continue
            previous=now
            raw=camera.getImage()
            if raw is None:
                continue
            start=time.perf_counter()
            # Webots Camera API 提供 BGRA，去除 alpha 後即為 OpenCV BGR。
            bgr=np.frombuffer(raw,dtype=np.uint8).reshape(camera.getHeight(),camera.getWidth(),4)[:,:,:3].copy()
            if seq==15:
                cv2.imwrite(str(ROOT/'results/screenshots/camera.png'),bgr)
            d=detect(bgr)
            d.update(version=1,seq=seq,time=now)
            seq+=1
            emitter.send(json.dumps(d).encode('utf-8'))
            elapsed=(time.perf_counter()-start)*1000
            if seq%8==0:
                log.write(json.dumps(dict(d,processing_ms=elapsed))+'\n');log.flush()
            if show:
                if d['status']=='DETECTED':
                    x,y,w,h=d['bbox'];cv2.rectangle(bgr,(x,y),(x+w,y+h),(0,255,255),2)
                    cv2.circle(bgr,(round(d['cx']),round(d['cy'])),4,(255,255,255),-1)
                    text=f"RED ({d['cx']:.1f}, {d['cy']:.1f})"
                else:
                    text='NO TARGET'
                cv2.putText(bgr,text,(15,30),cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,255,255),2)
                cv2.putText(bgr,f'{elapsed:.1f} ms | Camera 15.625 Hz',(15,60),cv2.FONT_HERSHEY_SIMPLEX,0.55,(255,255,255),1)
                try:
                    cv2.imshow('Vision Robot - Webots Camera',bgr)
                    if cv2.waitKey(1)&255==27:
                        show=False;cv2.destroyAllWindows()
                except cv2.error as exc:
                    print('OpenCV display disabled:',exc,flush=True);show=False
    finally:
        log.close();cv2.destroyAllWindows()
if __name__=='__main__':
    main()
