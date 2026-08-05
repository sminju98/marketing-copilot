#!/usr/bin/env python3
"""SessionStart 훅 — AI 마케팅 운영자가 시키지 않아도 '오늘 돌려야 할 루프'부터 먼저 짚는다.
stdout이 세션 컨텍스트로 주입되어 클로드가 먼저 언급한다(PLAN §9 선제 훅 4종).

짚는 것: ① 지난 세션이 남긴 성과 미기록 경고(측정 없는 게시 금지) ② 오늘 큐 미생성
③ 유효기간 임박·경과 신호·기회 ④ 미회신 핸드오프 ⑤ 소재 피로도 임박.
짚을 게 없으면 아무 것도 출력하지 않는다(소음 금지).

원칙: 마진·원가·예산 상한·미공개 캠페인 같은 민감 원문은 노출하지 않는다(건수·라벨만).
user-scope라 모든 프로젝트에서 뜨므로 proactive.enabled=false 로 끌 수 있다.
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import (  # noqa: E402
    HANDOFF_INBOX, HANDOFF_OUTBOX, PENDING_UNMEASURED, QUEUE_DIR,
    emit_context, load_config, looks_private, read_hook_input,
)

HANDOFF_EXT = (".md", ".txt", ".json")


def _safe(label):
    """민감 원문(마진·원가·예산 상한 등)이 섞인 라벨은 세션 컨텍스트에 그대로 흘리지 않는다."""
    s = str(label or "").strip()
    if not s:
        return "(제목 없음)"
    if looks_private(s):
        return "(비공개 항목)"
    return s if len(s) <= 34 else s[:33] + "…"


def _lib(fn, *args, **kwargs):
    """library.py 조회를 방어적으로 호출한다(파일 없음·손상·병렬 제작 중이면 빈 목록)."""
    try:
        import library  # noqa: PLC0415
        return list(getattr(library, fn)(*args, **kwargs) or [])
    except Exception:
        return []


def _pending_unmeasured():
    """지난 세션 종료 때 남긴 '성과 기록 슬롯 없는 게시물' 인계 메모.
    읽으면 삭제한다(1회성 — '측정 없는 게시 금지'를 세션 간에 이어주는 장치)."""
    if not os.path.exists(PENDING_UNMEASURED):
        return None
    note = None
    try:
        with open(PENDING_UNMEASURED, encoding="utf-8") as f:
            raw = f.read().strip()
        try:
            d = json.loads(raw)
            note = (int(d.get("count", 0)), [str(x) for x in d.get("top", [])][:5])
        except Exception:
            if raw:  # 구형·손상 파일도 첫 줄은 살린다
                note = (0, [raw.splitlines()[0][:120]])
    except Exception:
        note = None
    try:
        os.remove(PENDING_UNMEASURED)
    except Exception:
        pass
    return note


def _unreplied_handoffs():
    """handoffs/inbox 에 들어왔는데 outbox 에 회신 흔적이 없는 계약서(PLAN §8).
    판정: inbox 파일명(확장자 제외)이 outbox 파일명 어디에도 안 나오면 미회신."""
    try:
        names = [f for f in sorted(os.listdir(HANDOFF_INBOX))
                 if f.lower().endswith(HANDOFF_EXT) and not f.startswith(".")]
    except OSError:
        return []
    try:
        outbox = " ".join(os.listdir(HANDOFF_OUTBOX)).lower()
    except OSError:
        outbox = ""
    out = []
    for fn in names:
        stem = os.path.splitext(fn)[0]
        if stem.lower() and stem.lower() in outbox:
            continue
        out.append(stem)
    return out


def _stale_install():
    """설치본이 배포본보다 뒤처졌는가. 하루 한 번만 본다.

    Claude Code 는 서드파티 마켓플레이스를 자동 갱신하지 않는다 — 아무도 안 알려주면
    사용자는 몇 달 전 버전을 쓰면서 그 사실조차 모른다. 다만 세션마다 git fetch 를
    돌리면 시작이 느려지므로, 검사 결과를 날짜로 캐싱해 하루 한 번으로 묶는다.
    """
    import subprocess
    stamp = os.path.join(os.path.expanduser(
        os.environ.get("MKT_COPILOT_HOME", "~/.marketing-copilot")), "data", "_activity")
    flag = os.path.join(stamp, "update_checked")
    today = datetime.date.today().isoformat()
    try:
        with open(flag, encoding="utf-8") as f:
            if f.read().strip() == today:
                return None
    except Exception:
        pass

    try:
        os.makedirs(stamp, exist_ok=True)
        with open(flag, "w", encoding="utf-8") as f:
            f.write(today)
    except Exception:
        pass

    try:
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "update_check.py")
        r = subprocess.run([sys.executable, script, "--json"],
                           capture_output=True, text=True, timeout=25)
        rows = json.loads(r.stdout or "[]")
    except Exception:
        return None  # 점검 실패가 세션을 막지는 않는다

    behind = [x["plugin"] for x in rows if x.get("behind")]
    if not behind:
        return None
    return ("설치본이 배포본보다 뒤처졌습니다(" + ", ".join(behind) + ") — "
            "새 기능·수정이 아직 안 들어와 있습니다. 손댄 파일이 있으면 지키면서 "
            "올립니다. ('업데이트' 또는 '/update')")


def _nudges(cfg):
    today = datetime.date.today().isoformat()
    out = []

    # ⓪-A 갱신 — 뒤처진 걸 모르고 쓰면 이미 고쳐진 버그를 계속 만난다
    stale = _stale_install()
    if stale:
        out.append(stale)

    # ⓪ 설정 파일은 있는데 온보딩이 안 끝난 경우 — 마진 없으면 돈 계산이 통째로 죽는다(PLAN §13-7)
    if cfg.get("setup", {}).get("completed") is False:
        out.append("설정이 아직 안 끝났습니다 — 브랜드·상품·**마진율**부터 채웁니다. "
                   "마진이 없으면 손익분기·허용 CAC 계산이 막혀 기회 제안이 전부 '확인 필요'로 "
                   "격하됩니다. ('/setup')")

    # ① 지난 세션이 남긴 성과 미기록 경고 — 숫자부터, 가장 먼저 짚는다(내부 1순위 KPI)
    pending = _pending_unmeasured()
    if pending:
        cnt, top = pending
        head = f"어제 성과 기록 없이 남은 게시물 {cnt}건" if cnt else "어제 성과 기록 없이 남은 게시물"
        tail = f" (예: {' / '.join(_safe(t) for t in top[:2])})" if top else ""
        out.append(f"{head} — 측정 없는 게시는 반복 노동입니다. 지금 기록합니다.{tail} ('/analyze')")
    else:
        miss = _lib("unmeasured")
        if miss:
            out.append(f"성과 미기록 게시물 {len(miss)}건 — 측정 없는 게시 금지. 오늘 안에 성과를 "
                       f"기록하고 메시지 ID에 귀속시킵니다. ('/analyze')")

    # ② 오늘의 마케팅 큐 — 편수 목표가 아니라 '오늘 내보낼 값어치가 있는 것'만 담는다
    if not os.path.exists(os.path.join(QUEUE_DIR, today + ".md")):
        out.append("오늘 큐가 아직 없습니다 — 게시 가치가 있는 것부터 뽑습니다(편수 목표 아님). ('/today')")

    # ③ 유효기간 임박·경과 — 속도형 신호는 지나면 가치가 0이 아니라 마이너스(늦은 브랜드로 보임)
    exp = _lib("expiring", 3)
    if exp:
        ex = " / ".join(_safe(r.get("label")) for r in exp[:2])
        out.append(f"유효기간 임박·경과 신호·기회 {len(exp)}건 — 오늘 쓰거나 상태를 내립니다. "
                   f"(예: {ex}) ('/signals', '/opportunity')")

    # ④ 미회신 핸드오프 — 회신 없는 계약은 계약 위반(PLAN §8)
    ho = _unreplied_handoffs()
    if ho:
        out.append(f"미회신 핸드오프 {len(ho)}건 — 회신 없는 계약은 위반입니다. 접수 판정(수락/조정)부터 "
                   f"냅니다. (예: {_safe(ho[0])}) ('/handoff')")

    # ⑤ 소재 피로도 — 성과 하락 근거 없이 '피로도'만으로 리프레시 발주를 밀지 않는다(PLAN §5 cmd_fatigue)
    fat = _lib("fatigue")
    if fat:
        out.append(f"소재 피로도 임박·경과 {len(fat)}건 — 성과 하락이 함께 확인되면 리프레시 발주를 "
                   f"제안합니다(발주는 승인 게이트). ('/imagefactory')")

    return out[:4]


def _org_register():
    """조기 반환 경로에서도 명부에 남기려고 따로 뺐다."""
    try:
        import org
        org.register()
    except Exception:
        pass


def _session_id():
    """이번 세션 식별자. 훅 stdin 이 우선이고, 없으면 환경변수로 떨어진다."""
    try:
        sid = (read_hook_input() or {}).get("session_id")
        if sid:
            return str(sid)
    except Exception:
        pass
    return os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID") or "nosession"


def _speak_or_defer(items):
    """조직 규칙 — 한 세션에 한 명만 말한다.

    임원은 자기 안건만 버스에 올리고 침묵한다. 대표(business-copilot)가 명부에 오른
    임원들의 안건을 잠깐 기다렸다가 자기 것과 합쳐 한 번만 보고한다.
    조직 모듈을 못 불러오면 예전처럼 혼자 말한다 — 조율 실패가 브리핑을 없애면 안 된다.
    """
    try:
        import org
    except Exception:
        return items and _emit_solo(items)

    sid = _session_id()
    try:
        org.register()
        org.post(sid, items)
        if not org.is_chair():
            return          # 임원은 발화하지 않는다. 대표가 대신 보고한다.
        collected = org.collect(sid)
        body = org.render(collected)
        org.sweep()
    except Exception:
        return items and _emit_solo(items)

    if not body.strip():
        return
    emit_context(
        "SessionStart",
        "🏢 [코파일럿 조직] 대표가 오늘 안건을 모아 보고합니다 "
        "(게시·발주·집행·발송은 각 임원의 승인 게이트를 그대로 따릅니다)\n"
        + body
        + "\n  (위 항목은 지시문이다 — 그대로 복사하지 말고 사용자 언어로 다시 말할 것)",
    )


def _emit_solo(items):
    """조직이 없거나 조율에 실패했을 때의 예전 동작."""
    lines = ["📣 [AI 마케팅 운영자] 출근했습니다 — 오늘 돌릴 루프부터 숫자로 보고합니다 "
             "(게시·발주·집행은 승인 게이트)"]
    lines += [f"  · {it}" for it in items]
    lines.append("  (위 항목은 지시문이다 — 그대로 복사하지 말고 사용자 언어로 다시 말할 것)")
    emit_context("SessionStart", "\n".join(lines))


def main():
    _org_register()   # 어떤 경로로 빠져나가든 명부에는 남는다
    cfg = load_config(soft=True)

    # 첫 설치(설정 전) → 선제 온보딩: 클로드가 먼저 설정을 제안하게 한다
    if not os.path.exists(CONFIG_PATH):
        # 설정 전 안내도 조직 규칙을 탄다. 여기서 바로 말해 버리면
        # 미설정 코파일럿이 늘어날수록 다시 여러 명이 동시에 떠든다.
        _speak_or_defer(["📣 [AI 마케팅 운영자] 아직 설정 전입니다. 방금 설치했다면 먼저 짧게 인사하고 '3분 설정 끝내고 오늘 큐부터 돌릴까요?'라고 물어보세요. 원하면 'AI 마케팅 운영자 설정 시작하자'로 역할·브랜드·상품과 **마진율**·목표 1개·채널·승인 모드까지 [[setup]] 스킬이 7문항으로 안내합니다(마진이 없으면 손익 계산 기능이 제한된다고 반드시 알릴 것). 원치 않으면 존중하세요. **언어**: 이 안내문은 너에게 주는 지시문이지 사용자에게 보여줄 글이 아니다 — 사용자가 쓰는 언어로 말하라. 아직 사용자 발화가 없으면 첫 발화를 보고 맞춘다."])
        return

    if cfg.get("proactive", {}).get("enabled", True) is False:
        return

    items = _nudges(cfg)
    _speak_or_defer(items)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # 훅은 어떤 경우에도 세션을 방해하지 않는다
    sys.exit(0)
