## 1. Red first: the tests that fail on the current tree

- [x] 1.1 Write `tests/test_motion_package.py`: `solid_node.motion.ports`
  exports `Port`, `BoundPort`, `RotationalPort`, `TranslationalPort`,
  `SignalPort`, `bind`, `declared_ports`, `Time`, `declared_time`, and
  each is the class the framework actually uses (a node declaring a port
  binds and reads through it).
- [x] 1.2 In the same file, assert `solid_node.motion.joints` and
  `solid_node.motion.couplings` import, each has a non-empty docstring,
  and neither exposes a public name (`[n for n in vars(m) if not
  n.startswith('_')] == []`).
- [x] 1.3 In the same file, assert `solid_node.motion` itself exports no
  port, time-base, joint or coupling name: reading `RotationalPort` off
  the package raises `AttributeError`.
- [x] 1.4 In the same file, assert the refusal: `from solid_node.node
  import RotationalPort` (and each of the other five names) raises
  `ImportError`, and the message contains `solid_node.motion.ports`;
  reading `solid_node.node.ports` and `solid_node.node.timebase` as
  attributes raises with the same message; `from solid_node.node import
  AssemblyNode` still works.
- [x] 1.5 In the same file, assert both import orders in fresh
  subprocess interpreters — `solid_node.motion.ports` first, and
  `solid_node.node.internal` first — each complete and each let a node
  class declare and bind a port.
- [x] 1.6 In the same file, assert import cost: a fresh interpreter that
  imports only `solid_node.motion`, `solid_node.motion.joints` and
  `solid_node.motion.couplings` has, in `sys.modules`, no `solid_node`
  module other than the top-level `solid_node` package itself (which the
  import machinery necessarily creates as their parent; its `__init__`
  is version metadata only) and the three motion modules, and no CAD
  backend; one that imports `solid_node.motion.ports` has no `cadquery`,
  no BRep kernel and no STEP reader.
- [x] 1.7 Repoint `tests/test_ports.py` (its `solid_node.node` import and
  its `solid_node.node.ports` import of `BoundPort`, `Port`,
  `declared_ports`) at `solid_node.motion.ports`.
- [x] 1.8 Repoint `tests/test_time_base.py` (`Time` from
  `solid_node.node`, `declared_time` from `solid_node.node.timebase`) at
  `solid_node.motion.ports`.
- [x] 1.9 Update `tests/test_node_lazy_exports.py`: drop the six
  port/time entries from its expected export table and add the assertion
  that each of those names, and the two removed submodule names, is
  refused with a message naming `solid_node.motion.ports`.
- [x] 1.10 Run the suite and record the failures: every test in 1.1–1.9
  must fail on the current tree, for the right reason (name absent from
  `solid_node.motion.ports`, not a typo).

## 2. The move

- [x] 2.1 Create `solid_node/motion/__init__.py`: SPDX header, a
  docstring naming the three submodules and the question each answers,
  no imports, no `__getattr__`, no names.
- [x] 2.2 Create `solid_node/motion/ports.py` by merging
  `solid_node/node/ports.py` and `solid_node/node/timebase.py` verbatim
  under one module docstring covering both subjects; change only the
  `note_read` import to `from solid_node.node.phase import note_read`
  and `Time`'s two function-local imports to
  `from solid_node.node.assembly import ...`. No logic edits.
- [x] 2.3 Create `solid_node/motion/joints.py`: SPDX header and a
  docstring saying it will hold `Revolute` and `Prismatic` — a pair that
  places a body, declared on the node it moves, owning one coordinate —
  and that cycle 2 of `workflow/motion/roadmap.md` fills it. No names.
- [x] 2.4 Create `solid_node/motion/couplings.py`: SPDX header and a
  docstring saying it will hold `Affine` — a law between two coordinates,
  the value side of `a.drives(b)` — and that cycle 3 fills it. No names.
- [x] 2.5 Delete `solid_node/node/ports.py` and
  `solid_node/node/timebase.py`.
- [x] 2.6 Confirm the new package ships: check `pyproject.toml` /
  `setup.cfg` package discovery includes `solid_node.motion` (add it if
  packages are listed explicitly rather than found).

## 3. The node package stops exporting them

- [x] 3.1 Remove `Port`, `RotationalPort`, `TranslationalPort`,
  `SignalPort`, `declared_ports` and `Time` from `_EXPORTS` in
  `solid_node/node/__init__.py`.
- [x] 3.2 Add the `_MOVED` table (the six names plus `ports` and
  `timebase`, each mapping to `solid_node.motion.ports`) and consult it
  in `__getattr__` before `_submodule`, raising `AttributeError` with
  the message shape from design.md decision 4: the name, the new module,
  the replacement import line, and the one-sentence module rule.
- [x] 3.3 Update the module docstring of `solid_node/node/__init__.py`:
  the paragraph that explains why build parameters are deliberately not
  here gains the same statement for ports and the time base, so the next
  reader does not re-add them.

## 4. Internal consumers

- [x] 4.1 `solid_node/node/internal.py`: `from solid_node.motion.ports
  import bind`. `connect()` is unchanged.
- [x] 4.2 `solid_node/node/assembly.py`: `from solid_node.motion.ports
  import declared_time`.
- [x] 4.3 `solid_node/node/flexible.py`: `from solid_node.motion.ports
  import declared_ports` (four call sites unchanged).
- [x] 4.4 `solid_node/core/serializer.py` and
  `solid_node/manager/snapshot.py`: `from solid_node.motion.ports import
  declared_time`.
- [x] 4.5 `solid_node/parameters.py`: the docstring sentence naming
  `solid_node.node.ports` now names `solid_node.motion.ports`.
- [x] 4.6 `solid_node/simulation/driver.py`: the two comments referring
  to `declared_ports` still read correctly; adjust only if they name a
  module path.
- [x] 4.7 `tests/meta_project/machine.py` and
  `tests/test_simulate_split.py`: split their `solid_node.node` import
  lines so port kinds come from `solid_node.motion.ports`.
- [x] 4.8 `spike/expressions/machine_model.py` and
  `spike/axis/axis_model.py`: same split, so the spikes still import.
- [x] 4.9 `grep -rn "node import.*\(Port\|Time\)\|node\.ports\|node\.timebase"
  --include=*.py .` returns nothing outside
  `openspec/changes/archive` and `docs/adrs` (history stays as written).
- [x] 4.10 Run the full suite green:
  `PYTHONPATH=$PWD /home/asa/devel/libresolid-studio/.venv/bin/python -m
  pytest tests -x -q`, from the worktree root.

## 5. Documentation

- [x] 5.1 `docs/animation.rst` (`AssemblyNode, Time`),
  `docs/driving.rst` (`TranslationalPort`), `docs/leaf-nodes.rst`
  (`MolejoNode, TranslationalPort`): split each example import line so
  ports and `Time` come from `solid_node.motion.ports`, and add the
  one-line statement of which module answers for what where the page
  first introduces a port.
- [x] 5.2 `docs/api-reference.rst`: repoint every autodoc target that
  names a moved symbol. In the "Ports" section (from ~line 227): the
  prose "importable from ``solid_node.node``" becomes
  ``solid_node.motion.ports``, and `.. autoclass:: solid_node.node.Port`,
  `.. autoclass:: solid_node.node.RotationalPort`,
  `.. autoclass:: solid_node.node.TranslationalPort`,
  `.. autoclass:: solid_node.node.SignalPort` and
  `.. autofunction:: solid_node.node.declared_ports` each take the
  `solid_node.motion.ports.` prefix. In the assemblies/animation section
  (~line 183): `.. autoclass:: solid_node.node.Time` becomes
  `.. autoclass:: solid_node.motion.ports.Time`. The
  `:meth:`~solid_node.node.internal.InternalNode.connect`` cross-reference
  in the Ports prose is unchanged, because `connect` did not move.
- [x] 5.3 `grep -n "solid_node.node.\(Port\|Rotational\|Translational\|Signal\|declared_ports\|Time\)" docs/*.rst`
  returns nothing.
- [x] 5.4 `docs/declaring.rst` (or whichever page the
  `user-documentation` spec's declarative-authoring requirement points
  at): state that ports and the declared time base come from the motion
  package, beside the existing sentence about parameters, node classes
  and drivers.
- [x] 5.5 `docs/changelog.rst`: an "Unreleased" entry named for the
  break — ports and the time base moved to `solid_node.motion.ports`,
  `solid_node.node` no longer exports them, there is no shim, and the
  migration is `from solid_node.node import RotationalPort, SignalPort,
  Time` → `from solid_node.motion.ports import RotationalPort,
  SignalPort, Time`. Name the OpenSpec change and ADR-087.
- [x] 5.6 Docs evidence. The workspace venv has no `sphinx-build`
  (`/home/asa/devel/libresolid-studio/.venv/bin/sphinx-build` does not
  exist), so run the docs build only if the venv the cycle runs in
  actually provides sphinx. Otherwise the evidence is the 5.3 grep
  returning nothing plus a `python -c` import check that every autodoc
  target still resolves — `solid_node.motion.ports.Port`,
  `.RotationalPort`, `.TranslationalPort`, `.SignalPort`,
  `.declared_ports`, `.Time`, and
  `solid_node.node.internal.InternalNode.connect` — so a stale autodoc
  path cannot pass unnoticed. Say in the implementation notes which of
  the two was used and why.

## 6. Records

- [x] 6.1 Write `docs/adrs/NODE/ADR-087-one-module-one-question.md`
  after the implementation is green: the module rule, ports and the time
  base placed under it, the deliberate break with no shim and why
  (migration visibility), the redirect message as the only concession,
  and the two facts the design note got wrong (`connect` is an
  `InternalNode` method, not an import; `BoundPort` and `declared_time`
  move too). Status Accepted; amends ADR-056 and ADR-072 **on export
  location only**.
- [x] 6.2 `docs/adrs/README.md`: add the ADR-087 row in the NODE table
  in number order, with its amends note; update the ADR-056 and ADR-072
  rows' amended-by fields.
- [x] 6.3 `docs/architecture.md`: the Node model section's authoring
  paragraph and the Kinematics section's **Ports** paragraph name
  `solid_node/motion/ports.py`; the Simulation section's contrast
  between `Driver` and ports stays true at the new path; add the module
  rule (one module, one question) as a short paragraph where the package
  layout is described, and add a `Motion` row to the Map table
  (`solid_node/motion/`, spec `ports`, ADRs 056, 072, 087) with the
  Kinematics row's code list corrected.
- [x] 6.4 `openspec validate --change motion-package` passes, and the
  four delta specs still match the baseline requirement text they
  modify.

## 7. Project evidence

- [x] 7.1 In `/home/asa/devel/libresolid-studio/projects/3DPrintedClocks`,
  repoint the port and `Time` imports in `simulation/shared/assemblies.py`
  and in `simulation/wall_clock_48/clock.py`,
  `wall_clock_50/clock.py`, `wall_clock_52/clock.py`,
  `wall_clock_54/clock.py` at `solid_node.motion.ports`.
- [x] 7.2 Run that project's `simulation/shared` and
  `simulation/wall_clock_01` suites against this worktree, with
  `PYTHONPATH` naming the worktree ahead of any installed solid-node and
  the workspace venv's interpreter; record the command and the result in
  the cycle's implementation notes.
- [x] 7.3 Confirm the project's own repository is left with only those
  import edits and that **nothing in it is staged or committed from this
  cycle**; `git -C <worktree> status` shows no project path.

## 8. Roadmap

- [x] 8.1 `workflow/motion/roadmap.md`, Progress table, row
  `1 motion-package`: the "Proposed" cell already reads
  `2026-09-09 · motion-package` from the planning commit; fill "Applied"
  with the date and the implementation commit.
- [x] 8.2 In the same file's project table, fill 3DPrintedClocks' "Paths"
  cell only if the project's edits are committed in its own repository;
  otherwise leave it empty and note in the cycle record that the
  migration was run as evidence, not landed.
