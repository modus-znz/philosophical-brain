#!/usr/bin/env python3
"""Ask the Philosophical Brain for wisdom that fits the moment you are in.

WHY THIS EXISTS
---------------
The vault ships a graph, and graphify can traverse it, but a generic BFS is
built for code navigation: it ranks by connectivity, so the first thing it
returns is always the best-connected node. In this vault the best-connected
nodes are *documents*. Ask "what wisdom applies when the tests are failing"
and a raw traversal answers with a list of filenames -- which is exactly what
`grep -l` already gives you, for none of the cost. The payload of this vault
is the leaves: the quotes and the code directives. They sit one hop past the
documents and BFS puts them below the token budget.

So the retrieval here runs the other direction. It resolves the query to the
session moments and documents that match it, then walks *down* to the quotes
and directives those documents carry, and returns the text. The graph earns
its keep on the middle hop: `serves_moment` connects "the tests are failing"
to files whose words never contain "test", which is the one thing grep cannot
do. Everything else is ranking.

USAGE
  python3 ask.py "the tests are failing"
  python3 ask.py "guide me through a refactor" --n 8 --directives
  python3 ask.py "starting a hard task" --json
  python3 ask.py --moments            # what moments the vault knows about
"""
import argparse
import json
import os
import re
import subprocess
import sys

DEFAULT_GRAPH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "graphify-out", "graph.json")

# Words that carry no retrieval signal here. Deliberately short: this vault is
# about ordinary working situations, so most "common" words ("stuck", "hard",
# "done", "wrong") are exactly the ones that should match.
STOP = {
    "a", "an", "the", "i", "im", "am", "is", "are", "be", "was", "were", "for",
    "when", "what", "which", "should", "would", "could", "my", "me", "to", "of",
    "on", "in", "at", "and", "or", "but", "it", "its", "this", "that", "these",
    "with", "how", "do", "does", "did", "give", "get", "some", "any", "about",
    "wisdom", "quote", "quotes", "advice", "something", "need", "want", "help",
    "us", "we", "you", "your", "there", "here", "from", "by", "as", "so",
    # Function words that survive into a natural-sentence query and match
    # almost every document body by chance. "through" alone was enough to
    # let quotes/nature.md tie with quotes/refactoring.md on "guide me
    # through a refactor" -- pure noise outranking the actual answer.
    "through", "into", "out", "up", "down", "over", "under", "after",
    "before", "while", "during", "again", "just", "very", "really", "now",
    "then", "than", "been", "being", "have", "has", "had", "can", "will",
    "shall", "may", "might", "must", "all", "more", "most", "only", "own",
    "same", "too", "such", "if", "am", "let", "lets", "please", "thing",
}

def stem(w):
    """A deliberately crude stemmer -- enough to tie 'failing' to 'tests-failing'
    and 'refactoring' to 'refactor', which is all the matching needs."""
    for suf in ("ingly", "edly", "ing", "ies", "ied", "ed", "es", "s", "ly"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            base = w[: -len(suf)]
            return base[:-1] if suf in ("ies", "ied") else base
    return w

def toks(s):
    out = set()
    for w in re.findall(r"[a-z0-9]+", (s or "").lower()):
        if w in STOP or len(w) < 2:
            continue
        out.add(w)
        out.add(stem(w))
    return out

def overlap(a, b):
    """Fraction of the query covered by a candidate. Query-relative, not
    symmetric: a long document should not be penalised for saying more than
    was asked, but a document matching only one of five query words should
    not outrank one matching four."""
    return len(a & b) / len(a) if a else 0.0


def dice(a, b):
    """Symmetric overlap, for matching a query against a session moment.

    Query-relative overlap is wrong here: it let the single word "code" in
    "a code review came back harsh" match the moment `dead-code-removed` and
    confidently return quotes about deleting things. A moment is a short,
    specific phrase, so a match must account for most of *both* sides. Dice
    does that, and the floor below rejects a one-common-word coincidence."""
    return 2.0 * len(a & b) / (len(a) + len(b)) if (a and b) else 0.0


# Below this, a moment match is a coincidence rather than a signal. Tuned so
# "guide me through a refactor" -> `refactoring` (0.50) and "deleting dead
# code" -> `dead-code-removed` (0.50) survive, while "a code review came back
# harsh" -> `dead-code-removed` (0.20) does not.
MOMENT_FLOOR = 0.25


class Brain:
    def __init__(self, path):
        with open(path, encoding="utf-8") as fh:
            g = json.load(fh)
        self.nodes = {n["id"]: n for n in g["nodes"]}
        self.meta = g.get("graph", {})
        self.out = {}   # id -> [(relation, target)]
        self.inn = {}
        for l in g["links"]:
            self.out.setdefault(l["source"], []).append((l["relation"], l["target"]))
            self.inn.setdefault(l["target"], []).append((l["relation"], l["source"]))
        self.by_kind = {}
        for n in g["nodes"]:
            self.by_kind.setdefault(n.get("node_kind"), []).append(n)
        # Label and body are scored separately. A document titled
        # "Refactoring & Renewal" is a far stronger answer to "refactor" than
        # one that merely uses the word in a sentence, and collapsing both
        # into a single bag of words loses exactly that distinction.
        for n in g["nodes"]:
            n["_ltok"] = toks(n.get("label", ""))
            n["_btok"] = toks(n.get("text") or "")
            n["_tok"] = n["_ltok"] | n["_btok"]

    def moments(self):
        return sorted(n["label"] for n in self.by_kind.get("moment", []))

    def _score_documents(self, q):
        """Two routes into the document set, and the moment route is the one
        the graph exists for. A document scores directly on its own words, and
        again -- more heavily -- if it serves a moment the query names. That
        second route is how "the build is red" reaches a file about patience."""
        scores, why = {}, {}
        for m in self.by_kind.get("moment", []):
            s = dice(q, m["_ltok"])
            if s < MOMENT_FLOOR:
                continue
            for rel, src in self.inn.get(m["id"], []):
                if rel != "serves_moment":
                    continue
                if s * 2.5 > scores.get(src, 0):
                    why[src] = m["label"]
                scores[src] = scores.get(src, 0) + s * 2.5
        for d in self.by_kind.get("document", []):
            s = 1.5 * overlap(q, d["_ltok"]) + 0.6 * overlap(q, d["_btok"])
            if s > 0:
                scores[d["id"]] = scores.get(d["id"], 0) + s
                why.setdefault(d["id"], "topic match")
        return scores, why

    def ask(self, query, n=6, want_directives=True):
        q = toks(query)
        if not q:
            return {"query": query, "moments": [], "quotes": [], "directives": []}
        doc_scores, why = self._score_documents(q)

        # Leaves inherit their document's score, then compete on their own
        # words. A quote in a marginally-relevant file that happens to say
        # exactly the right thing should still win, so the direct lexical
        # term is weighted above the inherited one.
        quotes = {}
        for did, ds in doc_scores.items():
            for rel, tgt in self.out.get(did, []):
                if rel != "quotes":
                    continue
                node = self.nodes[tgt]
                s = ds + 3.0 * overlap(q, node["_tok"])
                if s > quotes.get(tgt, (0, None))[0]:
                    quotes[tgt] = (s, self.nodes[did])
        # A quote can also match on its own, with no document route at all.
        for node in self.by_kind.get("quote", []):
            s = 3.0 * overlap(q, node["_tok"])
            if s > 0 and s > quotes.get(node["id"], (0, None))[0]:
                parent = next((self.nodes[src] for rel, src
                               in self.inn.get(node["id"], [])
                               if rel == "quotes"), None)
                quotes[node["id"]] = (s, parent)

        ranked = sorted(quotes.items(), key=lambda kv: (-kv[1][0], kv[0]))[:n]
        out_quotes = []
        for qid, (s, parent) in ranked:
            node = self.nodes[qid]
            out_quotes.append({
                "quote": node.get("quote") or node["label"],
                "attribution": node.get("author"),
                "source": node.get("source_file"),
                "via": why.get(parent["id"]) if parent else None,
                "score": round(s, 3),
            })

        directives = []
        if want_directives:
            seen = set()
            for did, _ in sorted(doc_scores.items(),
                                 key=lambda kv: -kv[1])[:4]:
                for rel, tgt in self.out.get(did, []):
                    if rel == "directs" and tgt not in seen:
                        seen.add(tgt)
                        directives.append({
                            "directive": self.nodes[tgt].get("text"),
                            "source": self.nodes[tgt].get("source_file"),
                        })
        return {
            "query": query,
            "moments": sorted({v for v in why.values() if v != "topic match"}),
            "quotes": out_quotes,
            "directives": directives[:4],
        }


def render(r):
    if not r["quotes"]:
        return "Nothing in the vault matches that. Try `--moments` to see " \
               "the situations it knows about."
    lines = []
    if r["moments"]:
        lines.append("Moment: " + ", ".join(r["moments"]))
        lines.append("")
    for item in r["quotes"]:
        lines.append('  "%s"' % item["quote"])
        tail = item["attribution"] or "unattributed"
        lines.append("      — %s   [%s]" % (tail, item["source"]))
        lines.append("")
    if r["directives"]:
        lines.append("Code directives:")
        for d in r["directives"]:
            body = " ".join((d["directive"] or "").split())
            lines.append("  • %s" % body)
            lines.append("    [%s]" % d["source"])
    return "\n".join(lines).rstrip()


def record(query, result, outcome, note=None, graph=DEFAULT_GRAPH):
    """Log how an answer actually landed, into graphify's memory dir.

    A wisdom vault has no test suite: nothing fails when a question gets a
    mediocre answer, so nothing tells the curator what to write next. This is
    the substitute. Marking an answer `dead_end` records that the vault was
    asked something it could not answer well, and `graphify reflect` aggregates
    those into graphify-out/reflections/LESSONS.md -- a standing list of the
    gaps, ordered by how often they were hit.

    Best-effort by design: graphify is optional for querying this vault, so a
    missing binary degrades to a note on stderr rather than failing the query
    the user actually asked for.
    """
    answer = "\n".join(
        "%s — %s [%s]" % (q["quote"], q.get("attribution") or "?", q["source"])
        for q in result.get("quotes", []))
    # Cite the documents the answer came from. build_graph.py derives a
    # document id from its path, so "quotes/refactoring.md" -> quotes_refactoring.
    nodes = sorted({
        re.sub(r"\.md$", "", d["source"]).replace("/", "_").replace("-", "_")
        for d in result.get("quotes", []) + result.get("directives", [])
        if d.get("source")})
    cmd = ["graphify", "save-result",
           "--question", query,
           "--answer", answer or "(no match)",
           "--type", "wisdom-retrieval",
           "--outcome", outcome,
           "--memory-dir", os.path.join(os.path.dirname(graph), "memory")]
    if nodes:
        cmd += ["--nodes"] + nodes
    if note:
        cmd += ["--correction", note]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        print("note: graphify not installed; outcome not recorded",
              file=sys.stderr)
        return
    if r.returncode:
        print("note: could not record outcome: %s"
              % (r.stderr or r.stdout).strip()[:200], file=sys.stderr)
    else:
        print("recorded: %s" % outcome, file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(
        description="Retrieve wisdom matching a working situation.")
    ap.add_argument("query", nargs="*", help="the situation you are in")
    ap.add_argument("--graph", default=DEFAULT_GRAPH)
    ap.add_argument("-n", "--n", type=int, default=6,
                    help="how many quotes to return (default 6)")
    ap.add_argument("--no-directives", dest="directives",
                    action="store_false", help="quotes only")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--moments", action="store_true",
                    help="list every session moment the vault indexes")
    ap.add_argument("--record", choices=("useful", "dead_end", "corrected"),
                    help="log how this answer landed, for `graphify reflect`")
    ap.add_argument("--note", help="with --record corrected: what was wrong")
    a = ap.parse_args()

    if not os.path.exists(a.graph):
        sys.exit("no graph at %s — run: python3 build_graph.py ." % a.graph)
    brain = Brain(a.graph)

    if a.moments:
        print("\n".join(brain.moments()))
        return 0
    if not a.query:
        ap.error("give me a situation, or pass --moments")

    q = " ".join(a.query)
    r = brain.ask(q, n=a.n, want_directives=a.directives)
    print(json.dumps(r, ensure_ascii=False, indent=2) if a.json else render(r))
    if a.record:
        record(q, r, a.record, a.note, a.graph)
    return 0 if r["quotes"] else 1


if __name__ == "__main__":
    sys.exit(main())
