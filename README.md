# 🌙 Nightly NeetCode 150

A personal practice loop: every night you get an **email** with the next problem
in the NeetCode 150 (topic-ordered, **zero repeats**), solve it, then mark it done
from the CLI. Tags, difficulty, links, and your own notes ride along.

```
GitHub Actions cron  ──nightly──▶  📧 email reminder  ──▶  you solve it
        ▲                                                      │
        └──────────── state.json (source of truth) ◀── lc done ┘
```

**Tonight's problem is deterministic:** the lowest-id problem you haven't finished.
Because `done` only ever grows and the list is pre-sorted in NeetCode's roadmap
order, you march through all 150 in sequence and a problem *physically cannot*
repeat until you've cleared the list. No scheduler, no random state to drift.

---

## Layout

| File | What it does |
|------|--------------|
| `data/neetcode150.json` | The 150 problems, ordered, with topic/tags/difficulty/links (sourced from `neetcode-gh/leetcode`). |
| `core.py` | Shared engine: state, the picker, streaks, progress. Used by both the CLI and the emailer so they never disagree. |
| `lc.py` | Your CLI (`typer` + `rich`). |
| `nightly.py` | Builds + sends the reminder email. Pure stdlib. |
| `.github/workflows/nightly.yml` | The cron that runs `nightly.py`. |
| `state.json` | Your progress. Created on first `lc done`, committed back to the repo. |

---

## CLI

```bash
pip install -r requirements.txt

python lc.py today          # tonight's problem: tags, difficulty, links, notes
python lc.py done           # mark it done (logs the date) + auto commit/push
python lc.py flag           # mark it hard -> resurfaces after the main pass
python lc.py note "..."     # attach a note to tonight's problem
python lc.py notes --all    # review every note you've taken
python lc.py progress       # overall %, per-topic breakdown, streak
python lc.py sync           # manually commit/push state.json
```

Tip — drop an alias in your shell so it's just `lc`:
```bash
alias lc="python ~/dev/leetcode-nightly/lc.py"
```

**The review pass:** once all 150 are done, the picker automatically serves up
the problems you `flag`ged, one per night, until those are cleared too.

---

## Email setup (one time, ~5 min)

The cron sends mail through Gmail SMTP using an **App Password** (not your real
password — that won't work with 2FA on).

1. Enable 2-Step Verification on the Google account, then create an App Password:
   <https://myaccount.google.com/apppasswords> → pick "Mail" → copy the 16-char code.
2. In the GitHub repo: **Settings → Secrets and variables → Actions → New repository secret**, add three:
   - `GMAIL_USER` — the sending address (e.g. `dbueno.nyc@gmail.com`)
   - `GMAIL_APP_PASSWORD` — the 16-char app password (no spaces)
   - `NOTIFY_EMAIL` — where the reminder goes (can be the same address)
3. Test it now without waiting for night: **Actions tab → Nightly LeetCode reminder → Run workflow**.

### When does it fire?

Cron is **UTC** and ignores daylight saving. Default is `0 23 * * *`:
- **7:00 PM EDT** (summer) / **6:00 PM EST** (winter).

Change the hour in `.github/workflows/nightly.yml` to move it.

---

## Daily loop

1. 🌙 Email lands → open the problem.
2. Solve it (no AI — that's the point).
3. `lc done` (add `lc flag` if it was rough, `lc note "..."` to leave yourself a breadcrumb).
4. State pushes to the repo → tomorrow's email serves the next one.

That's it. 150 nights to the finish line, plus a review lap on the hard ones.
