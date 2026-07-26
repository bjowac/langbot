---
name: tickets
description: Manage GitHub issues (list, search, show, create, edit, close) using scripts/tickets_api.py. Use whenever the user asks to list, search, view, create, edit, or close a GitHub issue/ticket — in this repo (bjowac/langbot) or any other owner/repo they name.
---

# GitHub tickets via `scripts/tickets_api.py`

This repo ships a small, dependency-light (`requests` only) CLI for managing GitHub issues at `scripts/tickets_api.py`. Use it instead of raw `gh`/`curl` calls whenever the task is listing, searching, viewing, creating, editing, or closing issues.

## Auth

- Read operations (`list`, `show`) work without a token, but are rate-limited to 60 requests/hour and will print a warning.
- Write operations (`create`, `edit`, `close`) **require** `GITHUB_TOKEN` in the environment — the script exits with an error if it's unset.
- Never print or log the token value. If the user pastes a token directly into chat instead of running `! export GITHUB_TOKEN=...` themselves, flag that it's now in the conversation transcript and suggest rotating it once done.
- Check quickly with: `[ -n "$GITHUB_TOKEN" ] && echo set || echo unset`

## Commands

All commands take `<owner/repo>` as the first positional argument.

```sh
# List issues (paginates automatically)
python3 scripts/tickets_api.py list <owner/repo> [--state open|closed|all] [--labels a,b] [--search "text"]
# --search defaults --state to "all" and filters client-side over title/body (case-insensitive),
# printing a matching snippet per hit.

# Show one issue's full title/state/URL/body
python3 scripts/tickets_api.py show <owner/repo> <issue_number>

# Create an issue — use --body-file for anything multi-line or with special shell characters
python3 scripts/tickets_api.py create <owner/repo> --title "Title" --body "short body"
python3 scripts/tickets_api.py create <owner/repo> --title "Title" --body-file /path/to/body.md

# Edit title and/or body (--body and --body-file are mutually exclusive)
python3 scripts/tickets_api.py edit <owner/repo> <issue_number> --title "New title"
python3 scripts/tickets_api.py edit <owner/repo> <issue_number> --body-file /path/to/body.md

# Close an issue
python3 scripts/tickets_api.py close <owner/repo> <issue_number>
```

## Practical notes

- For any body longer than a line or containing backticks/quotes, write it to a scratch file first (use the scratchpad directory) and pass `--body-file` rather than fighting shell escaping in `--body`.
- `GITHUB_TOKEN` only persists within a single Bash tool call — if creating/editing multiple issues across separate tool calls, re-export it (or better, do all the write calls in one shell invocation).
- The script is invoked directly (`python3 scripts/tickets_api.py ...`); it is not currently an importable package (no `scripts/__init__.py` yet — see issue #2 in this repo's tracker if that changes).
- Any non-2xx GitHub API response causes the script to print the status code + response body to stderr and exit 1 — surface that error text to the user rather than retrying blindly.
