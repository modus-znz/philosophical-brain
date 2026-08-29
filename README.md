# Philosophical Brain — Modus Labs

A knowledge graph of 600 attributed quotations, 13 engineering principles and
93 code directives, built so an agent can ask it a question in the words of the
moment — "the tests are failing", "guide me through a refactor" — and get back
the handful of lines that actually apply, with their provenance attached.

## Quickstart

```bash
git clone <repo> philosophical-brain && cd philosophical-brain
python3 ask.py "the tests are failing"
```

No build step and no dependencies: `ask.py` is standard-library Python and
`graphify-out/graph.json` is committed. A clone is queryable immediately.

```
Moment: tests-failing, tests-passing

  "Ever tried. Ever failed. No matter. Try again. Fail again. Fail better."
      — Samuel Beckett   [quotes/resilience.md]

  "I have not failed. I've just found 10,000 ways that won't work."
      — Thomas Edison   [principles/resilience.md]
```

| Flag | Effect |
|---|---|
| `-n N` | how many quotes to return (default 6) |
| `--no-directives` | omit the `Code directives` block |
| `--json` | machine-readable, for wiring into an agent |
| `--moments` | list the 55 session moments the vault indexes |
| `--graph PATH` | query a graph other than the default |

## What it is for, and what it is not

The vault is plain markdown, so `grep` can search it — and in fact **grep finds
every file `ask.py` returns.** Each theme file names its own session moments in
plain text, so keyword search reaches them. This project makes no claim to find
things keywords cannot.

What it does instead is decide *which* of the matches answer the question, pull
out the specific lines rather than the files containing them, and carry the
attribution along. Measured against the flat-file baseline — grep the vault for
the query's content words, then read every file that matched, which is what an
agent without the graph does:

| Query | `ask.py` | grep + read | |
|---|---:|---:|---:|
| the tests are failing | 338 | 5,926 | 18x |
| guide me through a refactor | 355 | 16,315 | 46x |
| how should I harden this endpoint | 313 | 24,128 | 77x |
| I keep getting distracted | 117 | 8,582 | 73x |
| a code review came back harsh | 141 | 22,859 | 162x |
| **total** | **1,264** | **77,810** | **62x** |

Approximate tokens at 4 chars/token. The win is ranking and extraction, not
recall: same answers, 62x less context, and an agent that can afford to ask.

## Using it from an agent

`ask.py --json` is the portable integration and needs nothing installed.

For MCP, the graph is also served by [Graphify](https://pypi.org/project/graphifyy/)
(`pip install graphifyy`). Register it against **your own** clone path:

```bash
claude mcp add --scope user philosophical-brain -- \
    graphify-mcp "$(pwd)/graphify-out/graph.json"
```

Graphify's own CLI works against the same file:

```bash
graphify query "how should I approach a bug I can't reproduce?"
graphify path "Simplicity" "Reliability"
graphify explain "YAGNI"
```

Note that generic graph traversal ranks by connectivity, and the best-connected
nodes here are documents — so a raw BFS query tends to answer with filenames.
`ask.py` exists because it walks the other way: query → moment → document →
down to the quotes and directives that are the actual answer.

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

## Closing the loop

A wisdom vault has no test suite. Nothing fails when a question gets a
mediocre answer, so nothing tells the curator what to write next. `--record`
is the substitute:

```bash
python3 ask.py "the tests are failing" --record useful
python3 ask.py "how do I handle a bad review" --record dead_end
python3 ask.py "..." --record corrected --note "returned Stoic quotes; wanted craft"

graphify reflect --graph graphify-out/graph.json
```

`reflect` aggregates the outcomes into `graphify-out/reflections/LESSONS.md`,
grouped by graph community: which documents keep answering well, and — the
useful half — which questions the vault could not answer. That dead-end list is
the curation backlog, ordered by how often each gap was actually hit.

Recording is optional and best-effort; without `graphify` installed the query
still answers and prints a note. Outcomes are local session state and are not
committed.

## Provenance tooling

```bash
python3 lint_attributions.py --stats   # class histogram, always exits 0
python3 lint_attributions.py           # list defects
python3 lint_attributions.py --gate    # pre-commit mode: fail on NEW defects
```

`hooks/pre-commit` rebuilds the graph when markdown changes and runs the gate.
Git never installs a cloned repository's hooks by itself — running code from a
clone silently would be a security hole — so this is a deliberate opt-in, one
command per clone:

```bash
git config core.hooksPath hooks
```

That points git at the tracked `hooks/` directory, so any hook added there
later is picked up without a second install step. Bypass a single commit with
`git commit --no-verify`; if you skip the install entirely, run
`python3 lint_attributions.py --gate` yourself before committing.

**Keep that path relative.** `git config core.hooksPath` accepts an absolute
path too, and the result looks identical right up until you use a worktree:
an absolute path pins every worktree to the *main* checkout's hooks, so a hook
edited on a branch never runs, while `bash hooks/pre-commit` in that worktree
runs the edited copy and reports success. The verification passes and the
commit is ungated. A relative `hooks` resolves against each working tree's own
root, which is what you want — verified on both layouts.

The gate that runs here is `python3 engine/verify_policy.py`, unconditionally,
after the attribution gate. It re-resolves every binding in `policy/checks.json`
against the freshly built graph, because `policy/checks.json` can change with
no `.md` in the commit at all.

### Rewording a bound directive

Four directives are quoted verbatim by `policy/checks.json`. Rewording one of
them **fails that commit** until the policy quotes the new wording — that is the
gate doing its job, not a bug. The recovery is one command:

```bash
python3 engine/verify_policy.py --sync
```

It re-quotes `binding.text` from the freshly built graph, touching only the
changed line, and then re-verifies so you see the result rather than a promise.
Three deliberate limits:

- **It never touches `binding.match`.** If your rewording also changed the match
  phrase, the binding no longer resolves and only you know which directive was
  meant. `--sync` says so and stops.
- **It refuses to run against a stale graph.** Syncing before `build_graph.py`
  would re-quote the *old* wording and report success — the drift would survive
  the command that claims to cure it.
- **It is never run by the hook.** Auto-syncing on commit would silently defeat
  the gate. You run it, you read what changed, you commit.

### Measured hook payloads (Phase 0)

`engine/probe.py` observes hook events and changes nothing. It exists so the
enforcement design rests on measurement rather than inference. Wired on
`PostToolUse` and `Stop`, it appends shape-only rows to
`graphify-out/engine/probe.jsonl` — never file contents, never message text.

Three findings from the first session of real rows, all of which simplify the
design they were meant to test:

- **`PostToolUse` for the last tool call of a turn completes before `Stop`
  fires.** Measured 14.2 s apart, in that order, on a turn ending in a tool
  call. This was the open question that decided whether the integrity gate was
  buildable at all: had the two raced, a turn whose final act was *running the
  tests* would carry no record of it when `Stop` read the ledger, and the check
  would have blocked precisely the honest case it exists to reward.

- **Both events carry `prompt_id`.** A turn key, handed over directly. The
  design had scoped turns by parsing `transcript_path` for
  `origin.kind == "human"` — a file measured to be written asynchronously and
  to lag the live turn.

- **`Stop` carries `last_assistant_message`.** The completion claim itself, in
  the payload. The design had read claims from the transcript too.

Together the last two remove *both* of the integrity gate's dependencies on a
file that may not have caught up yet. The gate reads its own ledger, filtered
by `prompt_id`, and gets the claim from the event.

`Stop` also carries `stop_hook_active` (the loop guard), `session_id`, `cwd`,
`permission_mode`, `background_tasks` and `session_crons`.

The probe records `last_assistant_message_len`, never the message. Recording
what the assistant said would put every answer this machine gives into a plain
unencrypted log.

**Kill switch**, honored by the probe and by everything wired after it:

```bash
BRAIN_ENGINE_OFF=1 <command>        # one command
touch ~/.claude/brain-engine-off    # this machine, until removed
```

### Rendering the persona library

`render_persona.py` turns the vault into one flat browsable file grouped by
session moment. **Where it writes is opt-in.** With no configuration it renders
to `persona/wisdom-quotes.generated.md` inside the repo:

```bash
python3 render_persona.py            # in-repo, harmless
python3 render_persona.py --check    # exit 1 if the artifact is stale
```

To have it maintain a file elsewhere — on the author's machine that is
`~/.claude/knowledge/wisdom-quotes.md`, the library a Claude session greps —
drop the destination path into an untracked `.persona-target`:

```bash
echo "$HOME/.claude/knowledge/wisdom-quotes.md" > .persona-target
```

The pre-commit hook re-renders **only** when that file exists, so cloning this
repo and committing never touches your `~/.claude`. Once pointed at a
destination, treat that file as generated: fix the quote in the vault and
re-render, because direct edits are overwritten on the next commit.

## License

MIT — see [LICENSE](LICENSE). The quotations themselves are historical texts
and traditional sayings; the curation, principles, directives and tooling are
what this license covers.

## Index

- **Principles**: [[first-principles]] · [[yagni]] · [[simplicity]] · [[reliability]] · [[preparation]] · [[focus]] · [[patience]] · [[resilience]] · [[prudence]] · [[kaizen]] · [[collaboration]] · [[humility-and-learning]] · [[truth-and-integrity]]
- **Quotes**: [[quotes/simplicity]] · [[quotes/action]] · [[quotes/preparation]] · [[quotes/learning]] · [[quotes/debugging]] · [[quotes/craft]] · [[quotes/progress]] · [[quotes/integrity]] · [[quotes/refactoring]] · [[quotes/security]] · [[quotes/validation]] · [[quotes/resilience]] · [[quotes/patience]] · [[quotes/focus]] · [[quotes/teamwork]] · [[quotes/humility]] · [[quotes/courage]] · [[quotes/rest]] · [[quotes/gratitude]] · [[quotes/general-wisdom]] · [[quotes/contentment]] · [[quotes/ubuntu]] · [[quotes/love]] · [[quotes/freedom]] · [[quotes/justice]] · [[quotes/words]] · [[quotes/emotional-mastery]] · [[quotes/solitude]] · [[quotes/purpose]] · [[quotes/compassion]] · [[quotes/bushido]] · [[quotes/hebrew-wisdom]] · [[quotes/indigenous-wisdom]] · [[quotes/nature]] · [[quotes/exploration]] · [[quotes/creation]] · [[quotes/euphoria]]
- **Traditions**: [[quotes/traditions/chinese-philosophy]] · [[quotes/traditions/zen]] · [[quotes/traditions/taoism]] · [[quotes/traditions/greco-roman]] · [[quotes/traditions/nordic]] · [[quotes/traditions/japanese]] · [[quotes/traditions/old-english]] · [[quotes/traditions/french]] · [[quotes/traditions/german]] · [[quotes/traditions/romanian]] · [[quotes/traditions/world-philosophers]] · [[quotes/traditions/folk-sayings]]
- **Tech Mappings**: [[micro-saas-architecture]] · [[odoo-module-design]] · [[capacitor-mobile-perf]] · [[api-contract-design]] · [[monorepo-policy]] · [[security-hardening]] · [[testing-strategy]] · [[refactoring-policy]]
