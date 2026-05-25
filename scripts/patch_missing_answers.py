"""
JSON에서 answer가 null인 문항만 골라서, 같은 회차/level의 답지 PDF에서 정답을 뽑아 채워줌.
사용: python3 scripts/patch_missing_answers.py
"""

import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, Optional

import pdfplumber

CIRCLE_MAP = {"①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5}
RAW = Path(__file__).resolve().parents[1] / "pdfs" / "raw"
DATA = Path(__file__).resolve().parents[1] / "src" / "data"


def parse_answer_key(pdf_path: Path) -> Dict[int, Dict]:
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)

    # 형식 1: "1 ① 2" — 동그라미 숫자
    out: Dict[int, Dict] = {}
    for num, circle, pts in re.findall(r"(\d+)\s+([①②③④⑤])\s+(\d)", text):
        n = int(num)
        if 1 <= n <= 50:
            out[n] = {"answer": CIRCLE_MAP[circle], "points": int(pts)}
    if out:
        return out

    # 형식 2: "1 2 1" — 평문 숫자 (정답 1~5, 배점 1~3)
    # 행 단위로 보고 같은 행에서 (번호, 정답, 배점)이 1~50, 1~5, 1~3 범위에 들어가는 케이스만 채택
    for line in text.splitlines():
        tokens = line.split()
        nums = [int(t) for t in tokens if t.isdigit()]
        i = 0
        while i + 2 < len(nums):
            n, a, p = nums[i], nums[i + 1], nums[i + 2]
            if 1 <= n <= 50 and 1 <= a <= 5 and 1 <= p <= 3:
                out[n] = {"answer": a, "points": p}
                i += 3
            else:
                i += 1
    return out


def find_answer_pdf(round_n: int, level: str) -> Optional[Path]:
    kw = "기본" if level == "basic" else "심화"
    candidates = []
    for p in RAW.iterdir():
        name = unicodedata.normalize("NFC", p.name)
        if not name.endswith(".pdf"):
            continue
        if not re.search(rf"제?{round_n}\s*회", name):
            continue
        if kw not in name:
            continue
        if any(k in name for k in ("답지", "답표", "정답표", "정답지", "정답")):
            candidates.append(p)
    if not candidates:
        return None
    # 짧은 이름 우선
    candidates.sort(key=lambda p: len(p.name))
    return candidates[0]


def patch_round(json_path: Path):
    d = json.loads(json_path.read_text(encoding="utf-8"))
    null_qs = [q for q in d["questions"] if q.get("answer") is None]
    if not null_qs:
        return None
    pdf = find_answer_pdf(d["round"], d["level"])
    if pdf is None:
        return f"{json_path.name}: 답지 PDF 못 찾음"
    ans = parse_answer_key(pdf)
    filled = 0
    for q in null_qs:
        info = ans.get(q["number"])
        if info:
            q["answer"] = info["answer"]
            q["points"] = info["points"]
            filled += 1
    json_path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return f"{json_path.name}: {filled}/{len(null_qs)} 채움 (답지={pdf.name})"


def main():
    for p in sorted(DATA.glob("round-*.json")):
        result = patch_round(p)
        if result:
            print(result)


if __name__ == "__main__":
    main()
