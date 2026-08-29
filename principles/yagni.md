# YAGNI — You Aren't Gonna Need It

> "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away." — [[Antoine de Saint-Exupéry]]
> "To attain knowledge, add things every day. To attain wisdom, remove things every day." — [[Lao Tzu]]

**Definition:** Do not build for hypothetical future requirements. Build for the
requirement you have today. Defer speculative complexity until a real user or a
real requirement demands it.

## Core Axiom

Every line of code that does not serve an existing, concrete requirement is
deferred debt — not an asset. The cost of building it too early includes the
build cost, the maintenance cost, and the design rigidity it bakes in before
you understand the actual problem.

## Supporting Quotes

- [[quotes/simplicity]] — "It is not a daily increase, but a daily decrease. Hack away at the inessentials." — [[Bruce Lee]]
- [[quotes/simplicity]] — "Besides the noble art of getting things done, there is the noble art of leaving things undone." — [[Lin Yutang]]
- [[quotes/simplicity]] — "Everything should be made as simple as possible, but not simpler." — [[Albert Einstein]]

## Code Directives

- Do not extract an abstraction until it is used by a second call site.
- Do not add a config flag until a second environment needs a different value.
- Do not abstract a store, an adapter, or a gateway until a real second implementation exists.
- Remove code the moment its only job is to serve a future that has not arrived.

## Tech Mappings

- [[micro-saas-architecture]]
- [[odoo-module-design]]
- [[monorepo-policy]]

## Corollaries

- [[simplicity]] — YAGNI is the operational form of simplicity
- [[first-principles]] — speculative features answer no real question
