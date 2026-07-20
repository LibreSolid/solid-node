## Context

`solid develop` currently supervises a series of short-lived builders and
viewer processes.  A builder either starts one pending STL render and exits,
or, once the tree is current, waits for a source change.  This gives the
development viewer a reload boundary, but the CLI has no corresponding
one-shot command or stable external notification boundary.

STORY-005 in solid-node-shop is the originating requirement.  Its floor runs
one conventional-model build before opening, while the machinist separately
runs `solid develop`.  The floor reads the existing normal project build
directory; it must never import the project's Python model or own the
development process.  The existing static export/widget and web viewer remain
separate, already-public consumers of solid-node artifacts.

## Goals / Non-Goals

**Goals:**

- Reuse the command-first path grammar and the same node/build pipeline for a
  one-shot build and a development build.
- Make a successful complete build an observable publication boundary.
- Keep the normal project build directory as the only artifact location.
- Offer a narrow, best-effort notification seam for a local external consumer
  without adding a framework broker, platform service, or callback payload.
- Retain the current development behavior for build failures: watch continues
  on reload errors while the latest successful artifacts stay usable.

**Non-Goals:**

- Change the widget, export format, NodeAPI, browser reload protocol, or floor
  implementation.
- Add a callback to `solid build`, callbacks for failures, retries, delivery
  acknowledgements, or a general event protocol.
- Support callbacks in OpenSCAD or web-development viewer modes.
- Add an output-directory option or alter `SOLID_BUILD_DIR` semantics.
- Surface transient development errors to an external floor consumer.

## Decisions

### Add a one-shot command over the existing build pipeline

`Build` joins the existing duck-typed CLI command registry and accepts the
same required node path, including directory-to-`__init__.py` resolution, as
`Develop`.  It drives ordinary builder passes until the complete tree is
current, then exits 0.  It starts neither a watcher nor a viewer.

Reusing `Develop` with an option was rejected because its process and viewer
lifetime are explicitly long-lived.  Reimplementing node loading or STL
generation for the command was rejected because it would fork the framework's
build semantics.

### Treat a fully current build as the publication boundary

The builder/lifecycle seam will expose an explicit successful-completion
result, distinct from a pass that rendered work and must run again, a source
change, or a build error.  Build artifacts are prepared so a failed attempt
does not replace the latest complete successful project-build state.  Only
after the complete tree has been published is the build considered successful
to `Build` or an external notification consumer.

This replaces inferring readiness from child process exits, which is unsound
because an existing builder exits after individual render work as well as for
watch-loop changes.  Publishing individual partial results was rejected
because it would permit an external reader to see a mixed model.

### Limit callback delivery to normal-web development sessions

`Develop` accepts `--callback URL` only when using its default web mode.  The
completed builder pass issues an HTTP POST with no request body to the exact
provided URL after artifact publication.  It does this for the initial ready
build and every later ready rebuild.  The framework treats URL query text as
opaque; callers can use it as a local capability.

The callback uses a short bounded timeout, logs any transport or non-success
response failure, and continues watching without retrying.  It is not sent
after failed builds.  A callback in the OpenSCAD or web-development modes is
rejected at argument validation, rather than silently producing a different
event timing.

Polling, a framework-owned broker, and payload/state-delta notifications were
rejected: each expands the framework into platform orchestration and is
unnecessary when the consumer reads the normal completed artifacts.

### Distinguish a missing model from other initial failures

When the resolved node path does not exist, `solid build` emits a concise
diagnostic and exits 66, documented as `MODEL_NOT_FOUND`.  Other load,
assemble, or render failures retain generic non-zero failure behavior.  The
distinct code lets a caller report that a project has no conventional model
yet without parsing diagnostics.

## Risks / Trade-offs

- [Existing builder exits overload several lifecycle meanings] → introduce
  tested completion/status ownership before adding the command or callback.
- [Staging/publishing changes artifact lifetime] → verify successful builds,
  failed subsequent builds, and normal development reloads against the normal
  build directory.
- [An unavailable local callback delays a development loop] → bound delivery
  with a short timeout and make it best-effort.
- [A callback URL reaches an unintended listener] → preserve the supplied URL
  exactly, allowing the caller to carry a per-run unguessable capability; the
  framework does not invent or persist credentials.

## Migration Plan

The change only adds a command and optional development flag; existing
`develop`, `export`, and build-directory callers remain compatible.  Document
the new command and status 66.  Rollback is a normal revert; no stored project
state or protocol migration is required.

## Open Questions

None.  HTTP POST is an implementation detail of the narrow callback, not a
separate configurable transport contract.
