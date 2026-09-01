# ADR-061: A Call in a Node Class Body Is a Declaration

**Status:** Accepted
**Date:** 2026-09-01
**Extends:** [ADR-001: Composite Pattern Node Tree Architecture](./ADR-001-composite-pattern-node-tree-architecture.md)
**Depends on:**
- [ADR-056: Signals, Drivers, Ports, and Stepped Simulation](./ADR-056-signals-drivers-ports-and-stepped-simulation.md) — the declaration-as-class-attribute idiom (`Port`, `DriverDeclaration`)

## Context and Problem Statement

A node's children have always been built in `__init__`, before
`super().__init__()`, and its parameters stated three times — signature,
`self.x = x`, `super().__init__(x=x)`. Across two projects the corpus holds 99
such constructors. The shop's design reference (`docs/new-declarative-api.md`
in libresolid-studio) settles on the Django model shape instead: the class body
declares parameters and children, and the framework derives the rest.

The obstacle is a fact about Python, verified empirically: a node constructed
in a class body is a class attribute, one object mutated by every parent
instance. Eight cylinder units would drive one shared piston. So a call in a
class body cannot produce an instance; it must produce a *declaration* that
each parent realizes for itself. The framework needs a deterministic way to
tell the two situations apart.

## Decision Drivers

- Construction outside a class body must be untouched: every existing
  `__init__` keeps building real nodes.
- The signal must not depend on which arguments were passed — `guard = Guard()`
  in a class body is a declaration exactly as `piston = Piston(diameter=d)` is.
- A class body that raises on purpose (a dimension error, see ADR-062) must not
  poison later construction.
- The class body has to be able to name a declaration in an error message
  before the class exists.

## Considered Options

1. **A metaclass whose `__prepare__` marks the body's namespace, recognized on
   the stack by a node constructor** (chosen)
2. A metaclass counting body depth in `__prepare__` and `__new__`
3. Call-frame inspection for a class-body frame, with no metaclass
4. Intercepting the namespace's `__setitem__` to convert an instance into a
   declaration after the fact
5. An explicit wrapper, `Child(Piston, diameter=d)`

## Decision Outcome

Chosen: **`NodeMeta`, the metaclass of every node class, whose `__prepare__`
returns a namespace of a private type; `AbstractBaseNode.__new__` walks the
stack and returns a `ChildDeclaration` when a frame's locals are such a
namespace.**

The class statement runs its body as a frame whose locals *are* the mapping
`__prepare__` returned. That mapping's type on the stack is therefore the body
executing, and nothing else — a non-node class body, a function, a test — can
produce it. A body that raised is no longer on the stack, so the signal cannot
stick (which is what rejected option 2: `__new__` never runs for an aborted
body, and a counter would stay incremented forever). The walk costs a few
`isinstance` checks per construction.

The same namespace names each declaration as it is assigned, so a dimension
error in the next line of the body can say `bore` and `pressure_angle` rather
than describe two anonymous tokens; `__set_name__` confirms the name when the
class is created, which is also what covers a class built by `type()`.

Because `__new__` returns something that is not an instance of the class,
Python skips `__init__`: the declaration carries the class, args and kwargs and
nothing runs until a parent realizes it. Realization happens inside
`AbstractBaseNode.__init__`, last, in declaration order, into the instance dict
under the declaring attribute — so `_link_child` and `_attr_name_for` see the
tree they always saw and naming, qualification and the serialized document need
no change. A declaration is a non-data descriptor: the realized node in the
instance dict wins on the instance, and the class hands back the declaration
for enumeration.

### Why not the alternatives

- Frame inspection alone (option 3) has no reliable mark to look for; a class
  body frame is distinguishable only by heuristics that helpers and other
  interpreters break.
- Converting after assignment (option 4) is too late: the node has already been
  constructed, with build directories made and a source closure computed.
- The explicit wrapper (option 5) is the earlier draft's syntax, which the
  reference rejected: it puts a second vocabulary where the class body should
  read as a parts list.

## Consequences

- `CadQueryNode`'s existing `CheckCQEditor` metaclass derives from `NodeMeta`;
  any project metaclass on a node must do the same. Documented beside it.
- Any node constructed while a node class body executes becomes a declaration,
  even through a helper function. That is the meaning of the position.
- A legacy class that constructed a node at class level relied on the shared
  instance; it now holds a per-instance child. The old behaviour was the bug the
  reference's probe found.
- A class body list comprehension cannot see class-level names (its own
  scope); Python raises `NameError` before the framework can help. Documented,
  with the literal list and `repeat()` as the forms that work.
- Reading a parameter off a sibling declaration in a class body raises with
  the advice to declare it on the parent: siblings do not reach into each
  other, by the pilot's decision.

## References

- `solid_node/node/declarative.py` — `NodeMeta`, `_DeclaringNamespace`,
  `in_class_body`, `ChildDeclaration`, `RepeatDeclaration`, `realize_children`
- `solid_node/node/base.py` — `AbstractBaseNode.__new__` and construction order
- `tests/test_declarative_nodes.py`
- OpenSpec change `declarative-node-api`, capability `declarative-nodes`
