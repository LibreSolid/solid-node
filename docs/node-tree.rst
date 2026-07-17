
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

The NODE marker
===============

Solid Node loads one node class per file: `solid develop root` finds
the class defined in `root/__init__.py` and makes it the root of the
tree. When a file defines a single node class, nothing needs to be
said. When it defines several — like the panel-plus-assembly file in
:doc:`Fusing parts <fusion>` — set the module-level ``NODE`` marker to
name the intended one:

.. code-block:: python

    class Panel(Solid2Node):
        ...

    class VolumeControl(AssemblyNode):
        ...

    NODE = VolumeControl

Without the marker, loading a multi-class file fails with an
`AmbiguousNodeError` instead of silently picking one. Test classes
(:doc:`Test-driven CAD <testing>`) are not affected by the marker —
it only selects among node classes.

Build identity and caching
==========================

Solid Node caches every generated artifact — SCAD, STL — in the build
directory (`_build` by default, see ``SOLID_BUILD_DIR`` in the
:doc:`command line reference <cli>`), and rebuilds a part only when
its source or its parameters change.

The cache key of a node instance is derived from its **constructor
arguments**: a node built as `Gear(teeth=20)` and one built as
`Gear(teeth=21)` are two different artifacts, while two `Gear(teeth=20)`
instances share one — the geometry is the same, so it is built once,
no matter how many times the part appears in the assembly, or under
which names.

Consequences worth knowing:

* Renaming a node (``name=`` or the holding attribute) never
  invalidates its cache — names address the tree, they are not part of
  the build identity.
* Any parameter change, however deeply buried in a long value, produces
  a new artifact; stale geometry cannot be served for a same-named
  node with different parameters.
* Parameter values of any size are safe — the key embeds a bounded
  readable prefix plus a hash, not the values verbatim.
