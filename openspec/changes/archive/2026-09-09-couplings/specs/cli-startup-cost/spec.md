## MODIFIED Requirements

### Requirement: The motion package is cheap to import

The system SHALL keep `solid_node.motion` free of geometry. Importing
`solid_node.motion` SHALL import no `solid_node` module other than the
top-level `solid_node` package itself — its parent, which the import
machinery necessarily creates and whose `__init__` carries version
metadata only — and no CAD backend.
Importing `solid_node.motion.ports` SHALL import no
CAD backend and no exact-geometry stack: it reaches into
`solid_node.node` only for the render-phase reporter, and the node
classes it needs to validate and read a time base SHALL be imported
inside the methods that need them, never at module scope.

Importing `solid_node.motion.joints` or `solid_node.motion.couplings`
SHALL cost what importing `solid_node.motion.ports` costs and no more:
a joint owns a port as its coordinate and a relation relates two ports,
so the ports module is imported at their module scope, and everything
else they need from the node package — the tree, the operations, the
lifecycle phase, the declaring namespace, the driver declaration —
SHALL be imported inside the methods that need them, never at module
scope. Importing either SHALL import no CAD backend and no
exact-geometry stack.

Neither `solid_node.motion.ports` nor any module beneath
`solid_node.motion` SHALL be imported as a side effect of importing
`solid_node.motion`.

#### Scenario: The package itself costs nothing

- **WHEN** `solid_node.motion` is imported in a fresh interpreter
- **THEN** no `solid_node` module other than the top-level `solid_node`
  package itself, and no CAD backend, appears among the process's
  imported modules

#### Scenario: Ports pull no geometry backend

- **WHEN** `solid_node.motion.ports` is imported in a fresh interpreter
- **THEN** `cadquery`, the boundary-representation kernel and the STEP
  reader are absent from the process's imported modules

#### Scenario: Joints and couplings cost what ports cost

- **WHEN** `solid_node.motion.joints` is imported in a fresh
  interpreter, and `solid_node.motion.couplings` in another, and each
  one's imported `solid_node` modules are compared with those of an
  interpreter that imported only `solid_node.motion.ports`
- **THEN** each set is the same but for the module itself, and
  `cadquery`, the boundary-representation kernel and the STEP reader
  are absent from all three

#### Scenario: Either import order works

- **WHEN** `solid_node.motion.ports` is imported first in one fresh
  interpreter and `solid_node.node.internal` is imported first in
  another
- **THEN** both interpreters complete the import, and a node class
  declaring a port behaves identically in each
