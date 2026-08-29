# Resilience

> "What lies behind us and what lies before us are tiny matters compared to what lies within us." — attributed to [[Ralph Waldo Emerson]]
> "Fall seven times, stand up eight." — Japanese proverb

**Definition:** The capacity to fail and recover — in systems, in delivery, and
in the engineer. Resilience is designed in before the failure, and cultivated
in the engineer through each setback.

## Core Axiom

Failure is data, not verdict. Systems gain resilience from graceful degradation
and fast recovery; engineers gain it from treating each failure as a lesson
that sharpens the next attempt. "He conquers who endures." — [[Persius]]

## Supporting Quotes

- [[quotes/resilience]] — "It always seems impossible until it's done." — [[Nelson Mandela]]
- [[quotes/resilience]] — "Failure is simply the opportunity to begin again, this time more intelligently." — [[Henry Ford]]
- [[quotes/resilience]] — "I have not failed. I've just found 10,000 ways that won't work." — [[Thomas Edison]]
- [[quotes/resilience]] — "Our greatest glory is not in never falling, but in rising every time we fall." — [[Confucius]]
- [[quotes/resilience]] — "every adversity carries with it the seed of an equal or greater benefit." — [[Napoleon Hill]]

## Code Directives

- Design for graceful degradation: partial failure must not take down the whole.
- Make failures recoverable — idempotent retries, atomic writes, clear rollback.
- Log enough to diagnose post-mortem; treat every incident as a system improvement.
- After a bug, add a test or a guard so that class of failure cannot recur silently.

## Tech Mappings

- [[micro-saas-architecture]]
- [[api-contract-design]]
- [[security-hardening]]

## Corollaries

- [[patience]] — recovery requires enduring the setback
- [[kaizen]] — each failure feeds the next improvement
