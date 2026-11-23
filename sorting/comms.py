import json,math

def read_latest(receiver,now,timeout=.35):
    latest=None
    while receiver.getQueueLength():
        raw=receiver.getBytes();receiver.nextPacket()
        if len(raw)>65536:continue
        try:
            d=json.loads(raw)
            if not isinstance(d,dict) or type(d.get('time')) not in (int,float):continue
            if not math.isfinite(d['time']) or not 0<=now-d['time']<=timeout:continue
            latest=d
        except (ValueError,UnicodeError,TypeError):pass
    return latest

def send(emitter,now,**fields):
    emitter.send(json.dumps(dict(time=now,**fields),allow_nan=False).encode())
