# Proposal: instance-qualified drivers

## Why

Stage 3a of ADR-056. Stages 1–2 shipped multi-driver state binding and
the stepped simulation layer, but driver names are class-local while
every flat namespace that must consume them — the serialized document
the viewer evaluates, the `Sim` state bank, `set_state` propagation,
instruction targets — cannot address two same-named drivers on sibling
instances (a printer's X and Y axes sharing one `Axis` class). The
2026-08-26 expression spike (`spike/expressions/FINDINGS.md`) validated
the cure end-to-end with zero framework edits: eagerly-qualified driver
tokens whose string is the dotted instance-path id (`x_axis.motor`),
client parity at 2.5e-14, and free `.scad` snapshot substitution. This
change opens the eight seams the spike named, so the serialized
document can carry a driver table and named-driver expressions — the
substrate the stage-3b interactive viewer consumes.

## What Changes

- **Qualified per-instance state binding.** `set_state` gains a
  qualified form addressing a specific instance's driver
  (`x_axis.motor`); `time` remains the one global, flat-propagating
  entry. Unqualified project-driver binding on a colliding tree is no
  longer silently shared.
- **Guaranteed-linked qualification.** Qualification is only computed
  where parent linking has run; a pass that cannot qualify fails
  loudly instead of colliding on the bare local name. `set_state`'s
  child walk links before it recurses.
- **Identifier rule for qualified ids.** A derived child name that is
  not a legal expression identifier (list-held children serialize as
  `axes-0`, which parses as subtraction) fails loudly when a driver
  would qualify through it. v1 forbids; it does not sanitize.
- **Symbolic serialization mode.** Document serialization binds every
  declared driver to its qualified token, renders, and serializes —
  distinct from a numeric snapshot; `_validate_state`'s
  numbers-only contract for `set_state` is not relaxed.
- **Tree-walk driver enumeration.** One authority enumerates a tree's
  declared drivers by qualified id, feeding both the `Sim` bank and
  the document driver table, so the id in the document and the key in
  the bank are the same string by construction. `Sim` works over a
  root whose drivers live on descendants; instruction lookup and
  targets qualify the same way.
- **`time` as the simulation clock.** `Sim` binds the global `time`
  entry each tick to the exact simulation instant (k·dt seconds), so
  `self.time` under a simulation reads the stepped clock. The
  normalized 0..1 `$t` animation path outside simulations is
  unchanged. **Decision for ratification:** simulation `time` is in
  seconds, not normalized — ADR-056's "time demoted to one driver".
- **Document schema v2.** The shared export/viewer document gains a
  driver table (qualified id, default, range, unit, dtype, scale) and
  operation expressions may reference qualified driver ids, preserved
  verbatim exactly as `$t` is; `version` bumps with producers and
  consumers updated together. `range` is presentation metadata, not a
  clamp. The `.scad` path substitutes bound driver values numerically
  and keeps `$t` symbolic (spike-proven free).
- **Build-path defaults.** Loading a driver-declaring node for
  build/test binds its declared defaults across the tree before the
  first render, removing today's self-bind-in-`__init__` workaround,
  without `node/` importing `simulation/`.

Out of scope (stage 3b or later, per ADR-056): the widget evaluator's
driver map and free-variable analysis, any UI (buttons, sliders,
transport), the client stepping loop, ADR-022's staleness revision,
G-code/sequencing, flow variables, trace-driven OpenSCAD animation
(excluded outright), and merging `Driver.scale` with `Port.scale` (the
driver table publishes the driver's unit story; unifying the two
declarations is deferred until the viewer proves it needs one source).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `kinematics`: "Multi-driver state binding" gains qualified
  per-instance addressing with `time` global, the guaranteed-linked
  propagation walk, loud failure for unqualifiable or illegal ids, and
  the symbolic serialization binding mode.
- `simulation`: driver enumeration becomes a qualified tree walk (root
  class only → whole tree); the `Sim` bank, instruction lookup, and
  instruction targets key by qualified id; `Sim` binds the global
  `time` clock each tick.
- `export`: the manifest/viewer document contract gains the driver
  table and qualified named-driver expressions, with the version bump
  and verbatim-preservation guarantee extended from `$t` to driver
  ids.
- `build-pipeline`: node loading binds declared driver defaults across
  the tree before the first render, so driver-declaring projects are
  buildable and testable without self-binding.

## Impact

- `solid_node/node/`: `assembly.py` (`set_state` qualified entries and
  linked propagation), `base.py`/`internal.py` (linking guarantees,
  identifier rule), a small qualified-token type interoperating with
  solid2's `OpenSCADConstant` (spike `DriverToken`, productionized).
- `solid_node/simulation/`: `declared_drivers` tree walk, `Sim` bank
  keys, instruction qualification, `time` binding.
- `solid_node/core/serializer.py` and the export producer: symbolic
  binding mode, driver table, schema version bump; widget/web viewer
  consumers updated for the version gate only (evaluation of driver
  expressions is stage 3b — a v2 document with an empty driver table
  degrades to today's behavior).
- The dependency rule `node/` never imports `simulation/` is
  preserved; build-path default binding lives in the loader/manager.
- Callers: `set_keyframe`/`$t` behavior unchanged (v8-engine must pass
  unmodified); the stage-2 flat `set_state` form remains valid for
  non-colliding trees; `spike/expressions/` becomes caller validation
  after landing, as `spike/axis/` did for stage 2.
- Evidence chain: ADR-056, `spike/expressions/FINDINGS.md` (eight
  seams), originating projects Metamaquina2 (multi-axis requirement)
  and v8-engine (unchanged-behavior target).
