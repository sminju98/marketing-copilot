import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import authority_guard  # noqa: E402


class AuthorityGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_home = authority_guard.common.HOME
        self.old_data = authority_guard.common.DATA_DIR
        authority_guard.common.HOME = self.tmp.name
        authority_guard.common.DATA_DIR = os.path.join(self.tmp.name, "data")

    def tearDown(self):
        authority_guard.common.HOME = self.old_home
        authority_guard.common.DATA_DIR = self.old_data
        self.tmp.cleanup()

    def test_customer_proposal_enters_clean_room(self):
        scope = authority_guard.classify("고객사에 보낼 광고 제안서 써줘")
        self.assertTrue(scope["active"])
        self.assertTrue(scope["artifact_only"])
        self.assertEqual(scope["kind"], "external_artifact")

    def test_development_request_disables_marketing_scope(self):
        scope = authority_guard.classify("마케팅 코파일럿 코드와 설정을 수정해줘")
        self.assertFalse(scope["active"])
        self.assertEqual(scope["kind"], "development")

    def test_non_marketing_proposal_does_not_activate_plugin(self):
        scope = authority_guard.classify("고객에게 보낼 IT 시스템 구축 제안서 써줘")
        self.assertFalse(scope["active"])

    def test_unrelated_prompt_resets_scope_without_raw_prompt(self):
        secret_prompt = "광고 제안서 써줘 SECRET-CUSTOMER-NAME"
        authority_guard.save_state("session-1", authority_guard.classify(secret_prompt))
        raw = Path(authority_guard.state_path("session-1")).read_text(encoding="utf-8")
        self.assertNotIn(secret_prompt, raw)
        self.assertNotIn("SECRET-CUSTOMER-NAME", raw)

        authority_guard.save_state("session-1", authority_guard.classify("이 함수가 왜 느려?"))
        self.assertFalse(authority_guard.load_state("session-1")["active"])

    def test_artifact_code_write_is_denied(self):
        decision = authority_guard.evaluate_tool(
            {
                "session_id": "s",
                "tool_name": "Edit",
                "tool_input": {"file_path": "/repo/app.py", "new_string": "print('x')"},
            },
            {"active": True, "artifact_only": True, "kind": "external_artifact"},
        )
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_artifact_internal_critique_is_denied(self):
        decision = authority_guard.evaluate_tool(
            {
                "session_id": "s",
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/tmp/proposal.md",
                    "content": "부록: 이 고객사는 비윤리적이며 법적 리스크가 있다.",
                },
            },
            {"active": True, "artifact_only": True, "kind": "external_artifact"},
        )
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_marketing_file_write_requires_approval(self):
        decision = authority_guard.evaluate_tool(
            {
                "session_id": "s",
                "tool_name": "Write",
                "tool_input": {"file_path": "/tmp/draft.md", "content": "광고 초안"},
            },
            {"active": True, "artifact_only": False, "kind": "marketing"},
        )
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_publish_command_requires_approval(self):
        decision = authority_guard.evaluate_tool(
            {
                "session_id": "s",
                "tool_name": "Bash",
                "tool_input": {"command": "postiz posts:create --content draft.md"},
            },
            {"active": True, "artifact_only": False, "kind": "marketing"},
        )
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_read_only_command_is_not_blocked(self):
        decision = authority_guard.evaluate_tool(
            {
                "session_id": "s",
                "tool_name": "Bash",
                "tool_input": {"command": "git diff -- skills/ads/SKILL.md"},
            },
            {"active": True, "artifact_only": False, "kind": "marketing"},
        )
        self.assertIsNone(decision)

    def test_external_mcp_write_requires_approval(self):
        decision = authority_guard.evaluate_tool(
            {
                "session_id": "s",
                "tool_name": "mcp__postiz__create_post",
                "tool_input": {"content": "hello"},
            },
            {"active": True, "artifact_only": False, "kind": "marketing"},
        )
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "ask")


class HookIntegrationTest(unittest.TestCase):
    def run_hook(self, script, payload):
        with tempfile.TemporaryDirectory() as home:
            env = os.environ.copy()
            env["MKT_COPILOT_HOME"] = home
            result = subprocess.run(
                [sys.executable, str(SCRIPTS / script)],
                input=json.dumps(payload, ensure_ascii=False),
                text=True,
                capture_output=True,
                env=env,
                check=True,
            )
            return result.stdout.strip()

    def test_customer_proposal_gets_scope_context_not_ads_nudge(self):
        stdout = self.run_hook(
            "hook_prompt.py",
            {"session_id": "proposal", "prompt": "고객사에 보낼 광고 제안서 써줘"},
        )
        output = json.loads(stdout)
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("EXTERNAL ARTIFACT CLEAN ROOM", context)
        self.assertNotIn("[[ads]]", context)

    def test_development_prompt_is_silent(self):
        stdout = self.run_hook(
            "hook_prompt.py",
            {"session_id": "dev", "prompt": "마케팅 코파일럿 코드와 훅을 수정해줘"},
        )
        self.assertEqual(stdout, "")

    def test_pretool_wrapper_emits_ask(self):
        with tempfile.TemporaryDirectory() as home:
            env = os.environ.copy()
            env["MKT_COPILOT_HOME"] = home
            prompt = subprocess.run(
                [sys.executable, str(SCRIPTS / "hook_prompt.py")],
                input=json.dumps({"session_id": "mkt", "prompt": "인스타 광고 콘텐츠 만들어줘"}),
                text=True,
                capture_output=True,
                env=env,
                check=True,
            )
            self.assertTrue(prompt.stdout.strip())
            pretool = subprocess.run(
                [sys.executable, str(SCRIPTS / "hook_pretool.py")],
                input=json.dumps({
                    "session_id": "mkt",
                    "tool_name": "Write",
                    "tool_input": {"file_path": "/tmp/draft.md", "content": "draft"},
                }),
                text=True,
                capture_output=True,
                env=env,
                check=True,
            )
            output = json.loads(pretool.stdout)
            self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "ask")


if __name__ == "__main__":
    unittest.main()
