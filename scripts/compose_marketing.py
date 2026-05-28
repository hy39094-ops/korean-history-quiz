"""
실제 앱 캡쳐(assets-store/screenshots-real/*.png)를 1080x1920 마케팅 캔버스에
폰 mockup + 상단 캡션으로 합성. Google Play Console 등록용.
한국사검정시험 기출집 — Pretendard 폰트, 남색 톤.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "assets-store", "screenshots-real")
OUT_DIR = os.path.join(ROOT, "assets-store", "screenshots")
FONT_DIR = os.path.join(ROOT, "assets-store", "fonts")
os.makedirs(OUT_DIR, exist_ok=True)

F_BLACK = os.path.join(FONT_DIR, "Pretendard-Black.otf")
F_BOLD = os.path.join(FONT_DIR, "Pretendard-Bold.otf")
F_SEMIBOLD = os.path.join(FONT_DIR, "Pretendard-SemiBold.otf")
F_MEDIUM = os.path.join(FONT_DIR, "Pretendard-Medium.otf")

# 한국사 브랜드 톤: 진한 남색
BLUE_TOP = (30, 64, 175)    # #1E40AF
BLUE_BOT = (12, 24, 66)
ACCENT = (245, 197, 66)     # 전통 느낌의 골드
WHITE = (255, 255, 255)
TEXT_SUB = (210, 221, 245)
PHONE_BG = (245, 247, 252)
DARK = (24, 33, 55)


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def gradient_bg(w: int, h: int) -> Image.Image:
    col = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        r = int(BLUE_TOP[0] * (1 - t) + BLUE_BOT[0] * t)
        g = int(BLUE_TOP[1] * (1 - t) + BLUE_BOT[1] * t)
        b = int(BLUE_TOP[2] * (1 - t) + BLUE_BOT[2] * t)
        col.putpixel((0, y), (r, g, b))
    return col.resize((w, h))


def soft_blobs(img: Image.Image) -> None:
    w, h = img.size
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for cx, cy, r, color in [
        (-int(w * 0.18), -int(h * 0.08), int(w * 0.55), (70, 110, 210, 90)),
        (int(w * 0.62), int(h * 0.82), int(w * 0.6), (40, 70, 150, 90)),
        (int(w * 0.8), int(h * 0.05), int(w * 0.3), (245, 197, 66, 45)),
    ]:
        od.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    ov = ov.filter(ImageFilter.GaussianBlur(radius=80))
    img.alpha_composite(ov)


@dataclass
class Slide:
    src: str
    headline: list[str]
    sub: str
    out: str


SLIDES = [
    Slide("01_home.png",
          ["한국사 기출,", "회차별로 통째로 풀기"],
          "심화·기본 · 최신 기출 1,100문제 수록",
          "phone-01_home.png"),
    Slide("02_question.png",
          ["실전 그대로,", "50분 타이머 모의고사"],
          "사료 이미지까지 실제 시험처럼",
          "phone-02_exam.png"),
    Slide("03_answer.png",
          ["풀면 바로", "정답을 확인해요"],
          "틀린 문제는 오답 노트에 자동 저장",
          "phone-03_answer.png"),
    Slide("04_result.png",
          ["점수로 합격선까지", "한눈에 확인"],
          "약점만 골라 다시 풀어요",
          "phone-04_result.png"),
]


def make_phone(canvas_w, canvas_h, capture):
    phone_w = int(canvas_w * 0.74)
    phone_h = int(phone_w * 2.05)
    max_h = int(canvas_h * 0.70)
    if phone_h > max_h:
        phone_h = max_h
        phone_w = int(phone_h / 2.05)
    bezel = max(10, int(phone_w * 0.025))
    inner_w = phone_w - bezel * 2
    inner_h = phone_h - bezel * 2

    cap_w, cap_h = capture.size
    scale = inner_w / cap_w
    scaled = capture.resize((inner_w, int(cap_h * scale)), Image.LANCZOS)

    display = Image.new("RGB", (inner_w, inner_h), PHONE_BG)
    if scaled.height > inner_h:
        display.paste(scaled.crop((0, 0, inner_w, inner_h)), (0, 0))
    else:
        # 콘텐츠가 짧으면(예: 결과 화면) 세로 중앙 정렬로 빈 공간 균형
        y = (inner_h - scaled.height) // 2
        display.paste(scaled, (0, y))

    mask = Image.new("L", display.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, inner_w, inner_h], radius=int(inner_w * 0.075), fill=255)

    phone = Image.new("RGBA", (phone_w, phone_h), (0, 0, 0, 0))
    ImageDraw.Draw(phone).rounded_rectangle([0, 0, phone_w, phone_h], radius=int(phone_w * 0.1), fill=DARK + (255,))
    drgba = display.convert("RGBA")
    drgba.putalpha(mask)
    phone.paste(drgba, (bezel, bezel), drgba)
    return phone


def draw_caption(draw, w, top_y, headline, sub):
    hs = int(w * 0.078)
    f_head = font(F_BLACK, hs)
    f_sub = font(F_MEDIUM, int(w * 0.034))
    cy = top_y
    for line in headline:
        bb = draw.textbbox((0, 0), line, font=f_head)
        lw = bb[2] - bb[0]
        draw.text((int((w - lw) / 2 - bb[0]), cy - bb[1]), line, font=f_head, fill=WHITE)
        cy += bb[3] - bb[1] + int(hs * 0.18)
    line_w = int(w * 0.18)
    line_h = int(w * 0.0045) + 1
    cy += int(hs * 0.05)
    draw.rounded_rectangle([(w - line_w) // 2, cy, (w + line_w) // 2, cy + line_h], radius=line_h // 2, fill=ACCENT)
    cy += line_h + int(hs * 0.4)
    bb = draw.textbbox((0, 0), sub, font=f_sub)
    sw = bb[2] - bb[0]
    draw.text((int((w - sw) / 2 - bb[0]), cy - bb[1]), sub, font=f_sub, fill=TEXT_SUB)
    return cy + (bb[3] - bb[1])


def render(slide, w, h):
    capture = Image.open(os.path.join(SRC_DIR, slide.src)).convert("RGB")
    img = gradient_bg(w, h).convert("RGBA")
    soft_blobs(img)
    draw = ImageDraw.Draw(img)
    cap_bottom = draw_caption(draw, w, int(h * 0.06), slide.headline, slide.sub)

    phone = make_phone(w, h, capture)
    px = (w - phone.width) // 2
    avail_top = cap_bottom + int(h * 0.025)
    avail_bot = h - int(h * 0.06)
    py = max(avail_top, avail_top + ((avail_bot - avail_top) - phone.height) // 2)

    shadow = Image.new("RGBA", (phone.width + 80, phone.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([40, 50, 40 + phone.width, 50 + phone.height], radius=int(phone.width * 0.1), fill=(0, 0, 0, 130))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=24))
    img.alpha_composite(shadow, (px - 40, py - 40))
    img.alpha_composite(phone, (px, py))

    f_wm = font(F_SEMIBOLD, int(w * 0.022))
    wm = "한국사검정시험 기출집"
    bb = draw.textbbox((0, 0), wm, font=f_wm)
    ww = bb[2] - bb[0]
    draw.text((int((w - ww) / 2 - bb[0]), h - int(h * 0.04)), wm, font=f_wm, fill=(195, 210, 240))

    out = os.path.join(OUT_DIR, slide.out)
    img.convert("RGB").save(out, "PNG", optimize=True)
    print(f"saved: {out}")


if __name__ == "__main__":
    for s in SLIDES:
        render(s, 1080, 1920)
