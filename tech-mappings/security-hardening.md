# Security Hardening

**Domain:** Protecting Modus Labs systems, credentials, and data.

- **Governing Principles**: [[prudence]] · [[reliability]] · [[truth-and-integrity]]
- **Supporting Quotes**: [[quotes/security]] · [[quotes/preparation]]
- **Application:** Security is a state of mind, not a gadget — designed in by
  default, anticipated before impact, and never left to a final pass.

## Engineering Directives

**Prevention before cure.** Engage the risk while it is cheap — [[prudence]].
Seal the crack before it becomes a wall ("Usipoziba ufa, utajenga ukuta").

**Trust, but verify.** Never assume a dependency, a layer, or an upstream
behaves — validate at every trust boundary — [[prudence]] · [[reliability]].

**Secrets are never code.** No hardcoded keys, tokens, or passwords; keep them
in scoped env/secret stores, chmod-secured, and never committed — [[integrity]].

**Least privilege.** Grant the minimum access a credential or role needs; scope
it, rotate it, and revoke it when unused.

**Fail closed.** On ambiguity — unidentified input, missing auth, unclear state —
refuse, log, and alert rather than guess — [[prudence]].

## Decision Checklist

1. Is every input validated at its trust boundary? [[prudence]]
2. Are all secrets externalized and access least-privileged? [[integrity]]
3. Does it fail closed, not open, on ambiguity? [[prudence]]
4. Is the failure mode anticipated before impact? [[preparation]]
5. Is behavior observable (logged/altered) so abuse surfaces? [[reliability]]

## Related

- [[api-contract-design]] — hardening the transport/auth boundary
- [[micro-saas-architecture]] — defense across the product
