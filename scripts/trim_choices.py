"""이미지에서 선지(①②③④⑤) 영역을 잘라내고 문제 + 자료만 남기는 후처리.

문제는 보통:
[ 문제 텍스트 ]
[ 자료 (사진/지도/사료) ]
[ ① 선택지 1 ]
[ ② 선택지 2 ]
...

선지는 UI에 별도 버튼으로 보여주니 이미지에서 중복으로 보일 필요 없음.

전략:
1. OCR로 `①` 위치 찾기 (가장 아래에 있는 것 = 선지 영역 시작점)
2. 그 위쪽으로 이미지 크롭
3. 못 찾으면 원본 유지

사용: python3 scripts/trim_choices.py [--dry-run]
"""

import re
import sys
from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image

PROJECT = Path(__file__).resolve().parent.parent
IMAGES_ROOT = PROJECT / "public" / "images"

# 선지 마커들 — OCR이 다양하게 인식할 수 있음
CHOICE_PATTERNS = ["①", "1)", "①.", "(1)"]
# 좌측 마진 한계 — 선지는 보통 줄 맨 앞에 있음 (이미지 폭의 25% 이내)
MAX_LEFT_RATIO = 0.30


def find_choices_top(img: Image.Image) -> Optional[int]:
    """이미지에서 선지 영역이 시작하는 y 좌표 찾기."""
    w, h = img.size
    try:
        data = pytesseract.image_to_data(
            img, lang="kor+eng", output_type=pytesseract.Output.DICT
        )
    except Exception as e:
        print(f"  OCR fail: {e}")
        return None

    candidates = []
    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        if not text:
            continue
        conf_raw = data["conf"][i]
        try:
            conf = int(conf_raw)
        except (TypeError, ValueError):
            conf = -1
        if conf < 25:
            continue
        # `①` 또는 비슷한 패턴
        is_choice = False
        if "①" in text:
            is_choice = True
        elif re.match(r"^\(?1\)?[\s.,]?$", text):
            is_choice = True
        if not is_choice:
            continue
        # 좌측 마진 체크
        x = data["left"][i]
        if x > w * MAX_LEFT_RATIO:
            continue
        candidates.append({
            "y": data["top"][i],
            "x": x,
            "h": data["height"][i],
            "text": text,
            "conf": conf,
        })

    if not candidates:
        return None

    # 가장 아래쪽 ① = 선지 시작점
    candidates.sort(key=lambda c: c["y"], reverse=True)
    return candidates[0]["y"]


def trim_image(path: Path, dry_run: bool = False) -> str:
    img = Image.open(path)
    w, h = img.size
    y = find_choices_top(img)

    if y is None:
        return "no marker"
    if y < h * 0.25:
        return f"too high (y={y}, h={h})"
    if y > h * 0.95:
        return f"too low (y={y}, h={h})"

    # 위쪽 약간 여유 두고 자름
    crop_bottom = max(0, y - 6)
    cropped = img.crop((0, 0, w, crop_bottom))

    if not dry_run:
        # 원본 형식 유지 (.jpg or .png)
        if path.suffix.lower() in (".jpg", ".jpeg"):
            cropped.convert("RGB").save(path, "JPEG", quality=85, optimize=True)
        else:
            cropped.save(path, "PNG", optimize=True)

    return f"trimmed {h}→{crop_bottom}"


def main():
    dry_run = "--dry-run" in sys.argv

    folders = [
        d for d in IMAGES_ROOT.glob("round-*-*") if d.is_dir()
    ]
    print(f"폴더 {len(folders)}개 처리 시작 (dry_run={dry_run})")

    total = 0
    trimmed = 0
    for folder in sorted(folders):
        imgs = [p for p in folder.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
        if not imgs:
            continue
        print(f"\n[{folder.name}] {len(imgs)}장")
        for img_path in sorted(imgs):
            result = trim_image(img_path, dry_run)
            total += 1
            if result.startswith("trimmed"):
                trimmed += 1
            # 상태가 특이한 경우만 출력
            if not result.startswith("trimmed"):
                print(f"  {img_path.name}: {result}")

    print(f"\n=== 완료 ===")
    print(f"총 {total}장 중 {trimmed}장 잘라냄, {total - trimmed}장 변동 없음")


if __name__ == "__main__":
    main()
