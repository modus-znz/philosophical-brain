# Prudence

> "An ounce of prevention is worth a pound of cure." — [[Benjamin Franklin]]
> "The wise man does at once what the fool does finally." — attributed to [[Niccolò Machiavelli]]

**Definition:** Foresee the modes of failure and act to prevent them before they
arrive. Prudence is not fear — it is informed anticipation, the difference
between the wise and the fool being simply *when* each responds to risk.

## Core Axiom

Engage risk while it is cheap. A vulnerability, a data leak, a corrupt write is
far cheaper to prevent at design time than to repair after production impact.
"Trust, but verify" — never assume a layer you depend on will behave.

## Supporting Quotes

- [[quotes/security]] — "The superior man, when resting in safety, does not forget that danger may come." — [[Confucius]]
- [[quotes/security]] — "Forewarned is forearmed." — Latin proverb
- [[quotes/security]] — "Better a thousand times careful than once dead." — proverb
- [[quotes/preparation]] — "The time to repair the roof is when the sun is shining." — [[John F. Kennedy]]
- [[quotes/security]] — "He who is prudent and lies in wait for an enemy who is not, will be victorious." — [[Sun Tzu]]

## Code Directives

- Validate and sanitize all inputs at their trust boundary.
- Encrypt secrets at rest and in transit; least-privilege every credential.
- Back up before destructive operations; snapshot before migration.
- Fail closed on ambiguity — refuse, log, and alert rather than guess.

## Tech Mappings

- [[security-hardening]]
- [[api-contract-design]]
- [[micro-saas-architecture]]

## Corollaries

- [[preparation]] — prudence is preparation for contingencies
- [[reliability]] — a prudent system fails safely, not silently
