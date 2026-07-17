# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import re

from unittest import TestCase
from solid2 import cube
from solid_node.node import Solid2Node
from solid_node.node.base import _build_uniq_id
from .base import BaseNodeTest


class _KlassA:
    pass


class _KlassB:
    pass


class BuildUniqIdTest(TestCase):
    """Direct unit tests for _build_uniq_id(klass, args, kwargs) under
    the ratified scheme (skill-repo improvements.md #3 + #13 + #22):
    the key is ALWAYS class-and-parameter-derived (never name=),
    formatted as <readable-prefix>-<shorthash>, where shorthash is a
    sha256 of the full canonical serialization and prefix is a
    bounded, filesystem-safe truncation of it -- so basename length
    never depends on parameter size. #22 adds the class's __qualname__
    to the hashed identity, ahead of args/kwargs: without it, two
    DIFFERENT no-arg classes defined in the same file both serialized
    to the empty string and collided on one cached artifact (see
    DistinctClassesSameFileBuildTest below for that lie demonstrated
    end to end).
    """

    def test_same_args_and_kwargs_give_identical_id(self):
        a = _build_uniq_id(_KlassA, (10, 5), {'color': 'red'})
        b = _build_uniq_id(_KlassA, (10, 5), {'color': 'red'})
        self.assertEqual(a, b)

    def test_any_parameter_change_gives_a_different_id(self):
        base = _build_uniq_id(_KlassA, (10, 5), {})
        changed_positional = _build_uniq_id(_KlassA, (10, 6), {})
        changed_kwarg = _build_uniq_id(_KlassA, (10, 5), {'color': 'red'})
        self.assertNotEqual(base, changed_positional)
        self.assertNotEqual(base, changed_kwarg)

    def test_kwarg_order_does_not_affect_id(self):
        a = _build_uniq_id(_KlassA, (), {'a': 1, 'b': 2})
        b = _build_uniq_id(_KlassA, (), {'b': 2, 'a': 1})
        self.assertEqual(a, b)

    def test_positional_and_keyword_calls_do_not_collide(self):
        # Regression for B9: Node(5, 10) and Node(height=5, radius=10)
        # used to render as the same string, silently sharing one .stl
        # path even though they represent different geometry.
        positional = _build_uniq_id(_KlassA, (5, 10), {})
        keyword = _build_uniq_id(_KlassA, (), {'height': 5, 'radius': 10})
        self.assertNotEqual(positional, keyword)

    def test_name_is_not_an_input(self):
        # _build_uniq_id never even sees name= -- AbstractBaseNode.__init__
        # does not pass it through. Assert the contract at this level too:
        # two calls with identical args/kwargs always agree, regardless of
        # what name a caller might separately assign the instance.
        a = _build_uniq_id(_KlassA, (1, 2), {'x': 3})
        b = _build_uniq_id(_KlassA, (1, 2), {'x': 3})
        self.assertEqual(a, b)

    def test_long_list_kwarg_yields_a_bounded_basename(self):
        # Regression for #13: a 200-element float list used to serialize
        # verbatim into the filename, blowing the 255-byte filesystem
        # limit (hit in practice by a wall parametrized with per-gear tip
        # circles). The hash-keyed basename must stay well under it
        # regardless of parameter size.
        profile = [i * 0.1 for i in range(200)]
        uniq_id = _build_uniq_id(_KlassA, (), {'profile': profile})
        basename = f'some_script-{uniq_id}'
        self.assertLess(len(basename.encode()), 255)

    def test_no_args_no_kwargs_still_gets_a_class_derived_id(self):
        # Regression for #22: a no-arg node used to get uniq_id == ''
        # (the bare script basename) -- identity came from args/kwargs
        # alone, so any two no-arg classes in the same file collided.
        # The class is now always part of the canonical serialization,
        # so even a no-arg node's id is never empty, and differs by
        # class.
        a = _build_uniq_id(_KlassA, (), {})
        b = _build_uniq_id(_KlassB, (), {})
        self.assertNotEqual(a, '')
        self.assertNotEqual(b, '')
        self.assertNotEqual(a, b)

    def test_same_class_no_args_still_shares_an_id(self):
        # Two instances of the SAME no-arg class must still agree --
        # #22 only needed to add the class to the key, not stop
        # genuinely-identical calls from sharing a cached artifact.
        a = _build_uniq_id(_KlassA, (), {})
        b = _build_uniq_id(_KlassA, (), {})
        self.assertEqual(a, b)

    def test_prefix_contains_only_filesystem_safe_chars(self):
        uniq_id = _build_uniq_id(
            _KlassA, (), {'profile': [1, 2, 3], 'label': 'a b/c'})
        prefix = uniq_id.rsplit('-', 1)[0]
        self.assertRegex(prefix, r'^[A-Za-z0-9_,=.-]*$')


class _ArgsNode(Solid2Node):
    """A minimal node that forwards args/kwargs straight through to the
    base node, unlike flat_project.SimpleCylinder (which always forwards
    positionally to super().__init__ regardless of how it itself was
    called). This is what makes a positional vs. keyword call collide
    under the old _build_uniq_id."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def render(self):
        return cube(1)


class UniqIdCollisionTest(BaseNodeTest):

    def test_positional_and_keyword_calls_get_different_ids(self):
        positional = _ArgsNode(5, 10)
        keyword = _ArgsNode(height=5, radius=10)

        self.assertNotEqual(positional.uniq_id, keyword.uniq_id)
        self.assertNotEqual(positional.stl_file, keyword.stl_file)

    def test_keyword_call_order_does_not_affect_uniq_id(self):
        a = _ArgsNode(a=1, b=2)
        b = _ArgsNode(b=2, a=1)

        self.assertEqual(a.uniq_id, b.uniq_id)


class _SizedCube(Solid2Node):
    """Forwards name= to the base node (unlike tests/meta_project.parts.
    Cube's pre-#3 signature), so it can demonstrate the name/uniq_id
    decoupling directly."""

    def __init__(self, size=1.0, name=None):
        self.size = size
        super().__init__(size=size, name=name)

    def render(self):
        return cube(self.size, center=True)


class NamedNodeUniqIdTest(BaseNodeTest):

    def test_name_does_not_influence_uniq_id(self):
        named = _SizedCube(size=2.0, name='whatever')
        unnamed = _SizedCube(size=2.0)
        self.assertEqual(named.uniq_id, unnamed.uniq_id)

    def test_no_arg_node_basename_is_class_derived_not_bare_script(self):
        # Superseded by #22: a no-arg node's basename used to be the
        # BARE script name (uniq_id == ''), which is exactly what let
        # two different no-arg classes in the same file collide (see
        # DistinctClassesSameFileBuildTest). It now always carries a
        # class-derived suffix, but still starts with the script name.
        node = _ArgsNode()
        script = re.sub(r'\.py$', '', node.src.split('/')[-1])
        basename = os.path.basename(node.basepath)
        self.assertNotEqual(basename, script)
        self.assertTrue(basename.startswith(f'{script}-'))
        self.assertIn('_ArgsNode', basename)


class SameNameDifferentParamsBuildTest(BaseNodeTest):
    """The real lie (skill-repo improvements.md #3): on the OLD
    framework, name= REPLACED the parameter-based artifact key, so two
    same-named instances with different parameters collided on one stl
    file -- whichever built second served its geometry to both. Same-
    name siblings also collide in the viewer's tree (a separate open
    issue, #16), so this is asserted at build level rather than as a
    meta fixture: build both via assemble()+build_stls() and compare
    mesh volumes directly.
    """

    def test_same_name_different_sizes_get_independent_meshes(self):
        small = _SizedCube(size=1.0, name='dup')
        big = _SizedCube(size=2.0, name='dup')

        small.assemble()
        small.build_stls()
        big.assemble()
        big.build_stls()

        self.assertAlmostEqual(small.mesh.volume, 1.0, delta=0.02)
        self.assertAlmostEqual(big.mesh.volume, 8.0, delta=0.05)


class _NoArgSmallCube(Solid2Node):
    """A no-arg node -- volume 1."""

    def render(self):
        return cube(1, center=True)


class _NoArgBigCube(Solid2Node):
    """A DIFFERENT no-arg node, defined in this same file -- volume 8.
    Before #22, both this class and _NoArgSmallCube serialized to the
    identical empty canonical string (no args/kwargs, and the class
    itself was not part of the key), so they collided on the bare
    script-name artifact."""

    def render(self):
        return cube(2, center=True)


class DistinctClassesSameFileBuildTest(BaseNodeTest):
    """The lie improvements.md #22 fixes, discovered while building
    volume_epsilon's (#21) flush-shoulder meta fixture: two DIFFERENT
    node classes, both taking no constructor args, defined in the
    same source file, silently shared one cached STL -- uniq_id was
    derived only from args/kwargs (never the class), so both got the
    same empty key and the same bare-script-name basename. Whichever
    built second served its geometry to both. Modeled on
    SameNameDifferentParamsBuildTest (#3): build both via
    assemble()+build_stls() and compare mesh volumes directly, rather
    than as a meta fixture (a same-basename collision is a build-
    level lie, not something the tree/test-naming layer sees)."""

    def test_distinct_no_arg_classes_get_independent_artifacts_and_meshes(self):
        small = _NoArgSmallCube()
        big = _NoArgBigCube()

        self.assertNotEqual(small.uniq_id, big.uniq_id)
        self.assertNotEqual(small.stl_file, big.stl_file)

        small.assemble()
        small.build_stls()
        big.assemble()
        big.build_stls()

        self.assertAlmostEqual(small.mesh.volume, 1.0, delta=0.02)
        self.assertAlmostEqual(big.mesh.volume, 8.0, delta=0.05)
