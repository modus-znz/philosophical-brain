#!/usr/bin/env python3
"""Phase 0 instrument. Observes hook events; changes nothing.

Wired as:  probe.py <EventName>   with the hook payload on stdin.

It exists to answer three questions with evidence instead of inference, before
a single line of enforcement is written:

  1. THE RACE. Does PostToolUse for the last tool call of a turn complete
     before Stop fires? The integrity check wants to ask "did a test actually
     run this turn?" If the two race, a turn whose final action WAS running
     the tests has no record of it when Stop reads the ledger -- and the check
     false-blocks on precisely the honest case it exists to reward. Every row
     carries a wall clock and a monotonic-ns stamp so the ordering is a
     measurement, not a guess.

  2. THE STOP PAYLOAD. Which keys actually arrive on Stop -- transcript_path,
     stop_hook_active, session_id, cwd -- and in what shape.

  3. THE INJECTION CHANNEL. Whether PostToolUse.additionalContext reaches the
     model at all. Tier 2 -- every advisory directive the vault would ever
     offer -- is worth nothing if this channel is silent, so it is measured
     rather than assumed. See ARMING THE NONCE below.

Contract, in priority order:
  - FAIL OPEN, ALWAYS. Any exception exits 0 with empty stdout. A philosophy
    vault must never be why a command will not run.
  - EMPTY STDOUT unless a nonce is explicitly armed. One stray byte breaks
    hook JSON parsing for every other hook on the event -- including the
    sudo -> sudo -A rewrite that ~/.claude/settings.json already depends on.
    (That one is on PreToolUse, which this never writes to.)

ARMING THE NONCE
  Write a token to ~/.claude/brain-nonce. The next PostToolUse consumes it and
  returns it as additionalContext. Single-shot by construction: the file is
  DELETED BEFORE the token is emitted, never after. Deleting first can only
  lose one test; emitting first, then crashing, would re-inject on every tool
  call for the rest of the session -- an inert probe turned into a stuck one.

  The token is never written to probe.jsonl -- only its length. A test whose
  expected answer sits in a file the model can read proves nothing.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "graphify-out", "engine")
OUT = os.path.join(OUT_DIR, "probe.jsonl")

# Payload values worth keeping. The full tool_input is deliberately NOT
# recorded: it carries file contents and command lines, and this file is a
# plain unencrypted log. Shape and size are enough to answer the questions.
#
# prompt_id is the find that changes the ledger design. The plan scoped a turn
# by parsing the transcript for origin.kind == "human" -- reading a file that is
# written asynchronously and lags the live turn. PostToolUse hands us a turn key
# directly. All three added here are opaque identifiers and a duration; none
# carry content.
KEEP = ("hook_event_name", "session_id", "cwd", "transcript_path",
        "tool_name", "stop_hook_active", "permission_mode",
        "prompt_id", "tool_use_id", "duration_ms")


def summarize(value, depth=0):
    """Shape, not content."""
    if depth > 2:
        return "..."
    if isinstance(value, dict):
        return {k: summarize(v, depth + 1) for k, v in list(value.items())[:12]}
    if isinstance(value, list):
        return ["<%d items>" % len(value)]
    if isinstance(value, str):
        return "<str %d>" % len(value)
    return value


def disabled():
    """The kill switch policy/checks.json advertises, honored by the only
    component that is actually wired into settings.json. An off switch that
    turns nothing off is worse than no off switch at all.

        BRAIN_ENGINE_OFF=1              one command, one session
        touch ~/.claude/brain-engine-off   this machine, until removed
    """
    if os.environ.get("BRAIN_ENGINE_OFF"):
        return True
    return os.path.isfile(os.path.expanduser("~/.claude/brain-engine-off"))


def take_nonce():
    """Consume ~/.claude/brain-nonce and return it, or None.

    Removed before it is returned -- see ARMING THE NONCE. Any failure to
    remove it means it is not returned either, so a file that cannot be
    deleted can never be injected twice.
    """
    path = os.path.expanduser("~/.claude/brain-nonce")
    try:
        with open(path, encoding="utf-8") as fh:
            token = fh.read().strip()
    except Exception:
        return None
    try:
        os.remove(path)
    except Exception:
        return None
    return token or None


def main():
    event = sys.argv[1] if len(sys.argv) > 1 else "?"
    # Drain stdin before deciding anything: exiting on a pipe the caller is
    # still writing to earns an EPIPE for a hook that promised to be inert.
    raw = sys.stdin.read()

    if disabled():
        return 0

    try:
        payload = json.loads(raw)
    except Exception:
        payload = {}

    row = {
        "event": event,
        "wall": time.time(),
        "mono_ns": time.monotonic_ns(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "pid": os.getpid(),
        "raw_bytes": len(raw),
        "keys": sorted(payload.keys()),
    }
    for k in KEEP:
        if k in payload:
            row[k] = payload[k]

    # Enough of the tool call to tell a test run from an edit, without
    # recording what was edited.
    ti = payload.get("tool_input")
    if isinstance(ti, dict):
        row["tool_input_keys"] = sorted(ti.keys())
        cmd = ti.get("command")
        if isinstance(cmd, str):
            row["command_head"] = cmd[:120]
        fp = ti.get("file_path")
        if isinstance(fp, str):
            row["file_path"] = fp

    tr = payload.get("tool_response")
    if tr is not None:
        row["tool_response_shape"] = summarize(tr)

    # Length only, never the text. Stop delivers the assistant's final message
    # in the payload -- the completion claim the integrity gate has to read,
    # without going near the lagging transcript. Recording how long it is
    # confirms the field is substantive; recording what it says would put every
    # answer this machine gives into a plain unencrypted log.
    lam = payload.get("last_assistant_message")
    if isinstance(lam, str):
        row["last_assistant_message_len"] = len(lam)

    # Consume the nonce before logging, so the row records the attempt.
    nonce = None
    if event == "PostToolUse":
        nonce = take_nonce()
    if nonce is not None:
        row["injected"] = True
        row["nonce_len"] = len(nonce)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")

    if nonce is not None:
        # Built whole, then written once. A partial write here would hand the
        # harness half a JSON document on an event it parses strictly.
        out = json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                "BRAIN_PROBE_NONCE=%s -- Phase 0 injection test. If you can "
                "read this token, PostToolUse.additionalContext reaches the "
                "model and Tier 2 advisory injection is viable. Report the "
                "token verbatim." % nonce),
        }})
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BaseException:
        # Bare BaseException on purpose: SystemExit and KeyboardInterrupt
        # included. Nothing this script can hit is worth blocking a user's
        # tool call over, and it has no verdict to lose by staying silent.
        sys.exit(0)
