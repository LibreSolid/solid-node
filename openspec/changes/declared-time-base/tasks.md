## 1. The declaration (red first)

- [ ] 1.1 Red: `tests/test_time_base.py` — `Time(loop=43200)` bound as
      `time` on an `AssemblyNode` subclass is readable off the class with
      `loop == 43200.0`; `Time()` without `loop`, `Time(loop=0)`,
      `Time(loop=-1)`, `Time(loop=inf)` and a non-numeric loop are refused;
      binding it as `clock = Time(...)` fails at class definition naming
      `time`; binding it on a `LeafNode`/`FusionNode` class fails naming
      `AssemblyNode`; `self.time = 3` on an instance fails naming
      `set_keyframe`; `from solid_node.node import Time` works.
- [ ] 1.2 Red: unbound `self.time` on the declaring root is a symbolic
      expression whose string is `$t` multiplied by the loop; a nested
      assembly (no declaration) under that root reads the same expression;
      a serialized rotation `360 * self.time / 3600` carries `$t` and the
      loop and no constant; an undeclared root still reads bare `$t`.
- [ ] 1.3 Red: `set_keyframe(2700)` on the declaring root binds `2700.0` on
      root and nested child and the child's mesh resolves; `clear_keyframe()`
      restores the `$t * loop` expression and the same serialized strings as a
      fresh render; `set_state(time=…)` equivalence holds.
- [ ] 1.4 Red: a child class declaring `Time` linked under an undeclared
      root fails when its `simulate()` reads `self.time`, naming the child
      and the root; the same class loaded as a root reads its own `$t * loop`.
- [ ] 1.5 Implement `Time` in `solid_node/node/timebase.py` (frozen
      dataclass + data descriptor: `__set_name__` name/owner checks,
      `__get__` class/instance split, `__set__` refusal, `loop`
      validation) and `declared_time(cls)`; export it from
      `solid_node.node`'s deferred export table.
- [ ] 1.6 Implement the shared reader in `solid_node/node/assembly.py`:
      note the phase read, bound entry first, else walk `_parent` to the
      root, refuse a declaration strictly below it, return
      `get_animation_time() * loop` or bare `get_animation_time()`. Point
      the `time` property and `Time.__get__` at it. Turn 1.1–1.4 green.
- [ ] 1.7 Run the kinematics, declarative-nodes, simulation and flexible-leaf
      suites (`tests/test_kinematics*.py`, `tests/test_declarative*.py`,
      `tests/test_simulation*.py`, `tests/test_flexible*.py`) to confirm the
      undeclared path and `Sim`'s seconds are untouched.

## 2. Published documents

- [ ] 2.1 Red: `export_node` of a declaring root writes
      `manifest['animation'] == {'fps': …, 'frames': …, 'loop': 43200.0}`
      with an unchanged `version`; of an undeclared root the `animation`
      object has no `loop` key and the manifest is byte-identical to the
      current one.
- [ ] 2.2 Red: the builder's `viewer.json` for a declaring root carries
      `animation.loop`; for an undeclared root it does not (extend the
      existing `_write_viewer_snapshot` tests).
- [ ] 2.3 Red: the browser snapshot's staged document carries
      `animation.loop` under the same rule.
- [ ] 2.4 Implement one helper (`animation_block(root, fps, frames)` beside
      the document helpers) that reads `declared_time(type(root))` and
      builds the object; use it in `solid_node/core/builder.py`,
      `solid_node/core/export.py` and `solid_node/viewers/browser.py`. Green.

## 3. Snapshot and tests

- [ ] 3.1 Red: `manager/snapshot.py`'s node preparation keyframes a
      declaring root at `time * loop` for `--time 0.5` and an undeclared
      root at `0.5`; the option's validation is unchanged.
- [ ] 3.2 Implement the conversion in `_load_and_prepare_node`. Green.
- [ ] 3.3 Red: a `TestCase` over a declaring root decorated
      `@testing_steps(4, end=1.5)` observes `time` at 0, 0.5, 1.0, 1.5
      seconds under the runner. Confirm the decorators need no code change;
      update their docstrings.

## 4. Originating project

- [ ] 4.1 Migrate `projects/3DPrintedClocks/design/wall_clock_01`:
      `time = Time(loop=spec.SECONDS_PER_TURN)` on `WallClock01`,
      `simulate()` assigns `self.time` directly, `test_clock.py` states
      `SWING`, `GREAT_WHEEL_TURN` and `HALF_A_DAY_ROUND` in seconds; fix
      the `design/README.md` sentence claiming one turn is one beat.
- [ ] 4.2 Run `solid test` and `solid build` for the clock from this
      worktree (`PYTHONPATH` = worktree, workspace venv); confirm the same
      verdicts as before and `animation.loop == 43200` in its `viewer.json`.
      Record the evidence here. The project edits stay in the project's own
      repository for the pilot to commit.

## 5. Records

- [ ] 5.1 `docs/animation.rst`: a "Declaring the time base" section
      (declaration, seconds everywhere, `$t * loop`, root-only, what the
      viewer does with it today); `docs/declaring.rst` cross-reference;
      `docs/api-reference.rst` documents `Time`; `docs/changelog.rst`
      Unreleased entry with the migration note.
- [ ] 5.2 ADR "Declared time base" in `docs/adrs/NODE/` extending ADR-008
      (mark 008 extended by it), indexed in `docs/adrs/README.md`;
      `docs/architecture.md` kinematics and export sections rewritten for
      the new state.
- [ ] 5.3 Full framework suite green; `openspec validate`; sync and archive
      the change.
