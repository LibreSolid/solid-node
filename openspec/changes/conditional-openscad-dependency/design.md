## Context

OpenSCAD's obligation lives entirely in prose. It is not in `pyproject.toml`
and never was — `README.rst` tells the user to put it on the PATH, and
`node-model` ratifies all adapters as "compiled through OpenSCAD as the
universal target". Nothing enforces or checks it, so a user without the binary
meets a `FileNotFoundError` raised by `Popen` several frames below the code
that wanted it.

The preceding cycle removed the last invocation from an all-CadQuery project.
Traced with a wrapper binary: `projects/snowman` — CadQuery leaves and a
`FusionNode`, previously one invocation for the fusion — now builds with zero,
writing four `.brep` artifacts instead. `projects/snowman-3`, on Solid2 leaves,
still makes seven and always will.

So the prose is now wrong for eleven of eighteen catalogue projects, including
every substantial one. This cycle makes the declared dependency match the real
one.

## Goals / Non-Goals

**Goals:**

- State precisely which paths require the binary, and guarantee that a project
  reaching none of them requires nothing.
- Replace subprocess launch failures with errors that name the node or command
  that needed OpenSCAD and what to do about it.
- Leave every path that genuinely uses OpenSCAD exactly as it is.

**Non-Goals:**

- Removing OpenSCAD support, or weakening the multi-backend promise. ADR-004's
  adapter pattern stands; only its "universal compilation target" clause is
  superseded.
- Changing the snapshot default renderer. See the decision below.
- Detecting the binary at install time, import time, or CLI start. Availability
  is checked where an operation needs it and nowhere else.

## Decisions

**The requiring paths are enumerated rather than inferred.** There are five —
`Solid2Node`/`OpenScadNode` leaf STL rendering, faceted fusion STL rendering,
`Solid2Node.as_number()`, the GUI viewer, the OpenSCAD snapshot renderer.
Enumerating them in the spec makes the guarantee testable ("an all-exact
project reaches none of these") and makes a future path that shells out to
OpenSCAD an explicit addition to a list rather than a silent sixth case.

Writing the list out is what showed that `JScadNode` does not belong on it.
It looks like a mesh backend and was drafted as one, but `as_scad()` invokes
the separate `jscad` binary, writes the STL and stamps the mtime, so
`generate_stl` finds the artifact current and returns before any OpenSCAD
subprocess. The same is true of `CadQueryNode` and always was — which is why
an all-CadQuery project only ever invoked OpenSCAD for its fusion, and why
removing that invocation last cycle took the count to zero.

**JSCAD's own binary is deferred, deliberately.** `JScadNode` has exactly the
problem this cycle fixes — an undeclared external tool, a bare subprocess
failure when it is absent, and no statement of who needs it — but with `jscad`
rather than `openscad`. Two arguments for handling it here: it is the same
shape, and the availability helper would be reusable almost verbatim.

Against, and decisive: `jscad` is a distinct dependency with its own install
story (a Node toolchain, and per its adapter's docstring, node dependencies
installed in the directory `solid` runs from), no project in the catalogue
uses `JScadNode`, and so there is no caller to validate the change against.
Bundling it would widen a cycle whose whole claim is that it changes nothing
for a working installation, and would ratify a contract for a tool nobody here
exercises. It is recorded as deferred in the capability itself and in the ADR,
so it is a named gap rather than an oversight — until then, a missing `jscad`
keeps failing at its launch.

`as_number()` matters more than its size suggests: it evaluates symbolic `$t`
expressions through an OpenSCAD `echo`, so an animated Solid2 project needs the
binary even where no STL is being rendered. It is the one requiring path that
is not a render.

**Availability is checked at the point of use, never earlier.** A start-up or
import-time check would impose the dependency on every project to serve the
minority that needs it, which is the situation being removed. Checking at the
point of use means the guarantee — "reaches none of them, requires none of
them" — falls out of the control flow rather than being asserted separately.

**The snapshot default stays `openscad`.** Three alternatives were considered:

- *Default by availability* — use OpenSCAD when installed, web otherwise.
  Rejected: this is substitution, and `web-snapshot` already ratifies that a
  renderer which cannot run must fail rather than defer to the other one. The
  rule should not hold in one direction only.
- *Default by the project's backends* — web for an exact model, OpenSCAD
  otherwise. Rejected: it silently changes the appearance of snapshots of
  existing CadQuery projects — different background, different colour scheme —
  and the shop's recorded visual evidence for `v8-engine`, `gearbox` and the
  windmills depends on that continuity.
- *Default to web for everyone.* Rejected for the same reason, more broadly.

Keeping the default and failing with a named remedy costs an OpenSCAD-less user
one explicit `--renderer web`, and costs everyone else nothing. This cycle
therefore makes the existing rule symmetric rather than adding an exception to
it.

**Nothing is added to `pyproject.toml`.** OpenSCAD is an external binary, not a
Python distribution; there is nothing to declare as an extra. The dependency
was always documentation, and documentation is what this cycle corrects.

## Risks / Trade-offs

- **An availability check on a hot path.** The build renders many nodes, and a
  `shutil.which` per node would be wasteful. → Resolve availability once per
  process and reuse it; the check is about the binary's presence, which does
  not change mid-build.

- **A user relying on the blanket install instruction.** Someone who reads only
  the README could conclude OpenSCAD is now never needed. → The README states
  it as conditional on the backends a project uses, naming them, rather than
  simply dropping the line.

- **Silent scope creep into "OpenSCAD is deprecated".** It is not, and the
  specs should not read that way. → `node-model` keeps OpenSCAD as the
  compilation target for mesh backends and keeps `as_scad()` on every adapter;
  only the word "universal" goes.

- **A path that shells out to OpenSCAD is added later without joining the
  list.** → The enumeration is a ratified requirement, so adding such a path
  without amending it is a spec violation rather than an oversight.

## Migration Plan

1. Land the availability contract and the error paths. A machine with OpenSCAD
   installed sees no behavioural change whatsoever.
2. Update `README.rst` to state the dependency as conditional, naming the
   backends and commands that need it.
3. Supersede ADR-004 in part: record that the universal-compilation-target
   clause no longer holds, that the multi-backend adapter pattern it
   established does, and link the two ADRs from the preceding cycle.

Rollback is the branch. Nothing about an installed OpenSCAD's behaviour
changes, so a revert restores only the obligation and the poorer error
message.

## Open Questions

None blocking. STEP delivery and the `BRepExtrema` distance assertions remain
scoped to their own later cycles.
