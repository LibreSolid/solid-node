# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The STEP leaf: a vendor B-rep as a first-class part.

STEP is the format every CAD package and every vendor publishes, and
until this leaf the framework could not read one. Two projects
(`Internal-Cycloidal-Actuator` and `openvmp`) wrote the same reader by
hand: `STEPCAFControl_Reader` into an XCAF document, a walk of the
document's products to find one by name, and a document cache to avoid
paying the read cost -- 11.79 s on the actuator's own file -- more than
once per build.

`StepNode` is `StlNode`'s three rules -- admitted not assumed, selected
not guessed, corrected in code -- over a solid instead of a mesh, and it
is exact where `StlNode` is faceted: a STEP product is a B-rep the
moment it is read, so this leaf derives `ExactLeafNode` and inherits its
whole contract (`exact`, `shape()`, the `.brep`, and an `as_scad` that
needs no external tool).

No binary STEP is committed. Every fixture is authored with
`cadquery.Assembly` or `cq.exporters.export` and saved into
`tests/step_project/` (gitignored) by `setUpModule()` below, exactly as
`tests/stl_project`'s meshes are (design D11 of the `step-part-leaf`
change) -- the round trip itself is the evidence, and it proves every
case this change specifies is authorable without a vendor file:
duplicate names need two assembly levels (cadquery.Assembly refuses two
same-named siblings), a face-only product is a `cq.Shell`, and a
single-product file needs `cq.exporters.export` rather than an
assembly.
"""

import os
import tempfile
import time
from unittest import TestCase
from unittest.mock import patch

import cadquery as cq
import trimesh

from solid_node.exact import cached_shape
from solid_node.node import StepNode
from solid_node.node.adapters import step as step_module
from solid_node.node.adapters.step import STEPCAFControl_Reader

from .step_project import assemblies, parts
from .utils import edit_source


PROJECT = os.path.dirname(os.path.realpath(parts.__file__))
PARTS_MODULE = os.path.realpath(parts.__file__)
DIMENSIONS_MODULE = os.path.join(PROJECT, 'dimensions.py')

SINGLE_PRODUCT_STEP = os.path.join(PROJECT, 'single_product.step')
WRAPPED_SINGLE_PART_STEP = os.path.join(PROJECT, 'wrapped_single_part.step')
TWO_PRODUCTS_STEP = os.path.join(PROJECT, 'two_products.step')
REPEATED_PRODUCT_STEP = os.path.join(PROJECT, 'repeated_product.step')
NESTED_ASSEMBLY_STEP = os.path.join(PROJECT, 'nested_assembly.step')
DUPLICATE_NAMES_STEP = os.path.join(PROJECT, 'duplicate_names.step')
FACE_ONLY_STEP = os.path.join(PROJECT, 'face_only.step')
CURVED_STEP = os.path.join(PROJECT, 'curved.step')

#: The exact colour `two_products.step`'s `ColouredPart` is authored
#: with -- cadquery's own convention stores this straight into the
#: file's sRGB `COLOUR_RGB`, so this is what a correct round trip must
#: read back (design D7, fact 5).
COLOURED_PART_RGB = (0.9, 0.1, 0.1)


def _channels(hex_color):
    code = hex_color.lstrip('#')
    return tuple(int(code[i:i + 2], 16) for i in (0, 2, 4))


def _assert_close_colour(test, actual_hex, expected_rgb):
    """`actual_hex` matches `expected_rgb` within the STEP text's own
    round-trip precision.

    Not exact equality: the STEP file stores a truncated decimal
    (`COLOUR_RGB('', 0.899999998185, ...)`), and the linear/sRGB
    conversion (design D7, fact 5) is the inverse of a lossy forward
    conversion, so the channel that started as 0.9 comes back a hair
    under it -- close enough to round to the same byte, but not
    guaranteed to for a channel sitting on a rounding boundary. What
    must hold is that the deviation is a rounding hair, not the ~12%
    a raw-linear (unconverted) reading would show.
    """
    actual = _channels(actual_hex)
    expected = tuple(round(255 * channel) for channel in expected_rgb)
    for got, wanted in zip(actual, expected):
        test.assertLessEqual(abs(got - wanted), 1,
                             f'{actual_hex} too far from {expected_rgb}')


def build_single_product(path):
    """A bare file: one product, no assembly root at all (fact 8)."""
    cq.exporters.export(cq.Workplane('XY').box(5, 5, 5), path)


def build_wrapped_single_part(path):
    """An assembly root wrapping exactly one part -- the commoner shape
    an exporter actually produces (fact 8)."""
    root = cq.Assembly(name='Wrapper')
    root.add(cq.Workplane('XY').box(6, 6, 6), name='SoloPart')
    root.export(path, exportType='STEP')


def build_two_products(path):
    """A root wrapping two products: one coloured, one not."""
    root = cq.Assembly(name='TwoProducts')
    root.add(cq.Workplane('XY').box(4, 4, 4), name='ColouredPart',
             color=cq.Color(*COLOURED_PART_RGB))
    root.add(cq.Workplane('XY').box(2, 2, 2), name='PlainPart')
    root.export(path, exportType='STEP')


def build_repeated_product(path):
    """One product placed at two occurrences far apart, and far from its
    own (centred-on-origin) frame -- so a test can tell the part's own
    frame apart from either occurrence (fact 2, design D4)."""
    root = cq.Assembly(name='RepeatedHolder')
    part = cq.Workplane('XY').box(3, 3, 3)
    root.add(part, name='Repeated', loc=cq.Location(cq.Vector(200, 0, 0)))
    root.add(part, name='RepeatedFar', loc=cq.Location(cq.Vector(500, 0, 0)))
    root.export(path, exportType='STEP')


def build_nested_assembly(path):
    """A sub-assembly ('Gearbox'), placed away from the origin by its
    parent, holding one part at its own internal offset (fact 3)."""
    root = cq.Assembly(name='Root')
    gearbox = cq.Assembly(name='Gearbox')
    gearbox.add(cq.Workplane('XY').box(2, 2, 2), name='Gear',
               loc=cq.Location(cq.Vector(3, 0, 0)))
    root.add(gearbox, name='Gearbox', loc=cq.Location(cq.Vector(100, 0, 0)))
    root.add(cq.Workplane('XY').box(1, 1, 1), name='OtherPart')
    root.export(path, exportType='STEP')


def build_duplicate_names(path):
    """Two distinct products sharing one name, in two sub-assemblies --
    `cadquery.Assembly` refuses two same-named siblings, so duplication
    needs two levels (fact 7)."""
    root = cq.Assembly(name='Root')
    sub1 = cq.Assembly(name='Sub1')
    sub1.add(cq.Workplane('XY').box(1, 1, 1), name='Pin')
    sub2 = cq.Assembly(name='Sub2')
    sub2.add(cq.Workplane('XY').box(2, 2, 2), name='Pin')
    root.add(sub1, name='Sub1')
    root.add(sub2, name='Sub2')
    root.export(path, exportType='STEP')


def build_face_only(path):
    """A product carrying only faces: a `cq.Shell` missing one face of a
    box, openvmp's hook and battery in miniature (fact 6)."""
    box = cq.Workplane('XY').box(2, 2, 2).val()
    shell = cq.Shell.makeShell(box.Faces()[:-1])
    root = cq.Assembly(name='ShellHolder')
    root.add(cq.Workplane(obj=shell), name='OpenShell')
    root.export(path, exportType='STEP')


def build_curved(path):
    """A curved solid, so angular deflection actually shapes the mesh."""
    cq.exporters.export(cq.Workplane('XY').sphere(5), path)


def setUpModule():
    build_single_product(SINGLE_PRODUCT_STEP)
    build_wrapped_single_part(WRAPPED_SINGLE_PART_STEP)
    build_two_products(TWO_PRODUCTS_STEP)
    build_repeated_product(REPEATED_PRODUCT_STEP)
    build_nested_assembly(NESTED_ASSEMBLY_STEP)
    build_duplicate_names(DUPLICATE_NAMES_STEP)
    build_face_only(FACE_ONLY_STEP)
    build_curved(CURVED_STEP)


def realpaths(node):
    return {os.path.realpath(path) for path in node.files}


class BuildDirTestCase(TestCase):
    """A fresh build directory per test, and a cold document cache: the
    cache is process-scoped, so a test asserting on read counts must not
    inherit another test's warm entry."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.previous_build_dir = os.environ.get('SOLID_BUILD_DIR')
        os.environ['SOLID_BUILD_DIR'] = self.directory.name
        step_module._document_cache.clear()

    def tearDown(self):
        if self.previous_build_dir is None:
            os.environ.pop('SOLID_BUILD_DIR', None)
        else:
            os.environ['SOLID_BUILD_DIR'] = self.previous_build_dir

    def keep_times(self, path):
        times = (os.path.getatime(path), os.path.getmtime(path))
        self.addCleanup(os.utime, path, times)

    def inventory_error(self, NodeClass):
        with self.assertRaises(Exception) as raised:
            NodeClass().assemble()
        return str(raised.exception)


##############################################
# Section 2: declaration, freshness, selection


class StepSourceDeclarationTest(BuildDirTestCase):
    """What the node declares, and what makes its artifact stale."""

    def test_the_declared_file_resolves_beside_the_wrapper_module(self):
        node = parts.SingleProduct()

        self.assertEqual(os.path.realpath(node.get_source_file()),
                         SINGLE_PRODUCT_STEP)
        self.assertEqual(os.path.realpath(node.src), SINGLE_PRODUCT_STEP)

    def test_the_artifacts_mirror_the_source_location(self):
        node = parts.SingleProduct()

        self.assertEqual(node.basedir, PROJECT)
        self.assertEqual(os.path.basename(node.build_dir),
                         os.path.basename(PROJECT))
        self.assertTrue(node.stl_file.startswith(self.directory.name))

    def test_a_missing_declaration_fails_naming_the_class(self):
        with self.assertRaises(Exception) as raised:
            parts.UndeclaredPart()

        self.assertIn('UndeclaredPart', str(raised.exception))
        self.assertIn('step_source', str(raised.exception))

    def test_editing_the_step_file_invalidates_the_artifact(self):
        self.keep_times(SINGLE_PRODUCT_STEP)
        built = parts.SingleProduct()
        built.assemble()
        self.assertTrue(built._up_to_date(built.stl_file))

        edit_source(self, SINGLE_PRODUCT_STEP)
        future = time.time() + 10
        os.utime(SINGLE_PRODUCT_STEP, (future, future))

        self.assertFalse(parts.SingleProduct()._up_to_date(built.stl_file))

    def test_editing_the_wrapper_invalidates_the_artifact(self):
        self.keep_times(PARTS_MODULE)
        built = parts.ScaledSingleProduct()
        built.assemble()
        self.assertTrue(built._up_to_date(built.stl_file))

        edit_source(self, PARTS_MODULE)
        future = time.time() + 10
        os.utime(PARTS_MODULE, (future, future))

        self.assertFalse(
            parts.ScaledSingleProduct()._up_to_date(built.stl_file))

    def test_the_wrapper_module_is_tracked(self):
        self.assertIn(PARTS_MODULE, realpaths(parts.SingleProduct()))

    def test_a_module_the_wrapper_imports_is_tracked(self):
        self.assertIn(os.path.realpath(DIMENSIONS_MODULE),
                      realpaths(parts.ScaledSingleProduct()))

    def test_a_current_artifact_is_not_rewritten_and_the_document_is_not_read(self):
        """A colour declared on the class bypasses the document
        entirely (design D7), which is what lets this test prove the
        geometry side of currency without entangling colour laziness.
        """
        node = parts.OpaqueSingleProduct()
        node.assemble()

        second = parts.OpaqueSingleProduct()
        with patch.object(step_module, 'STEPCAFControl_Reader',
                          side_effect=AssertionError(
                              'must not read the document again')):
            second.assemble()

        self.assertTrue(os.path.exists(second.stl_file))


##############################################
# Section 2 (continued): selection


class StepSelectionTest(BuildDirTestCase):
    """Choosing one product out of the document, and the inventory that
    teaches a developer what the file holds."""

    def test_a_bare_single_product_file_needs_no_selection(self):
        node = parts.SingleProduct()

        node.assemble()

        self.assertTrue(node._up_to_date(node.stl_file))
        self.assertAlmostEqual(node.shape().Volume(), 125.0, places=3)

    def test_one_part_wrapped_in_an_assembly_needs_no_selection(self):
        node = parts.WrappedSinglePart()

        node.assemble()

        self.assertAlmostEqual(node.shape().Volume(), 216.0, places=3)

    def test_several_candidates_without_part_reports_the_inventory(self):
        message = self.inventory_error(parts.UnselectedTwoProducts)

        self.assertIn('ColouredPart', message)
        self.assertIn('PlainPart', message)
        self.assertNotIn('TwoProducts', message.split(':', 1)[1].split('\n')[0])

    def test_the_inventory_carries_one_line_per_product(self):
        message = self.inventory_error(parts.UnselectedTwoProducts)

        self.assertIn('part', message)
        self.assertIn('occurrence', message)
        self.assertIn('solid', message)
        self.assertIn('bounds', message)
        self.assertIn('volume', message)

    def test_naming_the_root_explicitly_still_selects_it(self):
        node = parts.WholeTwoProductAssembly()

        node.assemble()

        self.assertEqual(len(node.shape().Solids()), 2)

    def test_a_name_the_file_does_not_carry_reports_the_inventory(self):
        message = self.inventory_error(parts.MissingProduct)

        self.assertIn('NoSuchProduct', message)
        self.assertIn('ColouredPart', message)
        self.assertIn('PlainPart', message)

    def test_a_repeated_part_is_one_product_selected_without_ambiguity(self):
        node = parts.RepeatedProduct()

        node.assemble()

        self.assertAlmostEqual(node.shape().Volume(), 27.0, places=3)

    def test_a_repeated_part_is_one_inventory_line_with_its_occurrence_count(self):
        message = self.inventory_error(parts.MissingProduct)
        # MissingProduct shares the two_products.step file, which places
        # neither product more than once; the occurrence-count inventory
        # itself is asserted against the repeated-product file instead.
        document = step_module.cached_document(REPEATED_PRODUCT_STEP)
        inventory = document.inventory()

        self.assertIn('2 occurrences', inventory)

    def test_a_sub_assembly_is_a_selectable_product(self):
        node = parts.NestedGearbox()

        node.assemble()

        self.assertEqual(len(node.shape().Solids()), 1)
        self.assertAlmostEqual(node.shape().Volume(), 8.0, places=3)

    def test_an_ambiguous_name_is_refused_describing_both(self):
        message = self.inventory_error(parts.AmbiguousPin)

        self.assertIn('Pin', message)
        # The two Pins differ in size (1mm and 2mm cubes); both volumes
        # must be named so a reader can tell which is meant.
        self.assertIn('1.000', message)
        self.assertIn('8.000', message)


##############################################
# Section 3: frame, correction, admission


class StepFrameTest(BuildDirTestCase):
    """The product's own frame, never an occurrence's placed copy."""

    def test_two_occurrences_yield_one_unplaced_part(self):
        node = parts.RepeatedProduct()

        node.assemble()

        bounds = node.shape().BoundingBox()
        center = ((bounds.xmin + bounds.xmax) / 2,
                 (bounds.ymin + bounds.ymax) / 2,
                 (bounds.zmin + bounds.zmax) / 2)
        for value in center:
            self.assertAlmostEqual(value, 0.0, places=3)

    def test_a_selected_sub_assembly_is_unplaced_in_its_parent(self):
        node = parts.NestedGearbox()

        node.assemble()

        bounds = node.shape().BoundingBox()
        center = ((bounds.xmin + bounds.xmax) / 2,
                 (bounds.ymin + bounds.ymax) / 2,
                 (bounds.zmin + bounds.zmax) / 2)
        # The gear's own internal offset within the gearbox (3, 0, 0),
        # not the root's placement of the gearbox (100, 0, 0) nor their
        # sum.
        self.assertAlmostEqual(center[0], 3.0, places=3)
        self.assertAlmostEqual(center[1], 0.0, places=3)
        self.assertAlmostEqual(center[2], 0.0, places=3)


class StepAdjustTest(BuildDirTestCase):
    """Correction is code, not knobs."""

    def test_a_hook_correction_reaches_the_artifact(self):
        verbatim = parts.SingleProduct()
        verbatim.assemble()
        scaled = parts.ScaledSingleProduct()
        scaled.assemble()

        factor = parts.SCALE_FACTOR ** 3
        self.assertAlmostEqual(
            scaled.shape().Volume() / verbatim.shape().Volume(),
            factor, places=3)

    def test_a_node_without_the_hook_imports_the_product_verbatim(self):
        node = parts.SingleProduct()

        node.assemble()

        self.assertAlmostEqual(node.shape().Volume(), 125.0, places=3)

    def test_the_adapter_offers_no_scale_unit_recenter_or_sew_knob(self):
        self.assertFalse(hasattr(StepNode, 'scale'))
        self.assertFalse(hasattr(StepNode, 'unit'))
        self.assertFalse(hasattr(StepNode, 'recenter'))
        self.assertFalse(hasattr(StepNode, 'sew'))


class StepAdmissionTest(BuildDirTestCase):
    """Only a solid is admitted; nothing is repaired silently."""

    def test_a_face_only_product_is_rejected_naming_what_it_holds(self):
        node = parts.FaceOnlyPart()

        with self.assertRaises(Exception) as raised:
            node.assemble()

        message = str(raised.exception)
        self.assertIn('OpenShell', message)
        self.assertIn('face', message)
        self.assertIn('no solid', message)

    def test_a_rejected_product_leaves_no_artifact(self):
        node = parts.FaceOnlyPart()

        with self.assertRaises(Exception):
            node.assemble()

        self.assertFalse(os.path.exists(node.stl_file))

    def test_a_sewn_face_only_part_is_admitted(self):
        node = parts.SewnFaceOnlyPart()

        node.assemble()

        self.assertGreaterEqual(len(node.shape().Solids()), 1)

    def test_a_hook_that_returns_no_solid_is_still_rejected(self):
        node = parts.BrokenAdjustPart()

        with self.assertRaises(Exception) as raised:
            node.assemble()

        self.assertIn(node.name, str(raised.exception))
        self.assertFalse(os.path.exists(node.stl_file))


##############################################
# Section 4: colour


class StepColourTest(BuildDirTestCase):
    """A part's colour comes from the document, unless the node says
    otherwise."""

    def test_a_coloured_product_reads_back_as_its_colour(self):
        node = parts.ColouredPart()

        _assert_close_colour(self, node.color, COLOURED_PART_RGB)

    def test_the_naive_raw_linear_hex_encoding_would_be_wrong(self):
        """The regression design fact 5 exists to catch: hex-encoding
        the raw linear components XCAF hands back, rather than
        converting them to sRGB first, publishes a visibly darker
        colour."""
        node = parts.ColouredPart()

        raw_hex = '#%02x%02x%02x' % tuple(
            round(255 * channel) for channel in (0.787, 0.010, 0.010))
        self.assertNotEqual(node.color, raw_hex)

    def test_an_uncoloured_product_has_no_colour(self):
        node = parts.PlainPart()

        self.assertIsNone(node.color)

    def test_a_declared_colour_wins_and_never_opens_the_document(self):
        with patch.object(step_module, 'STEPCAFControl_Reader',
                          side_effect=AssertionError(
                              'a declared colour must not read the document')):
            node = parts.DeclaredColourPart()
            self.assertEqual(node.color, '#112233')

    def test_an_undeclared_colour_survives_ordinary_construction(self):
        """Constructing and assembling a node as a child of an assembly
        runs the framework's own node initialisation over it; that must
        not be mistaken for the subclass declaring `color = None`."""
        holder = assemblies.ColouredPartHolder()

        holder.assemble()

        _assert_close_colour(self, holder.child.color, COLOURED_PART_RGB)

    def test_a_current_node_with_declared_colour_reads_no_document(self):
        node = parts.DeclaredColourPart()
        node.assemble()

        second = parts.DeclaredColourPart()
        with patch.object(step_module, 'STEPCAFControl_Reader',
                          side_effect=AssertionError(
                              'must not read the document at all')):
            second.assemble()
            self.assertEqual(second.color, '#112233')


##############################################
# Section 5: one document read per file per process


class StepDocumentCacheTest(BuildDirTestCase):

    def _counting_reader(self):
        return patch.object(step_module, 'STEPCAFControl_Reader',
                            side_effect=STEPCAFControl_Reader)

    def test_many_nodes_over_one_file_cost_one_read(self):
        with self._counting_reader() as reader:
            parts.ColouredPart().assemble()
            parts.PlainPart().assemble()

        self.assertEqual(reader.call_count, 1)

    def test_a_replaced_file_evicts_and_is_read_again(self):
        with self._counting_reader() as reader:
            parts.ColouredPart().assemble()
            self.assertEqual(reader.call_count, 1)

            future = time.time() + 10
            build_two_products(TWO_PRODUCTS_STEP)
            os.utime(TWO_PRODUCTS_STEP, (future, future))

            parts.PlainPart().assemble()
            self.assertEqual(reader.call_count, 2)

        matching = [key for key in step_module._document_cache
                   if key[0] == TWO_PRODUCTS_STEP]
        self.assertEqual(len(matching), 1)

    def test_two_files_are_two_cache_entries(self):
        with self._counting_reader() as reader:
            parts.SingleProduct().assemble()
            parts.ColouredPart().assemble()

        self.assertEqual(reader.call_count, 2)
        paths = {key[0] for key in step_module._document_cache}
        self.assertEqual(paths, {SINGLE_PRODUCT_STEP, TWO_PRODUCTS_STEP})


##############################################
# Section 6: exactness and the deferred import


class StepExactnessTest(BuildDirTestCase):

    def test_exact_is_true_and_shape_is_the_selected_adjusted_geometry(self):
        node = parts.ScaledSingleProduct()

        self.assertTrue(node.exact)
        node.assemble()
        self.assertAlmostEqual(node.shape().Volume(),
                               125.0 * parts.SCALE_FACTOR ** 3, places=3)

    def test_a_fusion_over_a_step_node_is_exact_and_fuses_to_one_solid(self):
        fusion = assemblies.FusedWithStep()

        fusion.assemble()

        self.assertTrue(fusion.exact)
        self.assertEqual(len(fusion.shape().Solids()), 1)

    def test_the_brep_is_written_and_reloaded(self):
        node = parts.SingleProduct()

        node.assemble()

        self.assertTrue(os.path.exists(node.brep_file))
        reloaded = cached_shape(node.brep_file)
        self.assertAlmostEqual(reloaded.Volume(), 125.0, places=3)

    def test_a_project_of_step_leaves_builds_with_no_openscad_on_the_path(self):
        with patch('solid_node.openscad.shutil.which', return_value=None), \
             patch('solid_node.node.base.Popen', side_effect=AssertionError(
                 'no external renderer may be launched')):
            node = assemblies.TwoStepParts()
            node.build_stls()

        for child in node.children:
            self.assertTrue(os.path.exists(child.stl_file))


class StepDeflectionTest(BuildDirTestCase):

    def _triangles(self, path):
        return len(trimesh.load(path, process=False, file_type='stl').faces)

    def test_a_coarse_angular_declaration_yields_fewer_triangles_same_brep(self):
        default = parts.CurvedProduct()
        default.assemble()
        coarse = parts.CoarseCurvedProduct()
        coarse.assemble()

        self.assertLess(self._triangles(coarse.stl_file),
                        self._triangles(default.stl_file))

        with open(default.brep_file, 'rb') as handle:
            default_brep = handle.read()
        with open(coarse.brep_file, 'rb') as handle:
            coarse_brep = handle.read()
        self.assertEqual(default_brep, coarse_brep)


class StepDeferredImportTest(TestCase):

    def test_step_reader_is_the_real_ocp_class(self):
        # Sanity: the module-level name tests patch really is the OCP
        # reader class, so the cache and colour tests above are patching
        # the real dependency and not a framework-private shim.
        self.assertEqual(STEPCAFControl_Reader.__module__.split('.')[0],
                         'OCP')
