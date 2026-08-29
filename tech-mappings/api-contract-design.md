# API Contract Design

**Domain:** REST/JSON bridge between Odoo and the mobile app (FastAPI bridge),
plus any service-to-service boundary.

- **Governing Principles**: [[first-principles]] · [[simplicity]] · [[reliability]] · [[prudence]]
- **Supporting Quotes**: [[quotes/debugging]] · [[quotes/preparation]] · [[quotes/integrity]]
- **Application:** The contract is the single source of truth both sides agree
  to before any implementation. Design it on paper first — a contract well
  stated is a problem half solved [[quotes/debugging]].

## Engineering Directives

**Define the contract before code.** Agree on endpoints, shapes, and error
semantics first — [[preparation]]. Both the server and the client then build to a
shared, fixed surface — [[first-principles]].

**Version explicitly.** Never break a shipped contract silently. Add `/v2`
rather than mutating request/response shape under a live client.

**Validate at the boundary.** Sanitize and validate every input at the trust
boundary; return explicit, structured errors — [[prudence]]. Fail closed on
ambiguity rather than guessing.

**Keep the surface small and flat.** Fewer endpoints, flat payloads, no nested
surprises — [[simplicity]]. The smallest surface is the most reliable.

**Document the truth.** The contract doc must describe what the API actually
does — no gloss — [[truth-and-integrity]]. A lying doc is a live bug.

## Decision Checklist

1. Is this shape the minimal flat form that serves the client? [[simplicity]]
2. Is every field validated and every failure mode explicit? [[prudence]]
3. Is the contract doc truthful and current? [[truth-and-integrity]]
4. Is the version clear and the change non-breaking? [[reliability]]
5. Was the shape agreed before implementation? [[preparation]]

## Related

- [[capacitor-mobile-perf]] — the client that consumes this contract
- [[odoo-module-design]] — the models this contract exposes
- [[security-hardening]] — auth and transport for the boundary
