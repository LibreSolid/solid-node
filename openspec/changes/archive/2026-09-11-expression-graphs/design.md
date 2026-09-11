## Context

The primary framework base is `e51d196c74f10e240ef0f3580c52f9abee66d63b`.
The originating machine, measurements and accepted sequencing are recorded in
`workflow/docs/expression-graphs.md`. Curta fails during `symbolic_document()`
before `bind_document()`: `piecewise()` repeatedly embeds a roughly 7.7 MB
operand. The current serializer then stringifies operations and flexible
parameters before parsing those strings into the ADR-080 interner.

Existing boundaries matter: `DriverToken` subclasses `OpenSCADConstant`, time
comes from solid2, `math.py` dispatches on that type, flexible-node time
detection searches its string, and SCAD generation also consumes those values.
The parameter algebra is a separate third math face and already resolves to
numbers before geometry is built. The viewer understands schema 4 and is
owned by a separate repository. Nothing here changes its grammar.

## Goals / Non-Goals

**Goals:** preserve sharing while constructing and consuming motion; export
Curta within the agreed budget; keep project formulas and evaluated poses;
retain SolidPython/OpenSCAD geometry and numeric/SCAD compatibility; make the
expression graph and compiler framework-owned.

**Non-Goals:** replace `as_scad()` as the node lifecycle, remove solidpython2
from package dependencies, change fusion engines, decide the viewer's future,
change the declarative parameter algebra, simplify arithmetic, add lookup
primitives, fix unrelated numeric discrepancies, or rewrite Curta motion.

## Decisions

### D1. A native immutable operation graph, with bounded ownership

Use framework-internal scalar nodes for literals, input names, unary and binary
operations, and calls. A compound node holds references to its operands;
construction never renders them. Preserve operand order, literal distinctions
and expression structure. Do not commute operands, reassociate floating-point
sums or apply symbolic simplifications. Symbolic comparison returns a symbolic
value; testing its truth in Python remains refused.

Keep native nodes independent of SolidPython. Live expression values own the
nodes reachable through their operands. Construction need not globally intern
all independently authored equal expressions: reference reuse prevents the
explosion already, while structural interning during document compilation
deduplicates separately constructed equivalents. Compiler tables belong to
one compilation and are released afterward. No process-global strong cache of
all expressions and no graph-to-project backreferences.

Compiler traversal and structural identity use iterative postorder and scalar
child identities, not recursively hashed nested tuples. Count occurrences from
the final roots and operand edges, including repeated operand edges; do not
count abandoned temporary expressions as document uses. Propagate repeated
occurrence information through shared descendants without visiting the
expanded tree. A count saturated at two suffices for deciding sharing.

Alternative: a global hash-consing arena complicates lifetime and concurrent
builds without being necessary to prevent operand duplication. Alternative:
retain an eager string alongside the graph still fails on Curta.

### D2. Preserve the author-facing algebra through a compatibility adapter

Introduce a graph-backed SolidPython-compatible facade in a dedicated adapter
module. It can remain an `OpenSCADConstant` subtype while the graph itself
depends on no SolidPython type. Override the full supported operator surface,
including reflected operators, comparisons and `abs`; do not call the eager
base constructor or inherited text-building implementations. Its `.value`
and SCAD rendering are computed on demand, not stored as expanded text.

Framework time and driver values, and the symbolic math face, produce these
graph-backed values. Bare `$t` and qualified driver ids retain their spelling.
Numeric and declared math faces keep their current behavior. The facade is a
transitional compatibility boundary for the existing assembly lifecycle, not
a claim that this cycle removes every SolidPython import from core modules.

When a legacy constant meets a graph-backed value, import the legacy text into
the native graph and preserve left/right order. Verify Python's reflected
operator dispatch against the installed solidpython2 2.1 implementation.
Calls through legacy solid2 functions can still return text; re-import those
results at math/operation/port publication boundaries. Cache a parsed legacy
operand only for the lifetime of its compilation or facade.

Raw text outside the supported expression grammar retains the existing
verbatim publication and truncated-warning contract. It is not silently
converted to an approximate value. The growth guarantee covers framework
graph construction and supported combinations; a project explicitly creating
an expanded string in its own code has already incurred that allocation.
Repeatedly sending values through arbitrary third-party text producers cannot
be promised native-graph complexity.

### D3. Compile graph roots directly to the existing document contract

Provide an internal collection path for operation scalars and flexible port
values. Build/export collect graph roots before rendering any text. Compile
all roots of a document together, then fill the existing string slots and
top-level bindings. Keep the public document shape and version ladder.

Reuse ADR-080's name allocation, deterministic ordering, collision checks,
legacy parser and table validation where appropriate, separating their
algorithms from the requirement to start with strings. Unshared expressions
retain the legacy spelling; repeated compounds become `_bN` references under
the established collision-safe prefix. Never serialize internal node ids,
adapter objects, local SCAD bindings or a new expression opcode format.

The compiler can accept legacy string slots beside native roots, so custom
operations and already serialized inputs retain a path. Verify reconstruction
structurally against the original graph without flattening either side. The
ordinary build, export, browser snapshot and fixture-generation paths must
all use this compiler. Publication must not mutate live operation values or
driver bindings.

### D4. Self-contained SCAD closures only at the SCAD boundary

Emit a shared scalar as one `let(...)` expression with local definitions in
dependency order and a final expression referring to them. Choose local names
that do not capture any free input or name in the expression. Emit no `let`
for an unshared scalar. Each scalar closure is self-contained so nesting a
node under another SCAD scope does not introduce global temporaries or make
its meaning depend on which document was previously exported.

The OpenSCAD manual describes sequential assignment within an expression:
[OpenSCAD language manual](https://files.openscad.org/documentation/manual/The_OpenSCAD_Language.html#let).
Actual generated closures must also be evaluated by the installed OpenSCAD
binary in compatibility tests; documentation alone does not establish parity.

String rendering of a graph-backed value, including the standalone scalar
strings in `.serialized`, uses this bounded, self-contained representation.
`unserialize()` imports such scalars back into the graph. Add a narrowly scoped
SCAD-closure reader at the adapter boundary so a solid2 function that wraps a
graph value's text can return to native expression processing. Resolve local
definitions lexically into shared nodes, including shadowing and nested
closures; this is not a general OpenSCAD interpreter. Unrecognized user syntax
retains the old fallback. Generated closures must always be recognized; a
failure to read the framework's own closure is a framework defect.

Standalone operation serialization preserves its list shape and semantic
round-trip but is not itself a finished node-tree document. Document producers
compile graph roots or import those standalone scalars into schema-4 bindings;
they never forward SCAD-local closures to the browser. Document-free custom
consumers inspecting the old expanded spelling need the migration note.

SCAD output work is proportional to its written size: separate scalar closures
can repeat a shared graph across distinct output sites, but never expand a
graph internally into its exponentially larger expression tree. Native document
publication additionally shares across all output roots. Diagnostics use a
bounded structural summary; they must not render the full closure merely to
truncate it afterward.

This supersedes ADR-080's promise of unchanged expanded SCAD text, not its
rejection of OpenSCAD grammar in viewer documents. Alternative: retaining flat
`str()` makes legacy code a hidden expansion path. Alternative: document-wide
SCAD globals risk capture and depend on assembly lifecycle changes outside
this cycle. Alternative: dropping SolidPython compatibility contradicts the
pilot's explicit modelling-technology requirement.

### D5. Dependency inspection and numeric behavior remain faithful

Determine free inputs from the graph, memoizing visits within a traversal.
Time-fed flexible parts retain their current no-snapshot SCAD behavior;
driver-only unresolved parts still fail. Detection must follow time through
shared intermediates and through recognized legacy expressions.

Numeric poses normally rerun the same project formulas with numbers, as today;
do not replace that path with a new solver. Where an operation reconstructed
from an expression must evaluate, use the existing symbolic conventions and
an explicit input environment, and refuse unresolved values rather than
substituting zero/default time. Keep legacy Solid2 numeric evaluation working.
Audit type-name checks in `Solid2Node.as_number()` for the new facade.

Do not claim to fix the known Python-versus-SCAD `%` sign discrepancy recorded
in ADR-022. Preserve current symbolic remainder semantics, test them separately,
and keep `wrap` as the existing cross-runtime composition. Existing supported
degree math and fixture values must remain unchanged.

### D6. Independent evidence, then the real machine

First add resource-bounded regression cases on the actual symbolic construction
and producer paths. A depth-N doubling chain, deep unshared sums, and a small
carry/profile/flexible-port composition exercise different failure modes.
Use structural counts and memory limits for growth assertions; elapsed time
is recorded evidence, not a fragile unit-test threshold. Prove the tests red
before changing implementation, without intentionally exhausting the host.

Retain legacy expected values and fixtures from the recorded base. Compare
new publication with manageable legacy formulas and numeric poses, preserving
the corpus tolerance; check the same emitted expressions in the unmodified
viewer. Exercise OpenSCAD through a batched echo fixture with representative
boundary values and appropriate recorded numeric-output tolerance. Cover both
operand orders, every emitted builtin, comparisons, time, defaults, qualified
drivers, flexible parameters, name collisions, and repeated publication.

Finally export the complete Curta with the worktree implementation explicitly
selected, into a separate evidence output directory in the project. Keep the
project's source and modelling choices intact. Use an aggregate process memory
limit of 8,000,000,000 bytes (the explicit interpretation of the accepted 8 GB
budget); record enforcement method, process-tree peak, elapsed time, document
size, graph/binding counts, dependency versions and exact framework/viewer/
project states. Capture dirty source diffs or content hashes where necessary.
Distinguish warm-cache and fresh-geometry runs. No unenforced host-wide OOM
experiment and no deletion of the project's existing caches.

The final durable report and handoff must state the actual measured peaks for
both runs in bytes and MiB/GiB, the measurement method and its limitations,
headroom below the cap, and comparison with the earlier 7,857,084 KiB failure.
Distinguish aggregate charged memory from process RSS and do not equate either
observed peak with a proven minimum hardware requirement. The 8 GB limit is a
safety ceiling, not a success metric or a claim that the fix needs 8 GB.

Inspect browser poses at representative driver states and carry transitions,
including spring coordinates around the measured piecewise knots. Record
screenshots plus numerical checks; successful loading alone is insufficient.
Framework evidence belongs in this cycle; generated project artifacts remain
in the independent project repository's ignored build/evidence locations.

## Risks / Trade-offs

- Legacy string semantics and reflected dispatch → cover actual solidpython2
  operands before replacing tokens; preserve type compatibility in the facade.
- SCAD closure import broadens producer-side parsing → restrict it to expression
  scope, test capture/shadowing, and prove no closure syntax reaches the viewer.
- Exact string consumers can break → explicitly document the changed compound
  spelling and test stable bare/unshared cases; no silent claim of byte parity.
- Python recursion and hidden repeated traversal → iterative algorithms and
  deep/reused cases across construction, hashing, diagnostics and all outputs.
- Graphs retained between builds → inspect object lifetime and memory after
  discarded trees; keep compiler caches local.
- Numerical drift → no algebraic optimization, retain independent old expected
  values, and test actual consumer runtimes.
- Curta geometry may have independent costs → measure warm and cold paths
  separately; report any remaining failure rather than weakening the budget or
  simplifying the machine. Such a failure prevents claiming full completion.

## Migration Plan

Ratify this proposal and validate it before the planning-only commit. Implement
red-first in this worktree without intermediate implementation commits. After
proof, record the accepted architecture in a new ADR, update the architecture
synthesis and index, sync specs, archive the change and make the completed
cycle commit. Integration into main is separate and is not authorized here.

There is no release or publication in this cycle. The current viewer needs no
upgrade if schema compatibility holds. If a viewer change proves necessary,
return that scope decision to the pilot instead of editing the other product.
Before integration, rollback is simply leaving main on its existing base;
after integration any revert requires the pilot's direction.

## Open Questions

No purpose or backend-support decision remains open within this proposal.
The pilot ratified the facade, compact standalone spelling and SCAD-closure
importer on 2026-09-11, with actual memory reporting added. They are not yet
implemented contracts. Implementation must verify
their compatibility against real legacy callers. A need to weaken those
guarantees requires revised planning and re-ratification.

The available aggregate memory limiter and browser capture mechanism must be
verified before the Curta experiment; inability to enforce or observe the budget
is missing evidence, not a passing result. The viewer-role decision and complete
SCAD lifecycle removal remain in the separate follow-up plan.
