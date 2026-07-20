# ADR-030: Complete-build publication boundary

- **Status:** Accepted
- **Date:** 2026-07-20
- **Subsystem:** BUILD
- **Change:** `build-command-develop-callback`

## Context

The original builder process exited both after an individual STL render and
after a watched source change. That made a child process exit code unsuitable
as an external definition of build readiness. It also rendered directly into
the public build directory, so a later failed rebuild could leave a consumer
with a partial replacement of the last usable model.

The framework now needs a one-shot build command and a development-ready
callback. Both require one observable point at which a complete ordinary model
is available to an external local consumer.

## Decision

Build supervisors use explicit lifecycle outcomes: an intermediate render,
the complete current model, a source change, and a failure are distinct. A
build session renders into a private sibling candidate directory, seeded from
the last published build. It replaces the normal build directory only after
the candidate is fully current. A failed candidate is discarded.

`solid build` uses those outcomes to run the ordinary pipeline once without a
watcher or viewer. `solid develop` uses the same boundary before sending its
best-effort callback, then continues its existing watch loop. The public build
directory and `SOLID_BUILD_DIR` remain the consumer-facing location.

## Alternatives considered

- **Use child exit 0 as readiness.** Rejected because it also represents
  intermediate render work and watched source changes.
- **Render directly into the public directory and restore on failure.**
  Rejected because readers can observe a mixed artifact set while a build is
  in progress.
- **Introduce a broker or separate event service.** Rejected because the
  consumer can read the already-public artifacts and only needs a narrow local
  notification seam.

## Consequences

- A successful build is a complete publication, not merely one completed STL.
- Failed rebuilds retain the last successful artifact tree.
- Supervisors own lifecycle-status interpretation; direct legacy `Builder`
  callers retain their existing successful exit mapping.
- Candidate and previous directories exist briefly beside the build directory
  during publication and are implementation-private.
