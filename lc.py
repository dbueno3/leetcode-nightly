#!/usr/bin/env python3
"""lc -- nightly NeetCode 150 practice CLI.

Commands:
    lc today              show tonight's problem (tags, difficulty, links, notes)
    lc done [--no-push]   mark tonight's problem complete (logs the date)
    lc flag               flag tonight's problem as hard (resurfaced after the main pass)
    lc note "text"        attach a note to tonight's problem
    lc notes [--all]      show notes for tonight's problem (or every note with --all)
    lc progress           overall + per-topic progress and current streak
    lc sync               commit & push state.json so the nightly email stays in sync
"""
from __future__ import annotations

import subprocess

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

import core

app = typer.Typer(add_completion=False, help="Nightly NeetCode 150 practice.")
console = Console()

DIFF_COLOR = {"Easy": "green", "Medium": "yellow", "Hard": "red"}


def _git_push() -> tuple[bool, str]:
    try:
        subprocess.run(["git", "add", "state.json"], cwd=core.ROOT, check=True,
                       capture_output=True)
        r = subprocess.run(["git", "commit", "-m", "chore: update practice state"],
                           cwd=core.ROOT, capture_output=True, text=True)
        if r.returncode != 0 and "nothing to commit" in (r.stdout + r.stderr):
            return True, "nothing to commit"
        subprocess.run(["git", "push"], cwd=core.ROOT, check=True, capture_output=True)
        return True, "pushed"
    except subprocess.CalledProcessError as e:
        return False, (e.stderr or b"").decode() if isinstance(e.stderr, bytes) else str(e)
    except FileNotFoundError:
        return False, "git not found"


def _render_problem(p: dict, state: dict, data: dict) -> Panel:
    review = core.in_review_phase(data, state)
    diff = p["difficulty"]
    pos = f"{len(state['done'])}/{len(data['problems'])}"
    header = Text()
    header.append(f"#{p['id']}  ", style="bold cyan")
    header.append(p["name"], style="bold white")

    body = Text()
    body.append("Topic     ", style="dim")
    body.append(f"{p['topic']}  (#{p['topic_index']} in topic)\n")
    body.append("Tags      ", style="dim")
    body.append(", ".join(p["tags"]) + "\n")
    body.append("Difficulty", style="dim")
    body.append("  ")
    body.append(diff, style=f"bold {DIFF_COLOR.get(diff, 'white')}")
    body.append("\n")
    body.append("LeetCode  ", style="dim")
    body.append(p["leetcode"] + "\n", style="blue underline")
    if p.get("video"):
        body.append("Solution  ", style="dim")
        body.append(p["video"], style="blue underline")
    flagged = " 🚩" if p["id"] in state["flagged"] else ""
    notes = core.notes_for(state, p["id"])
    if notes:
        body.append("\n\nNotes\n", style="bold")
        for n in notes:
            body.append(f"  • {n}\n", style="italic")

    title = "📋 Review pass" if review else f"🌙 Tonight's problem · {pos} done"
    return Panel(Text.assemble(header, "\n\n", body), title=title + flagged,
                 border_style="cyan", padding=(1, 2))


@app.command()
def today():
    """Show tonight's problem."""
    data, state = core.load_data(), core.load_state()
    p = core.today_problem(data, state)
    if p is None:
        console.print(Panel("🎉 All 150 done and every flagged problem reviewed. "
                            "You've cleared the list.", border_style="green"))
        raise typer.Exit()
    console.print(_render_problem(p, state, data))


@app.command()
def done(no_push: bool = typer.Option(False, "--no-push", help="Don't auto commit/push.")):
    """Mark tonight's problem complete."""
    data, state = core.load_data(), core.load_state()
    p = core.today_problem(data, state)
    if p is None:
        console.print("[green]Nothing left to do — list cleared.[/green]")
        raise typer.Exit()
    review = core.in_review_phase(data, state)
    core.mark_done(state, p["id"], review=review)
    core.save_state(state)
    s = core.streak(state)
    console.print(f"[green]✓[/green] Marked [bold]#{p['id']} {p['name']}[/bold] done. "
                  f"🔥 {s}-day streak.")
    nxt = core.today_problem(data, state)
    if nxt:
        console.print(f"[dim]Next up:[/dim] #{nxt['id']} {nxt['name']} "
                      f"[dim]({nxt['topic']} · {nxt['difficulty']})[/dim]")
    if not no_push:
        ok, msg = _git_push()
        style = "dim" if ok else "yellow"
        console.print(f"[{style}]git: {msg}[/{style}]")


@app.command()
def flag():
    """Flag tonight's problem as hard (resurfaced in the review pass)."""
    data, state = core.load_data(), core.load_state()
    p = core.today_problem(data, state)
    if p is None:
        raise typer.Exit()
    core.flag(state, p["id"])
    core.save_state(state)
    console.print(f"🚩 Flagged [bold]#{p['id']} {p['name']}[/bold] for review.")


@app.command()
def note(text: str = typer.Argument(..., help="Note text to attach.")):
    """Attach a note to tonight's problem."""
    data, state = core.load_data(), core.load_state()
    p = core.today_problem(data, state)
    if p is None:
        raise typer.Exit()
    core.add_note(state, p["id"], text)
    core.save_state(state)
    console.print(f"📝 Note added to [bold]#{p['id']} {p['name']}[/bold].")


@app.command()
def notes(all: bool = typer.Option(False, "--all", help="Show every note.")):
    """Show notes for tonight's problem, or all notes with --all."""
    data, state = core.load_data(), core.load_state()
    by_id = core.problems_by_id()
    if all:
        if not state["notes"]:
            console.print("[dim]No notes yet.[/dim]")
            raise typer.Exit()
        for pid, ns in sorted(state["notes"].items(), key=lambda x: int(x[0])):
            name = by_id[int(pid)]["name"]
            console.print(f"[bold cyan]#{pid} {name}[/bold cyan]")
            for n in ns:
                console.print(f"  • {n}")
        raise typer.Exit()
    p = core.today_problem(data, state)
    ns = core.notes_for(state, p["id"]) if p else []
    if not ns:
        console.print("[dim]No notes on tonight's problem yet.[/dim]")
    else:
        console.print(f"[bold cyan]#{p['id']} {p['name']}[/bold cyan]")
        for n in ns:
            console.print(f"  • {n}")


@app.command()
def progress():
    """Show overall + per-topic progress and current streak."""
    data, state = core.load_data(), core.load_state()
    total = len(data["problems"])
    done = len(state["done"])
    pct = done / total * 100
    bar_len = 30
    filled = int(bar_len * done / total)
    bar = "█" * filled + "░" * (bar_len - filled)
    console.print(Panel(
        f"[bold]{done}/{total}[/bold]  ({pct:.0f}%)   🔥 {core.streak(state)}-day streak"
        f"\n[cyan]{bar}[/cyan]",
        title="Overall", border_style="cyan"))

    table = Table(show_header=True, header_style="bold")
    table.add_column("Topic")
    table.add_column("Done", justify="right")
    for row in core.topic_progress(data, state):
        d, t = row["done"], row["total"]
        style = "green" if d == t else ("yellow" if d else "dim")
        table.add_row(row["topic"], f"[{style}]{d}/{t}[/{style}]")
    console.print(table)
    if state["flagged"]:
        rem = [i for i in state["flagged"] if i not in state["review_done"]]
        console.print(f"[red]🚩 {len(state['flagged'])} flagged[/red] "
                      f"[dim]({len(rem)} still to review)[/dim]")


@app.command()
def sync():
    """Commit & push state.json so the nightly email stays in sync."""
    ok, msg = _git_push()
    console.print(f"[{'green' if ok else 'yellow'}]git: {msg}[/{'green' if ok else 'yellow'}]")


if __name__ == "__main__":
    app()
