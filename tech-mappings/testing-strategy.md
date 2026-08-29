# Testing Strategy

**Domain:** Verifying behavior before it ships — unit, contract, and device/smoke
levels across Modus Labs projects.

- **Governing Principles**: [[truth-and-integrity]] · [[preparation]] · [[resilience]] · [[kaizen]]
- **Supporting Quotes**: [[quotes/validation]] · [[quotes/preparation]] · [[quotes/resilience]]
- **Application:** The test is the honest contract that code must satisfy. It is
  written before or with the code and proves the real behavior — not a
  convenient fiction.

## Engineering Directives

**Prove the real behavior.** Test what the code actually does at its real
boundary, not an over-mocked happy path — [[truth-and-integrity]]. "The proof of
the pudding is in the eating."

**Reproduce before you fix.** A bug is not understood until its failing test is
written — [[preparation]]. "A problem well stated is a problem half solved."

**Make failure a gift.** Every test that catches a real regression is a portal —
turn each caught mistake into a permanent guard — [[resilience]] · [[humility-and-learning]].

**Tighten the loop.** Prefer fast, deterministic tests that run in seconds so the
feedback loop is short and run often — [[kaizen]].

**Test the truth, not the number.** A green build that doesn't exercise real
behavior is a lie; low-value tests that pass on noise are worse than none —
[[truth-and-integrity]].

## Decision Checklist

1. Does this test prove real, observable behavior? [[truth-and-integrity]]
2. Was it written to reproduce a real failure? [[preparation]]
3. Is it fast, deterministic, and run on every change? [[kaizen]]
4. Does it fail loudly and recoverably? [[resilience]]
5. Does passing it actually mean the requirement is met? [[truth-and-integrity]]

## Related

- [[monorepo-policy]] — the gate over each change set
- [[odoo-module-design]] — verifying modules before handoff
- [[capacitor-mobile-perf]] — device/emulator smoke before release
