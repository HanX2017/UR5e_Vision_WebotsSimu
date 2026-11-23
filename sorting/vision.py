"""相機 +X 光軸經固定旋轉朝 -Z；以方塊頂面高度做反投影。"""
import cv2
import numpy as np
from .settings import C

def pixel_to_world(u,v,z=None):
    z=C['table_top']+C['block_size'] if z is None else z
    focal=C['width']/(2*np.tan(C['fov']/2))
    distance=C['camera'][2]-z
    # Webots 像素中心使用 (width-1)/2；影像 v 向下，世界 y 向上。
    return [C['camera'][0]+(u-(C['width']-1)/2)*distance/focal,C['camera'][1]-(v-(C['height']-1)/2)*distance/focal,C['grasp_z']]

def world_to_pixel(x,y,z=None):
    z=C['table_top']+C['block_size'] if z is None else z
    focal=C['width']/(2*np.tan(C['fov']/2));d=C['camera'][2]-z
    return [(x-C['camera'][0])*focal/d+(C['width']-1)/2,(C['camera'][1]-y)*focal/d+(C['height']-1)/2]

def detect_all(bgr):
    hsv=cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)
    masks={'RED':cv2.inRange(hsv,(0,100,55),(10,255,255))|cv2.inRange(hsv,(170,100,55),(179,255,255)), 'GREEN':cv2.inRange(hsv,(35,85,45),(85,255,255)), 'BLUE':cv2.inRange(hsv,(95,90,45),(135,255,255))}
    found=[]
    for color,mask in masks.items():
        mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
        contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area=cv2.contourArea(contour)
            if not 180<area<6000:continue
            m=cv2.moments(contour)
            if not m['m00']:continue
            u,v=m['m10']/m['m00'],m['m01']/m['m00']
            xyz=pixel_to_world(u,v);xmin,xmax,ymin,ymax=C['initial_bounds']
            if not (xmin<xyz[0]<xmax and ymin<xyz[1]<ymax):continue
            x,y,w,h=cv2.boundingRect(contour)
            if not .65<w/h<1.5:continue
            found.append(dict(color=color,cx=u,cy=v,area=area,bbox=[x,y,w,h],xyz=xyz))
    return sorted(found,key=lambda d:(d['xyz'][0]**2+d['xyz'][1]**2,d['color']))
