## Context

The driver chrome (ADR-056 stage 3c) decides its content in
`controls.ts` as pure data and renders it in `viewer.ts`. One formatter,
`formatDisplay`, serves two different jobs today: the readout beside a
slider, and the value written into the number field a range-less driver
gets. It rounds to 6 decimals and then strips trailing zeros
(`String(Number(value.toFixed(6)))`), which is right for a field a maker
types into and wrong for a value that changes 60 times a second under a
drag — the string's width changes with every digit, and the sign appears
and disappears across zero.

The readout is also written as one string, `"<value> <unit>"`, into a
right-aligned `<output>`. Right-aligning that string aligns the *unit*,
not the number, so the digits still walk left and right underneath it.
The panel's font is `system-ui`, whose digits are proportional: `1` is
narrower than `0`, so even a constant digit count shifts.

## Goals / Non-Goals

**Goals:**

- The readout's digits, sign, and unit stay at fixed screen positions
  while a driver moves.
- The change is presentation-only: no value, conversion, range,
  pinning, or driving-API behaviour moves.

**Non-Goals:**

- Choosing the decimal count per driver, or deriving it from the
  driver's `scale` or `dtype`. Four places, fixed, for every driver;
  the pilot asked for that explicitly and for now.
- Changing the number field a range-less driver gets. It is an input,
  not a readout.
- Any wider typographic pass over the panel.

## Decisions

**D1 — A second formatter, not a changed one.** Add
`formatReadout(value)` returning `value.toFixed(4)` and leave
`formatDisplay` alone. The two callers want opposite things: a readout
wants a constant shape, an input wants the shortest faithful number a
maker can edit without the field rewriting what they typed. Collapsing
them would make the number field rewrite `2.5` to `2.5000` on every
external driver change. Alternative considered: one formatter with a
`places` argument — rejected because the call sites then carry the
policy, and the policy is what this change is about.

**D2 — `toFixed(4)`, keeping the trailing zeros.** `toFixed` both
rounds and pads, which is exactly the fixed shape wanted, and it already
underpins `formatDisplay`'s noise removal, so the float-noise case
(`3 * 0.0125 = 0.037500000000000006`) is handled by the same mechanism
that handles it today. Four places is finer than any millimetre-scale
machine in the shop resolves and coarser than binary noise.

**D3 — Number and unit in separate elements.** The `<output>` gains two
spans: a right-aligned fixed-width number, then the unit. Only the
number is aligned; the unit hangs off its right edge at a fixed offset
and therefore also stays put. Writing one string cannot achieve this —
the alignment box must be the number's, not the pair's.

**D4 — Tabular figures and a reserved sign column.** The number span
carries `font-variant-numeric:tabular-nums` (so proportional digits
stop mattering) and a `min-width` in `ch` that fits sign, integer
digits, point and four decimals. `ch` is the width of `0`, which under
tabular figures is the width of every digit, so the reservation is
exact rather than guessed. Right alignment then means a value that grows
a digit or a minus sign grows leftward into reserved space instead of
pushing its neighbours. Alternative considered: padding the string with
a figure space or a hidden `-` — rejected as it lies to a screen reader
and to anyone copying the value.

**D5 — Style stays inline.** The chrome sets every style through
`style.cssText` because the widget ships without a stylesheet and must
not depend on the host page having one. This follows that existing rule
rather than introducing the first CSS class the widget expects to be
styled.

## Risks / Trade-offs

- **A driver finer than 0.0001 design units reads as rounded** →
  Accepted, and the pilot's explicit "for now". No supported machine
  scale in the shop resolves below this; if one appears, the decimal
  count becomes per-driver policy in `controls.ts`, where D1 already
  isolates it.
- **A very large value overflows the reserved column** → It grows the
  column rather than truncating: `min-width`, not `width`, so the
  readout stays truthful and only that one row is wider. A machine
  travelling past ±99999 mm is not the case being designed for.
- **Two formatters can drift** → Both live in `controls.ts` next to each
  other with their jobs named in comment, and both are unit-tested.
- **The DOM change is not covered by node tests** → The formatter is;
  the two-span layout is proved the way the rest of the chrome is, by
  the live browser drive on Metamaquina2 (design D1 of stage 3c: this
  bench has no DOM test framework).
