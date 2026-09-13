Shared motion expressions
=========================

Motion laws still use ordinary arithmetic and ``solid_node.math``, with the same
numeric poses, degree trigonometry, drivers and ports. Reusing a deferred value
now keeps references to its operands instead of copying its entire formula.
No special intermediate-value API is needed.

Build and export compile the reachable graph into the existing schema-4
``bindings`` table. The browser's document language and controls have not changed.
OpenSCAD and SolidPython remain supported modelling technologies; this change
removed no geometry backend. A subsequent v0.7 decision removed the OpenSCAD
GUI from ``solid develop`` while retaining those modelling technologies and
the fixed-pose OpenSCAD snapshot renderer.

Under a running root the COMPILED PROGRAM shares that same table. A
version 5 document's law expressions, jump-plan skeletons, level
quantities and expression span bounds are compiled in one pass with the
tree's operations and ``params``, so a subexpression a law shares with
its own plan's level quantity is published once and nothing anywhere
carries the producer-side ``let(...)`` closure.

A jump plan's BRANCH PLACEHOLDERS are a published name kind of their
own. The compiler names them per plan; publication renames them
``_j0``, ``_j1``, … across the WHOLE document, in edge order and then
the graph's postorder, under a prefix lengthened by a leading underscore
for as long as any published id matches it — exactly as ``_b`` is
lengthened. Per-plan names would let three plans each calling their
first jump ``$j0`` share one binding entry between three different jump
nodes.

Text compatibility
------------------

Bare inputs keep their spelling (``$t``, ``drive``, ``axis.motor``). Unshared formulas
keep the familiar scalar spelling. ``str(value)``, ``value.value``, and standalone
operation ``.serialized`` may now use a self-contained SCAD closure for sharing:

.. code-block:: text

   let(_s0 = sin(drive)) (_s0 + _s0)

Local names avoid free-input collisions. These names are not a public identity
or a global namespace. ``repr(value)`` is a short diagnostic, not SCAD source.
Code that needs SCAD text should use ``str``, not parse or compare exact compound
spellings. Publication never changes the live operation's value.

``unserialize()`` accepts these standalone scalar forms without consuming its
input list. Numeric literal strings retain their historical form. Recognized
compound scalars recover their dependencies; unresolved inputs fail numeric
placement rather than silently substituting zero or a default animation time.
Ordinary numeric poses continue to rerun the author's laws with numbers.

Direct SolidPython operands work on either side of supported arithmetic, and
supported scalar function wrappers can return through the closure importer.
SCAD ``let`` is producer-side syntax only: normal viewer JSON contains the same
scalar vocabulary and binding references as before, never a new closure opcode.
Unknown legacy text retains its verbatim export fallback and truncated warning.
The importer is not a general OpenSCAD interpreter.

Limits and evidence
-------------------

The bound covers native graph construction and its normal consumers, not text
that project code or a third-party text builder already expanded. Separate SCAD
output sites may each contain their own compact closure. There is no global
strong expression registry retaining discarded machines.

The existing remainder caveat remains: Python ``%`` and symbolic SCAD/JavaScript
remainder differ for negative operands. This change preserves symbolic remainder;
it does not silently change the motion laws. Use the existing ``wrap`` composition
when its semantics are intended.

Curta acceptance measurements and reproduction commands live in the
completed change record at
``openspec/changes/archive/2026-09-11-expression-graphs/evidence.md``.
Measured peaks describe those processes on that machine, not a minimum hardware
specification. The 8,000,000,000-byte limit is a safety ceiling, not their actual
memory requirement.
