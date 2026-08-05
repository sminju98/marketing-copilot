#!/usr/bin/env python3
"""로컬 최소 마케팅 DB — GA4·광고계정 커넥터가 없어도 마케팅 루프가 돌게 하는 JSONL 저장소.

자산 계층(PLAN §2-3):
  SIGNAL(신호) → OPPORTUNITY(기회) → MESSAGE(메시지) → CONTENT(콘텐츠)
  → ASSET(소재) → CAMPAIGN(캠페인) → PERFORMANCE(성과)
  성과는 콘텐츠가 아니라 **메시지**까지 거슬러 귀속시킨다. 콘텐츠·소재는 소모품,
  메시지는 복리 자산이다.

저장: $MKT_COPILOT_HOME/library/<파일>.jsonl — 한 줄 = 한 레코드(JSON).

사용:
  python3 scripts/library.py stats
  python3 scripts/library.py add signal --json '{"kind":"voc","text":"규격 맞추는 게 제일 귀찮다","source_grade":"customer"}'
  python3 scripts/library.py list content --status published --limit 10
  python3 scripts/library.py update content CON-20260726-1 --json '{"status":"published","url":"https://..."}'
  python3 scripts/library.py unmeasured          # 게시했는데 성과 기록 없는 콘텐츠 (측정 없는 게시 금지)
  python3 scripts/library.py expiring --days 3   # 유효기간 임박·경과 신호·기회
  python3 scripts/library.py fatigue --days 14   # 피로도 임박 소재 (리프레시 발주 트리거)

모듈로도 쓴다: stats() / unmeasured() / expiring() / fatigue() — 훅(proactive 등)이 import.
"""
import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import LIBRARY_DIR, file_lock, load_config, now_iso  # noqa: E402

# kind → (id 접두사, 저장 파일)
KINDS = {
    "signal": ("SIG", "signals.jsonl"),
    "opportunity": ("OPP", "opportunities.jsonl"),
    "message": ("MSG", "messages.jsonl"),
    "content": ("CON", "contents.jsonl"),
    "campaign": ("CMP", "campaigns.jsonl"),
    "asset": ("AST", "assets.jsonl"),
    "performance": ("PRF", "performance.jsonl"),
}

KIND_KO = {
    "signal": "신호", "opportunity": "기회", "message": "메시지", "content": "콘텐츠",
    "campaign": "캠페인", "asset": "소재", "performance": "성과",
}

# 레코드 기본값 — add 시 빠진 칸을 채운다(칸이 비어 있는 것과 값이 없는 것을 구분하기 위해).
# 지어낸 값은 넣지 않는다. 모르는 값은 빈 문자열로 두고 스킬이 "확인 필요"로 표기한다.
DEFAULTS = {
    "signal": {
        "kind": "", "text": "", "source_grade": "", "ttl_days": 0, "expires": "",
        "related_offering": "", "status": "new",
    },
    "opportunity": {
        "title": "", "offering": "", "audience": "", "evidence": "", "evidence_grade": "",
        "expected_effect": "", "channel": "", "test_budget": 0, "breakeven": "",
        "stop_condition": "", "expires": "", "status": "proposed",
    },
    "message": {
        "angle": "", "proof": "", "source": "", "performance_note": "", "uses": 0,
        "synced_to_sales": False, "status": "candidate",
    },
    "content": {
        "title": "", "message_id": "", "channel": "", "format": "", "status": "idea",
        "publish_date": "", "parent_id": "", "quality_bar": {}, "url": "", "utm": "",
        # 게이트(§6-J)·커뮤니티 3모드(VIR-06) 기록 칸
        "mode": "", "source_url": "", "gate": "", "gate_fail": "",
        "disclosure_mode": "", "next_action": "",
    },
    "campaign": {
        "name": "", "goal": "", "audience": "", "budget": 0, "budget_daily": 0, "kpi": "",
        "offer": "", "channel": "", "message_id": "", "allowed_cac": 0,
        "breakeven_roas": 0, "stop_condition": "", "scale_condition": "",
        "verdict_days": 0, "adops": False, "status": "planned", "verdict": "",
        # 판정 후 회수하는 실측치(ANA-16~17)
        "actual_cac": 0, "actual_roas": 0, "actual_revenue": 0, "learned": "",
    },
    "asset": {
        "brief_id": "", "if_job_id": "", "type": "", "spec": "", "copy": "",
        "message_id": "", "channel": "", "variants": 0, "budget_cap": 0, "utm": "",
        "parent_id": "", "campaign_id": "", "first_used": "", "fatigue_flag": False,
        "status": "briefed",
    },
    "performance": {
        "target_kind": "", "target_id": "", "message_id": "", "metrics": {},
        "input_mode": "manual", "source": "", "note": "",
    },
}

# 알려진 상태값 — 벗어나면 막지 않고 경고만 한다(수기 운용을 방해하지 않기 위해).
STATUSES = {
    "signal": ("new", "watching", "expired", "converted"),
    "opportunity": ("proposed", "approved", "running", "won", "dropped"),
    "message": ("candidate", "validated", "retired"),
    "content": ("idea", "draft", "gated", "ready", "scheduled", "published",
                "needs_work", "held"),
    "campaign": ("planned", "running", "paused", "stopped", "done"),
    "asset": ("briefed", "ordered", "delivered", "running", "refresh_due", "retired"),
}
# 신호 출처 등급(SIG-16) — 실측 > 고객 발화 > 외부 관찰 > 추측. 기회 평가 때 근거 강도가 된다.
SOURCE_GRADES = ("measured", "customer", "external", "guess")

# 유효기간 판정에서 제외할 상태(이미 끝난 레코드는 만료를 재촉하지 않는다).
CLOSED_STATUS = {
    "signal": {"expired", "converted"},
    "opportunity": {"won", "dropped"},
}
# 피로도 판정에서 제외할 소재 상태.
FATIGUE_SKIP_STATUS = {"retired"}


# ---------- 저장소 ----------
def _path(kind):
    return os.path.join(LIBRARY_DIR, KINDS[kind][1])


def read_all(kind=None, path=None):
    """JSONL 전체를 list[dict]로. 깨진 줄은 조용히 건너뛴다(수기 편집 보호)."""
    p = path or _path(kind)
    rows = []
    if not os.path.exists(p):
        return rows
    with open(p, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _append(path, rec):
    os.makedirs(LIBRARY_DIR, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _rewrite(path, rows):
    """전체 재작성. 임시 파일에 다 쓰고 원자적으로 갈아끼운다.

    임시 파일 이름에 pid 를 붙인다 — 고정 이름이면 두 프로세스가 같은 tmp 를
    밟아 서로의 절반을 덮어쓴다(실제로 0바이트 .tmp 가 남아 있었다).
    fsync 까지 해야 갈아끼우기 전에 내용이 디스크에 닿는다.
    """
    os.makedirs(LIBRARY_DIR, exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def _next_id(kind, rows):
    """ID 형식: <접두사>-<YYYYMMDD>-<그날 일련번호>. 예: SIG-20260726-1"""
    prefix = KINDS[kind][0]
    stamp = datetime.date.today().strftime("%Y%m%d")
    pat = re.compile(rf"^{prefix}-{stamp}-(\d+)$")
    top = 0
    for r in rows:
        m = pat.match(str(r.get("id", "")))
        if m:
            top = max(top, int(m.group(1)))
    return f"{prefix}-{stamp}-{top + 1}"


# ---------- 정규화 ----------
def _norm(s):
    return str(s or "").strip().lower()


def _today():
    return datetime.date.today()


def _parse_date(v):
    """'YYYY-MM-DD' 또는 ISO 일시 문자열을 date로. 못 읽으면 None."""
    s = str(v or "").strip()
    if not s:
        return None
    try:
        return datetime.date.fromisoformat(s[:10])
    except ValueError:
        return None


def _days_left(v):
    """오늘 기준 남은 일수(음수면 이미 경과). 못 읽으면 None."""
    d = _parse_date(v)
    return None if d is None else (d - _today()).days


def _days_since(v):
    d = _parse_date(v)
    return None if d is None else (_today() - d).days


def _cadence(key, fallback):
    try:
        return int(load_config(soft=True).get("cadence", {}).get(key, fallback) or fallback)
    except (TypeError, ValueError):
        return fallback


def _label(kind, rec):
    """사람이 읽을 한 줄 식별자."""
    for k in ("title", "name", "angle", "text", "type", "spec"):
        v = str(rec.get(k) or "").strip()
        if v:
            return v if len(v) <= 40 else v[:39] + "…"
    return rec.get("id", "?")


# ---------- 핵심 동작 ----------
def add(kind, data):
    """레코드 추가. id·created 자동 부여, 기본 필드 채움, ttl_days가 있으면 expires 계산.

    채번이 '전체를 읽어 다음 번호를 정하는' 방식이라, 잠그지 않으면 동시에 들어온
    두 건이 같은 id 를 받는다. 중복 id 는 오류 없이 퍼지고 update() 가 첫 매치에서
    멈추므로, 이후 갱신이 한쪽에만 가서 성과 귀속이 조용히 어긋난다.
    """
    with file_lock(_path(kind)):
        return _add_locked(kind, data)


def _add_locked(kind, data):
    rows = read_all(kind)
    rec = dict(DEFAULTS.get(kind, {}))
    rec.update(data)
    rec["id"] = _next_id(kind, rows)
    rec["created"] = rec.get("created") or now_iso()
    rec["updated"] = now_iso()

    if kind == "signal":
        # 유효기간(SIG-15): 밈·유행은 반감기가 짧아 별도 기본값을 쓴다.
        if not rec.get("ttl_days"):
            default_ttl = _cadence("meme_ttl_days", 7) if _norm(rec.get("kind")) == "meme" \
                else _cadence("signal_ttl_days", 21)
            rec["ttl_days"] = default_ttl
    if not rec.get("expires") and rec.get("ttl_days"):
        try:
            rec["expires"] = (_today() + datetime.timedelta(days=int(rec["ttl_days"]))).isoformat()
        except (TypeError, ValueError):
            pass

    _append(_path(kind), rec)
    _warn_unknown(kind, rec)
    _warn_orphan_target(kind, rec)
    return rec


def _warn_orphan_target(kind, rec):
    """performance 의 target_id 가 실제로 없는 레코드를 가리키면 경고한다(막지는 않는다).

    측정 커버리지는 내부 1순위 KPI인데, target_id 오타 한 글자면 성과가 기록돼도
    커버리지가 영원히 오르지 않고 해당 게시물이 계속 '미측정'으로 뜬다. 조용히
    받으면 원인을 못 찾으므로 반드시 알린다. (외부 항목 기록 등 정당한 경우가
    있어 차단하지 않고 경고만 한다.)"""
    if kind != "performance":
        return
    tk = _norm(rec.get("target_kind"))
    tid = str(rec.get("target_id") or "").strip()
    if tk not in KINDS or not tid:
        return
    if any(str(r.get("id") or "").strip() == tid for r in read_all(tk)):
        return
    print(f"[경고] {tk} {tid} 를 찾지 못했습니다 — 성과는 저장했지만 어디에도 귀속되지 않습니다.\n"
          f"       ID 오타면 측정 커버리지가 오르지 않고 그 게시물은 계속 '미측정'으로 남습니다.\n"
          f"       확인: python3 library.py list {tk} --limit 5", file=sys.stderr)


def update(kind, rec_id, patch):
    """부분 갱신(merge). 없는 id면 None.

    read_all → 메모리 수정 → 전체 재작성 사이에 남이 쓰면 그 쓰기가 통째로 사라진다.
    구간 전체를 잠가야 한다 — 재작성만 잠그면 이미 낡은 뷰를 쓰게 된다.
    """
    with file_lock(_path(kind)):
        return _update_locked(kind, rec_id, patch)


def _update_locked(kind, rec_id, patch):
    rows = read_all(kind)
    hit = None
    for r in rows:
        if r.get("id") == rec_id:
            r.update(patch)
            r["updated"] = now_iso()
            hit = r
            break
    if hit is None:
        return None
    _rewrite(_path(kind), rows)
    _warn_unknown(kind, hit)
    return hit


def _warn_unknown(kind, rec):
    """알려지지 않은 상태·출처 등급이면 경고만(저장은 막지 않는다)."""
    known = STATUSES.get(kind)
    st = _norm(rec.get("status"))
    if known and st and st not in known:
        print(f"[주의] {kind} status '{rec.get('status')}' 는 표준값이 아닙니다 "
              f"({'|'.join(known)})", file=sys.stderr)
    if kind == "signal":
        g = _norm(rec.get("source_grade"))
        if g and g not in SOURCE_GRADES:
            print(f"[주의] signal source_grade '{rec.get('source_grade')}' 는 표준값이 아닙니다 "
                  f"({'|'.join(SOURCE_GRADES)})", file=sys.stderr)


def list_rows(kind, status=None, limit=0):
    rows = read_all(kind)
    if status:
        rows = [r for r in rows if _norm(r.get("status")) == _norm(status)]
    if limit and limit > 0:
        rows = rows[:limit]
    return rows


# ---------- 파생 조회 ----------
def _measured_targets():
    """성과 레코드가 붙어 있는 대상 집합 {(target_kind, target_id)}."""
    out = set()
    for p in read_all("performance"):
        tk = _norm(p.get("target_kind"))
        tid = str(p.get("target_id") or "").strip()
        if tid:
            out.add((tk, tid))
    return out


def unmeasured():
    """published 인데 performance 레코드가 없는 콘텐츠.
    '측정 없는 게시 금지'(PLAN §3-6)를 기계적으로 보장하는 장치."""
    measured = _measured_targets()
    out = []
    for c in read_all("content"):
        if _norm(c.get("status")) != "published":
            continue
        cid = str(c.get("id") or "").strip()
        if not cid or ("content", cid) in measured:
            continue
        out.append(c)
    return out


def coverage():
    """측정 커버리지 — 게시된 콘텐츠 중 성과가 기록된 비율(내부 1순위 KPI, 목표 100%)."""
    published = [c for c in read_all("content") if _norm(c.get("status")) == "published"]
    miss = len(unmeasured())
    measured = len(published) - miss
    # 게시물이 0건이면 비율은 '해당 없음'(None)이다. 0/0을 100%로 표시하면
    # 아무것도 안 한 상태가 '완벽히 측정됨'으로 보여 KPI가 거짓 안심을 준다.
    rate = round(100 * measured / len(published)) if published else None
    return {"published": len(published), "measured": measured, "missing": miss, "rate": rate}


def expiring(days=3):
    """유효기간이 임박(days 이내)했거나 이미 경과한 신호·기회.
    속도형 신호는 유효기간이 지나면 가치가 0이 아니라 마이너스(늦은 브랜드로 보임)."""
    out = []
    for kind in ("signal", "opportunity"):
        closed = CLOSED_STATUS.get(kind, set())
        for r in read_all(kind):
            if _norm(r.get("status")) in closed:
                continue
            left = _days_left(r.get("expires"))
            if left is None or left > days:
                continue
            out.append({
                "kind": kind,
                "id": r.get("id", "?"),
                "label": _label(kind, r),
                "status": r.get("status") or "?",
                "expires": r.get("expires") or "",
                "days_left": left,
                "state": "경과" if left < 0 else "임박",
                "record": r,
            })
    out.sort(key=lambda x: x["days_left"])
    return out


def fatigue(days=None):
    """first_used 기준 피로도 임박·경과 소재. 이미지팩토리 리프레시 발주 트리거(PLAN §7-2 #2).
    임박 = 기준일 3일 전부터."""
    days = int(days or _cadence("fatigue_days", 14))
    out = []
    for r in read_all("asset"):
        if _norm(r.get("status")) in FATIGUE_SKIP_STATUS:
            continue
        used = _days_since(r.get("first_used"))
        if used is None or used < days - 3:
            continue
        out.append({
            "id": r.get("id", "?"),
            "label": _label("asset", r),
            "spec": r.get("spec") or "",
            "campaign_id": r.get("campaign_id") or "",
            "first_used": r.get("first_used") or "",
            "days_used": used,
            "threshold": days,
            "state": "경과" if used >= days else "임박",
            "flagged": bool(r.get("fatigue_flag")),
            "record": r,
        })
    out.sort(key=lambda x: -x["days_used"])
    return out


def stats():
    """kind별 건수 · 측정 커버리지(내부 1순위 KPI) · 검증된 메시지 수 · 실행중 캠페인 수."""
    counts = {k: len(read_all(k)) for k in KINDS}
    validated = len([m for m in read_all("message") if _norm(m.get("status")) == "validated"])
    running = len([c for c in read_all("campaign") if _norm(c.get("status")) == "running"])
    return {
        "counts": counts,
        "coverage": coverage(),
        "validated_messages": validated,
        "running_campaigns": running,
        "expiring": len(expiring()),
        "fatigue": len(fatigue()),
    }


# ---------- CLI ----------
def _print_rec(rec):
    print(json.dumps(rec, ensure_ascii=False, indent=2))


def _parse_json(raw):
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(f"[오류] --json 파싱 실패: {e}")
    if not isinstance(data, dict):
        raise SystemExit("[오류] --json 은 JSON 객체({...})여야 합니다.")
    return data


def cmd_stats():
    s = stats()
    cov = s["coverage"]
    print("📣 로컬 마케팅 DB 현황")
    for k, n in s["counts"].items():
        print(f"- {KIND_KO.get(k, k)}: {n}건")
    if cov["rate"] is None:
        print("- 측정 커버리지: — (게시물 0건 · 목표 100%) "
              "— 게시물 중 성과가 기록된 비율(내부 1순위 KPI). 아직 잴 게 없습니다")
    else:
        print(f"- 측정 커버리지: {cov['rate']}% ({cov['measured']}/{cov['published']} · 목표 100%) "
              f"— 게시물 중 성과가 기록된 비율(내부 1순위 KPI)")
    if cov["missing"]:
        print(f"  ⚠️ 성과 미기록 게시물 {cov['missing']}건 — `unmeasured` 로 확인, 오늘 안에 기록할 것")
    print(f"- 검증된 메시지: {s['validated_messages']}건 (복리 자산 — 성과는 여기에 귀속)")
    print(f"- 실행중 캠페인: {s['running_campaigns']}건")
    if s["expiring"]:
        print(f"- ⏳ 유효기간 임박·경과: {s['expiring']}건 (`expiring`)")
    if s["fatigue"]:
        print(f"- 🔁 소재 피로도 임박·경과: {s['fatigue']}건 (`fatigue`)")


def cmd_unmeasured():
    rows = unmeasured()
    if rows:
        print("⚠️ 성과 기록 없는 게시물 — 측정 없는 게시 금지. 오늘 안에 성과를 기록할 것")
        print("| ID | 제목 | 채널 | 게시일 | 메시지 ID |")
        print("|---|---|---|---|---|")
        for c in rows:
            print(f"| {c.get('id','?')} | {_label('content', c)} | {c.get('channel') or '?'} "
                  f"| {c.get('publish_date') or '확인 필요'} | {c.get('message_id') or '미귀속'} |")
        print("→ 기록: `library.py add performance --json '{\"target_kind\":\"content\","
              "\"target_id\":\"<ID>\",\"message_id\":\"<MSG-ID>\",\"metrics\":{...},"
              "\"input_mode\":\"manual\"}'`")
    else:
        print("성과 미기록 게시물 없음 — 측정 커버리지 100% ✅")
    print(f"총 {len(rows)}건")


def cmd_expiring(days):
    rows = expiring(days)
    if rows:
        print(f"⏳ 유효기간 임박·경과 ({days}일 이내) — 지금 쓰거나 상태를 내릴 것")
        print("| 상태 | 유형 | ID | 내용 | 진행 | 만료일 | 남은 일수 |")
        print("|---|---|---|---|---|---|---|")
        for r in rows:
            left = f"{r['days_left']}일" if r["days_left"] >= 0 else f"{-r['days_left']}일 경과"
            print(f"| {r['state']} | {KIND_KO.get(r['kind'], r['kind'])} | {r['id']} "
                  f"| {r['label']} | {r['status']} | {r['expires'] or '확인 필요'} | {left} |")
    else:
        print("유효기간 임박·경과 항목 없음 ✅")
    print(f"총 {len(rows)}건")


def cmd_fatigue(days):
    rows = fatigue(days)
    thr = rows[0]["threshold"] if rows else int(days or _cadence("fatigue_days", 14))
    if rows:
        print(f"🔁 소재 피로도 임박·경과 (기준 {thr}일) — 리프레시 시점")
        print("| 상태 | ID | 소재 | 규격 | 캠페인 | 최초 사용 | 경과일 |")
        print("|---|---|---|---|---|---|---|")
        for r in rows:
            print(f"| {r['state']} | {r['id']} | {r['label']} | {r['spec'] or '?'} "
                  f"| {r['campaign_id'] or '-'} | {r['first_used'] or '확인 필요'} | {r['days_used']}일 |")
        print("→ 성과 하락이 함께 확인되면 리프레시 발주를 제안한다([[imagefactory]]). "
              "성과 근거 없이 '피로도'만으로 발주를 밀지 않는다.")
    else:
        print(f"피로도 임박·경과 소재 없음 (기준 {thr}일) ✅")
    print(f"총 {len(rows)}건")


def main():
    p = argparse.ArgumentParser(description="Marketing Copilot 로컬 최소 마케팅 DB (JSONL)")
    sub = p.add_subparsers(dest="cmd", required=True)
    kind_arg = dict(choices=sorted(KINDS))

    sub.add_parser("stats", help="kind별 건수·측정 커버리지·검증 메시지·실행중 캠페인")

    sp = sub.add_parser("add", help="레코드 추가(id·created 자동)")
    sp.add_argument("kind", **kind_arg)
    sp.add_argument("--json", required=True, dest="payload")

    sp = sub.add_parser("list", help="목록 조회")
    sp.add_argument("kind", **kind_arg)
    sp.add_argument("--status", default="")
    sp.add_argument("--limit", type=int, default=0)

    sp = sub.add_parser("update", help="부분 갱신(merge)")
    sp.add_argument("kind", **kind_arg)
    sp.add_argument("id")
    sp.add_argument("--json", required=True, dest="payload")

    sub.add_parser("unmeasured", help="published인데 성과 레코드가 없는 콘텐츠")

    sp = sub.add_parser("expiring", help="유효기간 임박·경과 신호·기회")
    sp.add_argument("--days", type=int, default=3)

    sp = sub.add_parser("fatigue", help="피로도 임박·경과 소재(리프레시 트리거)")
    sp.add_argument("--days", type=int, default=0)

    a = p.parse_args()

    if a.cmd == "stats":
        cmd_stats()
    elif a.cmd == "add":
        _print_rec(add(a.kind, _parse_json(a.payload)))
    elif a.cmd == "list":
        rows = list_rows(a.kind, a.status, a.limit)
        for r in rows:
            print(json.dumps(r, ensure_ascii=False))
        print(f"# 총 {len(rows)}건", file=sys.stderr)
    elif a.cmd == "update":
        rec = update(a.kind, a.id, _parse_json(a.payload))
        if rec is None:
            raise SystemExit(f"[오류] {a.kind} {a.id} 를 찾지 못했습니다.")
        _print_rec(rec)
    elif a.cmd == "unmeasured":
        cmd_unmeasured()
    elif a.cmd == "expiring":
        cmd_expiring(a.days)
    elif a.cmd == "fatigue":
        cmd_fatigue(a.days)


if __name__ == "__main__":
    main()
