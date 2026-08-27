## Context

A driver is declared as class metadata — `x = Driver(default=..., unit='mm')`
— and read back through a string key: `self.state['x']`. A port is
declared the same way and read as `self.position`, because `Port` is a
descriptor: the declaration lives on the class, the bound value
materializes per instance (`solid_node/node/ports.py`). Ports and
drivers are discovered by the same MRO scan over `vars()`; only the
read differs, and only drivers use a magic string.

The constraint that shapes this change is the layering ADR-056
established and both module docstrings restate: `solid_node/node/`
imports nothing from `solid_node/simulation/`. The node layer owns the
snapshot (`AssemblyNode._states`), its propagation, and the
`DriverDeclaration` marker it needs in order to recognize a
declaration; the simulation layer owns what a driver *means* — native
units, integer dtype, ramps, programs.

The `_states` dict a node holds is keyed by BARE local names, always.
Three places write it — `assembly._receive_state` (which filters
`'.' not in name`), `qualified.drive_tree` (which writes the
class-local name), and `serializer.symbolic_drivers`'s restore — so a
dotted qualified id never lands in a node's own snapshot. That is what
makes an attribute read possible at all: `set_state(**{'x_axis.motor': 8000})`
arrives at the child as plain `motor`.

## Goals / Non-Goals

**Goals:**

- Read a declared driver as `self.x`, in every binding mode, with the
  declaration still readable off the class.
- Keep the existing loud-failure contract for an unbound driver, and
  extend loudness to the two new mistakes the attribute namespace
  makes possible: assigning to a driver, and declaring one under a
  name the node class already carries.
- Leave exactly one way to read a driver value: delete the `state`
  mapping, and refuse to bind a name no declaration bears.
- Change nothing about propagation, qualification, the document
  schema, the simulation bank, or the viewer.

**Non-Goals:**

- Attribute access for `sim.state`, whose keys are qualified ids
  (`x_axis.motor`) and therefore not attribute names.
- Attribute forms for `set_state` binding, `Instruction` targets, or
  the document's driver table — all three are flat namespaces
  addressed by qualified id.
- Extending the shadowing guard to `Port`, which has the same latent
  hazard and no reported instance of it.

## Decisions

### The descriptor lives on `DriverDeclaration`, in the node layer

`DriverDeclaration` (in `solid_node/node/qualified.py`) gains
`__set_name__`, `__get__` and `__set__`. `Driver` (in
`solid_node/simulation/driver.py`) inherits them and gains nothing of
its own.

Alternative considered: put the descriptor on `Driver`. It works — a
throwaway monkeypatch of `Driver.__get__` ran the 130 driver, state,
port, simulation and document tests green — but it puts knowledge of
`AssemblyNode._states` in the simulation layer, whose entire stated
job is to be ignorable by a node that declares no driver. Reading a
bound value off a node is exactly the node layer's half of the split
the module docstring already draws: "the node layer has to RECOGNIZE a
declaration to qualify it and deliver a state entry to it, while what
a driver means stays here." Delivering the entry and handing it back
are the same responsibility, and `Port` — the precedent — is already a
node-layer descriptor.

### A data descriptor, not a non-data one

`__set__` is defined, and it raises. A descriptor with only `__get__`
loses to an instance attribute of the same name, so `self.x = 5` in a
subclass `__init__` would silently shadow the driver for every
subsequent read — a failure that surfaces as wrong geometry, not as an
error. Defining `__set__` makes the instance dict lose instead, and
turns the assignment into an error naming `set_state`.

This also keeps `_attr_name_for` — which derives child names by
scanning a node's `__dict__` — unaffected, because a data descriptor
never puts anything in the instance dict.

### The name is stored in a private non-field slot

`Driver` is a frozen dataclass, so `__set_name__` writes through
`object.__setattr__`, and it writes `_name` rather than a `name`
field. A field would join the generated `__eq__`, `__hash__` and
`__repr__`, changing declaration equality on the basis of where a
declaration happens to be bound — two identical declarations on
different attributes would stop comparing equal. `Port` can afford a
public `self.name` because it is a plain class; `Driver` cannot.

### The shadowing guard fires at class definition

`__set_name__` walks `owner.__mro__[1:]` and raises if any base
already carries the name under something that is not itself a driver
declaration. `AssemblyNode` has 36 public members — `render`, `state`,
`time`, `color`, `mesh`, `shape`, `exact`, `fn`, `validate` and the
rest — several of which read as plausible driver names for a
mechanical design. Before this change such a name was confined to a
mapping key and harmless; after it, `color = Driver(...)` would
displace `AssemblyNode.color` and break rendering with no message.

The guard is at declaration time because that is the only moment the
mistake is cheap to read. Excluding names carried by a base that are
themselves driver declarations is what keeps subclass redeclaration
legal, which `declared_drivers_of` explicitly supports ("walked
base-first so a subclass redeclaring an inherited driver wins").

Every driver declared anywhere in the framework and its spikes today
— `motor`, `lift`, `axis`, `whole`, `free`, `x` — clears the guard, so
it introduces no migration.

### Both failures raise `AttributeError`

An unbound read and a rejected assignment are attribute operations, and
`AttributeError` is what the protocol expects; the messages carry the
driver name and `set_state`, matching the mapping's existing wording.
Raising `KeyError` from `__get__` would also break `copy`, `pickle` and
`inspect`, which probe for optional dunders with
`getattr(obj, name, None)` and only catch `AttributeError`.

### The `state` mapping is removed, not demoted

An earlier draft of this design kept the mapping and demoted it in the
documentation. The three reasons it gave do not survive checking, and
none of them is a capability:

- **`time`.** `AssemblyNode.time` is already the interface, with the
  `$t` fallback. `state['time']` appears once in the whole repository,
  in a test assertion.
- **Undeclared names.** `set_state` accepts a name nothing declares,
  and the stage-1 classes in `tests/test_state_binding.py` and
  `tests/test_ports.py` rely on that. But this is a leftover of build
  order, not a design: `set_state` shipped in
  `multi-driver-state-seam` and `Driver` arrived after it in
  `stepped-simulation-layer`. Every real caller — `Sim` from
  `qualified_drivers`, the loader from declarations, the widget parity
  fixture, both spikes, Metamaquina 2 — binds declared drivers only.
- **`dict(node.state)` as enumeration.** Real, but it is a different
  operation from reading one driver, and it is not the designed
  authority for it either: `simulation/enumeration.qualified_drivers`
  is, by `docs/architecture.md`'s own words, "the one authority on
  what drivers a machine has". The dozen assertions that use it can
  assert the contract instead — the attribute reads the value, or
  raises after `clear_state()` — which pins behavior rather than a
  container's contents.

The one reason that would have been real is a render reading a driver
declared on an ANCESTOR, which a descriptor cannot reach. There are
zero such reads in the framework, its fixtures, its spikes, or
Metamaquina 2. The designed path for a parent's driver to reach a
child is `connect()` into a port, which is exactly what the
Metamaquina 2 root does with `x` and `y`.

Nothing is released, so there is no compatibility argument. Two read
surfaces for one value is noise the framework would have to keep
explaining, and the mapping is the one that does not match how a
`Port` is read. So `_BoundState` and the `state` property are deleted.

### `set_state` refuses a name no declaration bears

This follows from the removal rather than extending it. Once the
attribute is the only read, an entry with no declaration behind it can
never be read by anything: `set_state(motr=4000)` would bind a dead
key and fail later, somewhere else, as an unbound-driver error naming
a different name. Refusing it at the binding names the actual mistake.

The check is nearly free, because the walk already computes what it
needs. `_receive_state` collects `declared[local_name] -> [qualified
ids]` for every declared driver in the tree, to detect an ambiguous
bare name. A bare name absent from that map is undeclared; a dotted
name absent from the union of its values is not a qualified id the
tree publishes. Both reuse the rollback the ambiguity path already
performs, so a refused binding leaves no half-bound tree.

That rollback is the one cost. Today `saved` is built only when the
call carries a bare project-driver name, which is never true for
`Sim`, since it binds by qualified id — so the stepping loop pays
nothing. With names to validate in either form, `saved` is built on
every binding, which is one small dict copy per assembly node per
`set_state`.

Measured on the two-axis fixture over 200 ticks at dt=0.01, best of
five runs: 32.1 µs/tick with the snapshot against 30.1 µs/tick
without, so 2.0 µs/tick or 6.7%. That is 6.7% of a BARE tick, and a
bare tick is not what a scenario costs — `sim.py`'s own reasoning is
that "a bare tick is microseconds while one mesh assertion is
milliseconds", which is why cadence exists at all. Two microseconds
against a millisecond assertion is three orders of magnitude below the
thing that actually sets scenario runtime, so this is absorbed rather
than taken back to the pilot.

Alternatives considered: validating against a cached declaration set
(the declarations are only known by walking, and the walk is the
binding); and skipping rollback on refusal (it would leave a
partially-bound tree, which is exactly what the ambiguity path goes to
this trouble to avoid).

## Risks / Trade-offs

- [`hasattr(node, 'x')` returns `False` for an unbound driver, and
  `getattr(node, 'x', default)` silently yields the default, because
  both swallow `AttributeError`] → Accepted. No framework code probes
  a node for a driver name that way; discovery goes through
  `declared_drivers_of`, which reads `vars()` and never triggers the
  descriptor. The alternative — a non-`AttributeError` exception —
  breaks `copy`/`pickle`/`inspect`, which is a worse trade.

- [Nothing publicly reports "what is currently bound on this node"
  once the mapping is gone] → `qualified_drivers(root)` reports what a
  machine declares, the serialized document publishes the same ids and
  values, and `node._states` remains for a debugger. No caller in the
  framework, its spikes, or Metamaquina 2 needs a public per-node
  snapshot view; if one appears, it is a named enumeration surface to
  design, not a reason to keep a second read path.

- [`set_state` becoming strict could refuse a binding some caller
  makes today] → Verified against every caller: `Sim` (both the
  construction bind and the per-tick bind), the loader's default
  binding, `set_keyframe`, the widget parity fixture, and both spikes
  bind declared drivers or `time` only. The bindings it would refuse
  are in stage-1 test fixtures that declare nothing, and those are
  converted to declare what they bind.

- [The shadowing guard could reject a name a future project wants] →
  It rejects only names a node class already uses, where the
  alternative is silent breakage; the message names the collision and
  the cure is to rename the driver. It already catches one real case:
  `tests/test_ports.py`'s `Axis` binds `motor` while holding a CHILD
  node on `self.motor`, so converting it to a declaration requires
  renaming one of the two.

- [A driver declared on a `LeafNode` has no `_states` to read] → It
  already has no bound value today; the descriptor raises the same
  loud unbound error rather than inventing one. Drivers on leaves
  remain outside the enumeration walk, unchanged by this change.

## Migration Plan

Breaking, and deliberately so: nothing is released, and the only
callers are in this repository and in Metamaquina 2. Every
`self.state['name']` read becomes `self.name` on a class that declares
it; every `state['time']` read becomes `self.time`; every
`dict(node.state)` assertion becomes an assertion on the attribute.
Two stage-1 fixture classes that bind names they never declared get
declarations, one of them with a rename to clear the child-attribute
collision. The Metamaquina 2 project — the originating finding, and an
independent repository outside this change's commits — converts its
three root-assembly reads as the confirming caller.

There is no rollback plan beyond reverting the commit; the change is
two commits on a branch that integrates only under explicit pilot
direction.

## Open Questions

None.
