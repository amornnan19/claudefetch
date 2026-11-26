# claudefetch — plan

**สรุป (ไทย):** สร้าง `claudefetch` เป็นสคริปต์ Python ไฟล์เดียว (stdlib ล้วน) แสดงข้อมูล Claude แบบ fastfetch — โลโก้ ASCII ด้านซ้าย, รายการข้อมูลด้านขวา (plan, tier, model, usage 7 วัน/5 ชม., เวอร์ชัน Claude Code, จำนวน agents/skills/plugins/MCP, projects/sessions ฯลฯ) ใช้สี Catppuccin Frappé truecolor, ชื่อ plan (เช่น `Ultra`) เป็น rainbow ไล่สีวิ่ง ~2 วินาทีแล้วหยุด (ปิดได้ด้วย `--no-anim`), มี `--json`, `--no-color`, `--no-logo` ไม่แสดง email และไม่แตะ token ใน keychain นอกจาก 2 ฟิลด์ plan/tier มี unit test ด้วย fixture HOME ปลอม

## Context

The user wants a fastfetch-style CLI named `claudefetch` that prints information about their Claude setup (plan, model, usage, etc.). The project dir `/Users/amornnan/Documents/project/amornnan/claudefect` is empty and not a git repo. All data is local; no network calls.

## Decisions (do not reopen)

- **Python 3, single file, stdlib only.** Rejected: Go/Node (user chose Python).
- **Colours: Catppuccin Frappé truecolor** (`\033[38;2;r;g;bm`), never 256-colour codes. Rejected: Anthropic clay theme.
- **No network.** Usage comes from Claude Code's own cache, labelled with its age.
- **Never print email, tokens, UUIDs.** Keychain read extracts only `subscriptionType` and `rateLimitTier`; the rest of the JSON is discarded immediately.
- A field whose source is missing is **omitted**, never printed as `unknown`/`0`. The tool must never crash on a missing/malformed file (catch per-field).

## Files

| Path | What |
|---|---|
| `claudefetch` | executable script, `#!/usr/bin/env python3`, chmod +x |
| `tests/test_claudefetch.py` | unittest; loads the script via `importlib.machinery.SourceFileLoader` |
| `README.md` | what it shows, flags, install (`ln -s "$PWD/claudefetch" ~/.local/bin/claudefetch`) |
| `.gitignore` | `__pycache__/` |

Also `git init -b main` (no commit).

## Data sources

`home` = `Path(os.environ.get("CLAUDEFETCH_HOME", Path.home()))` — the override exists for tests. `claude_dir = home/".claude"`.

1. `home/.claude.json` → `oauthAccount`: `displayName`, `organizationName`, `planDisplayName`, `organizationType`, `organizationRateLimitTier`, `billingType`, `organizationRole`, `hasExtraUsageEnabled`, `accountCreatedAt`, `subscriptionCreatedAt`. Top-level: `cachedUsageUtilization` (`fetchedAtMs`, `utilization.five_hour`, `utilization.seven_day` each `{utilization, resets_at}` or null), `numStartups`, `installMethod`, `autoUpdates`, `claudeCodeFirstTokenDate`, `projects` (dict → count), `mcpServers` (dict → count).
2. Credentials (only `subscriptionType`, `rateLimitTier` from `claudeAiOauth`):
   - macOS: `security find-generic-password -s "Claude Code-credentials" -w`, timeout 2s, skipped when `CLAUDEFETCH_NO_KEYCHAIN=1` or not darwin.
   - else / fallback: `claude_dir/.credentials.json`.
3. `claude_dir/settings.json`: `model`, `outputStyle`, `theme`, `effortLevel`, `hooks` (count = total hook entries across events), `enabledPlugins` (count of true values).
4. Model resolution: `ANTHROPIC_MODEL` env > settings `model` > omit.
5. `claude --version` (subprocess, timeout 2s, first token of output, skip on failure; skipped when `CLAUDEFETCH_NO_SUBPROCESS=1`, used by tests).
6. Counts: `claude_dir/agents/*.md`, `claude_dir/skills/*/SKILL.md`, `claude_dir/output-styles/*.md`, sessions = `claude_dir/projects/*/*.jsonl`.
7. Terminal: `TERM_PROGRAM` (+ `TERM_PROGRAM_VERSION`); Shell: basename of `SHELL`.

## Formatting helpers (pure, tested)

- `model_name("claude-opus-5-5") -> "Opus 5.5"`; `claude-sonnet-4-5-20250929 -> "Sonnet 4.5"`; `claude-haiku-4 -> "Haiku 4"`; anything not matching `^claude-([a-z]+)-(\d+)(?:-(\d{1,2}))?` returned unchanged; a `[1m]` suffix becomes ` (1M)`.
- `tier_name("default_claude_max_20x") -> "Max 20x"`, `"default_claude_max_5x" -> "Max 5x"`, `"default_claude_pro"` → `"Pro"`; otherwise raw string.
- `duration(seconds) -> "2d 11h"` / `"3h 05m"` / `"12m"`.
- `gauge(pct, width=10)` → `━` filled, `─` empty; colour: `<50` overlay1, `≥50` yellow, `≥80` peach, `≥100` red (judged on the rounded integer displayed).
- `ago(ms)` for cache age → `"cached 4m ago"`.

## Output lines (order; label → value)

Title: `{displayName}@{organizationName}` (title in mauve bold, `@` text), then a `-` underline of the same visible length.

| Label | Value |
|---|---|
| Plan | `{planDisplayName} · {tier_name(organizationRateLimitTier)}` — tier falls back to credentials `rateLimitTier`; if no planDisplayName use credentials `subscriptionType.title()` |
| Billing | `billingType` with `_` → space (e.g. `stripe subscription`) |
| Model | `{model_name(id)} ({id})` |
| Effort | `effortLevel` |
| Usage 5h | `{gauge} {pct}% · resets in {duration}` (skip if null or reset passed) |
| Usage 7d | same |
| Usage note | dim `cached Xm ago` appended to the 7d line (or 5h if only that) |
| Extra usage | `on` / `off` |
| Role | `organizationRole` |
| Member since | `accountCreatedAt` date (YYYY-MM-DD) + ` ({N}y {M}mo)` or `({N}mo)` |
| Subscribed | `subscriptionCreatedAt` date, same format |
| Claude Code | `{version} ({installMethod}, auto-update on/off)` |
| Output style | `outputStyle` |
| Theme | `theme` |
| Extensions | `{n} agents · {n} skills · {n} plugins · {n} MCP · {n} hooks` (drop zero parts? no — keep all present sources, zeros allowed here) |
| Projects | `{projects} projects · {sessions} sessions · {numStartups} launches` |
| First token | `claudeCodeFirstTokenDate` date |
| Terminal / Shell | as above |

Then a blank line and two colour-block rows (`███` × 8 each): row 1 red, peach, yellow, green, teal, sky, blue, mauve; row 2 rosewater, flamingo, pink, maroon, sapphire, lavender, subtext0, surface2.

Labels in blue bold, `: ` in overlay0, values in text `#c6d0f5`.

## Running rainbow on the plan name (user request)

The user showed their status line where the plan name `Ultra` is drawn in a rainbow gradient and asked for a **running (animated) rainbow** on it.

- Applies to the `planDisplayName` part of the `Plan` value only (e.g. `Ultra`); the ` · Max 20x` after it stays text colour.
- Gradient stops (Frappé): red, peach, yellow, green, teal, sky, sapphire, blue, lavender, mauve, pink, then back to red. Character `i` at frame `f` gets the colour at position `(i * 0.15 + f * 0.08) mod 1` along that loop, **linearly interpolated in RGB** between neighbouring stops (smooth, not stepped). Pure function `rainbow(text, phase) -> str`, tested.
- Animation: after the full output is printed, if animation is enabled, hide the cursor (`\033[?25l`), and for **2.0 s at ~20 fps** redraw only the Plan line in place: move up `n` lines (`\033[{n}A`, where `n` = lines from the Plan line to the end of output), `\r`, reprint that whole row (logo part + info part) with `\033[K`, move back down `\033[{n}B`, flush, `time.sleep(0.05)`. Finish on a static frame (phase 0) and always restore the cursor (`\033[?25h`) in a `try/finally`, including on `KeyboardInterrupt` (exit 130 quietly).
- Animation is enabled only when: colour is on, stdout is a TTY, not `--json`, not `--no-anim`, and `CLAUDEFETCH_NO_ANIM` unset. With colour on but animation off, print the static gradient (phase 0). With `--no-color`, plain text.
- New flag: `--no-anim`. New flag: `--anim SECONDS` (float, default 2.0; `0` = no animation).
- Test: `rainbow("Ultra", 0)` contains 5 distinct truecolor escapes and strips to `Ultra`; `rainbow(..., 0) != rainbow(..., 0.5)`; the fixture run (not a TTY) contains no `\033[?25l`.

## Logo

A ~10-line ASCII Claude starburst (radiating asterisk made of `\ | /` `-` and `*` characters) in **peach `#ef9f76`**, the Frappé colour nearest Claude's clay. Logo left, info right, 3-space gap; pad logo to fixed width; the column longer than the other is padded with blanks. Compute visible width ignoring ANSI escapes.

## Flags (argparse)

- `--json`: print a JSON object of the collected raw-ish fields (same keys as the labels, snake_case, values as strings/numbers; no colours, no logo). Must not contain email/token/uuid.
- `--no-color`: no ANSI. Also implied by `NO_COLOR` env or stdout not a TTY.
- `--no-logo`.
- `--version`: `claudefetch 0.1.0`.

## Tests (`python3 -m unittest discover -s tests`)

- `model_name`, `tier_name`, `duration`, `gauge` thresholds (49→overlay1, 50→yellow, 79.6→peach since displays 80, 100→red).
- Fixture HOME (tempdir) with a full `.claude.json` + `settings.json` + a few agent/skill files; run `main(["--no-color"])` capturing stdout with `CLAUDEFETCH_HOME`, `CLAUDEFETCH_NO_KEYCHAIN=1`, `CLAUDEFETCH_NO_SUBPROCESS=1`: asserts `Plan: Ultra · Max 20x`, `Model: Opus 5.5 (claude-opus-5-5)`, `Usage 7d` with `70%`, counts correct.
- Fixture `.claude.json` includes an `emailAddress` and `accountUuid` and a credentials file with an `accessToken`: assert none of those strings appear in plain or `--json` output.
- Empty HOME (no files): exits 0, prints no traceback.
- Malformed `.claude.json` (`{not json`): exits 0.
- `--json` parses with `json.loads`.

## Out of scope

Network calls, config files, themes other than Frappé, Windows, packaging to PyPI/Homebrew.

## Done

1. `python3 -m unittest discover -s tests -v` passes.
2. `./claudefetch`, `./claudefetch --no-color`, `./claudefetch --json`, `NO_COLOR=1 ./claudefetch` all run on the real machine without traceback, and output shows no email address.
3. Main session then symlinks into `~/.local/bin` and runs `claudefetch` once to show the user.
