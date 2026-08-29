# Odoo Module Design

**Domain:** Custom Odoo 19 modules (prefix `zanzibar_fm`), Python 3 + XML views.

- **Governing Principles**: [[simplicity]] · [[yagni]] · [[first-principles]] · [[reliability]]
- **Supporting Quotes**: [[quotes/simplicity]] · [[quotes/craft]] · [[quotes/refactoring]]
- **Session Moments**: building · craft
- **Application:** Custom features carved cleanly onto the Odoo ORM without
  fighting the framework's grain. Add the smallest model/view/action that meets
  the real requirement.

## Engineering Directives

**One concept, one model.** Model each concept once, with the minimal field set —
[[simplicity]]. Extend a base model with inheritance where the domain demands it,
not where convenience tempts.

**Respect the framework grain.** Odoo provides search, security (`ir.rule`),
and ORM persistence. Build on these instead of re-implementing them —
[[first-principles]] says know what the platform already answers.

**No speculative fields/workflows.** Add a status, a state machine, or a field
only when a real workflow requires it — [[yagni]]. Remove an unused computed
field the day nothing consumes it.

**Views mirror the model.** Keep views as thin as possible over the model;
complex view logic is a smell that belongs in the model or a computed field.

**Reliability by construction.** Use `@api.constrains` for invariants and
`ir.rule`/record rules for access — [[prudence]]. Never trust the UI to keep
data consistent.

## Decision Checklist

1. Is this on the ORM the idiomatic way — no fighting the framework? [[first-principles]]
2. Is the model the minimal field set for the requirement? [[simplicity]]
3. Is every field/workflow consumed by a real path? [[yagni]]
4. Are invariants enforced in the model, not the view? [[reliability]]
5. Does it restart clean and pass a smoke test before handoff? [[preparation]]

## Related

- [[micro-saas-architecture]] — shared axioms, different terrain
- [[api-contract-design]] — the REST bridge exposing models to clients
- [[testing-strategy]] — verifying modules before they ship
