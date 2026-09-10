# Evidence: `repeat-fan-out`

Worktree `solid-node/WTs/motion-catalogue-2`, branch `motion-catalogue-2`,
base `5b28510`. `PYTHONPATH="$PWD"` and
`/home/asa/devel/libresolid-studio/.venv/bin/python` throughout.

## 0. Baseline

`python -c "import solid_node; print(solid_node.__file__)"` printed the
WORKTREE path before anything ran.

**Full suite at the base** (task 0.2), `.venv/bin/python -m pytest -x -q`:

    2066 passed, 16 skipped, 49 warnings, 683 subtests passed in 289.60s

**Full suite after the implementation** (task 6.1), same command:

    2105 passed, 16 skipped, 49 warnings, 725 subtests passed in 292.52s

Delta: **+39 passed** (exactly the new test methods: 7 in
`RepeatIndexTest`, 6 in `CoordinateReaderTest`, 26 in `FanOutTest`) and
**+42 subtests**; 16 skipped both times; zero failures, zero errors, no
pre-existing test's count changed. Nothing else moved.

**The four proposal probes, re-run against the current (pre-implementation)
tree** — task 0.3, exact output:

    1. driven broadcast  earth.drives(beads.travel): SidewaysReadError: cannot read 'travel' through beads.travel: 'beads' is a repeated declaration, so it names Bead many times and the path names many coordinates. State the relation inside Bead instead, where it applies per instance.

    2. node end          earth.drives(beads): TypeError: a repeated declaration names many coordinates, and a relation has one driven end. State the relation inside the repeated class instead.

    3. source broadcast  beads.travel.drives(earth): SidewaysReadError: cannot read 'travel' through beads.travel: 'beads' is a repeated declaration, so it names Bead many times and the path names many coordinates. State the relation inside Bead instead, where it applies per instance.

    4. path into repeat  drive.drives(column.beads.travel): TypeError: 'column.beads' reaches a repeated declaration: 'beads' of Column names many coordinates, and a relation has one end. State the relation inside the repeated class instead.

    5. get_coordinate import: ImportError: cannot import name 'get_coordinate' from 'solid_node.motion.ports' (.../solid_node/motion/ports.py)

       index on copy: ['<absent>', '<absent>', '<absent>', '<absent>']
       count on copy: ['<absent>', '<absent>', '<absent>', '<absent>']
    6. copy index/count: NO ERROR

    probe_wiring_repeat.py:
    beads: ['beads-0', 'beads-1', 'beads-2', 'beads-3']
    travels: [3.0, 3.0, 3.0, 3.0]
    uniq: {'Bead-aa06a2f044b4'}
    ops: [1, 1, 1, 1]

    probe_shadow.py:
    declared index reads: 0  dict says: 3
    declared count reads: 9  dict says: 2
    assignment: AttributeError parameter 'index' of Half cannot be assigned: ...

    probe_list_held_today.py:
    A. plates.travel in the same body: AttributeError: 'list' object has no attribute 'travel'
    B. drives(plates): TypeError: a repeated declaration names many coordinates, and a relation has one driven end. State the relation inside the repeated class instead.
    C. frame.plates.travel: TypeError: 'frame.plates' reaches a repeated declaration: 'plates' of Frame names many coordinates, and a relation has one end. State the relation inside the repeated class instead.

Identical to what `proposal.md` and `design.md` cite: no probe had
changed. This is the reason the four decisions in `design.md` read as
they do, and none of them needed adapting.

## 1. Red first (tasks 1-4)

Every new test was run and seen fail BEFORE the source change, for the
reason the task names.

### 1.1 The copy's index (`tests/test_declarative_nodes.py::RepeatIndexTest`)

4 of 7 cases red, 3 green (the zero-repeat, the uniq_id/identity case,
and the child-naming case do not depend on `index` at all and were
already correct):

    FAILED test_a_copy_reads_its_position — AttributeError: 'Bead' object has no attribute 'index'
    FAILED test_a_parent_declaring_index_is_not_refused — AttributeError: 'Bead' object has no attribute 'index'
    FAILED test_a_repeat_of_a_class_that_declares_index_is_refused — AssertionError: TypeError not raised
    FAILED test_halves_still_realizes — AttributeError: 'Half' object has no attribute 'index'
    4 failed, 3 passed, 8 subtests passed

Every failure here is what the task calls a WEAK red (`AttributeError:
index`, not a wrong value): the probe's own output above
(`'<absent>', '<absent>', '<absent>', '<absent>'`) is the value that was
there before, recorded per task 1's instruction.

### 1.2-1.4 The broadcast end, the law/ratio/solve, the refusals under a
broadcast (`tests/test_couplings.py`, new "Fan-out over a repeated
child" section — 26 new methods in `FanOutTest`, plus one rewritten
existing method)

    26 failed, 4 passed in 2.54s (FanOutTest alone: 25 failed, 4 passed)

The 4 that passed before any source change, and why:

- `test_a_list_in_the_same_body_is_a_bare_python_error` — pre-existing,
  unrelated to this cycle (a class-body list is a plain Python list; see
  §5 below).
- `test_the_wiring_path_still_works_alone` — task 4.4's own instruction:
  this case MUST be green before the change, as the evidence for
  building no `.repeat()` keyword.
- `test_a_wired_source_solved_by_a_relation_binds_in_the_same_pass` — a
  supporting characterisation of the pre-existing wiring/relation
  fixpoint, untouched by this cycle.
- `test_a_repeated_source_is_refused_three_ways` — the OUTER test method
  passed (unittest's `subTest` swallows the exception it catches), but
  all three subtests were SUBFAILED, e.g.:

      SUBFAILED(form='travel_form') ... : SidewaysReadError raised where TypeError was expected

  (today `beads.travel` itself already raises before `.drives()` is
  reached, with the wrong exception TYPE — genuine red, reported by a
  different mechanism than a bare FAILED line).

The renamed pre-existing test,
`RelationEndTest::test_a_repeated_child_named_as_the_source_is_refused`
(was `test_a_path_through_a_repeated_child_is_refused`, which tested the
DRIVEN case the delta spec's own scenario retargets to the SOURCE case):
red today with `SidewaysReadError` where the new test expects `TypeError`
— confirming the exception TYPE, not only the message, changes here.

Sample RED text (representative, the rest in the pytest log run at
`tests/test_couplings.py::FanOutTest`):

    test_a_repeated_driven_end_is_n_relations:
      SidewaysReadError: cannot read 'travel' through beads.travel: 'beads' is a repeated declaration ...
    test_a_repeated_node_with_no_joint_reaches_the_existing_message:
      AssertionError: 'Link' not found in 'a repeated declaration names many coordinates, and a relation has one driven end. ...'
    test_a_ratio_broadcasts_the_same_resolved_number:
      SidewaysReadError (same as above, through beads.travel)
    test_two_repeated_segments_are_refused:
      SidewaysReadError: cannot read 'joints' through legs.joints: 'legs' is a repeated declaration ...

### 1.5 `get_coordinate` (`tests/test_ports.py::CoordinateReaderTest`)

The whole MODULE failed to collect:

    ImportError: cannot import name 'get_coordinate' from 'solid_node.motion.ports'

— exactly the RED task 4.5 names ("today: `ImportError`").

## 2. The implementation, as built (task 5)

- `solid_node/node/declarative.py`:
  - `RepeatDeclaration.__set_name__` → `_adopt` → `_check_index`: refuses
    a repeat of a class that already answers to `index`
    (`getattr(node_class, 'index', None) is not None`), naming the
    declaring class, the attribute, the repeated class and the found
    declaration.
  - `RepeatDeclaration.realize`: stamps `child.__dict__['index'] = i`
    AFTER `self.declaration.realize(...)` returns (after construction).
  - `RepeatDeclaration.__getattr__`: calls `read_through` and, when it
    finds a `RepeatDeclaration` (a second repeat), refuses by name via
    `_refuse_two_repeats`; otherwise returns a `BroadcastRef`.
  - `RepeatDeclaration.drives`: added, mirroring `ChildDeclaration.drives`,
    so `beads.drives(x)` reaches the source refusal through `relate`
    rather than a nonsense path error.
  - `ChildDeclaration.__getattr__`: the SAME repeat-detection added (a
    plain child one level up from a repeat, `column.beads`, goes through
    here first).
- `solid_node/motion/couplings.py`:
  - `BroadcastRef(PathRef)`: same `(root, segments, terminal)` shape,
    plus `repeat` (the `RepeatDeclaration` object, for the messages).
    `check('driver')` refuses the source; `terms()` refuses a formula
    term; `__getattr__` keeps walking and refuses a SECOND repeat;
    `resolve_all(instance)` walks the tree EXPANDING at the repeated
    segment (`_walk_copies`) instead of raising on a list, returning a
    `ResolvedEnd` per realized copy.
  - `PathRef.__getattr__`: yields a `BroadcastRef` when `read_through`
    returns a `RepeatDeclaration`.
  - `read_through`: returns a bare `RepeatDeclaration` as a PLACE
    (previously raised); a LIST-HELD declaration keeps its own refusal,
    reworded to name the list and say "one by one" rather than reusing
    the old "repeated declaration" text.
  - `coordinate_ref`: a bare `RepeatDeclaration` becomes a `BroadcastRef`
    standing for the repeat's one joint (source or driven; `check()`
    decides); a bare list-held declaration keeps its own refusal, naming
    it via `_named_in_body`.
  - `Relation.resolve`: returns a LIST — one record for an ordinary
    relation, one per copy (`self.driven.resolve_all(instance)`) for a
    broadcast; the `ratio=`/`offset=`-derived `Affine` is built ONCE and
    shared by every copy's record; `law=` is called once per copy, with
    that copy as the second argument.
  - `resolve_declared_relations`: flattens every relation's list into one
    flat `_relations` list, in declaration order (copy order falls out
    of `resolve_all`'s own list order, with no separate sort).
  - `Relation.record_of`: returns a tuple when `self.driven` is a
    `BroadcastRef` (even an empty one), one record otherwise — the
    SHAPE, not the runtime count, decides.
  - `RelationRecord`: carries `copy` (`None` for an ordinary relation);
    `described()` appends `, copy <name>` when set.
  - `_step_relation`: never attempts the backward (driven-bound) branch
    when `record.relation.driven` is a `BroadcastRef`.
  - `_refuse`: for that same case, raises `NotInvertible` with the
    broadcast-specific text ("a broadcast is read forward only ...")
    instead of the generic "law offers no inverse" text.
- `solid_node/motion/ports.py`: `get_coordinate(node, name)`, checked
  against `declared_ports(type(node))` (refuses by name, `AttributeError`,
  otherwise) and reading through the same head/tail walk `set_coordinate`
  writes through.

**The seam in one sentence:** a path is a broadcast the moment it steps
onto a `RepeatDeclaration` (checked in four places that all reach the
same `BroadcastRef`: `ChildDeclaration.__getattr__`,
`RepeatDeclaration.__getattr__`, `PathRef.__getattr__` and
`coordinate_ref`'s bare-value case); `BroadcastRef` behaves exactly like
`PathRef` for class-definition-time validation and differs only in
`check('driver')` (refuses), `terms()` (refuses) and `resolve_all`
(returns n `ResolvedEnd`s instead of one) — the resolution rule is "a
`BroadcastRef` resolves to n records, one per realized copy, in copy
order, at the position of its declaration."

## 3. Fixes made while turning the tests green

Two implementation gaps were found only by running the RED tests and
are recorded here rather than silently folded into "the implementation":

- `ChildDeclaration.__getattr__` (declarative.py) needed the SAME
  repeat-detection as `PathRef.__getattr__` — a plain child one level
  above a repeat (`column.beads.travel`) goes through
  `ChildDeclaration.__getattr__` FIRST, and it was still unconditionally
  wrapping the result in a `PathRef`.
- The list-held source message in `coordinate_ref` needed the
  declaration's OWN name (`_named_in_body`), not a generic sentence,
  to satisfy "naming the list" the way the couplings spec requires.

Two of my own draft TESTS were also corrected, both because the FIRST
draft measured the wrong thing rather than because the implementation
was wrong:

- `test_a_broadcast_is_never_inverted` used a 4-copy repeat; with `earth`
  unbound, the OTHER three copies (whose both ends are unbound) reach
  `_refuse`'s `UnreachedCoordinate` branch before the solver gets to the
  one bound copy, in iteration order. Reduced to `repeat(1)` so the case
  proves the broadcast rule and not an ordering accident.
- `test_symbolic_values_pass_through_a_broadcast` first tried to read an
  UNBOUND `Driver`'s value directly (`.value` on a plain attribute
  access), which the driver descriptor refuses outright
  (`AttributeError: driver 'angle' ... is not bound`) — that is not what
  the claim in `design.md` decision 5 asks for anyway. Rewritten to
  check `id(record.law)` identity across the n records instead, which is
  the literal claim ("the SAME affine law ... shared by the n records").

## 4. Full suite counts

See §0: 2066 → 2105 passed (+39, exactly the new tests), 16 skipped both
times, no failures, no errors, no pre-existing count changed.

## 5. Pose comparison over every `.repeat()` project (task 6.2-6.4)

Base tree: the PRIMARY checkout `solid-node/` at `5b28510` (unmodified,
read-only, on `PYTHONPATH`). Head tree: this worktree. Script:
`docs/motion-general-refactor/capture_poses.py`, run from each project's
own root, `PYTHONPATH=.:<tree>`. Captures under
`openspec/changes/repeat-fan-out/evidence/poses/<project>/`
(`before.json`, `after.json`, `compare.txt`), never inside a project.

| Project | Reference | Poses | Leaves | Max deviation |
|---|---|---|---|---|
| abacus | `abacus.abacus:Abacus` | 11 | 56 | **0.000e+00** |
| v8-engine | `v8_engine.v8_engine:Engine` | 4 | 135 | **0.000e+00** |
| OpenCycloid | `simulation.actuator:OpenCycloid` | 7 | 46 | **0.000e+00** |
| openflexure-microscope | `simulation.microscope.microscope:Microscope` | 11 | 113 | **0.000e+00** |
| science-jubilee | `simulation.jubilee:Jubilee` | 11 | 35 | **0.000e+00** |
| Thor | `simulation.thor:Thor` | 19 | 441 | **0.000e+00** |
| Inmoov-sim | `Inmoov_sim.forearm:Forearm` | 17 | 61 | **0.000e+00** |
| hexapod_spiderbot_model | `simulation.spiderbot:Spiderbot` | 21 | 172 | **0.000e+00** |
| Metamaquina2 | `metamaquina2.metamaquina2:Metamaquina2` | 11 | 452 | **0.000e+00** |
| Prusa3-vanilla | `simulation.prusa_i3:PrusaI3` | 13 | 216 | **0.000e+00** |
| fender-bender | `simulation.fender_bender:FenderBender` | 13 | 45 | **0.000e+00** |
| hangprinter | `simulation.hangprinter:Hangprinter` | 11 | 149 | **0.000e+00** |
| kossel | `simulation.kossel:Kossel` | 11 | 378 | **0.000e+00** |
| snappy-reprap | `simulation.snappy_reprap:SnappyReprap` | 11 | 170 | **0.000e+00** |

**Fourteen for fourteen, maximum deviation zero, 181 poses, 2 469 leaf
world matrices (plus every reported port) compared.** No capture
failed, no pose went missing, no leaf stopped or started being a leaf.
Framework commit each ran against: the PRIMARY checkout `solid-node/`
at `5b28510` (before) and this worktree at the head content commit
recorded when this change is reviewed (after) — both unmodified by
this run; no project file was read from anywhere but each project's own
repository, and none was written to.

**Deferred-at-stage-A projects, and why their zero is the strongest of
the fourteen** (task 6.3): abacus, v8-engine, OpenCycloid, fender-bender
and kossel bind their `.repeat()` copies in hand-written `simulate()`
loops today — exactly the code this cycle's broadcast is built to
replace at stage B. None of the five states a broadcast relation yet, so
their zero deviation is not "nothing changed here" but "the primitive
that will let stage B happen is present and moves nothing on its own."

**Wired-repeat coverage (task 6.4):** `openflexure-microscope` (stage
nuts, gear-lock screws) and `abacus` (`Frame.halves`) both wire a
repeated child from a coordinate their own class declares. Both are in
the table above at zero deviation, so the "no wiring keyword on
`.repeat()`" decision (design.md Decision 9) is covered by measurement,
not only by `evidence/probe_wiring_repeat.py`.

## 6. Pixels (task 9.2)

`openspec/changes/repeat-fan-out/evidence/snapshot_bench.py:Column` —
four `Bead` leaves in a row (the parent's own `render()` loop over the
realized copies, `bead.translate([index * 12.0, 0, 0])`), lifted by ONE
broadcast relation (`earth.drives(beads.travel, law=stagger)`) whose
per-copy law reads `bead.index`:

    def stagger(column, bead):
        rank = bead.index
        return lambda level: level + rank * 3.0

`solid snapshot` at three poses (`--time 0.0/0.5/1.0`, `simulate()`
setting `self.earth = self.time * 10.0`), front orthographic
(`--projection ortho --camera 18,0,15,90,0,0,120`, so X is horizontal, Z
vertical, no perspective foreshortening) — PNGs under
`evidence/snapshots/front_t0.0.png`, `front_t0.5.png`, `front_t1.0.png`.

All three show the same 3 mm-per-copy staircase the law states (heights
0/3/6/9, 5/8/11/14, 10/13/16/19 mm respectively — verified directly
against the generated `.scad`, which carries two translations per body,
the joint's Z from the broadcast and the hand-written X from `render()`)
rising together as `earth` increases with time, four bodies from ONE
relation statement. (The default isometric `--autocenter --viewall`
view was tried first and rendered the three poses visually
indistinguishable — not a bug: a per-copy law adds a CONSTANT step
`rank * 3.0` to whatever `earth` is, so the group's shape is unchanged
between poses and only its baseline shifts, which autocentering hides.
The front view fixes the camera instead of re-fitting it, so the
baseline shift is visible too.)

## 6b. The three proposal probes, re-run against the built tree (task 9.3)

`probe_refusals_today.py`, new output (old beside it in §0 above):

    1. driven broadcast  earth.drives(beads.travel): NO ERROR
    2. node end          earth.drives(beads): NO ERROR
    3. source broadcast  beads.travel.drives(earth): TypeError: 'beads.travel' passes through the repeated declaration 'beads' of Bead (count=4), so it cannot be the SOURCE of a relation: a relation's source is one value, and the copies hold one each. Bind the source from a coordinate the parent holds, or state the relation inside Bead.
    4. path into repeat  drive.drives(column.beads.travel): NO ERROR
    5. get_coordinate import: NO ERROR
       index on copy: [0, 1, 2, 3]
       count on copy: ['<absent>', '<absent>', '<absent>', '<absent>']
    6. copy index/count: NO ERROR

Three of the four sentences the proposal wanted now work outright; the
fourth (source) is refused with a message naming the path, the repeated
declaration, its class and its count, as ADR-096 promises.
`probe_shadow.py` is not re-run here: nothing in this cycle changes what
it measures (a declared parameter still shadows an instance attribute of
the same name), which is exactly why the copy carries `index` and not
`count`.

`probe_wiring_repeat.py`: byte-identical output before and after —
GREEN on both trees, the evidence for building no `.repeat()` keyword
(task 4.4).

`probe_list_held_today.py`, new output for B and C (A is pre-existing
and untouched, by design):

    A. plates.travel in the same body: AttributeError: 'list' object has no attribute 'travel'
    B. drives(plates): TypeError: 'plates' holds 2 children, each with its own arguments -- named 'plates-0', 'plates-1', and so on, one by one -- so it cannot be the driven end of a relation naming all of them at once. Name one child by its own attribute.
    C. frame.plates.travel: TypeError: 'frame.plates' reaches a list-held child: Frame.plates holds 2 children, each with its own arguments -- named 'plates-0', 'plates-1', and so on -- and a relation names ONE of them, not the list. They are named one by one; a relation cannot reach all of them through this path.

B and C keep being refused, now with the list's OWN name and "one by
one" rather than the old "reaches a repeated declaration" text, which
would have been actively wrong once a REAL repeat no longer means that.

## 7. What was deliberately not done

- No `count` on the copy (design.md Decision 3, ADR-096 Consequences):
  the abacus's own `FrameHalf(count=...)` shape rules the name out, and
  no sighting's law needs it.
- No wiring keyword on `.repeat()` (design.md Decision 9): measured to
  already work for the identity case; the path case is exactly this
  cycle's broadcast.
- Indexing a repeat in a class body (`beads[2].travel`) and a per-copy
  SOURCE: real wants, neither this cycle's (design.md Non-Goals).
- The bare `AttributeError: 'list' object has no attribute '...'` for a
  list-held child read in its OWN class body: pre-existing, measured,
  recorded as-is (design.md Open Question 3).
- A `count` beside `index`: recorded, not decided (ADR-096, open
  question carried to task 10).

## 8. Open questions (task 10)

1. **Carried: a `count` on the copy.** Closed for now for want of a
   sighting and because `count` is a name the catalogue already uses on
   a repeated class (`FrameHalf`, measured, `evidence/probe_shadow.py`).
   If a law ever needs the total, the name would have to be chosen
   against the same survey; `repeat_count` is the obvious, ugly,
   candidate. Recorded in ADR-096 Consequences and design.md Open
   Question 1, not decided here.
2. **Carried: indexing a repeat in a class body (`beads[2].travel`), and
   a per-copy SOURCE.** Both real wants (the Pascaline's eight-way carry;
   InMoov's five motors), neither this cycle's. InMoov's ten
   `connect()`s are now explicitly moved to a future tuple-source cycle
   in `workflow/warts.md` and `workflow/docs/motion-catalogue-2.md` §1's
   finding table (cycle column corrected to "1+5").
3. **Closed for this cycle: whether a copy should learn its `index`
   DURING its own construction.** Not needed by any sighting (every
   broadcast law is declared on the PARENT and read after the copy's
   OWN construction has finished); the legacy-constructor ordering that
   makes it hard is recorded in `design.md` §3 and ADR-096. Left as
   `RepeatDeclaration.realize` stamping `child.__dict__['index']` AFTER
   `self.declaration.realize(...)` returns.
4. **Closed: the wiring keyword on `.repeat()`.** Not built. The
   evidence is `evidence/probe_wiring_repeat.py` (§6b above,
   byte-identical before and after): the identity case already works
   through the existing per-instance wiring mechanism, and the case a
   wiring cannot state — a PATH source — is exactly this cycle's
   broadcast. If the pilot wants the spelling anyway, that is a decision
   to take now, before the four cycles `workflow/docs/motion-catalogue-2.md`
   still lists are written against its absence.

## Review note (orchestrator, 2026-09-10)

The `before.json`/`after.json` captures under `evidence/poses/` (23 MB
over the fourteen projects) were deleted before the completion commit;
each project's `compare.txt` (the comparison's own output, maximum
deviation per pose) and the capture logs are kept. The captures are
reproducible from the base commit and the head with the command recorded
above.
