#!/usr/bin/env python3
"""SessionEnd 훅 — ① 오늘 활동 원장을 마케팅 활동 로그 초안으로 정리(로컬, 사람이 검토·보완)
② **성과 기록 슬롯 없는 게시물·게시 예정물**을 파일로 남겨 다음 세션의 proactive가 첫마디로 짚게 한다
("측정 없는 게시 금지" — proactive.py가 읽은 뒤 삭제).
주입 없음(로컬 파일만 쓴다).
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

# 게시 예정물로 보는 상태 — 여기 있는데 측정 슬롯(메시지 ID·UTM)이 비면 경고 대상.
SCHEDULED_STATUS = ("scheduled", "gated")


def _label(rec):
    """콘텐츠 레코드 하나를 한 줄 라벨로. 형태를 단정하지 않는다(방어적)."""
    if not isinstance(rec, dict):
        return str(rec)[:60]
    for k in ("title", "name", "id"):
        v = str(rec.get(k) or "").strip()
        if v:
            return v if len(v) <= 40 else v[:39] + "…"
    return "(제목 없음)"


def _pending_items():
    """① 게시했는데 성과 레코드가 없는 콘텐츠 ② 게시 예정인데 측정 슬롯(메시지 ID·UTM)이 빈 콘텐츠.
    library.py 가 없거나 실패하면 빈 목록(훅은 절대 세션을 방해하지 않는다)."""
    try:
        import library  # noqa: PLC0415
    except Exception:
        return [], []

    try:
        unmeasured = [f"{_label(c)}[성과 미기록]" for c in (library.unmeasured() or [])]
    except Exception:
        unmeasured = []

    no_slot = []
    try:
        for c in (library.read_all("content") or []):
            if str(c.get("status") or "").strip().lower() not in SCHEDULED_STATUS:
                continue
            missing = []
            if not str(c.get("message_id") or "").strip():
                missing.append("메시지 ID")
            if not str(c.get("utm") or "").strip():
                missing.append("UTM")
            if missing:
                no_slot.append(f"{_label(c)}[{'·'.join(missing)} 없음]")
    except Exception:
        no_slot = []

    return unmeasured, no_slot


def _save_pending_unmeasured():
    """측정 없이 끝나는 세션을 그냥 넘기지 않는다 — 다음 세션 첫마디로 인계."""
    unmeasured, no_slot = _pending_items()
    items = unmeasured + no_slot
    if not items:
        # 남길 게 없으면 묵은 인계 메모도 정리(해결된 경고를 다음 세션에 되풀이하지 않는다)
        try:
            if os.path.exists(common.PENDING_UNMEASURED):
                os.remove(common.PENDING_UNMEASURED)
        except Exception:
            pass
        return
    try:
        os.makedirs(common.DATA_DIR, exist_ok=True)
        with open(common.PENDING_UNMEASURED, "w", encoding="utf-8") as f:
            json.dump({
                "count": len(items),
                "unmeasured": len(unmeasured),
                "no_slot": len(no_slot),
                "top": items[:5],
                "saved": common.now_iso(),
            }, f, ensure_ascii=False)
    except Exception:
        pass


def _write_worklog():
    today = datetime.date.today().isoformat()
    src = os.path.join(common.ACTIVITY_DIR, today + ".md")
    if not os.path.exists(src):
        return
    try:
        with open(src, encoding="utf-8") as f:
            acts = f.read().strip()
    except Exception:
        return
    if not acts:
        return
    outdir = os.path.join(common.DATA_DIR, "worklog")
    try:
        os.makedirs(outdir, exist_ok=True)
        out = os.path.join(outdir, f"{today}-draft.md")
        with open(out, "w", encoding="utf-8") as f:
            f.write(
                f"<!-- {common.PRIVATE_SENTINEL} -->\n"
                f"# 마케팅 활동 로그 · {today}  (자동 수집 — 사람이 검토·보완)\n\n"
                f"## 오늘의 제작·게시·발주\n{acts}\n\n"
                f"> [claude ai] 자동 초안입니다. **무엇을 어느 채널에 게시했고 반응이 어땠는지**, "
                f"각 게시물의 성과와 귀속 메시지 ID, 광고·발주 건의 판정(유지/중단/확대)은 "
                f"직접 채워 완성하세요. 근거 없는 수치는 적지 말고 '확인 필요'로 두세요.\n"
            )
    except Exception:
        pass


def main():
    p = common.proactive_cfg()
    if p is None or p.get("end_check", True) is False:
        return
    _write_worklog()
    # 측정 없는 게시는 반복 노동이 된다 — 다음 세션 첫마디로 인계
    _save_pending_unmeasured()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # 훅은 어떤 경우에도 세션을 방해하지 않는다
    sys.exit(0)
