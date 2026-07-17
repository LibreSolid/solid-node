# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Sphinx extension embedding `solid export` output in documentation.

Add ``'solid_node.sphinx'`` to ``extensions`` in conf.py, then::

    .. solid-node:: path/to/export_dir
       :height: 300px
       :t: 0.25
       :autoplay: no

The argument is a directory produced by ``solid export`` (relative to
the current document, or to the source dir with a leading ``/``). The
directory is copied into the build output and embedded as an <iframe>
onto the widget's index.html; ``:t:`` (0..1) poses the animation and
``:autoplay: no`` starts it paused -- together they make a static
snapshot of one pose.

Exports made with ``--no-widget`` are completed at build time from the
installed package's widget files, so committed exports only need to
carry manifest.json and models/.
"""

import html
import json
import os
import re
import shutil

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
from sphinx.util.osutil import relative_uri

from solid_node import __version__

try:
    # Pulls in the framework's runtime dependencies; docs can build
    # without them as long as every export is self-contained
    from solid_node.core import export as core_export
except ImportError:
    core_export = None

logger = logging.getLogger(__name__)

# Kept in sync with solid_node.core.export.MANIFEST_FORMAT (asserted
# by tests); duplicated so the extension imports without the CAD stack
MANIFEST_FORMAT = 'solid-node-export'

# Directory under the HTML output where exports are copied
OUTPUT_DIR = '_solid_node'

WIDGET_FILES = ('index.html', 'solid-widget.js')

DEFAULT_HEIGHT = '480px'


def _time(argument):
    value = float(argument)
    if not 0 <= value <= 1:
        raise ValueError('expected a value between 0 and 1')
    # The original string goes verbatim into the query string
    return argument.strip()


def _height(argument):
    value = directives.length_or_unitless(argument)
    if re.fullmatch(r'\d+(\.\d+)?', value):
        value += 'px'
    return value


class solid_node_iframe(nodes.General, nodes.Element):
    pass


class SolidNode(SphinxDirective):
    """Embeds a `solid export` directory as an <iframe>."""

    required_arguments = 1
    option_spec = {
        'height': _height,
        't': _time,
        'autoplay': lambda arg: directives.choice(arg, ('yes', 'no')),
    }

    def run(self):
        rel_path, abs_path = self.env.relfn2path(self.arguments[0])

        if not os.path.isdir(abs_path):
            raise self.error(
                f'solid-node: no export directory at "{rel_path}". '
                'Generate it with: solid export <node.py> -o '
                f'{rel_path}'
            )

        manifest_path = os.path.join(abs_path, 'manifest.json')
        if not os.path.isfile(manifest_path):
            raise self.error(
                f'solid-node: "{rel_path}" has no manifest.json -- '
                'not a `solid export` output directory'
            )
        try:
            with open(manifest_path) as fh:
                manifest = json.load(fh)
        except ValueError:
            manifest = None
        if not isinstance(manifest, dict) \
           or manifest.get('format') != MANIFEST_FORMAT:
            raise self.error(
                f'solid-node: {rel_path}/manifest.json is not a '
                f'"{MANIFEST_FORMAT}" manifest'
            )

        # Rebuild this document when the export is regenerated
        self.env.note_dependency(os.path.join(rel_path, 'manifest.json'))

        dest = re.sub(r'[^\w.-]+', '-', rel_path)
        exports = getattr(self.env, 'solid_node_exports', None)
        if exports is None:
            exports = self.env.solid_node_exports = {}
        info = exports.setdefault(
            dest, {'path': abs_path, 'docnames': set()},
        )
        if info['path'] != abs_path:
            raise self.error(
                f'solid-node: exports "{info["path"]}" and '
                f'"{abs_path}" both map to output name "{dest}"'
            )
        info['docnames'].add(self.env.docname)

        params = []
        if 't' in self.options:
            params.append(f't={self.options["t"]}')
        if self.options.get('autoplay') == 'no':
            params.append('autoplay=0')

        node = solid_node_iframe(
            docname=self.env.docname,
            dest=dest,
            query='?' + '&'.join(params) if params else '',
            height=self.options.get('height', DEFAULT_HEIGHT),
        )
        return [node]


def visit_solid_node_iframe(self, node):
    page = f'{OUTPUT_DIR}/{node["dest"]}/index.html'
    src = relative_uri(
        self.builder.get_target_uri(node['docname']), page,
    ) + node['query']
    self.body.append(
        f'<iframe src="{html.escape(src)}" '
        f'style="width: 100%; height: {node["height"]}; border: 0;" '
        'loading="lazy"></iframe>\n'
    )
    raise nodes.SkipNode


def skip_node(self, node):
    raise nodes.SkipNode


def copy_exports(app):
    """html-collect-pages: copies every referenced export into the
    output, completing widget files from the package if the export
    was made with --no-widget."""
    exports = getattr(app.env, 'solid_node_exports', {})
    for dest, info in exports.items():
        target = os.path.join(app.outdir, OUTPUT_DIR, dest)
        shutil.copytree(info['path'], target, dirs_exist_ok=True)
        _complete_widget(target)
    return []


def _complete_widget(target):
    missing = [
        name for name in WIDGET_FILES
        if not os.path.exists(os.path.join(target, name))
    ]
    if not missing:
        return
    if core_export is None:
        logger.warning(
            f'solid-node: export at {target} lacks {missing} and '
            'solid_node\'s dependencies are not installed to supply '
            'them; install the full package, or export without '
            '--no-widget'
        )
        return
    sources = {
        'index.html': core_export.WIDGET_INDEX,
        'solid-widget.js': core_export.WIDGET_BUNDLE,
    }
    for name in missing:
        source = sources[name]
        if os.path.exists(source):
            shutil.copy2(source, os.path.join(target, name))
        else:
            logger.warning(f'solid-node: {core_export.WidgetBundleMissing()}')


def purge_exports(app, env, docname):
    exports = getattr(env, 'solid_node_exports', {})
    for dest in list(exports):
        exports[dest]['docnames'].discard(docname)
        if not exports[dest]['docnames']:
            del exports[dest]


def merge_exports(app, env, docnames, other):
    exports = getattr(env, 'solid_node_exports', None)
    if exports is None:
        exports = env.solid_node_exports = {}
    for dest, info in getattr(other, 'solid_node_exports', {}).items():
        target = exports.setdefault(
            dest, {'path': info['path'], 'docnames': set()},
        )
        target['docnames'].update(info['docnames'])


def setup(app):
    app.add_directive('solid-node', SolidNode)
    app.add_node(
        solid_node_iframe,
        # override: docutils registers visitors globally, so a second
        # Sphinx app in the same process (tests) would warn otherwise
        override=True,
        html=(visit_solid_node_iframe, None),
        latex=(skip_node, None),
        text=(skip_node, None),
        man=(skip_node, None),
        texinfo=(skip_node, None),
    )
    app.connect('env-purge-doc', purge_exports)
    app.connect('env-merge-info', merge_exports)
    app.connect('html-collect-pages', copy_exports)
    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
