# claudefetch

A fastfetch-style summary of your local Claude setup: plan, tier, model, usage
(from Claude Code's own cache, no network), Claude Code version, extension
counts, projects and sessions. Python 3, stdlib only, Catppuccin Frappe truecolor.

The plan name runs a rainbow for about two seconds on a TTY, then settles.

Never shown: email address, tokens, account or organisation UUIDs. From the
macOS keychain item `Claude Code-credentials` only `subscriptionType` and
`rateLimitTier` are read.

## Flags

- `--json` print fields as JSON (no colour, no logo)
- `--no-color` plain text (also implied by `NO_COLOR` or a non-TTY stdout)
- `--no-logo` hide the logo
- `--no-anim` static rainbow; `--anim SECONDS` animation length (default 2.0, `0` = off)
- `--title TEXT` title line. Default order: `--title`, `$CLAUDEFETCH_TITLE`, first line of `~/.config/claudefetch/title`, then your display name. A title you set is shown verbatim (the email filter does not apply to it).
- `--version`

`CLAUDEFETCH_NO_ANIM=1` also disables the animation.

## Install

    ln -s "$PWD/claudefetch" ~/.local/bin/claudefetch

## Tests

    python3 -m unittest discover -s tests -v
