"""Mochi(오리지널 캐릭터)의 상태별 도트 프레임을 그려 frames/ 와 config.json 을 만듭니다."""
import math, os, json
from PIL import Image, ImageDraw
import sys
HERE=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(HERE,"frames")
BODY=(255,214,170,255); OUTL=(70,45,40,255); CHEEK=(255,150,150,255); EYE=(40,30,30,255); LEAF=(110,190,110,255)
def base(dy=0, sx=0, sy=0, eyes=(0,0), mood="norm", arm=None, legs=0, extra=None):
    im=Image.new("RGBA",(40,40),(0,0,0,0)); d=ImageDraw.Draw(im)
    cx=20; bot=36+dy
    w=13+sx; h=11+sy
    # legs
    lo=[(-5,0),(5,0)] if legs==0 else ([(-6,-1),(4,1)] if legs>0 else [(-4,1),(6,-1)])
    for lx,ly in lo:
        d.rectangle([cx+lx-2,bot-2+ly,cx+lx+1,bot+ly],fill=OUTL)
    d.ellipse([cx-w,bot-2*h-2,cx+w,bot-1],fill=BODY,outline=OUTL)
    top=bot-2*h-2
    # leaf
    d.polygon([(cx,top+1),(cx+5,top-5),(cx+7,top-1)],fill=LEAF,outline=OUTL)
    ey=bot-h-3; ex,eyy=eyes
    if mood=="x":
        for x0 in (cx-6,cx+4):
            d.line([x0+ex,ey-1,x0+2+ex,ey+1],fill=EYE); d.line([x0+ex,ey+1,x0+2+ex,ey-1],fill=EYE)
    elif mood=="closed":
        for x0 in (cx-6,cx+4): d.line([x0,ey,x0+2,ey],fill=EYE)
    elif mood=="happy":
        for x0 in (cx-6,cx+4): d.line([x0,ey+1,x0+1,ey-1],fill=EYE); d.line([x0+1,ey-1,x0+2,ey+1],fill=EYE)
    else:
        for x0 in (cx-6,cx+4): d.rectangle([x0+ex,ey-1+eyy,x0+1+ex,ey+1+eyy],fill=EYE)
    d.rectangle([cx-10,ey+3,cx-8,ey+4],fill=CHEEK); d.rectangle([cx+8,ey+3,cx+10,ey+4],fill=CHEEK)
    if mood=="sad": d.arc([cx-2,ey+3,cx+2,ey+7],200,340,fill=EYE)
    else: d.line([cx-1+ex//2,ey+4,cx+1+ex//2,ey+4],fill=EYE)
    if arm is not None:
        ax,ay=cx+w-1,bot-h; tx=ax+int(5*math.cos(arm)); ty=ay-int(7*math.sin(arm))
        d.line([ax,ay,tx,ty],fill=OUTL,width=2); d.ellipse([tx-2,ty-2,tx+2,ty+2],fill=BODY,outline=OUTL)
    if extra: extra(d,cx,top,bot)
    return im
def save(name,frames):
    os.makedirs(f"{OUT}/{name}",exist_ok=True)
    for i,f in enumerate(frames): f.save(f"{OUT}/{name}/{i:02d}.png")
S={}
S["idle"]=[base(dy=-(i in(2,3)), sy=(1 if i in(2,3) else 0), mood="closed" if i==4 else "norm") for i in range(6)]
S["running-right"]=[base(dy=-[0,2,3,2,0,2,3,2][i], legs=1 if i<4 else -1, eyes=(2,0), sx=[1,0,-1,0,1,0,-1,0][i]) for i in range(8)]
S["waving"]=[base(arm=a, mood="happy") for a in (0.6,1.3,0.6,1.3)]
S["jumping"]=[base(dy=0,sy=-2,sx=2),base(dy=-5,sy=1),base(dy=-9,sy=1,mood="happy"),base(dy=-5),base(dy=0,sy=-2,sx=2)]
def tear(d,cx,t,b): d.rectangle([cx-7,b-9,cx-7,b-7],fill=(110,170,255,255))
S["failed"]=[base(mood="x" if i%2 else "sad", sy=-1, extra=tear if i>3 else None, eyes=((i%2)*1-0,0)) for i in range(8)]
def zz(i):
    def f(d,cx,t,b):
        z=8+i; d.line([cx+10,t-2-i,cx+13,t-2-i],fill=OUTL); d.line([cx+13,t-2-i,cx+10,t+1-i],fill=OUTL); d.line([cx+10,t+1-i,cx+13,t+1-i],fill=OUTL)
    return f
S["waiting"]=[base(mood="closed", sy=(i%2), extra=zz(i%3)) for i in range(6)]
def sweat(d,cx,t,b): d.rectangle([cx+11,t+3,cx+12,t+5],fill=(110,170,255,255))
S["running"]=[base(dy=-(i%2), eyes=((i%3)-1,1), extra=sweat if i%2 else None, arm=0.2+0.4*(i%2)) for i in range(6)]
def glasses(d,cx,t,b):
    ey=b-14; d.rectangle([cx-8,ey-3,cx-2,ey+2],outline=OUTL); d.rectangle([cx+2,ey-3,cx+8,ey+2],outline=OUTL); d.line([cx-2,ey-1,cx+2,ey-1],fill=OUTL)
S["review"]=[base(extra=glasses, eyes=([-1,0,1,1,0,-1][i],0)) for i in range(6)]
# look: 12시부터 시계방향 16방향
look=[]
for k in range(16):
    a=k/16*2*math.pi; look.append(base(eyes=(round(2*math.sin(a)), -round(2*math.cos(a)))))
S["look"]=look
for k,v in S.items(): save(k,v)
cfg={"id":"mochi","displayName":"Mochi","description":"Mochi, an original dot character, as a Codex desktop pet.","background":"none","states":{}}
for k,v in S.items(): cfg["states"][k]={"files":[f"frames/{k}/{i:02d}.png" for i in range(len(v))]}
cfg["states"]["running-left"]={"mirror":"running-right"}
json.dump(cfg,open(os.path.join(HERE,"config.json"),"w"),indent=2,ensure_ascii=False)
