# Design: multi-driver-state-seam

## Context

ADR-056 (this worktree, Proposed) sets the stepped-simulation
direction: state lives in drivers, geometry stays a pure function of a
bound snapshot. The 2026-08-25 spike (`spike/FINDINGS.md`) validated
the whole loop from outside the framework and named four seams; this
change opens the two that live in the node layer (state-dict binding;
declaration/state separation appears here only as the port-slot
pattern) plus the pre-emptive tag rename. The relevant machinery
today: `AssemblyNode._time` + `set_keyframe`/`clear_keyframe`
(assembly.py), the `_idempotent_render` sweep keyed on
`operation._driver` (base.py/assembly.py), and no port concept at all.

Constraints: v0.4-era projects (v8-engine and every existing project)
must observe zero behavior change; the framework repo owns this
change; stage 2 (`solid_node/simulation/`) builds only on surface
ratified here.

## Goals / Non-Goals

**Goals:**

- `set_state(**states)` / `clear_state(*names)` / `state` mapping on
  `AssemblyNode`, with `set_keyframe`/`clear_keyframe` as exact
  time-only wrappers.
- Domain-typed ports with class-level declaration, per-instance value
  slots, linear unit scale, and causal `connect()`.
- Rename `operation._driver`/`_driven_nodes` to
  `_animator`/`_animated_nodes`.

**Non-Goals:**

- No `Driver` declarations, programs, `Sim`, or scenario runner
  (stage 2). No viewer/document-schema change, no named-variable
  symbolic expressions, no flow variables, no equation solving, no
  G-code. No change to artifact caching or the build pipeline.

## Decisions

1. **Merge semantics for `set_state`.** `set_state` merges entries
   into the current snapshot; `clear_state(*names)` removes named (or
   all) entries. Alternative — replace-whole-snapshot — was rejected
   because `set_keyframe(t)` must stay exactly today's behavior
   (touching only time) while being a pure wrapper
   (`set_state(time=t)`); merge gives that for free, and a stepping
   loop that sends full snapshots each tick is unaffected.
2. **Unbound named state fails loudly; `time` keeps its symbolic
   fallback.** A state-consuming assembly rendered without a snapshot
   raises an error naming the missing entry and `set_state`.
   Alternative — silent defaults at the node layer — was rejected:
   defaults belong to stage 2's `Driver` declarations; inventing them
   here would bake an implicit contract the simulation layer must then
   honor forever. The `time` fallback to `$t` is grandfathered ADR-008
   behavior, not a precedent.
3. **Storage: one `_states` dict replaces `_time`.** `_time` becomes
   `_states['time']`; the `time` property reads the dict with the
   symbolic fallback. `clear_keyframe` = `clear_state('time')`.
   Propagation reuses the exact `_rendered_children` recursion and
   non-list tolerance that `set_keyframe` has today — the spike proved
   this path needs nothing else.
4. **Ports are descriptors materializing per-instance slots.** The
   class attribute (`crank = RotationalPort(out=True, unit='deg')`)
   holds declaration metadata only; `__set_name__`/`__get__`
   materialize a per-instance bound slot on first access (the
   Django-field pattern). Alternative — instance-attribute ports
   created in `__init__` (as the spike did) — was rejected because it
   conflates declaration with state exactly the way the spike flagged
   for drivers (FINDINGS seam 2), and blocks class-level discovery.
5. **`connect()` lives on `InternalNode`, runs per render, applies
   the sink's linear scale.** It is sugar over "sink.value =
   scale(source value)" — no registry, no graph object, no deferred
   resolution. Alternative — a connection graph resolved at assemble
   time — is the stage-3 acausal seam; building any of it now would
   speculate past ratified evidence.
6. **Tag rename is mechanical and internal.** `_driver` → `_animator`,
   `_driven_nodes` → `_animated_nodes`, in base.py, assembly.py, and
   the two test files that reach the attribute. No compatibility
   shim: the attribute is underscore-private and the framework repo
   plus its own tests are the only known readers.
7. **File layout.** New `solid_node/node/ports.py`; state seam in
   `solid_node/node/assembly.py` + no-op root in `base.py`;
   `connect()` in `internal.py`; exports in `node/__init__.py`.
   `solid_node/simulation/` is deliberately NOT created in this
   change.

## Risks / Trade-offs

- [Merge semantics let stale entries linger across logical runs] →
  `clear_state()` with no arguments empties the snapshot; stage 2's
  `Sim` owns lifecycle and always binds full snapshots per tick.
- [Loud unbound-state error makes `solid build` fail on
  state-consuming assemblies] → accepted for stage 1 and explicitly
  so: the error names the cure; stage 2's declared defaults are the
  designed resolution (ADR-056 seam 2).
- [Descriptor ports add a metaclass-adjacent pattern to a codebase
  that avoids magic] → scope is one small, standard descriptor;
  `__init_subclass__` precedent already exists in `AssemblyNode`.
- [Renaming `_driver` breaks an unknown external reader] → the
  attribute is private and pre-1.0; the kinematics spec text is
  updated in the same change, and grep shows only in-repo readers.

## Migration Plan

Purely additive plus an internal rename; no data or artifact
migration. Rollback is reverting the change commits. Existing projects
require no edits: `set_keyframe`/`clear_keyframe` behavior is
spec-pinned unchanged and re-validated against the v8-engine suite.

## Open Questions

None blocking. Deferred by design: driver declarations/defaults,
simulation package, viewer driver table (all ADR-056 stage 2+).
