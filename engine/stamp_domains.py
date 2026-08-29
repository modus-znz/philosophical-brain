#!/usr/bin/env python3
"""Paths on stdin, Brain-Domain trailers on stdout. Silent when nothing matches.

Used by hooks/prepare-commit-msg. Split out from the shell so the matcher is
one implementation shared with `first_touch_of_domain` -- the same
policy/domains.json patterns decide what a commit touched and what the Tier 2
trigger fires on. Two matchers would drift, and the one in a git hook would
drift unnoticed, because nobody reads a trailer closely enough to spot it.

Prints nothing at all when no domain matches, which is the common case. A
trailer on every commit is a trailer nobody reads.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOMAINS = os.path.join(ROOT, "policy", "domains.json")


def main():
    try:
        with open(DOMAINS, encoding="utf-8") as fh:
            domains = json.load(fh).get("domains", {})
    except Exception:
        return 0

    paths = [p.strip() for p in sys.stdin.read().splitlines() if p.strip()]
    if not paths:
        return 0

    hits = []
    for name in sorted(domains):
        spec = domains[name] or {}
        patterns = spec.get("path_re") or []
        for pat in patterns:
            try:
                rx = re.compile(pat)
            except re.error:
                continue
            if any(rx.search(p) for p in paths):
                hits.append((name, spec.get("source") or ""))
                break

    for name, source in hits:
        if source:
            sys.stdout.write("Brain-Domain: %s (%s)\n" % (name, source))
        else:
            sys.stdout.write("Brain-Domain: %s\n" % name)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BaseException:
        # Same contract as the hooks: a vault must never be why a commit fails.
        sys.exit(0)
