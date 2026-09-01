Why Solid Node
==============

A machine, not a mesh
---------------------

Most code-CAD tools answer one question: what shape is this part? A
machine raises more. Where does the carriage sit when the axis is
homed? How tall is the valve spring at full lift? Does the assembly
stand up under gravity, and does anything collide along a move? Solid
Node is built around those questions. A model is a tree of nodes whose
root is a *machine*: it declares its inputs as named **drivers**
(``x = Driver(default=0, range=(0, 200), unit='mm')``), reads them in
ordinary Python expressions, and publishes them — so the browser
viewer grows sliders and buttons a reader can drive, a simulation can
step the machine deterministically, and a test can assert what happens
along the way. Parts do not have to be rigid, either: a spring, a belt
or a filament path is a flexible part whose shape is a function of the
machine's state, not only of its placement.

The backend that suits each part
--------------------------------

Open Source parametric CAD is several ecosystems, not one. OpenSCAD
has its own language and an enormous library culture; SolidPython
writes OpenSCAD from Python; CadQuery and build123d drive the OCCT
kernel from Python with exact boundary representation; JSCAD does
code-CAD in JavaScript. Each has libraries and strengths the others
lack, and a real project may want a gear from one and an enclosure
from another. In Solid Node every leaf part is written against the
backend that suits it, and the tree composes them: one assembly, one
viewer, one test suite. Beyond the modelling backends, a leaf can also
be a laser-cut sheet authored as a 2D profile plus a thickness (with
its cut file derived from the same source), an imported STL mesh a new
part is designed to fit, or a flexible part.

Exact where it matters
----------------------

OCCT-backed parts are **exact**: geometric questions between exact
parts are answered by the kernel on true solids, not on tessellated
approximations, so a sub-facet interference fails and a nominally
exact fit passes without epsilon tuning. Exact parts fuse exactly —
even mixing CadQuery and build123d children — and persist their exact
geometry beside the meshes. Where a mesh is the honest representation
(an imported STL, an OpenSCAD part), the framework says so and takes
the faceted path knowingly.

Fast feedback at any size
-------------------------

Solid Node is inspired by web-development culture: a dev server
watches the filesystem, rebuilds only the pieces that changed, and the
browser reflects each edit as you save. That incremental discipline is
what keeps a project moving past the point where a monolithic render
becomes too slow — and in the viewer, dragging one driver re-evaluates
only the expressions that read it, not the world.

Tests instead of prototypes
---------------------------

Prototyping takes time and generates waste. Much of both can be
avoided by asserting properties before producing anything: that parts
do not interfere, that they stay connected, that an assembly is
supported against gravity and statically balanced, that a moving
scenario — homing an axis, running a full cycle — holds its
invariants at every step. Solid Node's test framework makes those
assertions ordinary test cases, run by its own runner or by pytest.

Open Source
-----------

Solid Node is released under the Apache License 2.0. You are free to
build any project with it and license your own designs however you
choose. As digital manufacturing becomes popular, distributing a
design's *source* — not just its meshes — lengthens the life of the
goods built from it and reduces waste. We encourage you to publish the
source of your models: Open Source modelling should become an industry
standard, and this project is one more step towards that.
