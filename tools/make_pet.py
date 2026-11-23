#!/usr/bin/env python3
"""
make_pet.py — 원하는 캐릭터 프레임을 Codex pet v2 형식으로 묶어주는 도구

Codex pet v2 형식
  - spritesheet.png : 1536 x 2288 투명 PNG, 8열 x 11행, 칸 하나 192 x 208
  - pet.json        : id / displayName / description / spriteVersionNumber=2 / spritesheetPath
  - 행 배치 (프레임은 왼쪽부터 채우고 남는 칸은 투명)
      0 idle(6)  1 running-right(8)  2 running-left(8)  3 waving(4)
      4 jumping(5)  5 failed(8)  6 waiting(6)  7 running(=작업중, 6)
      8 review(6)  9~10 look(16방향, 12시부터 시계방향, 8+8)

사용법
  python3 make_pet.py config.json  [-o 출력폴더]

config.json 예시
{
  "id": "mypet",
  "displayName": "My Pet",
  "description": "My character as a Codex desktop pet.",
  "source": "sheet.png",                 # 프레임을 잘라올 원본 시트 (선택)
  "background": "auto",                  # "auto"(모서리색 제거) | "none" | "#ffffff"
  "grid": {"cols": 8, "rows": 9},        # 원본이 균등 격자일 때 칸 번호로 지정 가능
  "states": {
    "idle":          {"cells": [0,1,2,3,4,5]},        # 격자 칸 번호
    "running-right": {"cells": [24,25,26,27,28,29,30,31]},
    "running-left":  {"mirror": "running-right"},     # 좌우반전으로 생성
    "waving":        {"files": ["wave1.png","wave2.png"]},   # 개별 PNG도 가능
    "jumping":       {"boxes": [[10,10,50,60], ...]}  # 원본에서 x,y,w,h로 자르기
  }
}
빠진 상태는 자동으로 채움: running-left←running-right 반전, 나머지←idle,
look 16방향이 없으면 idle 첫 프레임(오른쪽 방향은 반전)으로 채움.
"""
import json, sys, os, argparse
from PIL import Image, ImageOps

CELL_W, CELL_H, COLS, ROWS = 192, 208, 8, 11
ROW_SPEC = [("idle", 6), ("running-right", 8), ("running-left", 8), ("waving", 4),
            ("jumping", 5), ("failed", 8), ("waiting", 6), ("running", 6), ("review", 6)]
LOOK_FRAMES = 16
FOOT_Y = 200          # 발 기준선 (원본 레포 시트들과 동일하게 약 200px)
MAX_W, MAX_H = 170, 175


def remove_bg(img, mode):
    img = img.convert("RGBA")
    if mode == "none":
        return img
    px = img.load()
    w, h = img.size
    if mode == "auto":
        key = px[0, 0]
        if key[3] == 0:
            return img
    else:
        c = mode.lstrip("#")
        key = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if sum(abs(p[i] - key[i]) for i in range(3)) < 40:
                px[x, y] = (0, 0, 0, 0)
    return img


def load_frames(spec, src, cfg, base):
    if "files" in spec:
        return [remove_bg(Image.open(os.path.join(base, f)), cfg.get("background", "auto")) for f in spec["files"]]
    if src is None:
        raise SystemExit("cells/boxes 를 쓰려면 config 에 source 가 필요합니다")
    boxes = spec.get("boxes")
    if "cells" in spec:
        g = cfg["grid"]
        cw, ch = src.width / g["cols"], src.height / g["rows"]
        boxes = [[round((i % g["cols"]) * cw), round((i // g["cols"]) * ch), round(cw), round(ch)] for i in spec["cells"]]
    return [src.crop((x, y, x + w, y + h)) for x, y, w, h in boxes]


def trim(img):
    bb = img.getbbox()
    return img.crop(bb) if bb else img


def build(cfg, base, out_dir):
    src = None
    if cfg.get("source"):
        src = remove_bg(Image.open(os.path.join(base, cfg["source"])), cfg.get("background", "auto"))

    states = {}
    for name, spec in cfg.get("states", {}).items():
        if "mirror" not in spec:
            states[name] = [trim(f) for f in load_frames(spec, src, cfg, base)]
    for name, spec in cfg.get("states", {}).items():
        if "mirror" in spec:
            states[name] = [ImageOps.mirror(f) for f in states[spec["mirror"]]]

    if "idle" not in states:
        raise SystemExit("최소한 idle 상태는 있어야 합니다")
    filled = []
    if "running-left" not in states and "running-right" in states:
        states["running-left"] = [ImageOps.mirror(f) for f in states["running-right"]]; filled.append("running-left(반전)")
    if "running-right" not in states and "running-left" in states:
        states["running-right"] = [ImageOps.mirror(f) for f in states["running-left"]]; filled.append("running-right(반전)")
    for name, _ in ROW_SPEC:
        if name not in states:
            states[name] = states["idle"]; filled.append(f"{name}(idle 대체)")
    if "look" not in states:
        f0 = states["idle"][0]
        states["look"] = [ImageOps.mirror(f0) if 1 <= i <= 7 else f0 for i in range(LOOK_FRAMES)]
        filled.append("look(idle 대체)")

    # 모든 프레임에 같은 배율 적용 (캐릭터 크기가 상태마다 튀지 않게)
    every = [f for fs in states.values() for f in fs]
    scale = min(MAX_W / max(f.width for f in every), MAX_H / max(f.height for f in every))
    resample = Image.NEAREST if scale >= 1 else Image.LANCZOS  # 도트는 정수배 확대가 깔끔
    if scale >= 1:
        scale = max(1, int(scale))

    def place(sheet, frame, col, row):
        f = frame.resize((max(1, round(frame.width * scale)), max(1, round(frame.height * scale))), resample)
        x = col * CELL_W + (CELL_W - f.width) // 2
        y = row * CELL_H + FOOT_Y - f.height
        sheet.alpha_composite(f, (x, max(row * CELL_H, y)))

    sheet = Image.new("RGBA", (CELL_W * COLS, CELL_H * ROWS), (0, 0, 0, 0))
    for row, (name, n) in enumerate(ROW_SPEC):
        frames = states[name]
        for col in range(n):
            place(sheet, frames[col % len(frames)], col, row)   # 부족하면 반복
    look = states["look"]
    for i in range(LOOK_FRAMES):
        place(sheet, look[i % len(look)], i % 8, 9 + i // 8)

    os.makedirs(out_dir, exist_ok=True)
    sheet.save(os.path.join(out_dir, "spritesheet.png"))
    meta = {"id": cfg["id"], "displayName": cfg.get("displayName", cfg["id"]),
            "description": cfg.get("description", f"{cfg['id']} as a Codex desktop pet."),
            "spriteVersionNumber": 2, "spritesheetPath": "spritesheet.png"}
    with open(os.path.join(out_dir, "pet.json"), "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False, indent=2)

    # 확인용 GIF
    prev = os.path.join(out_dir, "preview"); os.makedirs(prev, exist_ok=True)
    rows = ROW_SPEC + [("look", 16)]
    for row, (name, n) in enumerate(rows):
        cells = [sheet.crop(((i % 8) * CELL_W, (row + i // 8) * CELL_H, (i % 8 + 1) * CELL_W, (row + i // 8 + 1) * CELL_H)) for i in range(n)]
        bg = [Image.alpha_composite(Image.new("RGBA", c.size, (245, 245, 240, 255)), c).convert("P") for c in cells]
        bg[0].save(os.path.join(prev, f"{name}.gif"), save_all=True, append_images=bg[1:], duration=140 if name != "look" else 120, loop=0)
    return filled


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(a.config))
    out = a.out or os.path.join(base, "pets", cfg["id"])
    filled = build(cfg, base, out)
    print(f"완료 → {out}")
    if filled:
        print("자동으로 채운 상태:", ", ".join(filled))
    print(f"설치: 폴더를 ~/.codex/pets/{cfg['id']}/ 로 복사한 뒤 Codex 재시작")
