#!/usr/bin/env python3
"""PostToolUse(Write|Edit) 훅 — 마케팅 작업물 저장을 활동 원장에 남기고,
저장된 파일이 **게시용 콘텐츠 초안**으로 보이면 게시 게이트를 리마인드한다(세션당 1회).
함께 **메시지 ID 귀속**(성과는 콘텐츠가 아니라 메시지에 귀속)을 확인시킨다.
마케팅 산출물이 아니면 조용히 종료.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

# 마케팅 작업물로 볼 파일명 키워드 (활동 원장 기록용)
MARKETINGLIKE = (
    "콘텐츠", "content", "카드뉴스", "릴스", "reels", "숏폼", "대본", "script", "캡션", "caption",
    "블로그", "blog", "포스트", "post", "인스타", "instagram", "틱톡", "tiktok", "댓글", "comment",
    "커뮤니티", "광고", "ads", "캠페인", "campaign", "소재", "asset", "배너", "banner",
    "브리프", "brief", "발주", "카피", "copy", "캘린더", "calendar", "큐", "queue",
    "브리핑", "신호", "signal", "기회", "opportunity", "메시지", "message", "성과", "마케팅", "marketing",
)

# 게시용 초안으로 볼 파일명 키워드 (게시 게이트 리마인드용)
PUBLISHLIKE = (
    "콘텐츠", "content", "카드뉴스", "릴스", "reels", "숏폼", "대본", "script", "캡션", "caption",
    "블로그", "blog", "포스트", "post", "인스타", "instagram", "틱톡", "tiktok", "댓글", "comment",
    "카피", "copy", "초안", "draft",
)

MSG_ID = re.compile(r"MSG-\d{8}-\d+")
CONTENT_MARKERS = ("해시태그", "훅:", "후킹", "cta", "캡션", "슬라이드", "본문:", "제목:",
                   "썸네일", "대본", "인트로", "아웃트로", "메타 디스크립션", "첫 장", "3초")


def is_marketing_artifact(path):
    if not path:
        return False
    p = path.lower()
    if "/.marketing-copilot/" in p:  # 플러그인이 다루는 데이터 폴더
        return True
    if not (p.endswith(".md") or p.endswith(".txt") or p.endswith(".html")):
        return False
    return any(k in os.path.basename(p) for k in MARKETINGLIKE)


def looks_publishable(path, content):
    """경로·내용으로 '대외 게시용 초안'인지 판별. 확신 없으면 False(소음 방지)."""
    base = os.path.basename((path or "").lower())
    if any(k in base for k in PUBLISHLIKE):
        return True
    c = (content or "")[:4000].lower()
    if not c:
        return False
    return sum(1 for m in CONTENT_MARKERS if m in c) >= 2


def gate_seen(session):
    """게시 게이트 리마인드는 세션당 1회만. 이미 봤으면 True."""
    p = os.path.join(common.DATA_DIR, "_gate_seen.json")
    d = {}
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            d = {}
    if d.get(session):
        return True
    try:
        os.makedirs(common.DATA_DIR, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump({session: True}, f)  # 현재 세션만 유지
    except Exception:
        pass
    return False


def main():
    p = common.proactive_cfg()
    if p is None or p.get("review_on_save", True) is False:
        return
    data = common.read_hook_input()
    ti = data.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("path") or ""
    content = ti.get("content") or ti.get("new_string") or ""
    if not is_marketing_artifact(path):
        return

    common.log_activity("작업물 저장", path)  # 세션 종료 워크로그·주간 회고의 원천

    if not looks_publishable(path, content):
        return
    session = data.get("session_id") or "-"
    if gate_seen(session):
        return

    name = os.path.basename(path)
    attrib = ("메시지 ID가 안 보인다 — **성과는 콘텐츠가 아니라 메시지에 귀속**한다. "
              "[[messages]] 원장에서 각도를 고르거나 새로 등록하고 content 레코드의 message_id에 "
              "박아라(귀속 없는 게시물은 성과가 쌓이지 않고 휘발된다)."
              if not MSG_ID.search(content or "")
              else "메시지 ID는 붙어 있다 — 게시 후 성과를 그 ID에 귀속시켜라.")

    common.emit_context(
        "PostToolUse",
        f"📣 마케터: 방금 저장한 **{name}** 은 게시용 초안으로 보인다. 게시 전 [[publish-policy]] "
        f"게이트 순서대로 — ①퀄리티 바 5항목(고유성·훅·플랫폼 네이티브·행동 유발·사실 검증), 미달이면 "
        f"게시가 아니라 **보강 큐** ②클레임 실증(context/claims.md 원장에 없는 수치·효능 주장은 '확인 "
        f"필요'로 반려) ③표시 의무(광고·협찬·경제적 이해관계, 커뮤니티는 3모드) ④브랜드 금지 표현·경쟁사 "
        f"비방 ⑤채널 정책 ⑥승인 모드(approval_mode). "
        f"측정 슬롯도 같이 — **UTM과 성과 기록 자리 없으면 게시하지 않는다.** {attrib} "
        f"**자동 게시는 하지 않는다(V1) — 초안까지가 플러그인, 게시는 사람.**",
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # 훅은 어떤 경우에도 세션을 방해하지 않는다
    sys.exit(0)
