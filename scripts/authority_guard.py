#!/usr/bin/env python3
"""Marketing Copilot의 과업 범위와 실행 권한을 기계적으로 제한한다.

프롬프트 지침만으로는 모델의 과도한 주도성을 완전히 막을 수 없다. 이 모듈은
UserPromptSubmit에서 세션 범위를 기록하고 PreToolUse에서 코드·파일·외부 시스템
변경을 승인 대기로 보내며, 고객용 산출물에 내부 평가가 섞이는 것을 차단한다.
원문 프롬프트는 저장하지 않는다.
"""
import hashlib
import json
import os
import re
import tempfile

import common


MARKETING_TERMS = (
    "마케팅", "광고", "캠페인", "콘텐츠", "카피", "브리프",
    "랜딩", "퍼널", "타깃", "타겟", "roas", "cpa", "cpc", "seo", "crm",
    "인스타", "틱톡", "블로그", "게시", "발행", "홍보",
    "marketing", "advertising", "campaign",
)
ARTIFACT_TERMS = (
    "고객용", "고객사에", "클라이언트용", "외부 공유", "대외용", "제출용", "발송용",
    "제안서", "견적서", "입찰서", "소개서", "납품 문서", "proposal", "quotation",
    "client-facing", "customer-facing", "send to client", "share with client",
)
DEV_TERMS = (
    "코드", "버그", "리팩터", "구현", "테스트", "배포", "깃", "github", "커밋", "브랜치",
    "플러그인", "스킬", "hook", "훅", "설정", "settings.json", "claude.md", "config.json",
    "api", "서버", "데이터베이스", "sql", "frontend", "backend", "python", "typescript",
    "javascript", "repository", "repo", "pull request", "merge", "deploy", "build",
)
EXPLICIT_MARKETING_OVERRIDE = (
    "마케팅 코드", "마케팅 플러그인", "마케팅 코파일럿", "marketing-copilot",
    "marketing copilot", "광고 코드", "캠페인 코드",
)
CRITIQUE_PATTERNS = (
    "비윤리", "윤리적 문제", "바람직하지", "고객사 문제", "고객의 문제", "사업상 문제",
    "사업 중단", "사업 폐기", "사업을 접", "법적 리스크", "내부 리스크", "리스크 분석",
    "과장광고", "과장 광고", "기만", "부도덕", "문제가 있는 사업", "개선해야 한다",
    "unethical", "immoral", "client risk", "customer risk", "legal risk", "shut down",
)
CODE_EXTENSIONS = (
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".sh", ".bash", ".zsh", ".sql",
    ".json", ".jsonc", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env",
)
EXTERNAL_TOOL_WORDS = re.compile(
    r"(?:^|__|_)(?:create|update|edit|delete|remove|send|post|publish|schedule|upload|"
    r"apply|execute|launch|deploy|invite|message|comment|transfer|purchase)(?:$|__|_)",
    re.I,
)
READ_ONLY_BASH = (
    re.compile(r"^(?:pwd|ls)(?:\s|$)"),
    re.compile(r"^(?:rg|grep|cat|head|tail|wc|find|stat|file)(?:\s|$)"),
    re.compile(r"^sed\s+-n(?:\s|$)"),
    re.compile(r"^jq(?:\s|$)"),
    re.compile(r"^git\s+(?:status|diff|log|show|branch)(?:\s|$)"),
    re.compile(r"^marketing-copilot\s+(?:doctor|--root|--list|library\s+(?:list|stats))(?:\s|$)"),
    re.compile(r"^python3?\s+[^\s]*gates\.py\s+(?:status|selftest|template\s+check)(?:\s|$)"),
)
SHELL_MUTATION = re.compile(
    r"(?:^|[;&|]\s*)(?:rm|rmdir|mv|cp|install|chmod|chown|mkdir|touch|truncate|tee)\b|"
    r"\bsed\s+-i\b|\bperl\s+-i\b|(?:^|\s)(?:>|>>)(?:\s|$)|"
    r"\bgit\s+(?:add|commit|push|pull|merge|rebase|reset|clean|restore|checkout|switch|"
    r"cherry-pick|revert|tag)\b|\b(?:curl|wget)\b|\bpostiz\b|"
    r"\b(?:publish|send|upload|deploy|launch|delete|remove)\b",
    re.I,
)


def _hits(text, terms):
    value = (text or "").lower()
    return sum(1 for term in terms if term in value)


def classify(prompt):
    """현재 요청의 최소 범위를 반환한다. 개발 과업이면 마케팅 훅은 침묵한다."""
    text = (prompt or "").strip().lower()
    marketing_hits = _hits(text, MARKETING_TERMS)
    dev_hits = _hits(text, DEV_TERMS)
    explicit_override = any(term in text for term in EXPLICIT_MARKETING_OVERRIDE)
    artifact_only = marketing_hits > 0 and any(term in text for term in ARTIFACT_TERMS)

    # 마케팅 플러그인 자체 수정 요청은 개발 과업이다. 마케팅 운영 스킬을 활성화하지 않는다.
    if dev_hits >= 2 or (dev_hits and not marketing_hits) or (explicit_override and dev_hits):
        active = False
        kind = "development"
    elif marketing_hits:
        active = True
        kind = "external_artifact" if artifact_only else "marketing"
    else:
        active = False
        kind = "unrelated"

    return {
        "active": active,
        "artifact_only": artifact_only and active,
        "kind": kind,
        "marketing_hits": min(marketing_hits, 20),
        "dev_hits": min(dev_hits, 20),
    }


def _state_dir():
    return os.path.join(common.DATA_DIR, "_scope_guard")


def _safe_session(session_id):
    return hashlib.sha256(str(session_id or "-").encode("utf-8")).hexdigest()[:24]


def state_path(session_id):
    return os.path.join(_state_dir(), _safe_session(session_id) + ".json")


def save_state(session_id, scope):
    """분류 결과만 원자적으로 저장한다. 프롬프트·산출물 내용은 저장하지 않는다."""
    payload = {
        "schema": 1,
        "active": bool(scope.get("active")),
        "artifact_only": bool(scope.get("artifact_only")),
        "kind": str(scope.get("kind") or "unrelated"),
    }
    try:
        os.makedirs(_state_dir(), exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix="scope-", suffix=".json", dir=_state_dir())
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
        os.replace(tmp, state_path(session_id))
    except OSError:
        return False
    return True


def load_state(session_id):
    try:
        with open(state_path(session_id), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError, TypeError):
        return {"active": False, "artifact_only": False, "kind": "unrelated"}
    return {
        "active": bool(data.get("active")),
        "artifact_only": bool(data.get("artifact_only")),
        "kind": str(data.get("kind") or "unrelated"),
    }


def authority_context(scope):
    if not scope.get("active"):
        return ""
    lines = [
        "[MARKETING COPILOT — AUTHORITY & SCOPE GUARD]",
        "사용자의 명시적 목표·요청 범위·기대이익이 최우선이다. 코파일럿은 조언자/작성자이며 경영자·윤리심사자·법률판단자가 아니다.",
        "요청하지 않은 고객·사업·상품의 윤리성/정당성/존폐를 평가하지 말고, 무관한 개선·비판·조사를 과업에 끼워 넣지 않는다.",
        "분석·진단·제안·초안 요청은 실행 권한이 아니다. 파일/코드/설정 수정, 삭제, 게시, 발송, 캠페인·예산 변경은 사용자의 명시적 요청과 직전 확인이 모두 필요하다.",
        "관련 없는 발견은 산출물을 바꾸지 말고 별도의 선택적 제안 1줄로만 알린다. 사용자가 요청한 산출물만 완성하면 정상적으로 종료할 수 있다.",
    ]
    if scope.get("artifact_only"):
        lines.extend([
            "[EXTERNAL ARTIFACT CLEAN ROOM] 고객/외부 제출본에는 요청된 내용만 넣는다.",
            "내부 위험평가·고객 비판·사업성/윤리성 판단·법적 추정·사내 메모를 본문/부록/주석/메타데이터에 동봉하지 않는다.",
            "승인되지 않은 조건은 [미확정]으로 두거나 사용자에게 묻는다. 운영 준비도 미충족은 실제 집행만 막고, 제안서 작성 자체를 다른 과업으로 확장하지 않는다.",
        ])
    return "\n".join(lines)


def _decision(kind, reason):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": kind,
            "permissionDecisionReason": reason,
        }
    }


def _tool_text(tool_input):
    values = []
    for key in ("content", "new_string", "command", "query", "message", "body", "text"):
        value = tool_input.get(key)
        if isinstance(value, str):
            values.append(value)
    return "\n".join(values)


def evaluate_tool(data, scope=None):
    """PreToolUse 입력을 ask/deny/무결정으로 판정한다."""
    session = data.get("session_id") or "-"
    scope = scope or load_state(session)
    if not scope.get("active"):
        return None

    tool_name = str(data.get("tool_name") or "")
    tool_input = data.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}
    path = str(tool_input.get("file_path") or tool_input.get("path") or "")
    content = _tool_text(tool_input)

    if scope.get("artifact_only") and tool_name in {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
        if path.lower().endswith(CODE_EXTENSIONS):
            return _decision("deny", "고객용 산출물 작성 범위에서는 코드·설정 파일을 수정할 수 없습니다.")
        lowered = content.lower()
        if any(pattern in lowered for pattern in CRITIQUE_PATTERNS):
            return _decision(
                "deny",
                "고객용 산출물에 내부 윤리·법률·사업 리스크 평가가 포함되었습니다. 요청된 제안 내용만 남겨 다시 작성하세요.",
            )

    if tool_name in {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
        return _decision("ask", "마케팅 과업의 파일 변경은 사용자 확인 후 실행합니다.")

    if tool_name == "Bash":
        command = str(tool_input.get("command") or "").strip()
        if command and any(pattern.search(command) for pattern in READ_ONLY_BASH) and not SHELL_MUTATION.search(command):
            return None
        return _decision("ask", "마케팅 과업의 셸 실행은 변경·전송 가능성이 있어 사용자 확인이 필요합니다.")

    normalized_tool = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", tool_name)
    if tool_name.lower().startswith("mcp__") and EXTERNAL_TOOL_WORDS.search(normalized_tool):
        return _decision("ask", "외부 시스템을 생성·수정·발송·게시하는 작업은 사용자 확인이 필요합니다.")

    return None
