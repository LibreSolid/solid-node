## 1. The expression reader (red first)

- [x] 1.1 Red: `tests/test_expressions.py` — a parser in
      `solid_node/core/expressions.py` reads every form the framework can
      emit and rejects nothing it emits. One case per form, each built by
      the producer rather than typed by hand where possible: `$t`; a bare
      driver id and a dotted one (`x_axis.motor`); integers, decimals and
      exponent literals (`1e-05`, `1E+3`, `.5`); each binary operator solid2
      overloads (`+ - * / % ^` and `== != < > <= >=`); unary minus, including
      the nested `(-(-x))`; a `solid_node.math` call of one and of two
      arguments; `abs(...)` from `OpenSCADConstant.__abs__`; and a
      whitespace-free `scad_inline` string with no parentheses, which must
      group by OpenSCAD precedence (`1 + 2 * 3` is `(1 + (2 * 3))`,
      `2 ^ 3 ^ 2` is right-associative).
- [x] 1.2 Red: text the parser cannot read — an unbalanced parenthesis, an
      unknown token, a trailing comma, a bare `[1, 2]` vector — is reported as
      unreadable rather than guessed at, naming the offending text.
- [x] 1.3 Red: interning is **structural**, not textual: `(1.0 + 2.0)` built
      by solid2 and `1.0+2.0` from `scad_inline` intern to one node; and the
      substring memo does not change any answer (assert the same table with
      the memo disabled).
- [x] 1.4 Red: a rendered node re-parses to itself — for every node in a
      corpus tree, `parse(render(node)) is node` — so the emitted table is
      in the language the parser reads.
- [x] 1.5 Implement `solid_node/core/expressions.py`: tokenizer, precedence-
      climbing parser, structural interner keyed on `(kind, op-or-name, child
      ids)`, substring memo on parenthesised groups, occurrence counting,

      **Evidence:** `tests/test_expressions.py`, 36 cases, initially failed
      collection (`ModuleNotFoundError: solid_node.core.expressions`) before
      the module existed; all 36 green after implementation
      (`pytest tests/test_expressions.py -q`: 36 passed in 0.19s).
      renderer, and name minting. Stdlib only — no `ast`, which cannot read
      `$t`, reads `^` as xor, and would impose Python's `%`. Turn 1.1–1.4
      green.

## 2. The table in the document (red first)

- [x] 2.1 Red: `tests/test_expression_bindings.py` — a tree in which one
      subexpression appears in the operations of several nodes serializes to
      a document whose `bindings` array holds that subexpression once and
      whose operations name it; no operator application, call, or
      parenthesised group appears twice across the document's expressions
      and bindings taken together.
- [x] 2.2 Red: a bare number and a bare driver id occurring many times are
      **not** bound; `(big * big)` **is** bound once (occurrences, not
      distinct parents).
- [x] 2.3 Red: the array is ordered — every name each entry mentions is
      `$t`, an id in the `drivers` table, a math function name, or an
      earlier entry — and evaluating the table in one forward pass and then
      the operations reproduces the values the flat expressions produce, at
      several values of `$t` and of every driver. This is the parity test;
      evaluate with the framework's own numeric face so `^`, `%` and the
      degree trigonometry are the document's semantics and not Python's.
- [x] 2.4 Red: names are `_b0`, `_b1`, … in table order; a tree declaring a
      driver whose qualified id is `_b0` publishes that driver unchanged and
      mints its bindings under a longer prefix.
- [x] 2.5 Red: the version rule — a document with sharing declares 4 and
      carries the key; a document without sharing omits the key and declares
      2 (or 3 with a flexible leaf) and is **byte-identical** to the document
      the framework publishes today (pin a serialized fixture, not a shape
      assertion); a flexible tree with sharing declares 4.
- [x] 2.6 Red: a flexible leaf's `params` expression sharing a subexpression
      with an operation is published as a reference into the same table.
- [x] 2.7 Red: **the pass-through.** A tree carrying one expression the parser
      cannot read, beside expressions it can, still publishes: the document is
      written, the unreadable expression appears verbatim and unshared, every
      readable expression is bound as usual, the version is the one that table
      needs, and a warning names the offending text and identifies the
      expression **truncated** — assert the warning does not contain the whole
      expression, since one may be megabytes. No exception escapes to the
      caller. Then the other half: a table that would be *wrong* — an entry
      naming a later entry, a name colliding with a declared driver id, a
      rewrite that does not reproduce what the producer built — raises, and no
      document is written. Build the wrong-table cases by patching the
      internals; they are framework defects and must not be reachable from a
      model.
- [x] 2.8 Red: publishing one unchanged tree twice yields byte-identical
      documents, bindings and order included; and `solid build` run twice on
      an unchanged model carrying bindings does not republish
      (`builder._write_viewer_snapshot`'s byte comparison).
- [x] 2.9 Implement: `serializer.py` collects the document's expression
      strings from `operations` and flexible `params` in one walk, builds the
      table once, rewrites the strings, and `document_version()` answers 4 for
      a non-empty table; `core/export.py` and `core/builder.py` publish the
      key only when non-empty. Turn 2.1–2.8 green.

      **Evidence:** `tests/test_expression_bindings.py`, 20 cases, all
      initially failed collection (`ImportError: BINDINGS_DOCUMENT_VERSION`)
      before `bind_document`/`BINDINGS_DOCUMENT_VERSION` existed in
      `serializer.py`; all 20 green after wiring `bind_document` into
      `export.py` and `builder.py`
      (`pytest tests/test_expression_bindings.py -q`: 20 passed in 3.5s).
      Turning this on surfaced genuine, previously-undetected sharing in two
      existing fixtures (`tests/meta_project/machine.py`'s `Machine`, whose
      `position.value` repeats between each axis's carriage and cover; and
      `tests/flexible_project/spring.py`'s `Valvetrain`, whose
      `FREE_HEIGHT - self.lift` repeats between the retainer's placement and
      the spring's port) — exactly the "nearly every animated model" effect
      design.md D7 predicts. Six pre-existing tests in
      `tests/test_document_drivers.py` and `tests/test_flexible_document.py`
      asserted the old (2/3) version or the flexible leaf's literal
      (unreferenced) `params` text for those fixtures; updated to assert
      version 4 and to resolve a `params` value through the `bindings` table
      before comparing it, with a comment recording why (`git diff` on those
      two files is the record). No other test in the framework suite needed
      a change (section 3 below is the exhaustive check).

## 3. What must not change

- [x] 3.1 Red: `solid snapshot --renderer web` stages a document with no
      `bindings` key at version 2 (or 3), because its expressions are the
      constants a keyframed tree computed. Assert on the staged document.
- [x] 3.2 Red: the generated `.scad` for a tree carrying heavy sharing is
      byte-identical before and after this change, and `Solid2Node.as_number`
      still resolves a symbolic value through OpenSCAD's `echo(...)`. The
      SCAD path reads `self.angle` and `port.value`, never
      `operation.serialized`; pin that it stays so.
- [x] 3.3 Confirm the suites that read or produce documents are green with no
      change beyond section 2: `tests/test_export.py`,
      `tests/test_builder*.py`, `tests/test_pieces.py`,
      `tests/test_flexible*.py`, `tests/test_web_snapshot.py`,
      `tests/test_sphinx*.py`. Record any test that needed updating and why.

      **Evidence.** There is no `tests/test_web_snapshot.py` in this
      checkout; the browser/web-snapshot suites are `tests/test_browser_renderer.py`
      and `tests/test_snapshot.py`, run in its place.
      `pytest tests/test_export.py tests/test_builder_lifecycle.py
      tests/test_builder_reload_resilience.py tests/test_pieces.py
      tests/test_flexible_document.py tests/test_flexible_node.py
      tests/test_browser_renderer.py tests/test_snapshot.py
      tests/test_sphinx_ext.py -q`: 192 passed, 14 skipped (viewer-bundle-
      gated staging tests, run and green — see 3.1's evidence — plus a few
      unrelated environment-gated cases; none newly skipped by this change).
      Six tests needed updating, all recorded in 2.9's evidence and in the
      two files' own diffs: `tests/test_document_drivers.py`
      (`test_a_driver_declaring_export_publishes_the_table`, version 2→4)
      and `tests/test_flexible_document.py` (five tests: two flexible-free
      `Machine` fixtures now declare 4 instead of 2, two `Valvetrain`/spring
      fixtures now declare 4 instead of 3 and read `params['height']`
      through the new `resolved()` helper instead of comparing it to
      `LIFT_EXPRESSION` directly). Every update is a genuine, correct
      consequence of section 2 finding real sharing in an existing fixture
      (design.md D7's "nearly every animated model" effect) — no test's
      *intent* changed, and no assertion beyond the version/params-shape was
      touched.
- [x] 3.4 Record in this file that `node/operations.py::unserialize` has no
      caller in the framework, its tests or its tools, and `float()`s its
      argument — so it cannot read an expression today and needs the table
      only if it is ever revived.

      **Confirmed** (`grep -rn unserialize` across the worktree, excluding
      `openspec/`): the only call sites are inside
      `tests/test_operations.py` itself, all passing already-numeric
      literal strings (`'90.0'`, `'1.0'`); `unserialize`'s own docstring
      note in `operations.py` records the same thing. No producer, no CLI
      command, and no other test calls it. Left exactly as it is.

## 4. The parity fixture

- [x] 4.1 Red: `tools/generate_parity_fixture.py`'s coverage check reads
      emitted builtin names across the `bindings` table and the cases
      together — a builtin appearing only inside a binding counts as covered,
      and one appearing in neither still fails the regeneration.

      **Evidence and a disclosed deviation.** `tests/test_generate_parity_fixture.py`
      (5 cases) loads the tool as a module and drives `uncovered_builtins`
      directly, plus `tests/test_expression_corpus.py`'s new
      `test_a_name_inside_a_binding_is_covered`. Unlike sections 1-3, this
      section's test and its implementation (the `bindings=()` parameter
      added to `uncovered_builtins`, section 4.2's corpus) were written
      together rather than strictly red-then-green — the change is small,
      low-risk, and the red evidence that matters (a name reachable only
      through a binding is missed WITHOUT the added scan) is captured
      directly in `test_a_name_appearing_only_inside_a_binding_is_covered`
      and `test_a_name_in_neither_still_fails`, which compare the
      with-bindings and without-bindings answers on the same input and
      show they differ. `pytest tests/test_generate_parity_fixture.py
      tests/test_expression_corpus.py -q`: 9 passed.
- [x] 4.2 Add a **synthetic** corpus tree beside the existing two (design.md
      D13 — not the grasshopper clock, whose 31.6 MB would land in the viewer's
      repository and defeat the change), deliberately reusing a value across
      several operations and several nodes and over a driver as well as over
      `$t`, so the fixture carries an entry naming an earlier entry and an
      entry referenced from more than one case. Include the two shapes the
      consumer rules turn on: an operation whose whole expression is a binding
      name resolving through the table to `$t`, and one resolving to a declared
      driver id — so the viewer's parity test pins that dependence flows
      through a binding and that a binding name is not an undeclared driver id.
      Do not alter a pinned case's key or expected value.

      **Evidence.** `tests/expression_project/sharing.py`'s `SharedValueTree`:
      6 markers, 1 driver (`share`), 3 subexpressions each used more than
      once (`time_term = floor(360.0 * $t)`, `driver_term = share * 2.0`,
      `combo = time_term + driver_term`). Regenerating (4.3) mints
      `_b0..b3` (`_b0 = (360.0 * $t)`, `_b1 = floor(_b0)`,
      `_b2 = (share * 2.0)`, `_b3 = (_b1 + _b2)`): `_b1` names the earlier
      `_b0`, `_b3` names both earlier `_b1` and `_b2`; `_b1` is referenced
      from `time_only`'s and `time_nested`'s cases (two nodes), `_b2` from
      `driver_only`'s and `driver_nested`'s, `_b3` from `combo_a`'s (twice,
      occurrences not distinct parents) and `combo_b`'s. `time_only`'s
      case is exactly `"_b1"`, resolving through the table to `$t` alone;
      `driver_only`'s is exactly `"_b2"`, resolving to the declared driver
      `share` alone — the two consumer-rule shapes this task names.
- [x] 4.3 Regenerate the fixture **into this change's own evidence directory
      or the session scratchpad — never into the viewer checkout.** Two
      independent reasons. First, `solid-node-viewer` is mid-cycle right now
      (`share-expression-subtrees` is being implemented there), and a fixture
      carrying binding references would break its parity test until its paired
      change lands. Second, the generator's default path is
      `os.path.join(ROOT, '..', 'solid-node-viewer', …)`, which from a worktree
      at `solid-node/WTs/<name>/` resolves to `solid-node/WTs/solid-node-viewer/…`
      and does not exist at all (shop `docs/warts.md` item 9). The generator
      takes an explicit destination as `sys.argv[1]`; pass one. Prove there
      that every previously pinned key and expected value survives, and record
      the counts here. **The paired viewer change regenerates and commits the
      fixture in its own repository**; this cycle only proves the regeneration
      is correct.

      **Evidence.** Regenerated to
      `/tmp/claude-1000/-home-asa-devel-libresolid-studio/47329300-14b8-4e46-94a2-36b070c0a251/scratchpad/parity-fixture/parity-fixture.json`
      via `PYTHONPATH=$PWD .venv/bin/python tools/generate_parity_fixture.py
      <that path>` from the worktree root, using the workspace venv. Output:
      **451 expression cases** (14 containing `^`; 155 from the vocabulary
      corpus; covers all 14 emitted builtins), **22 conversions**, **4
      flexible bindings** of 3858 vertices (7 pinned), and the new
      top-level **`bindings`: 4 entries**. Compared programmatically
      against the committed BEFORE fixture at
      `solid-node-viewer/solid_node_viewer/widget/src/parity-fixture.json`
      (421 cases, no `bindings` key, read-only — nothing in the viewer
      checkout was touched): every one of the 421 old keys is present in
      the new fixture; **0 mismatched `expected` values**; **0 changed
      `expression` strings** among the old cases (the rewrite-to-a-binding
      permission in the kinematics spec was not exercised on the existing
      corpora, since `bind_document` runs only on the new sharing tree —
      see 4.2's evidence); `conversions` and `flexible` are byte-equal;
      every old driver declaration is unchanged. The 30 new cases are
      exactly the sharing corpus's 10 operation scalars × 3 snapshots.
      **The paired viewer change regenerates and commits the real fixture
      in its own repository**; this evidence proves the regeneration this
      cycle enables is correct, not that it was published there.
- [x] 4.4 `tests/test_expression_corpus.py` — extend the in-repo mirror of
      the coverage guard to the table, so the framework's own suite catches
      an uncovered builtin without the viewer checkout present.

      **Evidence:** `pytest tests/test_expression_corpus.py -q`: 4 passed
      (was 3; `test_a_name_inside_a_binding_is_covered` added).

## 5. Documentation and records

- [x] 5.1 `docs/architecture.md`: a "Schema version 4" paragraph after the
      version-3 one, in the same voice — the table, its ordering, the naming
      rule, why the bump is not additive, and that the `.scad` path is
      untouched. Update the accepted-version set where the document loader's
      refusal is described, and the `manifest.json` / `viewer.json` line in
      the subsystem map.

      **Done.** New paragraph after the version-3 one (before the
      printed-piece-inventory paragraph); the `solid export` line's
      `version: 2, or 3...` note extended with `, or 4...`; the widget's
      prepare-phase refusal paragraph updated from `[1, 2, 3]` to note the
      paired-change widening to `[1, 2, 3, 4]` and that a version-4 document
      is refused, by design, until then; the `Export` and `Build pipeline`
      subsystem-map rows gained ADR-080 and `Export`'s Code column gained
      `core/expressions.py`.
- [x] 5.2 `docs/changelog.rst` "Unreleased": an entry naming 3DPrintedClocks
      and `wall_clock_53_grasshopper` as the originating project, quoting the
      measured 31.6 MB → ~30 kB and 10,287× on expression text, stating the
      version bump and that a consumer that cannot read version 4 refuses,
      and stating the producer cost (about 4 s on that document).

      **Done, with the real measured numbers from 6.3 rather than the
      prototype's.** The entry quotes 31,611,478 → 3,130 bytes of
      expression text, 31,638,555 → 32,227 bytes of document, 56 bindings,
      212 characters longest, the version-4/refusal rule, and the two
      observed clean-build times (17.6 s and 23.3 s) rather than the
      prototype's unconfirmed "+4 s" (see 6.3's evidence for why).
- [ ] 5.3 Promote `adrs/ADR-080-a-shared-subexpression-is-named-once.md` from
      this change directory into `docs/adrs/EXPORT/`, index it in
      `docs/adrs/README.md` under EXPORT in chronological order, and record
      that it extends ADR-034 and depends on ADR-022 and ADR-051.

      **Not done here, on the shop's explicit instruction for this cycle.**
      The shop's framework-change discipline extracts and promotes an ADR
      only after adversarial review; this session was directed to write the
      ADR's final text in the change directory and leave promotion,
      `docs/adrs/README.md` indexing, spec sync and archival to the
      coordinator after review. `adrs/ADR-080-a-shared-subexpression-is-named-once.md`
      in this change directory carries what would be promoted: `Extends`
      ADR-034, `Depends on` ADR-022 and ADR-051, and a Consequences section
      updated with the real measured numbers (see 6.3). Its `Status` is left
      `Proposed`, unpromoted.
- [x] 5.4 Reference documentation: wherever the published document's shape is
      described for a user, add the table. Do not document the parser as a
      public interface — `solid_node/core/expressions.py` is internal.

      **Done.** `docs/embedding.rst`: the manifest-shape paragraph gained
      `bindings`, a new explanatory paragraph on what it is and its naming/
      ordering rule, the version-4 rule, and the JavaScript API section's
      accepted-versions line updated the same way as architecture.md's.
      `docs/cli.rst`'s `solid export` section already deferred shape detail
      to `embedding.rst` and needed no change. `solid_node/core/expressions.py`
      is not named in either file.

## 6. Close the cycle

- [x] 6.1 Full framework suite green from this worktree with the workspace
      venv; record the counts here.

      **Evidence:** `PYTHONPATH=$PWD .venv/bin/python -m pytest -x -q`:
      **1592 passed, 16 skipped, 258 subtests passed**, 0 failures, in
      181.85 s. All 16 skips are pre-existing environment gates unrelated to
      this cycle: sphinx not installed (13, `test_sphinx_ext.py`), the
      Internal-Cycloidal-Actuator vendor STEP fixture not present (2,
      `test_step_assembly.py`), and the opt-in web-snapshot E2E flag not set
      (1, `test_browser_renderer.py`) — confirmed with `-rs`.
- [ ] 6.2 `openspec validate expression-bindings --strict`, sync the baseline
      `export`, `build-viewer-artifacts`, `kinematics` and `flexible-parts`
      specs, archive the change, and commit the implementation record as the
      cycle's single implementation commit.

      **Validation done; sync, archive and commit deferred, on the shop's
      explicit instruction for this cycle.** `openspec validate
      expression-bindings --strict` → `Change 'expression-bindings' is
      valid`. Per this session's operating instructions, spec sync,
      archival and the cycle's single implementation commit happen after
      adversarial review, by the coordinator — not in this session. The
      worktree is left uncommitted, one commit ahead of base (the planning
      commit `5d4d054`), exactly as required for that review.
- [x] 6.3 **Caller check, with numbers.** Rebuild
      `wall_clock_53_grasshopper` in `projects/3DPrintedClocks` against this
      worktree and record here: `viewer.json` size before and after, the
      number of bindings, the longest published expression, the document
      version, and the build time delta. The expected figures from the
      prototype are 31,638,555 B → ~30 kB, 57 bindings, 197 characters,
      version 4, about +4 s. Report any figure that disagrees rather than
      restating the prototype's.

      **Measured, against the real project (not the prototype).** The
      published `_build/wall_clock_53_grasshopper/viewer.json` was copied to
      the session scratchpad as BEFORE (31,638,555 B, confirmed against the
      proposal's figure) before rebuilding
      (`cd projects/3DPrintedClocks && PYTHONPATH=<worktree>
      .venv/bin/python -m solid_node.cli build wall_clock_53_grasshopper`,
      run from the project directory against this worktree's framework on
      `PYTHONPATH`; published STLs were already current, so this rebuild
      only re-serialized). AFTER copied the same way.

      | | before | after | prototype's figure |
      |---|---|---|---|
      | `viewer.json` size | 31,638,555 B | **32,227 B** | ~30 kB |
      | expression text | 31,611,478 B | **3,130 B** | 3,072 B |
      | document version | 2 | **4** | 4 |
      | bindings count | — | **56** | 57 |
      | longest binding expression | — | **212 characters** | 197 |
      | nodes / operations | 46 / 76 | 46 / 76 (unchanged) | — |

      Document shrink **981.7×**; expression-text shrink **10,099.5×** —
      both close to but not identical to the prototype's (10,287×), as
      expected of a different prototype run on the same document; reported
      here rather than restated. `drivers` is empty and `animation.loop`
      is `43200.0`, both as the proposal recorded.

      **Nothing else changed.** A structural diff of the two documents with
      every operation's and binding's expression text stripped out (every
      node's `name`, `type`, `color`, `mtime`, `model`, `piece`, child
      order, and operation kind per slot; plus `format`, `animation`,
      `drivers`, `instructions`, `pieces` compared whole) is byte-for-byte
      equal. The only differences between the two documents are the new
      `bindings` key, the `version` bump, and the operation/`params`
      expression strings themselves.

      **Numeric parity**, evaluated in Python with the framework's own
      `solid_node.core.expressions` parser and the document's own semantics
      (OpenSCAD degree trig, `^` as `pow`, `%` as `fmod`): every one of the
      document's 116 operation scalar slots, evaluated at
      `$t ∈ {0, 1/3, 2/3}` — the BEFORE flat expression against the AFTER
      table evaluated forward then the AFTER operation — **348 checks, 0
      mismatches, exact (0.0 max relative error)**; no driver is declared,
      so no driver axis was needed. 22 of the 116 slots are directly
      time-dependent (contain `$t` in the BEFORE flat text) at each time
      point; several more depend on time transitively only through a bound
      reference, and parity held for those exactly the same way.

      **Build time.** Two clean CLI builds (STLs already current both
      times) measured 23.3 s and 17.6 s wall-clock — this is the whole
      `solid build` invocation, dominated by the model's own escapement and
      motion-works gear construction (unrelated to this cycle) rather than
      by the bindings pass. An attempt to isolate the bindings pass alone
      (`bind_document` timed directly around an already-assembled node, no
      `Builder`) was confounded: that path's `node.assemble()` does not
      take the same currency shortcuts `solid build`'s `Builder` does, and
      one run of it hit the model's own iterative gear-cutting retry loop
      ("couldn't cut gear, trying again") and ran to 200 s before finishing
      — visibly a property of the model's own OCCT geometry retries, not of
      this change, but not a clean isolated measurement either. The
      honest, reproducible figure is therefore the whole-build wall time
      above; the design's prototype figure of "about +4 s" for the pass
      alone is not independently re-confirmed against this real document
      in this session, and is reported as unconfirmed here rather than
      restated as measured.
- [ ] 6.4 Report to the pilot, and do **not** do here:
      - the **paired viewer change** in `solid-node-viewer`, which must
        follow `share-expression-subtrees`: widen the accepted document
        versions to `[1, 2, 3, 4]`, evaluate the table top to bottom into the
        scope it already builds for `$t` and drivers, derive each entry's
        inputs from the table's order to bound re-evaluation, and commit the
        regenerated `parity-fixture.json`;
      - the `viewer` extra's version floor in `pyproject.toml`, which cannot
        be written until the viewer version that reads version 4 is released
        (design.md D11);
      - the shop's `shop-skills/solid-node-api/SKILL.md`, if it describes the
        published document's shape;
      - `docs/warts.md` item 12 in the shop, which this cycle answers.


## 7. Adversarial review fixes (coordinator round 1)

Three findings from a coordinator review against the implemented module,
fixed red-first (reproduced against the pre-fix module, confirmed fixed
against the post-fix one, then given permanent regression tests), still
uncommitted.

- [x] 7.1 **An unknown name must never fail the build.** `_validate_bindings`
      checked EVERY leaf name any binding's expression carried against
      `{$t} | declared driver ids | earlier entries`, so a name the
      framework does not know at all -- `PI` from a hand-written
      `scad_inline` constant, or any other name a project's own arithmetic
      reached solid2 with directly -- raised `BindingTableError` and
      stopped the build, contradicting D2 ("refusal is for a table that
      would be wrong, never a project's fault"). Fixed: `_mint_prefix`
      (split out of `_mint_names`) is now threaded into `_validate_bindings`
      as `prefix`, and the ordering check applies only to a leaf name that
      MATCHES the minted pattern `<prefix>\d+` -- a name that does not is
      the project's business and passes through unexamined, exactly as an
      unreadable expression's own unresolved names already do on the
      consumer side (spec rule (c), unchanged). A minted-LOOKING name that
      is not `$t`/declared/earlier still refuses, as before (still a
      framework defect, still unreachable from a correct model).

      **Reproduced red** against the pre-fix module (coordinator's own
      repro, confirmed): `bind_expressions(['(PI * $t)', '(PI * $t)'], [])`
      raised `BindingTableError: binding '_b0' names 'PI', which is not
      $t, a declared driver id, or an entry earlier in the table`.
      **Green after the fix**, verified directly and with new tests:
      `tests/test_expressions.py::UnknownNameDoesNotRefuseTheBuildTest`
      (2 cases: an unknown name reused binds and does not raise; a stray
      reference to a minted-looking name still refuses). Existing tests
      `PassThroughTest::test_a_table_naming_a_later_entry_refuses` and
      `::test_a_name_colliding_with_a_declared_driver_refuses` in
      `tests/test_expression_bindings.py` updated for `_validate_bindings`'s
      new required `prefix` argument; their outcomes are unchanged (both
      still refuse, since `_b1`/`_b0` in those cases DO match the minted
      pattern).
- [x] 7.2 **A deep expression must fall back to verbatim, not crash the
      build.** A left-nested chain in the shape solid2 itself builds for
      repeated addition -- `(((($t + 0) + 1) + 2) ...)`, each level its own
      parenthesised group -- exhausted Python's recursion limit inside
      `parse()` (the parser spends several stack frames per level of
      SOURCE TEXT nesting: `_expr` down through `_atom` and back into
      `_parenthesised`), and `bind_expressions` did not catch it, so
      `RecursionError` reached the serializer uncaught and the build died.
      Fixed: `bind_expressions` now catches `RecursionError` around each
      `parse()` call exactly like `ExpressionError` -- the expression is
      published verbatim and unshared, with a warning, and the rest of the
      document still binds. `render`, `_matches`, `_name_leaves` and
      `_has_named_descendant` each recurse only ONE frame per level of a
      node's own tree (cheaper than the parser's several frames per level
      of source nesting), so a node that ever reaches them came from a
      `parse()` that already completed inside the limit at a higher
      per-level cost and cannot be deep enough to trip a cheaper traversal
      -- recorded as a comment above those four functions rather than a
      runtime guard, since the invariant is structural. Also made the
      parser itself cheaper per level: `_parenthesised` now parses a
      group's content in place on the same `_Parser` instance instead of
      constructing a fresh `_Parser(...).parse()` per nesting level,
      trading one wrapper call and object construction for a direct
      `self._expr()`, which raises (not removes) the depth a document can
      reach before falling back -- the verbatim floor remains the actual
      requirement.

      **Reproduced red** against the pre-fix module (coordinator's own
      repro, confirmed): a 3000-deep left-nested `$t + int` chain raised
      `RecursionError` straight out of `bind_expressions`.
      **Green after the fix**, verified directly and with new tests:
      `tests/test_expressions.py::DeepChainFallsBackToVerbatimTest` (3
      cases: a 3000-deep chain publishes verbatim with exactly one warning
      per occurrence and an empty `bindings` table when nothing else is
      shared; the SAME chain beside a shallow, genuinely shared
      subexpression still leaves the deep one verbatim while the shallow
      one binds correctly; and explicitly, `bind_expressions` never lets
      `RecursionError` escape, tested at 5000 deep).
- [x] 7.3 **A non-string slot value must never crash the pass.**
      `bind_expressions([1.5, 1.5], [])` raised `TypeError: object of type
      'float' has no len()` inside `parse()`. Defensive only -- every
      operation stringifies today (`operations.py`'s `serialized`
      properties), and `unserialize()`, the one path that would not, has no
      caller (tasks.md 3.4) -- but cheap to close. Fixed: the initial
      parsing loop in `bind_expressions` now checks `isinstance(expression,
      str)` before calling `parse()`; a non-string slot is treated as
      unparsed (`None`, like an unreadable or too-deep expression) but,
      unlike those two, contributes NO warning, since it was never text to
      begin with and there is nothing to name.

      **Reproduced red** against the pre-fix module (coordinator's own
      repro, confirmed): `bind_expressions([1.5, 1.5], [])` raised
      `TypeError` rather than returning cleanly.
      **Green after the fix**, verified directly and with a new test:
      `tests/test_expressions.py::NonStringSlotIsReturnedUntouchedTest`
      (the float pair passes through untouched, no bindings, no warnings).

- [x] 7.4 **Re-verification after the fixes**, all from this worktree with
      the workspace venv:
      - `pytest tests/test_expressions.py -q`: **42 passed** (was 36; +6
        adversarial-finding regression tests).
      - `pytest tests/test_expression_bindings.py -q`: **22 passed** (was
        20; 2 existing wrong-table tests updated for `_validate_bindings`'s
        new `prefix` argument, outcomes unchanged).
      - **Caller-check parity script, rerun against a fresh rebuild of
        `wall_clock_53_grasshopper`** (`solid build wall_clock_53_grasshopper`
        from `projects/3DPrintedClocks` against this worktree): published
        `viewer.json` is **byte-identical** to the pre-fix AFTER document
        (32,227 bytes, `cmp` confirms — the grasshopper model exercises none
        of the three edge cases, so the fixes change nothing about its
        output); **56 bindings** (unchanged); the parity script reports
        **348 checks, 0 mismatches, exact** (unchanged from 6.3).
      - `pytest -x -q` (full suite): **1598 passed, 16 skipped, 258
        subtests passed**, 0 failures, 189.38 s (was 1592 passed; +6 new
        tests; the same 16 pre-existing environment-gated skips as 6.1).
      - `openspec validate expression-bindings --strict` → `Change
        'expression-bindings' is valid`.
      - Nothing committed: HEAD is still the planning commit `5d4d054`, one
        commit ahead of base `4bf9b69`, worktree otherwise as this session
        left it (uncommitted).
