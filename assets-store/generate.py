"""Generate logo (light/dark) and thumbnail for 한국사능력검정시험 기출문제집.

Concept: Korean traditional seal (印章) but with modern Pretendard typography.
Horizontal seal text, much heavier weights, tighter modern layout.
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import random

OUT = Path(__file__).parent
FONT_DIR = OUT / "fonts"

PT_BLACK = str(FONT_DIR / "Pretendard-Black.otf")
PT_BOLD = str(FONT_DIR / "Pretendard-Bold.otf")
PT_SEMI = str(FONT_DIR / "Pretendard-SemiBold.otf")
PT_MED = str(FONT_DIR / "Pretendard-Medium.otf")

# Palette
HANJI = "#F2E8D5"
HANJI_DARK = "#16161C"
SEAL_RED = "#B7322C"
INK = "#1A1A20"
INK_SOFT = "#6E6353"
WHITE = "#FFFFFF"


def f(path: str, size: int):
    return ImageFont.truetype(path, size)


def text_center(draw, cx, cy, text, fnt, fill, tracking=0):
    if tracking == 0:
        bbox = draw.textbbox((0, 0), text, font=fnt)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text(
            (cx - w / 2 - bbox[0], cy - h / 2 - bbox[1]),
            text,
            font=fnt,
            fill=fill,
        )
        return
    glyphs = [(ch, draw.textbbox((0, 0), ch, font=fnt)) for ch in text]
    total_w = sum((g[1][2] - g[1][0]) for g in glyphs) + tracking * (len(text) - 1)
    h = max((g[1][3] - g[1][1]) for g in glyphs)
    x = cx - total_w / 2
    for ch, bbox in glyphs:
        cw = bbox[2] - bbox[0]
        draw.text((x - bbox[0], cy - h / 2 - bbox[1]), ch, font=fnt, fill=fill)
        x += cw + tracking


def paper_texture(img, dark=False):
    rng = random.Random(7)
    w, h = img.size
    d = ImageDraw.Draw(img, "RGBA")
    color = (0, 0, 0, 12) if not dark else (255, 255, 255, 12)
    for _ in range(int(w * h * 0.0025)):
        d.point((rng.randint(0, w - 1), rng.randint(0, h - 1)), fill=color)


def draw_seal(d, cx, cy, size, text="한국사", seal_color=SEAL_RED, text_color=WHITE):
    """Square red seal with horizontal bold Korean text inside."""
    half = size // 2
    box = (cx - half, cy - half, cx + half, cy + half)
    d.rectangle(box, fill=seal_color)
    inset = size // 14
    d.rectangle(
        (cx - half + inset, cy - half + inset,
         cx + half - inset, cy + half - inset),
        outline=text_color,
        width=max(3, size // 100),
    )
    char_size = int(size * 0.30)
    fnt = f(PT_BLACK, char_size)
    text_center(d, cx, cy, text, fnt, text_color, tracking=-int(char_size * 0.04))


def make_logo(path, paper, ink, ink_soft, dark=False):
    S = 600
    img = Image.new("RGB", (S, S), paper)
    paper_texture(img, dark=dark)
    d = ImageDraw.Draw(img)

    # top eyebrow
    text_center(d, S / 2, 92, "한국사능력검정시험",
                f(PT_BOLD, 34), ink_soft, tracking=2)
    d.rectangle((S / 2 - 22, 118, S / 2 + 22, 121), fill=SEAL_RED)

    # seal (smaller, balanced)
    draw_seal(d, cx=S // 2, cy=S // 2 + 6, size=260)

    # bottom (Black weight, larger)
    text_center(d, S / 2, S - 80, "기출문제집",
                f(PT_BLACK, 58), ink, tracking=-3)

    img.save(path)
    print(f"saved {path}")


def make_thumbnail(path):
    W, H = 1932, 828
    img = Image.new("RGB", (W, H), HANJI)
    paper_texture(img, dark=False)
    d = ImageDraw.Draw(img)

    # Left: seal
    seal_size = 500
    seal_cx = 460
    seal_cy = H // 2
    draw_seal(d, seal_cx, seal_cy, seal_size)

    # Right: text block
    tx = 1020
    # eyebrow
    d.text((tx, 195), "K O R E A N   H I S T O R Y   E X A M",
           font=f(PT_BOLD, 32), fill=INK_SOFT)
    d.rectangle((tx, 250, tx + 64, 253), fill=SEAL_RED)
    # title line 1
    d.text((tx, 278), "한국사능력검정시험", font=f(PT_BLACK, 92), fill=INK)
    # title line 2 (accent)
    d.text((tx, 392), "기출문제집", font=f(PT_BLACK, 148), fill=SEAL_RED)
    # subline
    d.text((tx, 600), "회차별 기출 · 해설 · 오답노트",
           font=f(PT_SEMI, 40), fill=INK_SOFT)

    img.save(path)
    print(f"saved {path}")


if __name__ == "__main__":
    make_logo(OUT / "logo-light.png", paper=HANJI, ink=INK, ink_soft=INK_SOFT)
    make_logo(OUT / "logo-dark.png", paper=HANJI_DARK,
              ink="#F4ECDD", ink_soft="#A8997A", dark=True)
    make_thumbnail(OUT / "thumbnail.png")
