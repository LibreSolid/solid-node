# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""`StepAssembly`: the document's placements, read and decomposed.

`StepNode` (the previous cycle) reads one product in its OWN frame and
says nothing about where the document places it. This module tests the
other half: the occurrence walk through nested sub-assemblies, the
placement and world matrices, the exact quaternion decomposition into
the framework's own `rotate`-then-`translate` pair, and the propriety
gate that refuses a mirror or a scale.

No binary STEP is committed, exactly as `test_step_node.py`'s fixtures:
every document here is authored with `cadquery.Assembly` and exported to
a temporary build directory by `setUpModule()` below.
"""

import math
import os
import tempfile
from unittest import TestCase, skipUnless
from unittest.mock import patch

import cadquery as cq
import numpy as np
from OCP.gp import gp_Ax1, gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec

from solid_node.node.adapters.step import STEPCAFControl_Reader, StepAssembly
from solid_node.node.operations import Rotation, Translation
from solid_node.node.adapters import step as step_module

from .step_project import parts as _parts_module


PROJECT = os.path.dirname(os.path.realpath(_parts_module.__file__))

NESTED_TWO_LEVEL_STEP = os.path.join(PROJECT, 'nested_two_level.step')
AWKWARD_NAMES_STEP = os.path.join(PROJECT, 'awkward_names.step')

#: The actuator's own file, read-only input for tasks 3.2 and 4.2 --
#: not committed to this repository, so the tests it feeds are skipped
#: when it is absent.
ACTUATOR_STEP = (
    '/home/asa/devel/libresolid-studio/projects/'
    'Internal-Cycloidal-Actuator/simulation/actuator/vendor/'
    'Internal Cycloidal Actuator.stp')


def build_nested_two_level(path):
    """A part at (10, 0, 0) inside a sub-assembly turned 90 degrees
    about X and carried to (0, 20, 0) -- design fact 6's own numbers.
    The same product ('Shared') is placed a second time directly at
    the root, purely by translation, so it is a product at two depths
    AND the pure-translation case in one fixture. A third part is
    turned a full 180 degrees, and the sub-assembly's own component
    label is left unnamed by `cadquery.Assembly` (design fact 3), so
    no separate authoring is needed for that scenario either.
    """
    root = cq.Assembly(name='Root')
    sub = cq.Assembly(name='Sub')
    shared = cq.Workplane('XY').box(2, 2, 2)
    sub.add(shared, name='Shared', loc=cq.Location(cq.Vector(10, 0, 0)))
    root.add(sub, name='Sub',
             loc=cq.Location(cq.Vector(0, 20, 0), cq.Vector(1, 0, 0), 90))
    root.add(shared, name='Shared', loc=cq.Location(cq.Vector(500, 0, 0)))
    root.add(cq.Workplane('XY').box(3, 3, 3), name='HalfTurned',
            loc=cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), 180))
    root.export(path, exportType='STEP')


def build_awkward_names(path):
    """Product names shaped exactly as design fact 10 records --
    leading digit, embedded space, embedded `x`-dimension, a trailing
    digit meeting a leading digit -- plus two products whose names
    derive one class name, for the collision suffix (task 1.2)."""
    root = cq.Assembly(name='Root')
    root.add(cq.Workplane('XY').box(1, 1, 1), name='10010 Stator')
    root.add(cq.Workplane('XY').box(2, 2, 2), name='40x50x6mm_Bearing')
    root.add(cq.Workplane('XY').box(3, 3, 3), name='M4_12mm_Screw')
    root.add(cq.Workplane('XY').box(4, 4, 4), name='ODrive_S1')
    root.add(cq.Workplane('XY').box(5, 5, 5), name='Widget!')
    root.add(cq.Workplane('XY').box(6, 6, 6), name='Widget#')
    root.export(path, exportType='STEP')


def setUpModule():
    build_nested_two_level(NESTED_TWO_LEVEL_STEP)
    build_awkward_names(AWKWARD_NAMES_STEP)


class ColdCacheTestCase(TestCase):
    """A cold document cache per test: the cache is process-scoped, so
    a read-count assertion must not inherit another test's warm entry."""

    def setUp(self):
        step_module._document_cache.clear()


##############################################
# Section 1: the products of the document


class StepAssemblyProductsTest(ColdCacheTestCase):

    def test_products_report_name_kind_occurrences_solids_colour(self):
        assembly = StepAssembly(NESTED_TWO_LEVEL_STEP)

        by_name = {product.name: product for product in assembly.products}

        self.assertEqual(by_name['Root'].kind, 'root assembly')
        self.assertEqual(by_name['Sub'].kind, 'sub-assembly')
        self.assertEqual(by_name['Shared'].kind, 'part')
        self.assertEqual(by_name['HalfTurned'].kind, 'part')
        self.assertEqual(by_name['HalfTurned'].occurrence_count, 1)
        self.assertEqual(by_name['HalfTurned'].solid_count, 1)

    def test_a_product_placed_several_times_appears_once(self):
        assembly = StepAssembly(NESTED_TWO_LEVEL_STEP)

        matches = [product for product in assembly.products
                  if product.name == 'Shared']

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].occurrence_count, 2)

    def test_the_reader_is_not_a_node(self):
        """Constructing a StepAssembly writes no artifact and joins no
        tracked source set -- it has no `files`, no `build_dir`, no
        `assemble()` at all."""
        assembly = StepAssembly(NESTED_TWO_LEVEL_STEP)

        self.assertFalse(hasattr(assembly, 'files'))
        self.assertFalse(hasattr(assembly, 'assemble'))

    def test_the_document_is_read_through_the_shared_cache(self):
        """A StepAssembly constructed over a file already read into the
        shared cache -- by a StepNode or by an earlier StepAssembly --
        performs no further transfer (spec "the document is read
        once")."""
        step_module.cached_document(NESTED_TWO_LEVEL_STEP)

        with patch.object(step_module, 'STEPCAFControl_Reader',
                          side_effect=AssertionError(
                              'must not read the document again')):
            StepAssembly(NESTED_TWO_LEVEL_STEP)

    def test_constructing_it_costs_one_read_of_the_reader(self):
        with patch.object(step_module, 'STEPCAFControl_Reader',
                          side_effect=STEPCAFControl_Reader) as reader:
            StepAssembly(NESTED_TWO_LEVEL_STEP)

        self.assertEqual(reader.call_count, 1)


##############################################
# Section 2: the occurrence walk


class StepAssemblyOccurrenceWalkTest(ColdCacheTestCase):

    def _occurrences(self, product_name):
        assembly = StepAssembly(NESTED_TWO_LEVEL_STEP)
        return [occurrence for occurrence in assembly.occurrences
               if occurrence.product_name == product_name]

    def test_nested_placements_compose_outward(self):
        """design fact 6: a part at (10, 0, 0) inside a sub-assembly
        turned 90 degrees about X and carried to (0, 20, 0) reports a
        world translation of (10, 20, 0)."""
        assembly = StepAssembly(NESTED_TWO_LEVEL_STEP)
        inner = next(o for o in assembly.occurrences
                    if o.product_name == 'Shared' and
                    o.parent_name == 'Sub')

        self.assertEqual(inner.translation, (10.0, 0.0, 0.0))
        np.testing.assert_allclose(inner.world_matrix[:3, 3],
                                   [10.0, 20.0, 0.0], atol=1e-9)

    def test_a_product_placed_at_two_depths_is_two_occurrences(self):
        occurrences = self._occurrences('Shared')

        self.assertEqual(len(occurrences), 2)
        parents = {occurrence.parent_name for occurrence in occurrences}
        self.assertEqual(parents, {'Sub', None})

        assembly = StepAssembly(NESTED_TWO_LEVEL_STEP)
        product = next(p for p in assembly.products if p.name == 'Shared')
        self.assertEqual(product.occurrence_count, 2)

    def test_an_unnamed_component_still_has_a_distinguishable_identity(self):
        """design fact 3: `cadquery.Assembly` names the PRODUCT label,
        not the COMPONENT label carrying an occurrence's own placement
        -- so `label_name` must never be an occurrence's identity, and
        every occurrence must still be distinguishable without it.

        IMPLEMENTATION NOTE (evidence against the ratified spec text):
        the spec's scenario says the reported label name is empty
        ('') for a component the writer leaves unnamed. On this
        fixture `cadquery.Assembly`'s actual behaviour is inconsistent
        rather than uniformly blank: the nested occurrence's component
        label carries its own placeholder ('2'), distinct from the
        product name, while the fixture's ROOT-level occurrence of the
        same product ('Shared', added directly to the root assembly)
        reads back with its component label ALSO named 'Shared' --
        cadquery's exporter does not leave every component label
        equally uninformative. Neither shape is the empty string the
        scenario specifies. The reader still honours the normative
        half of the requirement this scenario exists for -- identity
        is never derived from a label name, at any nesting depth -- so
        this is flagged as a spec/design discrepancy for the reviewer
        rather than papered over by rewriting a real label into an
        empty one.
        """
        assembly = StepAssembly(NESTED_TWO_LEVEL_STEP)

        identities = {occurrence.identity for occurrence in assembly.occurrences}
        self.assertEqual(len(identities), len(assembly.occurrences))
        for occurrence in assembly.occurrences:
            self.assertIsInstance(occurrence.label_name, str)

    def test_a_one_part_file_is_one_occurrence_at_the_identity(self):
        single = os.path.join(PROJECT, 'bare_single_product.step')
        cq.exporters.export(cq.Workplane('XY').box(4, 4, 4), single)

        assembly = StepAssembly(single)

        self.assertEqual(len(assembly.occurrences), 1)
        occurrence = assembly.occurrences[0]
        self.assertEqual(occurrence.angle_deg, 0.0)
        self.assertEqual(occurrence.translation, (0.0, 0.0, 0.0))
        self.assertTrue(occurrence.proper)

    def test_an_occurrence_does_not_inherit_its_products_colour(self):
        coloured_path = os.path.join(PROJECT, 'assembly_coloured.step')
        root = cq.Assembly(name='Root')
        root.add(cq.Workplane('XY').box(2, 2, 2), name='ColouredPart',
                color=cq.Color(0.9, 0.1, 0.1))
        root.export(coloured_path, exportType='STEP')

        assembly = StepAssembly(coloured_path)
        product = next(p for p in assembly.products
                      if p.name == 'ColouredPart')
        occurrence = next(o for o in assembly.occurrences
                          if o.product_name == 'ColouredPart')

        self.assertIsNotNone(product.color)
        self.assertIsNone(occurrence.color)


##############################################
# Section 3: the decomposition


def _shepperd_quaternion(matrix):
    """An independent reference decomposition (design D2's rejected
    alternative), branching on the largest of the trace and the three
    diagonal entries -- used only to cross-check the reader's own
    OCCT-quaternion route (task 3.3), never as the implementation."""
    m = matrix[:3, :3]
    trace = m[0, 0] + m[1, 1] + m[2, 2]
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    return w, x, y, z


def _shepperd_matrix(matrix):
    """The pure-rotation matrix a Shepperd-decomposed quaternion
    reproduces, for the 1e-12 cross-check (task 3.3): compare
    matrices, not literals, since the two conventions may sign the
    axis differently."""
    w, x, y, z = _shepperd_quaternion(matrix)
    angle = 2 * math.atan2(math.sqrt(x * x + y * y + z * z), w)
    norm = math.sqrt(x * x + y * y + z * z)
    if norm < 1e-12:
        return np.eye(3)
    axis = (x / norm, y / norm, z / norm)
    return trimesh_rotation(angle, axis)


def trimesh_rotation(angle, axis):
    import trimesh
    return trimesh.transformations.rotation_matrix(angle, axis)[:3, :3]


class StepAssemblyDecompositionTest(ColdCacheTestCase):

    def _round_trip(self, occurrence):
        rotation = Rotation(occurrence.angle_deg, list(occurrence.axis))
        translation = Translation(list(occurrence.translation))
        return translation.matrix() @ rotation.matrix()

    def test_every_occurrence_of_the_fixture_round_trips(self):
        assembly = StepAssembly(NESTED_TWO_LEVEL_STEP)

        for occurrence in assembly.occurrences:
            with self.subTest(product=occurrence.product_name,
                              parent=occurrence.parent_name):
                composed = self._round_trip(occurrence)
                np.testing.assert_allclose(
                    composed, occurrence.matrix, atol=1e-9)

    def test_a_half_turn_round_trips(self):
        assembly = StepAssembly(NESTED_TWO_LEVEL_STEP)
        half_turn = next(o for o in assembly.occurrences
                        if o.product_name == 'HalfTurned')

        self.assertAlmostEqual(abs(half_turn.angle_deg), 180.0, places=6)
        composed = self._round_trip(half_turn)
        np.testing.assert_allclose(composed, half_turn.matrix, atol=1e-9)

    def test_an_unrotated_placement_is_a_zero_angle(self):
        assembly = StepAssembly(NESTED_TWO_LEVEL_STEP)
        translated_only = next(o for o in assembly.occurrences
                              if o.product_name == 'Shared' and
                              o.parent_name is None)

        self.assertEqual(translated_only.angle_deg, 0.0)
        norm = math.sqrt(sum(c * c for c in translated_only.axis))
        self.assertAlmostEqual(norm, 1.0, places=9)
        self.assertEqual(translated_only.translation, (500.0, 0.0, 0.0))

    def test_the_decomposition_is_deterministic(self):
        first = StepAssembly(NESTED_TWO_LEVEL_STEP)
        step_module._document_cache.clear()
        second = StepAssembly(NESTED_TWO_LEVEL_STEP)

        for one, two in zip(first.occurrences, second.occurrences):
            self.assertEqual(one.angle_deg, two.angle_deg)
            self.assertEqual(one.axis, two.axis)
            self.assertEqual(one.translation, two.translation)

    def test_cross_check_against_an_independent_shepperd_decomposition(self):
        """task 3.3: the reader's decomposition agrees with a Shepperd-
        method reference implementation to 1e-12, AS ROTATIONS -- the
        two conventions may sign the axis oppositely."""
        assembly = StepAssembly(NESTED_TWO_LEVEL_STEP)

        for occurrence in assembly.occurrences:
            reader_rotation = Rotation(
                occurrence.angle_deg, list(occurrence.axis)).matrix()[:3, :3]
            reference_rotation = _shepperd_matrix(occurrence.matrix)
            np.testing.assert_allclose(
                reader_rotation, reference_rotation, atol=1e-12)

    @skipUnless(os.path.exists(ACTUATOR_STEP),
               'Internal-Cycloidal-Actuator vendor STEP not present')
    def test_all_55_actuator_placements_round_trip_to_1e_minus_9(self):
        assembly = StepAssembly(ACTUATOR_STEP)

        self.assertEqual(len(assembly.occurrences), 55)
        worst = 0.0
        for occurrence in assembly.occurrences:
            self.assertTrue(occurrence.proper, occurrence.product_name)
            composed = self._round_trip(occurrence)
            worst = max(worst, float(np.max(np.abs(
                composed - occurrence.matrix))))

        self.assertLess(worst, 1e-9)
        # design fact 5: the quaternion route's worst case is ~4.4e-16,
        # thirty orders below the trace route's 3.0e-8 -- a regression
        # to the naive extraction must fail here, not in a project.
        self.assertLess(worst, 1e-12)


##############################################
# Section 4: the propriety gate


class PropertyGateUnitTest(TestCase):
    """The gate itself (design D5), tested directly on constructed
    `gp_Trsf`s rather than through a written-and-reread document.

    EMPIRICAL FINDING (evidence against the ratified design/spec text):
    design.md and the spec both assume a mirrored or scaled *occurrence*
    placement is authorable in a STEP fixture ("The fixtures author one
    by placing a mirrored shape"). It is not, through this framework's
    own write path or through raw XCAF calls: `STEPCAFControl_Writer`
    resets a component's location to the identity on write whenever the
    attached `gp_Trsf` is a mirror (`SetMirror`) or carries a uniform
    scale (`SetScale`), confirmed both through `cadquery.Assembly.add
    (..., loc=cq.Location(trsf))` and through raw
    `XCAFDoc_ShapeTool.AddComponent(..., TopLoc_Location(trsf))` --
    `STEPCAFControl_Reader` reads back the identity in both cases. This
    is not an OCCT bug so much as a structural fact about the mechanism
    STEP's `NEXT_ASSEMBLY_USAGE_OCCURRENCE` occurrences use: a
    component's placement is the *relative transform between two
    `AXIS2_PLACEMENT_3D` frames*, each necessarily right-handed by
    construction (its "Y" axis is always the cross product of the axis
    and the reference direction it declares), so the relative transform
    between any two such frames is always proper. An improper placement
    could in principle still arrive in a *different* document -- one
    using STEP's `CARTESIAN_TRANSFORMATION_OPERATOR_3D`/`MAPPED_ITEM`
    mechanism instead of NAUO, which does support an explicit
    reflection -- so the gate is real and worth keeping; there is
    simply no way, discovered in this session, to author the fixture
    the design and spec both describe. Flagged for the reviewer rather
    than silently dropped or worked around with an unwritten fixture.
    """

    def test_a_mirror_is_improper_with_its_determinant(self):
        trsf = gp_Trsf()
        trsf.SetMirror(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)))
        matrix = step_module._trsf_matrix(trsf)

        proper, determinant, scale_factor = step_module._propriety(matrix, trsf)

        self.assertFalse(proper)
        self.assertAlmostEqual(determinant, -1.0, places=9)

    def test_a_scale_is_improper_with_its_scale_factor(self):
        trsf = gp_Trsf()
        trsf.SetScale(gp_Pnt(0, 0, 0), 2.0)
        matrix = step_module._trsf_matrix(trsf)

        proper, determinant, scale_factor = step_module._propriety(matrix, trsf)

        self.assertFalse(proper)
        self.assertAlmostEqual(scale_factor, 2.0, places=9)

    def test_a_proper_rotation_and_translation_is_proper(self):
        trsf = gp_Trsf()
        trsf.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)),
                         math.radians(37.0))
        trsf.SetTranslationPart(gp_Vec(1, 2, 3))
        matrix = step_module._trsf_matrix(trsf)

        proper, determinant, scale_factor = step_module._propriety(matrix, trsf)

        self.assertTrue(proper)
        self.assertAlmostEqual(determinant, 1.0, places=9)
        self.assertAlmostEqual(scale_factor, 1.0, places=9)

    def test_an_improper_occurrence_is_not_decomposed_by_the_walk(self):
        """The walk itself (design D5): an occurrence the gate marks
        improper carries no angle/axis/translation, and the rest of the
        document is still walked -- proved by forcing exactly one
        occurrence of a real, all-proper fixture through the improper
        branch, since no real improper fixture is authorable (see the
        class docstring above)."""
        real_propriety = step_module._propriety
        calls = []

        def fake_propriety(matrix, trsf):
            proper, determinant, scale_factor = real_propriety(matrix, trsf)
            calls.append(1)
            if len(calls) == 1:
                return False, -1.0, 1.0
            return proper, determinant, scale_factor

        with patch.object(step_module, '_propriety', side_effect=fake_propriety):
            assembly = StepAssembly(NESTED_TWO_LEVEL_STEP)

        improper = [o for o in assembly.occurrences if not o.proper]
        proper = [o for o in assembly.occurrences if o.proper]

        self.assertEqual(len(improper), 1)
        self.assertIsNone(improper[0].angle_deg)
        self.assertIsNone(improper[0].axis)
        self.assertIsNone(improper[0].translation)
        self.assertAlmostEqual(improper[0].determinant, -1.0, places=9)
        # The rest of the document -- three occurrences -- is unaffected.
        self.assertEqual(len(proper), 3)
        self.assertEqual(len(assembly.products), 4)

    @skipUnless(os.path.exists(ACTUATOR_STEP),
               'Internal-Cycloidal-Actuator vendor STEP not present')
    def test_the_actuator_document_has_no_improper_placement(self):
        assembly = StepAssembly(ACTUATOR_STEP)

        improper = [o for o in assembly.occurrences if not o.proper]
        self.assertEqual(improper, [])


##############################################
# Section 5: awkward names read back verbatim


class StepAssemblyAwkwardNamesTest(ColdCacheTestCase):

    def test_every_awkward_name_reads_back_exactly(self):
        assembly = StepAssembly(AWKWARD_NAMES_STEP)

        names = {product.name for product in assembly.products}
        for expected in ('10010 Stator', '40x50x6mm_Bearing',
                        'M4_12mm_Screw', 'ODrive_S1', 'Widget!', 'Widget#'):
            self.assertIn(expected, names)
