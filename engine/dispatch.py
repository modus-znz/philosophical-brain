#!/usr/bin/env python3
"""The one hook entry point. Runs every check; in shadow mode, decides nothing.

    dispatch.py <EventName>      with the hook payload on stdin

WHAT IT IS ALLOWED TO COST

`policy/checks.json` sets `budgets.dispatch_ms` to 80, and this runs on every
tool call, so the budget is real in a way the commit-time hooks' is not. Two
rules keep it: never parse graphify-out/graph.json (54 ms by itself -- the
precompiled policy exists precisely so the hot path never needs the graph), and
never read a file the checks did not ask for. Each run records its own
duration in the ledger, so the budget is measured on real work rather than
asserted here.

WHAT IT IS ALLOWED TO SAY

Nothing, for now. Every check in policy/checks.json is `mode: "log"`, and the
promotion ratchet says a check leaves shadow mode on evidence from real work --
20 fires, no labelled false positives -- never on a hand-built test set. Until
then this writes verdicts to the ledger and exits silent.

That silence is also a hard compatibility requirement. One stray byte on
stdout breaks hook JSON parsing for every other hook on the event, including
the sudo -> sudo -A rewrite in ~/.claude/settings.json that this machine
already depends on. The emit paths are deliberately unwritten: code that
cannot run is code that cannot leak a byte.

FAIL OPEN, ALWAYS. Any exception exits 0 with empty stdout. A philosophy vault
must never be the reason a command will not run.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import ledger  # noqa: E402
import predicates  # noqa: E402

CHECKS = os.path.join(ROOT, "policy", "checks.json")
DOMAINS = os.path.join(ROOT, "policy", "domains.json")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def disabled(policy):
    """The kill switch, honored before anything else is read.

    An off switch that turns nothing off is worse than no off switch at all,
    so this is checked in the only component actually wired into settings.json,
    and it is checked first.
    """
    env = policy.get("kill_switch_env") or "BRAIN_ENGINE_OFF"
    if os.environ.get(env):
        return True
    f = policy.get("kill_switch_file") or "~/.claude/brain-engine-off"
    return os.path.isfile(os.path.expanduser(f))


def applies(chk, event, tool_name):
    if chk.get("event") != event:
        return False
    if chk.get("mode") == "off":
        return False
    tools = chk.get("tools")
    if tools and tool_name not in tools:
        return False
    return True


def build_context(payload, policy, session_id, rows):
    return {
        "cwd": payload.get("cwd") or os.getcwd(),
        "root": payload.get("cwd"),
        "evidence": ledger.evidence_for_turn(
            session_id, payload.get("prompt_id"), rows=rows),
        "seen_domains": ledger.domains_seen(session_id, rows=rows),
        "domains": load_json(DOMAINS, {}).get("domains", {}),
        "policy": policy,
    }


def run_checks(payload, policy, event, session_id, rows):
    tool_name = payload.get("tool_name")
    context = build_context(payload, policy, session_id, rows)
    verdicts = []

    for chk in policy.get("checks", []):
        if not applies(chk, event, tool_name):
            continue
        fn = getattr(predicates, chk.get("predicate") or "", None)
        if not callable(fn):
            # A check naming a predicate that does not exist is a policy bug,
            # and verify_policy.py fails the commit for it. At runtime it is
            # simply skipped -- the gate is the place to be loud, not the hook.
            continue
        try:
            hit = fn(payload, chk.get("params") or {}, context)
        except Exception as exc:
            verdicts.append({"id": chk.get("id"), "error": type(exc).__name__})
            continue
        if not hit:
            continue
        v = {
            "id": chk.get("id"),
            "principle": chk.get("principle"),
            "mode": chk.get("mode"),
            "tier": chk.get("tier"),
            "reason": ledger.truncate_reason(hit.get("reason")),
            "would_have": chk.get("mode"),
        }
        for k in ("pattern", "segment", "claim", "evidence", "domain",
                  "path", "misconfigured"):
            if k in hit:
                v[k] = hit[k]
        verdicts.append(v)

        # Once a domain has spoken it is spent for the session, including
        # within this same dispatch. Reading the budget only from disk would
        # let two checks on one domain both fire before either was written.
        if hit.get("domain"):
            context["seen_domains"] = set(context["seen_domains"]) | {
                hit["domain"]}
    return verdicts


def main():
    event = sys.argv[1] if len(sys.argv) > 1 else "?"
    started = time.monotonic()
    # Drain stdin before deciding anything: exiting on a pipe the caller is
    # still writing to earns an EPIPE for a hook that promised to be inert.
    raw = sys.stdin.read()

    policy = load_json(CHECKS, {})
    if not policy.get("enabled", True) or disabled(policy):
        return 0

    try:
        payload = json.loads(raw)
    except Exception:
        return 0

    # The loop guard. A Stop hook that blocks, on a turn that was itself
    # started by a Stop hook blocking, never terminates. This is the likeliest
    # way to ship something broken, so it returns before any check runs.
    if payload.get("stop_hook_active"):
        return 0

    session_id = payload.get("session_id")
    rows = ledger.read_rows(session_id)
    verdicts = run_checks(payload, policy, event, session_id, rows)

    row = ledger.record_tool(payload, verdicts)
    row["kind"] = "tool" if event == "PostToolUse" else event.lower()
    row["event"] = event
    row["dispatch_ms"] = round((time.monotonic() - started) * 1000, 2)
    budget = (policy.get("budgets") or {}).get("dispatch_ms")
    if budget and row["dispatch_ms"] > budget:
        # Recorded, never enforced. A hook that killed itself for being slow
        # would fail closed, which is the one thing this must never do.
        row["over_budget"] = True
    ledger.append(session_id, row)

    # Shadow mode. Nothing is emitted, by construction rather than by branch.
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BaseException:
        sys.exit(0)
