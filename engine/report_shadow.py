#!/usr/bin/env python3
"""What the engine would have done, and whether that is yet worth believing.

    python3 engine/report_shadow.py            human-readable
    python3 engine/report_shadow.py --json     the same numbers, machine-shaped

Shadow mode is only useful if somebody reads it. Without this, `mode: "log"` is
a way of writing to a file nobody opens, and the promotion rule in
policy/checks.json -- twenty fires, no false positives, at most one fire per
session -- stays a comment rather than a gate.

WHAT THIS DELIBERATELY WILL NOT DO

It never says "promote". It reports what the evidence supports and stops, for
one reason: **it cannot see a false positive.** A false positive is a fire that
a human looked at and judged wrong, and no count of fires contains that
judgement. A tool that promoted a check on volume alone would be doing exactly
what the falsified-green-build check exists to catch -- turning an unverified
number into a claim -- inside the enforcer of that very principle.

So the false-positive column reads `unlabelled` until somebody labels it, and
a check with unlabelled fires is reported as NOT READY no matter how clean it
looks. That is the honest state, and it should be uncomfortable enough to
prompt the review rather than paper over it.
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LEDGER_DIR = os.path.join(ROOT, "graphify-out", "engine")
POLICY = os.path.join(ROOT, "policy", "checks.json")

# A fire the reviewer has judged. Written by hand into the ledger row, or kept
# alongside it; either way it is a human act, never inferred here.
LABEL_KEYS = ("false_positive", "correct")


def load_policy():
    try:
        with open(POLICY, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def ledger_files():
    try:
        names = sorted(os.listdir(LEDGER_DIR))
    except OSError:
        return []
    return [os.path.join(LEDGER_DIR, n) for n in names
            if n.startswith("ledger-") and n.endswith(".jsonl")]


def read(path):
    rows = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except OSError:
        pass
    return rows


def collect():
    stats = defaultdict(lambda: {
        "fires": 0, "sessions": set(), "errors": 0,
        "false_positives": 0, "confirmed": 0, "unlabelled": 0,
        "examples": [],
    })
    sessions = 0
    calls = 0
    over_budget = 0
    slowest = 0.0

    for path in ledger_files():
        sid = os.path.basename(path)[len("ledger-"):-len(".jsonl")]
        rows = read(path)
        if not rows:
            continue
        sessions += 1
        for row in rows:
            calls += 1
            ms = row.get("dispatch_ms")
            if isinstance(ms, (int, float)):
                slowest = max(slowest, ms)
            if row.get("over_budget"):
                over_budget += 1
            for v in row.get("verdicts") or []:
                cid = v.get("id") or "<unknown>"
                s = stats[cid]
                if v.get("error"):
                    s["errors"] += 1
                    continue
                s["fires"] += 1
                s["sessions"].add(sid)
                if v.get("false_positive"):
                    s["false_positives"] += 1
                elif v.get("correct"):
                    s["confirmed"] += 1
                else:
                    s["unlabelled"] += 1
                if len(s["examples"]) < 3 and v.get("reason"):
                    s["examples"].append(v["reason"])
    return stats, {"sessions": sessions, "calls": calls,
                   "over_budget": over_budget, "slowest_ms": slowest}


def assess(s, promo):
    """Why this check is not ready, in the order a reviewer would ask."""
    blockers = []
    if s["fires"] < promo.get("min_fires", 20):
        blockers.append("needs %d fires, has %d"
                        % (promo.get("min_fires", 20), s["fires"]))
    if s["unlabelled"]:
        blockers.append("%d fire(s) nobody has judged" % s["unlabelled"])
    if s["false_positives"] > promo.get("max_false_positives", 0):
        blockers.append("%d labelled false positive(s)" % s["false_positives"])
    n_sessions = len(s["sessions"]) or 1
    rate = s["fires"] / float(n_sessions)
    cap = promo.get("max_fires_per_session", 1.0)
    if rate > cap:
        blockers.append("fires %.1f times per session, cap is %.1f"
                        % (rate, cap))
    if s["errors"]:
        blockers.append("%d run(s) raised" % s["errors"])
    return blockers


def main(argv):
    as_json = "--json" in argv[1:]
    policy = load_policy()
    promo = policy.get("promotion") or {}
    modes = {c["id"]: c.get("mode") for c in policy.get("checks", [])}
    stats, totals = collect()

    if as_json:
        out = {"totals": totals, "checks": {}}
        for cid, s in stats.items():
            out["checks"][cid] = {
                "mode": modes.get(cid), "fires": s["fires"],
                "sessions": len(s["sessions"]), "errors": s["errors"],
                "false_positives": s["false_positives"],
                "confirmed": s["confirmed"], "unlabelled": s["unlabelled"],
                "blockers": assess(s, promo),
            }
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0

    if not totals["sessions"]:
        print("shadow report: no ledgers yet.")
        print("Nothing has been observed, so nothing here is known. Wire")
        print("engine/dispatch.py into ~/.claude/settings.json and work "
              "normally.")
        return 0

    print("shadow report: %d session(s), %d tool call(s)"
          % (totals["sessions"], totals["calls"]))
    print("dispatch: slowest %.1f ms, %d over budget"
          % (totals["slowest_ms"], totals["over_budget"]))
    print()

    if not stats:
        # Worth saying out loud. Silence from a check that has never run is
        # indistinguishable from silence from a check that is broken.
        print("No check has fired in any recorded session.")
        print("That is either a quiet corpus or a rule that cannot fire.")
        print("Confirm at least one predicate fires on a known positive "
              "before reading this as good news.")
        return 0

    for cid in sorted(stats):
        s = stats[cid]
        n_sessions = len(s["sessions"]) or 1
        print("%s  [mode=%s]" % (cid, modes.get(cid, "?")))
        print("    %d fire(s) across %d session(s)  (%.1f per session)"
              % (s["fires"], n_sessions, s["fires"] / float(n_sessions)))
        print("    judged: %d correct, %d false positive, %d unlabelled"
              % (s["confirmed"], s["false_positives"], s["unlabelled"]))
        blockers = assess(s, promo)
        if blockers:
            print("    NOT READY to leave shadow mode:")
            for b in blockers:
                print("      - %s" % b)
        else:
            print("    evidence supports promotion -- the decision is still "
                  "a human one")
        for ex in s["examples"]:
            print("    e.g. %s" % ex)
        print()

    print("A fire is not a false positive until somebody says it is. Label "
          "one by adding")
    print('"false_positive": true or "correct": true to its verdict in the '
          "ledger row.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
