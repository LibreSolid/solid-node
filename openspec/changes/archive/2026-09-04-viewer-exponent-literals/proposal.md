## Why

The producer writes every operation value, driver scale and instruction
target into the published document as an expression *string*, formatted
by Python's `str()`. Python switches to exponent notation for any float
below `1e-4` or at or above `1e16` — and the viewer's expression reader
cannot read one. `jokenizer`, the tokenizer the widget's evaluator uses,
stops at the `e`:

    1.592040838891559e-15          Unexpected character (e) at index 17
    ((-x_motor) * 6.103515625e-05) Unexpected character (e) at index 25

Both lines are real content from a real model: the OpenFlexure Microscope
simulation (`projects/openflexure-microscope`, LibreSolid Studio). Its
three stepper axes advance 0.5 mm of lead screw over 8192 motor steps, so
the driver scale the producer emits is `6.103515625e-05`, and every
placement expression carries it. The tiny values are the other half of
the same story: a placement computed through a rotation lands on
`1.59e-15` instead of zero, which prints in exponent form for exactly the
same reason.

The consequence is total, not cosmetic: the viewer refuses the document
and the maker sees a parse error where the machine should be. Any model
whose numbers are small enough — a micrometre stage, a gear ratio in the
thousands, ordinary floating-point noise — hits it.

This is a producer/client agreement failure. The producer's own language
(OpenSCAD) accepts exponent literals, the producer emits them, and the
capability "Client evaluation matches producer numerics" already promises
that the two sides read the same expressions the same way. The parity
corpus that enforces that promise happens to contain no number small
enough to print with an exponent, so the gap went unseen.

## What Changes

- **The viewer reads every numeric literal the producer can emit.** The
  evaluator normalizes exponent-notation literals to plain decimal before
  tokenizing, by shifting the decimal point through the digit string —
  exactly, with no float round-trip, at any magnitude.
- **Only literals are touched.** The rewrite matches a number followed by
  `e`/`E` and a signed exponent, and never an identifier: a driver named
  `e5`, a member `motor.e10`, or the function `exp` is left alone.
- **The parity corpus gains the numbers that broke it.** The
  producer-generated fixture covers a scaled driver term whose scale is
  exponent-printed, a bare tiny literal, and a large one, so the corpus
  fails without the fix.

## Impact

- `solid_node/viewers/widget/src/evaluator.ts` — the normalization, on
  the cached-tokenize path, so it costs one pass per distinct expression
  rather than one per frame.
- `solid_node/viewers/widget/tools/generate_parity_fixture.py` and
  `src/parity-fixture.json` — the new corpus entries.
- `openspec/specs/viewer-package/spec.md` — the numerics requirement says
  which literals the client must read.
- No change to the producer, the document format, or the viewer API
  version: a document that worked before is byte-identical and still
  works.
