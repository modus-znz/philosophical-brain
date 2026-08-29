#!/usr/bin/env python3
"""Render the flat persona quote library from the vault.

`~/.claude/knowledge/wisdom-quotes.md` is read by every session (CLAUDE.md
§ Session Personality) as a zero-cost grep. It used to be maintained by hand,
which meant it drifted: 22 quotes stated flatly there were already hedged in
this vault. This script makes it a build artifact so the vault's attribution
discipline reaches the file that actually gets read.

Only the session-moment half is generated. `persona/theme-tree.md` belongs to
the Timeless Wisdom video project, is curated by hand, and is spliced onto the
end byte-for-byte.
"""
import argparse
import io
import os
import re
import sys
from collections import OrderedDict

QUOTE_RX = re.compile(r'^>\s*["“](.+?)["”]\s*[—–]\s*(.+)$')
MOMENT_RX = re.compile(r'^-\s*\*\*Session Moments\*\*:\s*(.+)$')
THEME_TREE = os.path.join("persona", "theme-tree.md")

# heading -> session-moment keys. Vault files declare compound forms
# ("focus/deep-work"), so keys are matched against each half separately.
GROUPS = OrderedDict([
    ("Task Start — beginnings",                    ["task-start"]),
    ("Planning & Strategy — before the work",      ["planning", "strategy"]),
    ("Step Complete — progress",                   ["step-complete"]),
    ("Reading / Studying — learning",              ["reading", "studying", "learning"]),
    ("Investigating / Debugging — inquiry",        ["investigating", "debugging", "investigation"]),
    ("Writing / Building — craft",                 ["writing", "building", "craft"]),
    ("Running a Command — action",                 ["running-a-command", "action"]),
    ("Installing / Gathering Tools — preparation", ["installing", "gathering-tools", "preparation"]),
    ("Git Commit / Push — preserving work",        ["git", "git-commit", "push", "preserving-work"]),
    ("Bug Found — challenge appears",              ["bug-found"]),
    ("Bug Fixed — overcoming",                     ["bug-fixed"]),
    ("Refactoring / Renewal — improving what exists", ["refactoring", "renewal"]),
    ("Dead Code Removed — simplicity",             ["dead-code-removed", "simplicity"]),
    ("Security Hardening — protection & prudence", ["security-hardening", "prudence"]),
    ("Tests Passing — validation",                 ["tests-passing", "validation"]),
    ("Tests Failing / Setback — resilience",       ["tests-failing", "setback", "resilience"]),
    ("Blocked / Waiting — patience",               ["blocked", "waiting", "patience"]),
    ("Focus & Discipline — deep work",             ["focus", "deep-work"]),
    ("Collaboration & Teamwork — working together", ["collaboration", "teamwork"]),
    ("Humility & Learning from Mistakes",          ["humility", "learning-from-mistakes"]),
    ("Courage & Risk — daring greatly",            ["courage", "risk-taking"]),
    ("Balance & Rest — sustainable pace",          ["balance", "rest", "sustainable-pace"]),
    ("Gratitude & Joy — appreciating the moment",  ["gratitude", "joy"]),
    ("Truth & Integrity — doing right",            ["truth", "integrity"]),
    ("Task Complete — fulfillment",                ["task-complete"]),
    ("General Wisdom — any moment",                ["general-wisdom", "any moment"]),
])
FALLBACK = "General Wisdom — any moment"

# Uncapped by default: a quote whose file declares three moments belongs in all
# three groups, and CLAUDE.md reads one group on demand rather than the whole
# file, so the duplication costs nothing at read time. Capping was measured to
# drop 85 curated quotes from the persona's reach to save 30 KB nobody loads.
# `--cap N` is kept for anyone who wants a smaller sample.
DEFAULT_CAP = 0

PREAMBLE = """# The Fountain of Knowledge — Wisdom & Positivity Quote Library

> **Generated file — do not edit by hand.** The session-moment groups below are
> rendered from the philosophical-brain vault at `{vault}` by
> `render_persona.py`, which its pre-commit hook runs. Edits made here are lost
> on the vault's next commit; fix the quote in the vault instead. Attributions
> carry that vault's hedges, so "attributed to" and "modern coinage" are
> deliberate and accurate — do not silently tighten them into a bare name.
> The `# Content Theme Tree` section at the end is hand-curated and spliced
> through untouched.
>
> Linked from `~/.claude/CLAUDE.md` § Session Personality.
> Usage: pick quotes **at random** — never default to the first entry of a group. Multiple quotes per update are welcome (1–2 is the sweet spot, 3 max on a milestone). Do not repeat a quote within the same session. Mix groups freely: a "General Wisdom" or tradition-pool quote is always a valid substitute for any moment. Attribute the source when one is given.
> Traditions represented: Greek & Roman philosophy, Stoicism, Taoism, Zen & Buddhist teaching, Confucianism, Sufi poetry, Vedic thought, Norse Hávamál, African & Swahili proverbs, Japanese & Chinese proverbs, Renaissance & Enlightenment, and modern positive thinking.
> For a ranked answer to a specific situation rather than a group to browse:
> `python3 {vault}/ask.py "<what you are doing>"`.

---
"""


def normalise(text):
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text.lower()).split())


def strip_links(text):
    return re.sub(r"\[\[(.+?)\]\]", r"\1", text)


def moment_keys(raw):
    """'focus/deep-work · bug-found' -> {'focus','deep-work','bug-found'}."""
    keys = set()
    for part in raw.split("·"):
        part = part.strip()
        if not part:
            continue
        keys.add(part.lower())
        for half in part.split("/"):
            if half.strip():
                keys.add(half.strip().lower())
    return keys


def read_vault(root):
    """-> list of (moment_keys, quote_text, attribution, source) in stable order."""
    entries = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith((".", "__")))
        rel = os.path.relpath(dirpath, root)
        if rel.split(os.sep)[0] in ("graphify-out", "persona"):
            continue
        for name in sorted(filenames):
            if not name.endswith(".md"):
                continue
            path = os.path.join(dirpath, name)
            keys = set()
            with io.open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.rstrip("\n")
                    m = MOMENT_RX.match(line.strip())
                    if m:
                        keys = moment_keys(m.group(1))
                        continue
                    q = QUOTE_RX.match(line.strip())
                    if q and len(q.group(1).strip()) > 15:
                        entries.append((keys, q.group(1).strip(),
                                        q.group(2).strip(),
                                        os.path.relpath(path, root)))
    return entries


def interleave(by_source, cap):
    """Round-robin across source files, so a capped group stays varied instead
    of being dominated by whichever file happens to sort first."""
    picked, seen, queues = [], set(), [list(v) for v in by_source.values()]
    while queues and (cap is None or len(picked) < cap):
        for q in queues:
            if cap is not None and len(picked) >= cap:
                break
            if q:
                key, line = q.pop(0)
                if key not in seen:
                    seen.add(key)
                    picked.append(line)
        queues = [q for q in queues if q]
    return picked


def render(root, cap=DEFAULT_CAP):
    entries = read_vault(root)
    buckets = OrderedDict((h, OrderedDict()) for h in GROUPS)

    def add(heading, source, key, line):
        buckets[heading].setdefault(source, []).append((key, line))

    for keys, quote, attribution, source in entries:
        line = '- "%s" — %s' % (strip_links(quote), strip_links(attribution))
        key = normalise(quote)
        placed = False
        for heading, wanted in GROUPS.items():
            if keys & set(wanted):
                add(heading, source, key, line)
                placed = True
        if not placed:
            add(FALLBACK, source, key, line)

    buckets = OrderedDict((h, interleave(by_src, cap)) for h, by_src in buckets.items())

    out = [PREAMBLE.format(vault=root)]
    for heading, quotes in buckets.items():
        if not quotes:
            raise SystemExit("render_persona: group %r came out empty — check "
                             "its moment keys against `ask.py --moments`" % heading)
        out.append("## %s\n" % heading)
        out.extend(quotes)
        out.append("")

    tree = os.path.join(root, THEME_TREE)
    tail = ""
    if os.path.exists(tree):
        tail = io.open(tree, encoding="utf-8").read().strip("\n")
        out.append("---\n")
    return "\n".join(out) + ("\n" + tail + "\n" if tail else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vault", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--out", default=os.path.expanduser("~/.claude/knowledge/wisdom-quotes.md"))
    ap.add_argument("--cap", type=int, default=DEFAULT_CAP,
                    help="max quotes per group; 0 (the default) is uncapped")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the artifact is stale; write nothing")
    args = ap.parse_args()

    previous = ""
    if os.path.exists(args.out):
        previous = io.open(args.out, encoding="utf-8").read()

    text = render(args.vault, args.cap or None)

    if args.check:
        if text != previous:
            print("wisdom-quotes.md is stale — run: python3 render_persona.py")
            return 1
        print("wisdom-quotes.md is up to date")
        return 0

    if text == previous:
        print("wisdom-quotes.md already up to date")
        return 0
    with io.open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    n = sum(1 for line in text.splitlines() if line.startswith('- "'))
    print("wrote %s (%d quotes, %d groups)" % (args.out, n, len(GROUPS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
