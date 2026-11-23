import json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'config/sorting.json').read_text(encoding='utf-8'))
if 'SORT_SEED' in os.environ:C['seed']=int(os.environ['SORT_SEED']);C['mode']='fixed'
if 'SORT_COUNT' in os.environ:C['object_count']=int(os.environ['SORT_COUNT'])
RUN=ROOT/'results/sorting'/os.getenv('SORT_RUN','demo')
RUN.mkdir(parents=True,exist_ok=True)
JOINTS=['shoulder_pan_joint','shoulder_lift_joint','elbow_joint','wrist_1_joint','wrist_2_joint','wrist_3_joint']
