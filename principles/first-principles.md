# First Principles

> "To find yourself, think for yourself." — modern coinage; widely misattributed to [[Socrates]]
> "When you have eliminated the impossible, whatever remains, however improbable, must be the truth." — [[Arthur Conan Doyle]]

**Definition:** Reason from the ground up. Strip every claim down to what is
verifiably true, then rebuild your conclusion from those irreducible facts —
never from inherited assumptions, convention, or "the way we've always done it."

## Core Axiom

Every decision in engineering must trace back to a first principle: a
non-negotiable truth about the system, the user, or the business that cannot be
further decomposed. If a layer of a design exists only because "it's standard
practice," it fails the first-principles test.

## Supporting Quotes

- [[quotes/debugging]] — "Doubt is the origin of wisdom." — [[René Descartes]]
- [[quotes/debugging]] — "The first principle is that you must not fool yourself — and you are the easiest person to fool." — [[Richard Feynman]]
- [[quotes/debugging]] — "Seek not the answer, but to understand the question." — Zen saying
- [[quotes/general-wisdom]] — "The unexamined life is not worth living." — [[Socrates]]

## Code Directives

- Ask **why** at every layer; delete any layer without a defensible answer.
- Reject "best practice" as a reason — demand the underlying mechanism.
- Understand the failing component fully before touching the code that calls it.
- Reduce every bug to its irreducible cause; treat observed symptoms as hypotheses, not conclusions.

## Tech Mappings

- [[micro-saas-architecture]]

## Corollaries

- [[simplicity]] — first principles produce the smallest valid system
- [[yagni]] — don't build layers that answer no real question
