## Context

`solid build` publishes `viewer.json` atomically with `_build`, allowing a
static host to render the raw model tree without importing the project. The
tree contains raw OpenSCAD operations, including `$t`, but no cadence. The
established static widget requires `fps` and `frames` to drive its timeline.

## Goals / Non-Goals

**Goals:**

- Publish the framework's established animation cadence with every build
  snapshot.
- Keep the complete snapshot and its cadence inside the same atomic build
  publication.
- Preserve source-free consumption by browser hosts such as Floor.

**Non-Goals:**

- Change the project animation defaults or introduce a new user-facing CLI
  option.
- Change `solid export`, its manifest, or its widget.
- Serve a project model from the framework after build publication.

## Decisions

### Snapshot metadata mirrors the established viewer cadence

The builder will write `animation: {fps: 30, frames: 360}` alongside the
existing snapshot version and root. These are the cadence values already used
by the development viewer. Publishing them makes the build snapshot sufficient
for a browser host to reproduce that viewer's timing, rather than forcing a
host to invent a cycle duration or inspect project code.

Changing the snapshot structure without a version bump was rejected. The
snapshot already declares a version, and this additive v1 metadata is required
for the originating Floor consumer; a future incompatible shape must increment
the version.

### Metadata is published only with the completed tree

The builder writes animation metadata into the staging `viewer.json` before
the existing atomic directory publication. Consumers therefore see either the
previous complete snapshot or a new tree and its cadence together.

Writing a separate timing file was rejected because it could become out of
sync with the snapshot during replacement and gives hosts two publication
inputs.

## Risks / Trade-offs

- [A future project needs a different cadence] → Add an explicit framework
  animation contract in a later versioned snapshot change rather than have
  Floor infer one.
- [Existing snapshot consumers expect only root] → The field is additive and
  existing consumers can ignore it; build and snapshot-backed-viewer tests
  cover the full serialized contract.
