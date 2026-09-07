"""Audit probes: create temporary projects, print observed behavior, and clean up.
Run with the project development environment; see README.md.
"""
import asyncio
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
ENV = dict(os.environ, PYTHONPATH=str(REPO), PYTHONDONTWRITEBYTECODE='1')
ENV.pop('SOLID_BUILD_DIR', None)
RESULTS = {}

def cli(root, *args):
    result = subprocess.run([sys.executable, '-c', 'from solid_node.cli import manage; manage()', *args], cwd=root, env=ENV, capture_output=True, text=True, timeout=90)
    return result

def project(root, code, manifest='model = "design.part:Part"'):
    (root / 'pyproject.toml').write_text('[tool.solid-node]\n' + manifest + '\n')
    (root / 'design').mkdir()
    (root / 'design/__init__.py').write_text('')
    (root / 'design/part.py').write_text(code)

GOOD = 'from solid_node.node import Solid2Node\nfrom solid2 import cube\nclass Part(Solid2Node):\n    def render(self):\n        return cube(1)\n'

with tempfile.TemporaryDirectory(prefix='solid-audit-') as directory:
    base = Path(directory)
    # Actual renderer failure, through the public CLI.
    root = base / 'renderer'; root.mkdir()
    project(root, 'from solid_node.node import OpenScadNode\nclass Part(OpenScadNode):\n    scad_source = "part.scad"\n')
    (root / 'design/part.scad').write_text('module part() { assert(false, "audit deliberate failure"); cube(1); }\n')
    result = cli(root, 'build')
    RESULTS['renderer_failure'] = dict(exitcode=result.returncode, stls=[(str(p.relative_to(root)), p.stat().st_size) for p in root.glob('_build/**/*.stl')], published=(root / '_build/viewer.json').exists(), errors=(root / '_build/errors.json').exists(), stderr=result.stderr[-2500:])

    # Same complete document after a transient failure.
    root = base / 'errors'; root.mkdir(); project(root, GOOD)
    first = cli(root, 'build')
    (root / '_build/errors.json').write_text('{"error": "previous transient failure", "tstamp": 0}')
    second = cli(root, 'build')
    RESULTS['stale_error'] = dict(first_exit=first.returncode, rebuild_exit=second.returncode, errors_remain=(root / '_build/errors.json').exists(), models=cli(root, 'models', '--json').stdout)

    # Export a path from outside the project (no model-name anchoring).
    result = cli(base, 'export', str(root / 'design/part.py'), '--no-widget', '-o', str(base / 'exported'))
    manifest_path = base / 'exported/manifest.json'
    RESULTS['external_export'] = dict(exitcode=result.returncode, model=json.loads(manifest_path.read_text())['root'].get('model') if manifest_path.exists() else None, files=[str(p.relative_to(base)) for p in base.rglob('*.stl')], stderr=result.stderr[-500:])

    # Unrelated sibling files must not be garbage collected.
    from solid_node.core.builder import prepare_build_dir
    root = base / 'cleanup'; root.mkdir()
    (root / '_build.notes').write_text('user notes')
    (root / '_build.backup').mkdir()
    (root / '_build.backup/keep.txt').write_text('user backup')
    prepare_build_dir(str(root / '_build'))
    RESULTS['cleanup'] = dict(notes_survive=(root / '_build.notes').exists(), backup_survives=(root / '_build.backup/keep.txt').exists())

    # Scaffold naming.
    result = cli(base, 'new', '3d-printer')
    scaffold = base / 'project_3d_printer'
    compile_result = cli(scaffold, 'build')
    RESULTS['numeric_scaffold'] = dict(new_exit=result.returncode, build_exit=compile_result.returncode, target=scaffold.name, source=(scaffold / 'project_3d_printer/project_3d_printer.py').read_text(), stderr=compile_result.stderr[-900:])

    # Max mtime collision despite a tracked helper's changed contents.
    root = base / 'mtime'; root.mkdir()
    project(root, 'from solid_node.node import Solid2Node\nfrom solid2 import cube\nfrom .dimensions import SIZE\nclass Part(Solid2Node):\n    def render(self):\n        return cube(SIZE)\n')
    helper = root / 'design/dimensions.py'; helper.write_text('SIZE = 1\n')
    stamp = time.time_ns()
    os.utime(root / 'design/part.py', ns=(stamp + 60_000_000_000, stamp + 60_000_000_000))
    first = cli(root, 'build')
    before = json.loads((root / '_build/viewer.json').read_text())['pieces'][0]['volume']
    helper.write_text('SIZE = 20\n')
    second = cli(root, 'build')
    after = json.loads((root / '_build/viewer.json').read_text())['pieces'][0]['volume']
    RESULTS['mtime_collision'] = dict(first_exit=first.returncode, rebuild_exit=second.returncode, before_volume=before, after_volume=after, expected_volume=8000)

    # Watch event dispatch uses the real watchdog handler but a controlled loop.
    from watchdog.events import FileModifiedEvent, FileMovedEvent
    from solid_node.core.builder import Builder
    loop = asyncio.new_event_loop()
    builder = Builder('design.part:Part', build_dir=str(base / 'watch'))
    builder.loop = loop
    precise_sources = [
        '/project/part.py', '/project/part.scad', '/project/part.stl',
        '/project/part.step', '/project/part.js',
    ]
    builder._watched_sources = {
        os.path.realpath(path) for path in precise_sources
    }
    observed = {}
    for event in [FileModifiedEvent('/project/part.py'), FileModifiedEvent('/project/part.scad'), FileModifiedEvent('/project/part.stl'), FileModifiedEvent('/project/part.step'), FileModifiedEvent('/project/part.js'), FileMovedEvent('/project/part.tmp', '/project/part.py')]:
        builder.file_changed = loop.create_future()
        builder.dispatch(event)
        loop.run_until_complete(asyncio.sleep(0))
        observed[event.event_type + ':' + event.src_path] = builder.file_changed.done()
    loop.close()
    RESULTS['watch_events'] = observed

print(json.dumps(RESULTS, indent=2))
