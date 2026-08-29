#!/usr/bin/env python3
"""Canonical knowledge-graph builder for the Philosophical Brain vault.

WHY THIS AND NOT `graphify update`
----------------------------------
graphify's extractor builds nodes from pages and headings only. Measured
against this vault that means:

  * no node carries any content -- `rationale` is "" on every node, so a
    query returns titles and never a quote;
  * `Session Moments` (authored in 49 files) does not exist in the graph at
    all -- it is a bullet, and bullets are invisible to the extractor;
  * 105 of 313 nodes are duplicated structural headings ("Code Directive"
    x23, "Related" x23), which win entry-point matches over real concepts.

Its 599 semantic edges were measured to be a strict 100% subset of the 943
this builder derives from wikilinks, so switching loses no connectivity.

WHAT THIS EMITS
---------------
Standard graphify node-link JSON, consumed unchanged by `graphify
query|path|explain` and `graphify-mcp`, with five node kinds:

  document  one per .md file, carrying an excerpt
  concept   a [[wikilink]] target with no file of its own (mostly authors)
  quote     one per authored quotation, carrying the FULL text + attribution
  moment    one per session moment (task-start, debugging, ...)
  directive one per Code/Engineering Directive, carrying its full text

and edge relations `cites`, `quotes`, `attributed_to`, `serves_moment`,
`directs`. Together these make the lookup the vault exists to serve --
situation -> moment -> document -> quote text -- an actual graph path.

Usage:
  python3 build_graph.py <vault-root> [OUT.json] [--force] [--dry-run]
"""
import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

GENERATOR = "build_graph.py"

if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
    sys.exit(__doc__.strip().split("Usage:")[-1].strip())

ROOT = os.path.abspath(sys.argv[1])
if not os.path.isdir(ROOT):
    sys.exit(f"not a directory: {ROOT}")

FORCE = "--force" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
_out = [a for a in sys.argv[2:] if not a.startswith("-")]
OUT = os.path.abspath(_out[0]) if _out else os.path.join(
    ROOT, "graphify-out", "graph.json")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# Positive identification: overwrite only a file this script wrote. Anything
# else -- a graphify graph, a hand-edit -- needs an explicit --force. Keyed on
# graph.graph.generator rather than on node fields, so it stays correct no
# matter how the node schema changes.
if os.path.exists(OUT) and not FORCE and not DRY_RUN:
    try:
        _prev = json.load(open(OUT)).get("graph", {}).get("generator")
    except Exception:
        _prev = None
    if _prev != GENERATOR:
        sys.exit(
            f"refusing to overwrite {OUT}: generator is {_prev!r}, not "
            f"{GENERATOR!r}.\nPass a different OUT path, or --force to "
            f"override."
        )

FILES = sorted(glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True))
FILES = [f for f in FILES
         if not f.startswith(os.path.join(ROOT, "graphify-out"))]

LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
# A quotation: a blockquote line, or a "Supporting Quotes" bullet. Both are
# `"text" - Author`; the bullet is prefixed with the source quote-file link.
QUOTE_RE = re.compile(r'[""\"]([^""\"]{8,})[""\"]\s*(?:[-—–]+\s*(.+))?$')
MOMENT_RE = re.compile(r"^\s*[-*]\s*\*\*Session Moments?\*\*\s*:\s*(.+)$", re.M)
PLACEHOLDERS = {"concept", "principle", "tech-mapping", "author"}


def slug(name):
    return re.sub(r"[^A-Za-z0-9]+", "_", name.lower()).strip("_") or "node"


def node_id(path_rel):
    base = os.path.splitext(os.path.basename(path_rel))[0]
    return slug(os.path.dirname(path_rel) + "_" + base)


def norm(label):
    return label.replace("-", " ").lower().strip()


def strip_links(s):
    """Render `[[Confucius]]` as `Confucius` for human-readable payload."""
    return LINK_RE.sub(lambda m: m.group(1).split("/")[-1], s).strip()


def clip(s, n=90):
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


nodes, links = [], []
node_ids = set()


def add_node(nid, **kw):
    if nid in node_ids:
        return False
    node_ids.add(nid)
    nodes.append(dict(id=nid, **kw))
    return True


def add_link(src, tgt, relation, source_file):
    if src == tgt:
        return
    links.append({
        "source": src, "target": tgt, "relation": relation,
        "confidence": "EXTRACTED", "confidence_score": 1.0,
        "source_file": source_file,
    })


# ---------------------------------------------------------------- 1. docs
raw = {}
for f in FILES:
    rel = os.path.relpath(f, ROOT)
    raw[rel] = open(f, encoding="utf-8").read()

doc_stem = {os.path.splitext(os.path.basename(r))[0]: r for r in raw}

for rel, text in raw.items():
    h1 = re.search(r"^# (.+)$", text, re.M)
    first_line = next((l for l in text.splitlines() if l.strip()), "")
    label = (h1.group(1) if h1 else "").strip() or first_line.strip()
    # Excerpt: the Definition line if present, else the first real prose
    # paragraph -- never a heading, bullet, quote or link line.
    excerpt = ""
    m = re.search(r"\*\*Definition:\*\*\s*(.+?)(?=\n\n|\n#)", text, re.S)
    if m:
        excerpt = strip_links(m.group(1))
    else:
        for para in re.split(r"\n\s*\n", text):
            p = para.strip()
            if p and not p.startswith(("#", "-", "*", ">", "|")):
                excerpt = strip_links(p)
                break
    add_node(
        node_id(rel),
        label=label,
        community=1,
        community_name="documents",
        file_type="document",
        node_kind="document",
        norm_label=norm(label),
        text=clip(excerpt, 400),
        rationale=clip(excerpt, 400),
        source_file=rel,
    )

# ------------------------------------------------- 2. concepts (wikilinks)
concept_id = {}
for rel, text in raw.items():
    for m in LINK_RE.finditer(text):
        if text[max(0, m.start() - 1):m.start()] == "`":
            continue
        link = m.group(1).strip()
        stem = os.path.splitext(link.split("/")[-1])[0]
        if stem in PLACEHOLDERS or stem in doc_stem:
            continue
        nm = norm(link)
        if nm in concept_id:
            continue
        nid = "obj_" + slug(nm)
        concept_id[nm] = nid
        add_node(
            nid, label=link.title(), community=2, community_name="concepts",
            file_type="concept", node_kind="concept", norm_label=nm,
            text="", rationale="", source_file=None,
        )


def resolve(link):
    stem = os.path.splitext(link.split("/")[-1])[0]
    if stem in PLACEHOLDERS:
        return None
    if stem in doc_stem:
        return node_id(doc_stem[stem])
    return concept_id.get(norm(link))


# ------------------------------------------------------------- 3. cites
for rel, text in raw.items():
    src = node_id(rel)
    for m in LINK_RE.finditer(text):
        if text[max(0, m.start() - 1):m.start()] == "`":
            continue
        tgt = resolve(m.group(1).strip())
        if tgt:
            add_link(src, tgt, "cites", rel)

# --------------------------------------------------------- 4. moments
# The lookup path the vault exists to serve, and the one graphify drops
# entirely: a dev situation resolves to a moment, the moment to its documents.
moment_id = {}
for rel, text in raw.items():
    if os.path.basename(rel) == "README.md":
        continue  # its line documents the schema, it is not data
    for m in MOMENT_RE.finditer(text):
        # Split on separators AND on "/" -- authors write "blocked/waiting"
        # and "focus/deep-work" as alternates, not as compound names, so the
        # slash forms must collapse onto the same canonical moments.
        for tok in re.split(r"[·•|,/]", m.group(1)):
            tok = strip_links(tok).strip(" .*_`")
            if not tok or len(tok) > 60:
                continue
            key = norm(tok)
            nid = moment_id.get(key)
            if not nid:
                nid = "moment_" + slug(key)
                moment_id[key] = nid
                add_node(
                    nid, label=tok, community=3, community_name="moments",
                    file_type="moment", node_kind="moment", norm_label=key,
                    text=f"Session moment: {tok}",
                    rationale=f"Session moment: {tok}", source_file=None,
                )
            add_link(node_id(rel), nid, "serves_moment", rel)

# ---------------------------------------------------------- 5. quotes
# One node per distinct quotation, carrying the FULL text. This is the fatal
# gap in the graphify graph: no node there held any content at all.
quote_id = {}
for rel, text in raw.items():
    if os.path.basename(rel) == "README.md":
        continue
    src = node_id(rel)
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(">"):
            s = s.lstrip("> ").strip()
        elif s.startswith(("- ", "* ")) and '"' in s:
            s = re.sub(r"^[-*]\s*(\[\[[^\]]+\]\]\s*[-—–]\s*)?", "", s)
        else:
            continue
        qm = QUOTE_RE.search(s)
        if not qm:
            continue
        body = " ".join(qm.group(1).split())
        attrib = strip_links(qm.group(2) or "").strip(" .*_")
        key = re.sub(r"[^a-z0-9]+", "", body.lower())[:120]
        nid = quote_id.get(key)
        if not nid:
            nid = "quote_" + (re.sub(r"[^a-z0-9]+", "_", body.lower())[:48]
                              .strip("_") or "q")
            while nid in node_ids:
                nid += "_x"
            quote_id[key] = nid
            add_node(
                nid, label=clip(body, 90), community=4,
                community_name="quotes", file_type="quote",
                node_kind="quote", norm_label=body.lower(),
                text=f'"{body}"' + (f" — {attrib}" if attrib else ""),
                rationale=f'"{body}"' + (f" — {attrib}" if attrib else ""),
                quote=body, author=attrib or None, source_file=rel,
            )
            # attribute to the author concept when one is linked
            if qm.group(2):
                for am in LINK_RE.finditer(qm.group(2)):
                    tgt = resolve(am.group(1).strip())
                    if tgt:
                        add_link(nid, tgt, "attributed_to", rel)
        add_link(src, nid, "quotes", rel)

# ------------------------------------------------------- 6. directives
# The actionable half of the vault: what the philosophy tells you to DO.
DIRECTIVE_H = re.compile(r"^#{2,3}\s*.*Directives?\s*$", re.I)
for rel, text in raw.items():
    if os.path.basename(rel) == "README.md":
        continue
    src = node_id(rel)
    lines = text.splitlines()
    inside = False
    for i, line in enumerate(lines):
        if line.startswith("#"):
            inside = bool(DIRECTIVE_H.match(line.strip()))
            continue
        if not inside:
            continue
        s = line.strip()
        body = ""
        if s.startswith(("- ", "* ")):
            body = s[2:]
        elif s.startswith("**") and "**" in s[2:]:
            # tech-mappings write `**Title.** prose...` across wrapped lines
            body = s
            j = i + 1
            while j < len(lines) and lines[j].strip() and not lines[j].startswith(("#", "-", "*")):
                body += " " + lines[j].strip()
                j += 1
        if len(body) < 12:
            continue
        body = strip_links(body).replace("**", "").strip()
        nid = "directive_" + slug(rel) + "_" + str(len(
            [n for n in nodes if n.get("node_kind") == "directive"]))
        add_node(
            nid, label=clip(body, 90), community=5,
            community_name="directives", file_type="directive",
            node_kind="directive", norm_label=body.lower()[:120],
            text=body, rationale=body, source_file=rel,
        )
        add_link(src, nid, "directs", rel)

# ------------------------------------------------------------- emit
seen, uniq = set(), []
for l in links:
    key = (l["source"], l["target"], l["relation"])
    if key not in seen:
        seen.add(key)
        uniq.append(l)

graph = {
    "directed": False,
    "multigraph": False,
    "graph": {
        "generator": GENERATOR,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "vault_root": ROOT,
        "source_files": len(FILES),
    },
    "nodes": nodes,
    "links": uniq,
    "hyperedges": [],
}

from collections import Counter
kinds = Counter(n["node_kind"] for n in nodes)
rels = Counter(l["relation"] for l in uniq)

if DRY_RUN:
    print("dry run - nothing written")
else:
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(graph, fh, ensure_ascii=False, indent=2)
    print(f"built {OUT}")
print(f"  nodes: {len(nodes)}  " + " ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
print(f"  links: {len(uniq)}  " + " ".join(f"{k}={v}" for k, v in sorted(rels.items())))
