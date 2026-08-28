## 1. The readout formatter (red first)

- [x] 1.1 Add failing cases to `controls.test.ts` for `formatReadout`:
      four decimals kept on a whole number, a shorter value padded, a
      longer value rounded, a negative value signed, and float noise
      from a scale conversion written cleanly
- [x] 1.2 Run the widget suite and see those cases fail on the missing
      export
- [x] 1.3 Implement `formatReadout` in `controls.ts` beside
      `formatDisplay`, with each formatter's job named in comment
      (design D1, D2)
- [x] 1.4 Run the widget suite green, including the existing
      `formatDisplay` cases unchanged

## 2. The steady readout row

- [x] 2.1 In `viewer.ts`, split the driver row's `<output>` into a
      number span and a unit span (design D3)
- [x] 2.2 Style the number span right-aligned, tabular-figured, and
      `min-width` in `ch` sized for sign, integer digits, point and
      four decimals (design D4, D5)
- [x] 2.3 Feed the number span from `formatReadout` and keep the pinned
      colour and title on the readout as a whole
- [x] 2.4 Confirm the range-less driver's number input still uses
      `formatDisplay` and is untouched

## 3. Evidence

- [x] 3.1 Run the full widget test suite
- [x] 3.2 Run the framework's viewer/widget Python tests that exercise
      the built widget
- [x] 3.3 Drive Metamaquina2's axis sliders in the browser from this
      worktree's bench and confirm the readout holds still through a
      drag, across zero, and at a pinned out-of-range value
