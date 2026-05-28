"""
PWABuilder/PWA용 아이콘 생성 → public/ 에 출력.
assets-store/icon-512.png(스토어 아이콘) 기반으로 192/512/apple-touch/favicon/maskable 생성.
"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "assets-store", "icon-512.png")
PUB = os.path.join(ROOT, "public")
os.makedirs(PUB, exist_ok=True)

NAVY = (12, 24, 66)  # maskable 배경(아이콘 하단 톤)

base = Image.open(SRC).convert("RGB")

# any 아이콘 (꽉 찬 디자인)
base.save(os.path.join(PUB, "icon-512.png"), "PNG", optimize=True)
base.resize((192, 192), Image.LANCZOS).save(os.path.join(PUB, "icon-192.png"), "PNG", optimize=True)
base.resize((180, 180), Image.LANCZOS).save(os.path.join(PUB, "apple-touch-icon.png"), "PNG", optimize=True)
base.resize((48, 48), Image.LANCZOS).save(os.path.join(PUB, "favicon.png"), "PNG", optimize=True)

# maskable: 안전영역 확보를 위해 콘텐츠를 78%로 축소 후 남색 배경 중앙 배치
S = 512
inner = int(S * 0.78)
canvas = Image.new("RGB", (S, S), NAVY)
shrunk = base.resize((inner, inner), Image.LANCZOS)
off = (S - inner) // 2
canvas.paste(shrunk, (off, off))
canvas.save(os.path.join(PUB, "icon-maskable-512.png"), "PNG", optimize=True)

for n in ["icon-512.png", "icon-192.png", "apple-touch-icon.png", "favicon.png", "icon-maskable-512.png"]:
    print("saved: public/" + n)
