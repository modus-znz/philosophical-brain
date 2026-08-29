#!/usr/bin/env python3
"""The predicates named by policy/checks.json.

Four rules, one function each. `verify_policy.py` extracts the names with
`^def\\s+(\\w+)` at column zero and asserts every check names a real one, so
these stay module-level functions -- a class, a closure or a `partial` is
invisible to that gate.

CONTRACT

    predicate(payload, params, context) -> verdict dict | None

    payload  the raw hook payload, as the harness delivered it
    params   the check's `params` block from policy/checks.json
    context  what the predicate cannot see for itself, supplied by the
             dispatcher: {"cwd", "evidence", "seen_domains", "root"}

    None means the rule did not fire. A dict means it did, and carries
    `reason` -- the sentence a human reads -- plus whatever detail made the
    call reproducible.

Two disciplines hold this together:

  1. PURE. A predicate reads its arguments and nothing else. No ledger reads,
     no clock, no environment. `completion_claim_without_evidence` needs to
     know whether a test ran this turn, and that is a prompt_id-filtered
     ledger query -- so the dispatcher runs it and hands the answer in
     `context["evidence"]`. The moment a predicate fetches its own evidence it
     stops being testable offline, and offline testability is the only reason
     the nonce work could be trusted before it ever ran live.

  2. NO PATTERNS HERE. Every regex lives in policy/checks.json, where
     verify_policy.py already validates it and where a change is visible as a
     policy diff. Copying one into this file would recreate exactly the
     source-of-truth drift the binding gate exists to prevent.
"""
import os
import re

# `a && b`, `a || b`, `a | b`, `a; b`, and newlines in a heredoc-free script.
# The patterns in checks.json are ^-anchored on purpose -- matching them
# against a whole command string would let `echo hi && rm -rf /` through,
# because `^rm` only ever matches at position 0.
_SEGMENTS = re.compile(r"\|\||&&|[|;&\n]")

# A leading `sudo` (with its flags) hides the command word from a ^-anchored
# pattern. ~/.claude/settings.json rewrites `sudo` to `sudo -A` on this
# machine, so this is the normal shape of a privileged command here, not an
# edge case: `sudo rm -rf /srv` must fire exactly as `rm -rf /srv` does.
_PRIVILEGE = re.compile(r"^(sudo|doas)\b(\s+-\w+)*\s+")

_FLAGS = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}


def _compile(pattern, flags=""):
    f = 0
    for ch in flags or "":
        f |= _FLAGS.get(ch, 0)
    return re.compile(pattern, f)


def _segments(command):
    """Split a shell command into the pieces a ^-anchored pattern should see."""
    out = []
    for raw in _SEGMENTS.split(command or ""):
        seg = raw.strip()
        if not seg:
            continue
        seg = _PRIVILEGE.sub("", seg).strip()
        if seg:
            out.append(seg)
    return out


def _args(segment):
    """Non-flag arguments after the command word. Crude on purpose."""
    parts = segment.split()[1:]
    return [p.strip("'\"") for p in parts if not p.startswith("-")]


def unrecoverable_bash(payload, params, context):
    """A command whose effect no reflog, snapshot or undo can walk back.

    Deliberately narrow. `git reset --hard` and `git stash drop` are absent
    from the pattern set because both are recoverable and both fire constantly
    in honest work; every false prompt spends trust this engine will need for
    the case that actually matters.
    """
    ti = payload.get("tool_input")
    if not isinstance(ti, dict):
        return None
    command = ti.get("command")
    if not isinstance(command, str) or not command.strip():
        return None

    seg_allow = [re.compile(p) for p in params.get("segment_allowlist", [])]
    path_allow = params.get("path_allowlist", [])
    patterns = [(p["name"], _compile(p["re"], p.get("flags", "")))
                for p in params.get("patterns", [])]

    for segment in _segments(command):
        # `--dry-run` and `--force-with-lease` carry no anchor of their own, so
        # this is a search, not a match.
        if any(a.search(segment) for a in seg_allow):
            continue
        for name, rx in patterns:
            if not rx.search(segment):
                continue
            # A build directory is not a loss. Suppress only when EVERY path
            # argument is disposable -- one real target among them and the
            # command is still unrecoverable.
            args = _args(segment)
            if args and all(any(tok in a for tok in path_allow) for a in args):
                continue
            return {
                "reason": "%s -- no snapshot recorded this turn" % name,
                "pattern": name,
                "segment": segment[:120],
            }
    return None


def _sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


def completion_claim_without_evidence(payload, params, context):
    """Claimed green, ran nothing.

    The vault directive is "never falsify a green build, a coverage number, or
    a status report", and this is the only mechanical piece of it: the claim is
    a regex over the final assistant message, the evidence is a matching tool
    call in the same turn. Both are literal facts. Whether the tests were any
    good is not a question this can ask, and it does not pretend to.

    DISARMS where there is no test infrastructure. A demand the model cannot
    satisfy is an invitation to fabricate a test run -- which is the very
    violation the check exists to catch.
    """
    message = payload.get("last_assistant_message")
    if not isinstance(message, str) or not message.strip():
        return None

    cwd = context.get("cwd") or ""
    infra = params.get("arm_if_test_infra", [])
    if not any(os.path.exists(os.path.join(cwd, name)) for name in infra):
        return None

    claims = [_compile(p, "i") for p in params.get("claim_patterns", [])]
    hedges = [_compile(p, "i") for p in params.get("hedge_patterns", [])]

    hit = None
    for sentence in _sentences(message):
        if not any(rx.search(sentence) for rx in claims):
            continue
        # Hedge scope is the sentence, not the message. "tests pass locally
        # per their report" and "should make the tests pass once you run them"
        # were both measured false positives, and both hedge in place. Scoping
        # to the whole message instead would let one honest caveat anywhere
        # excuse a bare claim everywhere.
        if any(rx.search(sentence) for rx in hedges):
            continue
        hit = sentence
        break
    if hit is None:
        return None

    needles = params.get("evidence_bash", [])
    for ran in context.get("evidence", []):
        low = (ran or "").lower()
        if any(n.lower() in low for n in needles):
            return None

    return {
        "reason": "stated tests pass; no test run recorded this turn",
        "claim": hit[:220],
    }


def disabled_or_vacuous_test(payload, params, context):
    """A test that cannot fail.

    An unconditional skip with no reason, or a body whose only assertion is a
    tautology. Both are syntactic facts about the string being written.

    `skipif(...)` and `xfail(strict=True)` are correct practice and excluded --
    `skip` matching the `skipif` prefix is the single easiest way to get this
    check wrong, and it did, on real conditional skips, before the negative
    lookaheads went in.
    """
    ti = payload.get("tool_input")
    if not isinstance(ti, dict):
        return None

    path = ti.get("file_path")
    if not isinstance(path, str):
        return None
    if not _compile(params.get("path_re", r"$^")).search(path):
        return None

    # new_string for an edit, content for a write. old_string is never read:
    # deleting an `assert True` must not trip the check that celebrates
    # deleting it.
    added = ti.get("new_string")
    if not isinstance(added, str):
        added = ti.get("content")
    if not isinstance(added, str) or not added.strip():
        return None

    for pat in params.get("vacuous_re", []):
        rx = _compile(pat, "m")
        m = rx.search(added)
        if m:
            return {"reason": "test body asserts a tautology",
                    "evidence": m.group(0).strip()[:120]}

    reason_kw = params.get("reason_kw", [])
    for pat in params.get("skip_re", []):
        rx = _compile(pat, "m")
        for m in rx.finditer(added):
            line = added[added.rfind("\n", 0, m.start()) + 1:]
            line = line.split("\n", 1)[0]
            if any(kw in line for kw in reason_kw):
                continue
            return {"reason": "test disabled unconditionally, with no reason",
                    "evidence": m.group(0).strip()[:120]}
    return None


def first_touch_of_domain(payload, params, context):
    """Not a check -- the Tier 2 trigger.

    Fires once per domain per session, on the first write to a path the domain
    claims, and can only inject text. Noise control is the whole design
    problem here, so the budget is structural rather than a matter of taste:
    a domain that has already spoken this session cannot speak again.
    """
    domain = params.get("domain")
    if not domain or domain in set(context.get("seen_domains") or ()):
        return None

    ti = payload.get("tool_input")
    if not isinstance(ti, dict):
        return None
    path = ti.get("file_path")
    if not isinstance(path, str) or not path:
        return None

    domains = context.get("domains") or {}
    spec = domains.get(domain)
    if not spec:
        # Silence here would be indistinguishable from a domain that simply
        # never matched. Say which one is missing.
        return {"reason": "domain %r has no entry in policy/domains.json"
                          % domain,
                "misconfigured": True}

    rel = path
    root = context.get("root")
    if root and path.startswith(root):
        rel = os.path.relpath(path, root)

    for pat in spec.get("path_re", []):
        if _compile(pat).search(rel):
            return {"reason": "first touch of %s this session" % domain,
                    "domain": domain, "path": rel[:200]}
    return None
