"""確保 Webots 控制器使用本專案的虛擬環境與套件。"""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def record_runtime(script):
    original_hook=sys.excepthook
    def report_error(kind,error,tb):
        import traceback
        folder=ROOT/'results/controller_errors';folder.mkdir(parents=True,exist_ok=True)
        (folder/(Path(script).stem+'.txt')).write_text(''.join(traceback.format_exception(kind,error,tb)),encoding='utf-8')
        original_hook(kind,error,tb)
    sys.excepthook=report_error
    executable=Path(sys.executable).resolve()
    if executable!=(ROOT/'.venv/Scripts/python.exe').resolve():
        raise RuntimeError('Please run Setup_Portable.cmd, then start with Start_Sorting.cmd.')
    import numpy,cv2,scipy
    paths=[numpy.__file__,cv2.__file__,scipy.__file__]
    if not all(Path(p).resolve().is_relative_to(ROOT/'.venv') for p in paths):raise RuntimeError('Dependency outside the project virtual environment detected.')
    folder=ROOT/'results/runtime_audit';folder.mkdir(parents=True,exist_ok=True)
    (folder/(Path(script).stem+'.json')).write_text(json.dumps(dict(executable=str(executable),prefix=sys.prefix,isolated=bool(sys.flags.isolated),script=str(script),packages=paths),indent=2),encoding='utf-8')
