import os
import tempfile
from contextlib import chdir
from unittest import TestCase

from solid_node.core.loader import (AmbiguousNodeError, ProjectManifestError,
                                    discover_project, load_node, resolve_node)


SOURCE = '''from solid_node.node import Solid2Node
class Sail(Solid2Node):
    def render(self): return None
class Hull(Solid2Node):
    def render(self): return None
NODE = Sail
'''


class ProjectManifestReferenceTest(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = self.temp.name
        os.mkdir(os.path.join(self.root, 'boat'))
        open(os.path.join(self.root, 'boat', '__init__.py'), 'w').close()
        with open(os.path.join(self.root, 'boat', 'model.py'), 'w') as stream:
            stream.write(SOURCE)
        with open(os.path.join(self.root, 'pyproject.toml'), 'w') as stream:
            stream.write('[tool.solid-node]\nmodel = "boat.model:Sail"\n')

    def test_nearest_manifest_and_reference_spellings(self):
        subdir = os.path.join(self.root, 'boat')
        with chdir(subdir):
            root, model = discover_project()
            by_qualifier, _, _ = resolve_node('boat.model:Sail')
            by_path, _, _ = resolve_node('model.py:Sail')
        self.assertEqual(root, self.root)
        self.assertEqual(model, 'boat.model:Sail')
        self.assertIs(by_qualifier, by_path)

    def test_no_reference_resolves_the_manifest_model(self):
        """The shared resolution every node-scoped command funnels into: with
        no reference, the manifest's `model` names the node. Asserted from a
        subdirectory as well as the root, because the manifest -- not the
        working directory -- is what says which node is the project's."""
        for cwd in (self.root, os.path.join(self.root, 'boat')):
            with self.subTest(cwd=cwd), chdir(cwd):
                klass, path, root = resolve_node()
                self.assertEqual(klass.__name__, 'Sail')
                self.assertEqual(root, self.root)
                self.assertEqual(
                    os.path.realpath(path),
                    os.path.realpath(os.path.join(self.root, 'boat', 'model.py')))
                self.assertEqual(load_node().__class__.__name__, 'Sail')

    def test_bare_multi_class_path_ignores_retired_marker(self):
        with chdir(self.root):
            with self.assertRaises(AmbiguousNodeError) as error:
                resolve_node('boat/model.py')
        self.assertIn('Sail', str(error.exception))
        self.assertIn('Hull', str(error.exception))

    def test_bare_single_class_and_invalid_targets(self):
        with open(os.path.join(self.root, 'boat', 'sail.py'), 'w') as stream:
            stream.write(SOURCE.replace('class Hull(Solid2Node):\n    def render(self): return None\n', ''))
        with chdir(self.root):
            klass, _, _ = resolve_node('boat/sail.py')
            self.assertEqual(klass.__name__, 'Sail')
            with self.assertRaises(ProjectManifestError):
                resolve_node('boat.model:missing')
            with self.assertRaises(ProjectManifestError):
                resolve_node('solid_node.node.leaf:Leaf')

    def test_missing_manifest_names_search_origin(self):
        with tempfile.TemporaryDirectory() as empty, chdir(empty):
            with self.assertRaises(ProjectManifestError) as error:
                discover_project()
        self.assertIn(empty, str(error.exception))

    def test_a_path_names_its_own_project_not_the_callers(self):
        """A path identifies a project as surely as it identifies a file. If
        discovery keyed on the working directory instead, a path in another
        project would resolve against the caller's root and be rejected as
        foreign -- and a repository holding fixture projects would have to
        declare itself a project to reach them."""
        with tempfile.TemporaryDirectory() as elsewhere:
            os.mkdir(os.path.join(elsewhere, 'shed'))
            open(os.path.join(elsewhere, 'shed', '__init__.py'), 'w').close()
            with open(os.path.join(elsewhere, 'shed', 'sail.py'), 'w') as stream:
                stream.write('from solid_node.node import Solid2Node\n'
                             'class Sail(Solid2Node):\n'
                             '    def render(self): return None\n')
            with open(os.path.join(elsewhere, 'pyproject.toml'), 'w') as stream:
                stream.write('[tool.solid-node]\nmodel = "shed.sail:Sail"\n')

            # Standing in one project, naming a file in another.
            with chdir(self.root):
                klass, path, root = resolve_node(
                    os.path.join(elsewhere, 'shed', 'sail.py'))

        self.assertEqual(os.path.realpath(root), os.path.realpath(elsewhere))
        self.assertEqual(klass.__name__, 'Sail')
