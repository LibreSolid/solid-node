## MODIFIED Requirements

### Requirement: Normalized animation time

The system SHALL expose animation exclusively on `AssemblyNode` via a `time`
property normalized to 0..1: symbolic OpenSCAD `$t` in the build/viewer path,
and a plain float once `set_keyframe(time)` is set. `set_keyframe` SHALL
recurse into rendered children so nested assemblies also render numerically.
All assemblies share the single `$t` timeline; users scale in code.

Keyframed time SHALL be reversible. `clear_keyframe()` SHALL drop the fixed
time, re-render, and recurse into rendered children exactly as `set_keyframe`
does, returning the subtree to symbolic `$t`. Because an assembly's re-render
sweeps only the operations it drove, the operations a cleared subtree carries
SHALL be the same symbolic expressions a never-keyframed render produces —
including expressions built through `solid_node.math` — while static placement
applied outside any assembly render SHALL survive unchanged and operations SHALL
NOT accumulate across repeated `set_keyframe`/`clear_keyframe` cycles.
`clear_keyframe()` SHALL be a no-op on non-animated nodes, mirroring
`set_keyframe`.

Both `set_keyframe` and `clear_keyframe` SHALL tolerate an assembly whose
`render()` returns a value that is not a list or tuple, recursing into no
children rather than raising, matching the partial-node tolerance the document
serializer already has.

#### Scenario: Keyframe freezes a frame

- **WHEN** `set_keyframe(0.25)` is called on a root assembly containing a
  nested assembly
- **THEN** both assemblies render with `time == 0.25` as a float and
  `node.mesh` resolves numerically

#### Scenario: Clearing a keyframe restores symbolic time

- **WHEN** `set_keyframe(0.5)` is called on a root assembly containing a nested
  assembly and `clear_keyframe()` is then called on the root
- **THEN** both assemblies report symbolic `$t` for `time`, and the nested
  child's operations serialize to the same `$t` expression strings a
  never-keyframed render produces

#### Scenario: Clearing restores a non-linear symbolic expression

- **WHEN** an assembly whose rotation is built with `solid_node.math` (for
  example `asin((r/l) * sin(360 * $t))`) is keyframed and then cleared
- **THEN** its operation serializes to the deferred OpenSCAD expression string,
  identical to the one a fresh render produces, not to the numeric value the
  keyframe computed

#### Scenario: Keyframe cycles do not accumulate operations

- **WHEN** `set_keyframe` and `clear_keyframe` are alternated several times on
  the same assembly
- **THEN** each driven child holds exactly the operations one render applies,
  and static placement applied outside any assembly render is still present

#### Scenario: A non-list render result is tolerated

- **WHEN** `set_keyframe` or `clear_keyframe` is called on an assembly whose
  `render()` returns a single node rather than a list or tuple
- **THEN** the call completes without raising and recurses into no children
