# Philosophical Brain — Modus Labs

A queryable, localized semantic knowledge graph distilled from the raw
philosophical-quote collection. Serves as the core decision-making and logic
library for development workflows across Claude Code CLI and Opencode.

Built on **Graphify** (`graphifyy` via PyPI) — query it with:

```bash
graphify query "how should I approach a bug I can't reproduce?"
graphify path "Simplicity" "Reliability"
graphify explain "YAGNI"
graphify --mcp        # Full MCP stdio server for agent access
```

## Vault Anatomy

| Directory | Purpose | File pattern |
|---|---|---|
| `principles/` | High-level axioms distilled from groups of quotes | `first-principles.md`, `yagni.md` |
| `quotes/` | The raw wisdom, grouped by theme, mapped to principles | `simplicity.md`, `bug-found.md` |
| `quotes/traditions/` | Lineage indexes: one per wisdom tradition, mapping authors + themes | `chinese-philosophy.md`, `japanese.md` |
| `tech-mappings/` | Applied logic for Modus Labs domains | `micro-saas-architecture.md` |

## Linking Convention

The vault uses **bidirectional Obsidian-style wikilinks** (`[[Concept]]`). Every
quote file links:
- **up** to its `[[Principle|principles]]` (via `Core Principle` fields)
- **across** to `[[Tech-Mapping|tech-mappings]]` it informs
- **back** to its `[[Author]]`

Principles and tech-mappings link back to the quote files that support them,
so the graph is fully navigable in both directions.

## File Schemas

Four schemas, one per directory. Each is used consistently; none was documented
before. Every file opens with an `# H1` title, then a metadata bullet block,
then content.

### `quotes/` and `quotes/traditions/` — theme files

One file per *theme* (not per quote), holding many quotations.

```markdown
# Progress & Kaizen

- **Core Principles**: [[kaizen]] · [[patience]] · [[focus]]
- **Session Moments**: step-complete · writing/building
- **Tech Mappings**: [[monorepo-policy]] · [[refactoring-policy]]

> "Quote text." — [[Author]] (*Work*, locus)

> "Another quote." — Tradition proverb
```

Bullet values are separated by ` · `. `quotes/traditions/` files add `##
Heritage`, `## Lineage`, and `## Signature Sayings` sections; their cross-
reference bullets take the form `- "quote" — Author → see [[theme]]`.

### `principles/` — axiom files

```markdown
# Kaizen — Continuous Improvement

> "Epigraph quote." — [[Author]]

**Definition:** what the principle means, and what it means in engineering.

## Core Axiom
## Supporting Quotes      (bullets: - [[quotes/theme]] — "quote" — [[Author]])
## Code Directives        (bullets: one actionable instruction each)
## Tech Mappings
```

### `tech-mappings/` — applied-domain files

```markdown
# API Contract Design

**Domain:** where this applies.

- **Governing Principles**: [[first-principles]] · [[simplicity]]
- **Supporting Quotes**: [[quotes/debugging]] · [[quotes/preparation]]
- **Application:** how the principles translate to concrete engineering.

## Engineering Directives
**Directive title.** Prose, citing the principles it rests on — [[prudence]].
```

## Attribution Convention

An audit against primary sources found one clean split: **every quote cited to
a locus was correct, and almost every quote cited to a bare name was not.**
Twenty misattributions were corrected on that basis. To keep the default
honest, an attribution must be one of:

| Form | Means | Example |
|---|---|---|
| `[[Author]], *Work* locus` | Verified primary source | `[[Marcus Aurelius]], *Meditations* 2.5` |
| `[[Author]] (year)` | Verified, modern, no classical locus | `[[Frank Outlaw]] (1977)` |
| `X proverb` | Genuine traditional saying | `East African saying` |
| `modern coinage; ... misattributed to [[X]]` | Circulates widely, no real source | see `quotes/compassion.md` |
| `[[A]], after [[B]]` / `as rendered in X` | Paraphrase or derivation | `[[Will Durant]], on [[Aristotle]]` |

**A bare `[[Author]]` with no locus, year, or hedge is a claim of verified
primary-source provenance.** Treat it as a defect until checked — that is the
form all twenty errors took. When correcting one, keep the quote and fix the
provenance; and re-sync the `Supporting Quotes` bullets in `principles/`, which
historically stripped whatever hedge the theme file carried.

## Building the Graph

`build_graph.py` is the canonical builder — **not** `graphify update`, whose
extractor sees only pages and headings and therefore drops every quote body,
every Code Directive and all 55 session moments.

```bash
python3 build_graph.py .            # rebuild graphify-out/graph.json
python3 build_graph.py . --dry-run  # counts only, writes nothing
```

It emits five node kinds — `document`, `concept`, `quote` (full text +
attribution), `moment`, `directive` — over relations `cites`, `quotes`,
`attributed_to`, `serves_moment`, `directs`, so that
**situation → moment → document → quote** is a real graph path. Rerun it after
editing any `.md` file; it refuses to overwrite a graph it did not generate
unless given `--force`.

## Index

- **Principles**: [[first-principles]] · [[yagni]] · [[simplicity]] · [[reliability]] · [[preparation]] · [[focus]] · [[patience]] · [[resilience]] · [[prudence]] · [[kaizen]] · [[collaboration]] · [[humility-and-learning]] · [[truth-and-integrity]]
- **Quotes**: [[quotes/simplicity]] · [[quotes/action]] · [[quotes/preparation]] · [[quotes/learning]] · [[quotes/debugging]] · [[quotes/craft]] · [[quotes/progress]] · [[quotes/integrity]] · [[quotes/refactoring]] · [[quotes/security]] · [[quotes/validation]] · [[quotes/resilience]] · [[quotes/patience]] · [[quotes/focus]] · [[quotes/teamwork]] · [[quotes/humility]] · [[quotes/courage]] · [[quotes/rest]] · [[quotes/gratitude]] · [[quotes/general-wisdom]] · [[quotes/contentment]] · [[quotes/ubuntu]] · [[quotes/love]] · [[quotes/freedom]] · [[quotes/justice]] · [[quotes/words]] · [[quotes/emotional-mastery]] · [[quotes/solitude]] · [[quotes/purpose]] · [[quotes/compassion]] · [[quotes/bushido]] · [[quotes/hebrew-wisdom]] · [[quotes/indigenous-wisdom]] · [[quotes/nature]] · [[quotes/exploration]] · [[quotes/creation]] · [[quotes/euphoria]]
- **Traditions**: [[quotes/traditions/chinese-philosophy]] · [[quotes/traditions/zen]] · [[quotes/traditions/taoism]] · [[quotes/traditions/greco-roman]] · [[quotes/traditions/nordic]] · [[quotes/traditions/japanese]] · [[quotes/traditions/old-english]] · [[quotes/traditions/french]] · [[quotes/traditions/german]] · [[quotes/traditions/romanian]] · [[quotes/traditions/world-philosophers]] · [[quotes/traditions/folk-sayings]]
- **Tech Mappings**: [[micro-saas-architecture]] · [[odoo-module-design]] · [[capacitor-mobile-perf]] · [[api-contract-design]] · [[monorepo-policy]] · [[security-hardening]] · [[testing-strategy]] · [[refactoring-policy]]
