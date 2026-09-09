
.. _leaf-nodes:

==============
Modeling parts
==============

Make sure you have completed the :doc:`Quickstart <quickstart>`.
At this point, you should be able to view your project in the viewer
- either Openscad or the web viewer - and have a source code to edit.

In Solid Node, a project is organized in a tree structure, with leaf
nodes and internal nodes. **Leaf nodes** use underlying modelling
libraries, namely **SolidPython**, **CadQuery**, **build123d**,
**OpenScad** and **JScad**, to generate solid models — each leaf node is
one part.
**Internal nodes** combine children nodes into assemblies and fusions,
covered in :doc:`Combining parts <assemblies>`.

Each node implements the `render()` method. Leaf nodes return an object
of the underlying library.

This page and the next build nodes the constructor way, with an
``__init__`` that takes the part's parameters. A part can instead
*declare* its parameters in the class body and let the framework derive
identity, propagation and the command-line surface from the
declaration; see :doc:`Declaring a machine <declaring>` once the
constructor form is familiar.

There are five types of LeafNodes, each supporting one underlying
technology to create solids:

* **Solid2Node** Uses Solid Python 2, which is a python wrapper around OpenScad
* **CadQueryNode** Uses CadQuery, a pure python modeler based on OCCT
* **Build123dNode** Uses build123d, a pure python modeler based on OCCT
* **OpenScadNode** A wrapper around one OpenScad module
* **JScadNode** A wrapper around one JScad module

There is also one leaf kind that is not a modelling technology but a way
of making:

* **Build123dSheetNode** A part cut from sheet stock, authored as a 2D
  profile plus a thickness. It is the first concrete backend of the
  **SheetLeafNode** base, which owns the sheet contract — other sheet
  backends can slot in beside it.

And two whose part is not modelled here at all, but imported:

* **StlNode** A part that comes from an STL mesh — a model
  published as a mesh rather than as CAD source
* **StepNode** A part that comes from one product of a STEP
  document — a vendor part or assembly, selected by name. Unlike
  `StlNode`, it is exact: a STEP product is a boundary representation
  the moment it is read.

And one whose part does not hold still:

* **MolejoNode** A flexible part — a spring, a belt, a cable — whose
  shape follows the machine's state instead of being fixed. It is the
  first adapter of the **FlexibleNode** base, which owns the flexible
  contract.

The :doc:`Quickstart <quickstart>` starts with a Solid2Node example showing
a box with a hole. Below are the codes for the same model in each modelling
technology.

Solid2Node
==========

The starting structure created by `solid new` implements a **Solid2Node**
node, which uses **solidpython2** to create models. Open `myproject/myproject.py`:

.. code-block:: python

    from solid_node.node import Solid2Node
    from solid2 import cube, cylinder, translate

    class DemoProject(Solid2Node):

        def render(self):
            return translate(-25, -25, 0)(
                cube(50, 50, 50)
            ) - cylinder(r=10, h=100)

Rendered with ``solid export`` and embedded below:

.. solid-node:: _exports/demo_project
   :height: 360px

Note that `translate` here is a **solid2** primitive, applied inside the
model. Nodes also have a `translate()` method of their own, used to
position parts in assemblies — that one is covered in
:doc:`Animating with time <animation>`.

CadQueryNode
============

The same model can be obtained using **CadQuery**:

.. code-block:: python

    import cadquery as cq
    from solid_node.node import CadQueryNode

    class DemoProject(CadQueryNode):

        def render(self):
            wp = cq.Workplane("XY")
            cube = wp.box(50, 50, 50)
            hole = wp.workplane(offset=-50).circle(10).extrude(100)
            return cube.cut(hole)

The same box with a hole, this time rendered by CadQuery:

.. solid-node:: _exports/demo_cadquery
   :height: 360px

**TIP**: if you want to use CQ-editor, you can add `show_object` without
conflicting with Solid Node:

.. code-block:: python

    if __name__ == '__cq_main__':
        show_object(DemoProject().render())

A `CadQueryNode` may declare `linear_deflection` and `angular_deflection`
to shape how finely its `.stl` is tessellated — see
:ref:`tessellation-precision`.

Build123dNode
=============

The same model in **build123d**, which like CadQuery is a pure python
modeler over OCCT, with a different API:

.. code-block:: python

    from build123d import BuildPart, Box, Cylinder, Mode
    from solid_node.node import Build123dNode

    class DemoProject(Build123dNode):

        def render(self):
            with BuildPart() as part:
                Box(50, 50, 50)
                Cylinder(radius=10, height=100, mode=Mode.SUBTRACT)
            return part.part

And the same box with a hole, rendered by build123d:

.. solid-node:: _exports/demo_build123d
   :height: 360px

build123d offers two ways to write a model, and a node may `render()`
either. The *builder* mode above collects objects inside a context
manager; the *algebra* mode composes shapes with operators, and needs no
builder:

.. code-block:: python

    from build123d import Box, Cylinder
    from solid_node.node import Build123dNode

    class DemoProject(Build123dNode):

        def render(self):
            return Box(50, 50, 50) - Cylinder(radius=10, height=100)

Returning the builder itself rather than its `.part` also works — the
node takes the finished part — so both of these are equivalent:

.. code-block:: python

    return part.part
    return part

A leaf node is one part, so `render()` must produce a solid: a
`Part`, a `Solid`, a `Compound`, or a builder holding one. Returning a
build123d sketch or curve raises an error naming the node, rather than
failing later in the STL export.

**NOTE**: `Build123dNode` and `CadQueryNode` are both OCCT front ends
and both produce exact geometry, so they mix freely — a fusion may take
children from either, and the parts fuse exactly. Neither needs OpenScad
installed. See :doc:`Fusing parts <fusion>`.

Build123dSheetNode
==================

Some parts are not modelled, they are cut. A panel of plywood, MDF or
acrylic is a flat profile in stock of a known thickness, and what a laser
cutter needs is that profile — not a mesh of the finished part.

A **Build123dSheetNode** authors exactly that. Instead of `render()`, it
implements `profile()`, returning a build123d sketch, and declares the
`thickness` of the stock:

.. code-block:: python

    from build123d import Circle, Rectangle
    from solid_node.node import Build123dSheetNode

    class DemoProject(Build123dSheetNode):

        thickness = 6

        def profile(self):
            return Rectangle(50, 50) - Circle(10)

The same square-with-a-hole, this time as a part cut from 6 mm sheet:

.. solid-node:: _exports/demo_sheet
   :height: 360px

The node's solid is that profile extruded from the XY plane along +Z by
`thickness`, and the node derives it for you — `render()` is not an
extension point here. That is the whole point of the type: the part you
see in the viewer, the STL you test against, and the file you cut all
come from one authored profile, so they cannot drift apart. A part whose
solid and cut file were written down separately would eventually
disagree, and the cutter would faithfully cut the disagreement.

The profile contract
--------------------

A sheet part is one piece, so `profile()` must produce exactly one planar
face: a single outer boundary with any holes strictly inside it, lying on
the XY plane. Anything else raises an error naming the node and what it
produced, before any file is written — two disjoint faces (author each
piece as its own node), a solid, a curve, or a profile authored on
another plane.

`profile()` may return a `Sketch`, a bare `Face`, or the `BuildSketch`
builder itself, just as `Build123dNode` accepts a `BuildPart` or its
`.part`:

.. code-block:: python

    def profile(self):
        with BuildSketch() as sketch:
            Rectangle(50, 50)
            Circle(10, mode=Mode.SUBTRACT)
        return sketch

The thickness
-------------

`thickness` is required and must be positive; a node without one fails as
soon as it is constructed, naming itself. It can be a class attribute, as
above, or a constructor argument, in which case one class covers a panel
in two stocks:

.. code-block:: python

    class Panel(Build123dSheetNode):

        def __init__(self, thickness, **kwargs):
            super().__init__(thickness=thickness, **kwargs)

        def profile(self):
            return Rectangle(120, 80)

    thin = Panel(3)
    thick = Panel(6)

Passed as a constructor argument the thickness reaches the node's
artifact key like any other parameter, so those two are two parts with
two sets of artifacts, and neither serves the other's.

Because the thickness is a declared number rather than something buried
in the geometry, the profile can be derived from it — a t-slot that
receives a tab of the same stock is `thickness` wide plus a fit
clearance, written once.

The cut file
------------

Every sheet part writes a **DXF** of its profile beside its `.stl` and
`.brep`, under the same name, whenever a build produces them. It is an
artifact like the others: regenerated when it is stale, left alone when
it is current, and its absence alone is enough to make the build rebuild
the part.

The DXF is *nominal*: the authored profile at model scale, in
millimeters. Circles and arcs are written as arc entities at their
modelled radius rather than tessellated into polylines, so a hole reaches
the cutter as a hole and not as a polygon that would cut tight.

Deliberately not covered yet:

* **Kerf compensation.** The DXF is the nominal profile; the width a
  particular machine burns away on a particular material is not applied.
  The persisted `.brep` keeps the exact profile, so an offsetting
  exporter remains possible.
* **Importing a profile** from SVG or DXF. Profiles are authored in
  build123d.
* **Engraving and marking**, material and process metadata, and nesting
  several parts onto one sheet.

**NOTE**: a `Build123dSheetNode` is not a `Build123dNode` — its
extension point is `profile()`, not `render()` — but it is exact in the
same way, drives the same kernel, and needs no OpenScad. A fusion may
take a sheet part and a CadQuery or build123d part as children and fuse
them exactly.

Like every `ExactLeafNode`, it may declare `linear_deflection` and
`angular_deflection` to shape its `.stl` — see
:ref:`tessellation-precision`. They shape the mesh only: the DXF above
comes from the nominal profile, not from the tessellation.

.. _tessellation-precision:

Tessellation precision
======================

Every exact leaf — `CadQueryNode`, `Build123dNode`, `Build123dSheetNode`
and any other `ExactLeafNode` subclass — writes its `.stl` artifact by
tessellating its OCCT shape, and MAY declare two class attributes that
shape how finely:

.. code-block:: python

    class VendorShaft(CadQueryNode):

        angular_deflection = 0.5

        def render(self):
            return cq.importers.importStep('shaft.step')

* `linear_deflection` — the maximum distance, in millimetres, between
  the mesh and the surface it approximates. OCCT's own
  `theLinDeflection`.
* `angular_deflection` — the maximum angle, in radians, between the
  normals of two adjacent facets. OCCT's own `theAngDeflection`.

Neither is required. A node declaring neither is tessellated at
`linear_deflection = 0.1` and `angular_deflection = 0.1` — the values the
framework has always used — so an existing project's artifacts do not
change. A node may declare either attribute alone; the other keeps its
default.

Vendor STEP geometry is overwhelmingly fillets and threads, and 0.1 rad
of angular deflection over such a part costs an order of magnitude in
artifact size for surface a viewer cannot see: one measured part went
from 19.9 MB (398,184 triangles) at the default to 1.8 MB (35,776
triangles) at `angular_deflection = 0.5`. `StepNode` (:ref:`below
<step-import>`) is that vendor part's own leaf: reading the same
product through it, at the same declaration, measures 19.91 MB
(398,184 triangles) against 1.76 MB (35,240 triangles) — the same
order-of-magnitude drop, produced by one direct mesh at the declared
value rather than the premesh trick that first measured it.

Like `SheetLeafNode.thickness`, this is a class attribute, not a
constructor argument, and it is not part of the node's artifact
identity: two tessellations of one solid are one node's artifact at two
times, not two nodes. It is declared in the module defining the node
class, which the node already tracks in its source set, so **editing the
declared value rebuilds the node** the way editing any other class body
text does — nothing new to opt into, nothing to configure at the project
or run level. A declared value that is not a positive finite number
raises at the point the artifact is written, naming the node and the
attribute.

**Only the mesh changes.** The node's `.brep` artifact and the shape
`shape()` returns are identical whatever is declared — exactness is a
property of the geometry, a mesh tolerance is a property of one derived
representation of it. Everything that reads the mesh sees the declared
precision as a consequence of that, not as a separate contract:

* the viewer and the exported STL carry the declared triangles;
* under ``solid test --faceted``, every comparison is answered on the
  compared nodes' meshes, so a coarse declaration can move a clearance
  verdict that the default (exact) kernel would not move — test a
  design whose clearances are close on the exact kernel, which is
  unaffected by any declaration here;
* a node's printed-piece id is a fingerprint of its built artifact's
  content, so redeclaring precision gives the node a new piece id even
  though the part did not change.

A `FusionNode` declares precision the same way, for its own fused solid
— see :ref:`fusion-tessellation-precision`.

The faceted adapters (`Solid2Node`, `OpenScadNode`, `JScadNode`,
`StlNode`) do not carry these attributes: the framework never
tessellates their geometry, so there is nothing for a deflection to
shape. `MolejoNode`'s geometry is tessellated by molejo's own evaluator
and is outside this declaration.

OpenScadNode
============

The same model can also be obtained using an **OpenScadNode**, which is a small
python wrapper around an OpenScad module.

.. code-block:: python

    from solid_node.node import OpenScadNode

    class DemoProject(OpenScadNode):

        scad_source = 'demo.scad'

Create a file `myproject/demo.scad` with a module to create the model:

.. code-block:: openscad

    module demo() {
      difference() {
        translate([-25, -25, 0]) {
          cube([50, 50, 50]);
        }
        cylinder(r=10, h=100);
      }
    }

And the same model again, driven by the OpenScad module above:

.. solid-node:: _exports/demo_openscad
   :height: 360px

By default the module is expected to have the same name as the file
(`demo.scad` → `module demo()`); if it doesn't, set the `module_name`
property. Arguments passed to the node's constructor are forwarded to the
OpenScad module, so one `.scad` module can back several parametrized
nodes:

.. code-block:: python

    class Demo(OpenScadNode):

        scad_source = 'shapes.scad'
        module_name = 'box_with_hole'

    demo = Demo(50, hole_radius=10)


JScadNode
=========

Finally, the model can also be obtained using a **JScadNode**, which similarly
to OpenScadNode, it's a python wrapper around a JScad function.

You need the **jscad** CLI tool installed in `$PATH`, and its node dependencies
installed in the directory you run `solid` from.

.. code-block:: python

    from solid_node.node import JScadNode

    class DemoProject(JScadNode):

        jscad_source = 'demo.js'

Create a file `myproject/demo.js` with a module to create the model:

.. code-block:: javascript

    const { square, circle } = require('@jscad/modeling').primitives
    const { subtract } = require('@jscad/modeling').booleans
    const { extrudeLinear  } = require('@jscad/modeling').extrusions

    function main() {
      let outerSquare = square({size: 50 });
      let innerCircle = circle({radius: 10 });

      let shape = subtract(outerSquare, innerCircle);
      return extrudeLinear({ height: 50 }, shape);
    }

    module.exports = { main }

And the same model once more, rendered by JScad:

.. solid-node:: _exports/demo_jscad
   :height: 360px

.. _stl-import:

StlNode
=======

Plenty of worthwhile mechanical designs are published only as **STL
meshes** — a printable part, with no CAD source behind it. An
**StlNode** brings such a file into a project as an ordinary part, so it
can be assembled with parts you model, fused with them, exported and
tested like any other.

Commit the `.stl` inside your project, beside the python module that
declares it, and name it:

.. code-block:: python

    from solid_node.node import StlNode

    class Bracket(StlNode):

        stl_source = 'bracket.stl'

That is the whole declaration for a well-behaved file. `render()` is not
an extension point here — the part is the mesh.

The node does not import the file in place: it materializes
**its own artifact** from it, exactly as every other leaf produces its
own STL, and that artifact is what the assembly, the fusion, the viewer,
the export and the printed-piece inventory all see. Producing it needs
no external tool at all — not OpenScad, not a CAD kernel.

Freshness
---------

Two things make an imported part stale, and both are tracked. The
obvious one is the `.stl`: replace the file and the part rebuilds. The
less obvious one is **the python module declaring the node**, because
that is where `body` and `adjust` live — code that decides the geometry
just as much as the mesh does. Editing the wrapper (or a module it
imports a constant from) rebuilds the part too. No other external-file
leaf tracks its wrapper this way; this one has to.

Watertight, or knowingly not
----------------------------

A mesh with holes in its surface encloses nothing. It has no volume, it
cannot be fused reliably, and a slicer has to guess its way across the
gaps. So a mesh that is not watertight fails at build time, naming the
file, the selected body and the defect, and **no artifact is written**:

.. code-block:: text

    Bracket: /home/me/rc-car/parts/bracket.stl is not watertight --
    3 open edges leave the surface unclosed, so the mesh encloses no
    solid. Repair the mesh, or declare `require_watertight = False` on
    Bracket to admit it knowingly.

Nothing is repaired for you: silently filling holes would machine
geometry you did not author, and you would not know it happened. If the
mesh is known to be open and you want it anyway, say so:

.. code-block:: python

    class Bracket(StlNode):

        stl_source = 'bracket.stl'
        require_watertight = False

The flag governs *admission only*. It never changes geometry, and it
does not key artifacts.

Part packs: selecting a body
----------------------------

A single STL often holds a whole plate of parts — a print pack. Those
are separate parts, not one part, so a node says which body it is:

.. code-block:: python

    class Wheel(StlNode):

        stl_source = 'pack.stl'
        body = 0

    class Hub(StlNode):

        stl_source = 'pack.stl'
        body = 2

`body` is a 0-based index into the file's connected components, ordered
by centroid — x first, then y, then z, which reads roughly as plate
order. You do not have to guess it: a node that omits `body` on a
multi-body file fails with the pack's inventory, and the failure is the
discovery tool:

.. code-block:: text

    Wheel: /home/me/rc-car/parts/pack.stl holds more than one body, so
    it is a pack of parts and this node must say which one it is. It
    holds 3 bodies; declare `body = <index>` to select one, indexing
    this inventory:
      body 0: centroid (-10.000, 0.000, 0.000)  bounds (-11.000, -1.000, -1.000)..(-9.000, 1.000, 1.000)  volume 8.000
      body 1: centroid (5.000, 0.000, 0.000)  bounds (3.500, -1.500, -1.500)..(6.500, 1.500, 1.500)  volume 27.000
      body 2: centroid (30.000, 0.000, 0.000)  bounds (28.000, -2.000, -2.000)..(32.000, 2.000, 2.000)  volume 64.000

An out-of-range `body` fails with the same inventory. A single-body file
needs no `body` at all.

Extraction keeps the file's coordinates: a part stays where it sat on
the plate. Bringing it somewhere useful is a placement operation, or the
hook below. Watertightness is judged on the selected body, so one torn
part in a pack does not condemn the sound ones.

Correcting a mesh: the adjust hook
----------------------------------

Downloaded meshes arrive in inches, upside down, or a long way from the
origin. Corrections are **code**, not a vocabulary of constructor knobs:
implement `adjust()`, which receives the selected body as a
`trimesh <https://trimesh.org/>`_ mesh and returns the corrected one.

.. code-block:: python

    class Bracket(StlNode):

        stl_source = 'bracket.stl'

        def adjust(self, mesh):
            mesh.apply_scale(25.4)        # authored in inches
            mesh.apply_translation(-mesh.centroid)
            return mesh

The full trimesh API is available. Whatever the hook returns is what is
written into the artifact, so the viewer, the tests, a fusion and the
export all see one geometry — and it is what the watertight gate judges,
so a hook cannot slip a defect past it.

What importing a mesh costs
---------------------------

Be clear-eyed about this: **an StlNode is faceted, and it makes any
fusion containing it faceted.** A fusion of exact parts is computed by
the OCCT kernel; add an imported mesh and the fusion falls back to the
OpenScad/CGAL mesh path (see :doc:`Fusing parts <fusion>`), which
on a dense downloaded mesh can be slow — minutes, not seconds, and it
needs the `openscad` binary. That is the price of designing a piece that
fits a part someone else published, and it is usually worth paying.
Assembling imported parts without fusing them costs nothing extra.

`exact` is false for an StlNode and it has no `shape()`. This is
deliberate and settled: **mesh-only is the doctrine for imported STLs.**
A mesh is not a boundary representation, and reconstructing one from
triangles guesses at intent — where a fillet was meant, which faces were
one cylinder. The framework will not pretend otherwise. Model the part
in a CAD backend if you need it exact.

Two more things the leaf deliberately does not do. It records no
provenance — the source URL and the licence of a downloaded model are
real obligations, but they belong in your project's documentation, not
in a class attribute. And it does not take an STL set apart into an
assembly: import each part you need and assemble them with the nodes and
operations you already have.

.. _step-import:

StepNode
========

STEP is the format every CAD package and every vendor publishes. A
**StepNode** brings one product of a STEP document into a
project as an ordinary part — selected by name, corrected in code, and
admitted only if it is a solid — exactly as `StlNode` does for a mesh.

Unlike `StlNode`, this leaf is **exact**: a STEP product is a boundary
representation the moment it is read, so `StepNode` derives the same
`ExactLeafNode` base `CadQueryNode` and `Build123dNode` do. `shape()`,
the `.brep` artifact, exact fusion, the spatial assertions and
:ref:`declared tessellation precision <tessellation-precision>` all come
for free; producing its artifacts needs no external tool at all, not
even the STEP file's own reader beyond OCCT.

Commit the `.step` file inside your project, beside the python module
that declares it, and name it:

.. code-block:: python

    from solid_node.node import StepNode

    class Bracket(StepNode):

        step_source = 'vendor/bracket.step'

A file holding exactly one product needs nothing more. `render()` is
not an extension point here — the part is the document's product.

Selecting a product by name
----------------------------

A STEP document is a tree of named **products** — parts and
sub-assemblies alike, each counted once however many times the document
places it. `part` names the product this node is, as the file carries
it:

.. code-block:: python

    class Gearbox(StepNode):

        step_source = 'vendor/gearbox.step'
        part = 'Output_Shaft'

You do not always need to say. The products a node may select *by
omission* are the document's **candidates** — every product except a
root that is itself an assembly. That covers both a bare single-part
file and the far commoner file in which an exporter wraps one part in
an assembly root: either way there is one candidate, so no name is
needed. A document's assembly root is never selected by omission, so a
project that forgot to name a part can never be handed the whole
assembly by accident — it stays selectable, just never the default.

When a document has more than one candidate and `part` is unset, or
`part` names a product the document does not have, the build fails with
the document's own inventory — one line per product, naming the
discovery tool as the failure itself, exactly as `StlNode`'s pack
inventory does for a mesh:

.. code-block:: text

    Gearbox: /home/me/rc-car/vendor/gearbox.step holds 3 candidate
    products, so `part` must name one of them. It holds 4 products;
    declare `part = "<name>"` to select one, indexing this inventory:
      Housing: root assembly, 1 occurrence, 0 solids, bounds (-40.000, -25.000, 0.000)..(40.000, 25.000, 30.000), volume 0.000
      Output_Shaft: part, 1 occurrence, 1 solid, bounds (-5.000, -5.000, 0.000)..(5.000, 5.000, 60.000), volume 4712.389
      Bearing_Cap: part, 2 occurrences, 1 solid, bounds (-12.000, -12.000, 0.000)..(12.000, 12.000, 4.000), volume 1809.557
      Idler: sub-assembly, 1 occurrence, 3 solids, bounds (-8.000, -8.000, 0.000)..(8.000, 8.000, 10.000), volume 892.412

A sub-assembly is a selectable product too: naming one selects its
components at their own internal placements, which is what you want
when a vendor ships a gearbox as one shippable unit inside a bigger
file. Two distinct products sharing one name fail naming the ambiguity
and describing both, rather than guessing which was meant.

The part arrives in its own frame
----------------------------------

Whichever way it is placed in the document, a selected product's
geometry is its **own**, unplaced shape — never an occurrence's located
copy. Two occurrences of one part, however far apart, select the same
unplaced geometry; a selected sub-assembly holds its components at
their internal placements, not its parent's placement of it. Placing a
part is your assembly's job, with the same placement operations you use
on any other node — exactly as `StlNode` never bakes a pack's layout
into the body it extracts.

Correcting a part: the adjust hook
------------------------------------

Corrections are **code**, not a vocabulary of constructor knobs:
implement `adjust()`, which receives the selected product as a CadQuery
`Shape` and returns the corrected one.

.. code-block:: python

    class Bracket(StepNode):

        step_source = 'vendor/bracket.step'

        def adjust(self, shape):
            return shape.scale(25.4)        # authored in inches

Whatever the hook returns is what the artifacts hold, so `shape()`, the
`.brep`, a fusion and the export all see one geometry — and it is what
the admission gate below judges, so a hook cannot slip a defect past it.

Only a solid is admitted
--------------------------

A STEP product that carries only faces has no volume: the exact kernel
cannot fuse or intersect it, and an STL written from it would enclose
nothing. So a product that holds no solid after `adjust` fails at build
time, naming the node, the file, the part and what the geometry does
hold, and **no artifact is written**:

.. code-block:: text

    Battery: /home/me/robot/vendor/robot.step part 'Battery' holds no
    solid -- 1 shells and 6 faces. Nothing is repaired automatically;
    correct it in adjust(), for example with solids_from_faces().

There is no escape hatch here the way `require_watertight = False` is
one for `StlNode`: a face-only B-rep would break `shape()`, every
fusion and every volume assertion outright, not merely disappoint a
watertight check. If a vendor genuinely published a part as bare
surfaces, sew it **knowingly**, in your own `adjust` hook, with the
helper this module provides:

.. code-block:: python

    from solid_node.node.adapters.step import solids_from_faces

    class Battery(StepNode):

        step_source = 'vendor/robot.step'
        part = 'Battery'

        def adjust(self, shape):
            return solids_from_faces(shape, tolerance=0.05)

`solids_from_faces(shape, tolerance)` sews within `tolerance` and wraps
each resulting closed shell in a solid. It does **not** guarantee that
the shells actually close, that `tolerance` is right for this file, or
that the result is watertight or manifold — sewing is a judgement your
project makes about a file it has inspected, not a repair the framework
performs for you.

Colour from the document
--------------------------

A subclass that declares no `color` takes the part's colour from the
document — the product's own surface colour, else the colour every
occurrence of it agrees on, else none — converted to the `#RRGGBB` your
project already writes for every other node. A STEP file's colour is
stored as linear RGB; the leaf converts it to sRGB before hex-encoding
it, so a part written at a given colour in your CAD package reads back
as that colour here, rather than roughly 12% darker.

.. code-block:: python

    class Bracket(StepNode):

        step_source = 'vendor/bracket.step'

    class RecolouredBracket(Bracket):

        color = '#8b93a0'   # overrides the document's own colour

A declared `color` always wins, and — because resolving the document's
colour is what would otherwise force every build to open the STEP file,
even one whose artifacts are already current — a subclass that declares
its own never opens the document at all.

What reading a STEP file costs
---------------------------------

XCAF's read-and-transfer is the expensive part, not the leaf: **14 to
17 seconds** measured through this leaf's own cache on a 35 MB vendor
assembly of 21 products (`ReadFile` and `Transfer`, plus indexing every
product's name, kind and occurrences). So a document is read and
transferred **at most once per file per process**, cached on the file's
path and modification time; every `StepNode` selecting a part out of
the same file after the first shares that one read — measured at
**0.0003 s**, roughly five orders of magnitude cheaper — and a node
whose artifacts are already current never triggers a read at all.
Replacing the file evicts the stale entry and the next read picks up
the change.

Precision, on a real vendor part
------------------------------------

Because `StepNode` is exact, it may declare `linear_deflection` and
`angular_deflection` exactly as `CadQueryNode` and `Build123dNode` do
— see :ref:`tessellation-precision`. Vendor STEP geometry is exactly
the case that section's example is drawn from: on the real
`Output_Shaft` product this leaf originates from, the framework's
inherited default (0.1 mm / 0.1 rad — declaring neither attribute)
writes a **19.91 MB** STL of **398,184 triangles**, where declaring

.. code-block:: python

    class OutputShaft(StepNode):

        step_source = 'vendor/actuator.step'
        part = 'Output_Shaft'
        angular_deflection = 0.5

writes **1.76 MB** (**35,240 triangles**) — the same part, the same
`.brep`, about a tenth of the triangles. `StepNode` inherits the framework's
historical defaults unchanged; a project reading vendor STEP is the one
that usually wants this line.

What importing a STEP document costs
----------------------------------------

Be clear-eyed about the reverse of `StlNode`'s trade-off: **a StepNode
is exact**, so fusing it with another exact part composes on the OCCT
kernel, not through OpenSCAD/CGAL — no external renderer needed at all.
What it does not do is read the document's placements: a selected
product always arrives in its own, unplaced frame, so an assembly of
several `StepNode` leaves is placed with your project's own placement
operations, the same way `StlNode`'s pack bodies are.

That placement can come from the document itself. :ref:`solid
import-step <import-step>` reads a document's whole assembly
structure — every occurrence, walked through nested sub-assemblies,
decomposed exactly into the ``rotate``/``translate`` pair above — and
scaffolds ``parts.py`` and ``assembly.py`` from it: one `StepNode`
subclass per part, one `AssemblyNode` per assembly product, placed at
the document's own transforms. It is a one-shot command, not part of
this leaf: it writes project-owned source you then edit, and never
touches a build.

.. _flexible-parts:

MolejoNode
==========

Every leaf so far promises a part that holds still: whatever the machine
does, the geometry is the same solid moved around. Plenty of parts do not
work that way. A valve spring is compressed by the cam that opens the
valve, a timing belt follows the idler that tensions it, a cable loom is
dragged along by the carriage it feeds. Their *shape*, not just their
placement, is a function of where the machine is.

A **MolejoNode** is that kind of part. It is a **flexible** leaf: instead
of returning a finished solid, `render()` returns a swept shape —  a
closed profile carried along a path — described analytically with
`molejo <https://molejo.readthedocs.io>`_, with the moving
dimensions left as *parameters*, fed through ports declared from
``solid_node.motion.ports``, the module that answers what moves and
what drives what:

.. code-block:: python

    from molejo import Circle, Helix, P, Shape
    from solid_node.node import MolejoNode
    from solid_node.motion.ports import TranslationalPort

    class ValveSpring(MolejoNode):

        height = TranslationalPort(unit='mm')

        def render(self):
            return Shape(
                profile=Circle(radius=2.0),
                path=[Helix(radius=14.0, turns=6.5, height=P.height)],
                path_samples=240,
                profile_samples=16,
            )

`P.height` is molejo's way of saying "this dimension is a parameter named
`height`". Circle radius, coil radius and turn count are written down as
numbers, because they describe the spring you would buy; the free height
is left open, because that is the thing the engine moves.

Mind where the shape sits: molejo paths start at the node's origin, so a
helix *winds about an axis offset by its coil radius* — the wire starts
at the origin and the coil's centreline runs through ``(-radius, 0)``.
Place the node (or author the path) with that in mind; the v8-engine
valve springs found this the hard way when a spring drawn "at" a valve
stem coiled 14 mm beside it.

Parameters come from ports
--------------------------

A flexible part never receives its moving values through its constructor.
It **declares one port per parameter**, and the parent assembly connects
them, exactly as it connects any other port:

.. code-block:: python

    from solid_node.node import AssemblyNode
    from solid_node.simulation import Driver

    FREE_HEIGHT = 46.8

    class Valvetrain(AssemblyNode):

        lift = Driver(default=0.0, range=(0.0, 12.0), unit='mm')

        def __init__(self):
            self.retainer = Retainer()
            self.spring = ValveSpring()
            super().__init__()

        def render(self):
            self.connect(FREE_HEIGHT - self.lift, self.spring.height)
            self.retainer.translate([0, 0, FREE_HEIGHT - self.lift])
            return [self.retainer, self.spring]

The port's attribute name **is** the parameter's name, and the two sets
must match exactly. A shape parameter with no port would be fed by
nothing; a port no parameter reads would bind a value no geometry
follows. Either one fails naming the node, the offending name and both
sets, before any geometry is produced. A port nobody connected fails too,
naming the node and the port — it is never quietly defaulted.

Values through the constructor are the one thing that would not work.
Constructor arguments key a node's build artifacts, so a value that
changes every frame would create a new part every frame. Ports keep the
identity structural: two `ValveSpring()` instances are one part, whatever
each is currently doing. Dimensions that genuinely describe a *different*
spring — a thicker wire, another coil count — do belong in the
constructor, for the same reason.

In the viewer
-------------

A flexible part travels into the viewer as its **shape spec**, not as a
mesh, and the browser evaluates it. Move the driver that feeds a port —
with the slider the viewer builds for it, or from your own host code —
and the spring re-computes its geometry on the frames the value actually
changed, in the buffers it already has. See :doc:`Driving a machine
<driving>`, where ports and drivers are introduced. A document holding
a flexible part declares schema version 3 rather than 2, which is what
tells a viewer it must evaluate shape specs — see
:doc:`Embedding models <embedding>`.

OpenScad has no equivalent, so it gets a snapshot: the part is evaluated
at its current state and written as an ordinary STL that the assembled
`.scad` imports, which keeps the document complete enough for the
OpenScad GUI to open any project. It is a still, not an animation — the
same treatment every other machine input already gets there.

Exact, with an honest tolerance
-------------------------------

A flexible part is **exact**: `shape()` gives the OCCT solid for the
state currently bound, so a spring at a given lift answers interference
and fit questions on real boundary geometry rather than on triangles, and
mixes with CadQuery and build123d parts in the usual way (see
:doc:`Test-driven CAD <testing>`).

Where the sweep has no closed form — a helix, a spline — the solid is
approximated, and the node says so: `shape_tolerance` reports the
approximation it was built to (`0.0` when every surface is analytic).
Nothing pretends a swept helix is exact to the last decimal.

What a flexible part is not
---------------------------

It cannot be **fused**. A fusion makes one printed solid out of its
children, and a part that deforms is not part of one — the fusion refuses
it, naming both nodes. For the same reason a flexible part is not a
printed piece and never appears in the pieces inventory: you buy a
spring, you do not print it. And it has no `time` of its own, like every
other leaf: its shape follows the values its parent binds, and nothing
else.

Where molejo comes from
-----------------------

`molejo <https://molejo.readthedocs.io>`_ is an ordinary dependency of
solid-node — installed with it from `PyPI
<https://pypi.org/project/molejo/>`_, with the ``brep`` extra that
provides the exact geometry above. The two are pinned by minor
version, because a molejo minor carries the shape-spec version it
implements and the documents this framework writes name that version.

.. _fn-property:

Model resolution: the fn property
=================================

Internally, every part becomes an STL file, and STLs are made of
triangles: circles and holes are approximated by polygons. In
OpenScad-derived nodes — `Solid2Node` and `OpenScadNode` — the number of
segments in that approximation is controlled by OpenScad's `$fn`
variable, and the default is coarse: a small hole can come out as a
hexagon.

Set the `fn` property on the node to raise the resolution:

.. code-block:: python

    class Pointer(Solid2Node):

        fn = 256

The OCCT-backed leaves — `CadQueryNode`, `Build123dNode`, the sheet
leaves and `MolejoNode` — are not affected: they export STL files with
high precision on their own.

This is mostly invisible while modeling, but it matters for fits: a
hexagonal "hole" is tighter than the circle it approximates. It comes
back in :doc:`Test-driven CAD <testing>`, where a pin fails to run free
in a low-resolution hole.

Colors
======

Any node can set a `color`, as a hex RGB string, which is used by the
viewer and carried into exports:

.. code-block:: python

    class Pointer(Solid2Node):

        color = '#cc4444'
