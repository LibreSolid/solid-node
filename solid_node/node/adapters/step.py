# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The solid-import leaf: a STEP document as a part.

STEP is the format every CAD package and every vendor publishes. Unlike
`StlNode`'s mesh, a STEP product is a boundary representation the
moment it is read, so this leaf derives `ExactLeafNode` instead of
writing its own artifact: `shape()`, the `.brep`, exact fusion and the
declared-tessellation-precision path all come from that base for free.
`StlNode`'s three rules carry over onto a document instead of a pack:

The part is admitted, not assumed. Geometry that holds no solid after
`adjust` fails at build time naming the node, the file, the part, and
what it does hold -- shells and faces -- and writes nothing. There is
no escape hatch: a face-only product is not a defect a flag can wave
past, because the exact kernel has no use for a shape with no volume.
Sewing one into a solid is a project's own, explicit `adjust` call to
`solids_from_faces`, promoted here from openvmp's hand-written helper.

The part is selected, not guessed. A STEP document is a tree of named
products -- parts and sub-assemblies alike -- and `part` names the one
this node is. A file with exactly one candidate needs no `part`; a file
with several fails with the document's own inventory, so no separate
inspection tool has to exist.

Corrections are code. `adjust(self, shape)` receives the selected
product's own CadQuery `Shape` and returns the corrected one -- no
scale, unit, recenter or sew constructor knob to invent.

One rule is new, because a document is not a pack: geometry never
carries an occurrence's placement. `GetShape_s` on a product's own
label returns its prototype shape, whichever of the document's
occurrences a reader has in mind; placing it is the assembly's job.

And the document is read at most once per file per process: XCAF's
transfer is expensive (11.79 s measured on a 35 MB vendor assembly) and
every node over one file shares the one cached read, evicted when the
file's mtime changes -- the same cache shape as
`solid_node.exact._shape_cache`.
"""

import math
import os
import sys

import cadquery as cq
import numpy as np
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
from OCP.gp import gp_Vec
from OCP.IFSelect import IFSelect_RetDone
from OCP.Quantity import Quantity_Color
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_AsciiString, TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label, TDF_LabelSequence, TDF_Tool
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFApp import XCAFApp_Application
from OCP.XCAFDoc import XCAFDoc_ColorSurf, XCAFDoc_DocumentTool

from solid_node.node.exact_leaf import ExactLeafNode
from solid_node.node.sources import source_closure


##############################################
# Reading and indexing the document


def _entry(label):
    """A stable string identity for a label within its document.

    `TDF_Label.__eq__` is object identity, not value equality (`IsEqual`
    is the value comparison), and two Python wrappers of the same
    underlying label are never the same object -- so a label cannot key
    a dict directly. Its tag-list entry (``"0:1:2"``) can.
    """
    ascii_string = TCollection_AsciiString()
    TDF_Tool.Entry_s(label, ascii_string)
    return ascii_string.ToCString()


def _label_name(label):
    attr = TDataStd_Name()
    if label.FindAttribute(TDataStd_Name.GetID_s(), attr):
        return str(attr.Get().ToExtString())
    return None


def _bounding_box(shape):
    """The shape's local bounding box, without tessellating.

    `cq.Shape.BoundingBox()` calls `BRepBndLib.AddOptimal_s`, which is
    exact but meshes first -- 10.78 s on the worst product of a 35 MB
    vendor assembly. The inventory is a failure path that must stay
    fast even when it names every product of a large document, so it
    calls `BRepBndLib.Add_s` directly with `useTriangulation=False`
    instead -- 0.21 s for the same 21 products (design D3, fact 10).
    """
    box = Bnd_Box()
    BRepBndLib.Add_s(shape.wrapped, box, False)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return (xmin, ymin, zmin), (xmax, ymax, zmax)


def _point(values):
    return '(' + ', '.join(f'{float(value):.3f}' for value in values) + ')'


def _srgb_hex(quantity_color):
    """A `Quantity_Color` as the framework's `#RRGGBB`.

    XCAF hands back **linear** RGB; the number a CAD package wrote into
    the file is sRGB (design D7, fact 5): a part written at
    `cq.Color(0.9, 0.1, 0.1)` reads back as (0.787, 0.010, 0.010), and
    hex-encoding that raw value publishes a colour about 12% darker
    than the file says. `Convert_LinearRGB_To_sRGB_s` is the inverse of
    whatever wrote the file, so the round trip holds.
    """
    channels = (quantity_color.Red(), quantity_color.Green(),
               quantity_color.Blue())
    srgb = (Quantity_Color.Convert_LinearRGB_To_sRGB_s(channel)
           for channel in channels)
    return '#%02x%02x%02x' % tuple(
        max(0, min(255, round(255 * channel))) for channel in srgb)


class _Product:
    """One top-level label of the document: a part, a sub-assembly, or
    the document's own root, however many times it is placed."""

    __slots__ = ('label', 'entry', 'name', 'is_free', 'is_assembly')

    def __init__(self, label, entry, name, is_free, is_assembly):
        self.label = label
        self.entry = entry
        self.name = name
        self.is_free = is_free
        self.is_assembly = is_assembly

    @property
    def display_name(self):
        return self.name if self.name is not None else '(unnamed)'

    @property
    def is_candidate(self):
        """Every product except a root that is itself an assembly
        (design D3): the one thing never handed to a node by omission.
        """
        return not (self.is_free and self.is_assembly)

    @property
    def kind(self):
        if self.is_free and self.is_assembly:
            return 'root assembly'
        if self.is_assembly:
            return 'sub-assembly'
        return 'part'


class _Document:
    """A transferred XCAF document: every product, its occurrences, and
    its colour, indexed once at read time."""

    def __init__(self, doc, path):
        self.path = path
        # Kept alive for the life of this cache entry: every label below
        # is a reference into `doc`, not a copy (design D6).
        self._doc = doc
        self.shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
        self.color_tool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())

        labels = TDF_LabelSequence()
        self.shape_tool.GetShapes(labels)

        self.order = []
        self.products = {}
        self._occurrences = {}
        for index in range(1, labels.Length() + 1):
            label = labels.Value(index)
            entry = _entry(label)
            self.order.append(entry)
            self.products[entry] = _Product(
                label=label, entry=entry, name=_label_name(label),
                is_free=bool(self.shape_tool.IsFree_s(label)),
                is_assembly=bool(self.shape_tool.IsAssembly_s(label)))
            self._occurrences[entry] = []

        for entry in self.order:
            product = self.products[entry]
            if not product.is_assembly:
                continue
            components = TDF_LabelSequence()
            self.shape_tool.GetComponents_s(product.label, components)
            for index in range(1, components.Length() + 1):
                component = components.Value(index)
                referred = TDF_Label()
                is_reference = self.shape_tool.GetReferredShape_s(
                    component, referred)
                target = referred if is_reference else component
                target_entry = _entry(target)
                # A malformed document could refer to a label GetShapes()
                # never listed; over-approximating "no occurrence" is
                # safer than raising deep inside a document reader.
                if target_entry in self._occurrences:
                    self._occurrences[target_entry].append(component)

    def candidates(self):
        return [self.products[entry] for entry in self.order
               if self.products[entry].is_candidate]

    def find(self, name):
        """Every product of the document named `name`, in document
        order -- searching every product, not only the candidates, so a
        multi-component root remains selectable by explicit name."""
        return [self.products[entry] for entry in self.order
               if self.products[entry].name == name]

    def occurrences(self, product):
        count = len(self._occurrences[product.entry])
        # A product no component refers to is the document's own root,
        # or a bare file's only product: it is still placed once, by
        # simply being the document.
        return count if count else 1

    def shape(self, product):
        """`product`'s own shape, independent of every other caller's.

        `GetShape_s` hands back a reference into this shared, cached
        document, and OCCT's mesher attaches a triangulation directly
        onto a face's underlying TShape -- so two `StepNode`s selecting
        the *same* product from the *same* cached document would
        otherwise contaminate each other's tessellation: whichever
        meshes first (at whatever precision it declares) would leave a
        triangulation the other's `exportStl` treats as already good
        enough and reuses, regardless of what the second node declared
        (the same relative/absolute-mode hazard ADR-077 documents).
        `.copy(mesh=False)` -- `BRepBuilderAPI_Copy`, not copying any
        existing triangulation -- gives each caller independent
        topology to mesh on its own terms.
        """
        return cq.Shape.cast(self.shape_tool.GetShape_s(product.label)).copy()

    def color(self, product):
        """`product`'s own surface colour, else the colour every
        occurrence of it agrees on, else None (design D7)."""
        own = self._label_color(product.label)
        if own is not None:
            return own
        found = {self._label_color(component)
                for component in self._occurrences[product.entry]}
        found.discard(None)
        if len(found) == 1:
            return next(iter(found))
        return None

    def _label_color(self, label):
        quantity = Quantity_Color()
        if self.color_tool.GetColor_s(label, XCAFDoc_ColorSurf, quantity):
            return _srgb_hex(quantity)
        return None

    def describe(self, product):
        shape = self.shape(product)
        solids = len(shape.Solids())
        minimum, maximum = _bounding_box(shape)
        volume = shape.Volume()
        occurrences = self.occurrences(product)
        return (
            f'  {product.display_name}: {product.kind}, '
            f'{occurrences} occurrence{"s" if occurrences != 1 else ""}, '
            f'{solids} solid{"s" if solids != 1 else ""}, '
            f'bounds {_point(minimum)}..{_point(maximum)}, '
            f'volume {volume:.3f}')

    def inventory(self):
        return '\n'.join(self.describe(self.products[entry])
                         for entry in self.order)


def _read_document(path):
    """Read and transfer `path` into a fresh `_Document`.

    Name mode and colour mode on, as both hand-written readers this
    leaf replaces already do: a node needs both to select a product by
    name and to take its colour from the file.
    """
    application = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString('XmlXCAF'))
    application.NewDocument(TCollection_ExtendedString('MDTV-XCAF'), doc)

    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.SetColorMode(True)
    status = reader.ReadFile(path)
    if status != IFSelect_RetDone:
        raise ValueError(
            f'{path}: could not read this STEP file (reader status '
            f'{status})')
    if not reader.Transfer(doc):
        raise ValueError(f'{path}: could not transfer this STEP document')

    return _Document(doc, path)


#: One document per (path, mtime_ns), in the shape of
#: `solid_node.exact._shape_cache` (design D6): a key miss for a path
#: drops every entry for that path before reading, so at most one live
#: entry exists per file, and the process pays the read once.
_document_cache = {}


def _evict_document_cache(path):
    for key in [key for key in _document_cache if key[0] == path]:
        del _document_cache[key]


def cached_document(path):
    mtime_ns = os.stat(path).st_mtime_ns
    key = (path, mtime_ns)
    cached = _document_cache.get(key)
    if cached is None:
        _evict_document_cache(path)
        cached = _document_cache[key] = _read_document(path)
    return cached


##############################################
# Sewing a face-only product


def solids_from_faces(shape, tolerance):
    """Sew `shape`'s faces into one solid per closed shell.

    This is openvmp's own `solids_from_faces`, promoted: a vendor STEP
    product published as bare surfaces has no volume the exact kernel
    can use, so `StepNode`'s admission gate refuses it -- and this is
    the explicit, knowing correction an `adjust` hook calls instead of
    the framework guessing a tolerance for a file it has never seen.

    It sews within `tolerance` and wraps each resulting closed shell in
    a solid. It does **not** guarantee that the shells actually close,
    that `tolerance` is right for this file, or that the result is
    watertight or manifold: sewing an open shell still returns
    *something* Solids() can count, and admission judges only whether a
    solid came back, not whether it is sound. A project calling this
    is vouching for the file it is sewing.
    """
    sewing = BRepBuilderAPI_Sewing(tolerance)
    sewing.Add(shape.wrapped)
    sewing.Perform()
    sewn = cq.Shape.cast(sewing.SewedShape())
    solids = [cq.Solid.makeSolid(shell) for shell in sewn.Shells()]
    if not solids:
        return sewn
    if len(solids) == 1:
        return solids[0]
    return cq.Compound.makeCompound(solids)


##############################################
# The node


class StepNode(ExactLeafNode):
    """A part that comes from one product of a STEP document.

    Declare the file with `step_source`, as a path relative to the
    directory of the module defining the subclass::

        class Bracket(StepNode):

            step_source = 'vendor/bracket.step'

    Select one product out of a multi-product document with `part`,
    naming it as the file carries it; a node that omits `part` on a
    document with more than one candidate product fails with the
    document's inventory. Correct the shape by implementing
    `adjust(self, shape)`. Sew a product a vendor published as bare
    surfaces with the module-level `solids_from_faces` helper, called
    knowingly from `adjust`.

    Unlike `StlNode`, this leaf is exact: it derives `ExactLeafNode` and
    supplies nothing beyond its own reading and selection, so `shape()`,
    the `.brep`, exact fusion and the declared tessellation precision
    are inherited whole.
    """

    #: The STEP file, relative to the wrapper module's
    #: directory.
    step_source = None

    #: The product this node is, named as the document carries it. None
    #: selects the document's one candidate product, if it has exactly
    #: one; otherwise a `part` must be declared.
    part = None

    #: `render()` returns a `cq.Workplane`, exactly as `CadQueryNode`
    #: does (design D2): a bare `cq.Shape` would force a broader
    #: namespace than every other CadQuery-backed adapter declares.
    namespace = 'cadquery.cq'

    #: Set only by the `color` setter below, and only for a non-None
    #: assignment: the property that shadows this attribute must be
    #: able to tell "never declared" apart from "assigned None" (design
    #: D7).
    _declared_color = None

    def __init__(self, *args, **kwargs):
        if not self.step_source:
            raise ValueError(
                f'{self.__class__.__name__} is a StepNode and must declare '
                f'"step_source", the path of a STEP file in the same '
                f'directory as the python module defining it')

        module = sys.modules[self.__class__.__module__]
        wrapper = os.path.realpath(module.__file__)
        self.step_source = os.path.realpath(
            os.path.join(os.path.dirname(module.__file__), self.step_source))

        super().__init__(*args, **kwargs)

        # The wrapper module joins the tracked set, for ADR-055's
        # reason: `part` and `adjust` live in the python file and
        # decide the part as much as the document does.
        self.files.update(source_closure(wrapper))

    def get_source_file(self):
        return self.step_source

    def render(self):
        return cq.Workplane(obj=self._materialized_shape())

    #: A subclass that declares its own `color` shadows this property
    #: entirely with a plain class attribute (ordinary Python attribute
    #: lookup), so it is never invoked and the document is never read
    #: for it. This descriptor is reached only by a subclass that
    #: leaves `color` undeclared.
    @property
    def color(self):
        if self._declared_color is not None:
            return self._declared_color
        document = cached_document(self.step_source)
        product = self._select(document)
        return document.color(product)

    @color.setter
    def color(self, value):
        # Only a non-None assignment is a declaration (design D7): the
        # framework's own initialisation, or a subclass `__init__`
        # writing `self.color = None`, must not be mistaken for one, or
        # the document's colour could never be reached.
        if value is not None:
            self._declared_color = value

    ##############################################
    # Materialization

    def _materialized_shape(self):
        """The geometry this node's artifact holds: the selected
        product, corrected by `adjust`, admitted by the gate."""
        document = cached_document(self.step_source)
        product = self._select(document)
        shape = document.shape(product)

        adjust = getattr(self, 'adjust', None)
        if adjust is not None:
            shape = adjust(shape)

        self._require_admissible(shape, product)

        return shape

    def _select(self, document):
        if self.part is None:
            candidates = document.candidates()
            if len(candidates) == 1:
                return candidates[0]
            raise ValueError(self._selection_error(
                document,
                f'holds {len(candidates)} candidate products, so `part` '
                f'must name one of them'))

        matches = document.find(self.part)
        if not matches:
            raise ValueError(self._selection_error(
                document, f'has no product named {self.part!r}'))
        if len(matches) > 1:
            raise ValueError(self._ambiguity_error(document, matches))
        return matches[0]

    def _selection_error(self, document, complaint):
        return (
            f'{self.name}: {self.step_source} {complaint}. It holds '
            f'{len(document.order)} products; declare `part = "<name>"` to '
            f'select one, indexing this inventory:\n{document.inventory()}')

    def _ambiguity_error(self, document, matches):
        lines = '\n'.join(document.describe(match) for match in matches)
        return (
            f'{self.name}: {self.step_source} has {len(matches)} products '
            f'named {self.part!r}; the name is ambiguous between:\n{lines}')

    def _require_admissible(self, shape, product):
        if shape.Solids():
            return
        raise ValueError(
            f'{self.name}: {self.step_source} part {product.display_name!r} '
            f'holds no solid -- {len(shape.Shells())} shells and '
            f'{len(shape.Faces())} faces. Nothing is repaired '
            f'automatically; correct it in adjust(), for example with '
            f'solids_from_faces().')


##############################################
# Assembly structure: StepAssembly, a reader, not a node
#
# StepNode above reads one product in its OWN frame and says nothing
# about where the document places it. This section reads the other
# half: the occurrence walk, the placement and world matrices, and the
# exact decomposition into the framework's own rotate-then-translate
# pair (design D1-D3 of step-assembly-import).

#: Tolerance for the propriety gate (design D5): a placement whose
#: rotation-block determinant or scale factor strays this far from 1
#: is a mirror or a scale, which `Rotation`/`Translation` cannot state.
_PROPRIETY_TOLERANCE = 1e-9

#: Below this angle (radians) a rotation is reported as the identity,
#: with a stated axis rather than whatever arbitrary direction OCCT's
#: quaternion carries for a zero turn (design D2, fact 5).
_ZERO_ANGLE_TOLERANCE = 1e-9


class ProductInfo:
    """One entry of `StepAssembly.products`: a product of the document,
    however many times it is placed (spec "document's assembly
    structure")."""

    __slots__ = ('name', 'kind', 'occurrence_count', 'solid_count', 'color')

    def __init__(self, name, kind, occurrence_count, solid_count, color):
        self.name = name
        self.kind = kind
        self.occurrence_count = occurrence_count
        self.solid_count = solid_count
        self.color = color

    def __repr__(self):
        return (f'ProductInfo(name={self.name!r}, kind={self.kind!r}, '
               f'occurrence_count={self.occurrence_count}, '
               f'solid_count={self.solid_count}, color={self.color!r})')


class Occurrence:
    """One entry of `StepAssembly.occurrences`: one placement of one
    product in the document (spec "every occurrence of the document is
    walked").

    `identity` is the component label's own `_entry` -- already a
    globally unique path within the document (design D3), because
    `TDF_Tool.Entry_s` reports the full tag chain from the document
    root, not a name. It is never the label name, which is absent or
    meaningless depending on the writer (design fact 3).

    `angle_deg`, `axis` and `translation` are None when `proper` is
    False (design D5): a mirror or a scale cannot be stated as the
    framework's `rotate`/`translate` pair.
    """

    __slots__ = ('identity', 'label_name', 'product_name', 'parent_name',
                'matrix', 'world_matrix', 'color', 'proper', 'determinant',
                'scale_factor', 'angle_deg', 'axis', 'translation')

    def __init__(self, identity, label_name, product_name, parent_name,
                matrix, world_matrix, color, proper, determinant,
                scale_factor, angle_deg, axis, translation):
        self.identity = identity
        self.label_name = label_name
        self.product_name = product_name
        self.parent_name = parent_name
        self.matrix = matrix
        self.world_matrix = world_matrix
        self.color = color
        self.proper = proper
        self.determinant = determinant
        self.scale_factor = scale_factor
        self.angle_deg = angle_deg
        self.axis = axis
        self.translation = translation

    def __repr__(self):
        return (f'Occurrence(product_name={self.product_name!r}, '
               f'parent_name={self.parent_name!r}, proper={self.proper})')


def _trsf_matrix(trsf):
    """The 4x4 matrix `trsf` states, exactly as the document carries
    it -- `Value(i, j)` for the 3x4 rigid (or scaled) block (design
    fact 1)."""
    matrix = np.eye(4)
    for i in range(3):
        for j in range(4):
            matrix[i, j] = trsf.Value(i + 1, j + 1)
    return matrix


def _propriety(matrix, trsf):
    """`(proper, determinant, scale_factor)` for a placement matrix
    (design D5). Both raw values are always returned, whether or not
    the placement is proper, so the report can name what is wrong."""
    determinant = float(np.linalg.det(matrix[:3, :3]))
    scale_factor = trsf.ScaleFactor()
    proper = (abs(determinant - 1.0) <= _PROPRIETY_TOLERANCE and
             abs(scale_factor - 1.0) <= _PROPRIETY_TOLERANCE)
    return proper, determinant, scale_factor


def _positive_axis(angle_deg, axis):
    """The determinism convention (design D2, ratification note): state
    the axis whose largest-magnitude component is positive, negating
    the angle to match. The same rotation either way; the same document
    always yields the same literals."""
    largest = max(range(3), key=lambda index: abs(axis[index]))
    if axis[largest] < 0:
        return -angle_deg, tuple(-component for component in axis)
    return angle_deg, axis


def _decompose(trsf):
    """`(angle_deg, axis, translation)` reproducing `trsf` through the
    framework's own `Rotation(angle, axis).matrix()` then
    `Translation(translation).matrix()` (design D2): OCCT's own
    quaternion, never trace-and-acos, so a 180 degree turn round-trips
    (design fact 5).

    Call only on a proper placement -- an improper one has no rotation
    to extract (design D5).
    """
    quaternion = trsf.GetRotation()
    vec = gp_Vec()
    # The OCP binding returns the angle as a ONE-ELEMENT TUPLE, writing
    # the axis into `vec` (design fact 11): unpacking any other shape
    # fails at runtime.
    (angle,) = quaternion.GetVectorAndAngle(vec)
    angle_deg = math.degrees(angle)

    if abs(angle_deg) <= math.degrees(_ZERO_ANGLE_TOLERANCE):
        # A zero rotation carries an arbitrary axis (design fact 5);
        # state one rather than publish whatever OCCT happened to keep.
        angle_deg = 0.0
        axis = (0.0, 0.0, 1.0)
    else:
        norm = math.sqrt(vec.X() ** 2 + vec.Y() ** 2 + vec.Z() ** 2)
        axis = (vec.X() / norm, vec.Y() / norm, vec.Z() / norm)
        angle_deg, axis = _positive_axis(angle_deg, axis)

    translation = (trsf.Value(1, 4), trsf.Value(2, 4), trsf.Value(3, 4))
    return angle_deg, axis, translation


#: The identity decomposition, for the one occurrence with no wrapping
#: component label at all: a bare file holding a single part and no
#: assembly (spec "a one-part file is one occurrence").
_IDENTITY_DECOMPOSITION = (0.0, (0.0, 0.0, 1.0), (0.0, 0.0, 0.0))


def _solid_count(document, product):
    """`product`'s own solid count, read from the shared shape rather
    than through `_Document.shape()`'s protective copy (design D4,
    fact 8): counting topology never meshes, so there is nothing the
    copy needs to protect here, and paying it would cost 163x on a
    large document."""
    shape = cq.Shape.cast(document.shape_tool.GetShape_s(product.label))
    return len(shape.Solids())


class StepAssembly:
    """A STEP document's assembly structure: every product, every
    occurrence walked through nested sub-assemblies, and the exact
    rotate/translate pair each proper placement decomposes to.

    Not a node: it declares no geometry, writes no artifact, and joins
    no tracked source set. It reads `path` through the same per-file
    cache `StepNode` uses (`cached_document`), so a process that has
    already read the file for a `StepNode` pays nothing more to read
    its structure, and a process that has not pays the read exactly
    once::

        assembly = StepAssembly('vendor/actuator.stp')
        for product in assembly.products:
            print(product.name, product.kind, product.occurrence_count)
        for occurrence in assembly.occurrences:
            print(occurrence.product_name, occurrence.angle_deg,
                 occurrence.axis, occurrence.translation)
    """

    def __init__(self, path):
        self.path = os.path.realpath(path)
        document = cached_document(self.path)
        self._document = document

        self.products = []
        #: The first free product the document lists, in document order
        #: -- the document's own root, whether OCCT calls it a `part`
        #: (a bare single-part file) or an assembly. `None` only for a
        #: document with no free product at all, which nothing in this
        #: reader expects but which is safer to represent than to
        #: raise on.
        self.root = None
        for entry in document.order:
            raw_product = document.products[entry]
            info = ProductInfo(
                name=raw_product.name,
                kind=raw_product.kind,
                occurrence_count=document.occurrences(raw_product),
                solid_count=_solid_count(document, raw_product),
                color=document.color(raw_product),
            )
            self.products.append(info)
            if raw_product.is_free and self.root is None:
                self.root = info

        self.occurrences = []
        for entry in document.order:
            product = document.products[entry]
            if product.is_free:
                self._walk(document, product, np.eye(4))

    def _walk(self, document, product, world):
        """Append one `Occurrence` per component of `product`, then
        recurse into every component that is itself an assembly,
        composing `world` outward (design D3: `world = parent_world @
        local`). `world` is `product`'s own world matrix -- identity
        for a free root."""
        if not product.is_assembly:
            # A bare file: one product, no assembly root at all (spec
            # "a one-part file is one occurrence"). There is no
            # component label to identify it by, so its own product
            # entry is the identity.
            angle_deg, axis, translation = _IDENTITY_DECOMPOSITION
            self.occurrences.append(Occurrence(
                identity=product.entry, label_name='',
                product_name=product.name, parent_name=None,
                matrix=np.eye(4), world_matrix=world, color=None,
                proper=True, determinant=1.0, scale_factor=1.0,
                angle_deg=angle_deg, axis=axis, translation=translation))
            return

        parent_name = None if product.is_free else product.name

        components = TDF_LabelSequence()
        document.shape_tool.GetComponents_s(product.label, components)
        for index in range(1, components.Length() + 1):
            component = components.Value(index)
            referred = TDF_Label()
            is_reference = document.shape_tool.GetReferredShape_s(
                component, referred)
            target = referred if is_reference else component
            target_entry = _entry(target)
            target_product = document.products.get(target_entry)
            if target_product is None:
                # Same over-approximation as `_Document.__init__`: a
                # malformed reference to a label GetShapes() never
                # listed is skipped rather than raised on.
                continue

            trsf = document.shape_tool.GetLocation_s(component).Transformation()
            local_matrix = _trsf_matrix(trsf)
            world_matrix = world @ local_matrix
            proper, determinant, scale_factor = _propriety(local_matrix, trsf)
            if proper:
                angle_deg, axis, translation = _decompose(trsf)
            else:
                angle_deg = axis = translation = None

            self.occurrences.append(Occurrence(
                identity=_entry(component),
                # Empty, not None, when the writer left the component
                # label unnamed (spec: "its reported label name is
                # empty rather than standing in as its identity").
                label_name=_label_name(component) or '',
                product_name=target_product.name,
                parent_name=parent_name,
                matrix=local_matrix,
                world_matrix=world_matrix,
                color=document._label_color(component),
                proper=proper, determinant=determinant,
                scale_factor=scale_factor,
                angle_deg=angle_deg, axis=axis, translation=translation))

            if target_product.is_assembly:
                self._walk(document, target_product, world_matrix)
