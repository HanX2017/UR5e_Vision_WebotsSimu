import unittest,sys,json,math,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2,numpy as np
from sorting.vision import pixel_to_world,world_to_pixel,detect_all
from sorting.kinematics import solve,fk,DOWN,LIMITS
from sorting.settings import C,ROOT
class CalibrationTests(unittest.TestCase):
 def test_optical_axis_and_cardinal_directions(self):
    x,y,z=pixel_to_world(319.5,239.5)
    self.assertAlmostEqual(x,-.39);self.assertAlmostEqual(y,0);self.assertEqual(z,.735)
    self.assertGreater(pixel_to_world(400,239.5)[0],x)
    self.assertLess(pixel_to_world(319.5,300)[1],y)
 def test_height_parallax_correction(self):
    top=pixel_to_world(500,240,.76);table=pixel_to_world(500,240,.7)
    self.assertGreater(abs(table[0]-C['camera'][0]),abs(top[0]-C['camera'][0]))
 def test_three_colors_and_roi(self):
    image=np.full((480,640,3),90,np.uint8)
    specs=[('RED',-.46,-.12,(0,0,255)),('GREEN',-.30,.12,(0,255,0)),('BLUE',-.46,.12,(255,0,0))]
    for color,x,y,bgr in specs:
        u,v=map(round,world_to_pixel(x,y));cv2.rectangle(image,(u-20,v-20),(u+20,v+20),bgr,-1)
    u,v=map(round,world_to_pixel(-.08,0));cv2.rectangle(image,(u-15,v-15),(u+15,v+15),(0,0,255),-1)
    found=detect_all(image);self.assertEqual(sorted(d['color'] for d in found),['BLUE','GREEN','RED'])
    for color,x,y,bgr in specs:
        d=next(d for d in found if d['color']==color);self.assertLess(math.hypot(d['xyz'][0]-x,d['xyz'][1]-y),.0015)
 def test_red_wrap_and_absence(self):
    hsv=np.zeros((480,640,3),np.uint8);hsv[215:265,295:345]=(179,240,240)
    self.assertEqual(detect_all(cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR))[0]['color'],'RED')
    self.assertEqual(detect_all(np.zeros((480,640,3),np.uint8)),[])
class KinematicsTests(unittest.TestCase):
 def test_workspace_pose_and_orientation(self):
    q=None
    for target in ([0,-.38,1.08],[-.48,-.17,.735],[-.30,.17,.735],[.318,-.302,.755],[.522,.042,.755],[.402,.302,.755]):
        q=solve(target,q);p,R=fk(q)
        self.assertLess(np.linalg.norm(p-target),.0006);self.assertLess(np.linalg.norm(R-DOWN),.003)
        self.assertTrue(np.all(q>=LIMITS[:,0]) and np.all(q<=LIMITS[:,1]))
 def test_reject_unreachable_or_under_table(self):
    for point in ([3,0,1],[.3,0,.2],[float('nan'),0,1]):
        with self.assertRaises(ValueError):solve(point)
 def test_truth_isolation(self):
    for name in ('sorting_arm','sorting_vision'):
        source=(ROOT/f'controllers/{name}/{name}.py').read_text(encoding='utf-8')
        self.assertNotIn('Supervisor(',source);self.assertNotIn('getFromDef',source);self.assertNotIn('spawn_truth',source)
class GenerationTests(unittest.TestCase):
 def test_reproducible_nonoverlap_and_bounds(self):
    from sorting.scene import sample_scene
    for count in range(3,7):
        for seed in range(20):
            colors,positions=sample_scene(seed,count)
            self.assertEqual((colors,positions),sample_scene(seed,count))
            self.assertTrue(set(('RED','GREEN','BLUE')).issubset(colors))
            for i,(x,y) in enumerate(positions):
                self.assertTrue(C['spawn_bounds'][0]<=x<=C['spawn_bounds'][1] and C['spawn_bounds'][2]<=y<=C['spawn_bounds'][3])
                for p in positions[:i]:self.assertGreater(math.dist((x,y),p),.105)
if __name__=='__main__':unittest.main(verbosity=2)
