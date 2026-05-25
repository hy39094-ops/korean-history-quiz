"""
한국사능력검정시험 PDF 파싱 스크립트

기능
- pdfs/raw/ 폴더의 모든 PDF를 한글 파일명에서 (round, level, type) 자동 추출
- 기본/심화 모두 처리
- 텍스트 추출 가능한 문제지: 문항·선지·정답 추출 + 자료 이미지가 필요한 문항은 영역을 PNG로 저장
- 텍스트 추출 불가(이미지 PDF): 답지만 처리, 문항은 비움
- 출력
  - src/data/round-{N}-{level}.json
  - public/images/round-{N}-{level}/q-{NN}.jpg

사용: python3 scripts/parse_pdf.py
"""

import json
import re
import unicodedata
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pdfplumber
import pypdfium2 as pdfium

CIRCLE_MAP = {"①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5}
CIRCLES = "①②③④⑤"
IMAGE_HINTS = [
    "사진", "지도", "그림", "도표", "유물", "유적", "탑", "비석",
    "초상", "조각", "회화", "표지", "포스터", "엽서", "기념물",
    "검색창", "화면", "다음 자료", "위 자료", "위의 자료",
    "다음 자료에", "다음 인물", "(가)", "(나)", "(다)",
]

# 렌더링 설정
RENDER_SCALE = 1.5  # pdf 1pt → 1.5px
JPEG_QUALITY = 80


def parse_filename(name: str) -> Optional[Tuple[int, str, str]]:
    """파일명에서 (round, level, type) 추출. macOS는 NFD라 NFC 정규화 필수."""
    name = unicodedata.normalize("NFC", name)
    m = re.search(r"(\d{2,3})\s*회", name)
    if not m:
        return None
    round_num = int(m.group(1))

    if "기본" in name:
        level = "basic"
    elif "심화" in name:
        level = "advanced"
    else:
        return None

    if "문제" in name:
        ftype = "questions"
    elif "답" in name or "정답" in name:
        ftype = "answers"
    else:
        return None

    return (round_num, level, ftype)


def discover_pdfs(raw_dir: Path) -> Dict[Tuple[int, str], Dict[str, Path]]:
    """{(round, level): {'questions': Path, 'answers': Path}}"""
    groups: Dict[Tuple[int, str], Dict[str, Path]] = {}
    for p in raw_dir.glob("*.pdf"):
        meta = parse_filename(p.name)
        if not meta:
            continue
        round_num, level, ftype = meta
        key = (round_num, level)
        groups.setdefault(key, {})[ftype] = p
    return groups


def parse_answer_key(pdf_path: Path) -> Dict[int, Dict]:
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    matches = re.findall(r"(\d+)\s+([①②③④⑤])\s+(\d)", text)
    out = {}
    for num, circle, pts in matches:
        n = int(num)
        if 1 <= n <= 50:
            out[n] = {"answer": CIRCLE_MAP[circle], "points": int(pts)}
    return out


def detect_choice_count(answers: Dict[int, Dict]) -> int:
    """답지의 정답 분포로 4지선다인지 5지선다인지 판단"""
    max_answer = max((v["answer"] for v in answers.values()), default=4)
    return 5 if max_answer == 5 else 4


def find_question_positions(
    pdf_path: Path,
) -> Tuple[Dict[int, Dict], List[Tuple[int, str, str]]]:
    """
    문제지에서 각 문항의 (page_index, column, y_top) 위치 찾기.

    Returns:
        positions: {q_num: {page, column, y_top, y_bottom, column_box}}
        column_texts: [(page_index, column, text)] - 텍스트 추출 결과
    """
    positions: Dict[int, Dict] = {}
    column_texts: List[Tuple[int, str, str]] = []

    # ①가 컬럼별로 어디에 나오는지도 같이 수집
    circle_positions: Dict[Tuple[int, str], List[float]] = {}

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            w, h = page.width, page.height
            for col, (x0, x1) in [("L", (0, w * 0.5)), ("R", (w * 0.5, w))]:
                col_box = (x0, h * 0.04, x1, h * 0.96)
                col_crop = page.crop(col_box)
                col_text = col_crop.extract_text() or ""
                column_texts.append((page_idx, col, col_text))

                # 문항 시작 위치 + ① 위치 동시에 추출
                words = col_crop.extract_words(keep_blank_chars=False)
                circles_in_col: List[float] = []
                for w_idx, word in enumerate(words):
                    text = word["text"]
                    # ① 검출 (선지 시작점)
                    if "①" in text:
                        circles_in_col.append(float(word["top"]))
                        continue

                    m = re.match(r"^(\d{1,2})\.$", text)
                    if not m:
                        continue
                    n = int(m.group(1))
                    if not 1 <= n <= 50:
                        continue
                    is_line_start = True
                    if w_idx > 0:
                        prev = words[w_idx - 1]
                        if abs(prev["top"] - word["top"]) < 5 and prev["x1"] < word["x0"]:
                            is_line_start = False
                    if not is_line_start:
                        continue

                    if n not in positions or word["top"] < positions[n].get("y_top", 1e9):
                        positions[n] = {
                            "page": page_idx,
                            "column": col,
                            "y_top": float(word["top"]),
                            "column_box": col_box,
                        }

                circle_positions[(page_idx, col)] = sorted(circles_in_col)

    # 각 문항의 y_bottom = 같은 column에서 다음 문항의 y_top, 또는 column 끝
    # 그리고 y_choices = 그 문항 영역 안에서 처음 등장하는 ① 위치
    by_col: Dict[Tuple[int, str], List[Tuple[int, float]]] = {}
    for q_num, pos in positions.items():
        by_col.setdefault((pos["page"], pos["column"]), []).append((q_num, pos["y_top"]))
    for items in by_col.values():
        items.sort(key=lambda x: x[1])
    for (page_idx, col), items in by_col.items():
        col_box = positions[items[0][0]]["column_box"]
        col_circles = circle_positions.get((page_idx, col), [])
        for i, (q_num, _) in enumerate(items):
            if i + 1 < len(items):
                next_y = items[i + 1][1]
            else:
                next_y = col_box[3]
            positions[q_num]["y_bottom"] = next_y
            # 이 문항 범위 안에서 첫 ① 위치
            y_t = positions[q_num]["y_top"]
            choice_y = next((c for c in col_circles if y_t < c < next_y), None)
            positions[q_num]["y_choices"] = choice_y

    return positions, column_texts


def split_questions(text: str) -> Dict[int, str]:
    out = {}
    lines = text.split("\n")
    current_num = None
    buf: List[str] = []
    for line in lines:
        m = re.match(r"^\s*(\d{1,2})\.\s", line)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 50:
                if current_num is not None:
                    out[current_num] = "\n".join(buf).strip()
                current_num = n
                buf = [line]
                continue
        if current_num is not None:
            buf.append(line)
    if current_num is not None and buf:
        out[current_num] = "\n".join(buf).strip()
    return out


def parse_question_block(block: str, choice_count: int = 5) -> Optional[Dict]:
    m_pts = re.search(r"\[(\d)\s*점\]", block)
    points = int(m_pts.group(1)) if m_pts else None

    target = CIRCLES[:choice_count]
    positions = []
    for c in target:
        idx = block.find(c)
        if idx == -1:
            return None
        positions.append((idx, c))
    positions.sort()
    if [c for _, c in positions] != list(target):
        return None

    first_choice_pos = positions[0][0]
    question_part = block[:first_choice_pos]
    question_part = re.sub(r"^\s*\d{1,2}\.\s*", "", question_part, count=1)
    question_part = re.sub(r"\[\d\s*점\]", "", question_part)
    question = re.sub(r"\s+", " ", question_part).strip()

    choices = []
    for i, (pos, _) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < choice_count else len(block)
        choice_text = block[pos + 1 : end]
        choice_text = re.sub(r"\s+", " ", choice_text).strip()
        choices.append(choice_text)

    if not question or any(not c for c in choices):
        return None

    return {"question": question, "choices": choices, "points": points}


def detect_image_dependency(question_text: str) -> bool:
    return any(hint in question_text for hint in IMAGE_HINTS)


def render_question_image(
    pdf_path: Path,
    page_idx: int,
    column_box: Tuple[float, float, float, float],
    y_top: float,
    y_bottom: float,
    output_path: Path,
) -> bool:
    """문항 영역을 JPEG로 저장. 성공시 True."""
    try:
        pdf = pdfium.PdfDocument(str(pdf_path))
        page = pdf[page_idx]
        page_w, page_h = page.get_size()
        pil = page.render(scale=RENDER_SCALE).to_pil()
        img_w, img_h = pil.size
        sx = img_w / page_w
        sy = img_h / page_h

        x0, _, x1, _ = column_box
        # 문항 영역을 약간 여유있게 (위 4pt, 아래 2pt)
        crop_top = max(0, (y_top - 4) * sy)
        crop_bottom = min(img_h, (y_bottom - 2) * sy)
        if crop_bottom - crop_top < 30:  # 너무 작으면 skip
            return False
        cropped = pil.crop((int(x0 * sx), int(crop_top), int(x1 * sx), int(crop_bottom)))
        # 흰 여백 트리밍 — 좌우는 column box로 충분하므로 그대로
        cropped.save(output_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
        return True
    except Exception as e:
        print(f"  render fail: page={page_idx} {y_top}-{y_bottom}: {e}")
        return False


def is_image_only_pdf(pdf_path: Path) -> bool:
    """PDF가 텍스트 추출 불가능한 이미지 전용인지 확인"""
    with pdfplumber.open(pdf_path) as pdf:
        total = sum(len(p.extract_text() or "") for p in pdf.pages)
    return total < 100


def render_full_page(pdf_path: Path, page_idx: int, output_path: Path) -> bool:
    """페이지 전체를 JPEG로 저장"""
    try:
        pdf = pdfium.PdfDocument(str(pdf_path))
        page = pdf[page_idx]
        pil = page.render(scale=RENDER_SCALE).to_pil()
        pil.save(output_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
        return True
    except Exception as e:
        print(f"  full-page render fail: page={page_idx}: {e}")
        return False


def render_page_quadrant(
    pdf_path: Path, page_idx: int, quadrant: str, output_path: Path
) -> bool:
    """페이지를 4분할(TL/BL/TR/BR) 중 하나로 잘라 저장.
    첫 페이지는 상단 제목 배너가 있어 약 18%까지 자르고, 나머지를 4분할.
    """
    try:
        pdf = pdfium.PdfDocument(str(pdf_path))
        page = pdf[page_idx]
        pil = page.render(scale=RENDER_SCALE).to_pil()
        w, h = pil.size
        # 첫 페이지(인덱스 0)는 상단 배너가 있어 18%까지 자름
        top_margin = int(h * 0.18) if page_idx == 0 else int(h * 0.04)
        bot_margin = int(h * 0.96)
        mid_y = (top_margin + bot_margin) // 2
        mid_x = w // 2
        box = {
            "TL": (0, top_margin, mid_x, mid_y),
            "BL": (0, mid_y, mid_x, bot_margin),
            "TR": (mid_x, top_margin, w, mid_y),
            "BR": (mid_x, mid_y, w, bot_margin),
        }[quadrant]
        pil.crop(box).save(output_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
        return True
    except Exception as e:
        print(f"  quadrant render fail: page={page_idx} {quadrant}: {e}")
        return False


def parse_image_only_round(
    round_num: int,
    level: str,
    q_pdf: Path,
    a_pdf: Path,
    images_dir: Path,
    manual_crops_dir: Optional[Path] = None,
) -> Dict:
    """텍스트 추출 불가한 PDF: 페이지를 4분할(TL/BL/TR/BR) 해서 한 문제씩 보이도록.
    한국 시험지의 2단 레이아웃 + 보통 페이지당 4문항을 가정.
    한 페이지에 5문항이 있으면 일부는 약간 잘릴 수 있음 — manual_crops_dir로 수동 크롭 우선.
    """
    answers = parse_answer_key(a_pdf)
    choice_count = detect_choice_count(answers)
    images_dir.mkdir(parents=True, exist_ok=True)

    with pdfplumber.open(q_pdf) as pdf:
        num_pages = len(pdf.pages)

    # 50문항을 num_pages 페이지에 분배. 페이지당 4문항 기준, 잔여는 앞쪽 페이지에 +1
    base = 50 // num_pages  # 4
    extra = 50 - base * num_pages  # 2 (pages with 1 extra)
    # 페이지 별 문항 수: 앞 extra 개 페이지가 base+1, 나머지가 base
    per_page_counts = [base + 1 if i < extra else base for i in range(num_pages)]

    # 읽기 순서: TL(좌상) → BL(좌하) → TR(우상) → BR(우하) ... 5번째는 (페이지 중앙)
    # 4문제 페이지: TL, BL, TR, BR
    # 5문제 페이지: TL, BL, TR, BR, FULL(전체) — 5번째는 페이지 전체로
    QUADRANT_ORDER_4 = ["TL", "BL", "TR", "BR"]
    QUADRANT_ORDER_5 = ["TL", "BL", "TR", "BR", "FULL"]

    questions = []
    image_rendered = 0
    rendered_full_pages: Dict[int, str] = {}

    q_num = 1
    for page_idx in range(num_pages):
        count = per_page_counts[page_idx]
        quadrants = QUADRANT_ORDER_5 if count == 5 else QUADRANT_ORDER_4

        for qi, quad in enumerate(quadrants[:count]):
            if q_num > 50:
                break

            # 1) 수동 크롭 파일이 있으면 우선 사용 (.jpg, .jpeg, .png 모두 지원)
            manual_url = None
            if manual_crops_dir is not None:
                for ext in (".jpg", ".jpeg", ".png"):
                    manual_path = manual_crops_dir / f"q-{q_num:02d}{ext}"
                    if manual_path.exists():
                        target = images_dir / f"q-{q_num:02d}{ext}"
                        target.write_bytes(manual_path.read_bytes())
                        manual_url = f"/images/round-{round_num}-{level}/q-{q_num:02d}{ext}"
                        image_rendered += 1
                        break

            # 2) 수동 크롭 없으면 자동 4분할 크롭
            image_url = manual_url
            if not image_url:
                if quad == "FULL":
                    # 5번째 문제는 페이지 전체
                    if page_idx not in rendered_full_pages:
                        full_name = f"page-{page_idx + 1:02d}.jpg"
                        full_path = images_dir / full_name
                        if render_full_page(q_pdf, page_idx, full_path):
                            rendered_full_pages[page_idx] = (
                                f"/images/round-{round_num}-{level}/{full_name}"
                            )
                    image_url = rendered_full_pages.get(page_idx)
                else:
                    crop_name = f"q-{q_num:02d}.jpg"
                    crop_path = images_dir / crop_name
                    if render_page_quadrant(q_pdf, page_idx, quad, crop_path):
                        image_url = f"/images/round-{round_num}-{level}/{crop_name}"
                        image_rendered += 1

            ans_info = answers.get(q_num, {})
            questions.append({
                "id": f"R{round_num}-{level[0].upper()}-Q{q_num:02d}",
                "round": round_num,
                "level": level,
                "number": q_num,
                "question": "",
                "choices": [""] * choice_count,
                "answer": ans_info.get("answer"),
                "points": ans_info.get("points"),
                "has_image": True,
                "image_url": image_url,
                "image_is_full_page": quad == "FULL",
            })
            q_num += 1

    return {
        "round": round_num,
        "level": level,
        "choice_count": choice_count,
        "total": len(questions),
        "parse_failed_numbers": [],
        "image_dependent_count": 50,
        "image_rendered_count": image_rendered,
        "image_only_pdf": True,
        "questions": questions,
    }


def find_manual_crop(manual_crops_dir: Optional[Path], q_num: int) -> Optional[Path]:
    """수동 크롭 파일이 있으면 경로 반환 (.jpg/.jpeg/.png 모두 지원)"""
    if manual_crops_dir is None or not manual_crops_dir.is_dir():
        return None
    for ext in (".jpg", ".jpeg", ".png"):
        p = manual_crops_dir / f"q-{q_num:02d}{ext}"
        if p.exists():
            return p
    return None


def parse_round_level(
    round_num: int,
    level: str,
    q_pdf: Path,
    a_pdf: Path,
    images_dir: Path,
    manual_crops_dir: Optional[Path] = None,
) -> Dict:
    if is_image_only_pdf(q_pdf):
        used_manual = manual_crops_dir is not None and manual_crops_dir.is_dir()
        print(f"  → 이미지 PDF 감지, 4분할 크롭{' (수동크롭 우선 사용)' if used_manual else ''}")
        return parse_image_only_round(
            round_num, level, q_pdf, a_pdf, images_dir, manual_crops_dir
        )

    answers = parse_answer_key(a_pdf)
    choice_count = detect_choice_count(answers)
    positions, column_texts = find_question_positions(q_pdf)

    # 모든 컬럼 텍스트에서 문항 블록 추출
    all_blocks: Dict[int, str] = {}
    for _, _, text in column_texts:
        for n, b in split_questions(text).items():
            if n not in all_blocks or len(b) > len(all_blocks[n]):
                all_blocks[n] = b

    images_dir.mkdir(parents=True, exist_ok=True)
    questions = []
    parse_fail = []
    image_rendered = 0

    for n in range(1, 51):
        block = all_blocks.get(n)
        parsed = parse_question_block(block, choice_count) if block else None
        ans_info = answers.get(n, {})
        manual = find_manual_crop(manual_crops_dir, n)

        # 텍스트 파싱 실패 & 수동 크롭도 없으면 skip
        if not parsed and manual is None:
            parse_fail.append(n)
            continue

        image_url = None
        # 1) 수동 크롭 우선 (선지 포함된 원본 그대로)
        if manual is not None:
            target = images_dir / f"q-{n:02d}{manual.suffix}"
            target.write_bytes(manual.read_bytes())
            image_url = f"/images/round-{round_num}-{level}/q-{n:02d}{manual.suffix}"
            image_rendered += 1
        # 2) 없으면 자동 렌더링 (문항 전체 — 선지 포함)
        elif parsed and n in positions:
            pos = positions[n]
            out_name = f"q-{n:02d}.jpg"
            out_path = images_dir / out_name
            ok = render_question_image(
                q_pdf,
                pos["page"],
                pos["column_box"],
                pos["y_top"],
                pos["y_bottom"],
                out_path,
            )
            if ok:
                image_url = f"/images/round-{round_num}-{level}/{out_name}"
                image_rendered += 1

        # 텍스트 파싱 실패했지만 수동 크롭으로 살리는 경우 — 빈 텍스트 + 답지 기반
        if not parsed:
            parse_fail.append(n)
            questions.append({
                "id": f"R{round_num}-{level[0].upper()}-Q{n:02d}",
                "round": round_num,
                "level": level,
                "number": n,
                "question": "",
                "choices": [""] * choice_count,
                "answer": ans_info.get("answer"),
                "points": ans_info.get("points"),
                "has_image": True,
                "image_url": image_url,
                "image_is_full_page": False,
            })
            continue

        has_image = detect_image_dependency(parsed["question"])
        questions.append({
            "id": f"R{round_num}-{level[0].upper()}-Q{n:02d}",
            "round": round_num,
            "level": level,
            "number": n,
            "question": parsed["question"],
            "choices": parsed["choices"],
            "answer": ans_info.get("answer"),
            "points": parsed["points"] or ans_info.get("points"),
            "has_image": has_image,
            "image_url": image_url,
            "image_is_full_page": False,
        })

    return {
        "round": round_num,
        "level": level,
        "choice_count": choice_count,
        "total": len(questions),
        "parse_failed_numbers": parse_fail,
        "image_dependent_count": sum(1 for q in questions if q["has_image"]),
        "image_rendered_count": image_rendered,
        "image_only_pdf": False,
        "questions": questions,
    }


def main():
    project = Path(__file__).resolve().parent.parent
    raw_dir = project / "pdfs" / "raw"
    manual_crops_root = project / "pdfs" / "manual-crops"
    data_dir = project / "src" / "data"
    public_images = project / "public" / "images"

    data_dir.mkdir(parents=True, exist_ok=True)
    public_images.mkdir(parents=True, exist_ok=True)

    groups = discover_pdfs(raw_dir)
    print(f"발견된 PDF 그룹: {len(groups)}")
    for k, v in sorted(groups.items()):
        print(f"  {k[0]}회 {k[1]:<8} {'문제지✓' if 'questions' in v else '문제지✗'} {'답지✓' if 'answers' in v else '답지✗'}")

    summary = []
    for (round_num, level), files in sorted(groups.items()):
        q_pdf = files.get("questions")
        a_pdf = files.get("answers")
        if not a_pdf:
            print(f"\n[{round_num}회 {level}] 답지 없음 — 건너뜀")
            continue
        if not q_pdf:
            print(f"\n[{round_num}회 {level}] 문제지 없음 — 건너뜀")
            continue

        images_dir = public_images / f"round-{round_num}-{level}"
        manual_crops_dir = manual_crops_root / f"{round_num}-{level}"
        print(f"\n[{round_num}회 {level}] 파싱 중...")
        result = parse_round_level(
            round_num, level, q_pdf, a_pdf, images_dir, manual_crops_dir
        )
        out_path = data_dir / f"round-{round_num}-{level}.json"
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summary.append({
            "round": round_num,
            "level": level,
            "parsed": result["total"],
            "failed": len(result["parse_failed_numbers"]),
            "image_dep": result["image_dependent_count"],
            "image_rendered": result["image_rendered_count"],
        })
        print(
            f"  → {result['total']}/50 문항, 자료 의존 {result['image_dependent_count']}, "
            f"이미지 추출 {result['image_rendered_count']}, 실패 {len(result['parse_failed_numbers'])}"
        )

    print("\n=== 전체 요약 ===")
    for s in summary:
        print(json.dumps(s, ensure_ascii=False))


if __name__ == "__main__":
    main()
