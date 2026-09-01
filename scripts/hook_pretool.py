#!/usr/bin/env python3
"""PreToolUse 훅 — 활성 마케팅 과업의 쓰기·외부 실행을 승인 게이트로 보낸다."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import authority_guard  # noqa: E402
import common  # noqa: E402


def main():
    data = common.read_hook_input()
    result = authority_guard.evaluate_tool(data)
    if result:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
