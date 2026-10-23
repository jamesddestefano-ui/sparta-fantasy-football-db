#!/usr/bin/env python3
"""Undo stale overwrites of the Grok Pulse mirror files (AGENTS.md rules 21-23, 27).

An external mirror job (grok.me /api/pulse, stuck on its 2026-10-19 pass) keeps
overwriting intelligence/grok_pulse_latest.json with an older pass and rewriting the
append-only intelligence/grok_pulse_history.jsonl down to one line. This script compares
the current files with a trusted base commit and repairs only those two problems:

  * latest.json: if the working copy's completedAt is older than the base's, the base
    version is restored (a newer or equal pass is always kept).
  * history.jsonl: the current latest pass is appended if missing, so Grok jobs only
    need to write latest.json.
  * history.jsonl: history is append-only. Every pass in the base is kept, in order;
    passes in the working copy that the base doesn't have (by completedAt) are appended.

It never touches anything outside those two files and never invents a pass.

  python scripts/pulse_guard.py --base <sha>      # repair the working tree; prints what changed
Exit code 0 always; prints CHANGED or UNCHANGED.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LATEST = "intelligence/grok_pulse_latest.json"
HISTORY = "intelligence/grok_pulse_history.jsonl"


def git_show(ref: str, path: str) -> str | None:
    r = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def completed_at(text: str | None) -> str:
    if not text:
        return ""
    try:
        return str(json.loads(text).get("completedAt") or "")
    except (ValueError, AttributeError):
        return ""


def pass_key(line: str) -> str:
    try:
        d = json.loads(line)
        return f"{d.get('product', '')}|{d.get('completedAt', '')}"
    except ValueError:
        return line


def repair_latest(base_text: str | None, cur_text: str | None) -> str | None:
    """Return the text to write, or None if the current file should stay."""
    if base_text is None:
        return None
    if completed_at(cur_text) < completed_at(base_text):
        return base_text
    return None


def is_pass(line: str) -> bool:
    try:
        return isinstance(json.loads(line), dict)
    except ValueError:
        return False


def repair_history(base_text: str | None, cur_text: str | None) -> str | None:
    raw_cur = [l for l in (cur_text or "").splitlines() if l.strip()]
    cur = [l for l in raw_cur if is_pass(l)]  # drop junk such as "PLACEHOLDER..." or "$(cat ...)"
    junk = len(cur) != len(raw_cur)
    base = [l for l in (base_text or "").splitlines() if l.strip() and is_pass(l)]
    if not base:
        return "\n".join(cur) + "\n" if junk else None
    if cur[: len(base)] == base or {pass_key(l) for l in base} <= {pass_key(l) for l in cur}:
        return "\n".join(cur) + "\n" if junk else None  # nothing lost
    seen = {pass_key(l) for l in base}
    merged = list(base)
    for l in cur:
        k = pass_key(l)
        if k not in seen:
            merged.append(l)
            seen.add(k)
    return "\n".join(merged) + "\n"


def append_latest(latest_text: str | None, history_text: str | None) -> str | None:
    """Append the current latest pass to history if history doesn't have it yet.

    Grok jobs write only latest.json; the guard keeps history append-only from it.
    """
    if not latest_text:
        return None
    try:
        d = json.loads(latest_text)
    except ValueError:
        return None
    if d.get("status") != "live" or not d.get("completedAt"):
        return None  # rule 23: only live, completed passes
    line = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    lines = [l for l in (history_text or "").splitlines() if l.strip()]
    if pass_key(line) in {pass_key(l) for l in lines}:
        return None
    return "\n".join(lines + [line]) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="trusted commit to compare against")
    a = ap.parse_args()
    changed = []
    for path, fn in ((LATEST, repair_latest), (HISTORY, repair_history)):
        p = ROOT / path
        cur = p.read_text() if p.exists() else None
        new = fn(git_show(a.base, path), cur)
        if new is not None and new != cur:
            p.write_text(new)
            changed.append(path)
    lp, hp = ROOT / LATEST, ROOT / HISTORY
    hist = hp.read_text() if hp.exists() else None
    new = append_latest(lp.read_text() if lp.exists() else None, hist)
    if new is not None and new != hist:
        hp.write_text(new)
        if HISTORY not in changed:
            changed.append(HISTORY)
    if changed:
        print("CHANGED " + " ".join(changed))
    else:
        print("UNCHANGED")


if __name__ == "__main__":
    main()
