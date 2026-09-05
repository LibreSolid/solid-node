# ADR-073: Named Project Models and Per-Model Build Directories

**Status:** Accepted
**Date:** 2026-09-05
**Amends:**
- [ADR-005: Path-Based Dynamic Module Loading](./ADR-005-path-based-dynamic-module-loading.md)
- [ADR-024: Command-First CLI Grammar and Duck-Typed Command Registry](./ADR-024-command-first-cli-grammar-and-duck-typed-command-registry.md)
- [ADR-038: Per-Artifact Atomic Build Publication](./ADR-038-per-artifact-atomic-build-publication.md)
**Depends on:**
- [ADR-067: Fresh-Interpreter Build Subprocesses](./ADR-067-fresh-interpreter-build-subprocesses.md)

## Context and Problem Statement

A project was one manifest naming one model, and one build directory whose
`viewer.json` publication swept every artifact it did not name (ADR-038).
Every node-scoped command fell back to that one model, and the build lock
was derived from that one directory.

That is the right shape for a machine and the wrong shape for a family of
them. `3DPrintedClocks` is one repository holding one shared `clocks` library
at its root and, under `design/`, one solid-node model per clock. The clocks
cannot become one repository each: the loader anchors the import path on the
manifest's directory and the library sits above every clock. And they cannot
share one build directory: building the second clock replaced the first's
publication and deleted its STLs. The framework had no way to say "this
project has these models", nothing to list them, and nothing to build them
all.

## Decision Drivers

- A project without several models must not change at all: neither the
  meaning of its manifest nor the paths in its build directory.
- Publishing one model must never disturb another's artifacts, document,
  errors or lock.
- A model must be addressable by a name a person would type and a host
  would display.
- A host must be able to list a project's models without importing project
  code.
- One broken model must not hide the others from a walk over all of them.

## Considered Options

1. **A `models` table of names, per-model directories under the build
   root.** Chosen.
2. **A list of references without names.** Nothing to call a model by and
   nothing to name a directory after.
3. **One flat directory with one document per model
   (`<name>.viewer.json`).** The sweep would have to union every model's
   document, the lock would stay shared, and every consumer of "the build
   directory's `viewer.json`" would have to learn the naming.
4. **A sibling root per model (`_build-<name>`).** Scatters a project's
   artifacts across its root and the gitignore rule.
5. **Nested manifests, one per model directory.** Moves the project root,
   and with it the import path, away from the shared library.

## Decision

A manifest may declare several models by name:

```toml
[tool.solid-node]
model = "wall_clock_01"

[tool.solid-node.models]
wall_clock_01 = "design.wall_clock_01.clock:WallClock01"
wall_clock_02 = "design.wall_clock_02.clock:WallClock02"
```

- The table is the only signal that a project has several models. Beside
  it, `model` names the default by its key and must equal one; without it
  the project has no default and a command given no reference lists the
  names rather than guessing. A manifest without the table keeps `model` as
  a reference, unchanged.
- A name is one word (`[A-Za-z_][A-Za-z0-9_-]*`), so it can never be read as
  a qualifier or a path, and it may not equal a directory at the project
  root, because artifacts mirror the source tree into the same place.
- A declared name is a fourth reference spelling, looked up before the
  module-qualifier reading; it therefore shadows a bare top-level module of
  the same spelling, which the project chose when it named the model.
- A declared model owns `<build root>/<name>/`, where the build root is what
  `$SOLID_BUILD_DIR` resolved to before. Everything that is per build
  directory — `viewer.json`, `errors.json`, the lock, the sweep, the
  symlink migration, git exclusion — is unchanged and now happens per
  model. A sub-node reference still builds in the build root; the root's
  sweep does not descend into a model's directory and spares `.lock` files,
  since a model's lock (`<build root>/<name>.lock`) lies inside the root.
- Each command selects before it loads: a selection step turns a name, or
  the default, into the concrete reference and the directory it owns, and
  anchors that directory for the process and, through `SOLID_BUILD_DIR`, for
  every fresh interpreter it starts (ADR-067). The anchor is valid only
  while the environment carries it, so a process that restores its
  environment — the test suite — is not left pointing at a directory that
  is gone.
- `solid models` lists the models from the manifest and the directories
  alone: `failed` when a directory holds `errors.json`, `published` when it
  holds `viewer.json`, `unbuilt` otherwise, with `--json` for hosts. A
  single-model project lists one entry with a null name.
- `solid build --all` and `solid test --all` walk the models in declaration
  order, sequentially, and never stop at a failing model — including one
  whose module does not import, which is recorded in that model's
  `errors.json` — exiting nonzero when any failed.

## Consequences

- A single-model project behaves and lays out its build directory exactly
  as before.
- A multi-model project has no project-level publication: `_build/viewer.json`
  belongs to whatever sub-node was last built there, and a host reads
  `solid models --json` to find each model's directory.
- Two models that contain the same node at the same parameters render it
  twice, once per directory. Sharing artifacts across directories is left
  open.
- Per-model locks permit concurrent builds of different models; the walks
  here are sequential, and a `--jobs` option is left open.
- Verifying the per-model lock exposed that the ADR-032 layout migration
  in `prepare_build_dir` had been unlinking the held lock file on every
  build — `<build dir>.lock` spells like the versioned siblings it removes —
  so mutual exclusion silently lapsed between one build's preparation and
  the next acquisition. The cleanup now skips the lock path, for the flat
  root as much as for a model's directory.
- Originating project: `projects/3DPrintedClocks`. OpenSpec change:
  `named-project-models`.
