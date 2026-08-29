# Monorepo Policy

**Domain:** Organization of code across Modus Labs repos (Hotel App, Odoo
addons, tooling).

- **Governing Principles**: [[collaboration]] · [[kaizen]] · [[simplicity]] · [[yagni]]
- **Supporting Quotes**: [[quotes/teamwork]] · [[quotes/progress]] · [[quotes/simplicity]]
- **Session Moments**: git/git-commit · push
- **Application:** One project, one coherent change set where practical;
  independent, versioned units where boundaries genuinely differ.

## Engineering Directives

**Shared code is shared context.** Changes that must land together belong in the
same change set so review and release stay atomic — [[collaboration]].

**Small, safe increments everywhere.** Commit one logical fix or feature at a
time with a clear message; keep each change landable — [[kaizen]]. "Step by step
walk the thousand-mile road."

**Document the why.** Write the reasoning behind a change in the commit and the
design note, not only the mechanism — [[collaboration]].

**Don't spin up a package for one consumer.** Extract a shared library only when
a second real consumer appears — [[yagni]].

**Review is a gate.** Non-trivial changes pass review before merge; the second
viewpoint is a reliability control — [[collaboration]] · [[reliability]].

## Decision Checklist

1. Can this change land atomically with its deps? [[collaboration]]
2. Is it one commit / one logical change? [[kaizen]]
3. Is the "why" recorded for the next reader? [[collaboration]]
4. Is this a premature shared-package, or a real second consumer? [[yagni]]
5. Does it pass review and the test gate? [[reliability]]

## Related

- [[micro-saas-architecture]] — the product inside the monorepo
- [[testing-strategy]] — the gate over every change set
