# ADR-047: One shared OCCT currency for every exact backend

**Status:** Accepted

**Date:** 2026-08-22

**Change:** `build123d-leaf-adapter`

**Depends on:**
- [ADR-004: Multi-CAD Backend Adapter Pattern](ADR-004-multi-cad-backend-adapter-pattern.md)
- [ADR-044: Derived exact-geometry capability](ADR-044-derived-exact-geometry-capability.md)
- [ADR-045: Exact fusion composition](ADR-045-exact-fusion-composition.md)

## Context and Problem Statement

Until this change `CadQueryNode` was the only exact adapter, so "exact
geometry" and "CadQuery geometry" were the same thing in practice.
`solid_node/exact.py` reflected that: it holds shapes as CadQuery `Shape`
objects, though it performs the actual booleans and transforms through OCP
directly.

Adding `Build123dNode` made the conflation a decision that had to be taken
explicitly. build123d is a second front end over the same OCCT, and a project
may hold both kinds of leaf in one fusion. The framework had to answer what
type flows through the exact-geometry layer once more than one backend can
feed it, and whether an exact composition may mix backends at all.

A second, packaging-level problem arrived with it. `cadquery` and `build123d`
both depend on the `cadquery-ocp` distribution, which provides the single
importable `OCP` module, so the two are installable together only where their
version ranges intersect.

## Decision Drivers

- Exactness is a capability that composes: ADR-044 already makes an internal
  node exact when every child is, without regard to which adapter produced
  each child.
- The exact layer's operations — placement, fuse, common, BREP persistence,
  volume and solid counting — are backend-neutral OCCT work already.
- A per-backend geometry type would push a type test into every one of those
  operations and into every future consumer.
- Importing a CAD backend is expensive, and `solid_node.node` imports every
  adapter eagerly, so a project on one backend must not pay for another.

## Considered Options

1. **One shared currency, converted at the adapter boundary** (Chosen)
2. Restate the exact layer in terms of raw `TopoDS_Shape`
3. Keep each backend's own type and dispatch inside the exact layer

## Decision Outcome

Chosen option: **one shared currency, converted at the adapter boundary.**
Every exact adapter converts its render result to the CadQuery `Shape` that
`exact.py` already trades in, and everything downstream is unchanged.

The conversion is a rewrap, not a translation: build123d and CadQuery objects
each wrap a single OCCT `TopoDS_Shape`, exposed as `.wrapped`, so
`cq.Shape.cast(rendered.wrapped)` is the whole of it. Measured on a
50×50×50 box less a radius-10 bore, the converted shape reports the identical
volume (109292.037) as the build123d original, survives a BREP write/read
roundtrip at that volume, and fuses with a CadQuery shape into one solid.

That the currency is *CadQuery's* type is incidental and worth stating
plainly: it is the type the exact layer already used, and cadquery remains a
dependency regardless because `CadQueryNode` needs it. The decision is that
there is exactly one such type, not that it belongs to a favoured backend.

Two consequences follow directly:

- **Mixed-backend exactness needs no rule of its own.** ADR-044's
  every-child-is-exact composition already covers it once all exact children
  yield one type, so a fusion may mix `CadQueryNode` and `Build123dNode`
  children and fuse exactly.
- **The recognition is by module name, not by import.** `exact.py` identifies
  a build123d result from `type(rendered).__module__` rather than importing
  build123d, which costs about 1.6 seconds on a package that
  `solid_node.node` imports eagerly. A test asserts that importing
  `solid_node.node` leaves build123d out of `sys.modules`.

The packaging problem is resolved by pinning `cadquery` 2.7 with `build123d`
0.10, which share `cadquery-ocp` 7.8 — the newest pair that resolves to one
`OCP`. The newest release of each cannot be combined at all: build123d 0.11
moved to `cadquery-ocp-novtk`, a second distribution installing the same
`OCP` package, which would collide with the `cadquery-ocp` that cadquery 2.8
requires. This pin is a constraint the framework now carries and must revisit
whenever either project moves.

## Pros and Cons of the Options

### One shared currency, converted at the adapter boundary

- **Good**: Every exact operation stays backend-neutral with no type tests
- **Good**: Mixed-backend composition is free rather than a special case
- **Good**: A new OCCT backend costs one conversion and nothing else
- **Bad**: A build123d node returns a CadQuery-typed shape, which reads oddly
  until one knows both wrap one `TopoDS_Shape`
- **Bad**: Keeps a CadQuery dependency in a layer that is otherwise OCP

### Raw `TopoDS_Shape` as the currency

- **Good**: Names the thing that is actually shared, with no incidental
  backend in the exact layer's types
- **Bad**: Rewrites working, specified code for no behavioural gain
- **Bad**: Loses the convenience methods (`Solids()`, `Volume()`,
  `BoundingBox()`, `exportBrep`) that consumers and assertions already use
- **Bad**: Does not remove the cadquery dependency anyway

### Per-backend types with dispatch inside the exact layer

- **Good**: No conversion at all
- **Bad**: Every operation, present and future, grows a backend test
- **Bad**: Mixed-backend fusion becomes a case to implement rather than a
  consequence
- **Bad**: Spreads backend knowledge across a layer whose whole point is that
  the geometry is already common

## Consequences

The exact-geometry layer is now explicitly multi-backend, and adding a third
OCCT front end is a matter of one adapter plus one line of recognition. The
cost is a shared-OCP version constraint spanning two independent upstream
projects, which is a real maintenance obligation: a future realignment of
`cadquery-ocp` and `cadquery-ocp-novtk` must be re-evaluated as its own
change with its own evidence.

Because the conversion is a rewrap of the same kernel object, no tolerance,
tessellation or precision question arises at the boundary — the two backends
are not exchanging geometry, they are naming the same geometry.

## References

- `solid_node/exact.py` — `build123d_shape()`, `shape_from_rendered()`
- `solid_node/node/adapters/build123d.py`
- `tests/test_build123d_adapter.py` — conversion, mixed fuse, import cost
- `openspec/changes/archive/*-build123d-leaf-adapter/`
