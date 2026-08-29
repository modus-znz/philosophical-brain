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
  anon      anonymous                  honest disclaimer, no claim made
  bare-mod  [[Walt Disney]]            ADVISORY: modern name, no source given
  BARE      [[Seneca]]                 DEFECT: unverified claim of provenance
  MISSING   (nothing)                  DEFECT: quotation with no attribution

Only BARE and MISSING fail the run. The split exists because a bare name means
two different things depending on who is named. An ancient author has a fixed,
indexed, citable corpus: if a line really is Seneca's, a locus exists, and the
absence of one is evidence the line is not his -- which is where every one of
the audit's misattributions actually lived. A modern figure said things in
interviews, letters and talks that no canonical numbering covers, so a bare
name there is ordinary practice rather than an overstated claim. Gating on both
would have meant gating on 51% of the vault, which is a gate nobody can pass
and therefore a gate nobody keeps.

Usage:
  python3 lint_attributions.py [VAULT_ROOT] [--json] [--stats] [--all]
                               [--gate] [--update-baseline]

Exit status: 0 clean, 1 defects found. `--stats` never fails the run.

`--gate` is the pre-commit mode, and it ratchets rather than demanding zero.
72 bare classical attributions remain, and clearing them means finding a locus
for each -- real research, one quote at a time, not something to block a commit
on today. So the gate fails only on defects absent from the baseline: the vault
cannot grow new ones, and every locus anyone does track down shrinks the
baseline permanently. A gate set to an unreachable zero gets commented out in a
week; one set to "no worse than yesterday" survives to do its job.

Baseline entries are keyed by the quote text, not by file and line, so moving
a quote between files or reordering a file does not read as a new defect.
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
ANON = re.compile(r"\banon(?:ymous)?\b|\bunknown\b|\bunattributed\b", re.I)

# Pre-modern authors with a closed, numbered corpus. For these a bare name is
# a claim that a locus exists, so the linter demands one. The list is
# deliberately explicit rather than heuristic: "is this author citable by
# chapter and verse" is a judgement about each corpus, not a property of a
# name, and a reader auditing this gate should be able to see exactly what it
# asserts and add to it.
CLASSICAL = {
    "lao tzu", "laozi", "confucius", "mencius", "zhuangzi", "sun tzu",
    "socrates", "plato", "aristotle", "heraclitus", "epictetus", "seneca",
    "marcus aurelius", "cicero", "plutarch", "epicurus", "diogenes",
    "pythagoras", "thucydides", "herodotus", "homer", "virgil", "ovid",
    "horace", "lucretius", "tacitus", "sophocles", "euripides", "aeschylus",
    "aesop", "pericles", "solon", "thales", "zeno", "chrysippus",
    "augustine", "thomas aquinas", "boethius", "rumi", "hafiz", "saadi",
    "omar khayyam", "al-ghazali", "avicenna", "averroes", "maimonides",
    "buddha", "gautama buddha", "nagarjuna", "patanjali", "valmiki", "vyasa",
    "miyamoto musashi", "yamamoto tsunetomo", "dogen", "basho",
    "matsuo basho", "sei shonagon", "murasaki shikibu", "hillel",
    "ben sira", "solomon", "quintilian", "publilius syrus", "menander",
    "pindar", "xenophon", "polybius", "livy", "suetonius", "juvenal",
    "martial",
}


def is_classical(authors, tail):
    names = [a.lower().strip() for a in authors]
    if any(n in CLASSICAL for n in names):
        return True
    # An unlinked bare name still counts if the tail names one of them.
    low = tail.lower()
    return any(c in low for c in CLASSICAL)


def classify(tail, authors=()):
    """Classify an attribution tail. Order encodes 'weakest claim wins'."""
    t = tail.strip(" .;—-–*_`")
    if not t:
        return "MISSING"
    if ANON.search(t):
        return "anon"
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
    # Anything left names a person with no source. Whether that is a defect
    # or merely unsourced depends on whether the corpus is citable at all.
    return "BARE" if is_classical(authors, t) else "bare-modern"


def scan(root):
    findings = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip dot-directories wholesale: .claude/worktrees/<name>/ holds a
        # full second copy of the vault, and linting it doubles every defect.
        dirnames[:] = [d for d in dirnames
                       if not d.startswith(".")
                       and d not in {"graphify-out", "__pycache__"}]
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
                    # Strip the traditions files' `→ see [[topic]]` suffix:
                    # it is a cross-reference, and leaving it in made topic
                    # links parse as author names.
                    tail = tail.split("→")[0].strip()
                    findings.append({
                        "file": rel,
                        "line": lineno,
                        "class": classify(tail, LINK.findall(tail)),
                        "quote": " ".join(body.split()),
                        "attribution": tail.strip() or None,
                        "authors": LINK.findall(tail),
                    })
    return findings


BASELINE = ".attribution-baseline.json"


def key(f):
    """Identify a defect by its quote text, so it survives line moves."""
    return " ".join(f["quote"].lower().split())


def load_baseline(root):
    path = os.path.join(root, BASELINE)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return set(json.load(fh)["known"])


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
    ap.add_argument("--gate", action="store_true",
                    help="pre-commit mode: fail only on defects not already "
                         "in the baseline")
    ap.add_argument("--update-baseline", action="store_true",
                    help="record the current defects as the accepted baseline")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    findings = scan(root)
    defects = [f for f in findings if f["class"] in ("BARE", "MISSING")]

    if args.update_baseline:
        path = os.path.join(root, BASELINE)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({
                "_comment": "Bare classical attributions accepted as known "
                            "debt. --gate fails only on defects absent from "
                            "this list. Shrink it by adding loci; never grow "
                            "it to make a commit pass.",
                "count": len(defects),
                "known": sorted({key(f) for f in defects}),
            }, fh, ensure_ascii=False, indent=2)
        print(f"baseline written: {len(defects)} defects accepted "
              f"-> {os.path.relpath(path, root)}")
        return 0

    if args.gate:
        base = load_baseline(root)
        if base is None:
            print(f"no {BASELINE} — run --update-baseline first "
                  "to record current debt.")
            return 1
        new = [f for f in defects if key(f) not in base]
        if not new:
            fixed = len(base) - len({key(f) for f in defects})
            msg = f"attribution gate: no new defects ({len(defects)} known)"
            if fixed > 0:
                msg += f"; {fixed} cleared since the baseline was set"
            print(msg)
            return 0
        print(f"attribution gate: {len(new)} NEW bare classical attribution(s)")
        for f in sorted(new, key=lambda x: (x["file"], x["line"])):
            print(f"  {f['file']}:{f['line']}  “{f['quote'][:60]}”"
                  f"  — {f['attribution'] or '(none)'}")
        print("\nAdd a locus, a year, or a hedge — see README "
              "§ Attribution Convention. Keep the quote; fix the claim.")
        return 1

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
        for k in ("locus", "dated", "proverb", "hedged", "derived", "anon",
                  "bare-modern", "BARE", "MISSING"):
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
    advisory = sum(1 for f in findings if f["class"] == "bare-modern")
    print(f"\n{total} quotations — {ok} pass, {len(defects)} defects "
          f"({len(defects) * 100.0 / total:.1f}%), {advisory} advisory")
    if defects:
        print("Each defect is a bare classical attribution: a claim that a "
              "locus exists, with no locus given. Fix by adding one, a year, "
              "or a hedge — see README § Attribution Convention. "
              "Keep the quote; fix the claim.")
    if advisory:
        print(f"{advisory} modern attributions carry no source. Not failing "
              "the run — a bare modern name is ordinary practice — but each "
              "is a citation someone could still go and add.")
    return 1 if defects else 0


if __name__ == "__main__":
    sys.exit(main())
