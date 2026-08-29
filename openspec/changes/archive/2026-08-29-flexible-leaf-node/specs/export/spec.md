## MODIFIED Requirements

### Requirement: Manifest contract

The manifest SHALL retain the document name `manifest.json` and SHALL declare
`format: "solid-node-export"`, `animation: {fps, frames}`, a
`drivers` table, an `instructions` table, and a
`root` tree with the same observable schema and child-name behavior as the
normal-build `viewer.json`. A rigid node SHALL emit one `model` reference and
stop recursion; a non-rigid node whose render result is a list or tuple SHALL
recurse into its children; a flexible leaf SHALL emit one `flexible` object
and stop recursion. Each node SHALL carry `name`, `type`, `color`,
`mtime`, and its operations as raw unevaluated expression strings so `$t`
animation is preserved verbatim. A rigid model reference SHALL remain rooted
beneath the export's `models/` directory and SHALL resolve to a copied artifact
so the export remains portable and self-contained. Changes to the shared tree
shape or operation serialization are breaking and MUST bump `version` and
update every producer and consumer of the shared schema together.

The document SHALL declare `version: 3` when the serialized tree contains at
least one flexible leaf, and `version: 2` otherwise, so a document without
flexible content stays byte-compatible with existing consumers and an old
consumer refuses only what it genuinely cannot render. Consumers SHALL accept
both versions.

A flexible leaf's `flexible` object SHALL carry the evaluating technology
(`tech`), the embedded shape spec verbatim as the adapter serialized it
(`spec`), and a `params` table mapping each of the leaf's parameter names to
its bound expression string. `params` expressions SHALL be produced in the
same symbolic driver mode as operation expressions and carry the same
verbatim guarantee: a numeric snapshot bound before serialization never bakes
a constant into them. Every qualified id referenced by a `params` expression
SHALL appear in the `drivers` table. A flexible leaf SHALL contribute no
`models/` entry and no piece: its geometry travels as the spec. Serializing a
flexible leaf with an unbound parameter port SHALL fail naming the node and
the port.

The `drivers` table SHALL map each qualified driver id in the serialized
tree to its declared metadata — `default`, `range`, `unit`, `dtype`, and
`scale` — verbatim from the declaration, with `range` carried as
presentation metadata only, never a clamp. Operation expression strings
MAY reference qualified driver ids, and the producer SHALL preserve them
verbatim under the same guarantee as `$t`: the document is serialized in
symbolic driver mode, with every declared driver bound to its qualified
symbolic token (and animation time symbolic), regardless of any numeric
snapshot bound before serialization; the producer SHALL restore the
node's prior binding discipline afterwards exactly as it already does
for animation time. Every qualified id referenced by any serialized
expression SHALL appear in the `drivers` table. A tree declaring no
drivers SHALL serialize an empty `drivers` table, and consumers SHALL
render such a document exactly as they rendered `version: 1`. A consumer
SHALL either evaluate driver-referencing expressions or fail loudly on a
non-empty `drivers` table rather than render a wrong pose. The OpenSCAD
`.scad` output path is unchanged by this contract: it substitutes bound
driver values numerically and keeps `$t` symbolic. A flexible leaf whose
port is bound over `$t` contributes no geometry to that output (the
`flexible-parts` capability): the surrounding document still animates in
the OpenSCAD GUI, and the flexible part is simply absent there rather
than frozen at an invented instant.

The `instructions` table SHALL map each declared instruction's qualified
name (the declaring node's instance path joined with the instruction
name; root-declared instructions keep bare names) to its design-unit
targets keyed by qualified driver id and its duration, verbatim from the
declarations the tree-walk enumeration finds. The `instructions` key is
additive within `version: 2`: a document carrying instructions
necessarily carries a non-empty `drivers` table, which consumers without
driver evaluation already refuse loudly, so no consumer can misread the
added key. A tree declaring no instructions SHALL serialize an empty
`instructions` table.

Preserving `$t` verbatim SHALL be a guarantee of the export producer, not an
obligation on its caller. Export SHALL return the node to symbolic animation
time before serializing it, so a node that was keyframed at any time before
export still yields a manifest whose operations are `$t` expressions rather
than the constants that keyframe computed. Export SHALL leave the node in
symbolic time afterwards and SHALL NOT restore a previously set keyframe; a
caller needing a numeric pose again applies `set_keyframe` itself. A static
presentation of an exported document is obtained from the widget's `?t=` and
`?autoplay=0` options, not by publishing a frozen document.

#### Scenario: Animated operations survive export

- **WHEN** an assembly's rotation is `$t * 360`
- **THEN** the manifest stores that expression as a string, not a baked
  numeric pose

#### Scenario: Animated operations survive export from a keyframed node

- **WHEN** a caller applies `set_keyframe(0.25)` to an assembly whose rotation
  is `$t * 360` and then exports that same node
- **THEN** the manifest still stores the `$t` expression, not the constant the
  keyframe computed

#### Scenario: Driver expressions survive export from a stepped node

- **WHEN** an assembly whose pulley angle derives from a declared driver
  is bound to a numeric snapshot by a simulation and then exported
- **THEN** the manifest stores the expression referencing the qualified
  driver id (e.g. `(x_axis.motor * 0.1125)`), not the constant the
  snapshot computed, and the `drivers` table carries `x_axis.motor`
  with its declared default, range, unit, dtype, and scale

#### Scenario: A flexible leaf travels as its spec

- **WHEN** an assembly holding a molejo spring whose `height` port derives
  from a declared driver is exported
- **THEN** the manifest's spring node carries `flexible` with `tech`,
  the embedded spec, and a `height` expression referencing the qualified
  driver id; the document declares `version: 3`; the referenced id appears
  in the `drivers` table; and `models/` contains no entry for the spring

#### Scenario: Flexible expressions survive export from a snapshot-bound tree

- **WHEN** the same tree is bound to a numeric snapshot by a simulation and
  then exported
- **THEN** the spring's `params` still carry expressions, not the constants
  the snapshot computed

#### Scenario: A flexible-free document keeps its version

- **WHEN** a tree containing no flexible leaf is exported
- **THEN** the document declares `version: 2` and is exactly what the
  producer emitted before flexible parts existed

#### Scenario: Sibling instances serialize distinct ids

- **WHEN** two instances of one `motor`-declaring class are exported
  under one parent
- **THEN** their operations reference `x_axis.motor` and
  `y_axis.motor` respectively and both ids appear in the `drivers`
  table

#### Scenario: Declared instructions are published qualified

- **WHEN** both axis instances of one class declare
  `'Home': Instruction({'motor': 0.0}, duration=2.0)` and the tree is
  exported
- **THEN** the `instructions` table carries `x_axis.Home` and
  `y_axis.Home`, each with targets keyed `x_axis.motor` /
  `y_axis.motor` in design units and duration 2.0

#### Scenario: A driverless document degrades to prior behavior

- **WHEN** a tree declaring no drivers is exported
- **THEN** the document declares `version: 2` with empty `drivers` and
  `instructions` tables and existing consumers render it exactly as a
  `version: 1` document

#### Scenario: Export leaves the node in symbolic time

- **WHEN** a keyframed node is exported
- **THEN** the node's animation time afterwards is symbolic `$t`, and applying
  `set_keyframe` again resolves its mesh numerically as before

#### Scenario: Linked names and additive metadata survive export

- **WHEN** an assembly returns children held by named attributes or list/tuple
  attributes
- **THEN** `manifest.json` uses their established linked names and includes
  each node's `mtime`, matching the shared node fields emitted in `viewer.json`

#### Scenario: A rendered child is recreated and rebound

- **WHEN** an assembly recreates a logical child and stores it on an attribute
  during each render
- **THEN** `manifest.json` and normal-build `viewer.json` publish the same
  attribute-derived child name

#### Scenario: A rendered child is reachable only through internal children state

- **WHEN** a child is reachable only through the parent's public `children`
  list when document serialization links it
- **THEN** both documents publish its established `children-<index>` name

#### Scenario: A rendered child has no parent attribute

- **WHEN** a child is not referenced by any parent attribute
- **THEN** its existing class-name fallback remains unchanged

#### Scenario: Export paths remain portable

- **WHEN** a rigid node is exported
- **THEN** its manifest model path is rooted beneath `models/` and resolves to
  the copied deduplicated STL within the export directory
