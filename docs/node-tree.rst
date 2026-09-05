
.. _node-tree:

==================================
Names, the node tree and caching
==================================

Every node has a **name**, which addresses it in the viewer tree and
in tests, and a **build identity**, which decides which cached STL file
backs it. They are independent, and each has simple rules.

Node names
==========

A node's name defaults to its class name. When a node becomes a child
of another node, the name is derived from the attribute the parent
holds it under:

.. code-block:: python

    class SimpleClock(AssemblyNode):

        def __init__(self):
            self.base = ClockBase()
            self.pointer = Pointer()
            super().__init__()

Here the children appear in the tree as ``base`` and ``pointer``, not
``ClockBase`` and ``Pointer``. This is what keeps two same-class
siblings apart — `self.hours = Pointer()` and `self.minutes =
Pointer()` are distinct nodes named ``hours`` and ``minutes``.

Children held in a list or tuple attribute get indexed names:

.. code-block:: python

    self.planets = [Planet(i) for i in range(3)]
    # named planets-0, planets-1, planets-2

An explicit ``name=`` passed to the constructor always wins over the
derived name. Attributes starting with an underscore are ignored by
the derivation.

The same attribute-derived path is what qualifies a **driver id**
(:doc:`Driving a machine <driving>`). Two instances of one axis class
held as `self.x_axis` and `self.y_axis` publish their same-named
driver as ``x_axis.position`` and ``y_axis.position`` — one string,
identical in the exported document's driver table, in `set_state`, in
instruction targets and in a simulation's state. The id must be a
legal expression identifier, which the indexed list names above are
not (``planets-0`` would parse as a subtraction): a driver-declaring
node held in a list makes the tree unqualifiable, and it fails loudly
naming the offending segment rather than letting two siblings share
one value.

Node references
===============

A node is named by **reference**: a qualifier (`package.module:Class`),
a file path, or a file path plus class (`path/to/file.py:Class`). With
no reference, a node-scoped command like `solid develop` operates on
the project's model, declared as `model = "package.module:Class"` under
`[tool.solid-node]` in `pyproject.toml` — what `solid new` writes for
you. A project holding several machines declares them by name in
`[tool.solid-node.models]`, and each name is then a reference of its
own; see :ref:`several-models`.

A bare path resolves to the single node class defined in that file.
When a file defines several — like the panel-plus-assembly file in
:doc:`Fusing parts <fusion>` — name the one you mean:

.. code-block:: python

    class Panel(Solid2Node):
        ...

    class VolumeControl(AssemblyNode):
        ...

A bare path to that file fails with an `AmbiguousNodeError` instead of
silently picking one; name the class you mean, either by qualifier
(`panel_and_knob:VolumeControl`) or hybrid path
(`panel_and_knob.py:VolumeControl`). See the :doc:`command line
reference <cli>` for the full reference grammar. Test classes
(:doc:`Test-driven CAD <testing>`) resolve independently and may each
declare the node they bind to.

Build identity and caching
==========================

Solid Node caches every generated artifact in the build directory
(`_build` by default, see ``SOLID_BUILD_DIR`` in the :doc:`command
line reference <cli>`): the SCAD and STL of OpenSCAD-family parts, a
`.brep` with the exact geometry beside the STL of OCCT-backed parts,
and a `.dxf` cut profile beside each sheet part — and rebuilds a part
only when its source or its parameters change.

"Changed" is decided by stamps, exactly. Source modification times are
read as integer nanoseconds and artifacts are stamped with the very
value that was read, so freshness is decided by **exact equality**, no
tolerance window: an artifact is current when its stamp matches its
sources, stale otherwise. (When a copy or checkout disturbs mtimes,
a content check rescues the artifact rather than rebuilding the
world.) One part tracks more than its parameters: an
:ref:`imported STL <stl-import>` leaf also counts its declaring Python
module among its sources, because its ``adjust()`` hook can change the
geometry without any constructor argument moving.

The cache key of a node instance is derived from its **constructor
arguments**: a node built as `Gear(teeth=20)` and one built as
`Gear(teeth=21)` are two different artifacts, while two `Gear(teeth=20)`
instances share one — the geometry is the same, so it is built once,
no matter how many times the part appears in the assembly, or under
which names.

A node that *declares* its parameters (:doc:`Declaring a machine
<declaring>`) is keyed the same way, by the framework: the class plus
the resolved value of every declared parameter, so no keyword can be
forgotten. Identical units from ``repeat()`` share one key and one
artifact.

Consequences worth knowing:

* Renaming a node (``name=`` or the holding attribute) never
  invalidates its cache — names address the tree, they are not part of
  the build identity.
* Any parameter change, however deeply buried in a long value, produces
  a new artifact; stale geometry cannot be served for a same-named
  node with different parameters.
* Parameter values of any size are safe — the key embeds a bounded
  readable prefix plus a hash, not the values verbatim.
* Driver and port values are deliberately **not** part of the build
  identity. A part's placement and a flexible part's pose change with
  every bound snapshot; keying artifacts on them would mint a new part
  per frame. Identity stays structural — constructor arguments — and
  state stays in the snapshot.
