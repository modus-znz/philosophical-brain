# Simplicity

> "Simplicity is the ultimate sophistication." — Apple II brochure (1977), after Clare Boothe Luce; no da Vinci source
> "Nature is pleased with simplicity." — [[Isaac Newton]]

**Definition:** Reduce complexity to its necessary minimum. Prefer the smallest,
flattest, least-indirect structure that satisfies the requirement. Complexity
that buys no capability or reliability is waste.

## Core Axiom

The reliable system is the simple system. Every indirection, every layer, every
abstraction is a potential failure point and a tax on comprehension. Make the
complex appear simple is the goal of good engineering.

## Supporting Quotes

- [[quotes/simplicity]] — "The details are not the details. They make the design." — [[Charles Eames]]
- [[quotes/simplicity]] — "Our life is frittered away by detail. Simplify, simplify." — [[Henry David Thoreau]]
- [[quotes/simplicity]] — "The function of good software is to make the complex appear to be simple." — [[Grady Booch]]
- [[quotes/simplicity]] — "Less is more." — [[Ludwig Mies van der Rohe]]
- [[quotes/simplicity]] — "Truth is ever to be found in simplicity, and not in the multiplicity and confusion of things." — [[Isaac Newton]]

## Code Directives

- Favor flat architectures over deep class hierarchies.
- Reject early optimization; optimize against measured evidence.
- One concept, one place — no parallel implementations.
- If a design needs a diagram to be understood by one engineer, it is too complex.

## Tech Mappings

- [[micro-saas-architecture]]
- [[odoo-module-design]]
- [[capacitor-mobile-perf]]
- [[api-contract-design]]

## Corollaries

- [[yagni]] — simplicity without a requirement boundary becomes over-engineering
- [[reliability]] — simplicity is a prerequisite for reliability
