import unittest,sys,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,numpy as np
from common import detect,decode_packet,BaseControl,CONFIG
class VisionTests(unittest.TestCase):
 def test_positions_and_hue_edges(self):
  for x in (80,320,560):
   for hue in (0,179):
    hsv=np.zeros((480,640,3),np.uint8);hsv[210:270,x-30:x+30]=(hue,240,240)
    d=detect(cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR));self.assertEqual(d['status'],'DETECTED');self.assertAlmostEqual(d['cx'],x-.5,delta=1)
 def test_absence_background_noise(self):
  for bgr in ((60,60,60),(255,0,0),(0,255,0),(0,0,255)):
   self.assertEqual(detect(np.full((480,640,3),bgr,np.uint8))['status'],'NO TARGET')
  image=np.zeros((480,640,3),np.uint8);image[10:12,10:12]=(0,0,255);self.assertEqual(detect(image)['status'],'NO TARGET')
 def test_largest_contour(self):
  image=np.zeros((480,640,3),np.uint8);image[10:30,10:30]=(0,0,255);image[200:260,300:360]=(0,0,255)
  self.assertAlmostEqual(detect(image)['cx'],329.5,delta=1)
class ControlTests(unittest.TestCase):
 def packet(self,**kw):
  d=dict(version=1,seq=1,time=1,status='DETECTED',color='RED',width=640,height=480,cx=100,cy=200);d.update(kw);return json.dumps(d).encode()
 def test_packet_validation(self):
  self.assertIsNotNone(decode_packet(self.packet(),1.1))
  for raw in (b'bad',b'[]',self.packet(cx=float('nan')),self.packet(width=0),self.packet(cx=640),self.packet(time=0),self.packet(time=2),self.packet(seq=True),self.packet(version=4)):
   self.assertIsNone(decode_packet(raw,1.1))
  self.assertIsNone(decode_packet(self.packet(),1.1,last_seq=1))
 def test_slew_limits_and_recenter(self):
  c=BaseControl();last=c.angle
  for i in range(200):
   a=c.update(dict(status='DETECTED',cx=0,width=640),.032);self.assertLessEqual(abs(a-last),CONFIG['max_speed']*.032+1e-10);self.assertTrue(CONFIG['base_min']<=a<=CONFIG['base_max']);last=a
  self.assertGreater(c.angle,CONFIG['base_center'])
  for i in range(200):c.update(None,.032)
  self.assertAlmostEqual(c.angle,CONFIG['base_center'],places=5)
 def test_deadband(self):
  c=BaseControl();self.assertEqual(c.update(dict(status='DETECTED',cx=321,width=640),.032),CONFIG['base_center'])
if __name__=='__main__':unittest.main(verbosity=2)
