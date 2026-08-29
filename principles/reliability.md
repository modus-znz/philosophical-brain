# Reliability

> "Simplicity is prerequisite for reliability." — [[Edsger W. Dijkstra]]

**Definition:** The measure of a system's trustworthiness under real conditions.
Reliability is bought by reducing the number of ways the system can fail, not
by accumulating more machinery.

## Core Axiom

You cannot make an unreliable system reliable by adding more parts — you make
it reliable by removing parts until only the necessary, well-understood
mechanism remains. A system that is too complex to reason about is too complex
to trust.

## Supporting Quotes

- [[quotes/craft]] — "We are what we repeatedly do. Excellence, then, is not an act, but a habit." — [[Will Durant]], on [[Aristotle]]
- [[quotes/craft]] — "We are what we repeatedly do. Excellence, then, is not an act, but a habit." — [[Will Durant]], on [[Aristotle]]
- [[quotes/security]] — "Trust, but verify." — Russian proverb
- [[quotes/craft]] — "Whatever you do, do it well." — [[Walt Disney]]

## Code Directives

- Favor flat architectures over deep class hierarchies.
- Reject early optimization — premature complexity is a reliability defect.
- Verify each assumption at its boundary (inputs, API responses, DB state).
- Build repeatable, deterministic behavior; make failure loud and observable.

## Tech Mappings

- [[micro-saas-architecture]]
- [[api-contract-design]]
- [[testing-strategy]]

## Corollaries

- [[simplicity]] — reliability is a property of simple systems
- [[prudence]] — reliability requires anticipating the modes of failure
