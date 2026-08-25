# Tasks: multi-driver-state-seam

## 1. Animator tag rename (isolated, keeps later diffs clean)

- [ ] 1.1 Red: add a focused test asserting the sweep keys on
      `operation._animator` / `assembly._animated_nodes` (fails while
      the old names exist)
- [ ] 1.2 Rename `_driver`/`_driven_nodes` to
      `_animator`/`_animated_nodes` in `solid_node/node/base.py` and
      `solid_node/node/assembly.py`; update the references in
      `tests/test_meta.py` and
      `tests/meta_project/test_steered_wheel.py`
- [ ] 1.3 Green: full existing kinematics/meta test set passes
      unchanged

## 2. Multi-driver state binding

- [ ] 2.1 Red: new `tests/test_state_binding.py` covering the six
      kinematics-delta scenarios — two named drivers bind numerically;
      merge preserves unrelated entries; unbound access raises naming
      the entry and `set_state`; repeated `set_state` cycles hold
      exactly one render's operations with static placement intact;
      `clear_state()` restores symbolic `$t`; leaf no-op
- [ ] 2.2 Implement `set_state`/`clear_state` no-op roots on
      `AbstractBaseNode` and the real binding on `AssemblyNode`:
      `_states` dict replacing `_time`, `state` mapping with the loud
      unbound error, `time` property reading `_states['time']` with
      symbolic fallback, propagation through the existing
      `_rendered_children` recursion
- [ ] 2.3 Red→green: keyframe-equivalence tests —
      `set_keyframe(t)` ≡ `set_state(time=t)` preserving other
      entries; `clear_keyframe()` ≡ `clear_state('time')`; then
      reimplement both as wrappers
- [ ] 2.4 Green: the entire pre-existing keyframe/animation test set
      passes with zero edits (spec-pinned unchanged behavior)

## 3. Ports

- [ ] 3.1 Red: new `tests/test_ports.py` covering the four ports-spec
      scenarios — per-instance value isolation; class-level discovery
      with domain/unit/direction/scale; microsteps-to-millimetres
      conversion through `connect()` under `set_state`; absolute
      rebinding across successive snapshots
- [ ] 3.2 Implement `solid_node/node/ports.py`: `Port` descriptor
      (`__set_name__`/`__get__` materializing per-instance slots),
      `RotationalPort`, `TranslationalPort`, `SignalPort`, declared
      linear scale; no flow variable
- [ ] 3.3 Implement `connect(source, sink)` on `InternalNode`
      (per-render causal binding, scale applied); export the port
      classes from `solid_node/node/__init__.py`
- [ ] 3.4 Green: ports tests pass; whole framework suite passes

## 4. Validation and records

- [ ] 4.1 Run the full framework test suite from the worktree bench
      (worktree `.env`, `PYTHONPATH=$PWD`, workspace venv)
- [ ] 4.2 Caller validation: run the v8-engine project suite against
      this worktree's framework — zero behavior change expected; run
      the spike scenario (`spike/axis/scenario.py`) — still green
      through the compatibility wrapper
- [ ] 4.3 Update the kinematics spec text and ADR index per the
      archived delta; extract/update ADRs only for decisions this
      implementation confirms (ADR-056 remains Proposed until its
      stages complete); sync `docs/architecture.md` if the synthesis
      changed
