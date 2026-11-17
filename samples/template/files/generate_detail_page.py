#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
상세페이지 자동 생성기 (v6 표준)
================================
JSON 하나 + 사진 폴더 하나로 스마트스토어 상세페이지를 통째로 찍어냅니다.

    python3 generate_detail_page.py --data product.example.json --out ./out/제주감귤

만들어지는 것
  · 상세페이지_<버전>_상단.png / _중단.png / _하단.png   (1720px, 2배 해상도)
  · 상세페이지_<버전>_전체.png                           (확인용)
  · 860/…_상단_860.png …                                 (스마트스토어 업로드용 860px)
  · 상세페이지_<버전>_<상품>.html                        (GIF가 실제로 움직이는 원본)
  · gif_01_benefit.gif / gif_02_peel_juice.gif / gif_03_check.gif
  · <버전>_제작노트.md

설계 원칙(2026 상세페이지 상위 판매자 공식 리서치 반영)
  · 860px 모바일 기준. 본문 24px 이상, 제목 52~58px, 숫자 56~84px
  · 첫 화면 3요소: 대표 실사컷 + 한 줄 약속 + 가격·무료배송
  · 구매 전 5가지 의심(뭔데/품질/얼마나/배송/교환)을 순서대로 해소
  · 숫자·배송·보관은 글 대신 인포그래픽(SVG)으로
  · 사진 70 : 글 30, 신뢰 요소 3곳 이상, CTA 2회 이상
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
import time
from html import escape

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")

# ----------------------------------------------------------------------------
# 0. 팔레트 / 폰트
# ----------------------------------------------------------------------------
C = {
    "ink": "#221A12",
    "body": "#4C4238",
    "muted": "#8B7C6A",
    "orange": "#F26522",
    "orange_dk": "#D24E0B",
    "orange_soft": "#FF8F52",
    "amber": "#FFB03A",
    "cream": "#FFF9F0",
    "cream2": "#FFF3E2",
    "white": "#FFFFFF",
    "green": "#1F6B4A",
    "line": "#F1DDC7",
}

FONT_FILES = [
    ("GmarketSansBold.ttf", "GMB", 700),
    ("GmarketSansMedium.ttf", "GMM", 500),
    ("Jua-Regular.ttf", "JUA", 400),
    ("MapoGoldenPierA.ttf", "HAND", 400),
    ("Pretendard-Regular.ttf", "PRE", 400),
    ("Pretendard-Medium.ttf", "PRE", 500),
    ("Pretendard-SemiBold.ttf", "PRE", 600),
    ("Pretendard-Bold.ttf", "PRE", 700),
    ("Pretendard-ExtraBold.ttf", "PRE", 800),
]

# ----------------------------------------------------------------------------
# 1. 아이콘 (인라인 SVG — 이미지 파일 의존 없이 선명)
# ----------------------------------------------------------------------------
ICON_PATHS = {
    "truck": '<path d="M2 6.5h11.5v9.5H2z"/><path d="M13.5 9.5h3.6l3 3.2v3.3h-6.6z"/><circle cx="6.2" cy="18" r="1.7"/><circle cx="16.6" cy="18" r="1.7"/>',
    "box": '<path d="M3 8l9-4 9 4-9 4-9-4z"/><path d="M3 8v8l9 4 9-4V8"/><path d="M12 12v8"/>',
    "clock": '<circle cx="12" cy="12" r="8.6"/><path d="M12 7.2v5.1l3.4 2"/>',
    "shield": '<path d="M12 3l7.5 2.8v5.7c0 4.7-3.2 7.8-7.5 8.7-4.3-.9-7.5-4-7.5-8.7V5.8L12 3z"/><path d="M9 12.2l2.1 2.1 4.2-4.3"/>',
    "leaf": '<path d="M20 4c-8 0-13.6 3.7-13.6 9.5 0 2.2.8 4 2 5.3C11 14 15 10.6 20 9"/><path d="M4 20c1-3 3-5.6 6-7.4"/>',
    "sugar": '<circle cx="12" cy="12" r="8.4"/><path d="M8.4 9.2l3.6 2.1 3.6-2.1M12 11.3v5.2M8.4 14.8l3.6-2.1 3.6 2.1"/>',
    "ruler": '<path d="M3.6 14.4L14.4 3.6l6 6L9.6 20.4z"/><path d="M7.2 10.8l1.8 1.8M10.2 7.8l1.8 1.8M13.2 4.8l1.8 1.8"/>',
    "weight": '<path d="M5 8h14l1.5 12H3.5z"/><circle cx="12" cy="5.6" r="2.4"/>',
    "calendar": '<rect x="3.4" y="5" width="17.2" height="15.4" rx="2"/><path d="M3.4 9.8h17.2M8.2 3v4M15.8 3v4"/>',
    "peel": '<path d="M12 3.2c4.2 0 7.4 3 7.4 6.8 0 2.7-2 5.6-5.4 8.6L12 20.4l-2-1.8C6.6 15.6 4.6 12.7 4.6 10 4.6 6.2 7.8 3.2 12 3.2z"/><path d="M12 3.2c-1.4 3.4-1.4 8.6 0 17.2"/>',
    "aroma": '<path d="M8 20c-1.4-2-1.4-3.6 0-5.6s1.4-3.4 0-5.2"/><path d="M12 20c-1.4-2-1.4-3.6 0-5.6s1.4-3.4 0-5.2"/><path d="M16 20c-1.4-2-1.4-3.6 0-5.6s1.4-3.4 0-5.2"/>',
    "cold": '<rect x="6.2" y="3.2" width="11.6" height="17.6" rx="2.4"/><path d="M10 7h4M10 11h4"/><path d="M12 14.4v3.2"/>',
    "sun": '<circle cx="12" cy="12" r="4.2"/><path d="M12 2.6v2.6M12 18.8v2.6M2.6 12h2.6M18.8 12h2.6M5.4 5.4l1.9 1.9M16.7 16.7l1.9 1.9M18.6 5.4l-1.9 1.9M7.3 16.7l-1.9 1.9"/>',
    "newspaper": '<rect x="3.6" y="5" width="16.8" height="14" rx="1.6"/><path d="M6.8 9h5.4M6.8 12.4h5.4M6.8 15.8h3.4M15 9h2.2M15 12.4h2.2M15 15.8h2.2"/>',
    "check": '<path d="M4.6 12.4l4.6 4.6L19.4 6.8"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "arrow_down": '<path d="M12 4v14M6.4 12.6L12 18.4l5.6-5.8"/>',
    "thermo": '<path d="M12 3.4a2.6 2.6 0 0 1 2.6 2.6v7.2a4.6 4.6 0 1 1-5.2 0V6A2.6 2.6 0 0 1 12 3.4z"/><path d="M12 9v6.2"/>',
    "hand": '<path d="M9 11V5.4a1.6 1.6 0 1 1 3.2 0V10M12.2 9.6V4.6a1.6 1.6 0 1 1 3.2 0V11M15.4 10.6V7a1.6 1.6 0 1 1 3.2 0v7.4c0 4-2.6 6.6-6.4 6.6-2.6 0-4.3-1.2-5.6-3.2l-3-4.6a1.6 1.6 0 0 1 2.6-1.8L9 13.2"/>',
    "droplet": '<path d="M12 3.4c3.2 3.8 5.6 6.6 5.6 9.6a5.6 5.6 0 1 1-11.2 0c0-3 2.4-5.8 5.6-9.6z"/>',
    "star": '<path d="M12 3.6l2.6 5.4 5.9.8-4.3 4.1 1.1 5.9-5.3-2.9-5.3 2.9 1.1-5.9L3.5 9.8l5.9-.8z"/>',
    "pin": '<path d="M12 21s6.6-6 6.6-11A6.6 6.6 0 0 0 5.4 10c0 5 6.6 11 6.6 11z"/><circle cx="12" cy="10" r="2.4"/>',
    "gift": '<rect x="3.4" y="9" width="17.2" height="11.4" rx="1.6"/><path d="M3.4 13.4h17.2M12 9v11.4"/><path d="M12 9c-1-3-3-4.4-4.6-3.6C6 6 7.2 8 12 9zM12 9c1-3 3-4.4 4.6-3.6C18 6 16.8 8 12 9z"/>',
    "info": '<circle cx="12" cy="12" r="8.6"/><path d="M12 11v5.6M12 8.2v.2"/>',
}

def icon(name: str, size: int = 24, color: str = "currentColor", sw: float = 1.9, cls: str = "") -> str:
    p = ICON_PATHS.get(name, ICON_PATHS["check"])
    return (
        f'<svg class="ic {cls}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{p}</svg>'
    )


def emoji(code: str, size: int = 22, style: str = "") -> str:
    """Twemoji SVG (CC-BY 4.0) — assets/emoji/<code>.svg"""
    return (f'<img class="em" src="assets/emoji/{code}.svg" '
            f'style="width:{size}px;height:{size}px;{style}" alt="">')


# ----------------------------------------------------------------------------
# 2. CSS
# ----------------------------------------------------------------------------
def build_css(d) -> str:
    c = C
    return f"""
  @font-face{{font-family:'GMB';src:url('fonts/GmarketSansBold.subset.woff2');font-weight:700}}
  @font-face{{font-family:'GMM';src:url('fonts/GmarketSansMedium.subset.woff2');font-weight:500}}
  @font-face{{font-family:'JUA';src:url('fonts/Jua.subset.woff2');font-weight:400}}
  @font-face{{font-family:'HAND';src:url('fonts/MapoGoldenPier.subset.woff2');font-weight:400}}
  @font-face{{font-family:'PRE';src:url('fonts/Pretendard-Regular.subset.woff2');font-weight:400}}
  @font-face{{font-family:'PRE';src:url('fonts/Pretendard-Medium.subset.woff2');font-weight:500}}
  @font-face{{font-family:'PRE';src:url('fonts/Pretendard-SemiBold.subset.woff2');font-weight:600}}
  @font-face{{font-family:'PRE';src:url('fonts/Pretendard-Bold.subset.woff2');font-weight:700}}
  @font-face{{font-family:'PRE';src:url('fonts/Pretendard-ExtraBold.subset.woff2');font-weight:800}}

  :root{{
    --ink:{c['ink']}; --body:{c['body']}; --muted:{c['muted']};
    --orange:{c['orange']}; --orange-dk:{c['orange_dk']}; --orange-soft:{c['orange_soft']};
    --amber:{c['amber']}; --cream:{c['cream']}; --cream2:{c['cream2']};
    --green:{c['green']}; --line:{c['line']};
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  @page{{size:860px 40000px;margin:0}}
  html,body{{width:860px}}
  body{{font-family:'PRE',sans-serif;background:#fff;color:var(--ink);
    font-size:24px;line-height:1.62;font-weight:400;
    word-break:keep-all;line-break:strict;-webkit-font-smoothing:antialiased}}
  .page{{width:860px;overflow:hidden;background:#fff}}
  img{{display:block}}
  .sec{{padding-left:60px;padding-right:60px}}
  .em{{display:inline-block;vertical-align:-4px}}

  /* ---------- 공통 타입 ---------- */
  .eyebrow{{font-family:'PRE';font-size:17px;font-weight:800;letter-spacing:.24em;color:var(--orange);text-transform:uppercase}}
  .eyebrow .ln{{display:inline-block;width:26px;height:2px;background:currentColor;vertical-align:middle;margin-right:10px;opacity:.5}}
  h2{{font-family:'GMB';font-size:54px;line-height:1.2;font-weight:700;letter-spacing:-.045em}}
  h2 em{{font-style:normal;color:var(--orange)}}
  .mark{{background:linear-gradient(180deg,rgba(255,176,58,0) 56%,rgba(255,196,94,.85) 56%,rgba(255,196,94,.85) 93%,rgba(255,176,58,0) 93%);padding:0 4px}}
  .lead{{font-size:25px;line-height:1.75;color:var(--body);letter-spacing:-.012em}}
  .lead b{{color:var(--ink);font-weight:700}}
  .hn{{font-family:'HAND';letter-spacing:-.005em;line-height:1.25}}
  .jua{{font-family:'JUA'}}
  .note{{font-size:18px;line-height:1.7;color:var(--muted)}}
  .num{{font-family:'GMB';letter-spacing:-.03em;font-variant-numeric:tabular-nums}}

  /* ---------- 0. TOP STRIP ---------- */
  .tb{{height:62px;background:var(--cream2);display:flex;align-items:center;justify-content:space-between;padding:0 60px;border-bottom:1px solid #F6E2CB}}
  .tb .l{{font-size:19px;font-weight:700;color:#B4520E;letter-spacing:-.01em;white-space:nowrap}}
  .tb .r{{font-size:14px;font-weight:700;letter-spacing:.22em;color:#B7A48C}}

  /* ---------- 1. HERO ---------- */
  .hero{{background:#fff;padding-bottom:0}}
  .hero .brandrow{{display:flex;align-items:center;justify-content:space-between;padding:22px 60px 18px}}
  .hero .wordmark{{font-family:'GMB';font-size:25px;font-weight:700;letter-spacing:.13em;color:var(--ink)}}
  .hero .wordmark .em{{vertical-align:-6px;margin-right:7px}}
  .hero .since{{font-size:15px;font-weight:700;letter-spacing:.2em;color:#B9A894}}
  .hero .shot{{position:relative;width:860px;height:640px;overflow:hidden;background:#FBF1E4}}
  .hero .shot img{{width:860px;height:640px;object-fit:cover}}
  .hero .shot .stkr{{position:absolute;right:40px;top:34px;width:124px;height:124px;border-radius:50%;
    background:rgba(255,251,244,.96);border:2.5px dashed var(--orange);transform:rotate(9deg);
    text-align:center;font-family:'JUA';color:var(--orange-dk);padding-top:24px;
    box-shadow:0 10px 26px rgba(150,80,20,.16)}}
  .hero .shot .stkr b{{display:block;font-size:31px;font-weight:400;line-height:1.05}}
  .hero .shot .stkr span{{display:block;font-size:17px;line-height:1.2;margin-top:2px}}
  .hero .shot .stkr s{{display:block;font-size:10px;letter-spacing:.18em;color:#DB9A66;text-decoration:none;margin-top:5px}}
  .hero .shot .live{{position:absolute;left:34px;top:32px;display:flex;align-items:center;gap:8px;white-space:nowrap;
    background:rgba(255,255,255,.94);border-radius:100px;padding:9px 18px 9px 14px;
    font-size:17px;font-weight:800;color:#B8450B;letter-spacing:.02em}}
  .hero .shot .live i{{width:10px;height:10px;border-radius:50%;background:var(--orange);display:block;flex:none}}
  .hero .shot .cap{{position:absolute;left:30px;bottom:26px;background:rgba(255,252,246,.92);border-radius:100px;padding:8px 18px;
    font-family:'HAND';font-size:24px;color:#8A5A20;transform:rotate(-1.6deg);box-shadow:0 6px 16px rgba(120,70,20,.12)}}
  .hero .copy{{padding:44px 60px 0}}
  .hero .kick{{display:inline-block;white-space:nowrap;background:var(--cream2);color:#B8450B;border-radius:100px;
    padding:10px 20px;font-size:19px;font-weight:800;letter-spacing:-.01em}}
  .hero h1{{font-family:'GMB';font-size:84px;line-height:1.09;font-weight:700;letter-spacing:-.055em;margin:24px 0 0}}
  .hero h1 .l1{{display:block}}
  .hero h1 .l3{{display:block;margin-top:-2px}}
  .hero h1 .l2{{display:inline-block;display:inline-block;background:linear-gradient(100deg,#FF8B45,#F26522 62%,#DC520A);color:#fff;
    padding:16px 26px 12px;margin:2px 0 0 -8px;line-height:1.12;transform:rotate(-1.3deg);
    box-shadow:0 14px 30px rgba(210,80,10,.22)}}
  .hero .handline{{margin-top:14px}}
  .hero .handline svg{{display:block;margin:-6px 0 0 2px}}
  .hero .handline .t{{font-family:'HAND';font-size:40px;color:#A65A16}}
  .hero .handline svg{{margin-bottom:6px}}
  .hero .sub{{margin-top:20px;font-size:24px;line-height:1.72;color:var(--body);font-weight:500}}
  .hero .pills{{display:flex;gap:9px;margin-top:24px;flex-wrap:wrap}}
  .pill{{background:#fff;border:1.5px solid #EBD8C3;border-radius:100px;padding:10px 18px;
    font-size:19px;font-weight:700;color:#6B5C4B;white-space:nowrap}}
  .pill.on{{background:var(--orange);border-color:var(--orange);color:#fff}}
  .pricecard{{margin:34px 60px 0;background:#fff;border:2px solid #F3DFC8;border-radius:22px;
    display:flex;box-shadow:0 14px 34px rgba(170,100,30,.09);overflow:hidden}}
  .pricecard .cell{{flex:1;padding:22px 20px 20px;border-right:1px solid #F5E4D1}}
  .pricecard .cell:last-child{{border-right:0}}
  .pricecard .k{{font-size:14px;font-weight:800;letter-spacing:.16em;color:#B9A38B;margin-bottom:6px}}
  .pricecard .v{{font-family:'GMB';font-size:47px;font-weight:700;letter-spacing:-.03em;color:var(--ink);line-height:1.05;white-space:nowrap}}
  .pricecard .v small{{font-size:22px;font-weight:500;color:#8B7761;margin-left:7px;letter-spacing:0;vertical-align:2px}}
  .pricecard .v.ship{{font-family:'GMB';font-size:30px;line-height:1.4;color:var(--green)}}
  .pricecard .s{{font-size:17px;font-weight:600;color:var(--muted);margin-top:4px}}

  /* ---------- 2. TRUST ---------- */
  .trust{{background:var(--cream);padding:26px 44px 28px;display:flex;border-top:1px solid #F7E8D6;border-bottom:1px solid #F7E8D6}}
  .trust .it{{flex:1;text-align:center;padding:0 6px}}
  .trust .icw{{width:62px;height:62px;border-radius:50%;background:#fff;border:1.5px solid #F6DFC6;
    display:flex;align-items:center;justify-content:center;margin:0 auto 10px}}
  .trust .t{{font-size:21px;font-weight:800;color:#3D3228;letter-spacing:-.02em;line-height:1.3}}
  .trust .d{{font-size:16px;color:#8B7C6A;margin-top:3px;font-weight:500}}

  /* ---------- GIF BANDS ---------- */
  .gifband{{position:relative;background:var(--cream2);text-align:center}}
  .gifband img{{width:860px;display:block}}
  .gifband .tag{{position:absolute;left:0;right:0;top:-1px;height:6px;background:linear-gradient(90deg,#F26522,#FFB03A,#F26522)}}

  /* ---------- 3. SPEC CARDS ---------- */
  .spec{{background:#fff;padding:76px 60px 70px}}
  .spec h2{{margin:16px 0 14px}}
  .spec .lead{{max-width:680px}}
  .specgrid{{display:flex;flex-wrap:wrap;gap:18px;margin-top:38px}}
  .speccard{{width:352px;background:#fff;border:1.5px solid #F2DFC9;border-radius:22px;padding:26px 26px 24px;position:relative}}
  .speccard.soft{{background:var(--cream)}}
  .speccard .icw{{width:46px;height:46px;border-radius:14px;background:var(--cream2);display:flex;align-items:center;justify-content:center;margin-bottom:14px}}
  .speccard .v{{font-family:'GMB';font-size:68px;line-height:1;font-weight:700;letter-spacing:-.045em;color:var(--ink)}}
  .speccard .v small{{font-size:26px;font-weight:500;letter-spacing:-.01em;color:#8B7761;margin-left:4px}}
  .speccard .l{{font-size:22px;font-weight:800;margin-top:10px;color:#3D3228;letter-spacing:-.02em}}
  .speccard .d{{font-size:17px;color:var(--muted);line-height:1.55;margin-top:4px;font-weight:500}}

  /* ---------- 4. STATEMENT ---------- */
  .statement{{background:var(--cream);padding:78px 60px 74px;position:relative}}
  .statement .hd{{position:relative}}
  .statement h2{{margin:16px 0 22px}}
  .statement .handnote{{text-align:right;margin:22px 0 0}}
  .statement .handnote .b{{display:inline-block;background:#fff;border:2px solid #F0C695;border-radius:18px;padding:9px 16px;font-family:'HAND';font-size:26px;color:#96601E;box-shadow:0 10px 20px rgba(150,90,20,.1);transform:rotate(2.4deg)}}
  .statement .handbubble .b{{display:inline-block;background:#fff;border:2px solid #F0C695;border-radius:18px;
    padding:10px 16px;font-family:'HAND';font-size:25px;color:#96601E;box-shadow:0 10px 20px rgba(150,90,20,.1)}}
  .statement .lead{{max-width:700px}}
  .compare{{margin-top:36px;display:table;width:100%;table-layout:fixed;background:#fff;border-radius:22px;overflow:hidden;border:1.5px solid #F2DFC9}}
  .compare .head{{display:table-row}}
  .compare .col{{display:table-cell;vertical-align:top;padding:20px 22px 18px;width:auto}}
  .compare .col.k{{width:132px;background:#FFFBF4}}
  .compare .col.a{{background:linear-gradient(135deg,#FF8B45,#E4560E);color:#fff}}
  .compare .col.b{{background:#FBF6EE;color:#5E5041}}
  .compare .tag{{font-size:15px;font-weight:800;letter-spacing:.04em;opacity:.92}}
  .compare .nm{{font-family:'GMB';font-size:29px;font-weight:700;letter-spacing:-.03em;margin-top:4px}}
  .compare .row{{display:table-row}}
  .compare .row .k{{display:table-cell;width:132px;background:#FFFBF4;font-size:19px;font-weight:800;color:#A38F78;padding:19px 22px;vertical-align:middle}}
  .compare .row .v{{display:table-cell;padding:19px 22px;font-size:22px;font-weight:700;color:#3D3228;letter-spacing:-.02em;vertical-align:middle}}
  .compare .row .v.dim{{background:#FDFAF4;color:#8B7C6A;font-weight:500}}
  .fit{{display:flex;gap:16px;margin-top:18px}}
  .fit .col{{flex:1;background:#fff;border-radius:20px;padding:24px 22px;border:1.5px solid #F2DFC9}}
  .fit .col.no{{background:#FCF9F3;border-color:#EFE6D8}}
  .fit .hh{{font-size:20px;font-weight:800;letter-spacing:-.02em;margin-bottom:10px}}
  .fit .hh .badge{{display:inline-block;vertical-align:-5px;margin-right:8px}}
  .fit .col.no .hh{{color:#8B7C6A}}
  .fit .badge{{width:26px;height:26px;border-radius:50%;background:var(--orange);display:flex;align-items:center;justify-content:center;flex:none}}
  .fit .col.no .badge{{background:#C9BBAA}}
  .fit li{{list-style:none;font-size:19px;line-height:1.62;color:var(--body);padding-left:16px;position:relative;margin-top:7px;font-weight:500}}
  .fit li:before{{content:'';position:absolute;left:0;top:13px;width:6px;height:6px;border-radius:50%;background:var(--amber)}}
  .fit .col.no li:before{{background:#D8CBB9}}

  /* ---------- 5. POINT ---------- */
  .point{{position:relative;padding:76px 60px 0;background:#fff;overflow:hidden}}
  .point.cream{{background:var(--cream)}}
  .point .ghost{{position:absolute;right:26px;top:10px;font-family:'JUA';font-size:186px;line-height:1;
    color:#FDF1E1;z-index:0}}
  .point .inner{{position:relative;z-index:1}}
  .point h2{{margin:16px 0 20px;max-width:640px}}
  .point .lead{{max-width:690px}}
  .chips{{display:flex;gap:12px;margin-top:30px}}
  .chip{{flex:1;background:var(--cream);border-radius:18px;padding:20px 18px;border:1.5px solid #F4E3CF}}
  .chip .n{{font-family:'JUA';font-size:16px;color:var(--orange);letter-spacing:.02em}}
  .chip .t{{font-size:21px;font-weight:700;line-height:1.42;margin-top:6px;letter-spacing:-.02em;color:#3D3228}}
  .checks{{margin-top:28px}}
  .ck{{display:flex;align-items:flex-start;gap:14px;padding:18px 0;border-bottom:1px solid #F3E4D2}}
  .ck:last-child{{border-bottom:0}}
  .ck .dot{{width:34px;height:34px;border-radius:50%;background:var(--orange);display:flex;align-items:center;justify-content:center;flex:none;margin-top:2px}}
  .ck .t{{font-size:24px;line-height:1.55;color:#3D3228;font-weight:500;letter-spacing:-.02em}}
  .ck .t b{{font-weight:800;color:var(--ink)}}
  .photorow{{position:relative;margin:36px -60px 0;display:flex}}
  .photorow .big{{width:560px;height:520px;object-fit:cover}}
  .photorow .small{{width:300px;height:520px;object-fit:cover}}
  .photorow .sticker{{position:absolute;left:44px;bottom:34px;background:rgba(255,251,244,.96);border-radius:16px;
    padding:12px 18px;transform:rotate(-3deg);box-shadow:0 12px 26px rgba(120,60,10,.2);border:2px solid #fff}}
  .photorow .sticker .t{{font-family:'JUA';font-size:29px;color:var(--orange-dk);line-height:1.1}}
  .photorow .sticker .s{{font-size:11px;font-weight:800;letter-spacing:.16em;color:#C58F5C;margin-top:3px}}
  .pcap{{display:flex;justify-content:space-between;padding:14px 0 0;font-size:15px;font-weight:700;letter-spacing:.14em;color:#B7A48C}}

  /* ---------- 6. SHIPPING TIMELINE ---------- */
  .flow{{background:#fff;padding:78px 46px 76px}}
  .flow .hd{{padding:0 14px}}
  .flow h2{{margin:16px 0 14px}}
  .flow .strip{{display:flex;gap:14px;margin:26px 14px 0}}
  .flow .strip figure{{flex:1;position:relative}}
  .flow .strip img{{width:100%;height:250px;object-fit:cover;border-radius:18px}}
  .flow .strip .cap{{position:absolute;left:14px;bottom:14px;background:rgba(255,252,246,.94);border-radius:100px;
    padding:6px 14px;font-size:16px;font-weight:800;color:#8A5A20}}
  .tl{{margin-top:44px;position:relative}}
  .tl .rail{{position:absolute;left:20px;right:20px;top:43px;height:4px;background:repeating-linear-gradient(90deg,#F6DCC0 0 12px,transparent 12px 22px)}}
  .tl .row{{display:flex;position:relative}}
  .tl .st{{flex:1;text-align:center;padding:0 16px}}
  .tl .dot{{width:88px;height:88px;border-radius:50%;background:#fff;border:3px solid #FFD9B6;margin:0 auto;
    display:flex;align-items:center;justify-content:center;position:relative}}
  .tl .st.on .dot{{background:var(--orange);border-color:var(--orange)}}
  .tl .dot .no{{position:absolute;right:-6px;top:-6px;width:32px;height:32px;border-radius:50%;background:var(--ink);
    color:#fff;font-family:'JUA';font-size:18px;display:flex;align-items:center;justify-content:center}}
  .tl .time{{font-family:'GMB';font-size:31px;font-weight:700;letter-spacing:-.03em;margin-top:14px;color:var(--orange)}}
  .tl .st:nth-child(1) .time{{color:var(--ink)}}
  .tl .tt{{font-size:23px;font-weight:800;margin-top:2px;letter-spacing:-.02em}}
  .tl .dd{{font-size:17px;line-height:1.5;color:#7C6D5C;margin-top:7px;font-weight:500}}
  .flow .promise{{margin-top:34px;background:var(--cream);border-radius:20px;padding:26px 28px;display:flex;align-items:center;gap:18px;border:1.5px solid #F4E2CC}}
  .flow .promise .icw{{width:60px;height:60px;border-radius:50%;background:#fff;display:flex;align-items:center;justify-content:center;flex:none;border:1.5px solid #F3DFC8}}
  .flow .promise .t{{font-family:'GMB';font-size:29px;font-weight:700;letter-spacing:-.03em;line-height:1.3}}
  .flow .promise .s{{font-size:18px;color:#7C6D5C;font-weight:600;margin-top:2px}}

  /* ---------- 7. PACKING CUTAWAY ---------- */
  .pack{{background:var(--cream);padding:0 60px 76px}}
  .pack .box{{background:#fff;border-radius:24px;padding:30px 30px 26px;border:1.5px solid #F3E1CB}}
  .pack .ttl{{font-family:'GMB';font-size:32px;font-weight:700;letter-spacing:-.03em;margin-bottom:6px}}
  .pack .sub{{font-size:19px;color:#7C6D5C;font-weight:600}}
  .pack svg.cut{{width:100%;height:auto;margin-top:18px}}
  .pack .legend{{display:flex;gap:18px;margin-top:14px}}
  .pack .lg{{font-size:17px;font-weight:700;color:#8B7C6A;display:flex;align-items:center;gap:7px;white-space:nowrap}}
  .pack .lg i{{width:16px;height:16px;border-radius:4px;display:block;flex:none;border:1px solid rgba(0,0,0,.06)}}

  /* ---------- 8. SIZE ---------- */
  .size{{background:#fff;padding:78px 60px 72px}}
  .size .hero-row{{display:flex;align-items:center;gap:22px;margin-top:20px}}
  .size .hero-row .ref{{width:270px;flex:none}}
  .size .hero-row .ref img{{width:270px;height:186px;object-fit:cover;border-radius:18px}}
  .size .hero-row .ref .cap{{font-size:16px;font-weight:700;color:#9A846C;margin-top:8px;letter-spacing:-.01em}}
  .size .bignum{{flex:1}}
  .size .bignum .v{{font-family:'GMB';font-size:88px;line-height:1;font-weight:700;letter-spacing:-.045em;color:var(--orange)}}
  .size .bignum .v small{{font-size:30px;color:#9A846C;margin-left:6px;letter-spacing:0}}
  .size .bignum .k{{font-size:17px;font-weight:700;color:#9A846C;margin-top:6px;letter-spacing:.02em}}
  .size .handsv{{margin-bottom:6px}}
  .sizegrid{{display:flex;gap:18px;margin-top:34px}}
  .boxcard{{flex:1;background:var(--cream);border-radius:22px;padding:24px 22px 20px;border:1.5px solid #F4E2CC;position:relative}}
  .boxcard.best{{background:#FFF6E9;border-color:#F6CFA6}}
  .boxcard .rib{{position:absolute;right:18px;top:-13px;background:var(--orange);color:#fff;font-family:'JUA';
    font-size:15px;padding:6px 14px;border-radius:100px;letter-spacing:.02em}}
  .boxcard .kg{{font-family:'GMB';font-size:40px;font-weight:700;letter-spacing:-.03em;line-height:1}}
  .boxcard .kg small{{font-size:21px;color:#9A846C;margin-left:3px}}
  .boxcard .cnt{{font-size:20px;font-weight:800;color:var(--orange-dk);margin-top:5px;font-family:'GMB';letter-spacing:-.02em}}
  .boxcard .dots{{margin-top:12px}}
  .boxcard .won{{font-size:17px;font-weight:700;color:#7C6D5C;margin-top:10px}}
  .bars{{margin-top:22px;background:#fff;border:1.5px solid #F2DFC9;border-radius:20px;padding:24px 26px}}
  .bars .bt{{font-size:19px;font-weight:800;color:#3D3228;margin-bottom:14px}}
  .bars .b{{display:flex;align-items:center;gap:12px;margin-top:10px}}
  .bars .lb{{width:78px;font-size:18px;font-weight:800;color:#6B5C4B}}
  .bars .tr{{flex:1;height:26px;background:#F8EFE3;border-radius:6px;overflow:hidden}}
  .bars .tr i{{display:block;height:26px;border-radius:6px}}
  .bars .vl{{width:172px;text-align:right;font-family:'GMB';font-size:21px;font-weight:700;letter-spacing:-.02em}}
  .spec-table{{margin-top:22px;border:1.5px solid #F2DFC9;border-radius:20px;overflow:hidden}}
  .spec-table .r{{display:flex;border-bottom:1px solid #F6E7D5}}
  .spec-table .r:last-child{{border-bottom:0}}
  .spec-table .k{{flex:none;width:210px;background:#FFFBF4;padding:16px 22px;font-size:19px;font-weight:800;color:#8B7C6A}}
  .spec-table .v{{flex:1;padding:16px 22px;font-size:22px;font-weight:700;color:#3D3228;letter-spacing:-.02em}}
  .spec-table .v span{{font-size:18px;font-weight:600;color:#9A846C;margin-left:6px}}
  .tip{{margin-top:18px;background:#FFF8EC;border-radius:16px;padding:18px 22px;font-size:18px;line-height:1.65;color:#7C6D5C;font-weight:500;border:1.5px dashed #F0D3AE}}
  .tip b{{color:#B4520E;font-weight:800}}

  /* ---------- 9. OPTIONS ---------- */
  .opt{{background:var(--cream);padding:78px 60px 74px}}
  .opt h2{{margin:16px 0 30px}}
  .ocards{{display:flex;gap:18px}}
  .ocard{{flex:1;background:#fff;border-radius:24px;padding:28px 26px 26px;border:2px solid #F1DEC8;position:relative}}
  .ocard.best{{border-color:var(--orange);box-shadow:0 16px 34px rgba(200,100,20,.12)}}
  .ocard .rib{{position:absolute;right:20px;top:-15px;background:var(--orange);color:#fff;font-family:'JUA';font-size:16px;padding:7px 16px;border-radius:100px}}
  .ocard .w{{font-size:15px;font-weight:800;letter-spacing:.16em;color:#B4A08A}}
  .ocard .kg{{font-family:'GMB';font-size:56px;line-height:1.1;font-weight:700;letter-spacing:-.04em;margin-top:4px}}
  .ocard .kg small{{font-size:26px;color:#9A846C;margin-left:3px}}
  .ocard .meta{{font-size:19px;font-weight:700;color:#6B5C4B;margin-top:2px}}
  .ocard .line{{height:1.5px;background:#F3E3D0;margin:18px 0 14px}}
  .ocard .price{{font-family:'GMB';font-size:50px;font-weight:700;letter-spacing:-.04em;line-height:1}}
  .ocard .price small{{font-size:24px;color:#8B7761;margin-left:3px}}
  .ocard .per{{font-size:19px;font-weight:700;color:var(--orange-dk);margin-top:6px}}
  .ocard ul{{margin-top:16px}}
  .ocard li{{list-style:none;font-size:19px;line-height:1.55;color:var(--body);padding-left:18px;position:relative;margin-top:7px;font-weight:500}}
  .ocard li:before{{content:'';position:absolute;left:0;top:12px;width:7px;height:7px;border-radius:50%;background:var(--amber)}}
  .opt .foot{{margin-top:22px;display:flex;align-items:center;justify-content:center;gap:12px;font-size:17px;font-weight:700;color:#8B7C6A}}
  .opt .foot i{{width:5px;height:5px;border-radius:50%;background:#D8C4AC;display:block}}

  /* ---------- 10. STORAGE ---------- */
  .keep{{background:#fff;padding:78px 60px 76px}}
  .keep h2{{margin:16px 0 8px}}
  .keep .lead{{max-width:660px}}
  .kgrid{{display:flex;flex-wrap:wrap;gap:18px;margin-top:34px}}
  .kcard{{width:352px;background:var(--cream);border-radius:22px;padding:24px 24px 22px;border:1.5px solid #F4E2CC;position:relative}}
  .kcard .step{{font-family:'JUA';font-size:20px;color:var(--orange);letter-spacing:.04em}}
  .kcard .ttl{{font-size:24px;font-weight:800;line-height:1.35;margin-top:6px;letter-spacing:-.025em;color:#2E251C;padding-right:52px}}
  .kcard .d{{font-size:18px;line-height:1.6;color:#7C6D5C;margin-top:8px;font-weight:500}}
  .kcard .icw{{position:absolute;right:22px;top:22px;width:52px;height:52px;border-radius:16px;background:#fff;display:flex;align-items:center;justify-content:center;border:1.5px solid #F3DFC8}}
  .temp{{margin-top:18px;display:flex;gap:14px}}
  .temp .t{{flex:1;background:#F4FAF6;border:1.5px solid #CFE7D8;border-radius:18px;padding:20px 22px;display:flex;align-items:center;gap:14px}}
  .temp .t.cold{{background:#F4F9FD;border-color:#D3E4F2}}
  .temp .v{{font-family:'GMB';font-size:30px;font-weight:700;letter-spacing:-.03em;color:#204C39}}
  .temp .t.cold .v{{color:#1E4A6B}}
  .temp .k{{font-size:17px;font-weight:700;color:#7C6D5C;margin-top:1px}}

  /* ---------- 11. FAQ ---------- */
  .faq{{background:var(--cream);padding:78px 60px 70px}}
  .faq h2{{margin:16px 0 28px}}
  .qa{{background:#fff;border-radius:20px;padding:24px 26px;margin-top:14px;border:1.5px solid #F3E2CE}}
  .qa .qrow{{display:flex;gap:14px;align-items:flex-start}}
  .qa .q{{width:40px;height:40px;border-radius:50%;background:var(--orange);color:#fff;font-family:'JUA';
    font-size:24px;display:flex;align-items:center;justify-content:center;flex:none;margin-top:1px}}
  .qa .qt{{font-size:25px;font-weight:800;line-height:1.42;letter-spacing:-.03em;color:#2E251C;padding-top:4px}}
  .qa .at{{font-size:21px;line-height:1.66;color:#4C4238;margin:12px 0 0 2px;font-weight:400}}
  .qa .at b{{font-weight:800;color:var(--ink)}}

  /* ---------- 12. CS ---------- */
  .cs{{background:#fff;padding:76px 60px 68px}}
  .cs h2{{margin:16px 0 28px}}
  .csgrid{{display:flex;flex-wrap:wrap;gap:18px}}
  .cscard{{width:352px;background:var(--cream);border-radius:20px;padding:24px 24px 22px;border:1.5px solid #F4E2CC}}
  .cscard .icw{{width:48px;height:48px;border-radius:14px;background:#fff;display:flex;align-items:center;justify-content:center;border:1.5px solid #F3DFC8;margin-bottom:12px}}
  .cscard .t{{font-size:23px;font-weight:800;letter-spacing:-.02em}}
  .cscard .d{{font-size:19px;line-height:1.62;color:#6B5C4B;margin-top:7px;font-weight:500}}
  .cscard .d b{{color:var(--orange-dk);font-weight:800}}

  /* ---------- 13. CLOSING ---------- */
  .closing{{background:#fff;padding:0 60px 60px}}
  .closing .box{{background:linear-gradient(160deg,#FFF6E8,#FFE9CE 70%,#FFDFBB);border-radius:28px;padding:52px 46px 44px;text-align:center;position:relative;overflow:hidden}}
  .closing .eyebrow{{color:#B4520E}}
  .closing h2{{margin:14px 0 14px;font-size:52px}}
  .closing .p{{font-size:23px;color:#6B5C4B;font-weight:600}}
  .closing .hn{{font-family:'HAND';font-size:34px;color:#A65A16;margin-top:16px}}
  .closing .badges{{display:flex;justify-content:center;gap:10px;margin-top:26px}}
  .closing .badge{{background:#fff;border-radius:16px;padding:14px 20px;box-shadow:0 10px 22px rgba(170,100,30,.1)}}
  .closing .badge small{{display:block;font-size:13px;font-weight:800;letter-spacing:.14em;color:#B4A08A}}
  .closing .badge b{{font-family:'GMB';font-size:29px;font-weight:700;letter-spacing:-.03em;white-space:nowrap}}

  /* ---------- 14. FOOTER ---------- */
  .footer{{background:#FBF7F1;padding:34px 60px 40px;border-top:1px solid #F1E3D2}}
  .footer .bm{{font-family:'GMB';font-size:24px;font-weight:700;letter-spacing:.1em}}
  .footer .slogan{{font-size:16px;color:#8B7C6A;margin-top:5px;font-weight:500}}
  .footer .cs2{{font-size:16px;color:#6B5C4B;font-weight:600;text-align:right;line-height:1.7}}
  .footer .legal{{margin-top:18px;font-size:14px;line-height:1.8;color:#A49380;font-weight:500}}
  .footer .legal b{{color:#8B7C6A;font-weight:700}}
"""


# ----------------------------------------------------------------------------
# 3. 공통 파편
# ----------------------------------------------------------------------------
def split_marks() -> str:
    return '<div class="mark-mid"></div>'


def img(d: dict, key: str, cls: str = "", w: int = 0, h: int = 0, alt: str = "") -> str:
    name = d.get("images", {}).get(key)
    if not name:
        return ""
    size = ""
    if w:
        size += f"width:{w}px;"
    if h:
        size += f"height:{h}px;"
    return f'<img class="{cls}" src="assets/{name}" style="{size}" alt="{escape(alt)}">'


def para(lines) -> str:
    if isinstance(lines, str):
        lines = [lines]
    return "<br>".join(lines)


# ----------------------------------------------------------------------------
# 4. 섹션 빌더
# ----------------------------------------------------------------------------
def sec_topbar(d):
    t = d.get("topbar", {})
    return (f'<div class="tb"><div class="l">{escape(t.get("left", ""))}</div>'
            f'<div class="r">{escape(t.get("right", ""))}</div></div>')


def sec_hero(d):
    h = d.get("hero", {})
    title = h.get("title", ["", "", ""])
    while len(title) < 3:
        title.append("")
    st = h.get("sticker", {})
    pills = "".join(
        f'<div class="pill{" on" if i == 0 else ""}">{escape(p)}</div>'
        for i, p in enumerate(h.get("pills", [])))
    prices = ""
    for p in h.get("prices", []):
        if p.get("wide"):
            prices += (f'<div class="cell"><div class="k">{escape(p.get("label", ""))}</div>'
                       f'<div class="v ship">{escape(p.get("value", ""))}</div>'
                       f'<div class="s">{escape(p.get("sub", ""))}</div></div>')
        else:
            prices += (f'<div class="cell"><div class="k">{escape(p.get("label", ""))}</div>'
                       f'<div class="v">{escape(p.get("value", ""))}<small>{escape(p.get("unit", "원"))}</small></div>'
                       f'<div class="s">{escape(p.get("sub", ""))}</div></div>')
    return f"""
  <div class="hero">
    <div class="brandrow">
      <div class="wordmark">{emoji(d.get('emoji_codes', {}).get('fruit', '1f34a'), 24)} {escape(d.get('meta', {}).get('brand', ''))}</div>

    </div>
    <div class="shot">
      {img(d, 'hero', alt=d.get('meta', {}).get('product', ''))}
      <div class="live"><i></i>{escape(h.get('live', 'LIVE'))} {escape(h.get('live_note', ''))}</div>
      <div class="stkr"><b>{escape(st.get('big', ''))}</b><span>{escape(st.get('text', ''))}</span><s>{escape(st.get('small', ''))}</s></div>
      <div class="cap">{escape(h.get('photo_caption', ''))}</div>
    </div>
    <div class="copy">
      <div class="kick">{escape(h.get('kicker', ''))}</div>
      <h1><span class="l1">{escape(title[0])}</span><span class="l2">{escape(title[1])}</span><span class="l3">{escape(title[2])}</span></h1>
      <div class="handline"><span class="t">{escape(h.get('hand', ''))}</span>
        <svg width="196" height="22" viewBox="0 0 196 22"><path d="M3 14 C 40 5, 70 20, 105 12 S 165 4, 193 11" stroke="#F26522" stroke-width="5" fill="none" stroke-linecap="round" opacity=".85"/></svg>
      </div>
      <div class="sub">{para(h.get('body', []))}</div>
      <div class="pills">{pills}</div>
    </div>
    <div class="pricecard">{prices}</div>
  </div>"""


def sec_trust(d):
    items = d.get("trust", [])
    out = []
    for it in items:
        out.append(f"""<div class="it"><div class="icw">{icon(it.get('icon', 'check'), 28, C['orange'])}</div>
      <div class="t">{escape(it.get('title', ''))}</div><div class="d">{escape(it.get('desc', ''))}</div></div>""")
    return f'<div class="trust">{"".join(out)}</div>'


def sec_gif_band(name, ratio_h, note=""):
    return (f'<div class="gifband"><div class="tag"></div>'
            f'<img src="{name}" width="860" height="{ratio_h}" alt="{escape(note)}"></div>')


def sec_specs(d):
    s = d.get("specs", {})
    if not s:
        return ""
    cards = ""
    for i, c in enumerate(s.get("cards", [])):
        soft = " soft" if i % 3 == 1 else ""
        cards += f"""<div class="speccard{soft}">
        <div class="icw">{icon(c.get('icon', 'star'), 26, C['orange'])}</div>
        <div class="v">{escape(str(c.get('value', '')))}<small>{escape(c.get('unit', ''))}</small></div>
        <div class="l">{escape(c.get('label', ''))}</div>
        <div class="d">{escape(c.get('desc', ''))}</div></div>"""
    note = f'<div class="tip" style="margin-top:20px">{icon("info", 20, C["orange"], 2, "em")} {s.get("note", "")}</div>' if s.get("note") else ""
    return f"""
  <div class="spec sec">
    <div class="eyebrow"><span class="ln"></span>{escape(s.get('eyebrow', ''))}</div>
    <h2>{para(s.get('title', []))}</h2>
    <div class="lead">{s.get('lead', '')}</div>
    <div class="specgrid">{cards}</div>
    {note}
  </div>"""


def sec_statement(d):
    st = d.get("statement", {})
    if not st:
        return ""
    cmp_ = st.get("compare", {})
    rows = ""
    for r in cmp_.get("rows", []):
        rows += (f'<div class="row"><div class="k">{escape(r.get("k", ""))}</div>'
                 f'<div class="v">{escape(r.get("a", ""))}</div>'
                 f'<div class="v dim">{escape(r.get("b", ""))}</div></div>')
    fit = st.get("fit", {})
    yes = "".join(f"<li>{escape(x)}</li>" for x in fit.get("yes", []))
    no = "".join(f"<li>{escape(x)}</li>" for x in fit.get("no", []))
    return f"""
  <div class="statement">
    <div class="hd">
      <div class="eyebrow"><span class="ln"></span>{escape(st.get('eyebrow', ''))}</div>
      <h2>{para(st.get('title', []))}</h2>
    </div>
    <div class="handnote"><div class="b">{escape(st.get('hand', ''))}</div></div>
    <div class="lead">{st.get('lead', '')}</div>
    <div class="compare">
      <div class="head"><div class="col k"></div>
        <div class="col a"><div class="tag">{escape(cmp_.get('tag_a', ''))}</div><div class="nm">{escape(cmp_.get('name_a', ''))}</div></div>
        <div class="col b"><div class="tag">{escape(cmp_.get('tag_b', ''))}</div><div class="nm">{escape(cmp_.get('name_b', ''))}</div></div>
      </div>{rows}
    </div>
    <div class="fit">
      <div class="col yes"><div class="hh"><span class="badge">{icon('check', 15, '#fff', 3.4)}</span>{escape(fit.get('yes_title', '이런 분께 맞습니다'))}</div><ul>{yes}</ul></div>
      <div class="col no"><div class="hh"><span class="badge">{icon('x', 13, '#fff', 3.4)}</span>{escape(fit.get('no_title', '이런 분은 다른 상품이 맞습니다'))}</div><ul>{no}</ul></div>
    </div>
    <div class="note" style="margin-top:18px">{st.get('note', '')}</div>
  </div>"""


def sec_point(d, p, idx):
    cream = " cream" if p.get("tone") == "cream" else ""
    ghost = escape(p.get("no", f"{idx:02d}"))
    chips = ""
    if p.get("chips"):
        chips = '<div class="chips">' + "".join(
            f'<div class="chip"><div class="n">{escape(c.get("n", ""))}</div><div class="t">{escape(c.get("t", ""))}</div></div>'
            for c in p["chips"]) + "</div>"
    checks = ""
    if p.get("checks"):
        checks = '<div class="checks">' + "".join(
            f'<div class="ck"><div class="dot">{icon("check", 17, "#fff", 3.2)}</div>'
            f'<div class="t">{c}</div></div>' for c in p["checks"]) + "</div>"
    photos = ""
    if p.get("photo"):
        sticker = ""
        if p.get("sticker"):
            sticker = (f'<div class="sticker"><div class="t">{escape(p["sticker"].get("t", ""))}</div>'
                       f'<div class="s">{escape(p["sticker"].get("s", ""))}</div></div>')
        photos = (f'<div class="photorow">{img(d, p["photo"], "big")}{img(d, p.get("photo2", p["photo"]), "small")}{sticker}</div>'
                  f'<div class="pcap"><span>{escape(p.get("cap_l", ""))}</span><span>{escape(p.get("cap_r", ""))}</span></div>')
    return f"""
  <div class="point{cream}">
    <div class="ghost">{ghost}</div>
    <div class="inner">
      <div class="eyebrow"><span class="ln"></span>{escape(p.get('eyebrow', ''))}</div>
      <h2>{para(p.get('title', []))}</h2>
      <div class="lead">{p.get('lead', '')}</div>
      {chips}{checks}
    </div>
    {photos}
  </div>"""


def sec_shipping(d):
    s = d.get("shipping", {})
    if not s:
        return ""
    steps = ""
    for i, st in enumerate(s.get("steps", [])):
        on = " on" if i == 0 else ""
        color = "#fff" if i == 0 else C["orange"]
        steps += f"""<div class="st{on}"><div class="dot">{icon(st.get('icon', 'box'), 38, color, 1.8)}<div class="no">{i+1}</div></div>
        <div class="time">{escape(st.get('time', ''))}</div>
        <div class="tt">{escape(st.get('title', ''))}</div>
        <div class="dd">{escape(st.get('desc', ''))}</div></div>"""
    pr = s.get("promise", {})
    strip = ""
    if s.get("photos"):
        figs = ""
        for ph in s["photos"]:
            figs += f'<figure>{img(d, ph["key"])}<div class="cap">{escape(ph.get("cap", ""))}</div></figure>'
        strip = f'<div class="strip">{figs}</div>'
    # 한 층 포장 단면도
    box_svg = ""
    if s.get("cutaway"):
        box_svg = f"""
    <div class="pack" style="padding:0 60px 0">
      <div class="box">
        <div class="ttl">{escape(s['cutaway'].get('title', '상자 단면'))}</div>
        <div class="sub">{escape(s['cutaway'].get('sub', ''))}</div>
        <svg class="cut" viewBox="0 0 700 262" xmlns="http://www.w3.org/2000/svg">
          <!-- 뚜껑 -->
          <rect x="70" y="14" width="560" height="30" rx="6" fill="#E6CBAB" stroke="#CBA075" stroke-width="2.5"/>
          <line x1="70" y1="29" x2="630" y2="29" stroke="#D9B78F" stroke-width="1.5"/>
          <path d="M350 54 v14" stroke="#CBA075" stroke-width="2.5" stroke-dasharray="5 5"/>
          <path d="M344 62 l6 8 l6 -8" fill="none" stroke="#CBA075" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
          <!-- 박스 -->
          <rect x="60" y="82" width="580" height="158" rx="8" fill="#EAD2B3" stroke="#C79A67" stroke-width="3"/>
          <rect x="76" y="98" width="548" height="126" rx="4" fill="#FFFBF4" stroke="#E3C7A6" stroke-width="2"/>
          <!-- 바닥 완충재 -->
          <path d="M76 186 q18 -10 36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 L624 224 L76 224 Z" fill="#F7E5CE"/>
          <!-- 귤 -->
          <g>
            <circle cx="140" cy="158" r="31" fill="#EF8930"/>
            <path d="M118 146 a31 31 0 0 1 40 -8" stroke="#FFC084" stroke-width="7" fill="none" stroke-linecap="round"/>
            <circle cx="235" cy="158" r="31" fill="#F2913A"/>
            <path d="M213 146 a31 31 0 0 1 40 -8" stroke="#FFC084" stroke-width="7" fill="none" stroke-linecap="round"/>
            <circle cx="330" cy="158" r="31" fill="#EF8930"/>
            <path d="M308 146 a31 31 0 0 1 40 -8" stroke="#FFC084" stroke-width="7" fill="none" stroke-linecap="round"/>
            <circle cx="425" cy="158" r="31" fill="#F49A45"/>
            <path d="M403 146 a31 31 0 0 1 40 -8" stroke="#FFC084" stroke-width="7" fill="none" stroke-linecap="round"/>
            <circle cx="520" cy="158" r="31" fill="#EF8930"/>
            <path d="M498 146 a31 31 0 0 1 40 -8" stroke="#FFC084" stroke-width="7" fill="none" stroke-linecap="round"/>
            <circle cx="592" cy="158" r="26" fill="#F2913A"/>
            <path d="M574 148 a26 26 0 0 1 34 -7" stroke="#FFC084" stroke-width="6" fill="none" stroke-linecap="round"/>
            <ellipse cx="150" cy="128" rx="15" ry="7" fill="#3D8B5C" transform="rotate(-18 150 128)"/>
            <ellipse cx="440" cy="128" rx="15" ry="7" fill="#3D8B5C" transform="rotate(-14 440 128)"/>
          </g>
          <!-- 위 완충재 -->
          <path d="M76 112 q18 -9 36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 L624 92 L76 92 Z" fill="#FFFDF8" opacity=".95"/>
          <path d="M76 112 q18 -9 36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0 t36 0" fill="none" stroke="#EBD9C2" stroke-width="2"/>
          <!-- 옆면 크림색 종이 -->
          <path d="M76 98 q10 26 0 52 q12 6 0 20" fill="#FDF6EA" stroke="#EBD9C2" stroke-width="1.6"/>
          <path d="M624 98 q-10 26 0 52 q-12 6 0 20" fill="#FDF6EA" stroke="#EBD9C2" stroke-width="1.6"/>
        </svg>
        <div class="legend">
          <div class="lg"><i style="background:#FFFDF8;border:1px solid #E0C6A6"></i>{escape(s['cutaway'].get('l1', '종이 완충재'))}</div>
          <div class="lg"><i style="background:#F58A34"></i>{escape(s['cutaway'].get('l2', '한 층 · 눌림 방지'))}</div>
          <div class="lg"><i style="background:#EFD4B4;border:1px solid #D3A877"></i>{escape(s['cutaway'].get('l3', '5중 골판지'))}</div>
        </div>
      </div>
    </div>"""
    return f"""
  <div class="flow">
    <div class="hd">
      <div class="eyebrow"><span class="ln"></span>{escape(s.get('eyebrow', ''))}</div>
      <h2>{para(s.get('title', []))}</h2>
      <div class="lead">{s.get('lead', '')}</div>
    </div>
    {strip}
    <div class="tl"><div class="rail"></div><div class="row">{steps}</div></div>
    <div class="promise"><div class="icw">{icon(pr.get('icon', 'truck'), 30, C['orange'])}</div>
      <div><div class="t">{escape(pr.get('title', ''))}</div><div class="s">{escape(pr.get('desc', ''))}</div></div></div>
  </div>{box_svg}"""


def dot_grid(n: int, cols: int = 9, r: int = 8.4, gap: int = 19, color: str = "#F58A34") -> str:
    rows = math.ceil(n / cols)
    w = cols * gap
    h = rows * gap
    dots = []
    k = 0
    for y in range(rows):
        for x in range(cols):
            if k >= n:
                break
            dots.append(f'<circle cx="{gap/2 + x*gap:.1f}" cy="{gap/2 + y*gap:.1f}" r="{r}" fill="{color}"/>')
            k += 1
    return (f'<svg width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(dots)}</svg>')


def sec_size(d):
    s = d.get("size", {})
    if not s:
        return ""
    cards = ""
    for i, b in enumerate(s.get("boxes", [])):
        best = " best" if b.get("best") else ""
        rib = f'<div class="rib">{escape(b.get("rib", "BEST VALUE"))}</div>' if b.get("best") else ""
        cards += f"""<div class="boxcard{best}">{rib}
        <div class="kg">{escape(str(b.get('kg', '')))}<small>kg</small></div>
        <div class="cnt">{escape(b.get('count', ''))}</div>
        <div class="dots">{dot_grid(int(b.get('dots', 36)), 9, 8.4, 19, C['orange'] if b.get('best') else '#F8A868')}</div>
        <div class="won">{escape(b.get('won', ''))}</div></div>"""
    bars = ""
    if s.get("bars"):
        mx = max(x["value"] for x in s["bars"])
        for b in s["bars"]:
            pct = int(b["value"] / mx * 100)
            bars += (f'<div class="b"><div class="lb">{escape(b["label"])}</div>'
                     f'<div class="tr"><i style="width:{pct}%;background:{b.get("color", C["orange"])}"></i></div>'
                     f'<div class="vl">{escape(b["text"])}</div></div>')
        bars = (f'<div class="bars"><div class="bt">{escape(s.get("bars_title", "100g당 가격"))}</div>{bars}</div>')
    rows = "".join(
        f'<div class="r"><div class="k">{escape(r["k"])}</div><div class="v">{escape(r["v"])}'
        f'{f"<span>{escape(r["note"])}</span>" if r.get("note") else ""}</div></div>'
        for r in s.get("table", []))
    tip = f'<div class="tip">{icon("info", 19, C["orange"], 2, "em")} {s["tip"]}</div>' if s.get("tip") else ""
    return f"""
  <div class="size">
    <div class="eyebrow"><span class="ln"></span>{escape(s.get('eyebrow', ''))}</div>
    <h2>{para(s.get('title', []))}</h2>
    <div class="hero-row">
      <div class="bignum">
        <div class="v">{escape(s.get('big_value', ''))}<small>{escape(s.get('big_unit', 'mm'))}</small></div>
        <div class="k">{escape(s.get('big_label', ''))}</div>
        <svg width="240" height="18" viewBox="0 0 240 18" style="margin-top:10px"><path d="M4 11 C 44 3, 84 17, 124 9 S 200 3, 236 10" stroke="#F26522" stroke-width="4.6" fill="none" stroke-linecap="round" opacity=".8"/></svg>
      </div>
      <div class="ref">{img(d, 'size')}<div class="cap">{escape(s.get('ref_caption', ''))}</div></div>
    </div>
    <div class="sizegrid">{cards}</div>
    {bars}
    <div class="spec-table">{rows}</div>
    {tip}
  </div>"""


def sec_options(d):
    o = d.get("options", {})
    if not o:
        return ""
    cards = ""
    for it in o.get("cards", []):
        best = " best" if it.get("best") else ""
        rib = f'<div class="rib">{escape(it.get("rib", "BEST"))}</div>' if it.get("best") else ""
        li = "".join(f"<li>{escape(x)}</li>" for x in it.get("points", []))
        cards += f"""<div class="ocard{best}">{rib}
        <div class="w">{escape(it.get('weight_label', ''))}</div>
        <div class="kg">{escape(str(it.get('kg', '')))}<small>kg</small></div>
        <div class="meta">{escape(it.get('meta', ''))}</div>
        <div class="line"></div>
        <div class="price">{escape(it.get('price', ''))}<small>원</small></div>
        <div class="per">{escape(it.get('per', ''))}</div>
        <ul>{li}</ul></div>"""
    foot = o.get("foot", [])
    foot_html = '<i></i>'.join(f"<span>{escape(x)}</span>" for x in foot)
    return f"""
  <div class="opt">
    <div class="eyebrow"><span class="ln"></span>{escape(o.get('eyebrow', ''))}</div>
    <h2>{para(o.get('title', []))}</h2>
    <div class="ocards">{cards}</div>
    <div class="foot">{foot_html}</div>
  </div>"""


def sec_storage(d):
    s = d.get("storage", {})
    if not s:
        return ""
    cards = ""
    for i, c in enumerate(s.get("steps", [])):
        cards += f"""<div class="kcard"><div class="icw">{icon(c.get('icon', 'cold'), 26, C['orange'])}</div>
        <div class="step">STEP {i+1:02d}</div>
        <div class="ttl">{escape(c.get('title', ''))}</div>
        <div class="d">{escape(c.get('desc', ''))}</div></div>"""
    temp = ""
    if s.get("temps"):
        parts = ""
        for i, t in enumerate(s["temps"]):
            cold = " cold" if i % 2 else ""
            parts += (f'<div class="t{cold}">{icon(t.get("icon", "thermo"), 26, "#1E4A6B" if i % 2 else "#204C39")}'
                      f'<div><div class="v">{escape(t.get("value", ""))}</div><div class="k">{escape(t.get("label", ""))}</div></div></div>')
        temp = f'<div class="temp">{parts}</div>'
    return f"""
  <div class="keep">
    <div class="eyebrow"><span class="ln"></span>{escape(s.get('eyebrow', ''))}</div>
    <h2>{para(s.get('title', []))}</h2>
    <div class="lead">{s.get('lead', '')}</div>
    <div class="kgrid">{cards}</div>
    {temp}
  </div>"""


def sec_faq(d):
    items = d.get("faq", [])
    if not items:
        return ""
    qs = "".join(
        f'<div class="qa"><div class="qrow"><div class="q">Q</div><div class="qt">{escape(i["q"])}</div></div>'
        f'<div class="at">{i["a"]}</div></div>' for i in items)
    return f"""
  <div class="faq">
    <div class="eyebrow"><span class="ln"></span>BEFORE YOU ORDER</div>
    <h2>주문 전에<br>많이 묻는 것들</h2>
    {qs}
  </div>"""


def sec_cs(d):
    s = d.get("cs", {})
    if not s:
        return ""
    cards = ""
    for c in s.get("cards", []):
        cards += (f'<div class="cscard"><div class="icw">{icon(c.get("icon", "truck"), 24, C["orange"])}</div>'
                  f'<div class="t">{escape(c.get("title", ""))}</div><div class="d">{c.get("desc", "")}</div></div>')
    return f"""
  <div class="cs">
    <div class="eyebrow"><span class="ln"></span>{escape(s.get('eyebrow', ''))}</div>
    <h2>{para(s.get('title', []))}</h2>
    <div class="csgrid">{cards}</div>
  </div>"""


def sec_closing(d):
    c = d.get("closing", {})
    if not c:
        return ""
    badges = "".join(
        f'<div class="badge"><small>{escape(b.get("label", ""))}</small><b>{escape(b.get("value", ""))}</b></div>'
        for b in c.get("badges", []))
    return f"""
  <div class="closing">
    <div class="box">
      <div class="eyebrow">{escape(c.get('eyebrow', ''))}</div>
      <h2>{para(c.get('title', []))}</h2>
      <div class="p">{c.get('lead', '')}</div>
      <div class="hn">{escape(c.get('hand', ''))}</div>
      <div class="badges">{badges}</div>
    </div>
  </div>"""


def sec_footer(d):
    f = d.get("footer", {})
    legal = "<br>".join(f.get(k, "") for k in ("legal1", "legal2", "legal3") if f.get(k))
    return f"""
  <div class="footer">
    <div style="display:flex;justify-content:space-between;align-items:flex-start">
      <div><div class="bm">{escape(d.get('meta', {}).get('brand', ''))}</div>
        <div class="slogan">{escape(f.get('slogan', ''))}</div></div>
      <div class="cs2">{escape(f.get('cs1', ''))}<br>{escape(f.get('cs2', ''))}</div>
    </div>
    <div class="legal">{legal}</div>
  </div>"""


# ----------------------------------------------------------------------------
# 5. HTML 조립
# ----------------------------------------------------------------------------
def build_html(d: dict) -> str:
    meta = d.get("meta", {})
    brand, product = meta.get("brand", ""), meta.get("product", "")
    title = f"{product} | {brand}"
    points = d.get("points", [])
    body = [sec_topbar(d), sec_hero(d), sec_trust(d)]
    if d.get("gif", {}).get("enabled", True):
        body.append(sec_gif_band("gif_01_benefit.gif", d.get("gif", {}).get("h1", 300)))
    body.append(sec_specs(d))
    body.append(sec_statement(d))
    if len(points) > 0:
        body.append(sec_point(d, points[0], 1))
    if d.get("gif", {}).get("enabled", True):
        body.append(sec_gif_band("gif_02_peel_juice.gif", d.get("gif", {}).get("h2", 600)))
    if len(points) > 1:
        body.append('<div class="mark-mid" style="height:0;line-height:0"></div>')
        body.append(sec_point(d, points[1], 2))
    if len(points) > 2:
        body.append(sec_point(d, points[2], 3))
    body.append(sec_shipping(d))
    body.append(sec_size(d))
    body.append(sec_options(d))
    if d.get("gif", {}).get("enabled", True):
        body.append(sec_gif_band("gif_03_check.gif", d.get("gif", {}).get("h3", 300)))
    body.append('<div class="mark-bot" style="height:0;line-height:0"></div>')
    body.append(sec_storage(d))
    body.append(sec_faq(d))
    body.append(sec_cs(d))
    body.append(sec_closing(d))
    body.append(sec_footer(d))

    out_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{escape(title)}</title>
<meta name="description" content="{escape(d.get('seo', {}).get('description', ''))}">
<style>{build_css(d)}</style>
</head>
<body>
<div class="page">
{''.join(body)}
</div>
</body>
</html>
"""
    return keepall(out_html)


def _wj_text(s: str) -> str:
    """텍스트 노드 안에서 '띄어쓰기에서만' 줄이 바뀌도록 WORD JOINER를 넣는다.
    HTML 엔티티(&amp; 등)는 건드리지 않는다."""
    chunks = re.split(r'(&[a-zA-Z]+;|&#\d+;)', s)
    out = []
    for i, ch in enumerate(chunks):
        if i % 2 == 1:
            out.append(ch)
        else:
            out.append(re.sub(r'(?<=[^ \n\t.,!?:;)\]}"”’])(?=[^ \n\t(\[{"“‘])', '\u2060', ch))
    return ''.join(out)


def keepall(html: str) -> str:
    """WeasyPrint(Pango)이 word-break:keep-all 을 지키지 않아
    어절 단위로 줄이 바뀌게 만든다."""
    parts = re.split(r'(<[^>]+>)', html)
    out, in_style = [], False
    for p in parts:
        if p.startswith('<'):
            low = p.lower()
            if low.startswith('<style'):
                in_style = True
            elif low.startswith('</style'):
                in_style = False
            out.append(p)
        elif in_style:
            out.append(p)
        else:
            out.append(_wj_text(p))
    return ''.join(out)


# ----------------------------------------------------------------------------
# 6. 파이프라인
# ----------------------------------------------------------------------------
def log(msg):
    print(msg, flush=True)



def shrink_image(path, max_side=1800, quality=90):
    """출력용 사진 최적화: 긴 변 1800px, JPEG 90%. (원본 파일은 건드리지 않음)"""
    from PIL import Image
    try:
        im = Image.open(path)
    except Exception:
        return
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    w, h = im.size
    if max(w, h) <= max_side and os.path.getsize(path) < 700_000:
        im.close()
        return
    k = max_side / max(w, h)
    if k < 1:
        im = im.resize((int(w * k), int(h * k)), Image.LANCZOS)
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jpg", ".jpeg"):
        im.save(path, quality=quality, optimize=True, progressive=True)
    else:
        im.save(path, optimize=True)
    im.close()


def copy_assets(d: dict, data_dir: str, out: str):
    adir = os.path.join(out, "assets")
    os.makedirs(adir, exist_ok=True)
    src_dirs = [os.path.join(data_dir, d.get("images_dir", "assets")), data_dir, BASE_DIR,
                os.path.join(BASE_DIR, "assets", "example")]
    for key, name in d.get("images", {}).items():
        if not name:
            continue
        dst = os.path.join(adir, os.path.basename(name))
        if os.path.exists(dst):
            continue
        for sd in src_dirs:
            cand = os.path.join(sd, name)
            if os.path.exists(cand):
                shutil.copy2(cand, dst)
                shrink_image(dst)
                break
        else:
            log(f"  ! 이미지 없음: {name}")
    # 이모지
    ed = os.path.join(adir, "emoji")
    os.makedirs(ed, exist_ok=True)
    src_e = os.path.join(BASE_DIR, "assets", "emoji")
    if os.path.isdir(src_e):
        for f in os.listdir(src_e):
            shutil.copy2(os.path.join(src_e, f), os.path.join(ed, f))


def subset_fonts(html_text: str, out: str):
    """HTML에 실제로 쓰인 글자만 남겨 woff2로 서브셋 (CLI 경로 사용 — 라틴/숫자 누락 방지)."""
    from fontTools import subset as fts
    fdir = os.path.join(out, "fonts")
    os.makedirs(fdir, exist_ok=True)
    chars = set(html_text)
    chars |= set("0123456789.,:;!?~-–—·()[]{}'\"’“”/\\%+×=<>@#&*_|°°"
                 "가나다라마바사아자차카타파하")
    text = "".join(sorted(c for c in chars if c not in "\r\n\t"))
    work = os.path.join(out, "work")
    os.makedirs(work, exist_ok=True)
    charset_path = os.path.join(work, "charset.txt")
    with open(charset_path, "w", encoding="utf-8") as f:
        f.write(text)
    plan = [
        ("GmarketSansBold.ttf", "GmarketSansBold.subset.woff2"),
        ("GmarketSansMedium.ttf", "GmarketSansMedium.subset.woff2"),
        ("Jua-Regular.ttf", "Jua.subset.woff2"),
        ("MapoGoldenPierA.ttf", "MapoGoldenPier.subset.woff2"),
        ("Pretendard-Regular.ttf", "Pretendard-Regular.subset.woff2"),
        ("Pretendard-Medium.ttf", "Pretendard-Medium.subset.woff2"),
        ("Pretendard-SemiBold.ttf", "Pretendard-SemiBold.subset.woff2"),
        ("Pretendard-Bold.ttf", "Pretendard-Bold.subset.woff2"),
        ("Pretendard-ExtraBold.ttf", "Pretendard-ExtraBold.subset.woff2"),
    ]
    for src, dst in plan:
        sp = os.path.join(FONT_DIR, src)
        if not os.path.exists(sp):
            log(f"  ! 폰트 없음: {src}")
            continue
        fts.main([
            sp,
            f"--text-file={charset_path}",
            "--flavor=woff2",
            "--layout-features=*",
            "--name-IDs=*",
            "--notdef-outline",
            "--desubroutinize",
            "--drop-tables+=FFTM",
            f"--output-file={os.path.join(fdir, dst)}",
        ])
    log(f"  폰트 서브셋 완료 ({len(text)}자)")


def _walk(box, fn, skip_self=False):
    if not skip_self:
        fn(box)
    for ch in getattr(box, "children", []) or []:
        _walk(ch, fn)


def render_pngs(out: str, prefix: str, slug: str, scale: int = 2, html_name: str = "source.html"):
    import weasyprint
    import pymupdf
    from PIL import Image

    src = os.path.join(out, "work", html_name)
    # PNG 렌더에서는 GIF 대신 대표 정지컷을 쓴다 (WeasyPrint는 GIF를 못 읽는 경우가 있음)
    render_path = src
    posters = {"gif_01_benefit.gif": "poster_01.png", "gif_02_peel_juice.gif": "poster_02.png",
               "gif_03_check.gif": "poster_03.png"}
    if os.path.exists(os.path.join(out, "assets", "poster_01.png")):
        render_path = os.path.join(out, "work", "render.html")
        html = open(src, encoding="utf-8").read()
        for g, pst in posters.items():
            html = html.replace(f'src="{g}"', f'src="assets/{pst}"')
        open(render_path, "w", encoding="utf-8").write(html)
    doc = weasyprint.HTML(filename=render_path, base_url=out + "/").render()
    page = doc.pages[0]

    content_bottom = [0.0]
    marks = {}

    def visit(b):
        y = float(getattr(b, "position_y", 0) or 0) + float(getattr(b, "height", 0) or 0)
        content_bottom[0] = max(content_bottom[0], y)
        el = getattr(b, "element", None)
        if el is not None:
            cls = (el.get("class") or "")
            if "mark-mid" in cls and "mid" not in marks:
                marks["mid"] = float(b.position_y)
            if "mark-bot" in cls and "bot" not in marks:
                marks["bot"] = float(b.position_y)

    _walk(page._page_box, visit, skip_self=True)
    H = content_bottom[0]
    log(f"  레이아웃 높이 {H:.0f}px (860px 폭 기준) / 마커 {marks}")

    work_pdf = os.path.join(out, "work", "page.pdf")
    doc.write_pdf(work_pdf)
    pdf = pymupdf.open(work_pdf)
    if pdf.page_count > 1:
        log(f"  ! 페이지가 {pdf.page_count}장으로 나뉘었습니다 — @page 높이를 늘려주세요")

    y1_css = marks.get("mid", H * 0.35)
    y2_css = marks.get("bot", H * 0.7)
    segs = [(0, y1_css), (y1_css, y2_css), (y2_css, H)]
    names = ["상단", "중단", "하단"]

    os.makedirs(os.path.join(out, "860"), exist_ok=True)
    crops_860 = []
    for (a, b), nm in zip(segs, names):
        clip = pymupdf.Rect(0, max(0, a) * 0.75, 860 * 0.75, min(b, H) * 0.75)
        mat = pymupdf.Matrix(scale * 96 / 72, scale * 96 / 72)
        pix = pdf[0].get_pixmap(matrix=mat, clip=clip)
        p = os.path.join(out, f"{prefix}_{nm}.png")
        pix.save(p)
        im = Image.open(p).convert("RGB")
        small = im.resize((860, int(im.height * 860 / im.width)), Image.LANCZOS)
        sp = os.path.join(out, "860", f"{prefix}_{nm}_860.png")
        small.save(sp, optimize=True)
        crops_860.append(small)
        log(f"  {os.path.basename(p)}  {im.width}x{im.height}")
        im.close()

    total_h = sum(c.height for c in crops_860)
    full = Image.new("RGB", (860, total_h), "white")
    yy = 0
    for c in crops_860:
        full.paste(c, (0, yy))
        yy += c.height
    full.save(os.path.join(out, f"{prefix}_전체.png"), optimize=True)
    log(f"  {prefix}_전체.png  860x{total_h}")
    pdf.close()


def make_all(out: str, data: dict, data_dir: str, prefix: str, scale: int = 2, do_gif: bool = True):
    os.makedirs(os.path.join(out, "work"), exist_ok=True)
    log("[1/5] 사진·이모지 복사")
    copy_assets(data, data_dir, out)

    log("[2/5] HTML 생성")
    html = build_html(data)
    src_path = os.path.join(out, "work", "source.html")
    with open(src_path, "w", encoding="utf-8") as f:
        f.write(html)
    # GIF가 실제로 움직이는 배포용 HTML
    slug = data.get("meta", {}).get("product_slug", "상품")
    ver = data.get("meta", {}).get("version", "v6")
    pub_path = os.path.join(out, f"{prefix}_{slug}.html")
    with open(pub_path, "w", encoding="utf-8") as f:
        f.write(html)
    log(f"  {os.path.basename(pub_path)}")

    log("[3/5] 폰트 서브셋")
    subset_fonts(html, out)

    if do_gif and data.get("gif", {}).get("enabled", True):
        log("[4/5] GIF 3종 렌더")
        try:
            import gif_renderer
            gif_renderer.build_all(out, data)
        except Exception as e:  # noqa
            log(f"  ! GIF 생성 실패: {e}")

    log("[5/5] PNG 렌더 + 분할")
    render_pngs(out, prefix, slug, scale=scale)

    write_notes(out, data, prefix)
    log("완료: " + out)


# ----------------------------------------------------------------------------
# 7. 제작 노트
# ----------------------------------------------------------------------------
def write_notes(out: str, d: dict, prefix: str):
    meta = d.get("meta", {})
    ver = meta.get("version", "v6")
    product = meta.get("product", "")
    files = []
    for nm in ("상단", "중단", "하단", "전체"):
        p = os.path.join(out, f"{prefix}_{nm}.png")
        if os.path.exists(p):
            from PIL import Image
            im = Image.open(p)
            files.append((f"{prefix}_{nm}.png", im.width, im.height, os.path.getsize(p) / 1e6))
            im.close()
    rows = "\n".join(f"| `{n}` | {w}×{h} | {s:.1f}MB |" for n, w, h, s in files)
    gif_rows = []
    for g in ("gif_01_benefit.gif", "gif_02_peel_juice.gif", "gif_03_check.gif"):
        p = os.path.join(out, g)
        if os.path.exists(p):
            gif_rows.append(f"| `{g}` | {os.path.getsize(p)/1024:.0f}KB |")
    notes = f"""# {product} 상세페이지 {ver} — 제작 노트

생성 {time.strftime('%Y-%m-%d %H:%M')} · `generate_detail_page.py` 자동 생성

## 1. 이번 버전에서 바꾼 것

| 항목 | 이전(v4) | {ver} |
|---|---|---|
| 배경 | 다크 에메랄드 섹션 | `#FFFFFF` · `#FFF9F0` · `#FFF3E2` 밝은 상업용 톤. 딥그린은 작은 배지에만 |
| 본문 글자 | 15~17px | **24~25px** (860px 기준), 한 줄 15자 이내 |
| 섹션 제목 | 44~50px | **52~54px** |
| 핵심 숫자 | 28~74px | **56~86px** |
| GIF | 어두운 배경 3종 | **밝은 톤으로 재렌더** 3종 (히어로 배지 · 껍질→과즙 · 옵션 체크) |
| 배송·보관·스펙 | 줄글 | **인포그래픽**(4단계 타임라인 · 상자 단면도 · 도트 개수 · 100g당 가격 바) |

## 2. 산출물

| 파일 | 크기 | 용량 |
|---|---|---|
{rows}

GIF 3종:

| 파일 | 용량 |
|---|---|
{chr(10).join(gif_rows)}

- `860/` — 스마트스토어 업로드용 860px 3분할
- `{prefix}_{meta.get('product_slug','')}.html` — GIF가 실제로 움직이는 원본
- `assets/` — 사용한 사진과 이모지(트위모지 CC-BY 4.0)

## 3. 디자인 공식 (2026 상위 판매자 리서치 반영)

1. **첫 화면 3요소** — 대표 실사컷 + 한 줄 약속 + 가격·무료배송. 스크롤 전 3초 안에 "이거 괜찮다"를 만든다.
2. **구매 전 5가지 의심 순서** — ①이게 뭔데 ②품질은 ③얼마나 들어있어 ④배송은 안전해 ⑤교환·환불은. 섹션 순서가 곧 이 순서다.
3. **사진 70 : 글 30** — 식품은 10~18컷. 색감이 구매 결정의 대부분을 차지하므로 밝은 자연광 톤을 유지한다.
4. **숫자 먼저, 형용사 금지** — "정성껏" 대신 "53–62mm · 33–38개 · 익일 도착".
5. **신뢰 요소 3곳 이상 분산** — 상단 신뢰바 · 중단 산지/선별 · 하단 보상 기준.
6. **CTA 2회** — 중간(GIF 체크 카드) · 하단(클로징 가격 배지).
7. **모바일 타이포** — 860px 기준 본문 24pt 이상, 제목 36pt 이상, 한 줄 15자 이내(2026 모바일 최적화 가이드).
8. **분할 업로드** — 860px 폭, 5,000px 이하로 나눠 올리면 로딩이 느려지지 않는다.

## 4. 섹션 흐름

0. 상단 띠 — 한정·무료배송을 첫 줄에
1. 히어로 — 실사컷 · 큰 제목 · 손글씨 한 줄 · 가격 카드
2. 신뢰바 4종 — 산지직송 / 한 층 포장 / 당일 출고 / 파손 보상
3. GIF 01 — 산지직송·당일수확 + 숫자 3개 카운트업
4. 숫자로 보는 한 상자 — 당도·지름·무게·수확 시기 카드
5. 왜 덜 단가 — 비교표 + 맞음/안 맞음 (두괄식)
6. POINT 01 — 껍질 (사진 2컷 + CHECK 3개 + 스티커)
7. GIF 02 — 껍질 → 과육 → 과즙
8. POINT 02 — 향 (체크 3개 + 손글씨)
9. POINT 03 — 밭→문 앞 4단계 타임라인 + 상자 단면도
10. 크기·개수 — 53–62mm · 도트 개수 · 100g당 가격 바 · 스펙표
11. 옵션 — 2.5kg / 4.5kg 카드
12. GIF 03 — 구매 전 3초 체크 (중간 CTA)
13. 보관 4단계 + 온도 카드
14. FAQ 5문항
15. 배송·교환/환불
16. 클로징 + 가격 배지 (하단 CTA)
17. 푸터 — 사업자 정보

## 5. 게시 전 반드시 바꿀 것

- **사진**: AI 생성 시안 컷입니다. 실제 상품 사진으로 교체하세요(`assets/` 안 파일명만 같게 덮으면 그대로 재생성).
- **사업자 정보**: {d.get('footer', {}).get('legal1', '')}
- **가격·배송비**: 판매 시점 값으로 재확인.
- **스펙 수치**: {d.get('specs', {}).get('note', '')}
- **출고·보상 기준**: 실제 운영 기준으로.

## 6. 다시 만들 때

```bash
python3 generate_detail_page.py --data product.example.json --out ./out/제주감귤
```
"""
    p = os.path.join(out, f"{ver}_제작노트.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(notes)
    log(f"  {os.path.basename(p)}")


def main():
    ap = argparse.ArgumentParser(description="상세페이지 자동 생성기")
    ap.add_argument("--data", required=True, help="상품 데이터 JSON 경로")
    ap.add_argument("--out", required=True, help="산출물 폴더")
    ap.add_argument("--scale", type=int, default=2, help="PNG 배율 (기본 2 → 1720px)")
    ap.add_argument("--no-gif", action="store_true", help="GIF 생성 건너뛰기")
    args = ap.parse_args()

    data_path = os.path.abspath(args.data)
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    data_dir = os.path.dirname(data_path)
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    meta = data.get("meta", {})
    prefix = meta.get("file_prefix", f"상세페이지_{meta.get('version','v6')}")
    log(f"▶ {meta.get('product','')} → {out}")
    make_all(out, data, data_dir, prefix, scale=args.scale, do_gif=not args.no_gif)


if __name__ == "__main__":
    main()
