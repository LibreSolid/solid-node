## Context

`solid_node/node/ports.py` (ADR-056) and `solid_node/node/timebase.py`
(ADR-072) live under the node package for historical reasons: they were
written while `solid_node.node` was the only place a declaration could
go. Neither describes a shape. The design note
`workflow/motion/joints-and-couplings.md` settles the rule that one
top-level module answers one question and plans two further cycles —
`joints` and `couplings` — whose names have no home under that rule.
`workflow/motion/roadmap.md` makes this cycle 1 of the three.

Current shape, read from the source rather than from the note:

- `node/ports.py` defines `BoundPort`, `Port`, `bind`, `RotationalPort`,
  `TranslationalPort`, `SignalPort`, `declared_ports`. It imports
  `note_read` from `solid_node/node/phase.py` at module scope and
  nothing else.
- `node/timebase.py` defines `Time` and `declared_time`. It imports
  `math` and `dataclasses`; both of its reaches into the node tree
  (`AssemblyNode` in `Time.__set_name__`, `read_time` in `Time.__get__`)
  are already function-local imports, written that way to break exactly
  the cycle this change would otherwise create.
- `node/internal.py` imports `bind` at module scope; `node/assembly.py`
  imports `declared_time` at module scope; `node/flexible.py`,
  `core/serializer.py` and `manager/snapshot.py` import from the module
  paths.
- `node/__init__.py` defers all six public names through `_EXPORTS`
  (`Port`, `RotationalPort`, `TranslationalPort`, `SignalPort`,
  `declared_ports`, `Time`) so `solid` startup does not pay for them.

**The design note is wrong on one point, and the source wins.** It lists
`connect` among the names moving to `solid_node.motion.ports`. There is
no module-level `connect`: `connect(source, sink)` is a method of
`InternalNode` (`solid_node/node/internal.py`), sugar over `bind`. It is
a verb a node performs, not a name a project imports, and it stays where
it is. What moves is `bind`, which `connect` calls. The note also does
not mention `BoundPort` or `declared_time`; both move with their module,
`BoundPort` because it is the value slot `Port.__get__` materializes and
`declared_time` because the serializer and the snapshot manager read it.

Constraint from `cli-startup-cost` and `source-closure-cost`: the node
package defers its exports precisely so a `solid` invocation touching no
geometry pays no CAD import. Nothing here may make an import eager that
is lazy today, and no import may become circular at module load.

## Goals / Non-Goals

**Goals:**

- One package, `solid_node.motion`, answering "what moves, and what
  drives what", with `ports`, `joints` and `couplings` submodules.
- Ports and the time base reachable only from
  `solid_node.motion.ports`, with the old modules deleted.
- The old import path failing loudly, with a message that names the new
  one.
- Zero behaviour change: same classes, same descriptors, same errors,
  same warnings, same expressions.

**Non-Goals:**

- Any joint or coupling content. `joints.py` and `couplings.py` are
  empty in this cycle by design; naming a class in them now would let
  cycles 2 and 3 be written against a guess.
- A compatibility shim, alias, or `DeprecationWarning` path.
- Relocating `Driver`, `Instruction`, `Sim` or anything else in
  `solid_node.simulation`; the note is explicit that `Driver` is what
  the machine is told, not the channel it is told through.
- Touching `solid_node/simulation/timebase.py`. It is a different module
  with a different subject (`finite_seconds`, ADR-083) that happens to
  share a filename; it stays where it is.

## Decisions

### 1. `motion.ports` is a single module holding both files' contents

`node/ports.py` and `node/timebase.py` merge into
`solid_node/motion/ports.py`. **Why:** `Time` is a port-kind thing — the
root's own channel, the note's words — and it already reads as a
declaration descriptor with a per-instance value, the same shape `Port`
has. Two modules for one kind would put `from solid_node.motion.ports
import SignalPort` and `from solid_node.motion.timebase import Time`
side by side in the same clock, when the rule says the import line
should say the kind, and the kind is the same. **Alternative
considered:** keep a separate `motion/timebase.py`. Rejected: it
preserves a split with no question behind it, and the roadmap names
`motion.ports` as the home of `Time` explicitly.

The merged module keeps both docstrings, joined under one module
docstring that states the subject: values that flow between nodes,
including the root's time channel.

### 2. Dependency direction: `node` imports `motion`; `motion` reaches back only through `node.phase` and lazily through `node.assembly`

- `solid_node/motion/ports.py` imports, at module scope, exactly one
  framework name: `note_read` from `solid_node.node.phase`. That module
  is a deliberate leaf — its own docstring says it "imports nothing" so
  that every declaration kind can import it — so this edge cannot close
  a cycle.
- `Time.__set_name__` and `Time.__get__` keep their function-local
  imports of `solid_node.node.assembly` (`AssemblyNode`, `read_time`),
  unchanged from today. They are the only reach from motion into the
  node classes and they happen at class-definition and attribute-read
  time, never at module load.
- `solid_node/node/internal.py` imports `bind` and
  `solid_node/node/assembly.py` imports `declared_time` from
  `solid_node.motion.ports` at module scope, exactly as they import them
  from `.ports` / `.timebase` today.

**Why this direction:** the node classes are the consumers — a node
declares ports, an assembly reads a time base — and a consumer importing
its vocabulary is the normal direction. The reverse (motion importing
the node classes at module scope) would be a genuine cycle, because
`node/__init__.py` eagerly imports `.base` and `internal`/`assembly`
sit above it.

**Load-order check.** Importing `solid_node.motion.ports` first runs
`solid_node/node/__init__.py` (which eagerly imports only `.base`;
`base.py` imports `sources`, `phase`, `declarative`, `operations` and
never `internal`, `assembly`, `ports` or `timebase`), then
`solid_node.node.phase`. Nothing in that chain reaches back into
`motion`, so `motion.ports` finishes its own module body. Importing
`solid_node.node.internal` first completes `node/__init__` before
reaching `motion.ports`, which then finds `solid_node.node` already in
`sys.modules`. Neither order sees a half-built module. A red-first test
imports each of the two orders in a fresh interpreter so a future edit
cannot quietly close the loop.

**Import-time cost.** `solid_node.motion.ports` pulls
`solid_node.node.__init__` and therefore `solid_node.node.base`
(`numpy`, `solid2`) — which is exactly what it pulls today, since it *is*
a node submodule today, and what any consumer of it already pulls by
declaring a node. No CAD backend and no exact stack are added, so
`cli-startup-cost`'s ceiling is unchanged. **Alternative considered:**
relocate `phase.py` to a neutral `solid_node/phase.py` so `motion`
imports nothing from `node` at all. Rejected for this cycle: `phase` is
the render lifecycle, which belongs to what has shape; moving it is a
second relocation with its own spec surface and its own break. Noted as
an option if cycle 2 finds the edge awkward.

### 3. `solid_node.motion.__init__` exports nothing

The package `__init__` carries a docstring naming the three submodules
and their questions, and defines no names, no `__all__` entry beyond an
empty list, and **no** `__getattr__` deferring to `ports`. **Why:** the
import line is supposed to say which kind is in use —
`from solid_node.motion.ports import RotationalPort`. A convenience
re-export would create a second working path for every name, which is
precisely the ambiguity the `node`/`parameters` split removed (see the
`solid_node/node/__init__.py` docstring: "a second working path restores
exactly the ambiguity the split removed"). It also would make `import
solid_node.motion` cost `solid_node.node`, which an empty package does
not. **Alternative considered:** re-export the port kinds from
`solid_node.motion` for brevity. Rejected on the same rule that
motivates the whole change.

### 4. The old path fails as an `ImportError` naming the new module

`node/__init__.py` gains a table of moved names beside `_EXPORTS`:

```python
_MOVED = {
    'Port': 'solid_node.motion.ports',
    'RotationalPort': 'solid_node.motion.ports',
    'TranslationalPort': 'solid_node.motion.ports',
    'SignalPort': 'solid_node.motion.ports',
    'declared_ports': 'solid_node.motion.ports',
    'Time': 'solid_node.motion.ports',
    'ports': 'solid_node.motion.ports',
    'timebase': 'solid_node.motion.ports',
}
```

`__getattr__` consults it before falling through to `_submodule`, and
raises

```
ImportError: module 'solid_node.node' has no attribute
'RotationalPort': ports and the declared time base moved to
'solid_node.motion.ports'. Write `from solid_node.motion.ports import
RotationalPort`. solid_node.node answers what has shape;
solid_node.motion answers what moves.
```

It is an `ImportError`, not an `AttributeError`, because CPython's
`from X import Y` catches an `AttributeError` raised by a module
`__getattr__` and discards its message, substituting its own generic
"cannot import name" text; only an `ImportError` reaches the failing
import line unmodified, which is where the migration happens. The same
choice already governs a broken backend import in `_load`. `hasattr`
probes of a moved name therefore raise rather than answer False; no
framework code probes these names. The last two entries mean that reading
`solid_node.node.ports` as an attribute (the submodule access
`cli-startup-cost` guarantees) gets the same redirect rather than a bare
"no attribute". A direct `import solid_node.node.ports` statement raises
`ModuleNotFoundError` from the import system, which we accept as-is: a
shim module carrying a better message would be exactly the shim this
change refuses.

**Why a message at all**, when the point is that the break is visible:
because the break's purpose is to send a project to the new API, and a
message naming the module is the difference between a migration and a
bug report. It is a string, not a code path: nothing is importable
through it.

**Alternative considered:** a module-level `__getattr__` in a surviving
`node/ports.py` that warns and re-exports. Rejected — the roadmap and
the design note both state the break is deliberate and unshimmed, and a
warning shim leaves an unmigrated project running, which is the outcome
the break exists to prevent.

### 5. `connect` stays on `InternalNode`

See Context. `internal.py` changes one import line and nothing else. The
`ports` spec's "Per-render causal port binding" requirement already
describes `connect` as being "on an internal node", so no spec sentence
changes for it.

### 6. Spec deltas

- **`ports`** — MODIFIED "Domain-typed ports": one sentence stating the
  declarations are exported from `solid_node.motion.ports`. MODIFIED
  "Per-render causal port binding": one sentence stating the same for
  `bind`, `connect` being unchanged. ADDED "Ports are not node exports":
  the six names are not reachable from `solid_node.node`, with the
  scenario "The old path is refused" pinning the `ImportError` and the
  message naming `solid_node.motion.ports`, plus a scenario pinning that
  `solid_node.motion` itself exports no name. No behavioural sentence is
  rewritten.
- **`kinematics`** — MODIFIED "Declared time base": `exported from
  solid_node.node` becomes `exported from solid_node.motion.ports`.
  Everything else in the requirement is reproduced verbatim, because a
  MODIFIED block replaces the whole requirement.
- **`cli-startup-cost`** — MODIFIED "Node backend exports resolve on
  first use": the ports leave the deferred-export list, and the "unknown
  name" scenario gains its moved-name sibling. ADDED "The motion package
  is cheap to import": importing `solid_node.motion` imports no other
  `solid_node` module, and importing `solid_node.motion.ports` imports
  no CAD backend and no exact-geometry stack.
- **`user-documentation`** — MODIFIED only if its requirement names an
  import path for the port kinds; it names `solid_node.simulation` and
  `solid_node.math` today, so the apply step checks and adds a delta
  only if a sentence actually moves. Recorded here so the check is not
  forgotten.

`node-model`, `simulation`, `declarative-nodes`, `flexible-parts` and
`source-closure-cost` are untouched: none of them names the port module
path, and none of their behaviour depends on it.

### 7. One ADR, written during apply, as ADR-087

`docs/adrs/README.md` shows 086 in use (BUILD), so the next free number
is **087**: `docs/adrs/NODE/ADR-087-one-module-one-question.md`. It
records the module rule (`parameters` sizes a design, `node` has shape,
`motion` moves and drives, `simulation` tells the machine, `mechanisms`
is the arithmetic of laws, `math` is the algebra), the placement of
ports and the time base under it, and the deliberate break with no shim
and its reason — migration visibility. It **amends ADR-056 and ADR-072
on export location only**; both decisions' substance stands. It is
written after implementation, so it records what the code does rather
than what was hoped.

### 8. Evidence

- The framework suite from the worktree root:
  `PYTHONPATH=$PWD /home/asa/devel/libresolid-studio/.venv/bin/python -m
  pytest tests -x -q`.
- Red first: `tests/test_motion_package.py` asserting the new exports,
  the two empty submodules, the refused old path and its message, and
  the two import orders; plus the existing `tests/test_ports.py`,
  `tests/test_time_base.py` and `tests/test_node_lazy_exports.py`
  rewritten to the new paths, all failing on the current tree before the
  move.
- One migrated project, as proof the path fix is real and not just
  internally consistent: 3DPrintedClocks at
  `/home/asa/devel/libresolid-studio/projects/3DPrintedClocks`, whose
  `simulation/shared/assemblies.py` and four clock modules import port
  kinds and `Time` from `solid_node.node`. Its `simulation/shared` and
  `simulation/wall_clock_01` suites run against this worktree with
  `PYTHONPATH` pointing at it. **Its files are never committed from this
  cycle**; the project is its own repository and migrates on its own
  when the release lands.

## Risks / Trade-offs

- **A circular import appears later, when cycle 2 gives a joint a
  coordinate that is a port and a placement that is an operation** →
  the joint's reach into `node` is the same shape `Time`'s is, so the
  same function-local import solves it; the two-order import test added
  here fails loudly if a module-scope edge ever closes the loop.
- **Seventy-nine project files break at once** → that is the intent, and
  it is one mechanical edit per file. The changelog entry gives the exact
  before/after line, and the error message gives it again at the failure
  site. The break lands in an unreleased version, so no published
  release changes meaning under a user.
- **Merging two modules loses `git log --follow` on one of them** →
  `timebase.py`'s history stays reachable through the delete, and the
  ADR names both origins. Accepted as the cost of the merge.
- **`declared_time` and `BoundPort` are not named in the design note**,
  so a reader of the note alone will not expect them to move → the ADR
  and the changelog name every relocated symbol, and the spec delta
  names the public six.
- **Someone adds a convenience re-export to `motion/__init__.py`
  later** → the added spec scenario pins that `solid_node.motion`
  exports no name, so the suite refuses it.

## Migration Plan

The move is one atomic edit to the framework; there is no phased
rollout, because a shim is the thing being refused. A project migrates
by replacing, per file:

```python
from solid_node.node import AssemblyNode, RotationalPort, SignalPort, Time
```

with

```python
from solid_node.node import AssemblyNode
from solid_node.motion.ports import RotationalPort, SignalPort, Time
```

Rollback is `git revert` of the two cycle commits; nothing outside the
framework repository is written, so there is no external state to undo.

## Open Questions

None blocking. Two recorded for later cycles, neither decided here:

- Whether `solid_node/node/phase.py` eventually becomes
  `solid_node/phase.py`, so `motion` imports nothing from `node`.
  Deferred to cycle 2, which will know whether the edge hurts.
- Whether `motion.ports` should later split once joints own coordinates
  and the module grows. Deliberately not pre-empted: the note's rule is
  about questions, and one question is still one module.
