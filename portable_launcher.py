"""GitHub 可攜入口：從專案目錄定位虛擬環境、資源與 Webots。"""
import argparse,json,os,platform,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PYTHON=ROOT/'.venv/Scripts/python.exe'
CONFIG=ROOT/'config/webots.json'

def validate_webots(value):
    if not value:return None
    path=Path(os.path.expandvars(str(value).strip().strip('"'))).expanduser()
    if path.is_file():
        if path.name.lower() not in ('webots.exe','webotsw.exe'):return None
        path=path.parent
        if path.name.lower()=='bin':path=path.parents[2]
    path=path.resolve()
    exe=path/'msys64/mingw64/bin/webots.exe'
    version=path/'resources/version.txt'
    if not exe.is_file() or not version.is_file():return None
    if not version.read_text(encoding='utf-8').strip().startswith('R2023b'):return None
    if not (path/'lib/controller/python/controller').is_dir():return None
    return path

def find_webots(explicit=None,interactive=True):
    if explicit:
        valid=validate_webots(explicit)
        if not valid:raise RuntimeError('The selected folder must contain Webots R2023b (Windows x64).')
        return valid
    candidates=[]
    if CONFIG.exists():
        try:candidates.append(json.loads(CONFIG.read_text(encoding='utf-8')).get('webots_home'))
        except (ValueError,OSError):pass
    candidates.extend([os.environ.get('WEBOTS_HOME'),ROOT.parent/'Webots',ROOT.parent.parent/'Webots'])
    for key in ('ProgramFiles','LOCALAPPDATA'):
        if os.environ.get(key):candidates.append(Path(os.environ[key])/'Webots')
    for part in os.environ.get('PATH','').split(os.pathsep):
        if part and (Path(part)/'webots.exe').is_file():candidates.append(Path(part)/'webots.exe')
    for candidate in candidates:
        valid=validate_webots(candidate)
        if valid:return valid
    if not interactive:raise RuntimeError('Webots R2023b was not found. Run Configure_Webots.cmd or use --webots PATH.')
    print('Webots R2023b was not found. Paste its installation folder or webots.exe path.')
    while True:
        value=input('Webots path (Enter to cancel): ').strip()
        if not value:raise RuntimeError('Webots configuration cancelled.')
        valid=validate_webots(value)
        if valid:
            CONFIG.write_text(json.dumps({'webots_home':str(valid)},indent=2),encoding='utf-8')
            return valid
        print('Not a valid Webots R2023b installation. Please try again.')

def environment(home=None):
    env=os.environ.copy()
    # 清除會污染子程序的 Python／測試環境變數。
    for name in ('PYTHONHOME','PYTHONPATH','VIRTUAL_ENV','SORT_HEADLESS','SORT_AUTO_QUIT','SORT_SEED','SORT_COUNT','VISION_HEADLESS','VISION_SOAK','VISION_TEST_GUI'):
        env.pop(name,None)
    for key,name in [('TEMP','Temp'),('TMP','Temp'),('PIP_CACHE_DIR','Cache/pip'),('LOCALAPPDATA','Cache/LocalAppData'),('APPDATA','Cache/AppData'),('XDG_CACHE_HOME','Cache'),('XDG_CONFIG_HOME','config'),('HOME','Cache/home')]:
        path=ROOT/name;path.mkdir(parents=True,exist_ok=True);env[key]=str(path)
    env['PATH']=str(PYTHON.parent)+os.pathsep+env.get('PATH','')
    env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONIOENCODING']='utf-8';env['PORTABLE_PROJECT_ROOT']=str(ROOT)
    if home is not None:env['WEBOTS_HOME']=str(home)
    return env

def prepare_controllers():
    for file in (ROOT/'controllers').glob('*/*.py'):
        # 每次啟動重新產生實際解壓路徑，可覆寫 Webots 的全域 Python 偏好。
        (file.parent/'runtime.ini').write_text('[python]\nCOMMAND = '+PYTHON.as_posix()+'\nOPTIONS = -B\n',encoding='utf-8')

def main():
    p=argparse.ArgumentParser(description='Vision Robot Windows portable launcher')
    p.add_argument('--webots');p.add_argument('--configure',action='store_true');p.add_argument('--diagnose',action='store_true')
    p.add_argument('--unit-tests',action='store_true');p.add_argument('--stage1',action='store_true');p.add_argument('--test',action='store_true')
    p.add_argument('--headless',action='store_true');p.add_argument('--seed',type=int);p.add_argument('--count',type=int,choices=range(3,7))
    p.add_argument('--run',default='demo');p.add_argument('--vision-loss-test',action='store_true');p.add_argument('--no-prompt',action='store_true')
    a=p.parse_args()
    if Path(sys.executable).resolve()!=PYTHON.resolve():raise RuntimeError('Run Setup_Portable.cmd first, then use the supplied .cmd files.')
    if platform.machine().lower() not in ('amd64','x86_64'):raise RuntimeError('Windows x64 is required.')
    if a.unit_tests:
        return subprocess.call([str(PYTHON),'-B','-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],cwd=ROOT,env=environment())
    if a.diagnose:
        import cv2,numpy,scipy
        result={'python':sys.executable,'prefix':sys.prefix,'isolated':bool(sys.flags.isolated),'numpy':numpy.__version__,'opencv':cv2.__version__,'scipy':scipy.__version__,'project':str(ROOT),'package_paths':[numpy.__file__,cv2.__file__,scipy.__file__]}
        for file in result['package_paths']:
            if not Path(file).resolve().is_relative_to(ROOT/'.venv'):raise RuntimeError('A package was imported from outside the project virtual environment.')
        output=ROOT/'results/portable_diagnostics.json';output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2));return 0
    home=find_webots(a.webots,not a.no_prompt)
    if a.configure:
        if not a.webots:
            print('Current Webots:',home)
            value=input('New Webots folder (Enter to keep current): ').strip()
            if value:home=find_webots(value)
        CONFIG.write_text(json.dumps({'webots_home':str(home)},indent=2),encoding='utf-8');print('Saved:',home);return 0
    run=Path(a.run)
    if run.is_absolute() or len(run.parts)!=1 or a.run in ('.','..'):raise ValueError('--run must be one folder name.')
    env=environment(home);prepare_controllers()
    if a.stage1:
        world=ROOT/'worlds'/('integration_test.wbt' if a.test else 'vision_robot.wbt')
        folder=ROOT/'results/logs'
        if a.headless:env['VISION_HEADLESS']='1'
    else:
        world=ROOT/'worlds'/('sorting_vision_loss.wbt' if a.vision_loss_test else 'sorting_robot.wbt')
        folder=ROOT/'results/sorting'/a.run;env['SORT_RUN']=a.run
        if a.seed is not None:env['SORT_SEED']=str(a.seed)
        if a.count is not None:env['SORT_COUNT']=str(a.count)
        if a.headless:env['SORT_HEADLESS']='1'
        if a.test:env['SORT_AUTO_QUIT']='1'
    for name in ('results/logs','results/screenshots','results/experiments'):(ROOT/name).mkdir(parents=True,exist_ok=True)
    folder.mkdir(parents=True,exist_ok=True)
    cmd=[str(home/'msys64/mingw64/bin/webots.exe'),'--batch','--stdout','--stderr','--mode='+('fast' if a.test else 'realtime')]
    if a.headless:cmd.append('--no-rendering')
    cmd.append(str(world))
    print('Project:',ROOT,'\nPython:',PYTHON,'\nWebots:',home,flush=True)
    with (folder/'console.txt').open('w',encoding='utf-8') as log:
        proc=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        print('Webots PID:',proc.pid,flush=True)
        return proc.wait()
if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,RuntimeError,ValueError,EOFError) as exc:
        print('ERROR:',exc,file=sys.stderr);raise SystemExit(2)
