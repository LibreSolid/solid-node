# ADR-065: Instance Checks After Resolution

**Status:** Accepted
**Date:** 2026-09-02
**Extends:** [ADR-062: Typed Parameters and the Exponent Algebra](./ADR-062-typed-parameters-and-the-exponent-algebra.md)
**Depends on:**
- [ADR-061: A Call in a Node Class Body Is a Declaration](./ADR-061-a-call-in-a-class-body-is-a-declaration.md)
- [ADR-063: Identity From Resolved Declared Values](./ADR-063-identity-from-resolved-declared-values.md)

## Context and Problem Statement

A declared parameter carries `min=` and `max=`, and most of a project's
guards are exactly that: the v8-engine migration turned about forty of them
into declarations. The rest relate two parameters — the valve stop must clear
the stem, the cap must be tall enough for the frame clearance plus the head —
and had nowhere to go. A comparison in a class body is refused (ADR-062), and
the framework called nothing after resolving an instance's parameters, so nine
migrated classes grew an `__init__` back for the sole purpose of holding a
guard, which is the method the declarative form set out to delete.

## Decision Drivers

- A guard must run once the parameters are plain values and before anything
  is built or realized on their strength: a refused root should build no
  subtree.
- The exception must reach the caller unchanged; project tests expect
  `ValueError` from a constructor with a bad pair.
- One method, chaining through subclasses, on the existing surface.
- `validate(self, rendered)` already means the render-output check on leaves,
  fusions and flexible parts, and a name cannot mean two things.

## Considered Options

1. **`check(self)`, a no-op on `AbstractBaseNode`, called by `__init__` on a
   declarative instance immediately after `resolve_parameters` and before
   `realize_children`** (chosen)
2. A class-body constraint form, `Check(stop > stem, "...")`
3. Calling the hook after children are realized
4. Leaving guards to a hand-written `__init__`

## Decision Outcome

Chosen: **`check()`, after resolution, before realization.**

`AbstractBaseNode.check()` does nothing; a subclass overrides it, reads its
parameters as the plain values they already are, and raises. `__init__` calls
it right after `_parameters` is resolved: `self.name` is set, nothing is
built, no child exists. Whatever it raises propagates. Because `check` is now
a base attribute, the shadow guard of ADR-062 refuses a *parameter* of that
name, which is right.

The framework calls it only on a declarative instance. A class in the
constructor form assigns its attributes after `super().__init__()` returns,
so a call from the base constructor would see none of them; such a class
keeps its guards where it has them, and the documentation says so.

Option 2 would put comparisons back into the class body that ADR-062 keeps
them out of, and a constraint language is a larger design the pilot has not
asked for. Option 3 is later, costlier, and a guard over parameters needs no
children. Option 4 is the state this decision replaces.

## Consequences

- A migrated class with a cross-parameter guard needs no `__init__` for it.
- A refused root realizes nothing: `Engine(clearance=0.1)` with a guard
  against it fails before a single child is constructed.
- `check()` runs on every construction, including each of `repeat(count)`'s
  identical units; it is a few comparisons.
- A project method already named `check` on a declarative class is now
  called at construction. None of the three migrated projects has one; the
  changelog names the hook.

## References

- `solid_node/node/base.py` — `AbstractBaseNode.check`, the call in `__init__`
- `tests/test_declarative_nodes.py` (`InstanceCheckTest`)
- `docs/declaring.rst`, "Checking parameters together"
- OpenSpec change `declarative-node-api-fixes`, capability `declarative-nodes`
