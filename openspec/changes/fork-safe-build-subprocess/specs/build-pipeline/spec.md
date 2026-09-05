## ADDED Requirements

### Requirement: Build subprocesses are isolated from the parent process

Every subprocess a build command starts to load a node, render an artifact, or
serve a viewer SHALL begin from a fresh interpreter that inherits none of the
parent process's native runtime state — in particular no thread pool, worker
team, or lock belonging to a native library the parent initialised.

A build SHALL therefore always reach an outcome: it publishes its artifacts, or
it fails with a reported error and a non-zero exit. It SHALL NOT stop
indefinitely without progress. What the parent process imported, and whether
that import ran geometry, SHALL NOT change whether a build completes.

Because a subprocess no longer inherits the parent's memory, what a build
command passes to one SHALL be limited to values that survive being reconstructed
in a fresh interpreter.

#### Scenario: The parent has already run geometry

- **WHEN** `solid build` resolves a model whose import runs geometry, leaving
  native worker threads live in the command's own process, and then starts its
  builder subprocess
- **THEN** the subprocess renders and publishes the model and the command exits
  0, rather than blocking forever on a worker team the parent left behind

#### Scenario: A cold build directory for a mesh-engine project

- **WHEN** `solid build` runs against a project whose nodes render through the
  in-process mesh engine and whose build directory holds no current artifacts,
  so every artifact must be tessellated
- **THEN** each artifact is rendered and published and the command exits 0

#### Scenario: The watch loop respawns a builder

- **WHEN** `solid develop` respawns its builder after a watched source file
  changes
- **THEN** the new builder starts from a fresh interpreter, rebuilds from the
  edited source, and the loop continues
