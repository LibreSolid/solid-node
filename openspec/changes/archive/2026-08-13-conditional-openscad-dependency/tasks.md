## 1. Red evidence first

- [x] 1.1 Add a framework test that builds an all-exact fixture with
      `openscad` removed from the PATH and requires the build, the test run
      and the publication to succeed. Confirm it currently PASSES for the
      build (Cycle A already removed the invocations) and record which of the
      three, if any, still reaches for the binary.
- [x] 1.2 Add a framework test that renders a `Solid2Node` fixture with
      `openscad` removed from the PATH and requires an error naming the node
      and its backend. Confirm it FAILS today with a bare `FileNotFoundError`
      from `Popen`, and record that message — it is what the cycle replaces.
- [x] 1.3 Add the same red test for `solid develop --openscad`, for
      `solid snapshot --renderer openscad`, and for `Solid2Node.as_number()`
      on a symbolic value. Confirm each fails obscurely today.

## 2. Availability contract

- [x] 2.1 Add a single availability helper resolving the OpenSCAD binary once
      per process and reporting whether it is present, so the check is not
      repeated per node during a build.
- [x] 2.2 Give it one error type carrying what needed the binary and the
      remedy, so every requiring path raises the same shape.
- [x] 2.3 Add a framework test that the helper is never consulted during an
      all-exact build, so the guarantee follows from control flow rather than
      from a separate assertion.

## 3. The five requiring paths

- [x] 3.1 Check availability in `AbstractBaseNode.generate_stl` before
      launching the subprocess (`solid_node/node/base.py`), failing with the
      node named and the reason its backend needs OpenSCAD.
- [x] 3.2 Check it in `Solid2Node.as_number` before its `Popen`
      (`solid_node/node/adapters/solid2.py`), naming the node and that
      symbolic value evaluation needs OpenSCAD.
- [x] 3.3 Check it in `OpenScadViewer` (`solid_node/viewers/openscad.py`),
      reporting the requested viewer and the missing binary, and verify the
      web viewer is not silently left as a stand-in.
- [x] 3.4 Check it in `OpenScadRenderer` / `solid_node/manager/snapshot.py`,
      naming the missing binary and `--renderer web`, and writing no image.
      Keep it distinct from the existing xvfb error, which is about a display
      rather than the binary.
- [x] 3.5 Confirm a faceted `FusionNode` reaches 3.1 exactly as a
      `Solid2Node` leaf does, and that an exact one never does.
- [x] 3.6 Confirm a `JScadNode` reaches NONE of the five checks: its
      `as_scad()` writes the STL through `jscad` and stamps the mtime, so
      `generate_stl` returns before the availability check. Add a test
      pinning that a `JScadNode` builds with no `openscad` on the PATH.
- [x] 3.7 Turn 1.2 and 1.3 green.

## 4. The default renderer stays put

- [x] 4.1 Add a test pinning that `solid snapshot` with no `--renderer`
      selects OpenSCAD for an all-exact project on a machine where the binary
      is installed — the default follows neither availability nor the
      project's backends.
- [x] 4.2 Add a test that the OpenSCAD renderer, when unavailable, does not
      produce an image through the web renderer.

## 5. Records and documentation

- [x] 5.1 Update `README.rst` to state OpenSCAD as conditional on the backends
      and commands that use it, naming them, rather than as a blanket
      requirement. Do not imply OpenSCAD is deprecated.
- [x] 5.2 Supersede ADR-004 in part: the universal-compilation-target clause
      no longer holds; the multi-backend adapter pattern stands. Link
      ADR-044 and ADR-045 from the preceding cycle. Update
      `docs/adrs/README.md` status fields.
- [x] 5.3 State the deferral explicitly in the ADR for this cycle, under
      consequences: `JScadNode` carries the same undeclared-external-tool
      problem with the `jscad` binary and is deliberately left out of scope,
      because `jscad` has its own install story and no catalogue project
      exercises `JScadNode`, so there is no caller to validate it against.
      Record that a missing `jscad` therefore still fails at its subprocess
      launch, and that extending this capability to it is the natural
      follow-on.
- [x] 5.4 Update `docs/architecture.md` where the synthesis changed.

## 6. Validating callers

- [x] 6.1 Run the full framework suite. All green.
- [x] 6.2 Build, test and snapshot `projects/snowman` with `openscad` removed
      from the PATH. The build and tests must succeed; the snapshot must fail
      naming `--renderer web`, and must succeed when given it.
- [x] 6.3 Build `projects/snowman-3` (Solid2) with OpenSCAD present and
      confirm nothing changed. Then remove it from the PATH and confirm the
      failure names the node and its backend.
- [x] 6.4 Build one CadQuery project with OpenSCAD present
      (`projects/gearbox`) and confirm the traced invocation count is still
      zero and its artifacts are unchanged.
