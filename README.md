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

## Quote Schema

```markdown
# "Quote text" — Author

- **Author**: [[Author]]
- **Tradition**: Stoicism / Taoism / ...
- **Core Principle**: [[Simplicity]]
- **Tech Mapping**: [[Micro-SaaS Architecture]]
- **Code Directive**: actionable engineering instruction distilled from the quote
- **Session Moment**: task-start / bug-found / ... (which dev moment it serves)
```

## Tech-Mapping Schema

```markdown
# Domain

- **Governing Principles**: [[YAGNI]], [[Simplicity]]
- **Supporting Quotes**: [[quotes/simplicity]], ...
- **Application**: how the principles translate to concrete engineering in this domain
```

## Index

- **Principles**: [[first-principles]] · [[yagni]] · [[simplicity]] · [[reliability]] · [[preparation]] · [[focus]] · [[patience]] · [[resilience]] · [[prudence]] · [[kaizen]] · [[collaboration]] · [[humility-and-learning]] · [[truth-and-integrity]]
- **Quotes**: [[quotes/simplicity]] · [[quotes/action]] · [[quotes/preparation]] · [[quotes/learning]] · [[quotes/debugging]] · [[quotes/craft]] · [[quotes/progress]] · [[quotes/integrity]] · [[quotes/refactoring]] · [[quotes/security]] · [[quotes/validation]] · [[quotes/resilience]] · [[quotes/patience]] · [[quotes/focus]] · [[quotes/teamwork]] · [[quotes/humility]] · [[quotes/courage]] · [[quotes/rest]] · [[quotes/gratitude]] · [[quotes/general-wisdom]] · [[quotes/contentment]] · [[quotes/ubuntu]] · [[quotes/love]] · [[quotes/freedom]] · [[quotes/justice]] · [[quotes/words]] · [[quotes/emotional-mastery]] · [[quotes/solitude]] · [[quotes/purpose]] · [[quotes/compassion]] · [[quotes/bushido]] · [[quotes/hebrew-wisdom]] · [[quotes/indigenous-wisdom]] · [[quotes/nature]] · [[quotes/exploration]] · [[quotes/creation]] · [[quotes/euphoria]]
- **Traditions**: [[quotes/traditions/chinese-philosophy]] · [[quotes/traditions/zen]] · [[quotes/traditions/taoism]] · [[quotes/traditions/greco-roman]] · [[quotes/traditions/nordic]] · [[quotes/traditions/japanese]] · [[quotes/traditions/old-english]] · [[quotes/traditions/french]] · [[quotes/traditions/german]] · [[quotes/traditions/romanian]] · [[quotes/traditions/world-philosophers]] · [[quotes/traditions/folk-sayings]]
- **Tech Mappings**: [[micro-saas-architecture]] · [[odoo-module-design]] · [[capacitor-mobile-perf]] · [[api-contract-design]] · [[monorepo-policy]] · [[security-hardening]] · [[testing-strategy]] · [[refactoring-policy]]
