#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gif_renderer.py — 상세페이지용 GIF 3종을 Pillow로 직접 렌더합니다.
generate_detail_page.py 가 자동으로 호출합니다.

  1) gif_01_benefit.gif     860×300  산지직송·당일수확 + 숫자 카운트업
  2) gif_02_peel_juice.gif  860×600  껍질 → 과육 → 과즙 3컷 크로스페이드
  3) gif_03_check.gif       860×300  구매 전 3초 체크 + CTA 펄스
"""
from __future__ import annotations

import math
import os
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SS = 3  # 슈퍼샘플 배율

# 팔레트 (상세페이지 CSS와 동일)
ORANGE = (242, 101, 34)
ORANGE_DK = (210, 78, 11)
ORANGE_SOFT = (255, 143, 82)
AMBER = (255, 176, 58)
CREAM = (255, 249, 240)
CREAM2 = (255, 243, 226)
INK = (34, 26, 18)
BODY = (76, 66, 56)
MUTED = (139, 124, 106)
WHITE = (255, 255, 255)
GREEN = (31, 107, 74)
LINE = (241, 221, 199)

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


@lru_cache(maxsize=64)
def _font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), int(round(size * SS)))


def GMB(s): return _font("GmarketSansBold.ttf", s)
def GMM(s): return _font("GmarketSansMedium.ttf", s)
def JUA(s): return _font("Jua-Regular.ttf", s)
def HAND(s): return _font("MapoGoldenPierA.ttf", s)
def PRE(s): return _font("Pretendard-Regular.ttf", s)
def PREM(s): return _font("Pretendard-Medium.ttf", s)
def PREB(s): return _font("Pretendard-Bold.ttf", s)
def PREX(s): return _font("Pretendard-ExtraBold.ttf", s)


# ---------------------------------------------------------------- helpers
def canvas(w, h, bg=(255, 255, 255, 255)):
    return Image.new("RGBA", (w * SS, h * SS), bg)


def finish(im, w, h):
    return im.resize((w, h), Image.LANCZOS)


def text(d, xy, s, font, fill, anchor="la", tracking=0):
    x, y = xy[0] * SS, xy[1] * SS
    if tracking:
        for ch in s:
            d.text((x, y), ch, font=font, fill=fill, anchor=anchor)
            x += d.textlength(ch, font=font) + tracking * SS
        return
    d.text((x, y), s, font=font, fill=fill, anchor=anchor)


def tw(d, s, font, tracking=0):
    if not tracking:
        return d.textlength(s, font=font) / SS
    return sum(d.textlength(c, font=font) for c in s) / SS + tracking * (len(s) - 1)


def rrect(d, box, r, fill=None, outline=None, width=1):
    d.rounded_rectangle([v * SS for v in box], radius=r * SS, fill=fill,
                        outline=outline, width=max(1, int(width * SS)))


def ell(d, box, fill):
    d.ellipse([v * SS for v in box], fill=fill)


def line(d, pts, fill, width=1):
    d.line([(x * SS, y * SS) for x, y in pts], fill=fill, width=max(1, int(width * SS)))


def vgrad(w, h, stops):
    W, H = w * SS, h * SS
    im = Image.new("RGBA", (W, H))
    px = im.load()
    for y in range(H):
        t = y / max(1, H - 1)
        c = stops[-1][1]
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                k = (t - p0) / max(1e-6, p1 - p0)
                c0 = tuple(c0) + ((255,) if len(c0) == 3 else ())
                c1 = tuple(c1) + ((255,) if len(c1) == 3 else ())
                c = tuple(int(c0[j] + (c1[j] - c0[j]) * k) for j in range(4))
                break
        for x in range(W):
            px[x, y] = c
    return im


def glow(w, h, color, alpha=40):
    import numpy as np
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2.0, h / 2.0
    d2 = (xx - cx) ** 2 / cx ** 2 + (yy - cy) ** 2 / cy ** 2
    a = (np.exp(-d2 * 2.2) * alpha).astype("uint8")
    im = Image.new("RGBA", (w, h), tuple(color) + (0,))
    im.putalpha(Image.fromarray(a, "L"))
    return im


def ease_out(t):
    return 1 - (1 - max(0.0, min(1.0, t))) ** 2.4


def ease_in_out(t):
    t = max(0.0, min(1.0, t))
    return 4 * t * t * t if t < .5 else 1 - (-2 * t + 2) ** 3 / 2


def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))


def lerp(a, b, t):
    return a + (b - a) * t


def handstroke(d, x0, x1, y, prog, color, w=2.6, amp=1.8):
    n = max(2, int((x1 - x0) * 1.4))
    pts = [(lerp(x0, x1, i / n), y + math.sin(i / n * 2.4 * math.pi) * amp) for i in range(n + 1)]
    m = int(len(pts) * prog)
    for i in range(m):
        r = w * (0.72 + 0.28 * math.sin(i / max(1, m) * math.pi))
        d.ellipse([(pts[i][0] - r) * SS, (pts[i][1] - r) * SS,
                   (pts[i][0] + r) * SS, (pts[i][1] + r) * SS], fill=color)


def star(d, cx, cy, r, fill, inner=0.3, rot=0):
    pts = []
    for i in range(8):
        a = rot + i * math.pi / 4
        rr = r if i % 2 == 0 else r * inner
        pts.append(((cx + rr * math.cos(a)) * SS, (cy + rr * math.sin(a)) * SS))
    d.polygon(pts, fill=fill)


def cover(im, w, h, zoom=1.0, focus=(0.5, 0.5)):
    iw, ih = im.size
    s = max(w / iw, h / ih) * zoom
    nw, nh = int(iw * s), int(ih * s)
    im2 = im.resize((nw, nh), Image.LANCZOS)
    x = int((nw - w) * focus[0])
    y = int((nh - h) * focus[1])
    return im2.crop((x, y, x + w, y + h))


def load(path, w, h, zoom=1.0, focus=(0.5, 0.5)):
    im = Image.open(path).convert("RGB")
    return cover(im, w, h, zoom, focus)


# ---------------------------------------------------------------- GIF 1
def gif_01(out, d):
    W, H = 860, 300
    N, DUR = 54, 80
    g = d.get("gif", {}).get("benefit", {})
    headline = g.get("headline", ["산지직송", "당일수확"])
    stats = g.get("stats", [
        {"from": 46, "to": 62, "unit": "mm", "label": "로열과 지름", "range": True},
        {"from": 0, "to": 38, "unit": "개", "label": "2.5kg 기준", "range": True},
        {"from": 0, "to": 2, "unit": "일", "label": "평일 오전 출고", "range": False},
    ])
    foot = g.get("footnote", "")
    sign = d.get("meta", {}).get("brand", "")

    bg = vgrad(W, H, [(0.0, (255, 255, 255)), (0.55, (255, 252, 246)), (1.0, (255, 243, 226))])
    bg.alpha_composite(glow(int(W * SS * .9), int(H * SS * .9), AMBER, 26), (int(W * SS * .55), int(-H * SS * .35)))

    frames = []
    for i in range(N):
        t = i / N
        im = bg.copy()
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(ov)

        # eyebrow / chip
        text(dr, (46, 30), g.get("eyebrow", "11월 수확분 · 제주 노지 조생"), PREB(15),
             fill=(150, 120, 88, 255), tracking=1.4)
        chip = g.get("chip", "전 상품 무료배송")
        cw = tw(dr, chip, PREB(15)) + 32
        rrect(dr, (W - 46 - cw, 24, W - 46, 56), 16, fill=(255, 255, 255, 235), outline=(243, 214, 184, 255), width=1.4)
        text(dr, (W - 46 - cw / 2, 40), chip, PREB(15), fill=(178, 88, 20, 255), anchor="mm")

        # LIVE pill
        px, py, pw, ph = 46, 60, 104, 38
        rrect(dr, (px, py, px + pw, py + ph), 19, fill=ORANGE + (255,))
        cx, cy = px + 23, py + ph / 2
        for k in range(2):
            p = (t * 2 + k * .5) % 1.0
            rr = 6 + p * 12
            dr.ellipse([(cx - rr) * SS, (cy - rr) * SS, (cx + rr) * SS, (cy + rr) * SS],
                       outline=(255, 255, 255, int(150 * (1 - p))))
        ell(dr, (cx - 5.5, cy - 5.5, cx + 5.5, cy + 5.5), (255, 255, 255, 255))
        text(dr, (px + 40, py + ph / 2 + 1), "LIVE", JUA(19), fill=WHITE, anchor="lm")

        # headline
        hx, hy = 168, 90
        text(dr, (hx, hy), headline[0], GMB(42), fill=INK, anchor="ls")
        w1 = tw(dr, headline[0], GMB(42))
        text(dr, (hx + w1 + 26, hy), headline[1], GMB(42), fill=ORANGE, anchor="ls")
        w2 = tw(dr, headline[1], GMB(42))
        p = clamp((t - .10) / .28)
        if p > 0:
            handstroke(dr, hx + w1 + 24, hx + w1 + 26 + w2, hy + 12, ease_out(p), AMBER + (235,), 3.0, 2.2)

        # divider
        line(dr, [(46, 122), (W - 46, 122)], LINE + (255,), 2)

        # stats
        xs = [46, 316, 604]
        for idx, st in enumerate(stats):
            ap = clamp((t - .18 - idx * .05) / .12)
            if ap <= 0:
                continue
            a = int(255 * ease_out(ap))
            cp = ease_in_out(clamp((t - .18 - idx * .05) / .30))
            lift = (1 - ease_out(ap)) * 10
            x = xs[idx]
            y = 188 + lift
            if st.get("range", True):
                va = int(lerp(st.get("from", 0), st.get("to", 10), cp))
                vb = int(lerp(st.get("from2", st.get("from", 0) + 5), st.get("to2", st.get("to", 10) + 8), cp))
                sa, sb = str(va), str(vb)
                text(dr, (x, y), sa, GMB(52), fill=INK + (a,), anchor="ls")
                wa = tw(dr, sa, GMB(52))
                rrect(dr, (x + wa + 5, y - 14, x + wa + 20, y - 8), 3, fill=INK + (a,))
                text(dr, (x + wa + 26, y), sb, GMB(52), fill=INK + (a,), anchor="ls")
                wb = tw(dr, sb, GMB(52))
                text(dr, (x + wa + 26 + wb + 6, y - 4), st.get("unit", ""), GMB(26), fill=MUTED + (a,), anchor="ls")
            else:
                v = int(lerp(st.get("from", 0), st.get("to", 2), cp))
                s = f"{v}"
                text(dr, (x, y), s, GMB(52), fill=INK + (a,), anchor="ls")
                ws = tw(dr, s, GMB(52))
                text(dr, (x + ws + 4, y - 4), "-", GMB(34), fill=INK + (a,), anchor="ls")
                s2 = str(v + 1)
                text(dr, (x + ws + 24, y), s2, GMB(52), fill=INK + (a,), anchor="ls")
                w2b = tw(dr, s2, GMB(52))
                text(dr, (x + ws + 24 + w2b + 6, y - 4), st.get("unit", ""), GMB(26), fill=MUTED + (a,), anchor="ls")
            text(dr, (x, y + 34), st.get("label", ""), PREM(16), fill=(124, 109, 92, a), anchor="ls")

        for x in (292, 578):
            line(dr, [(x, 152), (x, 236)], (243, 226, 208, 255), 1.5)

        # footnote + signature
        if foot:
            text(dr, (46, 272), foot, PREM(15), fill=(160, 141, 118, 255), anchor="ls")
        if sign:
            text(dr, (W - 46, 274), sign, HAND(26), fill=(190, 140, 92, 255), anchor="rs")

        # sparkles
        for (sx, sy, ph, r) in [(250, 40, 0.0, 7), (818, 150, .35, 8), (470, 250, .2, 5)]:
            k = (math.sin((t + ph) * math.pi * 2 * 2) + 1) / 2
            if k < .18:
                continue
            star(dr, sx, sy, r * (.6 + .4 * k), AMBER + (int(200 * k),))

        im.alpha_composite(ov)
        frames.append(finish(im, W, H).convert("RGB"))

    save(frames, os.path.join(out, "gif_01_benefit.gif"), DUR)


# ---------------------------------------------------------------- GIF 2
def gif_02(out, d):
    W, H = 860, 600
    g = d.get("gif", {}).get("peel", {})
    keys = g.get("images", ["peel", "segments", "juice"])
    caps = g.get("captions", ["껍질이 얇아 두 번이면 벗겨집니다",
                              "과육 사이로 과즙이 맺힙니다",
                              "손에 남는 향이 오래 갑니다"])
    files = [os.path.join(out, "assets", d.get("images", {}).get(k, "")) for k in keys]
    files = [f for f in files if os.path.exists(f)]
    if not files:
        return
    N_PER, FADE = 10, 3
    N = len(files) * N_PER
    DUR = 110

    frames = []
    for i in range(N):
        seg = i // N_PER
        local = (i % N_PER) / N_PER
        cur = load(files[seg], W, H, zoom=1.02 + .06 * local, focus=(.5, .45))
        im = cur.convert("RGBA").resize((W * SS, H * SS), Image.LANCZOS)
        # 다음 컷으로 크로스페이드
        if i % N_PER >= N_PER - FADE and len(files) > 1:
            nxt = (seg + 1) % len(files)
            k = (i % N_PER - (N_PER - FADE) + 1) / FADE
            nxt_im = load(files[nxt], W, H, zoom=1.02, focus=(.5, .45)).convert("RGBA").resize((W * SS, H * SS), Image.LANCZOS)
            im = Image.blend(im, nxt_im, clamp(k) ** 1.4)

        ov = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
        dr = ImageDraw.Draw(ov)
        # 하단 가독용 밝은 그라데이션
        grad = vgrad(W, 180, [(0.0, (255, 255, 255, 0)), (.5, (255, 255, 255, 150)), (1.0, (255, 255, 255, 232))])
        ov.alpha_composite(grad, (0, (H - 180) * SS))

        # 캡션
        cap = caps[seg] if seg < len(caps) else ""
        idx = f"0{seg + 1}"
        cw = tw(dr, cap, GMB(30))
        px0, py0, ph = 34, 440, 76
        rrect(dr, (px0, py0, px0 + cw + 110, py0 + ph), 20, fill=(255, 253, 249, 244))
        rrect(dr, (px0 + 12, py0 + 12, px0 + 64, py0 + 64), 14, fill=ORANGE + (255,))
        text(dr, (px0 + 38, py0 + 38), idx, JUA(26), fill=WHITE, anchor="mm")
        text(dr, (px0 + 80, py0 + ph / 2 + 1), cap, GMB(30), fill=INK, anchor="lm")

        # 진행 표시
        for k in range(len(files)):
            x = 44 + k * 30
            if k == seg:
                rrect(dr, (x, 540, x + 44, 548), 4, fill=ORANGE + (255,))
            else:
                rrect(dr, (x, 540, x + 18, 548), 4, fill=(226, 208, 188, 255))

        im.alpha_composite(ov)
        frames.append(finish(im, W, H).convert("RGB"))

    save(frames, os.path.join(out, "gif_02_peel_juice.gif"), DUR)


# ---------------------------------------------------------------- GIF 3
def gif_03(out, d):
    W, H = 860, 300
    N, DUR = 40, 80
    g = d.get("gif", {}).get("check", {})
    title = g.get("title", "구매 전 3초 체크")
    items = g.get("items", ["옵션·가격 확인", "배송·보관 확인", "파손 보상 기준"])
    cta = g.get("cta", "옵션·가격 확인")
    callout = g.get("callout", "")

    bg = vgrad(W, H, [(0.0, (255, 250, 242)), (1.0, (255, 238, 218))])
    frames = []
    for i in range(N):
        t = i / N
        im = bg.copy()
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(ov)
        rrect(dr, (20, 20, W - 20, H - 20), 24, fill=(255, 255, 255, 255), outline=(245, 218, 188, 255), width=1.6)

        text(dr, (48, 46), title, GMB(38), fill=INK, anchor="la")

        for k, it in enumerate(items):
            ap = clamp((t - .10 - k * .10) / .16)
            if ap <= 0:
                continue
            a = int(255 * ease_out(ap))
            y = 140 + k * 44
            ell(dr, (50, y - 11, 72, y + 11), (255, 240, 225, a))
            if ap > .35:
                dr.line([(56 * SS, y * SS), (60.5 * SS, (y + 5) * SS), (67 * SS, (y - 5) * SS)],
                        fill=ORANGE + (255,), width=int(2.6 * SS), joint="curve")
            text(dr, (84, y), it, PREB(21), fill=(70, 58, 46, a), anchor="lm")

        # CTA 버튼 + 펄스
        bx, by, bw, bh = 540, 96, 268, 74
        pulse = (t * 1.6) % 1.0
        for k in range(3):
            pp = (pulse + k / 3) % 1.0
            grow = 6 + pp * 16
            rrect(dr, (bx - grow, by - grow, bx + bw + grow, by + bh + grow), 22 + grow,
                  outline=(242, 101, 34, int(90 * (1 - pp))), width=2)
        rrect(dr, (bx, by, bx + bw, by + bh), 20, fill=ORANGE + (255,))
        text(dr, (bx + bw / 2, by + bh / 2 - 8), cta, GMB(26), fill=WHITE, anchor="mm")
        text(dr, (bx + bw / 2, by + bh / 2 + 20), "지금 확인하기", PREM(15), fill=(255, 226, 205, 255), anchor="mm")

        # 아래로 바운스하는 화살표
        bo = math.sin(t * math.pi * 4) * 5
        dr.line([((bx + bw / 2) * SS, (by + bh + 14 + bo) * SS), ((bx + bw / 2) * SS, (by + bh + 34 + bo) * SS)],
                fill=ORANGE + (200,), width=int(2.6 * SS))
        dr.line([((bx + bw / 2 - 7) * SS, (by + bh + 26 + bo) * SS), ((bx + bw / 2) * SS, (by + bh + 35 + bo) * SS),
                 ((bx + bw / 2 + 7) * SS, (by + bh + 26 + bo) * SS)], fill=ORANGE + (200,), width=int(2.6 * SS))

        if callout:
            cwid = tw(dr, callout, JUA(18)) + 30
            rrect(dr, (bx + bw - cwid, 218, bx + bw, 252), 15, fill=(255, 243, 226, 255), outline=(246, 205, 161, 255), width=1.4)
            text(dr, (bx + bw - cwid / 2, 235), callout, JUA(18), fill=(180, 82, 14, 255), anchor="mm")

        im.alpha_composite(ov)
        frames.append(finish(im, W, H).convert("RGB"))

    save(frames, os.path.join(out, "gif_03_check.gif"), DUR)


def save(frames, path, dur):
    pal = [f.convert("P", palette=Image.ADAPTIVE, colors=150) for f in frames]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=dur, loop=0,
                optimize=True, disposal=1)
    print(f"  {os.path.basename(path)}  {os.path.getsize(path)//1024}KB  {len(frames)}f")


def poster(gif_path, idx, out_png):
    try:
        im = Image.open(gif_path)
        im.seek(idx)
        im.convert("RGB").save(out_png)
    except Exception as e:
        print("  ! poster 실패", gif_path, e)


def build_all(out, data):
    gif_01(out, data)
    gif_02(out, data)
    gif_03(out, data)
    adir = os.path.join(out, "assets")
    os.makedirs(adir, exist_ok=True)
    # PNG 렌더용 대표 정지컷
    poster(os.path.join(out, "gif_01_benefit.gif"), 47, os.path.join(adir, "poster_01.png"))
    poster(os.path.join(out, "gif_02_peel_juice.gif"), 3, os.path.join(adir, "poster_02.png"))
    poster(os.path.join(out, "gif_03_check.gif"), 30, os.path.join(adir, "poster_03.png"))
