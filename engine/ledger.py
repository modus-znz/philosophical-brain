#!/usr/bin/env python3
"""The append-only record the engine reasons from.

WHY A LEDGER AND NOT THE TRANSCRIPT

The integrity check has to answer one question at Stop: did a test actually run
this turn? The obvious source is `transcript_path` -- and it is the wrong one.
It is written asynchronously and lags the live turn, so the final tool call of
a turn may not be in the file yet when Stop fires. A gate that reads it would
go blind on precisely the turn where the last thing the model did was run the
tests: the honest case it exists to reward.

So the engine keeps its own record, written synchronously by the PostToolUse
hook as each tool returns. By the time Stop runs, everything Stop needs is
already on disk, because the same process wrote it.

TURN SCOPING

`prompt_id` is the turn key, measured rather than assumed: Stop carries the
same value as the PostToolUse rows of its own turn. That replaces the plan's
original approach of parsing the transcript for `origin.kind == "human"` -- the
lagging file again, for a value the payload hands over directly.

Two things the measurement also showed, which anything reading this must
respect. A turn does not always end in a Stop row -- two of five observed
prompt_id groups had none -- so nothing here may assume one arrives. And
`prompt_id` was absent from the earliest rows, before the probe recorded it;
rows without one are simply invisible to a turn query, never merged into it.

WHAT IS NEVER WRITTEN

Same discipline as probe.py, for the same reason: this is a plain unencrypted
file. Shapes, lengths and opaque ids only. Commands are truncated to their
head, file contents never appear, and the assistant's message is recorded as a
length. The single exception is the fired verdict's own `reason`, which is
machine-authored text the engine composed itself.
"""
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "graphify-out", "engine")

# graphify-out/* is gitignored except graph.json, so the ledger cannot reach
# the repo by accident. The plan said .brain/; this lives beside probe.jsonl
# instead, under an ignore rule that already exists and has been verified,
# rather than adding a second place to forget.
COMMAND_HEAD = 120
REASON_MAX = 220


def path_for(session_id):
    sid = "".join(c for c in (session_id or "unknown") if c.isalnum() or c in "-_")
    return os.path.join(OUT_DIR, "ledger-%s.jsonl" % (sid[:64] or "unknown"))


def append(session_id, row):
    """Write one row. Returns False rather than raising: a ledger that cannot
    be written must not be why a tool call fails."""
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(path_for(session_id), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        return True
    except Exception:
        return False


def record_tool(payload, verdicts):
    """One row per completed tool call, plus whatever the checks made of it."""
    ti = payload.get("tool_input")
    ti = ti if isinstance(ti, dict) else {}

    row = {
        "kind": "tool",
        "wall": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "prompt_id": payload.get("prompt_id"),
        "tool_name": payload.get("tool_name"),
        "tool_use_id": payload.get("tool_use_id"),
    }

    cmd = ti.get("command")
    if isinstance(cmd, str):
        row["command_head"] = cmd[:COMMAND_HEAD]
    fp = ti.get("file_path")
    if isinstance(fp, str):
        row["file_path"] = fp

    # Length only, never the text. Stop hands over the assistant's final
    # message -- the completion claim the integrity check reads -- and
    # recording what it says would put every answer this machine gives into a
    # plain unencrypted file.
    lam = payload.get("last_assistant_message")
    if isinstance(lam, str):
        row["last_assistant_message_len"] = len(lam)

    if verdicts:
        row["verdicts"] = verdicts
    return row


def read_rows(session_id):
    """Every row for a session. A malformed line is skipped, not fatal --
    a truncated write from a killed process must not blind the gate."""
    try:
        with open(path_for(session_id), encoding="utf-8") as fh:
            raw = fh.read()
    except Exception:
        return []
    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def evidence_for_turn(session_id, prompt_id, rows=None):
    """The commands run during one turn.

    Returns [] when prompt_id is absent rather than falling back to the whole
    session. The fallback looks harmless and is not: it would let a test run
    from an earlier turn excuse a claim made in this one, which is the exact
    falsification the check exists to catch.
    """
    if not prompt_id:
        return []
    out = []
    for row in (read_rows(session_id) if rows is None else rows):
        if row.get("prompt_id") != prompt_id:
            continue
        cmd = row.get("command_head")
        if isinstance(cmd, str):
            out.append(cmd)
    return out


def domains_seen(session_id, rows=None):
    """Domains that have already spoken this session.

    This is the once-per-domain budget, and it is structural: read from what
    was written, so it survives the hook process exiting between tool calls.
    """
    seen = set()
    for row in (read_rows(session_id) if rows is None else rows):
        for v in row.get("verdicts") or []:
            d = v.get("domain")
            if d:
                seen.add(d)
    return seen


def truncate_reason(text):
    text = (text or "").strip()
    return text[:REASON_MAX]
