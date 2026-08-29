# Capacitor Mobile Performance

**Domain:** Capacitor-wrapped mobile app (Hotel Facility Management App), WebView
JS + native bridge, mobile-first and performance-sensitive.

- **Governing Principles**: [[simplicity]] · [[kaizen]] · [[focus]] · [[reliability]]
- **Supporting Quotes**: [[quotes/simplicity]] · [[quotes/craft]] · [[quotes/action]]
- **Application:** A snappy, native-feeling app on constrained device resources.
  Performance is a property of removing waste, not of adding machinery.

## Engineering Directives

**Performance is subtraction.** Profile first, then remove — reduce re-renders,
payloads, and bridge round-trips — [[simplicity]]. "Less is more."

**The WebView bridge is the bottleneck.** Batch native-plugin calls and state
syncs; a chatty bridge is the prime latency source. Minimize and coalesce.

**Measure against evidence.** Optimize only what profiling shows is slow, and
verify each change moves the measured number — [[kaizen]]. Never earlier,
never by feel.

**Incremental delivery to the device.** Every screen change ships as a small,
testable increment — [[kaizen]] — with a device/emulator smoke test before
release.

**Stay focused per screen.** Build one screen's flow to completion before the
next — [[focus]] — so each landable slice is coherent and fast.

## Decision Checklist

1. Is this render/bridge call necessary, or removable? [[simplicity]]
2. Have I measured the hotspot before optimizing? [[kaizen]]
3. Does the change ship as a landable increment? [[kaizen]]
4. Has it passed an emulator smoke test? [[preparation]]
5. Does it degrade gracefully on a low-end device? [[resilience]]

## Related

- [[micro-saas-architecture]] — the backend this client talks to
- [[api-contract-design]] — the contract shaping payload size
- [[testing-strategy]] — verifying screen behavior
