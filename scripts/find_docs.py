#!/usr/bin/env python3
"""로컬 PC에서 마케팅 자료(브랜드 가이드·로고·상품 소개서·가격표·기존 광고 소재·
콘텐츠 캘린더·GA 리포트)를 자동으로 찾아 목록으로 보여준다.

"브랜드 자료가 없다"는 사용자는 거의 없다 — 대개 바탕화면·문서·다운로드 어딘가에 있다.
기본 위치와 브랜드 자산 폴더(config `imagefactory.brand_assets_dir`)를 훑어 후보를
카테고리별로 정리한다. **읽기 전용**: 파일 내용을 열거나 어디로 보내지 않고 경로·크기·
수정일만 나열한다(반영은 context 스킬이 사용자가 고른 뒤에 한다).

  python3 scripts/find_docs.py                   # 기본 위치 스캔, 사람이 읽는 표
  python3 scripts/find_docs.py --json            # 기계용 JSON(스킬이 파싱)
  python3 scripts/find_docs.py --root ~/브랜드   # 추가 위치도 스캔
  python3 scripts/find_docs.py --days 365        # 최근 N일 안에 수정된 것만(기본 1095=3년)
"""
import argparse
import datetime
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_config  # noqa: E402

# 이미지(로고·광고 소재·썸네일) / 영상(숏폼 소재) / 문서(가이드·소개서·가격표·리포트·캘린더).
IMG_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".gif", ".svg", ".ai", ".psd"}
VIDEO_EXTS = {".mp4", ".mov"}
DOC_EXTS = {
    ".pdf", ".ppt", ".pptx", ".key", ".doc", ".docx", ".hwp", ".hwpx",
    ".xls", ".xlsx", ".xlsm", ".csv", ".numbers", ".pages", ".md",
}
EXTS = IMG_EXTS | VIDEO_EXTS | DOC_EXTS

# 파일명 키워드 → 카테고리(위에서부터 먼저 잡히는 순서로 판정). 소문자 비교.
# 3글자 이하 영문 키워드(ci·bi·ad·kv…)는 **낱말 경계**로만 잡는다 — 부분일치로 두면
# 'recipients'·'agencies' 같은 무관한 파일이 브랜드 자료로 잡혀 목록이 쓰레기가 된다.
CATEGORY_KEYWORDS = [
    ("brand", ["브랜드", "brand", "로고", "logo", "ci", "bi", "가이드라인", "guideline",
               "style guide", "styleguide", "브랜드북", "brandbook", "톤앤매너", "tone",
               "폰트", "font", "컬러"]),
    ("product", ["상품", "제품", "소개서", "회사소개", "product", "brochure", "브로셔",
                 "카탈로그", "catalog", "one pager", "onepager", "deck", "소개자료",
                 "상세페이지", "상세 페이지", "detail page"]),
    ("price", ["가격", "price", "단가", "요금", "pricing", "견적", "quote", "프로모션",
               "promotion", "할인", "쿠폰", "coupon", "이벤트가"]),
    ("creative", ["광고", "소재", "배너", "banner", "creative", "ad", "ads", "썸네일",
                  "thumbnail", "카드뉴스", "카드 뉴스", "릴스", "reels", "숏폼", "shorts",
                  "ugc", "상세컷", "누끼", "키비주얼", "key visual", "kv"]),
    ("calendar", ["캘린더", "calendar", "발행", "게시일정", "게시 일정", "콘텐츠 일정",
                  "editorial", "콘텐츠계획", "콘텐츠 계획", "content plan", "포스팅"]),
    ("report", ["ga4", "ga", "애널리틱스", "analytics", "리포트", "report", "성과",
                "performance", "roas", "인사이트", "insight", "대시보드", "dashboard",
                "광고비", "지표", "kpi", "서치콘솔", "search console"]),
    ("audience", ["고객", "customer", "타깃", "타겟", "target", "페르소나", "persona",
                  "설문", "survey", "voc", "리뷰", "review", "후기", "인터뷰"]),
]
# (카테고리, 부분일치 키워드들, 낱말경계 정규식들) — 스캔 루프에서 매번 컴파일하지 않도록 미리 준비.
CATEGORY_MATCHERS = [
    (cat,
     [k for k in kws if not (k.isascii() and len(k) <= 3)],
     [re.compile(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])")
      for k in kws if k.isascii() and len(k) <= 3])
    for cat, kws in CATEGORY_KEYWORDS
]
CATEGORY_LABEL = {
    "brand": "🎨 브랜드 가이드·로고",
    "product": "📦 상품 소개서·상세",
    "price": "💰 가격표·프로모션",
    "creative": "🖼️ 기존 광고 소재",
    "calendar": "🗓️ 콘텐츠 캘린더",
    "report": "📊 GA·광고 성과 리포트",
    "audience": "🗣️ 고객 목소리·타깃 자료",
}
CATEGORY_ORDER = ["brand", "product", "price", "creative", "calendar", "report", "audience"]

# 스캔에서 통째로 제외할 디렉토리 이름(시스템/캐시/코드 저장소 등).
SKIP_DIRS = {
    "library", "node_modules", ".git", "__pycache__", ".cache", "caches",
    ".npm", ".venv", "venv", "env", ".Trash", "trash", ".gradle", ".m2",
    "applications", "movies", "music", "public", "dist", "build", ".next", "vendor",
    ".marketing-copilot", ".sales-copilot", ".business-copilot", ".pm-copilot",
}
MAX_HITS = 200          # 후보 상한(너무 많으면 무의미).
MAX_DEPTH = 6           # 루트 기준 최대 탐색 깊이.
TIME_BUDGET_SEC = 12    # 전체 스캔 시간 예산(넘으면 조기 종료).


def categorize(name_lower, ext, in_brand_assets):
    """파일명·확장자로 카테고리 판정. 해당 없으면 None(스킵)."""
    for cat, subs, regexes in CATEGORY_MATCHERS:
        if any(kw in name_lower for kw in subs) or any(r.search(name_lower) for r in regexes):
            return cat
    # 브랜드 자산 폴더 안의 이미지·영상은 이름에 키워드가 없어도 소재 후보로 본다.
    if in_brand_assets and ext in (IMG_EXTS | VIDEO_EXTS):
        return "creative"
    return None


def human_size(n):
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}GB"


def brand_assets_path():
    """config `imagefactory.brand_assets_dir` 폴더(설정돼 있고 실제로 있으면). 없으면 ''."""
    try:
        p = load_config(soft=True).get("imagefactory", {}).get("brand_assets_dir", "")
    except Exception:
        return ""
    p = os.path.abspath(os.path.expanduser(p)) if p else ""
    return p if p and os.path.isdir(p) else ""


def default_roots(brand_assets):
    home = os.path.expanduser("~")
    roots = [os.path.join(home, d) for d in ("Desktop", "Documents", "Downloads")]
    # 한글 macOS는 데스크탑/문서가 영문 심볼릭이라 위로 커버됨.
    roots = [r for r in roots if os.path.isdir(r)]
    if brand_assets and brand_assets not in roots:
        roots.append(brand_assets)
    return roots


def scan(roots, cutoff_ts, brand_assets):
    hits = []
    start = time.time()
    for root in roots:
        root = os.path.abspath(os.path.expanduser(root))
        base_depth = root.rstrip(os.sep).count(os.sep)
        for dirpath, dirnames, filenames in os.walk(root):
            if time.time() - start > TIME_BUDGET_SEC:
                return hits, True
            depth = dirpath.rstrip(os.sep).count(os.sep) - base_depth
            if depth >= MAX_DEPTH:
                dirnames[:] = []
                continue
            # 숨김/제외 디렉토리 프루닝
            dirnames[:] = [d for d in dirnames
                           if not d.startswith(".") and d.lower() not in SKIP_DIRS]
            in_assets = bool(brand_assets) and (dirpath == brand_assets
                                                or dirpath.startswith(brand_assets + os.sep))
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in EXTS:
                    continue
                cat = categorize(fn.lower(), ext, in_assets)
                if not cat:
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                if st.st_mtime < cutoff_ts:
                    continue
                hits.append({
                    "path": full,
                    "name": fn,
                    "category": cat,
                    "size": st.st_size,
                    "mtime": st.st_mtime,
                })
                if len(hits) >= MAX_HITS:
                    return hits, True
    return hits, False


def main():
    ap = argparse.ArgumentParser(
        description="로컬 마케팅 자료 탐색(브랜드 가이드·상품 소개서·가격표·광고 소재·캘린더·리포트)")
    ap.add_argument("--root", action="append", default=[], help="추가 스캔 위치(여러 번 가능)")
    ap.add_argument("--days", type=int, default=1095, help="최근 N일 내 수정된 것만(기본 3년)")
    ap.add_argument("--json", action="store_true", help="기계용 JSON 출력")
    args = ap.parse_args()

    brand_assets = brand_assets_path()
    roots = default_roots(brand_assets) + args.root
    if not roots:
        print("스캔할 위치가 없습니다. --root 로 폴더를 지정하세요.")
        return
    cutoff_ts = time.time() - args.days * 86400

    hits, truncated = scan(roots, cutoff_ts, brand_assets)
    for h in hits:
        h["mtime_str"] = datetime.date.fromtimestamp(h["mtime"]).isoformat()
        h["size_str"] = human_size(h["size"])
    hits.sort(key=lambda h: (CATEGORY_ORDER.index(h["category"]), -h["mtime"]))

    if args.json:
        print(json.dumps({"roots": [os.path.expanduser(r) for r in roots],
                          "brand_assets_dir": brand_assets,
                          "count": len(hits), "truncated": truncated,
                          "hits": hits}, ensure_ascii=False, indent=2))
        return

    print("=== 로컬에서 찾은 마케팅 자료 후보 ===")
    print(f"(스캔 위치: {', '.join(os.path.expanduser(r) for r in roots)} · 최근 {args.days}일)\n")
    if not hits:
        print("자료를 못 찾았어요. 다른 폴더에 있다면 클로드에게 위치를 알려주거나,")
        print("  python3 scripts/find_docs.py --root <폴더경로>  로 다시 찾아보세요.")
        print("브랜드 자산 폴더를 지정해두면 다음부터 자동으로 봅니다:")
        print("  python3 scripts/set_config.py imagefactory.brand_assets_dir=<경로>")
        return

    by_cat = {}
    for h in hits:
        by_cat.setdefault(h["category"], []).append(h)
    for cat in CATEGORY_ORDER:
        rows = by_cat.get(cat)
        if not rows:
            continue
        print(f"{CATEGORY_LABEL[cat]}  ({len(rows)}개)")
        for h in rows[:12]:
            print(f"  · {h['name']}  —  {h['size_str']}, 수정 {h['mtime_str']}")
            print(f"      {h['path']}")
        if len(rows) > 12:
            print(f"  … 외 {len(rows)-12}개")
        print()
    if truncated:
        print("(후보가 많아 일부만 표시 — 필요하면 --days 를 줄여 좁히세요.)")
    print("다음: 클로드에게 '마케팅 컨텍스트 채우자'(context)라고 하면 위에서 고른 자료로")
    print("  brand·products·audiences·tone·claims 를 채웁니다. 특히 가격표·리포트는 마진율과")
    print("  실제 CAC의 근거가 되고, 기존 광고 소재는 승자 메시지 추출의 재료입니다.")
    print("  (내용은 이 스캔에서 열지 않았습니다 — 경로만 나열.)")


if __name__ == "__main__":
    main()
