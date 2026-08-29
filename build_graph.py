#!/usr/bin/env python3
"""Deterministic graphify-compatible knowledge graph builder for the
Philosophical Brain vault (~/philosophical-brain).

The vault is a fully-linked Markdown wiki: its semantic graph IS the set of
[[wikilinks]]. Building it from the links is exact, complete and zero-cost
(every edge is a real authored link), unlike a lossy LLM backend which dropped
27/50 files on extraction. Output is standard graphify node-link JSON at
graphify-out/graph.json, consumed unchanged by `graphify query|path|explain`
and `graphify-mcp`.

Usage: python3 build_graph.py <vault-root>
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(sys.argv[1])

# Default output is NOT the live graph. `graphify update` is the canonical
# builder for this vault: its graph carries heading-level nodes and semantic
# community structure that a wikilink-only walk cannot represent. This script
# is a deterministic CROSS-CHECK — it catches literal [[links]] that graphify's
# extraction misses. Writing it over graphify's output silently destroys that
# structure, so that requires an explicit --force.
FORCE = "--force" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
_out = [a for a in sys.argv[2:] if not a.startswith("-")]
OUT = os.path.abspath(_out[0]) if _out else os.path.join(
    ROOT, "graphify-out", "graph.wikilinks.json")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

if os.path.exists(OUT) and not FORCE and not DRY_RUN:
    try:
        _existing = json.load(open(OUT))
        _native = any(
            n.get("node_kind") == "heading" or "_origin" in n
            for n in _existing.get("nodes", [])
        )
    except Exception:
        _native = False
    if _native:
        sys.exit(
            f"refusing to overwrite {OUT}: it was produced by graphify "
            f"(heading nodes / _origin present), not by this script.\n"
            f"Use --out PATH to write elsewhere, or --force to override."
        )

FILES = sorted(glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True))
FILES = [f for f in FILES
         if not f.startswith(os.path.join(ROOT, "graphify-out"))]

LINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def slug(name):
    base = re.sub(r"[^A-Za-z0-9]+", "_", name.lower()).strip("_")
    return base or "node"


def node_id(path_rel):
    base = os.path.splitext(os.path.basename(path_rel))[0]
    return slug(os.path.dirname(path_rel) + "_" + base)


def norm(label):
    return label.replace("-", " ").lower().strip()


# 1. Document nodes
doc_meta = {}
for f in FILES:
    rel = os.path.relpath(f, ROOT)
    text = open(f, encoding="utf-8").read()
    first_h1 = re.search(r"^# (.+)$", text, re.M)
    first_line = next((l for l in text.splitlines() if l.strip()), "")
    doc_meta[rel] = (first_h1.group(1) if first_h1 else "").strip() or first_line.strip()

PLACEHOLDERS = {"concept", "principle", "tech-mapping", "author"}
doc_basenames = {os.path.basename(r) for r in doc_meta}
doc_stem = {os.path.splitext(os.path.basename(r))[0]: r for r in doc_meta}

nodes = []
node_ids = set()
for rel, label in doc_meta.items():
    nid = node_id(rel)
    nodes.append({
        "id": nid,
        "label": label,
        "community": 1,  # doc community
        "file_type": "document",
        "norm_label": norm(label),
        "rationale": "",
        "source_file": rel,
    })
    node_ids.add(nid)

# 2. Object references (authors, principles, mappings rendered via links)
object_cites = {}  # norm_label -> set(files)
raw_label = {}      # norm_label -> authored label
for f in FILES:
    rel = os.path.relpath(f, ROOT)
    text = open(f, encoding="utf-8").read()
    for m in LINK_RE.finditer(text):
        link = m.group(1).strip()
        nm = norm(link)
        start = m.start()
        if text[max(0, start - 1):start] == "`":
            continue
        obj = nm.split("/")[-1]
        if obj in PLACEHOLDERS:
            continue
        if os.path.splitext(link.split("/")[-1])[0] in doc_stem:
            # resolve to matching doc node below
            continue
        object_cites.setdefault(nm, set()).add(rel)
        raw_label.setdefault(nm, link)

ref_nodes = {}
for nm in sorted(object_cites):
    nid = "obj_" + slug(nm)
    if nid in node_ids:
        continue
    # only add a ref node if cited >=1 times (always) and not shadowed by doc
    if os.path.splitext(nm)[0] in doc_stem:
        continue
    ref_nodes[nm] = nid
    nodes.append({
        "id": nid,
        "label": raw_label[nm].title(),
        "community": 2,  # concept community
        "file_type": "concept",
        "norm_label": nm,
        "rationale": "",
        "source_file": None,
    })
    node_ids.add(nid)

# 3. Links
links = []
for f in FILES:
    rel = os.path.relpath(f, ROOT)
    src_id = node_id(rel)
    text = open(f, encoding="utf-8").read()
    for m in LINK_RE.finditer(text):
        link = m.group(1).strip()
        start = m.start()
        if text[max(0, start - 1):start] == "`":
            continue
        base = link.split("/")[-1]
        stem = os.path.splitext(base)[0]
        nm = norm(link)
        if stem in PLACEHOLDERS:
            continue
        if stem in doc_stem:
            target = node_id(doc_stem[stem])
        elif nm in ref_nodes:
            target = ref_nodes[nm]
        else:
            continue
        if target == src_id:
            continue
        links.append({
            "source": src_id,
            "target": target,
            "relation": "cites",
            "confidence": "EXTRACTED",
            "confidence_score": 1.0,
            "source_file": rel,
        })

seen = set()
uniq = []
for l in links:
    key = (l["source"], l["target"], l["relation"])
    if key in seen:
        continue
    seen.add(key)
    uniq.append(l)

graph = {
    "directed": False,
    "multigraph": False,
    "graph": {},
    "nodes": nodes,
    "links": uniq,
    "hyperedges": [],
}

with open(OUT, "w", encoding="utf-8") as fh:
    json.dump(graph, fh, ensure_ascii=False, indent=2)

doc_count = sum(1 for n in nodes if n["file_type"] == "document")
concept_count = sum(1 for n in nodes if n["file_type"] == "concept")
print(f"built {OUT}")
print(f"  nodes: {len(nodes)} (docs {doc_count}, concepts {concept_count})")
print(f"  links: {len(uniq)}")

