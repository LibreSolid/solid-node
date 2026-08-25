# Proposal: multi-driver-state-seam

## Why

A machine that is not periodic — the Metamaquina2 printer executing
instructions, a car with independent steering and throttle — cannot be
expressed as a function of the single looping `time` scalar ADR-008
provides; its pose depends on several independent inputs. ADR-056
(Proposed, in this worktree) designs the stepped-simulation direction
and its core was spike-validated end-to-end on 2026-08-25
(`spike/FINDINGS.md`) using the existing keyframe machinery shimmed
from outside; the spike named the exact node-layer seams the framework
must open. This change is stage 1: open those seams, and only those,
so the simulation layer (stage 2) can be built on ratified surface.

## What Changes

- Generalize keyframe binding to a **multi-driver state snapshot**:
  `set_state(**states)` binds a dict of named numeric driver values on
  an assembly and propagates recursively exactly as `set_keyframe`
  does today; `render()` reads the snapshot via a `state` mapping.
  `time` is one entry among several.
- `set_keyframe(time)` and `clear_keyframe()` are preserved as exact
  compatibility surfaces over the generalized binding — existing
  projects (v8-engine) observe no behavior change.
- Add **domain-typed ports**: `Port` base plus `RotationalPort`,
  `TranslationalPort`, and `SignalPort` — unit-tagged value slots a
  node re-binds on every render, with a declared unit conversion and a
  reserved (absent) flow slot per ADR-056's bond-graph down payment —
  and a causal `connect()` binding on internal nodes.
- Rename the ADR-023 internal operation tag `operation._driver` /
  `assembly._driven_nodes` to `operation._animator` /
  `assembly._animated_nodes`, clearing the naming collision with the
  new Driver concept before stage 2 introduces it. Internal attribute;
  the kinematics spec text that names it is updated in the delta.
- Explicitly excluded (stage 2 and later, per ADR-056): the
  `solid_node/simulation/` package (Driver declarations, programs,
  Sim loop, scenarios), viewer/document schema changes, G-code, flow
  variables, and any equation solving.

## Capabilities

### New Capabilities
- `ports`: domain-typed connection points on nodes — value slots with
  unit metadata, per-render re-binding, unit conversion for
  design-unit targets, and the causal `connect()` wiring.

### Modified Capabilities
- `kinematics`: the "Normalized animation time" requirement
  generalizes to multi-driver state binding (`set_state` as the
  primitive, `set_keyframe`/`clear_keyframe` as the preserved
  time-only surface over it); the "Driver-tagged idempotent renders"
  requirement is re-worded for the `_animator` tag rename (behavior
  unchanged).

## Impact

- Code: `solid_node/node/base.py` (no-op `set_state` root, tag
  rename), `solid_node/node/assembly.py` (state dict, propagation,
  `state`/`time` properties, tag rename), new `solid_node/node/ports.py`,
  `solid_node/node/__init__.py` exports, `solid_node/node/internal.py`
  (`connect()`).
- Specs: `kinematics` delta; new `ports` spec.
- Tests: new red-first tests for state binding, compatibility, sweep
  purity under `set_state`, and ports; existing kinematics/keyframe
  tests must pass unchanged.
- Validation callers: v8-engine test suite unchanged (periodic path);
  the spike model in this worktree exercises the new seam shape.
- No viewer, export, document-schema, or CLI changes; no dependency
  changes.
