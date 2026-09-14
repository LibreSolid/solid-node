# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Every export the documentation embeds must be produced by something.

A ``.. solid-node::`` directive names a directory that `solid export`
produced, and the Sphinx extension fails the build if it is not there.
Those directories arrive two different ways:

* the small tutorial models are committed under ``docs/_exports/``;
* the two example machines are built during the documentation build,
  into the example submodules, by a step written twice -- once in
  ``.readthedocs.yaml`` and once in the GitHub Actions ``docs`` job.

Nothing links those three files, so an example can be embedded and
taught to Read the Docs while the Actions job is never told to build it.
It then fails on the export it does not have, because Sphinx runs there
with ``-W``. That is exactly how the Metamaquina 2 example landed: the
directive, the submodule and the Read the Docs steps were added
together, and the workflow was missed.

These tests close the loop, so the failure surfaces in the suite rather
than in a documentation build. They also hold the built machines one to
a page: each directive is an <iframe> running a viewer, so a page
carrying two of them opens two.
"""

import os
import re
import unittest
from collections import Counter
from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / 'docs'
WORKFLOW = REPO / '.github' / 'workflows' / 'python-app.yml'
READTHEDOCS = REPO / '.readthedocs.yaml'

# Committed exports live here; anything else a directive names is built
# during the documentation build.
COMMITTED = 'docs/_exports/'

# Only a directive at column 0 asks for an export. embedding.rst indents
# one inside a literal block to show the syntax and changelog.rst names
# it in prose; neither is a request to build anything.
DIRECTIVE = re.compile(r'^\.\. +solid-node:: +(\S+)', re.MULTILINE)

# The output directory of a `solid export` command, however the command
# is spelled -- both build configurations drive the CLI through
# `python -c "from solid_node.cli import manage; manage()"`.
EXPORT_OUTPUT = re.compile(r'\bexport\s+-o\s+(\S+)')

# `cd <dir> && ...`, which is how .readthedocs.yaml chooses the
# directory a command runs in; the workflow uses `working-directory`.
LEADING_CD = re.compile(r'\s*cd\s+(\S+)\s*&&')

# Mirrors exclude_patterns in docs/conf.py: _build is output and the
# examples are separate repositories with their own documentation.
NOT_OUR_DOCS = ('_build', 'examples')


def embedded_exports():
    """(document, export directory) for every directive in the docs.

    Paths are repo-relative, resolved the way the directive resolves
    them: against the document, or against the Sphinx source directory
    when the argument is absolute.
    """
    found = []
    for rst in sorted(DOCS.rglob('*.rst')):
        relative = rst.relative_to(DOCS)
        if relative.parts[0] in NOT_OUR_DOCS:
            continue
        for target in DIRECTIVE.findall(rst.read_text()):
            base = DOCS if target.startswith('/') else rst.parent
            export = Path(os.path.normpath(base / target.lstrip('/')))
            found.append((relative.as_posix(),
                          export.relative_to(REPO).as_posix()))
    return found


def _outputs(workdir, command):
    """Export directories `command` writes, relative to the repository."""
    return {
        Path(os.path.normpath(Path(workdir) / output)).as_posix()
        for output in EXPORT_OUTPUT.findall(command)
    }


def actions_exports():
    """Export directories the GitHub Actions docs job generates."""
    workflow = yaml.safe_load(WORKFLOW.read_text())
    generated = set()
    for step in workflow['jobs']['docs']['steps']:
        generated |= _outputs(step.get('working-directory', '.'),
                              step.get('run', ''))
    return generated


def readthedocs_exports():
    """Export directories the Read the Docs build generates."""
    jobs = yaml.safe_load(READTHEDOCS.read_text())['build']['jobs']
    generated = set()
    for command in jobs.get('pre_build', []):
        cd = LEADING_CD.match(command)
        generated |= _outputs(cd.group(1) if cd else '.', command)
    return generated


class DocumentationExportsTest(unittest.TestCase):
    """The documentation and both build configurations must agree on
    which exports exist and who makes them."""

    def setUp(self):
        self.embedded = embedded_exports()
        self.actions = actions_exports()
        self.readthedocs = readthedocs_exports()

    def test_directives_are_found(self):
        """Guards the other tests from passing on an empty scan."""
        self.assertTrue(
            self.embedded,
            f'No `.. solid-node::` directives found under {DOCS}. Either '
            'the documentation stopped embedding exports or DIRECTIVE no '
            'longer matches how they are written.',
        )

    def test_committed_exports_exist(self):
        """An export under docs/_exports/ is committed, so it is there."""
        for document, export in self.embedded:
            if not export.startswith(COMMITTED):
                continue
            with self.subTest(document=document, export=export):
                path = REPO / export
                self.assertTrue(
                    path.is_dir(),
                    f'docs/{document} embeds {export}, which is committed '
                    'documentation content but is missing. Restore it, or '
                    'regenerate it with `solid export`.',
                )
                self.assertTrue(
                    (path / 'manifest.json').is_file(),
                    f'docs/{document} embeds {export}, which has no '
                    'manifest.json, so it is not a `solid export` output '
                    'the directive can read.',
                )

    def test_generated_exports_are_built_by_both_configurations(self):
        """An export built at documentation-build time has to be built by
        every configuration that builds the documentation."""
        for document, export in self.embedded:
            if export.startswith(COMMITTED):
                continue
            with self.subTest(document=document, export=export):
                self.assertIn(
                    export, self.actions,
                    f'docs/{document} embeds {export}, which is not '
                    'committed and which no step of the docs job in '
                    f'{WORKFLOW.relative_to(REPO)} generates. Sphinx runs '
                    'there with -W, so that job fails on the missing '
                    'export. Add a step that exports it to that path.',
                )
                self.assertIn(
                    export, self.readthedocs,
                    f'docs/{document} embeds {export}, which is not '
                    'committed and which no pre_build command in '
                    f'{READTHEDOCS.relative_to(REPO)} generates, so the '
                    'published documentation is missing it. Add a command '
                    'that exports it to that path.',
                )

    def test_build_configurations_agree(self):
        """Catches a step added to one configuration only, before any
        directive depends on it."""
        self.assertEqual(
            self.actions, self.readthedocs,
            f'{WORKFLOW.relative_to(REPO)} and '
            f'{READTHEDOCS.relative_to(REPO)} build different sets of '
            'exports. Both build the same documentation, so they have to '
            'produce the same directories.',
        )


    def test_generated_exports_get_a_page_each(self):
        """A machine built for the docs is the whole point of its page.

        Every directive is an <iframe> running a viewer, and the two
        example machines are the largest models published here. Two of
        them on one page start two viewers and animate both at once,
        which is how the examples page used to open.
        """
        embedded = [(document, export) for document, export in self.embedded
                    if not export.startswith(COMMITTED)]
        pages = Counter(document for document, _ in self.embedded)

        for document, export in embedded:
            with self.subTest(document=document, export=export):
                self.assertEqual(
                    pages[document], 1,
                    f'docs/{document} embeds {export}, a machine built '
                    'during the documentation build, alongside '
                    f'{pages[document] - 1} other model(s). Each one '
                    'starts its own viewer, so give the machine a page '
                    'of its own and leave the page it came from linking '
                    'to it.',
                )

        for export, count in Counter(e for _, e in embedded).items():
            with self.subTest(export=export):
                self.assertEqual(
                    count, 1,
                    f'{export} is embedded by {count} documents. It is '
                    'built once, for one page; a second page embedding '
                    'it means a reader can load it twice over.',
                )


if __name__ == '__main__':
    unittest.main()


class EmbeddedExportVersionWarningTest(unittest.TestCase):
    """(7.4b) The directive embeds a COMMITTED export it does not
    produce and cannot fix. It warns about a version the installed
    viewer cannot read and does not fail the build -- and it reads the
    version off the manifest it already opened, loading no CAD runtime
    to do it."""

    def warned(self, manifest, versions):
        from unittest.mock import Mock, patch

        from solid_node import sphinx as sphinx_module

        directive = sphinx_module.SolidNode.__new__(sphinx_module.SolidNode)
        logger = Mock()
        with patch.object(sphinx_module, 'logger', logger), \
             patch.object(sphinx_module.viewer_bundle, 'document_versions',
                          return_value=versions):
            directive.warn_unreadable('docs/export', manifest)
        return logger

    def test_an_embedded_version_five_export_warns(self):
        logger = self.warned({'format': 'solid-node-export', 'version': 5},
                             [1, 2, 3, 4])
        self.assertEqual(logger.warning.call_count, 1)
        message = logger.warning.call_args[0][0]
        self.assertIn('docs/export', message)
        self.assertIn('5', message)
        self.assertIn('1, 2, 3, 4', message)

    def test_an_export_the_viewer_can_read_warns_about_nothing(self):
        logger = self.warned({'format': 'solid-node-export', 'version': 5},
                             [1, 2, 3, 4, 5])
        logger.warning.assert_not_called()

    def test_the_extension_loads_no_cad_runtime(self):
        import ast
        import inspect

        from solid_node import sphinx as sphinx_module

        tree = ast.parse(inspect.getsource(sphinx_module))
        modules = {node.module for node in ast.walk(tree)
                   if isinstance(node, ast.ImportFrom) and node.module}
        modules |= {alias.name for node in ast.walk(tree)
                    if isinstance(node, ast.Import) for alias in node.names}
        heavy = {name for name in modules
                 if name.startswith('solid_node.')
                 and not name.startswith('solid_node.viewers')}
        self.assertEqual(heavy, set(), heavy)
