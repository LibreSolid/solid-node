## Context

`New.handle()` creates files without loading project or viewer configuration,
then prints `solid develop` followed by an unconditional localhost URL. The
later command owns `.env` loading, viewer discovery, port selection, and
dependency diagnostics. Reproducing that logic in the offline scaffold would
couple an otherwise small command to optional runtime state and could still be
stale when development starts from another shell.

## Goals / Non-Goals

**Goals:**

- Keep the generated-directory and `solid develop` next steps actionable.
- Make the message correct for configured ports, browser viewing, OpenSCAD,
  and missing-viewer diagnostics.
- Pin the public output so a fixed endpoint cannot return unnoticed.

**Non-Goals:**

- Select or launch a viewer during scaffolding.
- Import viewer metadata, parse `.env`, or duplicate develop's configuration.
- Change generated project content or the develop command's behavior.

## Decisions

### D1: End the scaffold guidance at the owning command

The success message will print `cd <target>` and `solid develop`, then stop.
`solid develop` will continue to open the selected GUI or run the browser
server, using its own configuration and remedies.

Interpolating `SOLID_NODE_PORT` was rejected because it would still promise a
browser in an OpenSCAD-only installation and would require scaffolding to
interpret configuration that is not active until after the user changes
directory. Inspecting viewer availability was rejected because installed
packages and executables can differ between scaffolding and the later project
environment.

### D2: Test absence of endpoint prediction

A focused manager test will capture successful output and require the target,
the directory change, and `solid develop`. It will reject the old fixed URL.
This pins the ownership boundary while leaving presentation otherwise free.

## Risks / Trade-offs

- **The scaffold no longer prints a URL.** The browser viewer reports and
  opens its endpoint when development actually starts; OpenSCAD users receive
  no irrelevant browser instruction.
- **A user sees one fewer explanatory line.** The remaining command is the
  only universally valid action and owns detailed diagnostics.

## Migration Plan

No project migration is required. Reverting the one output-line removal
restores the previous text without affecting generated files.

## Open Questions

None.
