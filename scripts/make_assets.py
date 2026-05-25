"""앱인토스 콘솔 등록용 로고·썸네일 생성.

출력:
  public/logo.png        — 1024x1024 (앱 아이콘용)
  public/thumbnail.png   — 1920x1080 (스토어 썸네일/대표 이미지용)

특징
- 크롭 없이 안전영역 안에 텍스트 배치
- 토스 블루(#1E40AF) 배경 + 노랑 강조(#FBBF24)
- 한국어 폰트는 Apple SD Gothic Neo (macOS 기본)
"""
import unicodedata
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PROJECT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT / "public"

BG = "#1E40AF"
ACCENT = "#FBBF24"
WHITE = "#FFFFFF"
SUB = "#DBEAFE"

FONT_CANDIDATES = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
    "/Library/Fonts/AppleGothic.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def make_gradient_bg(w: int, h: int) -> Image.Image:
    """위 → 아래로 진한 파랑 → 살짝 밝은 파랑 그라데이션."""
    top = (30, 64, 175)
    bottom = (37, 99, 235)
    img = Image.new("RGB", (w, h), top)
    for y in range(h):
        ratio = y / h
        r = int(top[0] + (bottom[0] - top[0]) * ratio)
        g = int(top[1] + (bottom[1] - top[1]) * ratio)
        b = int(top[2] + (bottom[2] - top[2]) * ratio)
        ImageDraw.Draw(img).line([(0, y), (w, y)], fill=(r, g, b))
    return img


def center_text(draw, text, y, font, fill, w):
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    draw.text(((w - tw) // 2 - bb[0], y), text, fill=fill, font=font)
    return bb[3] - bb[1]


def make_logo():
    size = 1024
    img = make_gradient_bg(size, size)
    draw = ImageDraw.Draw(img)

    # 노란 상단 띠
    band_h = 18
    draw.rectangle([(0, 0), (size, band_h)], fill=ACCENT)

    # 안전영역: 양쪽 100px 여백
    big = load_font(290)
    sub = load_font(95)
    micro = load_font(54)

    # 중앙 한국사 (살짝 위쪽)
    center_text(draw, "한국사", 290, big, WHITE, size)
    center_text(draw, "기출 문제", 660, sub, ACCENT, size)
    center_text(draw, "능력검정시험", 820, micro, SUB, size)

    out = img.filter(ImageFilter.SMOOTH)
    out.save(OUT_DIR / "logo.png", optimize=True)
    print(f"✓ {OUT_DIR / 'logo.png'} (1024x1024)")


def make_thumbnail():
    w, h = 1920, 1080
    img = make_gradient_bg(w, h)
    draw = ImageDraw.Draw(img)

    # 노란 상단 띠
    band_h = 22
    draw.rectangle([(0, 0), (w, band_h)], fill=ACCENT)

    huge = load_font(220)
    big = load_font(120)
    sub = load_font(64)

    # 중앙 정렬 메인 카피
    center_text(draw, "한국사능력검정시험", 280, huge, WHITE, w)
    center_text(draw, "최신 기출 문제집", 570, big, ACCENT, w)
    center_text(draw, "심화·기본 회차별 풀이 · 오답 노트 · 실전 모의고사", 760, sub, SUB, w)

    # 하단 작은 캡션
    tiny = load_font(40)
    center_text(draw, "출처 · 국사편찬위원회", 920, tiny, SUB, w)

    img.save(OUT_DIR / "thumbnail.png", optimize=True)
    print(f"✓ {OUT_DIR / 'thumbnail.png'} (1920x1080)")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    make_logo()
    make_thumbnail()


if __name__ == "__main__":
    main()
