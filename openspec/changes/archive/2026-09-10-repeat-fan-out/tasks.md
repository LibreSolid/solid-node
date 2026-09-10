## 0. Before anything

- [x] 0.1 Work only in
  `solid-node/WTs/motion-catalogue-2` (branch `motion-catalogue-2`, base
  `5b28510`), with `PYTHONPATH="$PWD"` and the workspace venv
  `/home/asa/devel/libresolid-studio/.venv/bin/python`. Confirm
  `python -c "import solid_node; print(solid_node.__file__)"` prints the
  WORKTREE path before running anything: the venv's editable install
  points at the primary checkout.
- [x] 0.2 Record the FULL SUITE at the base:
  `.venv/bin/python -m pytest -x -q` from the worktree, exact counts,
  into `evidence.md`. Any failure here is pre-existing and must be shown
  to be so before task 5 begins.
- [x] 0.3 Re-run the four proposal probes and paste their current output
  into `evidence.md`: `evidence/probe_refusals_today.py` (the four
  refusals and the missing reader), `evidence/probe_wiring_repeat.py`
  (the identity wiring over a repeat already works),
  `evidence/probe_shadow.py` (a declared parameter silently hides an
  instance attribute of the same name), and
  `evidence/probe_list_held_today.py` (which list-held forms reach the
  framework's message and which raises a bare Python one). They are the
  reason four decisions in `design.md` read as they do; if any of them
  has changed, STOP and report rather than adapting the design.

## 1. Red first: the copy's index

Lands in `tests/test_declarative_nodes.py`, in a new section after the
repeat section. **Every case MUST be seen RED on the current tree before
task 5 begins, and the RED text recorded in `evidence.md`.** A case that
is red only with `AttributeError: index` is a weak red; for each of
those, also record the value the case reads today (the probe shows
`'<absent>'`) so the evidence says what was there before.

- [x] 1.1 **Fixtures.** `Bead`, a rigid leaf declaring one `Prismatic`
  and no `index`; `Column`, declaring `beads = Bead(...).repeat(4)` and
  one `SignalPort`; `Ranked`, a class declaring `index = Count(0)` of its
  own; `Halves`, reproducing the abacus's real shape —
  `halves = Half(count=count, ...).repeat(2)` where `Half` declares
  `count = Count(9, min=1)`.
- [x] 1.2 **A copy reads its position.** The four copies of `Column.beads`
  read `index` `0, 1, 2, 3` in order. RED.
- [x] 1.3 **The position is not identity.** The four share one `uniq_id`,
  and that `uniq_id` equals the one an un-repeated `Bead(...)` of the
  same arguments has; none of the four carries `index` in its resolved
  parameters. Assert the `uniq_id` string, not just equality between the
  four.
- [x] 1.4 **A zero repeat still carries nothing.** `.repeat(0)` realizes
  no copies and raises nothing.
- [x] 1.5 **A repeat of a class that declares `index` is refused**, at
  the PARENT's class definition, with a message naming the declaring
  class, the attribute, `Ranked` and the declaration found. RED. Record
  what happens today instead: the class defines, the copies realize, and
  `copy.index` reads the DECLARED value while `copy.__dict__['index']`
  holds the framework's — the silence `evidence/probe_shadow.py`
  measures. Also assert the OTHER side of the rule with InMoov's real
  shape: a PARENT declaring `index = Driver(...)` and
  `fingers = Finger().repeat(4)` is NOT refused, because the name is
  checked on the repeated class only.
- [x] 1.6 **`Halves` still realizes.** The abacus's real shape is NOT
  refused: `Half` declares `count`, not `index`, and both copies read
  `count` as the parent passed it and `index` as `0` and `1`. This case
  is what fixes the decision to stamp `index` and not `count`; if it goes
  red, the decision is wrong and the cycle stops.
- [x] 1.7 **A copy's `index` does not become a child name or a tree
  entry.** The parent's declared child names are still `beads-0`…
  `beads-3`, `declared_child_nodes` returns the four, and no traversal
  names a child `index`.

## 2. Red first: the broadcast end resolves

Lands in `tests/test_couplings.py`, in a new "Fan-out over a repeated
child" section after the path-reference section.

- [x] 2.1 **A repeated driven end is n relations.** `Column` states
  `earth.drives(beads.travel)`; binding `earth` in `simulate()` binds all
  four copies' `travel` and places all four bodies. Assert each copy's
  composed world matrix, not only the slot values. RED (today:
  `SidewaysReadError`, text in `evidence/probe_refusals_today.py`).
- [x] 2.2 **A repeated NODE end is the copies' one joint.**
  `earth.drives(beads)` gives the same four bindings. A repeated class
  declaring no joint, or two, is refused at class definition by the
  existing message, naming the class and its joints — confirm the
  existing message is reached and not a broadcast-specific one.
- [x] 2.3 **A repeat one level down.** A root states
  `drive.drives(column.beads.travel)`; the four copies of that realized
  column are bound and no other column's are. Use TWO columns so the
  per-instance rule is proved, not assumed.
- [x] 2.4 **A plain child under the copies.** `yaw.drives(legs.femur.lift)`
  where `legs` is repeated and `femur` is a plain child of `Leg`: one
  fan-out, six bindings.
- [x] 2.5 **Two repeats in one path are refused** at class definition,
  naming BOTH repeated segments. RED.
- [x] 2.6 **A list-held child is still refused**, with its own message
  (its children carry their own arguments and are named one by one), and
  the message is NOT the two-repeat one. Two forms reach it, measured in
  `evidence/probe_list_held_today.py`: `power.drives(plates)` and
  `power.drives(frame.plates.turn)`. A THIRD form does not reach the
  framework at all — `plates.turn` in the class body that declares the
  list is a plain `AttributeError: 'list' object has no attribute
  'turn'`, because a class-body list is a Python list and not a
  declaration object. Record that as it is; do NOT fix it here.
- [x] 2.7 **A repeated SOURCE is refused at class definition**, in all
  three spellings: `beads.travel.drives(earth)`, `beads.drives(earth)`
  (which must reach this refusal and not a path error — `drives` on the
  repeat itself), and `column.beads.travel.drives(earth)`. Each message
  names the path as written, the repeated declaration and its class.
- [x] 2.8 **A broadcast in a formula is refused**: `bad = beads.travel -
  earth` raises at class definition naming the formula and the path.
- [x] 2.9 **A path that stops on a repeat of a multi-coordinate joint**
  keeps the ADR-095 refusal: `beads.pose` over repeated `Bead`s
  declaring `pose = Free()` lists the six coordinates.

## 3. Red first: the law, the ratio, and the solve

Same section as task 2.

- [x] 3.1 **The law is called once per copy, with the copy.**
  `earth.drives(beads.travel, law=earth_lift)` where `earth_lift(driver,
  driven)` appends `(driver, driven, driven.index)` to a module list and
  returns a distinct `ForwardOnly` per copy. Assert: four calls, at
  REALIZATION (before any `simulate()`), each second argument the copy in
  index order, each first argument the node owning the driver; then
  simulate at three instants and assert the call count is still four and
  each copy carries its own law's result.
- [x] 3.2 **The law's signature is unchanged.** The same two-argument
  callable, used on an ordinary relation elsewhere in the same class,
  still runs once. No `inspect` of any kind is reachable from the
  framework's side — assert by using a callable whose signature is
  `(*args)`, which any signature-sniffing implementation would get wrong.
- [x] 3.3 **`ratio=`/`offset=` broadcast unchanged**, resolved once
  against the declaring instance: a `Count`/`Length` token as the ratio
  resolves from the parent's parameters, and all four copies get the same
  number. Assert with a token, not only a literal.
- [x] 3.4 **Declaration order, copy order.** A class declaring relation
  A, then a broadcast over four, then relation B: assert the order the
  four solved in is copy order and that the whole solve is
  order-independent (state the same three declarations in a different
  order in a second fixture and assert identical values).
- [x] 3.5 **A named broadcast reads as a tuple of records** off the
  instance, in copy order, each with its own `direction` of `'forward'`;
  a named ordinary relation still reads as one record. A broadcast over
  a zero-count repeat reads as an empty tuple.
- [x] 3.6 **A zero-count broadcast binds nothing and refuses nothing.**
  Simulate; the source keeps the value the author bound and no error is
  raised.
- [x] 3.7 **Omitted copies are still driven.** A `render()` that omits
  `beads-2`: the broadcast still resolves four records, all four are
  bound, the assembled tree has three children, and nothing is refused.
- [x] 3.8 **The second run re-solves.** Three successive instants: each
  run clears what the previous bound, every copy holds the current
  instant's value, and nothing is refused as doubly bound — the existing
  freshness rule, over n records.
- [x] 3.9 **Symbolic values pass through.** With nothing bound, each
  copy's operation carries the driver's expression (the SAME expression
  on every copy under `ratio=`; a per-copy one only where a per-copy
  law makes it so), and `set_keyframe` makes them numeric. Assert the
  published strings.

## 4. Red first: the refusals under a broadcast, and the reader

- [x] 4.1 **A broadcast is never inverted.** `earth` unbound, one copy's
  `travel` bound by the author's `simulate()`: `NotInvertible` naming the
  relation, the COPY, the bound coordinate, and saying a broadcast is
  read forward only. Use the DEFAULT identity law, which would invert
  perfectly well, so the case proves the rule and not the law.
- [x] 4.2 **A doubly bound copy names that copy.** The author binds
  `beads-2.travel` while `earth` is also bound: `DoublyBound` naming
  `beads-2` and the relation, and the other three copies are unaffected
  by the message's content (they are not bound either, because the raise
  stops the pass — assert the message, not the partial state).
- [x] 4.3 **A wired copy and a broadcast are two binders.**
  `Bead(travel=earth).repeat(4)` AND `earth.drives(beads.travel)` in one
  class: refused naming the wiring and the relation, per copy.
- [x] 4.4 **The wiring path still works alone**, exactly as
  `evidence/probe_wiring_repeat.py` measures, including the case the
  fixpoint decides: the wired source is itself solved by a relation of
  the same class in the same pass, and the wiring binds after it. This
  case is GREEN before the change; run it and record that it is, because
  it is the evidence for building no keyword.
- [x] 4.5 **`get_coordinate`** in `tests/test_ports.py`: every name
  `declared_ports` reports reads back as a slot, dotted names included;
  an unbound slot returns with `value is None`; a name the enumerator
  does not report — a declared PARAMETER's name, and a coordinate no
  joint owns — raises naming the node, the name and the reported names.
  RED (today: `ImportError`).
- [x] 4.6 **The pair is symmetric.** For every reported name,
  `set_coordinate(node, name, v)` then `get_coordinate(node, name).value`
  round-trips `v` (scale applied where a port declares one — assert the
  scaled value, not `v`, and say so in the test's name).

## 5. The implementation

Only after every case above has been seen red and recorded.

- [x] 5.1 `solid_node/node/declarative.py`:
  `RepeatDeclaration.__set_name__` refuses a repeated class that answers
  to `index`; `RepeatDeclaration.realize` stamps
  `child.__dict__['index']` after each copy is constructed;
  `RepeatDeclaration.__getattr__` returns a broadcast reference through
  `read_through` instead of raising; `RepeatDeclaration.drives`, so
  naming the repeat itself as a source reaches the source refusal.
- [x] 5.2 `solid_node/motion/couplings.py`: `BroadcastRef` beside
  `PathRef`, carrying the position of the repeated segment; `read_through`
  returns a `RepeatDeclaration` as a place and keeps refusing a
  list-held one with its own message; `PathRef.__getattr__` yields a
  `BroadcastRef` when it steps onto a repeat; `BroadcastRef.__getattr__`
  refuses a second; `BroadcastRef.check('driver')` and the arithmetic
  refusals; `coordinate_ref` maps a bare `RepeatDeclaration` to a
  `BroadcastRef`.
- [x] 5.3 `Relation.resolve` returns a LIST of records; the law callable
  is called once per record; `resolve_declared_relations` flattens;
  `Relation.__get__`/`record_of` yields a tuple for a broadcast and one
  record otherwise; `RelationRecord` carries and describes its copy.
- [x] 5.4 `_step_relation` never reads a broadcast record backwards, and
  `_refuse` raises `NotInvertible` with the broadcast reason. Do not add
  an error kind.
- [x] 5.5 `solid_node/motion/ports.py`: `get_coordinate`, checked against
  `declared_ports(type(node))` and refusing an unreported name.
- [x] 5.6 Keep every existing message that does not have to change. Where
  one does, the new text is asserted by a test in tasks 1-4 — a message
  changed with no test asserting it is a message nobody reads.

## 6. Nothing that is not rewritten moves

The proof, not an argument. Run ONE heavy process at a time: the VM
exhausts file descriptors under parallel CAD runs.

- [x] 6.1 Full framework suite from the worktree,
  `.venv/bin/python -m pytest -x -q`, exact counts, compared with the
  base counts from task 0.2. Any newly red test is a stop.
- [x] 6.2 **Pose comparison over every project that uses `.repeat()` with
  the motion layer.** Fourteen, surveyed for this proposal:
  `Vibecoded-demos/abacus`, `Vibecoded-demos/v8-engine`,
  `Actuators/OpenCycloid`, `Lab-Equipment/openflexure-microscope`,
  `Lab-Equipment/science-jubilee`, `Robotic-Arms/Thor`,
  `Robotic-Hands/Inmoov-sim`, `Robots/hexapod_spiderbot_model`,
  `3D-Printers/Metamaquina2`, `3D-Printers/Prusa3-vanilla`,
  `3D-Printers/fender-bender`, `3D-Printers/hangprinter`,
  `3D-Printers/kossel`, `3D-Printers/snappy-reprap`. For each, and for
  every model its manifest declares:
  `PYTHONPATH=.:<worktree> .venv/bin/python
  <shop>/docs/motion-general-refactor/capture_poses.py capture
  <module:Class> before.json` at the BASE tree, the same at the HEAD
  tree, then `compare before after`. **Maximum deviation must be 0**;
  anything else is a stop and a report, not a tolerance.
  Read-only: capture files go under
  `openspec/changes/repeat-fan-out/evidence/poses/`, never into a
  project repository, and no project file is edited.
- [x] 6.3 Note in `evidence.md` which of the fourteen are DEFERRED at
  stage A (abacus, v8-engine, OpenCycloid, fender-bender, kossel): their
  copies are bound in `simulate()` loops today, which is exactly the code
  a broadcast will replace at stage B, so their zero deviation now is the
  strongest of the fourteen.
- [x] 6.4 A pose comparison run over a project whose repeat is WIRED
  (`Lab-Equipment/openflexure-microscope` and the abacus both have some),
  so the "no keyword" decision is covered by measurement and not only by
  the probe.

## 7. Specs, decision record and docs

- [x] 7.1 Sync the three delta specs into `openspec/specs/` and archive
  the change, in the order the framework-change skill states.
- [x] 7.2 A new ADR under `docs/adrs/NODE/`: *A relation broadcasts over
  a repeated child*, extending ADR-089, depending on ADR-061/063/093,
  with the four rejected options `design.md` records (one broadcast
  object; a third law argument; a first-segment-only rule; a wiring
  keyword on `.repeat()`), and its row in `docs/adrs/README.md` in
  chronological order.
- [x] 7.3 `docs/architecture.md` §Couplings: the broadcast, in the
  reference voice.
- [x] 7.4 `docs/driving.rst`: a fan-out passage with the abacus's
  `for` loop beside the sentence that replaces it, and the source
  refusal stated.
- [x] 7.5 `docs/declaring.rst`: the paragraph "Per-unit variation never
  lives in the declaration. Placement variation is `enumerate` plus
  constants in `render()`; drive variation is port feeding" is now half
  wrong — drive variation is a broadcast relation with a per-copy law,
  or port feeding. Rewrite it, keep the GEOMETRY half exactly as it is,
  and add the copy's `index` where `repeat` is introduced with the
  artifact rule beside it.
- [x] 7.6 `docs/api-reference.rst`: `get_coordinate` beside
  `declared_ports`; `docs/changelog.rst` `Unreleased`.
- [x] 7.7 `tests/test_docs_exports.py` passes unchanged — confirm rather
  than assume.

## 8. The plan note and the findings

- [x] 8.1 `workflow/warts.md`: mark FIXED the fan-out finding in its four
  places (the OpenCycloid entry under "Motion catalogue refactor", the
  abacus entry, OpenFlexure's sighting (a), and fender-bender's third
  blocker), naming this change and the ADR. Mark FIXED the hexapod's
  dotted-reader finding. **Move InMoov's ten `connect()`s to cycle 5**
  with the reason: each of the four repeated fingers has its OWN driver,
  and a broadcast has one source.
- [x] 8.2 `workflow/docs/motion-catalogue-2.md` §3.1 was refined when
  this change was proposed; confirm it still matches what was built, and
  correct the finding table's cycle column for the InMoov sighting.
- [x] 8.3 Do NOT touch `libresolid-studio/docs/motion-general-refactor.md`
  or any project. OpenCycloid's and the abacus's stage B are their own
  cycles in their own repositories.

## 9. Evidence

- [x] 9.1 `evidence.md`: the base and head suite counts; the RED text of
  every case in tasks 1-4, weak reds separated from strong ones; the
  mechanism as implemented; every message that changed, old beside new;
  the fourteen pose comparisons with their deviations; what was
  deliberately not done.
- [x] 9.2 **Pixels.** `solid snapshot` on a small bench whose four
  repeated bodies are placed by ONE broadcast with a per-copy law, at
  three poses, so the fan-out is on the record as an image and not only
  as four numbers. Under `evidence/`.
- [x] 9.3 The three proposal probes re-run against the built tree, with
  their new output recorded beside the old.

## 10. Open questions to close or carry

- [x] 10.1 Carry: a `count` on the copy. Closed for now for want of a
  sighting AND because `count` is a name the catalogue already uses on a
  repeated class (`FrameHalf`). Record the name that would have to be
  chosen instead, and the survey that decides it.
- [x] 10.2 Carry: indexing a repeat in a class body (`beads[2].travel`),
  and a per-copy SOURCE. Both are real wants — the Pascaline's eight-way
  carry and InMoov's five motors — and neither is this cycle's.
- [x] 10.3 Close or carry: whether a copy should learn its index DURING
  its own construction, so a joint argument or a `check()` could read it.
  Not needed by any sighting; the legacy-constructor ordering that makes
  it hard is recorded in `design.md` §3.
- [x] 10.4 Close: the wiring keyword on `.repeat()`. Not built, with the
  probe as the reason. If the pilot wants the spelling anyway, that is a
  decision to take now rather than after the four later cycles are
  written against its absence.
