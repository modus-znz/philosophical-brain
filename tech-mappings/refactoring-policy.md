# Refactoring Policy

**Domain:** Improving existing code without breaking behavior.

- **Governing Principles**: [[kaizen]] · [[simplicity]] · [[reliability]] · [[humility-and-learning]]
- **Supporting Quotes**: [[quotes/refactoring]] · [[quotes/simplicity]] · [[quotes/resilience]]
- **Application:** Change is the only constant in code [[quotes/refactoring]].
  Refactor in small, tested, behavior-preserving slices — never a big-bang
  rewrite.

## Engineering Directives

**Small slices, always green.** Refactor in increments that keep the build and
tests passing — [[kaizen]]. "Little strokes fell great oaks."

**Behavior-preserving.** A refactor changes structure, not semantics. Profilers
and the existing test suite guard that — [[reliability]].

**Remove, then simplify.** "To attain wisdom, remove things every day" [[Lao Tzu]] —
delete dead code, then simplify what remains — [[simplicity]].

**Improve the loop, not just the code.** Refactor also the tooling and process
that produced the mess — shortens the next cycle — [[kaizen]].

**Learn from the old shape.** Understand *why* the code became complex before
simplifying, so the same mistake isn't repeated — [[humility-and-learning]].

## Decision Checklist

1. Is this one behavior-preserving slice, mergeable now? [[kaizen]]
2. Does the existing suite prove the behavior before and after? [[reliability]]
3. Is dead code removed before simplifying? [[simplicity]]
4. Have I understood why the complexity arose? [[humility-and-learning]]
5. Does it stay green and landable? [[kaizen]]

## Related

- [[monorepo-policy]] — the change-set discipline applied to refactors
- [[testing-strategy]] — the guard that makes refactoring safe
