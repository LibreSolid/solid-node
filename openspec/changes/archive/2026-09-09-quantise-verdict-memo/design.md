## Context

ADR-029 removed redundant geometry construction; ADR-070 removed
redundant *asking* by memoizing an intersection verdict per run under
the key `(identity1, identity2, path, bytes(inv(M1) @ M2))`. ADR-073
made the comparison kernel and the volume epsilon properties of the
run, resolved once from flags, then the environment, then defaults.

The finding this cycle answers is recorded in `workflow/warts.md`, last
section, "3DPrintedClocks wall clock 02 (2026-09-09, exact sweep cost)".
Under the exact kernel a sweep instant of that clock costs ~19 s,
essentially all of it inside `BRepAlgoAPI_Common`. Of 118 candidate
pairs from the world-AABB broad phase, ~110 booleans run per instant
and every one comes back empty. 30 of those pairs are rigidly carried
together — the pendulum with its suspension, the motion works, the
weight with its line — and their relative matrices differ between
instants by ~1e-13. Only 5 pairs hit the memo.

That ~1e-13 is not a placement. It is the residue of composing the same
rigid motion by two different routes in IEEE 754: the parent rotation
multiplies into each child's chain in a different order, and the last
bits disagree. The memo asks "are these the same bytes?" when the
question it means is "are these the same placement?".

The pilot has ratified the answer: **quantise the relative matrix in
the verdict key to a grid, and make the grid a stated property of the
run.** This design records how, and what a reviewer must be able to
check.

### The conflict with ADR-070, stated

ADR-070 explicitly considered and rejected "key on the relative matrix
rounded to a tolerance":

> A tolerance on the key is a tolerance on the assertions. Rounding
> decides that two placements differing by less than ε are the same
> question — which is precisely the judgement `volume_epsilon` exists
> to let a *project* make, per contract, in millimetres of material.
> Making it globally and invisibly in a cache key would decide it for
> every project at once.

Two words in that paragraph carry the rejection: **globally** and
**invisibly**. This design removes both, and separates the two
judgements ADR-070 conflated:

- `volume_epsilon` is a judgement about **material**: how much shared
  solid a project is willing to call clearance. A project must state
  it, per contract, and the framework must never pick a value.
- The placement quantum is a judgement about **float noise**: below
  what difference two computed matrices are the same rigid placement.
  That is a property of double-precision arithmetic and of the scale of
  a machine, not of a project's manufacturing intent, which is why it
  can have a default at all.

And unlike a rounding buried in a cache, the quantum here is a field of
the run's `ComparisonPolicy`, a documented flag, a documented
environment variable, announced on the summary line when it is not the
default, and **removable**: `--placement-quantum 0` restores exactly
the key ADR-070 specified, byte for byte. ADR-070's own consequence
paragraph — "the temptation to widen a key until it hits its forecast
is exactly how a correct cache becomes a wrong one" — stands, and is
the reason the quantum is visible and removable rather than tuned.

## Goals / Non-Goals

**Goals:**

- A pair carried rigidly through a sweep is asked once, not once per
  instant.
- The memo still cannot change a verdict, and this is argued from the
  arithmetic, not asserted.
- The quantum is visible in the run's policy, selectable per run,
  removable, and documented beside the kernel and the epsilon.
- The default run's output is byte-for-byte what it is today.

**Non-Goals:**

- Any change to what geometry a comparison sees. `placed_shape`,
  `_placement_cache`, `_bounds_cache` and `_world_bounds` keep their
  exact keys and their exact inputs.
- Any change to the broad phase, to `volume_epsilon`, or to any
  assertion's contract.
- The other three wall-clock-02 findings (root-frame broad phase, face
  box tier, mesh-distance tier, parallel booleans). Independent cycles.
- Sharing the memo across processes or runs. It stays per-run and
  bounded, exactly as ADR-070 left it.

## Decisions

### 1. The key's placement term is a tuple of integer cell indices

`_verdict_key` today:

```python
relative = np.linalg.inv(matrix1) @ matrix2
return (identity1, identity2, path, relative.tobytes())
```

becomes, for a quantum `q > 0`:

```python
relative = np.linalg.inv(matrix1) @ matrix2
if not np.all(np.isfinite(relative)):
    return None
cells = np.rint(relative / q).astype(np.int64)
return (identity1, identity2, path, q, cells.tobytes())
```

and for `q == 0` keeps `relative.tobytes()` in the placement slot.

Three properties of that line matter, and each is a scenario a reviewer
can check.

**Integers, not rounded floats.** The key must not be built from
`np.round(relative / q) * q` and then `.tobytes()`. Rounding back into
floats reintroduces representation: `-0.0` and `0.0` are distinct byte
patterns for the same number, and a translation component that lands on
zero from below and from above would key differently — precisely the
miss this cycle exists to remove, reappearing at every cell boundary
that happens to be the origin. `np.rint(x)` maps both `-0.0` and `+0.0`
to `-0.0`/`0.0` as floats, but `.astype(np.int64)` maps both to the
integer `0`, which has one representation. Integer cells also make the
key exact: two matrices are one question iff their twelve (sixteen)
integers are equal, with no float comparison anywhere.

**The range is ample, and float64's mantissa is what bounds it.**
A cell index is `entry / q`, and that division happens in float64
*before* the cast. `int64` would allow ±9.22e18 cells; float64
represents consecutive integers exactly only up to 2^53 ≈ 9.0e15, and
beyond that `np.rint` is rounding a value that is already spaced more
than 1 apart. So the binding limit is the mantissa, not the integer
type: at the default `q = 1e-9` mm a translation entry is exactly
representable as a cell index up to about ±9.0e15 cells, i.e.
**±9.0e6 mm — a 9 km machine**. Rotation entries are dimensionless and
bounded by 1 for a rigid matrix, so ±1e9 cells, nowhere near it.

Nine kilometres is ample for anything this framework models, and the
degradation past it is graceful rather than wrong: cells simply stop
being finer than the float spacing, so the key coarsens where the
coordinate itself has already coarsened. The genuinely dangerous case
would be a quantum so small that a real coordinate exceeds the
mantissa's exact range and two distinct placements collapse onto one
representable cell index — at which point the key is wrong, not merely
slow. It is unreachable at any quantum meant for noise, and the docs
say that is what the quantum is for. A non-finite matrix is refused
above.

**Whole matrix, one quantum.** All sixteen entries are quantised with
the same `q`, including the bottom row, which for a rigid relative
matrix is `(0, 0, 0, 1)` and quantises to constant cells — carrying it
costs nothing and avoids asserting a shape the array might not have.
The rotation entries are dimensionless while the translation entries
are millimetres, so one quantum means two different physical
tolerances; §2 shows both are negligible at the default and gives the
bound.

**A non-finite relative matrix yields no key.** `np.linalg.inv` on a
singular or degenerate matrix can produce `inf`/`nan`, and
`astype(np.int64)` on those is undefined. Returning `None` puts such a
comparison on the existing "not cacheable" path — it is computed
exactly as today. This is a new refusal that did not exist under the
byte key (where `nan` bytes were merely a key that never repeated); it
is strictly safer and never changes a verdict.

**The quantum is part of the key.** `q` sits in the key tuple beside
`path`. Without it, a process that changes policy mid-run — which the
framework's own tests do, via `set_comparison_policy` — could have two
different quanta produce the same integer cells for two genuinely
different relative placements and serve one verdict for the other. With
`q` in the key those entries can never meet. The cost is one float in a
tuple; the run resolves its policy once, so in practice every entry
carries the same `q`.

*Alternative rejected:* clearing `_verdict_cache` inside
`set_comparison_policy`. That makes correctness depend on a side effect
of a setter which today has none, and ADR-073 was careful to keep the
memo holding raw verdicts so a policy change could never serve a
filtered verdict as a raw one. Putting `q` in the key keeps that
property in the key, where it is visible.

### 2. Why a quantised hit cannot serve a wrong verdict

Let `R = inv(M1) @ M2` and `R'` be two relative matrices that land in
the same cell. Per entry, `|R'ᵢⱼ − Rᵢⱼ| < q` (each is within `q/2` of
the cell centre).

Split the matrix. Write a point of the second solid, in the first
solid's frame, as `p = A x + t` where `A` is the 3×3 block and `t` the
translation. For the two placements:

```
|p' − p| = |(A' − A) x + (t' − t)|
         ≤ ‖A' − A‖ · |x| + |t' − t|
         ≤ 3q · L        +  √3 q
```

using the entrywise bound and `|x| ≤ L`, the extent of the part from
its own origin. Both terms are linear in `q`.

At the default `q = 1e-9` mm and a generous `L = 1000 mm` (a metre-scale
part), the bound is `3e-6 + 1.7e-9` mm — about **3 nanometres**. Every
point of one solid, in the other's frame, is within 3 nm of where it
would have been. No manufacturing question this framework asks can
distinguish that: the exact kernel's own tolerances, OCCT's
`Precision::Confusion` at 1e-7 mm, and any clearance a machine is
designed to hold are all orders of magnitude larger. The flush-contact
contract of ADR-025/029 — a non-empty result at exactly 0.0 mm³ — is a
statement about *touching*, and two placements 3 nm apart both touch or
both do not, unless the design's clearance itself is 3 nm, which is not
a design.

That argument is what distinguishes this quantum from `volume_epsilon`:
it is not a decision about how much interference a project tolerates.
It is a decision about when two computed numbers are the same number.
The material judgement stays exactly where ADR-070 put it.

**The failure direction is a miss, not a wrong hit.** Nothing forces
two placements within `q` into the same cell — two values straddling a
cell boundary differ by a hair and key differently, and the comparison
is recomputed, which is exactly today's behaviour. So the change can
only *add* hits, never remove correctness margin at the boundary. To
get a wrong verdict from the memo, two placements would have to differ
by a real, intended amount *smaller than `q`* and share a cell. At
`q = 1e-9` mm no such intended difference exists. A user who raises the
quantum to a value where one might exist has stated that value on the
command line or in `.env`, and the summary line says so.

**Why a default is admissible at all.** The rule this shop works under
is that a framework never silently makes a project's manufacturing
judgement. The quantum does not make one: at 1e-9 mm it merges only
placements that IEEE 754 arithmetic could not have distinguished
meaningfully in the first place. That is the same class of judgement as
"two identical bytes are the same placement" — which ADR-070 also made,
by default, for every project.

### 3. The option: one name, three spellings, both kernels

| where | spelling |
|---|---|
| policy field | `placement_quantum` |
| flag | `--placement-quantum MM` |
| environment | `SOLID_TEST_PLACEMENT_QUANTUM` |

`ComparisonPolicy` becomes
`namedtuple('ComparisonPolicy', 'kernel volume_epsilon placement_quantum')`,
and `DEFAULT_PLACEMENT_QUANTUM = 1e-9` is a module constant so the
runner, the docs test and the error messages name one value.

Resolution mirrors ADR-073 exactly: explicit value (the flag) beats
`SOLID_TEST_PLACEMENT_QUANTUM` beats `DEFAULT_PLACEMENT_QUANTUM`.
Outside `solid test` — a `ScenarioTest` under pytest, an assertion
driven directly — the same policy is resolved from the environment at
the first comparison of the process, with the same defaults and the
same errors. The environment is read through the CLI's `.env` rule, so
a checkout can pin a quantum the way it pins a kernel.

**`0` means the exact-bytes key.** Not "no memo": the memo still runs,
keyed exactly as ADR-070 specified. This is the escape hatch that keeps
ADR-070's key reachable and testable, and it is how the reviewer checks
that nothing else in the change depends on quantisation.

**Errors.** A negative value is refused naming the flag or the
variable, in the shape `resolve_comparison_policy` already uses for
`volume_epsilon`. `inf` and `nan` parse as valid floats but are refused the
same way: dividing by an infinite quantum collapses every relative matrix
to the same all-zero cell, serving one verdict for every pair in the run,
and `nan` reaches `astype(np.int64)` undefined, so both are checked with
`math.isfinite` alongside the negative check, from either source. A
non-numeric environment value is refused naming
`SOLID_TEST_PLACEMENT_QUANTUM` and saying it is a length in mm. A
non-numeric flag value is argparse's own error (`type=float`).

**It applies under both kernels, and the exact kernel accepts it.**
This is the one place the option deliberately does not mirror
`volume_epsilon`. The epsilon is refused by the exact kernel because
the exact kernel has nothing for it to absorb — it is about mesh
slivers. The quantum is about the composed float matrices, which both
kernels compute identically and both feed into the same `_verdict_key`.
Refusing it under the exact kernel would leave the originating
finding — an exact-kernel sweep — unfixed. So `resolve_comparison_policy`
validates and stores the quantum before the kernel branch, and both
policies carry it.

*Alternative rejected:* a separate quantum per kernel. There is one
memo, one key function, and one source of noise; two knobs would be two
ways to say the same thing.

**No upper bound is imposed.** A cap would be a second, invisible
judgement, and any cap defensible at one machine scale is wrong at
another. The docs state the contract instead: the quantum is for float
noise and must stay far below the smallest clearance the suite judges.
The summary line makes a non-default choice visible in every log.

### 4. Announcement: only when it is not the default

ADR-073's rule is that a green fast run must never read as an exact one
in a log, and it pays for that with a line before the first build and a
summary suffix. The quantum is weaker news — at the default it changes
no verdict and no output — so:

- **Default quantum: no line, no suffix, no change of any kind to the
  run's output.** A reviewer can diff the output of `solid test` before
  and after this change on any project and see nothing.
- **Non-default quantum: the summary line says so**, in the same
  parenthesis ADR-073 established, and beside the faceted label when
  both apply:

```
Ran 16 tests in 300.10 seconds: 16 passed, 0 failed (placement quantum 1e-06 mm)
Ran 16 tests in 90.10 seconds: 16 passed, 0 failed (faceted kernel, volume epsilon 0.5 mm³, placement quantum 1e-06 mm)
```

The summary prefix stays verbatim for parsers, as ADR-073 required.

*Alternative rejected:* a pre-build line like the faceted kernel's. The
faceted line exists because the whole run's verdicts are at a weaker
precision and a developer should be told before waiting. A non-default
quantum does not weaken a verdict at any value a sane user picks, and
the summary carries it into the log where a reviewer of a commit looks.
*Alternative rejected:* announcing the quantum always. That would
change the default run's output, which goal four forbids.

### 5. Blast radius: one function

Both verdict-producing paths reach the memo through `_verdict_key`:

- `_engine_intersection_stats` (line ~1285) calls
  `_verdict_key(shape_identity(shape1), matrix1, ...)` directly for the
  exact path and for the faceted fast path — direct pair assertions;
- `_placed_intersection` (line ~645) calls `_record_key`, which calls
  `_verdict_key` — assembly assertions.

So the whole change to the memo is inside `_verdict_key`, and both
callers inherit it without edit. `_record_key` keeps its own
responsibility (a record with no identity is not cached) unchanged.
`_memoized` is untouched, and so is the 8192-entry bound and its
insertion-order eviction.

**What must NOT change, and is a reviewable line:** `placed_shape`,
`_placement_cache` and `_bounds_cache` in `solid_node/exact.py` key on
the **exact** matrix bytes and continue to. The spec says so in as many
words ("no tolerance or rounding SHALL enter the key"), and it is right:
that cache decides which *geometry object* a boolean is handed. Two
placements a cell apart must still be placed by their own matrices; only
the *question's identity* is quantised, never the geometry that answers
it. `_world_bounds` and `_boxes_disjoint` are likewise untouched — the
broad phase reads real matrices.

### 6. `ComparisonPolicy` grows a third field, with a default

`ComparisonPolicy` is a `namedtuple`, and it is constructed
POSITIONALLY with two arguments in seven places today:

| site | construction |
|---|---|
| `solid_node/test.py:140` | `ComparisonPolicy('exact', 0.0)` |
| `solid_node/test.py:153` | `ComparisonPolicy('faceted', volume_epsilon)` |
| `solid_node/manager/test.py:281` | `getattr(self, 'policy', ComparisonPolicy('exact', 0.0))` |
| `tests/test_exact_geometry.py:560` | `ComparisonPolicy('faceted', epsilon)` |
| `tests/test_exact_geometry.py:731` | `ComparisonPolicy('exact', 0.0)` |
| `tests/test_tessellation_precision.py:489` | `ComparisonPolicy('faceted', 0.0)` |
| `tests/test_manager_test.py:698` | `ComparisonPolicy('faceted', 0.5)` |

A mandatory third field makes every one of those a `TypeError`. The
field is therefore declared with a default:

```python
ComparisonPolicy = namedtuple(
    'ComparisonPolicy', 'kernel volume_epsilon placement_quantum',
    defaults=(DEFAULT_PLACEMENT_QUANTUM,))
```

That is not a compatibility shim, it is the definition of the default:
a policy constructed without a quantum IS a policy at the default
quantum, which is exactly what those seven sites mean. The two
resolution returns in `resolve_comparison_policy` still pass the
resolved quantum explicitly; the rest keep working unchanged and keep
saying what they meant.

Equality is the one place the default cannot help. A 2-tuple never
equals a 3-tuple, so the assertions in `ComparisonKernelSelectionTest`
of the form `self.assertEqual(policy, ('exact', 0.0))` fail and are
widened to 3-tuples carrying the default quantum. That is the intended
visible break: a policy is what the run compares on, and a new
dimension of it belongs in the tuple a test pins.

No external API takes a `ComparisonPolicy` positionally beyond those
sites; it is otherwise constructed in `resolve_comparison_policy` and
read by field.

## Risks / Trade-offs

- **A user sets a quantum large enough to merge a real difference.** →
  The value is stated on the command line or in `.env`, the summary
  line repeats it in every log, and the docs say what it is for. The
  bound of §2 is written down so a user can compute what a value
  merges. No cap, deliberately (§3).
- **int64 overflow at an absurdly small quantum.** → Unreachable at any
  quantum a machine-scale model would use (§1); a non-finite matrix is
  refused; the docs say the quantum is for noise.
- **The memo hits more, so a latent bug in the memo would bite
  harder.** → The existing invalidation discipline is untouched
  (identity change evicts; exact and faceted never cross-serve;
  identity-less nodes are never cached), and the flush-contact scenario
  is kept intact and re-run under the default quantum.
- **The measured win could be smaller than the finding predicts.** →
  Task 5 measures it in the originating project, before and after, and
  records the numbers in `evidence.md` whatever they are. ADR-070's own
  consequence — a forecast generous by more than a factor of two, and
  the key not loosened in response — is the precedent: if the win is
  small, the number is reported and the quantum is not raised to chase
  it.
- **Two runs at different quanta share one process (pytest).** → The
  quantum is in the key, so entries cannot cross-serve (§1).

## Migration Plan

None needed. The change is additive and the default preserves current
output; the escape hatch `--placement-quantum 0` reproduces the
pre-change key exactly, which is also the rollback if one is ever
wanted.

## Open Questions

None outstanding. The judgement calls made here without asking the
pilot, recorded so they can be overturned cheaply:

1. Name `--placement-quantum` / `SOLID_TEST_PLACEMENT_QUANTUM` /
   `placement_quantum` (§3).
2. `q` is carried in the key tuple, rather than clearing the cache when
   the policy changes (§1).
3. All sixteen entries quantised with one quantum, rather than a
   separate angular quantum for the rotation block (§1, §2).
4. A non-finite relative matrix yields no key instead of raising (§1).
5. No upper bound on the quantum (§3).
6. The summary announces a non-default quantum; the default run's
   output is unchanged, and there is no pre-build line (§4).
7. `ComparisonPolicy`'s third field is declared with a default, so the
   seven positional two-argument constructions keep working and mean
   "at the default quantum"; the 2-tuple EQUALITY assertions are
   widened, since no default can make a 2-tuple equal a 3-tuple
   (§6).
8. The new ADR is `ADR-090`, the next number after `ADR-089`, filed
   under `TEST-FRAMEWORK/` and marked as amending ADR-070 (the pattern
   ADR-074 and ADR-075 already use for "amends").

## The ADR this cycle produces (outline for the implementer)

`docs/adrs/TEST-FRAMEWORK/ADR-090-the-placement-quantum-is-a-property-of-the-test-run.md`,
**Accepted**, *Amends* ADR-070, *Related to* ADR-073, ADR-029, ADR-025.
Written after implementation, with the measured numbers in it.

- **Context**: the wall-clock-02 measurement, cited to
  `workflow/warts.md`; the 30-of-118 co-moving pairs and the ~1e-13
  noise; that the byte key asks a different question than it means to.
- **Decision drivers**: the memo must never change a verdict (ADR-070's
  first driver, carried over verbatim in force); the default run's
  output must not change (ADR-073's driver); a tolerance must not be
  global or invisible (ADR-070's stated reason for rejecting it).
- **Considered options**: (1) quantised key as a run-level option
  [chosen]; (2) canonicalise the relative matrix instead — re-orthonormalise
  the rotation block and round to a fixed number of significant digits
  [rejected: still a tolerance, and one with no name and no dial];
  (3) key on the two nodes' *declared* placements rather than the
  composed matrices [rejected: a flexible or derived placement has no
  declared form, and ADR-070's finding 5 shows name-shaped keys
  overcount]; (4) leave it and take the cost [rejected: the finding is
  a quarter of a sweep instant].
- **Decision outcome**: the quantised key, the integer cells, the
  policy field, the flag, the variable, `0` as the exact-bytes escape
  hatch, both kernels, the summary suffix.
- **The amendment to ADR-070, stated plainly**: ADR-070 rejected
  "option 3: key on the relative matrix rounded to a tolerance" because
  a tolerance on the key would be a tolerance on the assertions, chosen
  globally and invisibly. This record amends that: the rejection was
  right about a hidden tolerance and wrong to conclude that no
  tolerance is admissible. `volume_epsilon` is a judgement about
  material and stays the project's; the placement quantum is a
  judgement about float noise and belongs to the run, stated where the
  kernel and the epsilon are stated, and removable. Reproduce §2's
  bound, and §1's range note — float64's 2^53 mantissa, not `int64`,
  is what bounds the usable coordinate range at a given quantum
  (±9.0e6 mm at the default).
- **Consequences**: the measured before/after from `evidence.md`; that
  the default output is unchanged; that `placed_shape`'s cache still
  keys on exact bytes; that flexible parts remain uncacheable
  (unchanged from ADR-070); that the remaining wall-clock-02 cost is
  the two broad-phase findings, which are their own cycles.
- **References**: `solid_node/test.py` (`ComparisonPolicy`,
  `resolve_comparison_policy`, `_verdict_key`),
  `solid_node/manager/test.py`, `tests/test_intersection_memo.py`,
  `tests/test_manager_test.py`, `workflow/warts.md`, this change.
