# Refactoring & Renewal

- **Core Principles**: [[kaizen]] · [[simplicity]] · [[reliability]] · [[humility-and-learning]]
- **Session Moments**: refactoring/renewal · dead-code-removed
- **Tech Mappings**: [[refactoring-policy]] · [[monorepo-policy]]

> "Every new beginning comes from some other beginning's end." — modern coinage; widely misattributed to [[Seneca]]

> "No man ever steps in the same river twice, for it's not the same river and he's not the same man." — [[Heraclitus]], fragments DK B12/B49a, as commonly rendered

> "When you're finished changing, you're finished." — attributed to [[Benjamin Franklin]]

> "The snake which cannot cast its skin has to die." — [[Friedrich Nietzsche]]

> "Renew thyself completely each day; do it again, and again, and forever again." — Chinese inscription cited by [[Henry David Thoreau]] (*Walden*)

> "It is not the strongest of the species that survives, but the one most responsive to change." — [[Leon C. Megginson]] (1963), paraphrasing [[Charles Darwin]]

> "Change is the only constant in life." — modern aphorism summarising [[Heraclitus]]; not a surviving fragment

> "We shape our buildings; thereafter they shape us." — [[Winston Churchill]]

> "There is nothing permanent except change." — [[Heraclitus]], as paraphrased in later doxography; not a surviving fragment

## Code Directive

Refactor in small, behavior-preserving slices that keep the build green. Remove
dead code, then simplify what remains — understand why the complexity arose
first.
