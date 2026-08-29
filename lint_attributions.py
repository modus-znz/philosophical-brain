#!/usr/bin/env python3
"""Provenance linter for the Philosophical Brain vault.

Every quotation in this vault carries an attribution, and the README states
the rule those attributions must satisfy:

    A bare `[[Author]]` with no locus, year, or hedge is a claim of verified
    primary-source provenance. Treat it as a defect until checked.

That rule was written after an audit found the split it describes -- quotes
cited to a locus were right, quotes cited to a bare name mostly were not.
A rule nothing enforces decays, so this script enforces it: it parses every
quotation line in the vault, classifies its attribution, and exits non-zero
if any unhedged bare-name claim survives. Wire it into a pre-commit hook and
the vault cannot silently regrow the defect class it was just cleaned of.

CLASSES
-------
  locus     [[Author]], *Work* 2.5     verified against a primary source
  dated     [[Author]] (1977)          verified, modern, no classical locus
  proverb   Swahili proverb            traditional saying, no single author
  hedged    attributed to [[X]]        circulates widely, provenance uncertain
  derived   [[A]], after [[B]]         paraphrase, translation or rendering
  BARE      [[Author]]                 DEFECT: unverified claim of provenance
  MISSING   (nothing)                  DEFECT: quotation with no attribution

Usage:
  python3 lint_attributions.py [VAULT_ROOT] [--json] [--stats] [--all]

Exit status: 0 clean, 1 defects found. `--stats` never fails the run.
"""
import argparse
import json
import os
import re
import sys

# A quotation line is either a blockquote or a `Supporting Quotes` bullet.
# Both render as `"text" -- attribution`; the bullet additionally carries a
# leading wikilink back to the theme file the quote was lifted from.
QUOTE_LINE = re.compile(r'^\s*(?:>|[-*])\s')
BODY = re.compile(r'["“”]([^"“”]{8,})["“”]\s*(.*)$')
LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")

# Ordered: the first match wins, so the most specific evidence is tested
# first. A tail carrying both a work title and a hedge is hedged-and-sourced;
# crediting it as `locus` would overstate what the vault actually knows.
HEDGE = re.compile(
    r"\battributed\b|\bmisattributed\b|\bapocryphal\b|\bmodern coinage\b"
    r"|\btraditional(?:ly)?\b|\bwidely (?:quoted|circulated|attributed)\b"
    r"|\bcommonly (?:quoted|attributed)\b|\bvariously attributed\b"
    r"|\bin the spirit of\b|\boften attributed\b|\bno known source\b"
    r"|\bunverified\b|\bfolk-attributed\b|\bpopularly attributed\b",
    re.I,
)
DERIVED = re.compile(
    r"\bafter\b|\bon \[\[|\bas rendered\b|\bparaphras|\brendering\b"
    r"|\btrans(?:\.|lated|lation)\b|\bsummaris|\bsummariz|\bglossing\b",
    re.I,
)
PROVERB = re.compile(
    r"\bproverb\b|\bsaying\b|\badage\b|\bmaxim\b|\bdictum\b|\baphorism\b"
    r"|\bfolk wisdom\b|\bteaching\b|\btradition(?:al)?\b|\bkoan\b"
    r"|\bsutra\b|\bhadith\b|\bpsalm\b|\bproverbs\b|\btalmud|\bmishnah\b"
    r"|\bbushido\b|\bhavamal\b|\bhávamál\b|\bupanishad|\bgita\b"
    r"|\bdhammapada\b|\banalects\b|\bi ching\b|\btao te ching\b",
    re.I,
)
# A locus is a pointer precise enough for a reader to go check: a work title
# plus a number (book/chapter/verse/line), or an explicit citation word.
LOCUS = re.compile(
    r"\*[^*]+\*[^,]*?\d|\b(?:bk\.?|book|ch\.?|chapter|sec\.?|§|line|fr\.?"
    r"|fragment|letter|ep\.?|verse|sonnet|act|scene)\s*\.?\s*\d",
    re.I,
)
DATED = re.compile(r"\((?:c\.\s*)?\d{3,4}(?:\s*[–-]\s*\d{2,4})?\)")


def classify(tail):
    """Classify an attribution tail. Order encodes 'weakest claim wins'."""
    t = tail.strip(" .;—-–*_`")
    if not t:
        return "MISSING"
    if HEDGE.search(t):
        return "hedged"
    if DERIVED.search(t):
        return "derived"
    if LOCUS.search(t):
        return "locus"
    if PROVERB.search(t):
        return "proverb"
    if DATED.search(t):
        return "dated"
    # Anything left that names a person -- linked or not -- is an unhedged
    # claim of primary-source provenance, which is exactly the defect.
    return "BARE"


def scan(root):
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in {"graphify-out", ".git", "__pycache__"}]
        for fn in sorted(filenames):
            if not fn.endswith(".md") or fn == "README.md":
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root)
            with open(path, encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    if not QUOTE_LINE.match(line):
                        continue
                    s = line.strip().lstrip(">-* ").strip()
                    # drop a leading `[[source.md|Label]] --` back-reference
                    s = re.sub(r"^\[\[[^\]]+\]\]\s*[—–-]+\s*", "", s)
                    m = BODY.match(s)
                    if not m:
                        continue
                    body, tail = m.group(1), m.group(2)
                    tail = re.sub(r"^\s*[—–-]+\s*", "", tail)
                    findings.append({
                        "file": rel,
                        "line": lineno,
                        "class": classify(tail),
                        "quote": " ".join(body.split()),
                        "attribution": tail.strip() or None,
                        "authors": LINK.findall(tail),
                    })
    return findings


def main():
    ap = argparse.ArgumentParser(
        description="Enforce the vault's attribution convention.")
    ap.add_argument("root", nargs="?", default=".",
                    help="vault root (default: current directory)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--stats", action="store_true",
                    help="class histogram only; always exits 0")
    ap.add_argument("--all", action="store_true",
                    help="list every quotation, not only the defects")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    findings = scan(root)
    defects = [f for f in findings if f["class"] in ("BARE", "MISSING")]

    if args.json:
        print(json.dumps(args.all and findings or defects,
                         ensure_ascii=False, indent=2))
        return 0 if args.stats or not defects else 1

    counts = {}
    for f in findings:
        counts[f["class"]] = counts.get(f["class"], 0) + 1
    total = len(findings)

    if args.stats:
        print(f"{total} quotations in {root}")
        for k in ("locus", "dated", "proverb", "hedged", "derived",
                  "BARE", "MISSING"):
            n = counts.get(k, 0)
            if n:
                print(f"  {k:<8} {n:>4}  {n * 100.0 / total:5.1f}%")
        return 0

    shown = findings if args.all else defects
    cur = None
    for f in sorted(shown, key=lambda x: (x["file"], x["line"])):
        if f["file"] != cur:
            cur = f["file"]
            print(f"\n{cur}")
        q = f["quote"]
        print(f"  {f['line']:>4}  {f['class']:<8} “{q[:64]}"
              f"{'…' if len(q) > 64 else ''}”"
              f"  — {f['attribution'] or '(none)'}")

    ok = total - len(defects)
    print(f"\n{total} quotations — {ok} pass, {len(defects)} defects "
          f"({len(defects) * 100.0 / total:.1f}%)")
    if defects:
        print("Each defect is an unhedged claim of verified provenance. "
              "Fix by adding a locus, a year, or a hedge — see README "
              "§ Attribution Convention. Keep the quote; fix the claim.")
    return 1 if defects else 0


if __name__ == "__main__":
    sys.exit(main())
