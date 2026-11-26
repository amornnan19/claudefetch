import contextlib
import io
import json
import os
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
cf = SourceFileLoader("claudefetch", str(ROOT / "claudefetch")).load_module()

EMAIL = "someone@example.com"
UUID = "12345678-90ab-4cde-8f01-234567890abc"
TOKEN = "sk-ant-oat01-SECRETTOKEN"
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def iso(dt):
    return dt.isoformat()


class Pure(unittest.TestCase):
    def test_model_name(self):
        self.assertEqual(cf.model_name("claude-opus-5-5"), "Opus 5.5")
        self.assertEqual(cf.model_name("claude-sonnet-4-5-20250929"), "Sonnet 4.5")
        self.assertEqual(cf.model_name("claude-haiku-4"), "Haiku 4")
        self.assertEqual(cf.model_name("claude-haiku-4-20250101"), "Haiku 4")
        self.assertEqual(cf.model_name("claude-opus-5-5[1m]"), "Opus 5.5 (1M)")
        self.assertEqual(cf.model_name("gpt-4"), "gpt-4")

    def test_tier_name(self):
        self.assertEqual(cf.tier_name("default_claude_max_20x"), "Max 20x")
        self.assertEqual(cf.tier_name("default_claude_max_5x"), "Max 5x")
        self.assertEqual(cf.tier_name("default_claude_pro"), "Pro")
        self.assertEqual(cf.tier_name("weird"), "weird")
        self.assertIsNone(cf.tier_name(None))

    def test_duration(self):
        self.assertEqual(cf.duration(2 * 86400 + 11 * 3600 + 5), "2d 11h")
        self.assertEqual(cf.duration(3 * 3600 + 5 * 60), "3h 05m")
        self.assertEqual(cf.duration(12 * 60), "12m")

    def test_gauge_colour_thresholds(self):
        self.assertEqual(cf.gauge_color(49), "overlay1")
        self.assertEqual(cf.gauge_color(50), "yellow")
        self.assertEqual(cf.gauge_color(79.6), "peach")
        self.assertEqual(cf.gauge_color(79.4), "yellow")
        self.assertEqual(cf.gauge_color(100), "red")

    def test_gauge_shape(self):
        self.assertEqual(cf.gauge(70), "━" * 7 + "─" * 3)
        self.assertEqual(cf.gauge(0), "─" * 10)
        self.assertEqual(cf.gauge(250), "━" * 10)

    def test_ago(self):
        self.assertEqual(cf.ago(1_000_000 - 4 * 60_000, now=1000), "cached 4m ago")
        self.assertEqual(cf.ago(1_000_000, now=1000), "cached just now")

    def test_rainbow(self):
        out = cf.rainbow("Ultra", 0)
        self.assertEqual(ANSI.sub("", out), "Ultra")
        escapes = set(re.findall(r"\x1b\[38;2;\d+;\d+;\d+m", out))
        self.assertEqual(len(escapes), 5)
        self.assertNotEqual(cf.rainbow("Ultra", 0), cf.rainbow("Ultra", 0.5))
        self.assertTrue(out.startswith("\033[38;2;231;130;132m"))  # red at phase 0


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.claude = self.home / ".claude"
        self.saved = dict(os.environ)
        self.addCleanup(self.restore_env)
        os.environ.update({
            "CLAUDEFETCH_HOME": str(self.home),
            "CLAUDEFETCH_NO_KEYCHAIN": "1",
            "CLAUDEFETCH_NO_SUBPROCESS": "1",
        })
        for k in ("ANTHROPIC_MODEL", "NO_COLOR", "CLAUDEFETCH_NO_ANIM", "CLAUDEFETCH_TITLE",
                  "TERM_PROGRAM", "TERM_PROGRAM_VERSION", "SHELL"):
            os.environ.pop(k, None)

    def restore_env(self):
        os.environ.clear()
        os.environ.update(self.saved)

    def run_main(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cf.main(list(args))
        return code, buf.getvalue()

    def populate(self):
        now = datetime.now(timezone.utc)
        (self.claude / "agents").mkdir(parents=True)
        (self.claude / "agents" / "a.md").write_text("x")
        (self.claude / "agents" / "b.md").write_text("x")
        for s in ("s1", "s2", "s3"):
            (self.claude / "skills" / s).mkdir(parents=True)
            (self.claude / "skills" / s / "SKILL.md").write_text("x")
        (self.claude / "projects" / "p1").mkdir(parents=True)
        (self.claude / "projects" / "p1" / "one.jsonl").write_text("{}")
        (self.claude / "projects" / "p1" / "two.jsonl").write_text("{}")
        (self.claude / ".credentials.json").write_text(json.dumps({
            "claudeAiOauth": {"accessToken": TOKEN, "refreshToken": TOKEN + "R",
                              "subscriptionType": "max",
                              "rateLimitTier": "default_claude_max_5x"}}))
        (self.claude / "settings.json").write_text(json.dumps({
            "model": "claude-opus-5-5", "outputStyle": "Orchestrator",
            "theme": "dark", "effortLevel": "high",
            "hooks": {"Stop": [{"hooks": [{"type": "command"}, {"type": "command"}]}],
                      "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command"}]}]},
            "enabledPlugins": {"a@m": True, "b@m": False, "c@m": True}}))
        (self.home / ".claude.json").write_text(json.dumps({
            "numStartups": 12, "installMethod": "native", "autoUpdates": False,
            "claudeCodeFirstTokenDate": "2025-10-27T00:00:00Z",
            "projects": {"/a": {}, "/b": {}}, "mcpServers": {"m": {}},
            "cachedUsageUtilization": {
                "fetchedAtMs": int((now - timedelta(minutes=4)).timestamp() * 1000),
                "accountUuid": UUID,
                "utilization": {
                    "five_hour": None,
                    "seven_day": {"utilization": 70,
                                  "resets_at": iso(now + timedelta(days=2, hours=11, minutes=30))}}},
            "oauthAccount": {
                "emailAddress": EMAIL, "accountUuid": UUID, "organizationUuid": UUID,
                "displayName": "Ton", "organizationName": EMAIL + "'s Organization",
                "planDisplayName": "Ultra", "organizationRateLimitTier": "default_claude_max_20x",
                "billingType": "stripe_subscription", "organizationRole": "admin",
                "hasExtraUsageEnabled": False,
                "accountCreatedAt": "2025-03-24T11:40:03.460789Z",
                "subscriptionCreatedAt": "2025-06-05T09:01:05.810516Z"}}))

    def test_plain_output(self):
        self.populate()
        code, out = self.run_main("--no-color")
        self.assertEqual(code, 0)
        self.assertIn("Plan: Ultra · Max 20x", out)
        self.assertIn("Model: Opus 5.5 (claude-opus-5-5)", out)
        self.assertRegex(out, r"Usage 7d: ━{7}─{3} 70% · resets in 2d 1[12]h")
        self.assertIn("cached 4m ago", out)
        self.assertNotIn("Usage 5h", out)
        self.assertIn("Extensions: 2 agents · 3 skills · 2 plugins · 1 MCP · 3 hooks", out)
        self.assertIn("Local: 2 projects · 2 sessions · 12 launches", out)
        self.assertIn("Claude Code: (native, auto-update off)", out)
        self.assertIn("Effort: high", out)
        self.assertIn("First token: 2025-10-27", out)
        self.assertNotIn("\033", out)

    def test_no_logo(self):
        self.populate()
        _, out = self.run_main("--no-color", "--no-logo")
        self.assertTrue(out.splitlines()[0].startswith("Ton"))

    def test_custom_title_precedence_and_kept_verbatim(self):
        self.populate()
        cfg = self.home / ".config" / "claudefetch"
        cfg.mkdir(parents=True)
        (cfg / "title").write_text("file@title.xyz\n")
        _, out = self.run_main("--no-color", "--no-logo")
        self.assertEqual(out.splitlines()[:2], ["file@title.xyz", "-" * 14])
        os.environ["CLAUDEFETCH_TITLE"] = "env@title.xyz"
        _, out = self.run_main("--no-color", "--no-logo")
        self.assertTrue(out.startswith("env@title.xyz\n"))
        _, out = self.run_main("--no-color", "--no-logo", "--title", "flag@title.xyz")
        self.assertTrue(out.startswith("flag@title.xyz\n"))
        _, out = self.run_main("--json", "--title", "flag@title.xyz")
        self.assertEqual(json.loads(out)["name"], "flag@title.xyz")

    def test_secrets_never_printed(self):
        self.populate()
        for args in (["--no-color"], ["--json"], ["--no-color", "--no-logo"]):
            _, out = self.run_main(*args)
            for secret in (EMAIL, "example.com", UUID, TOKEN, "SECRETTOKEN"):
                self.assertNotIn(secret, out, args)

    def test_credentials_fallback_when_oauth_missing(self):
        self.populate()
        cj = json.loads((self.home / ".claude.json").read_text())
        del cj["oauthAccount"]["planDisplayName"]
        del cj["oauthAccount"]["organizationRateLimitTier"]
        (self.home / ".claude.json").write_text(json.dumps(cj))
        _, out = self.run_main("--no-color")
        self.assertIn("Plan: Max · Max 5x", out)

    def test_env_model_wins(self):
        self.populate()
        os.environ["ANTHROPIC_MODEL"] = "claude-sonnet-4-5-20250929"
        _, out = self.run_main("--no-color")
        self.assertIn("Model: Sonnet 4.5 (claude-sonnet-4-5-20250929)", out)

    def test_expired_reset_omits_usage(self):
        self.populate()
        cj = json.loads((self.home / ".claude.json").read_text())
        cj["cachedUsageUtilization"]["utilization"]["seven_day"]["resets_at"] = iso(
            datetime.now(timezone.utc) - timedelta(hours=1))
        (self.home / ".claude.json").write_text(json.dumps(cj))
        _, out = self.run_main("--no-color")
        self.assertNotIn("Usage", out)

    def test_json(self):
        self.populate()
        code, out = self.run_main("--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["plan"], "Ultra · Max 20x")
        self.assertEqual(data["model"], "Opus 5.5 (claude-opus-5-5)")
        self.assertNotIn("\033", out)

    def test_empty_home(self):
        for args in (["--no-color"], ["--json"]):
            code, out = self.run_main(*args)
            self.assertEqual(code, 0)
            self.assertNotIn("Traceback", out)
        self.assertNotIn("unknown", self.run_main("--no-color")[1])

    def test_malformed_files(self):
        (self.home / ".claude.json").write_text("{not json")
        (self.claude).mkdir()
        (self.claude / "settings.json").write_text("[1, 2")
        (self.claude / ".credentials.json").write_text("nope")
        for args in (["--no-color"], ["--json"]):
            code, out = self.run_main(*args)
            self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.run_main("--json")[1]), {})

    def test_wrong_types_do_not_crash(self):
        (self.home / ".claude.json").write_text(json.dumps({
            "oauthAccount": "x", "projects": [], "mcpServers": 3, "numStartups": "n",
            "cachedUsageUtilization": {"utilization": {"seven_day": {"utilization": "hi"}}}}))
        (self.claude).mkdir()
        (self.claude / "settings.json").write_text(json.dumps(
            {"hooks": {"Stop": "x"}, "enabledPlugins": [], "model": 5}))
        code, _ = self.run_main("--no-color")
        self.assertEqual(code, 0)

    def test_non_tty_has_no_cursor_codes(self):
        self.populate()
        _, out = self.run_main()
        self.assertNotIn("\033[?25l", out)
        self.assertNotIn("\033", out)

    def test_pick_creds_discards_everything_else(self):
        got = cf.pick_creds(json.dumps({"claudeAiOauth": {
            "accessToken": TOKEN, "subscriptionType": "max", "rateLimitTier": "t"}}))
        self.assertEqual(got, {"subscriptionType": "max", "rateLimitTier": "t"})


if __name__ == "__main__":
    unittest.main()
