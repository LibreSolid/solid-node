
.. _testing:

===============
Test-driven CAD
===============

Solid Node has a test runner and `solid_node.test.TestCase` extension to
run tests with meshes. As an example, you could use
`assertNotIntersecting` to verify that two gears do not overlap during
movement, or `assertIntersecting` to verify that a handle is not
detached during movement.

Tests can be written in two styles, both run by the same
``solid test`` command:

* mixing `solid_node.test.TestCaseMixin` into the node class, so tests
  live next to the rendering logic — used through most of this page;
* in a separate companion file, extending `solid_node.test.TestCase` —
  shown at the end, and the style the larger
  :doc:`V8 engine example <example-v8-engine>` uses.

A pin for the clock
===================

To demonstrate testing, let's make a pin holding the pointer and base
of the :doc:`simple clock <assemblies>` together.
First, to create a 6mm hole at the base, edit `myproject/clock_base.py`

.. code-block:: python

    class ClockBase(CadQueryNode):

        def render(self):
            wp = cq.Workplane("XY")
            return wp.circle(100).extrude(2) \
                .faces(">Z").workplane().hole(6)

Rendered — the base with its 6 mm hole:

.. solid-node:: _exports/clock_base_hole
   :height: 360px

And a hole in the pointer, at `myproject/pointer.py`

.. code-block:: python

    class Pointer(Solid2Node):

        def render(self):
            pointer = translate(-5, -5, 3)(
                cube(10, 90, 10)
            )
            hole = cylinder(r=3, h=15)
            return pointer - hole

Rendered — the pointer with its hole:

.. solid-node:: _exports/pointer_hole
   :height: 360px

Now, you should see a hole through both pointer and
base, while the pointer is rotating.

Let's make a pin through them. Create the file `myproject/pin.py`:

.. code-block:: python

    from solid_node.node import Solid2Node
    from solid2 import cube, cylinder, translate

    class Pin(Solid2Node):

        def render(self):
            return cylinder(r=3, h=20)

Rendered — the pin:

.. solid-node:: _exports/pin
   :height: 360px

And at `myproject/myproject.py`, assemble the pin together:

.. code-block:: python

    from solid_node.node import AssemblyNode
    from .clock_base import ClockBase
    from .pointer import Pointer
    from .pin import Pin

    class SimpleClock(AssemblyNode):

        def __init__(self):
            self.base = ClockBase()
            self.pointer = Pointer()
            self.pin = Pin()
            super().__init__()

        def render(self):
            return [self.base, self.pointer, self.pin]

        def simulate(self):
            angle = -360 * self.time
            self.pointer.rotate(angle, [0, 0, 1])

Rendered — the full clock with the pin fitted (press play):

.. solid-node:: _exports/simple_clock_pin
   :height: 360px

You should see the pin rendered in viewer, with a tight fit.
We want to test if this is functional: if in reality, this
arrangement will work. So, let's write a test.

TestCaseMixin
=============

For that, we'll use `solid_node.test.TestCaseMixin`. Our SimpleClock
class will extend it, and we'll add two tests to `myproject/myproject.py`:

.. code-block:: python

    from solid_node.node import AssemblyNode
    from solid_node.test import TestCaseMixin
    from .clock_base import ClockBase
    from .pointer import Pointer
    from .pin import Pin

    class SimpleClock(AssemblyNode, TestCaseMixin):

        def __init__(self):
            self.base = ClockBase()
            self.pointer = Pointer()
            self.pin = Pin()
            super().__init__()

        def render(self):
            return [self.base, self.pointer, self.pin]

        def simulate(self):
            angle = -360 * self.time
            self.pointer.rotate(angle, [0, 0, 1])

        def test_pin_runs_free_in_base(self):
            self.assertNotIntersecting(self.base, self.pin)

        def test_pin_runs_free_in_pointer(self):
            self.assertNotIntersecting(self.pointer, self.pin)

On the command line, stop the `solid develop` command, and
run `solid test`.

You should see two tests failing, as in practice there is a very
small intersection between rendered meshes even though mathematically
they should not. Let's reduce the radius of our pin to 2.99, at
`myproject/pin.py`:

.. code-block:: python

    class Pin(Solid2Node):

        def render(self):
            return cylinder(r=2.99, h=20)

Rendered — the slimmer pin:

.. solid-node:: _exports/pin_thin
   :height: 360px

Run the tests again. This time, the two tests will pass.

.. _testing-steps:

@testing_steps
==============

Even though the test has passed, if you look closely, the hole in pointer
and the pin are not really round, they are approximated by hexagons —
the :ref:`resolution problem <fn-property>` from Modeling parts. We
have tested that in the initial setup the pieces do not overlap, but
our test can't tell yet if the parts can freely move.

By using the decorator `@testing_steps`, we can test the intersection of
pieces in several moments of the animation:

.. code-block:: python

    ...
    from solid_node.test import TestCaseMixin, testing_steps

    class SimpleClock(AssemblyNode, TestCaseMixin):
        ...

        @testing_steps(16)
        def test_pin_runs_free_in_base(self):
            self.assertNotIntersecting(self.base, self.pin)

        @testing_steps(16)
        def test_pin_runs_free_in_pointer(self):
            self.assertNotIntersecting(self.pointer, self.pin)

The tests above will each run 16 times, at 16 different instants.
Run the tests again, and you'll see that the tests will pass and fail
in a pattern: the base passes, because CadQuery renders it very
roundly, but the hexagonal hole in the pointer catches the pin at some
angles.

The fix is the `fn` property from
:ref:`Modeling parts <fn-property>` — set ``fn = 256`` on `Pointer`
and `Pin`, and the 0.01 margin we left is enough to make the tests
pass at every step. You should take in consideration the approximation
error on holes whenever OpenScad-derived nodes, like `Solid2Node` and
`OpenScadNode`, take part in a fit.

Running tests on the full animation cycle can be very time consuming.
We can keep test performance by applying the test to a slice of time

.. code-block:: python

        @testing_steps(4, end=0.125)
        def test_pin_runs_free_in_base(self):
            self.assertNotIntersecting(self.base, self.pin)

@testing_instant
================

While `@testing_steps` runs a test across a range of the animation,
`@testing_instant` runs it at one specific instant:

.. code-block:: python

    from solid_node.test import TestCaseMixin, testing_instant

    class SimpleClock(AssemblyNode, TestCaseMixin):
        ...

        @testing_instant(0.5)
        def test_pointer_at_half_turn(self):
            self.assertNotIntersecting(self.pointer, self.pin)

Tests in a separate file
========================

Instead of mixing `TestCaseMixin` into the node class, tests can live in
their own file, extending `solid_node.test.TestCase`. The test runner
looks for a companion file next to the node being tested:

* for a node in a package, like `windmill/__init__.py`, it loads
  `windmill/test.py`;
* for a node in a module, like `myproject/pointer.py`, it loads
  `myproject/test_pointer.py`.

The test class receives the built node as `self.node`, plus an alias
named after the test class (CamelCase converted to snake_case, with the
`Test` suffix dropped) — so a `SimpleClockTest` can also refer to the
node as `self.simple_clock`. The clock tests from above, in a separate
`myproject/test_myproject.py`:

.. code-block:: python

    from solid_node.test import TestCase, testing_steps

    class SimpleClockTest(TestCase):

        @testing_steps(4, end=0.125)
        def test_pin_runs_free_in_base(self):
            self.assertNotIntersecting(self.node.base, self.node.pin)

        @testing_steps(4, end=0.125)
        def test_pin_runs_free_in_pointer(self):
            self.assertNotIntersecting(self.node.pointer, self.node.pin)

Both styles are run by the same `solid test` command, and can be
combined — this is how the :doc:`V8 engine <example-v8-engine>` keeps
one test file per part.

Available assertions
====================

Besides `assertNotIntersecting` and `assertIntersecting`, the test case
provides mesh assertions for fits and clearances:

* `assertNotIntersecting(node1, node2)` — the two meshes do not overlap
* `assertIntersecting(node1, node2)` — the two meshes have some overlap
* `assertInside(node1, node2)` — every mesh vertex of node2 is classified
  inside node1
* `assertClose(node1, node2, max_distance)` — every mesh vertex of node2 is
  at most `max_distance` away from node1's mesh surface
* `assertFar(node1, node2, min_distance)` — every mesh vertex of node2 is at
  least `min_distance` away from node1's mesh surface
* `assertIntersectVolumeAbove(node1, node2, min_volume)` — the overlap
  volume is above `min_volume`
* `assertIntersectVolumeBelow(node1, node2, max_volume)` — the overlap
  volume is below `max_volume`

``assertInside``, ``assertClose`` and ``assertFar`` sample node2's vertices;
they do not inspect points along its edges or faces. Their result therefore
depends on mesh density and direction, and by itself does not prove
whole-solid containment or a bound between every pair of surface points. This
matters especially for coarse meshes and concave boundaries. Use the
intersection and intersection-volume assertions when the contract concerns
overlap between a named pair, ``assertNoSolidInterference`` for clashes among
the topmost rigid solids of an assembly, and ``assertNoDisconnectedSolids``
for connectedness of each printed solid. There is currently no whole-surface
containment assertion.

Perturbation assertions
-----------------------

Two assertions verify a fit by perturbing a part and checking the
consequence. Each comes in two mutually exclusive modes, selected by
which of `axis` (rotation, the default) or `along` (translation) is
given — passing both is an error:

* `assertBlockedBeyond(node, angle, against, axis=(0, 0, 1), volume_epsilon=0.0, along=None, directions='both')`
  — rotated by ``+angle``/``-angle`` degrees about `axis`, or
  displaced by ``+angle``/``-angle`` mm along the unit vector `along`,
  `node` must intersect `against`: the fit genuinely locks beyond its
  play. Use it to prove a key, a dog clutch or a hex socket actually
  engages — or, in translation mode, that a pin is genuinely captured
  in its bore.
* `assertFreeWithin(node, angle, against, axis=(0, 0, 1), volume_epsilon=0.0, along=None, directions='both')`
  — the anti-gaming twin: perturbed the same way (`angle` accepts a
  list in either mode, e.g. a journal sweep or a set of clearance
  distances), `node` must **not** touch `against`. A blocking test
  alone could be satisfied by an undersized bore that always rubs;
  asserting free play within a smaller angle/distance closes that
  loophole.

Both perturb `node` about/along its own **local** frame, not the
world origin or world axes: the perturbation is inserted right before
node's own first placement `Translation`, so a rotation turns node
about its own axis, and a translation is carried by any placement
rotation that runs after it (node's own, or an ancestor assembly's) —
`along` is a direction in node's frame as it existed at that point in
its own placement, not a fixed world vector.

`directions='both'` (the default) checks both signed directions and
requires both to agree; `directions='forward'` checks only
``+angle``, for contracts that are deliberately one-sided (e.g. a
sleeve blocked sliding inward by a lip but free to slide outward).

`volume_epsilon` (mm^3, default ``0.0``) guards against boolean-noise
slivers from a legitimate flush contact (the deprecated leaf sweep has the
same historical parameter): above zero, a perturbation
only counts as fouling once its intersection volume exceeds the
epsilon.

.. code-block:: python

    def test_dog_clutch_engages(self):
        self.assertFreeWithin(self.sleeve, 2, self.gear)
        self.assertBlockedBeyond(self.sleeve, 5, self.gear)

    def test_pin_captured_in_bore(self):
        self.assertFreeWithin(self.pin, 0.1, self.bore, along=(1, 0, 0))
        self.assertBlockedBeyond(self.pin, 0.5, self.bore, along=(1, 0, 0))

Connectivity contracts
----------------------

Connectivity asks whether geometry hangs together inside one printed solid;
it is local and invariant under rigid placement. Collision asks whether
separately placed parts clash in the world and can change at each animation
instant. Solid Node keeps those frames distinct:

* ``assertNoDisconnectedSolids(node)`` — starting at ``node``, descends
  through assemblies and stops at the first rigid node on each branch. Each
  selected solid's own STL must contain exactly one connected component.
  Rigid ingredients inside a fusion are not checked independently.
* ``assertJoined(node1, node2, min_weld_volume=0.0)`` — proves two named
  features of the same printed solid meet directly, optionally with a minimum
  weld volume.

Neither assertion runs automatically. Declare the whole-solid contract as an
ordinary counted test where it is wanted:

.. code-block:: python

    def test_solid_integrity(self):
        self.assertNoDisconnectedSolids(self.node)

Because the assertion reads local STLs and composes no placement matrix, it
has the same verdict beneath an animated assembly at every instant. Passing a
subassembly scopes the check to that subtree.

Assembly integrity
------------------

``assertNoSolidInterference(node)`` is the world-space complement to solid
integrity. It descends through assemblies and selects the first rigid node on
each branch: the same topmost printed-solid boundary used by
``assertNoDisconnectedSolids``. It then certifies that those solids have no
positive-volume overlap at the testing instant already selected by the
runner. Ingredients inside a rigid fusion are not treated as separate parts.

A rigid root contains only one selected solid, so the assertion passes without
loading geometry. This makes both initial tests useful from a project's first
generated leaf through its later evolution into a nested assembly:

.. code-block:: python

    def test_solid_integrity(self):
        self.assertNoDisconnectedSolids(self.node)

    def test_assembly_integrity(self):
        self.assertNoSolidInterference(self.node)

The assembly assertion uses current world transforms. Decorate the ordinary
test with :ref:`@testing_steps <testing-steps>` or ``@testing_instant`` when
the contract must cover motion; the assertion itself neither accepts nor sets
a keyframe.

Empty intersections and exact zero-volume boundary contact pass. Every
positive intersection volume reported by the geometry kernel fails, and the
diagnostic names an offending pair. The assertion has deliberately no
overlap epsilon of its own; under the :ref:`faceted kernel
<comparison-kernel>` it reads verdicts the run's epsilon has already been
applied to, like every other volume question in that run, and adds nothing.
A volume waiver can hide a real narrow penetration and is not a
production allowance. Where parts must run free, encode physical clearance in
the model and add a pair-specific distance or fit contract with a
manufacturing margin expressed in length.

Internally, the assertion places each selected solid's cached Manifold, builds
one conservative bound per solid in a CHOSEN INDEXING FRAME, and uses a
sweep-and-prune index to emit only the pairs whose boxes overlap. The chosen
frame is the world frame, or the placement frame of one of the assembly's
largest topmost solids by local-bounds diagonal — whichever scores the
smallest total box volume, world winning ties — so an assembly sharing one
outermost rigid turn (a common ``facing`` applied to every part, say) is not
charged for every box growing under that turn. A bound taken in a non-world
frame is enlarged by a small fixed margin absorbing the extra arithmetic the
frame change costs, so a flush-contact pair is never lost to it; world bounds
are never enlarged, so an assembly that gains nothing from the choice is
indexed exactly as it always was. The choice can only change which candidate
pairs are emitted, never a verdict. Each emitted pair meets an exact Manifold
intersection. Nothing is computed over the assembly as a whole, so the cost
tracks the number of interacting pairs rather than the model's total triangle
count. This is a CPU geometry-kernel path (Manifold may use its own CPU
parallelism), not a GPU computation. The ``manifold3d`` dependency behind it
is conditional in the same sense as OpenSCAD: it is resolved at the faceted
operation that needs it, so a fully exact model runs its geometric
assertions without the compiled wheel, and a path that needs it and cannot
import it says so by name.

An emitted pair of two exact solids can cost less than a kernel call even
when their bounds genuinely overlap — a wheel running in the clearance gap
between two plates, say, whose box spans the wheel's position wherever it
turns. When no surface of one solid comes anywhere near a surface of the
other, the assertion decides that pair empty without asking the geometry
kernel at all. A solid that really is nested inside another is not
mistaken for this case: it is still caught, and still fails, naming both
solids and the shared volume, exactly as it always has. Nothing about a
project's own verdicts changes here — only some of the geometry kernel
calls a passing or failing assembly used to pay for are skipped.

Gravity support
---------------

``assertAssemblySupported(node, gravity=(0, 0, -1), max_drop=1.0, ground=None,
supports=None, stability_margin=0.0)`` answers the opposite question to
assembly integrity: not whether two parts share material, but whether the
assembly can exist. It selects the same topmost rigid solids, places them at
the testing instant the runner has already chosen, and proves two things about
them: that every one is transitively held against gravity, and that the whole
set can then stand.

A solid is *directly supported* by another when, displaced by ``max_drop``
along the normalized ``gravity`` vector, it intersects that solid with
positive volume. A part resting on a face, sitting in its clearance gap, or
hanging by an engaged lip all land in their support; a part placed in mid-air
lands in nothing. Zero-volume boundary contact after the drop is not a hold,
just as it is not interference. Those relations form a support graph, and a
part is supported only if that graph leads it to a grounded solid: a block
resting on a floating bracket is reported along with the bracket. Two parts
leaning on each other are grounded exactly when one of them reaches the
ground, never by leaning.

.. code-block:: python

    def test_assembly_supported(self):
        self.assertAssemblySupported(self.node)

Reaching ground is not standing up
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A bar resting on a single support at one end reaches ground through a perfectly
good support edge, and falls over. So once reachability holds, the assertion
proves **frictionless static equilibrium**: that some distribution of push-only
normal contact forces over the detected interfaces balances every non-anchored
solid's weight *and* the torque it makes about its own centre of mass — all of
them simultaneously. That is a linear feasibility question, decided by one
deterministic linear program, and its failure names the solid that cannot be
balanced and whether force or torque is what does not close::

    bar cannot rest in frictionless static equilibrium on its detected
    contacts (unbalanced torque)

The interfaces come from the same displaced intersections the support edges do,
meshed and classified so the contact points and normals lie on the *supporter's*
real, undisplaced surface. Detection runs in both directions: the drop finds
what a solid lands on, and a symmetric **lift** — the same displacement against
gravity — finds the overhead restraints. That second sweep is what lets an
engaged couple balance legitimately: a pin cantilevering out of a snug hole is
pushed up by the hole's lower wall near the mouth and down by its upper wall at
its inner end, and it passes without an exemption. Lift-detected contacts
contribute interfaces only; they never add support-graph edges.

Because the drop is what finds a contact, ``max_drop`` bounds the interfaces
too: a drop that carries a feature past the face it rests on cannot extract the
patch resting on it, which is the same window the paragraph on ``max_drop``
below describes.

With ``ground=None`` the assembly must hold itself together: the solids
reaching within ``max_drop`` of the assembly's furthest extent along gravity
are grounded, which is also what an unmodelled floor would touch. For the
equilibrium phase that floor is a real body — a slab whose top plane lies at
that furthest extent — and it is the *only* anchored one, so a default-grounded
solid must balance on the footprint it actually lands on. A top-heavy part
standing on too small a foot now fails instead of being exempt for being
lowest. Pass ``ground`` — a node, or a sequence of nodes, each resolved to its
selected solid — for an assembly anchored somewhere else, hung from a ceiling
or bolted to a frame that is not modelled; those solids then become the only
seeds and the only anchored bodies, and no floor exists:

.. code-block:: python

    def test_hangs_from_the_rail(self):
        self.assertAssemblySupported(self.node, ground=self.node.rail)

``supports=[(supported, supporter), ...]`` declares holds the assertion
deliberately cannot prove — press fits, glue, friction — and keeps the
exemption visible in the test rather than hidden in a tolerance. A declared
edge grounds the supported solid and transmits an unrestricted wrench between
the pair, force and torque in both signs, which is what a glue joint or a press
fit really does. A declared supporter must still be grounded itself; declaring
an edge grounds nothing on its own:

.. code-block:: python

    def test_supported(self):
        self.assertAssemblySupported(
            self.node, supports=[(self.node.bushing, self.node.housing)])

``stability_margin`` (mm, default ``0.0``) shrinks every contact patch toward
its own centroid before the equilibrium decision. At the default the check is
pure feasibility, so a knife-edge balance — the centre of mass exactly over a
patch boundary — is an equilibrium and passes. A positive margin demands that
much interior reserve in every patch and rejects it, which makes robustness an
explicit statement in the test rather than an assumption:

.. code-block:: python

    def test_stands_with_a_millimetre_to_spare(self):
        self.assertAssemblySupported(self.node, stability_margin=1.0)

A negative ``stability_margin`` is a loud error, as are a zero ``gravity``
vector, a non-positive ``max_drop``, and a ``ground`` or ``supports`` entry
that resolves to no selected solid.

Choosing ``max_drop`` (mm) is the one real judgement the assertion asks for.
It must be **larger** than the design's vertical clearance play, or a part
sitting in its own clearance gap reads as floating, and **smaller** than the
thinnest supporting feature's thickness plus the gap above it, or the dropped
solid tunnels straight through its support and reads as floating again. The
1.0 default sits in the usual window between printed clearances (0.5 mm or
less) and printed walls (1.2 mm or more).

What passing means: support reachability, force balance, torque balance, and
toppling over the contacts the assertion detects. What it does *not* mean:
friction, adhesion, purely lateral (gravity-parallel) wall reactions, the
toppling of a *single* solid on the floor — a lone selected solid still passes
without any geometric work — and every dynamic effect. The frictionless model
is deliberately conservative: a hold that exists only through friction fails
and must be declared in ``supports``, the same trade the reachability phase
already makes.

Internally it reuses the assembly-integrity machinery: the same cached
Manifolds and the same sweep-and-prune index, asked a directed question —
solid *i* displaced against solid *j* placed — so only pairs whose displaced
and placed boxes overlap ever meet a Boolean, in the drop and lift sweeps
alike. Its own bounds, unlike assembly integrity's, stay conservative world
AABBs always: gravity is a world-frame fact, so a projection along it (the
grounded seeds, the virtual floor) is only meaningful in that frame, and no
indexing frame is ever chosen for this assertion. A pair of exact solids has its
support edge decided by the boundary-representation kernel, as in assembly
integrity, while contact patches and mass properties are read off the placed
faceted geometry: statics needs a patch's extent and direction, not Boolean
validity. Zero or one selected solid passes without loading geometry.

Deprecated leaf-pair sweep
--------------------------

``assertNoPairwiseIntersections(node, volume_epsilon=0.0)`` is retained for
compatibility but deprecated. It visits every leaf pair and preserves its
historical ``volume_epsilon`` behavior. New tests should use
``assertNoSolidInterference`` and account for the deliberate scope change:
topmost rigid printed solids instead of every leaf, with no overlap epsilon.

.. _comparison-kernel:

Choosing the comparison kernel
==============================

Every intersection, containment, connectivity and weld question above is
decided by one of two kernels, and which one is a property of the *run*,
not of the model:

* The **exact** kernel compares two exact parts (CadQuery, build123d,
  molejo) on their boundary-representation solids. Boundary contact is
  exactly empty, a nominally exact fit is not interference, and there is
  no tolerance anywhere. This is the default, and the kernel a release or
  CI run uses.
* The **faceted** kernel compares every pair on the parts' meshes — the
  path a part without exact geometry always takes — at tessellation
  precision. It is the fast development loop: a flexible part such as a
  valve spring costs about 14 ms per comparison on meshes against about
  430 ms on the exact kernel, and on the v8-engine root suite the whole
  run went from 28 minutes to a minute and a half with the same verdict on
  every comparison.

Select the kernel with ``solid test --exact`` or ``solid test --faceted``.
Without a flag the ``SOLID_TEST_KERNEL`` environment variable decides
(``exact`` or ``faceted``), and without that the run is exact. The
``solid`` command loads the project's ``.env`` at startup, so a developer
records the fast loop once, in that ignored checkout-local file::

    SOLID_TEST_KERNEL=faceted

A CI runner has no such file and needs no configuration: its runs are
exact. Keep ``.env`` out of the repository (``solid new`` ignores it) so
the choice never travels.

A faceted run says what it is — a line before the first build names the
kernel, and the summary line ends with ``(faceted kernel, volume epsilon
E mm³)`` — so a green fast run is never mistaken for an exact one in a
log or a commit message. A faceted verdict is at the precision of the
STL tessellation (a chord may deviate from the true surface by up to
0.1 mm): a clearance thinner than that can read as slight overlap, and
interference thinner than that can be missed. Commit evidence and release
checks come from the exact run.

Where solids meet exactly — a boss seated on a plate, a shaft at zero
nominal clearance in its bore — their meshes overlap by slivers the exact
kernel never sees. The **volume epsilon** is the developer's stated size
for that noise: ``solid test --faceted --volume-epsilon 0.5`` (or
``SOLID_TEST_VOLUME_EPSILON=0.5`` beside the kernel line in ``.env``)
reports every intersection of at most 0.5 mm³ as empty for the whole run,
before any assertion reads it. The default is 0, and a project whose
clearances exceed the tessellation deviation needs none — the v8-engine
suite runs faceted at 0. The epsilon exists only for the faceted kernel:
the exact kernel refuses it, because it has nothing to absorb. An
assertion's own ``volume_epsilon`` still filters on top of it, and the
warning that an epsilon was ignored never fires under the faceted kernel,
where no comparison routes exact.

.. _placement-quantum:

The placement quantum
======================

Every intersection verdict above is asked once per run and remembered
(:ref:`comparison-kernel`'s memo, ADR-070) — two comparisons of the same
pair in the same relative placement are one question. "Same placement" is
decided by comparing the pair's relative matrix — one part's composed
world matrix inverted and applied to the other's. When a rigid parent
carries several children together, each child's world matrix is composed
through its own chain of operations, and recomposing the SAME rigid
motion by two different multiplication orders leaves float noise between
the two results — around 1e-13 on a real assembly — even though nothing
about the pair's placement changed. Keyed on exact bytes, that noise reads
as a different question every time, and a sweep that carries a pendulum,
a motion works or a weight through dozens of instants re-asks a question
it already answered at a quarter of the run's cost.

The **placement quantum** absorbs that noise: the relative matrix is
divided by the quantum and rounded to integer cell indices, and two
placements landing in the same cell are one question. It is selected the
same way as the kernel and the epsilon — ``solid test
--placement-quantum MM``, else ``SOLID_TEST_PLACEMENT_QUANTUM`` in
``.env``, else the framework's default of ``1e-9`` mm — and, unlike the
volume epsilon, it applies under BOTH kernels: it identifies a question,
not a quantity of material, and both kernels' verdicts pass through the
same memo. ``--placement-quantum 0`` restores the exact-bytes key exactly
as ADR-070 specified it, with no cell arithmetic at all.

This is not a tolerance on any assertion. At the default quantum, two
placements sharing a cell move every point of one solid, in the other's
frame, by at most a few nanometres at metre scale — far below the exact
kernel's own precision, OCCT's ``Precision::Confusion``, or any clearance
a machine is designed to hold. A pair that straddles a cell boundary
simply misses and recomputes, exactly as today, so the quantum can only
ADD cache hits, never blur a verdict at the boundary. Raising it well
past the default is a real judgement about arithmetic noise, not about
material, and the run says so: a non-default quantum is named on the
summary line, beside the faceted label and epsilon when the run is
faceted, so a green run at a widened quantum is never mistaken for one at
the default in a log or a commit message.

Testing motion: scenarios
=========================

Everything on this page judges the machine at instants of the ``$t``
timeline. A machine with :doc:`drivers <driving>` is also testable *in
motion* — an instruction triggered, an invariant held at a cadence, a
terminal state asserted at an exact tick — with ``ScenarioTest`` and the
stepped simulation loop: see :doc:`Simulating and testing scenarios
<scenarios>`.

See the :doc:`API Reference <api-reference>` for details. All the
standard `unittest.TestCase` assertions are available as well.
