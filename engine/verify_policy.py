#!/usr/bin/env python3
"""Binding-integrity gate for policy/checks.json.

The engine quotes vault directives back to the model at decision points. If the
vault prose is reworded and the policy keeps quoting the old text, the engine
starts lying about its own source of truth -- a truth-and-integrity violation
committed by the truth-and-integrity enforcer. This script makes that state
impossible to commit.

Run by hooks/pre-commit, after build_graph.py so it validates against the
freshly built graph, and after lint_attributions.py --gate.

    verify_policy.py           verify; exit 1 names the drift
    verify_policy.py --sync    re-quote binding.text from the vault, then verify

Exit 0 = policy and vault agree. Exit 1 = they do not, with the drift named.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
POLICY = os.path.join(ROOT, "policy", "checks.json")
GRAPH = os.path.join(ROOT, "graphify-out", "graph.json")

VALID_EVENTS = {"PreToolUse", "PostToolUse", "Stop"}
VALID_MODES = {"off", "log", "ask", "deny", "block", "inject"}


def fail(errors):
    print("policy gate: %d problem(s)\n" % len(errors))
    for e in errors:
        print("  - %s" % e)
    print("\nThe policy quotes vault prose verbatim so the model sees the real")
    print("directive. When the vault moves, the policy must move with it.")
    return 1


def check_no_markdown(errors):
    """policy/ and engine/ must contain no .md files.

    build_graph.py globs ROOT/**/*.md; lint_attributions.py walks the same
    tree. A .md here would become a document node with serves_moment/directs
    edges, pollute ask.py retrieval, and expose machine prose to the
    attribution linter. Documentation goes in the root README.md, which both
    tools already skip.
    """
    for sub in ("policy", "engine"):
        d = os.path.join(ROOT, sub)
        if not os.path.isdir(d):
            continue
        for dirpath, dirnames, filenames in os.walk(d):
            dirnames[:] = [x for x in dirnames if not x.startswith(".")]
            for fn in filenames:
                if fn.endswith(".md"):
                    rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
                    errors.append(
                        "%s is Markdown inside %s/ -- build_graph.py would "
                        "ingest it as a document node. Move the prose to "
                        "README.md." % (rel, sub))


def load_directives():
    with open(GRAPH, encoding="utf-8") as fh:
        graph = json.load(fh)
    return [n for n in graph["nodes"] if n.get("node_kind") == "directive"]


def _hits(chk, directives):
    """Directive nodes a binding resolves to. One definition, two callers."""
    b = chk.get("binding") or {}
    src, match = b.get("source"), b.get("match")
    if not (src and match):
        return []
    return [n for n in directives
            if n.get("source_file") == src and match in n.get("text", "")]


def check_binding(chk, directives, errors):
    """Resolve binding -> exactly one directive node, and match its text.

    Deliberately NOT keyed on the node id. build_graph.py numbers directives
    from a global counter (directive_<file>_<n>, incremented across all
    files), so adding one bullet to any earlier principle silently shifts
    every downstream id. Text is the stable key -- the same reasoning that
    makes .attribution-baseline.json key on quote text rather than line
    number.
    """
    cid = chk["id"]
    b = chk.get("binding") or {}
    src, match, text = b.get("source"), b.get("match"), b.get("text")

    if not (src and match and text):
        errors.append("%s: binding needs source, match and text" % cid)
        return

    if not os.path.isfile(os.path.join(ROOT, src)):
        errors.append("%s: binding.source %s does not exist" % (cid, src))
        return

    hits = _hits(chk, directives)

    if len(hits) == 0:
        errors.append(
            "%s: binding.match %r matches no directive in %s. The directive "
            "was reworded or deleted. --sync cannot help here: only you know "
            "which directive was meant, so pick a new binding.match by hand."
            % (cid, match, src))
        return
    if len(hits) > 1:
        errors.append(
            "%s: binding.match %r is ambiguous in %s (%d directives match: "
            "%s). Lengthen it until it is unique."
            % (cid, match, src, len(hits),
               "; ".join(repr(h["text"][:50]) for h in hits)))
        return

    actual = hits[0]["text"]
    if actual != text:
        errors.append(
            "%s: binding.text has drifted from the vault.\n"
            "        vault:  %r\n"
            "        policy: %r\n"
            "        fix:    python3 engine/verify_policy.py --sync"
            % (cid, actual, text))


def check_shape(chk, principles, predicate_names, errors):
    cid = chk.get("id", "<no id>")

    if chk.get("event") not in VALID_EVENTS:
        errors.append("%s: event %r not in %s"
                      % (cid, chk.get("event"), sorted(VALID_EVENTS)))
    if chk.get("mode") not in VALID_MODES:
        errors.append("%s: mode %r not in %s"
                      % (cid, chk.get("mode"), sorted(VALID_MODES)))

    p = chk.get("principle")
    if p not in principles:
        errors.append("%s: principle %r has no principles/%s.md" % (cid, p, p))

    pred = chk.get("predicate")
    if predicate_names is not None and pred not in predicate_names:
        errors.append("%s: predicate %r is not defined in engine/predicates.py"
                      % (cid, pred))

    if not (chk.get("determinism") or "").strip():
        errors.append(
            "%s: no determinism statement. Every check must say in plain "
            "words what makes it mechanical -- or admit that it is not."
            % cid)

    params = chk.get("params") or {}

    for key in ("patterns", "vacuous_re", "skip_re", "claim_patterns",
                "hedge_patterns", "segment_allowlist"):
        for item in params.get(key, []):
            pat = item["re"] if isinstance(item, dict) else item
            try:
                re.compile(pat)
            except re.error as exc:
                errors.append("%s: params.%s pattern %r does not compile (%s)"
                              % (cid, key, pat, exc))

    # Scalar regex params, checked separately: iterating a bare string with the
    # loop above would compile it one character at a time and pass trivially.
    # A gate whose own patterns go unvalidated is the failure it exists to stop.
    for key in ("path_re",):
        pat = params.get(key)
        if pat is None:
            continue
        if not isinstance(pat, str):
            errors.append("%s: params.%s must be a string, got %s"
                          % (cid, key, type(pat).__name__))
            continue
        try:
            re.compile(pat)
        except re.error as exc:
            errors.append("%s: params.%s pattern %r does not compile (%s)"
                          % (cid, key, pat, exc))


def stale_sources(policy):
    """Binding source files modified after graph.json was last built.

    A sync against a stale graph would re-quote the OLD wording and report
    success -- the drift would survive the very command that claims to cure
    it. That is worse than the failure it is fixing, so it is refused.
    """
    if not os.path.isfile(GRAPH):
        return ["graphify-out/graph.json (missing)"]
    built = os.path.getmtime(GRAPH)
    out = []
    for chk in policy.get("checks", []):
        src = (chk.get("binding") or {}).get("source")
        if not src or src in out:
            continue
        p = os.path.join(ROOT, src)
        if os.path.isfile(p) and os.path.getmtime(p) > built:
            out.append(src)
    return out


def sync():
    """Re-quote binding.text from the vault, in place, preserving formatting.

    Rewording a bound directive fails the commit by design: the gate cannot
    tell a deliberate edit from silent prose drift, and guessing is the one
    thing it exists not to do. This is the one-command recovery -- you still
    choose to run it, and you still re-commit.

    Only binding.text is ever rewritten. If binding.match no longer resolves
    to exactly one directive, the match itself needs a human decision and
    this refuses rather than guess.

    The substitution is textual, on the JSON-encoded string, because
    json.dump(indent=2) reflows 135 of this file's 151 lines -- the compact
    one-line pattern objects are deliberate and worth keeping.
    """
    if not os.path.isfile(POLICY):
        print("policy sync: no policy/checks.json -- nothing to sync")
        return 0

    with open(POLICY, encoding="utf-8") as fh:
        policy = json.load(fh)

    stale = stale_sources(policy)
    if stale:
        print("policy sync: refusing -- graph.json is older than %s"
              % ", ".join(stale))
        print("Syncing now would re-quote the stale text and call it fixed.")
        print("Run:  python3 build_graph.py --force")
        print("then: python3 engine/verify_policy.py --sync")
        return 1

    directives = load_directives()
    with open(POLICY, encoding="utf-8") as fh:
        raw = fh.read()
    changed, blocked = [], []

    for chk in policy.get("checks", []):
        cid = chk.get("id", "<no id>")
        b = chk.get("binding") or {}
        old, match = b.get("text"), b.get("match")
        hits = _hits(chk, directives)

        if len(hits) != 1:
            blocked.append(
                "%s: binding.match %r matches %d directives in %s. Pick a "
                "match that is present and unique, by hand."
                % (cid, match, len(hits), b.get("source")))
            continue

        new = hits[0]["text"]
        if new == old:
            continue

        old_lit = json.dumps(old, ensure_ascii=False)
        n = raw.count(old_lit)
        if n != 1:
            blocked.append(
                "%s: binding.text occurs %d times in checks.json, so it "
                "cannot be replaced unambiguously. Edit it by hand." % (cid, n))
            continue

        raw = raw.replace(old_lit, json.dumps(new, ensure_ascii=False))
        changed.append((cid, old, new))

    if changed:
        # Parse before writing. A botched substitution must never reach disk:
        # an unparseable checks.json fails every future commit at load time.
        json.loads(raw)
        with open(POLICY, "w", encoding="utf-8") as fh:
            fh.write(raw)
        print("policy sync: re-quoted %d binding(s) from the vault\n"
              % len(changed))
        for cid, old, new in changed:
            print("  %s" % cid)
            print("      was: %r" % old)
            print("      now: %r" % new)
        print("")
    elif not blocked:
        print("policy sync: every binding already quotes the vault verbatim")

    if blocked:
        print("policy sync: %d binding(s) need a human\n" % len(blocked))
        for b in blocked:
            print("  - %s" % b)
        print("\nbinding.match is the stable key. When a rewording changes")
        print("the match too, only you know which directive was meant.")
        return 1

    # Prove the sync worked by re-verifying, rather than asserting it.
    return verify()


def verify():
    errors = []

    if not os.path.isfile(POLICY):
        print("policy gate: no policy/checks.json -- nothing to verify")
        return 0
    if not os.path.isfile(GRAPH):
        print("policy gate: no graphify-out/graph.json -- run build_graph.py")
        return 1

    with open(POLICY, encoding="utf-8") as fh:
        policy = json.load(fh)

    principles = {fn[:-3] for fn in os.listdir(os.path.join(ROOT, "principles"))
                  if fn.endswith(".md")}

    predicate_names = None
    pred_path = os.path.join(HERE, "predicates.py")
    if os.path.isfile(pred_path):
        with open(pred_path, encoding="utf-8") as fh:
            predicate_names = set(re.findall(r"^def\s+(\w+)", fh.read(),
                                             re.MULTILINE))

    check_no_markdown(errors)
    directives = load_directives()

    seen = set()
    for chk in policy.get("checks", []):
        cid = chk.get("id", "<no id>")
        if cid in seen:
            errors.append("%s: duplicate check id" % cid)
        seen.add(cid)
        check_shape(chk, principles, predicate_names, errors)
        check_binding(chk, directives, errors)

    if errors:
        return fail(errors)

    n = len(policy.get("checks", []))
    modes = sorted({c["mode"] for c in policy["checks"]})
    # Say out loud when the predicate check was skipped. Otherwise a green
    # line implies every check names a real predicate, and until
    # predicates.py exists not one of them does.
    caveat = "" if predicate_names is not None else \
        "; predicates.py absent -- predicate names UNCHECKED"
    print("policy gate: %d check(s) bound to live vault directives; modes=%s%s"
          % (n, ",".join(modes), caveat))
    return 0


def main(argv):
    args = argv[1:]
    if "--sync" in args:
        return sync()
    if args:
        print("usage: verify_policy.py [--sync]")
        return 2
    return verify()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
