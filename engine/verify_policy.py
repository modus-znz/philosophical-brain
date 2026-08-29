#!/usr/bin/env python3
"""Binding-integrity gate for policy/checks.json.

The engine quotes vault directives back to the model at decision points. If the
vault prose is reworded and the policy keeps quoting the old text, the engine
starts lying about its own source of truth -- a truth-and-integrity violation
committed by the truth-and-integrity enforcer. This script makes that state
impossible to commit.

Run by hooks/pre-commit, after build_graph.py so it validates against the
freshly built graph, and after lint_attributions.py --gate.

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

    hits = [n for n in directives
            if n.get("source_file") == src and match in n.get("text", "")]

    if len(hits) == 0:
        errors.append(
            "%s: binding.match %r matches no directive in %s. The directive "
            "was reworded or deleted -- update the policy to the new wording."
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
            "        policy: %r" % (cid, actual, text))


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

    for key in ("patterns", "vacuous_re", "skip_re", "claim_patterns",
                "hedge_patterns", "segment_allowlist"):
        for item in (chk.get("params") or {}).get(key, []):
            pat = item["re"] if isinstance(item, dict) else item
            try:
                re.compile(pat)
            except re.error as exc:
                errors.append("%s: params.%s pattern %r does not compile (%s)"
                              % (cid, key, pat, exc))


def main():
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
    print("policy gate: %d check(s) bound to live vault directives; modes=%s"
          % (n, ",".join(modes)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
