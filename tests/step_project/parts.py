# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The project's imported STEP parts, one class per part.

Every class here declares one STEP file and, where the document needs
it, the code that selects or corrects the product. That code is the
reason the wrapper module joins the node's tracked source set: editing
`part` or an `adjust` hook changes the part just as an edit to the STEP
file would.

The STEP fixtures these classes wrap are authored and written by
`tests/test_step_node.py`'s `setUpModule()`, exactly as `stl_project`'s
meshes are: no binary fixture is committed, so this module names files
that exist only once the test suite has run.
"""

from solid_node.node import StepNode
from solid_node.node.adapters.step import solids_from_faces

from .dimensions import SCALE_FACTOR, SEWING_TOLERANCE


class UndeclaredPart(StepNode):
    """A subclass that forgot to say which STEP file it is."""


class SingleProduct(StepNode):
    """A bare file holding one product and no assembly: the plain case,
    needing no `part`."""

    step_source = 'single_product.step'


class WrappedSinglePart(StepNode):
    """An assembly root wrapping exactly one part: still needs no `part`,
    and selects the part, not the root."""

    step_source = 'wrapped_single_part.step'


class OpaqueSingleProduct(SingleProduct):
    """The plain file's product, with its own declared colour -- so a
    currency test can prove no document read happens without entangling
    itself with colour-from-document behaviour."""

    color = '#445566'


class ScaledSingleProduct(SingleProduct):
    """The same file, corrected in code rather than by a constructor
    knob -- and by a constant that lives in another module, which the
    node must therefore track too."""

    def adjust(self, shape):
        return shape.scale(SCALE_FACTOR)


class ColouredPart(StepNode):
    """One of two products in a file whose root wraps them both; this one
    carries the document's own surface colour."""

    step_source = 'two_products.step'
    part = 'ColouredPart'


class PlainPart(StepNode):
    """The other product of the same file, carrying no colour."""

    step_source = 'two_products.step'
    part = 'PlainPart'


class DeclaredColourPart(StepNode):
    """The document's coloured product, but the node declares its own
    colour, which must win and must never open the document for it."""

    step_source = 'two_products.step'
    part = 'ColouredPart'
    color = '#112233'


class UnselectedTwoProducts(StepNode):
    """The two-product file with no `part` declared: several candidates,
    so the build fails with the inventory."""

    step_source = 'two_products.step'


class WholeTwoProductAssembly(StepNode):
    """The same file's assembly root, named explicitly -- still
    selectable, even though it is never chosen by omission."""

    step_source = 'two_products.step'
    part = 'TwoProducts'


class MissingProduct(StepNode):
    """A `part` naming no product of the file."""

    step_source = 'two_products.step'
    part = 'NoSuchProduct'


class RepeatedProduct(StepNode):
    """One product placed at two occurrences far apart."""

    step_source = 'repeated_product.step'
    part = 'Repeated'


class NestedGearbox(StepNode):
    """A sub-assembly, selected by name, placed away from the origin by
    its parent."""

    step_source = 'nested_assembly.step'
    part = 'Gearbox'


class AmbiguousPin(StepNode):
    """Two distinct products of one name: the name alone cannot select
    either."""

    step_source = 'duplicate_names.step'
    part = 'Pin'


class FaceOnlyPart(StepNode):
    """A product that carries only faces: no `adjust`, so it is rejected
    at admission."""

    step_source = 'face_only.step'


class SewnFaceOnlyPart(StepNode):
    """The same face-only product, sewn knowingly by its own `adjust`
    hook."""

    step_source = 'face_only.step'

    def adjust(self, shape):
        return solids_from_faces(shape, SEWING_TOLERANCE)


class CurvedProduct(StepNode):
    """A curved solid, whose angular deflection actually matters."""

    step_source = 'curved.step'


class CoarseCurvedProduct(CurvedProduct):
    """The same file, declaring a coarser angular deflection."""

    angular_deflection = 0.5


class BrokenAdjustPart(StepNode):
    """An `adjust` hook that returns geometry with no solid at all: the
    gate must still reject it, hook or no hook."""

    step_source = 'single_product.step'

    def adjust(self, shape):
        return shape.Faces()[0]
