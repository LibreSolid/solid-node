## 1. The expression reader (red first)

- [ ] 1.1 Red: `tests/test_expressions.py` — a parser in
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
- [ ] 1.2 Red: text the parser cannot read — an unbalanced parenthesis, an
      unknown token, a trailing comma, a bare `[1, 2]` vector — is reported as
      unreadable rather than guessed at, naming the offending text.
- [ ] 1.3 Red: interning is **structural**, not textual: `(1.0 + 2.0)` built
      by solid2 and `1.0+2.0` from `scad_inline` intern to one node; and the
      substring memo does not change any answer (assert the same table with
      the memo disabled).
- [ ] 1.4 Red: a rendered node re-parses to itself — for every node in a
      corpus tree, `parse(render(node)) is node` — so the emitted table is
      in the language the parser reads.
- [ ] 1.5 Implement `solid_node/core/expressions.py`: tokenizer, precedence-
      climbing parser, structural interner keyed on `(kind, op-or-name, child
      ids)`, substring memo on parenthesised groups, occurrence counting,
      renderer, and name minting. Stdlib only — no `ast`, which cannot read
      `$t`, reads `^` as xor, and would impose Python's `%`. Turn 1.1–1.4
      green.

## 2. The table in the document (red first)

- [ ] 2.1 Red: `tests/test_expression_bindings.py` — a tree in which one
      subexpression appears in the operations of several nodes serializes to
      a document whose `bindings` array holds that subexpression once and
      whose operations name it; no operator application, call, or
      parenthesised group appears twice across the document's expressions
      and bindings taken together.
- [ ] 2.2 Red: a bare number and a bare driver id occurring many times are
      **not** bound; `(big * big)` **is** bound once (occurrences, not
      distinct parents).
- [ ] 2.3 Red: the array is ordered — every name each entry mentions is
      `$t`, an id in the `drivers` table, a math function name, or an
      earlier entry — and evaluating the table in one forward pass and then
      the operations reproduces the values the flat expressions produce, at
      several values of `$t` and of every driver. This is the parity test;
      evaluate with the framework's own numeric face so `^`, `%` and the
      degree trigonometry are the document's semantics and not Python's.
- [ ] 2.4 Red: names are `_b0`, `_b1`, … in table order; a tree declaring a
      driver whose qualified id is `_b0` publishes that driver unchanged and
      mints its bindings under a longer prefix.
- [ ] 2.5 Red: the version rule — a document with sharing declares 4 and
      carries the key; a document without sharing omits the key and declares
      2 (or 3 with a flexible leaf) and is **byte-identical** to the document
      the framework publishes today (pin a serialized fixture, not a shape
      assertion); a flexible tree with sharing declares 4.
- [ ] 2.6 Red: a flexible leaf's `params` expression sharing a subexpression
      with an operation is published as a reference into the same table.
- [ ] 2.7 Red: **the pass-through.** A tree carrying one expression the parser
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
- [ ] 2.8 Red: publishing one unchanged tree twice yields byte-identical
      documents, bindings and order included; and `solid build` run twice on
      an unchanged model carrying bindings does not republish
      (`builder._write_viewer_snapshot`'s byte comparison).
- [ ] 2.9 Implement: `serializer.py` collects the document's expression
      strings from `operations` and flexible `params` in one walk, builds the
      table once, rewrites the strings, and `document_version()` answers 4 for
      a non-empty table; `core/export.py` and `core/builder.py` publish the
      key only when non-empty. Turn 2.1–2.8 green.

## 3. What must not change

- [ ] 3.1 Red: `solid snapshot --renderer web` stages a document with no
      `bindings` key at version 2 (or 3), because its expressions are the
      constants a keyframed tree computed. Assert on the staged document.
- [ ] 3.2 Red: the generated `.scad` for a tree carrying heavy sharing is
      byte-identical before and after this change, and `Solid2Node.as_number`
      still resolves a symbolic value through OpenSCAD's `echo(...)`. The
      SCAD path reads `self.angle` and `port.value`, never
      `operation.serialized`; pin that it stays so.
- [ ] 3.3 Confirm the suites that read or produce documents are green with no
      change beyond section 2: `tests/test_export.py`,
      `tests/test_builder*.py`, `tests/test_pieces.py`,
      `tests/test_flexible*.py`, `tests/test_web_snapshot.py`,
      `tests/test_sphinx*.py`. Record any test that needed updating and why.
- [ ] 3.4 Record in this file that `node/operations.py::unserialize` has no
      caller in the framework, its tests or its tools, and `float()`s its
      argument — so it cannot read an expression today and needs the table
      only if it is ever revived.

## 4. The parity fixture

- [ ] 4.1 Red: `tools/generate_parity_fixture.py`'s coverage check reads
      emitted builtin names across the `bindings` table and the cases
      together — a builtin appearing only inside a binding counts as covered,
      and one appearing in neither still fails the regeneration.
- [ ] 4.2 Add a **synthetic** corpus tree beside the existing two (design.md
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
- [ ] 4.3 Regenerate the fixture **into this change's own evidence directory
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
- [ ] 4.4 `tests/test_expression_corpus.py` — extend the in-repo mirror of
      the coverage guard to the table, so the framework's own suite catches
      an uncovered builtin without the viewer checkout present.

## 5. Documentation and records

- [ ] 5.1 `docs/architecture.md`: a "Schema version 4" paragraph after the
      version-3 one, in the same voice — the table, its ordering, the naming
      rule, why the bump is not additive, and that the `.scad` path is
      untouched. Update the accepted-version set where the document loader's
      refusal is described, and the `manifest.json` / `viewer.json` line in
      the subsystem map.
- [ ] 5.2 `docs/changelog.rst` "Unreleased": an entry naming 3DPrintedClocks
      and `wall_clock_53_grasshopper` as the originating project, quoting the
      measured 31.6 MB → ~30 kB and 10,287× on expression text, stating the
      version bump and that a consumer that cannot read version 4 refuses,
      and stating the producer cost (about 4 s on that document).
- [ ] 5.3 Promote `adrs/ADR-080-a-shared-subexpression-is-named-once.md` from
      this change directory into `docs/adrs/EXPORT/`, index it in
      `docs/adrs/README.md` under EXPORT in chronological order, and record
      that it extends ADR-034 and depends on ADR-022 and ADR-051.
- [ ] 5.4 Reference documentation: wherever the published document's shape is
      described for a user, add the table. Do not document the parser as a
      public interface — `solid_node/core/expressions.py` is internal.

## 6. Close the cycle

- [ ] 6.1 Full framework suite green from this worktree with the workspace
      venv; record the counts here.
- [ ] 6.2 `openspec validate expression-bindings --strict`, sync the baseline
      `export`, `build-viewer-artifacts`, `kinematics` and `flexible-parts`
      specs, archive the change, and commit the implementation record as the
      cycle's single implementation commit.
- [ ] 6.3 **Caller check, with numbers.** Rebuild
      `wall_clock_53_grasshopper` in `projects/3DPrintedClocks` against this
      worktree and record here: `viewer.json` size before and after, the
      number of bindings, the longest published expression, the document
      version, and the build time delta. The expected figures from the
      prototype are 31,638,555 B → ~30 kB, 57 bindings, 197 characters,
      version 4, about +4 s. Report any figure that disagrees rather than
      restating the prototype's.
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
