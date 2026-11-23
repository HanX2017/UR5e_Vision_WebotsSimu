import unittest,sys,os,re,tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import portable_launcher as launcher
class PortableTests(unittest.TestCase):
 def fake_webots(self,root,version='R2023b'):
    for folder in ('msys64/mingw64/bin','resources','lib/controller/python/controller'):(root/folder).mkdir(parents=True,exist_ok=True)
    (root/'msys64/mingw64/bin/webots.exe').write_bytes(b'fake for path validation')
    (root/'resources/version.txt').write_text(version)
 def test_folder_and_executable_selection(self):
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)/'安裝 路徑';self.fake_webots(root)
        self.assertEqual(launcher.validate_webots(root),root.resolve())
        self.assertEqual(launcher.validate_webots(root/'msys64/mingw64/bin/webots.exe'),root.resolve())
 def test_reject_wrong_webots_version(self):
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);self.fake_webots(root,'R2025a')
        self.assertIsNone(launcher.validate_webots(root))
        with self.assertRaises(RuntimeError):launcher.find_webots(root,interactive=False)
 def test_child_environment_is_isolated(self):
    with patch.dict(os.environ,{'PYTHONHOME':'invalid-home','PYTHONPATH':'invalid-path','VIRTUAL_ENV':'invalid-venv','SORT_HEADLESS':'1'}):
        env=launcher.environment()
        for key in ('PYTHONHOME','PYTHONPATH','VIRTUAL_ENV','SORT_HEADLESS'):self.assertNotIn(key,env)
        self.assertEqual(env['PATH'].split(os.pathsep)[0],str(launcher.PYTHON.parent))
        self.assertEqual(os.environ['PYTHONHOME'],'invalid-home')
 def test_model_references_are_local_and_complete(self):
    root=launcher.ROOT
    for file in [*list((root/'worlds').glob('*.wbt')),*list((root/'models').rglob('*.proto'))]:
        text=file.read_text(encoding='utf-8')
        for name in re.findall(r'"([^"\n]+\.(?:proto|obj|png|jpg|jpeg|dae|stl))"',text):
            self.assertNotIn('://',name,str(file))
            resolved=(file.parent/name).resolve()
            self.assertTrue(resolved.is_relative_to(root),str(resolved))
            self.assertTrue(resolved.is_file(),str(resolved))
 def test_runtime_and_packages_are_inside_project_environment(self):
    import numpy,scipy,cv2
    self.assertEqual(Path(sys.executable).resolve(),launcher.PYTHON.resolve())
    for module in (numpy,scipy,cv2):self.assertTrue(Path(module.__file__).resolve().is_relative_to(launcher.ROOT/'.venv'))
if __name__=='__main__':unittest.main(verbosity=2)
