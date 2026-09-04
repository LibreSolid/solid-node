## Context

The widget evaluates the published document's expression strings with
`jokenizer`, chosen because a qualified driver id (`x_axis.motor`) is
member access in its grammar and needed no extension. Its number rule is
digits, an optional separator, digits — and then, if a variable-start
character follows, it throws. Scientific notation is simply absent from
the grammar.

## Goals / Non-Goals

- Goal: the client reads every numeric literal the producer can write.
- Goal: no float round-trip in the rewrite. `6.103515625e-05` must come
  back as those digits, not as whatever the shortest repr of a
  reconstructed double happens to be.
- Non-Goal: changing what the producer emits. Formatting numbers
  differently on the Python side would fix this corpus and leave the
  agreement just as untested; the producer is entitled to its language's
  literals.
- Non-Goal: replacing or patching `jokenizer`.

## Decisions

**Normalize, do not extend the grammar.** The one place that turns a
string into tokens is `tokenizeCached()`. Rewriting there means the cost
is paid once per distinct expression — the same cache that already keeps
per-frame evaluation cheap — and every consumer of the evaluator gets the
fix without knowing about it.

**Shift the decimal point through the digit string.** Given mantissa
digits and an exponent, the result is those same digits with the point
moved and zeros padded. `1.592040838891559e-15` becomes
`0.000000000000001592040838891559`: every significant digit preserved, at
any magnitude, with no `Number()` in the path. `toFixed` was rejected — it
caps at 100 fractional digits and returns exponent form itself above
1e21, which would reintroduce the bug for large values.

**Match a literal, never an identifier.** The pattern requires a digit
before the `e` and a digit after the optional sign, and refuses a
preceding word character, `.`, or `$`. So `1e-5` is rewritten; `e5`,
`x.e5`, `$e5` and `exp(2)` are not. The exponent marker is followed by a
digit or sign, which no identifier continuation can be.

**Rewrite before tokenizing, not after evaluating.** A post-hoc fixup
would have to understand the expression; a pre-tokenize normalization
only has to understand numbers.

## Risks / Trade-offs

- A regex over expression text could in principle alter something inside
  a string literal. The producer emits arithmetic over numbers, driver
  ids and `$t` and never a string, and the corpus pins that; if string
  literals ever enter the document format, this rewrite must move into a
  real tokenizer.
- The rewrite lengthens an extreme literal (`1e-300` becomes 300-odd
  characters). It is parsed once, cached, and such values are noise
  rather than dimensions.

## Migration Plan

None. The change is client-side and additive: documents already
published parse exactly as before, and documents that could not be
parsed at all now can be. No API version bump.
