# Micro-SaaS Architecture

**Domain:** Single-product, single-team SaaS — the Modus Labs core pattern.

- **Governing Principles**: [[simplicity]] · [[yagni]] · [[reliability]] · [[first-principles]] · [[kaizen]]
- **Supporting Quotes**: [[quotes/simplicity]] · [[quotes/action]] · [[quotes/validation]]
- **Session Moments**: planning · strategy
- **Application:** A tiny, focused product held together by the smallest
  defensible stack. Each decision must trace to a first principle, and no
  component exists unless a real requirement or a real user demands it.

## Engineering Directives

**Flat architecture.** Favor a flat structure over deep class hierarchies —
[[simplicity]]. A single table, a single handler, a single service is easier to
reason about and therefore more reliable [[reliability]].

**Ship the minimum.** Build for the requirement that exists today, not the one
you imagine in six months — [[yagni]]. Defer billing, multi-tenancy, and role
systems until a real need arrives.

**Composite over speculative abstraction.** Do not add a store adapter, a
message queue, or an event bus until a second, concrete consumer exists.

**Compounding delivery.** Release small, working increments continuously —
[[kaizen]] — rather than a single heroic launch. Each small release tightens the
feedback loop.

**Prudent defaults.** Validate all inputs, least-privilege credentials, fail
closed on ambiguity — [[prudence]]. Do the secure thing by default so safety is
never an afterthought.

## Decision Checklist

1. Does this component answer a first-principles question? [[first-principles]]
2. Is there a real user or requirement demanding it now? [[yagni]]
3. Is this the simplest structure that works? [[simplicity]]
4. What failure mode does it introduce, and is it anticipated? [[prudence]]
5. Can it ship incrementally this week? [[kaizen]]

## Related

- [[odoo-module-design]] — same axioms, Odoo ORM/XML terrain
- [[api-contract-design]] — the contract between this app and its clients
- [[monorepo-policy]] — how the codebase of the product is organized
