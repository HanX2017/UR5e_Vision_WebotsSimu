"""純影像辨識、封包驗證與平滑控制；不存取場景座標。"""
import json
import math
from pathlib import Path
import cv2
import numpy as np
ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / 'config/settings.json').read_text(encoding='utf-8'))
JOINTS = ['shoulder_pan_joint','shoulder_lift_joint','elbow_joint','wrist_1_joint','wrist_2_joint','wrist_3_joint']

def detect(bgr, config=CONFIG):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    # 紅色同時跨越 H=0 與 H=179。
    mask = cv2.inRange(hsv, (0,110,65), (10,255,255)) | cv2.inRange(hsv, (170,110,65), (179,255,255))
    kernel = np.ones((3,3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    height, width = bgr.shape[:2]
    valid = [c for c in contours if config['min_area'] <= cv2.contourArea(c) <= width*height*config['max_area_fraction']]
    result = dict(status='NO TARGET', color=None, width=width, height=height, cx=None, cy=None)
    if valid:
        c = max(valid, key=cv2.contourArea)
        moments = cv2.moments(c)
        if moments['m00'] > 0:
            result.update(status='DETECTED',color='RED',cx=moments['m10']/moments['m00'],cy=moments['m01']/moments['m00'],bbox=list(cv2.boundingRect(c)))
    return result

def decode_packet(raw, now, last_seq=-1, config=CONFIG):
    try:
        if len(raw) > 2048:
            return None
        d = json.loads(raw)
        if not isinstance(d,dict) or d.get('version') != 1:
            return None
        if type(d.get('seq')) is not int or d['seq'] <= last_seq:
            return None
        t = d.get('time')
        if type(t) not in (int,float) or not math.isfinite(t) or not 0 <= now-t <= config['timeout']:
            return None
        if d.get('status') == 'NO TARGET':
            return d
        if d.get('status') != 'DETECTED' or d.get('color') != 'RED':
            return None
        for key in ('width','height','cx','cy'):
            if type(d.get(key)) not in (int,float) or not math.isfinite(d[key]):
                return None
        if not (d['width'] > 0 and d['height'] > 0 and 0 <= d['cx'] < d['width'] and 0 <= d['cy'] < d['height']):
            return None
        return d
    except (ValueError,TypeError,UnicodeError):
        return None

class BaseControl:
    def __init__(self, config=CONFIG):
        self.c=config
        self.angle=config['base_center']
    def update(self, detection, dt):
        c=self.c
        target=c['base_center']
        if detection and detection['status']=='DETECTED':
            error=(detection['cx']-detection['width']/2)/(detection['width']/2)
            if abs(error)<c['deadband']:
                error=0
            target+=c['base_gain']*error
        target=max(c['base_min'],min(c['base_max'],target))
        delta=(target-self.angle)*(1-math.exp(-dt/c['filter_tau']))
        limit=c['max_speed']*dt
        self.angle+=max(-limit,min(limit,delta))
        return self.angle
