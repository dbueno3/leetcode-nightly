#!/usr/bin/env python3
"""Send the nightly NeetCode 150 reminder email.

Runs in GitHub Actions on a cron. Reads the committed state.json, figures out
tonight's problem (same logic as the CLI), and emails it. Does NOT mutate state
-- the problem only advances when you run `lc done`, so the email never gets
ahead of you.

Required env vars (set as GitHub Actions secrets):
    GMAIL_USER          the sending Gmail address
    GMAIL_APP_PASSWORD  a Gmail App Password (not your normal password)
    NOTIFY_EMAIL        where to send the reminder (can equal GMAIL_USER)
"""
from __future__ import annotations

import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import core

DIFF_COLOR = {"Easy": "#16a34a", "Medium": "#ca8a04", "Hard": "#dc2626"}


def build_html(p: dict, state: dict, data: dict) -> str:
    done = len(state["done"])
    total = len(data["problems"])
    pct = round(done / total * 100)
    streak = core.streak(state)
    review = core.in_review_phase(data, state)
    diff = p["difficulty"]
    color = DIFF_COLOR.get(diff, "#334155")
    tags = "".join(
        f'<span style="display:inline-block;background:#1e293b;color:#cbd5e1;'
        f'padding:3px 10px;border-radius:12px;font-size:12px;margin-right:6px;">{t}</span>'
        for t in p["tags"]
    )
    notes = core.notes_for(state, p["id"])
    notes_html = ""
    if notes:
        items = "".join(f"<li style='margin-bottom:4px;'>{n}</li>" for n in notes)
        notes_html = (
            f'<div style="margin-top:16px;padding:12px 16px;background:#0f172a;'
            f'border-left:3px solid #38bdf8;border-radius:4px;">'
            f'<div style="color:#94a3b8;font-size:12px;text-transform:uppercase;'
            f'letter-spacing:1px;margin-bottom:6px;">Your notes</div>'
            f'<ul style="margin:0;padding-left:18px;color:#e2e8f0;">{items}</ul></div>'
        )
    video = ""
    if p.get("video"):
        video = (f'&nbsp;&nbsp;·&nbsp;&nbsp;<a href="{p["video"]}" '
                 f'style="color:#38bdf8;text-decoration:none;">▶ NeetCode solution</a>')
    label = "🔁 Review pass" if review else f"🌙 Night {done + 1} of {total}"

    return f"""\
<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:560px;
margin:0 auto;background:#0b1120;border-radius:16px;overflow:hidden;
border:1px solid #1e293b;">
  <div style="padding:20px 24px;background:#111827;border-bottom:1px solid #1e293b;">
    <div style="color:#64748b;font-size:13px;letter-spacing:1px;text-transform:uppercase;">
      {label}</div>
    <div style="color:#f1f5f9;font-size:14px;margin-top:4px;">
      Time for tonight's problem 💪</div>
  </div>
  <div style="padding:24px;">
    <div style="color:#475569;font-size:13px;">#{p['id']} · {p['topic']}
      (#{p['topic_index']} in topic)</div>
    <div style="color:#f8fafc;font-size:24px;font-weight:700;margin:6px 0 14px;">
      {p['name']}</div>
    <div style="margin-bottom:14px;">
      <span style="display:inline-block;background:{color};color:#fff;padding:3px 12px;
      border-radius:12px;font-size:12px;font-weight:600;margin-right:6px;">{diff}</span>
      {tags}
    </div>
    <a href="{p['leetcode']}" style="display:inline-block;background:#38bdf8;color:#06121f;
    font-weight:700;padding:12px 22px;border-radius:8px;text-decoration:none;">
      Solve on LeetCode →</a>
    <span style="font-size:13px;color:#64748b;">{video}</span>
    {notes_html}
  </div>
  <div style="padding:16px 24px;background:#0f172a;border-top:1px solid #1e293b;
  color:#94a3b8;font-size:13px;">
    <strong style="color:#e2e8f0;">{done}/{total}</strong> done ({pct}%)
    &nbsp;·&nbsp; 🔥 <strong style="color:#fb923c;">{streak}</strong>-day streak
    <div style="margin-top:6px;color:#475569;font-size:12px;">
      Finish it, then run <code style="color:#cbd5e1;">lc done</code>
      (add <code style="color:#cbd5e1;">lc flag</code> if it was rough).</div>
  </div>
</div>"""


def main() -> int:
    user = os.environ.get("GMAIL_USER")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    to = os.environ.get("NOTIFY_EMAIL") or user
    if not (user and pw and to):
        print("Missing GMAIL_USER / GMAIL_APP_PASSWORD / NOTIFY_EMAIL", file=sys.stderr)
        return 1

    data, state = core.load_data(), core.load_state()
    p = core.today_problem(data, state)
    if p is None:
        subject = "🎉 NeetCode 150 — list cleared!"
        html = ('<div style="font-family:sans-serif;padding:24px;">'
                "You've finished all 150 and reviewed every flagged problem. "
                "Nothing to send tonight.</div>")
    else:
        tag = "Review" if core.in_review_phase(data, state) else f"#{p['id']}"
        subject = f"🌙 LeetCode tonight: {p['name']} ({p['difficulty']}) · {tag}"
        html = build_html(p, state, data)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to
    msg.attach(MIMEText("Open in an HTML-capable client to see tonight's problem.", "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(user, pw)
        server.sendmail(user, [to], msg.as_string())
    print(f"Sent: {subject}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
