#!/usr/bin/env python3
"""Render assets/preview.png: claudefetch in a frosted Frappé terminal window.

Runs claudefetch under a pseudo-TTY against a demo HOME (so the picture holds
no real account data), converts its truecolor ANSI output to HTML, and
screenshots the page with chrome-headless.

    python3 scripts/render-preview.py
"""

import html
import json
import os
import pty
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "preview.png"
SIZE = (1600, 900)

PALETTE = [  # chips under the window
    ("mauve", "#ca9ee6"), ("blue", "#8caaee"), ("teal", "#81c8be"),
    ("green", "#a6d189"), ("yellow", "#e5c890"), ("peach", "#ef9f76"),
    ("red", "#e78284"), ("pink", "#f4b8e4"), ("lavender", "#babbf1"),
    ("base", "#303446"),
]


def demo_home(root: Path) -> None:
    now = datetime.now(timezone.utc)
    iso = lambda d: d.isoformat().replace("+00:00", "Z")
    claude = root / ".claude"
    for sub in ("agents", "output-styles"):
        (claude / sub).mkdir(parents=True)
    for name in ("implementer", "reviewer", "verifier", "fitter"):
        (claude / "agents" / f"{name}.md").write_text("x")
    for i in range(12):
        (claude / "skills" / f"skill-{i}").mkdir(parents=True)
        (claude / "skills" / f"skill-{i}" / "SKILL.md").write_text("x")
    for p in range(6):
        d = claude / "projects" / f"p{p}"
        d.mkdir(parents=True)
        for s in range(14):
            (d / f"{s}.jsonl").write_text("{}")
    (root / ".claude.json").write_text(json.dumps({
        "oauthAccount": {
            "displayName": "you",
            "planDisplayName": "Ultra",
            "organizationRateLimitTier": "default_claude_max_20x",
            "billingType": "stripe_subscription",
            "organizationRole": "admin",
            "hasExtraUsageEnabled": False,
            "accountCreatedAt": iso(now - timedelta(days=610)),
            "subscriptionCreatedAt": iso(now - timedelta(days=540)),
        },
        "cachedUsageUtilization": {
            "fetchedAtMs": int(now.timestamp() * 1000),
            "utilization": {
                "five_hour": {"utilization": 34, "resets_at": iso(now + timedelta(hours=2, minutes=11))},
                "seven_day": {"utilization": 62, "resets_at": iso(now + timedelta(days=3, hours=11))},
            },
        },
        "numStartups": 125,
        "installMethod": "native",
        "autoUpdates": True,
        "claudeCodeFirstTokenDate": iso(now - timedelta(days=400)),
        "projects": {f"/p{i}": {} for i in range(24)},
        "mcpServers": {"context7": {}, "playwright": {}},
    }))
    (claude / "settings.json").write_text(json.dumps({
        "model": "claude-opus-5-5",
        "effortLevel": "high",
        "outputStyle": "Orchestrator",
        "theme": "dark",
        "enabledPlugins": {"a": True, "b": True, "c": True},
        "hooks": {"Stop": [{"hooks": [{}]}], "PreToolUse": [{"hooks": [{}, {}]}]},
    }))


def capture(home: Path) -> str:
    env = dict(os.environ, CLAUDEFETCH_HOME=str(home), CLAUDEFETCH_NO_KEYCHAIN="1",
               TERM_PROGRAM="ghostty", TERM_PROGRAM_VERSION="1.4.0", SHELL="/bin/zsh")
    env.pop("CLAUDEFETCH_TITLE", None)
    env.pop("NO_COLOR", None)
    pid, fd = pty.fork()
    if pid == 0:
        os.execve(sys.executable, [sys.executable, str(ROOT / "claudefetch"),
                                   "--no-anim", "--title", "you@claude.ai"], env)
    chunks = []
    while True:
        try:
            data = os.read(fd, 65536)
        except OSError:
            break
        if not data:
            break
        chunks.append(data)
    os.waitpid(pid, 0)
    return b"".join(chunks).decode("utf-8").replace("\r\n", "\n").rstrip("\n")


SGR = re.compile(r"\x1b\[([0-9;]*)m")
OTHER = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def ansi_to_html(text: str) -> str:
    out, color, bold, pos = [], None, False, 0

    def emit(chunk):
        if not chunk:
            return
        style = []
        if color:
            style.append("color:%s" % color)
        if bold:
            style.append("font-weight:700")
        if color and "█" in chunk:
            # paint block runs as solid boxes: font glyphs leave seams between cells
            for run in re.split(r"(█+)", chunk):
                if run.startswith("█"):
                    out.append('<span class="blk" style="background:%s;box-shadow:0 1px 0 %s">%s</span>'
                               % (color, color, " " * len(run)))
                elif run:
                    emit(run)
            return
        esc = html.escape(chunk)
        out.append('<span style="%s">%s</span>' % (";".join(style), esc) if style else esc)

    for m in SGR.finditer(text):
        emit(OTHER.sub("", text[pos:m.start()]))
        pos = m.end()
        codes = [int(c) for c in m.group(1).split(";") if c] or [0]
        i = 0
        while i < len(codes):
            c = codes[i]
            if c == 0:
                color, bold = None, False
            elif c == 1:
                bold = True
            elif c == 38 and i + 4 < len(codes) and codes[i + 1] == 2:
                color = "rgb(%d,%d,%d)" % tuple(codes[i + 2:i + 5])
                i += 4
            i += 1
    emit(OTHER.sub("", text[pos:]))
    return "".join(out)


def page(body: str) -> str:
    chips = "".join(
        '<div class="chip"><i style="background:%s"></i><span>%s</span></div>' % (hexv, name)
        for name, hexv in PALETTE)
    return """<!doctype html><meta charset="utf-8">
<style>
  html,body{margin:0;width:%dpx;height:%dpx;overflow:hidden;background:#303446}
  .blob{position:absolute;border-radius:50%%;filter:blur(110px);opacity:.55}
  .win{position:absolute;left:50%%;top:44%%;transform:translate(-50%%,-50%%);
       padding:0 0 34px;border-radius:16px;
       background:rgba(41,44,60,.72);backdrop-filter:blur(28px);
       border:1px solid rgba(198,208,245,.12);
       box-shadow:0 30px 80px rgba(20,22,32,.55)}
  .bar{height:44px;display:flex;align-items:center;padding:0 18px;gap:8px;
       border-bottom:1px solid rgba(198,208,245,.08)}
  .bar i{width:12px;height:12px;border-radius:50%%;display:block}
  .bar span{flex:1;text-align:center;margin-right:52px;color:#838ba7;
            font:500 13px -apple-system,system-ui,sans-serif}
  pre{margin:0;padding:22px 34px 0;color:#c6d0f5;
      font:15px/20px "JetBrains Mono",monospace;font-variant-ligatures:none}
  .blk{display:inline-block;height:20px;vertical-align:top}
  .prompt{color:#a6d189}
  .chips{position:absolute;bottom:44px;left:0;right:0;display:flex;justify-content:center;gap:10px}
  .chip{display:flex;flex-direction:column;align-items:center;gap:6px}
  .chip i{display:block;width:84px;height:28px;border-radius:7px;border:1px solid rgba(198,208,245,.1)}
  .chip span{color:#a5adce;font:12px -apple-system,system-ui,sans-serif}
</style>
<div class="blob" style="left:-120px;top:-160px;width:620px;height:520px;background:#ca9ee6"></div>
<div class="blob" style="right:-140px;top:-80px;width:600px;height:500px;background:#8caaee"></div>
<div class="blob" style="left:-60px;bottom:-220px;width:620px;height:480px;background:#81c8be"></div>
<div class="blob" style="right:180px;bottom:-260px;width:560px;height:440px;background:#ef9f76;opacity:.35"></div>
<div class="win">
  <div class="bar"><i style="background:#e78284"></i><i style="background:#e5c890"></i><i style="background:#a6d189"></i><span>claudefetch — zsh</span></div>
<pre><span class="prompt">❯</span> claudefetch
%s</pre>
</div>
<div class="chips">%s</div>
""" % (SIZE[0], SIZE[1], body, chips)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        home.mkdir()
        demo_home(home)
        raw = capture(home)
        # the colour blocks are already shown as chips below the window
        lines = raw.split("\n")
        while lines and not SGR.sub("", lines[-1]).replace("█", "").strip():
            lines.pop()
        html_path = Path(tmp) / "preview.html"
        html_path.write_text(page(ansi_to_html("\n".join(lines))))
        OUT.parent.mkdir(exist_ok=True)
        subprocess.run(["chrome-headless", "--headless", "--hide-scrollbars",
                        "--screenshot=%s" % OUT, "--window-size=%d,%d" % SIZE, "--force-device-scale-factor=2",
                        "--user-data-dir=%s" % (Path(tmp) / "chrome"),
                        html_path.as_uri()], check=True, capture_output=True, timeout=60)
    print(OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
