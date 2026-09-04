## Context

`AssemblyNode` wraps every subclass `render()` in `_idempotent_render`:
before the author's code runs, the assembly drops every operation it tagged
(`operation._animator is self`) on the nodes it ever animated, and every
`rotate()`/`translate()` applied while it is on the render stack is tagged.
That makes a re-render absolute, and it makes *every* operation applied in
`render()` a per-frame one. `InternalNode` wraps the same method for the
declarative substitution (`None` means the declared children minus the
omitted). Every tree walker — `assemble()`, the serializer, the driver walk,
`set_state`/`clear_state` propagation, the test manager — calls `render()`
directly and links what it returns.

Time reaches `render()` through `AssemblyNode.time`, which falls back to
solid2's symbolic `$t` when nothing bound it; a declared driver is read as an
attribute through `DriverDeclaration.__get__`; a port's value is a plain
attribute of its `BoundPort`. Placement in `__init__` runs outside any render
and is untagged, so it survives the sweep but sits innermost on the chain.

## Goals / Non-Goals

**Goals:**

- One lifecycle: `render()` builds the rest state once, `simulate()` moves
  it per binding. Authors stop deciding per operation whether it survives.
- Motion composes innermost; rest placement outermost of the node's own
  chain. This matches every case in the three migrated projects.
- Every current model keeps working, with a warning where it reads a
  driver, `time` or a port in `render()`.
- No change to any walker, the serializer, the published document, the
  widget, or the test runner's checkpoint mechanics.

**Non-Goals:**

- A joint or axis abstraction (the pilot's later refactor).
- Renaming `render()` (dropped by the pilot).
- `simulate()` on leaves or fusions.
- Removing the legacy path in this cycle.

## Decisions

### D1. The framework runs `simulate()` inside the render wrapper

The public entry point stays `render()`. `_idempotent_render` becomes the
lifecycle wrapper: sweep the assembly's tagged operations, produce the
children (see D3), then run `self.simulate()` with the assembly on the phase
stack in the *simulate* phase, and return the children. Every walker that
calls `render()` therefore gets a tree whose pose is current for the
binding, exactly as it does today, and none of them changes. The scad build,
which calls `render()` with `time` unbound, runs `simulate()` once under
symbolic `$t`; the simulator and the test runner run it per binding.

Alternative rejected: a separate `simulate()` call site in each walker. Six
call sites, one more thing for a walker author to forget, and no benefit.

### D2. Motion goes to the head of the one operations list

The node keeps a single `operations` list. An operation applied during a
*simulate* phase is inserted at the end of the leading motion region
(operations flagged `_motion`) rather than appended; one applied during a
*render* phase or outside any phase is appended as today. Composition walks
the list in order, so motion is innermost. The sweep removes the assembly's
tagged operations wherever they sit; the invariant that motion operations
lead the list holds because only the simulate phase inserts and everything
else appends. Cross-animator order stays what it is today: a later animator's
motion sits outside an earlier one's.

Alternative rejected: a second `motion` list composed before `operations`.
It would touch `_compose_matrix`, `assemble()`, the serializer, the widget's
composition, the test perturbation insert and both checkpoint mechanisms,
and the published document would need a schema change. The head insertion
keeps the serialized `operations` array the widget already composes in
order.

### D3. A render that read nothing runs once; one that read something is legacy

The wrapper puts the assembly on the phase stack in the *render* phase and
runs the author's `render()`. `DriverDeclaration.__get__`,
`AssemblyNode.time` and `BoundPort.value` report a read to the innermost
render phase. When the first run ends:

- **no read:** the operations it applied are untagged (they persist), the
  returned children are cached, and later wrapper calls skip the author's
  `render()` and go straight to the sweep and `simulate()`. `omit()` marks
  and the structure record are those of the first run.
- **a read:** the instance is marked legacy, its operations stay tagged and
  are swept and re-applied on every call as today, and one `FutureWarning`
  per class names the class, the read, and `simulate()`.

The decision is per instance, made on the first run. A class whose
`render()` reads a driver only under a condition is decided by what its
first run did; the warning text says so. A read through solid2's
`get_animation_time()` directly is not detectable and is documented as such.

Alternative rejected: deciding by whether the class defines `simulate()`.
A pure grouping node would be legacy for no reason, and a class that both
defines `simulate()` and reads a driver in `render()` would freeze its first
binding silently. Detection warns in exactly the case that needs it.

Alternative rejected: raising on a driver read in `render()`. Refused by the
pilot; current models must keep working.

### D4. `omit()` refuses the simulate phase

`omit()` raises `StructureError` when the innermost phase is *simulate*.
Structure is decided at rest; the existing recorded-set check stays for the
legacy path, where `render()` still re-runs.

### D5. The warning is a `FutureWarning`

Python shows `FutureWarning` to end users by default and hides
`DeprecationWarning` outside `__main__` and test runners; a maker running
`solid build` must see this one. Emitted once per class, through
`warnings.warn` with the class-level dedup done by the framework so the
message does not depend on the call site.

### D6. Ports and leaves

`connect()` and port assignment are unchanged as operations; their home is
`simulate()`, and a port read in `render()` is a detected read (D3). A leaf
never gets a `simulate()`: its `render()` is a function of its parameters
and, for a flexible leaf, its bound ports, evaluated when the tree is walked
for export, snapshot or a test instant — after the assembly has bound its
state. `FusionNode` is untouched.

### D7. Records

One ADR records the lifecycle (extends ADR-002 and ADR-023, supersedes the
placement note in ADR-064 and the fixes cycle's recommendation). The
architecture synthesis, the declaring, animation, driving and testing pages,
the changelog and `HISTORY.rst` follow.

## Risks / Trade-offs

- **First-run decision.** A `render()` whose driver read is conditional may
  be classified once-only and go stale. Mitigation: the warning and the
  docs state the rule; a read on any later run cannot happen because the
  method is not re-run. This is the same class of risk `assemble()`'s
  memoization already carries.
- **Cached children on constructor-form classes.** A legacy `render()`
  that constructs fresh children each call and reads no driver now keeps
  its first children. Identity is better for it; a class relying on
  re-construction side effects would differ. None is known.
- **Warning noise.** The framework's own test suite defines many assemblies
  that read `self.time` in `render()`; they now warn. Tests are not
  configured to treat warnings as errors, and the suite's own fixtures are
  migrated only where a test is about the new behaviour.
- **Perturbation assertions.** The test framework inserts a perturbation
  before the node's first `Translation`; with a driven translation at the
  head of the list the insert lands before it, still in the node's own
  pre-placement frame, which is the documented intent.
