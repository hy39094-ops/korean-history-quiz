"""
Google Play 등록용 아이콘(512x512) + 그래픽 이미지(1024x500) 생성.
한국사검정시험 기출집 — 남색 + 골드, Pretendard.
"""
import os
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets-store")
FONT_DIR = os.path.join(OUT, "fonts")
os.makedirs(OUT, exist_ok=True)

F_BLACK = os.path.join(FONT_DIR, "Pretendard-Black.otf")
F_BOLD = os.path.join(FONT_DIR, "Pretendard-Bold.otf")
F_SEMIBOLD = os.path.join(FONT_DIR, "Pretendard-SemiBold.otf")
F_MEDIUM = os.path.join(FONT_DIR, "Pretendard-Medium.otf")

NAVY_TOP = (37, 78, 190)
NAVY_BOT = (10, 22, 60)
GOLD = (240, 195, 75)
GOLD_SOFT = (250, 218, 130)
WHITE = (255, 255, 255)
SUB = (205, 217, 245)


def f(path, size):
    return ImageFont.truetype(path, size=size)


def diag_gradient(w, h, top, bot):
    """대각선 느낌의 세로 그라데이션."""
    col = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        col.putpixel((0, y), tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3)))
    return col.resize((w, h))


def center_text(draw, cx, cy, text, font, fill):
    bb = draw.textbbox((0, 0), text, font=font)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    draw.text((cx - w / 2 - bb[0], cy - h / 2 - bb[1]), text, font=font, fill=fill)
    return w, h


def make_icon():
    S = 512
    img = diag_gradient(S, S, NAVY_TOP, NAVY_BOT).convert("RGBA")
    # 은은한 광원
    ov = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.ellipse([-120, -150, 320, 290], fill=(90, 130, 230, 80))
    od.ellipse([S - 200, S - 160, S + 160, S + 200], fill=(245, 195, 75, 50))
    ov = ov.filter(ImageFilter.GaussianBlur(60))
    img.alpha_composite(ov)

    d = ImageDraw.Draw(img)
    # 상단 골드 라인 + "한능검 기출" 태그
    tag_font = f(F_BOLD, 40)
    tag = "한능검 기출"
    bb = d.textbbox((0, 0), tag, font=tag_font)
    tw = bb[2] - bb[0]
    # 태그 배경 pill
    pad_x, pad_y = 26, 12
    pill_w = tw + pad_x * 2
    pill_h = (bb[3] - bb[1]) + pad_y * 2
    pill_x = (S - pill_w) // 2
    pill_y = 96
    d.rounded_rectangle([pill_x, pill_y, pill_x + pill_w, pill_y + pill_h], radius=pill_h // 2,
                        fill=(255, 255, 255, 28))
    center_text(d, S / 2, pill_y + pill_h / 2, tag, tag_font, GOLD_SOFT)

    # 메인 타이틀 "한국사"
    title_font = f(F_BLACK, 168)
    center_text(d, S / 2, 268, "한국사", title_font, WHITE)

    # 하단 "기출집"
    sub_font = f(F_BLACK, 78)
    center_text(d, S / 2, 392, "기출집", sub_font, GOLD)

    # 골드 언더라인
    line_w = 150
    d.rounded_rectangle([(S - line_w) // 2, 446, (S + line_w) // 2, 456], radius=5, fill=GOLD)

    img.convert("RGB").save(os.path.join(OUT, "icon-512.png"), "PNG", optimize=True)
    print("saved: icon-512.png (512x512)")


def make_feature():
    W, H = 1024, 500
    img = diag_gradient(W, H, NAVY_TOP, NAVY_BOT).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.ellipse([-160, -180, 360, 320], fill=(90, 130, 230, 80))
    od.ellipse([W - 320, H - 200, W + 160, H + 220], fill=(245, 195, 75, 45))
    ov = ov.filter(ImageFilter.GaussianBlur(70))
    img.alpha_composite(ov)
    d = ImageDraw.Draw(img)

    left = 70
    # 상단 태그
    tag_font = f(F_BOLD, 30)
    tag = "2026 최신 기출"
    bb = d.textbbox((0, 0), tag, font=tag_font)
    tw = bb[2] - bb[0]
    pad_x, pad_y = 22, 10
    d.rounded_rectangle([left, 96, left + tw + pad_x * 2, 96 + (bb[3] - bb[1]) + pad_y * 2],
                        radius=24, fill=(255, 255, 255, 30))
    d.text((left + pad_x - bb[0], 96 + pad_y - bb[1]), tag, font=tag_font, fill=GOLD_SOFT)

    # 메인 타이틀
    t_font = f(F_BLACK, 76)
    d.text((left, 168), "한국사능력검정시험", font=t_font, fill=WHITE)
    d.text((left, 256), "기출집", font=t_font, fill=GOLD)

    # 부제
    s_font = f(F_MEDIUM, 34)
    d.text((left, 372), "회차별 기출 · 실전 타이머 · 오답 노트로 합격까지", font=s_font, fill=SUB)

    # 오른쪽 장식: 골드 원 + 펼친 책 아이콘
    cx, cy = W - 175, H // 2
    d.ellipse([cx - 105, cy - 105, cx + 105, cy + 105], outline=GOLD, width=6)
    bw, bh = 116, 84
    bx, by = cx - bw // 2, cy - bh // 2
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=10, outline=GOLD_SOFT, width=6)
    d.line([cx, by + 8, cx, by + bh - 8], fill=GOLD_SOFT, width=5)  # 가운데 접힘선
    for i in range(3):
        ly = by + 24 + i * 17
        d.line([bx + 16, ly, cx - 12, ly], fill=GOLD_SOFT, width=4)
        d.line([cx + 12, ly, bx + bw - 16, ly], fill=GOLD_SOFT, width=4)

    img.convert("RGB").save(os.path.join(OUT, "feature-graphic-1024x500.png"), "PNG", optimize=True)
    print("saved: feature-graphic-1024x500.png (1024x500)")


if __name__ == "__main__":
    make_icon()
    make_feature()
