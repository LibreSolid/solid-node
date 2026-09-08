#!/usr/bin/env python3
"""Reproduce the September 2026 performance audit without editing core code.

Run from the framework bench with the shop venv and PYTHONPATH=$PWD.
Results are measurements, not timing assertions or a performance guarantee.
All geometry and project execution happen in disposable copied projects.
"""

import argparse
import cProfile
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import pstats
import resource
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import traceback

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MARKER = 'PERFORMANCE_RESULT='


def summary(values):
    return {'samples_s': values, 'median_s': statistics.median(values),
            'min_s': min(values), 'max_s': max(values)}


def measure(fn, repeats=3):
    times = []
    result = None
    for _ in range(repeats):
        start = time.perf_counter()
        result = fn()
        times.append(time.perf_counter() - start)
    return dict(summary(times), result=result)


def rss_kib():
    for line in Path('/proc/self/status').read_text().splitlines():
        if line.startswith('VmRSS:'):
            return int(line.split()[1])


def environment():
    packages = {}
    for name in ('solid-node', 'cadquery', 'cadquery-ocp', 'build123d',
                 'trimesh', 'manifold3d', 'molejo', 'numpy', 'scipy'):
        packages[name] = importlib.metadata.version(name)
    return {'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'framework_commit': subprocess.check_output(
                ['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
            'python': sys.version, 'executable': sys.executable,
            'platform': platform.platform(), 'packages': packages,
            'affinity_cpus': sorted(os.sched_getaffinity(0)),
            'load_average': os.getloadavg(),
            'cpu': next(line.split(':', 1)[1].strip()
                        for line in Path('/proc/cpuinfo').read_text().splitlines()
                        if line.startswith('model name')),
            'thread_environment': {k: os.environ.get(k) for k in
                ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')},
            'openscad': subprocess.run(['openscad', '--version'],
                capture_output=True, text=True).stderr.strip(),
            'jscad_available': shutil.which('jscad') is not None}


def invoke(mode, cwd, *, snippet='', argv=(), profile=False, timeout=300):
    env = dict(os.environ, PYTHONPATH=str(REPO), PYTHONDONTWRITEBYTECODE='1')
    env.pop('SOLID_BUILD_DIR', None)
    env.pop('SOLID_TEST_KERNEL', None)
    env.pop('SOLID_TEST_VOLUME_EPSILON', None)
    command = [sys.executable, str(HERE / 'probe.py'), '--worker', mode,
               '--snippet', snippet]
    if profile:
        command.append('--profile')
    command += ['--', *argv]
    start = time.perf_counter()
    proc = subprocess.Popen(command, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            stdout, stderr = proc.communicate()
        return {'timeout_s': timeout, 'wall_s': time.perf_counter() - start,
                'status': proc.returncode, 'stderr': stderr[-8000:]}
    wall = time.perf_counter() - start
    lines = [line for line in stdout.splitlines() if line.startswith(MARKER)]
    data = json.loads(lines[-1][len(MARKER):]) if lines else {}
    data.update(wall_s=wall, status=proc.returncode, stderr=stderr[-16000:],
                stdout='\n'.join(line for line in stdout.splitlines()
                                 if not line.startswith(MARKER))[-16000:])
    return data


def profile_text(profiler):
    stream = io.StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs().sort_stats('cumulative').print_stats(45)
    stats.sort_stats('tottime').print_stats(25)
    return stream.getvalue()


def worker(args):
    data = {}
    profiler = cProfile.Profile() if args.profile else None
    start = time.perf_counter()
    status = 0
    try:
        if profiler:
            profiler.enable()
        if args.worker == 'snippet':
            exec(args.snippet, {'data': data, '__name__': '__probe__'})
        elif args.worker == 'cli':
            import solid_node.manager.build as build_module
            real_process = build_module.Process
            children = []

            def counted(*a, **kw):
                proc = real_process(*a, **kw)
                children.append(proc)
                return proc

            build_module.Process = counted
            from solid_node.cli import manage
            sys.argv = ['solid', *args.argv]
            try:
                manage()
            finally:
                data['builder_processes'] = len(children)
                data['builder_exitcodes'] = [p.exitcode for p in children]
        elif args.worker == 'builder':
            import asyncio
            from solid_node.core.builder import Builder
            from solid_node.core.loader import select_model
            selection = select_model(None)
            selection.anchor()
            result = asyncio.run(Builder(selection.reference, watch=False)._start())
            data['build_outcome'] = result.name
        elif args.worker == 'algorithms':
            data.update(algorithm_probes())
        elif args.worker == 'memory':
            data.update(memory_probe())
        elif args.worker == 'detail':
            data.update(project_detail())
        elif args.worker == 'batch':
            import asyncio
            from solid_node.core.builder import Builder, BuildOutcome
            from solid_node.core.loader import select_model
            selection = select_model(args.argv[0])
            selection.anchor()
            data['build_passes'] = 0
            while True:
                result = asyncio.run(Builder(selection.reference, watch=False,
                    overrides=[f'count={args.argv[1]}'])._start())
                data['build_passes'] += 1
                if result is BuildOutcome.RENDERED:
                    continue
                if result is not BuildOutcome.CURRENT:
                    raise RuntimeError(f'Counterfactual cannot handle {result}')
                break
        else:
            raise ValueError(args.worker)
    except SystemExit as exc:
        status = exc.code or 0
    except BaseException:
        status = 1
        data['error'] = traceback.format_exc()
    finally:
        if profiler:
            profiler.disable()
            data['profile'] = profile_text(profiler)
        data['elapsed_s'] = time.perf_counter() - start
        data['peak_self_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        data['peak_child_rss_kib'] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        data['module_count'] = len(sys.modules)
        data['heavy_imports'] = [p for p in ('trimesh', 'cadquery', 'OCP', 'build123d',
                               'molejo', 'solid_node.test') if p in sys.modules]
        print(MARKER + json.dumps(data), flush=True)
    return status


def startup_probes(scratch):
    snippets = {
        'python_control': 'pass',
        'cli_import': 'import solid_node.cli',
        'parameters_import': 'import solid_node.parameters',
        'Solid2Node_import': 'from solid_node.node import Solid2Node',
        'CadQueryNode_import': 'from solid_node.node import CadQueryNode',
        'test_import': 'import solid_node.test',
        'viewer_command': "import sys; sys.argv=['solid','viewer']; from solid_node.cli import manage; manage()",
        'models_command': "import sys; sys.argv=['solid','models','--json']; from solid_node.cli import manage; manage()",
        'build_help': "import sys; sys.argv=['solid','build','-h']; from solid_node.cli import manage; manage()",
    }
    runs = {}
    for name, snippet in snippets.items():
        print('startup:', name, flush=True)
        samples = [invoke('snippet', scratch, snippet=snippet) for _ in range(5)]
        runs[name] = dict(summary([x['wall_s'] for x in samples]), runs=samples)
    return runs


def artifact_record(project):
    build = Path(project) / '_build'
    doc = build / 'viewer.json'
    if not doc.exists():
        return None
    data = json.loads(doc.read_text())
    stls = list(build.rglob('*.stl'))
    return {'manifest_sha256': hashlib.sha256(doc.read_bytes()).hexdigest(),
            'manifest_mtime_ns': doc.stat().st_mtime_ns,
            'stl_files': len(stls), 'stl_bytes': sum(p.stat().st_size for p in stls),
            'pieces': len(data.get('pieces', [])),
            'piece_instances': sum(p['count'] for p in data.get('pieces', []))}


def build_probes(scratch):
    results = []
    for backend, counts in (('solid', (1, 8, 24)), ('exact', (1, 8))):
        for count in counts:
            for repeat in range(3):
                project = Path(scratch) / f'{backend}-{count}-{repeat}'
                shutil.copytree(HERE / 'fixtures', project)
                argv = ['build', f'bench.{backend}:Machine', '--set', f'count={count}']
                print('build:', backend, count, repeat, flush=True)
                cold = invoke('cli', project, argv=argv)
                before = artifact_record(project)
                warm = invoke('cli', project, argv=argv)
                results.append({'backend': backend, 'count': count, 'repeat': repeat,
                                'cold': cold, 'warm': warm,
                                'manifest_unchanged': before == artifact_record(project),
                                'artifacts': before})
    return results


def batch_probes(scratch):
    results = []
    for repeat in range(3):
        project = Path(scratch) / f'batch-{repeat}'
        shutil.copytree(HERE / 'fixtures', project)
        batch = invoke('batch', project, argv=['bench.solid:Machine', '24'])
        batch_stls = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (project / '_build').rglob('*.stl')}
        # A separate empty output tree drives the normal CLI from cold, so
        # comparing outputs does not merely compare two cache hits.
        normal = Path(scratch) / f'normal-{repeat}'
        shutil.copytree(HERE / 'fixtures', normal)
        baseline = invoke('cli', normal,
                          argv=['build', 'bench.solid:Machine', '--set', 'count=24'])
        normal_stls = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in (normal / '_build').rglob('*.stl')}
        results.append({'batch': batch, 'baseline': baseline,
                        'stl_hashes_identical': batch_stls == normal_stls,
                        'stl_files': len(batch_stls)})
        print('batch comparison:', repeat, batch['wall_s'], baseline['wall_s'], flush=True)
    return results


def project_probes(scratch, catalogue, detail=False):
    selected = ('Vibecoded-demos/abacus', 'Vibecoded-demos/v8-engine',
                '3D-Printers/Metamaquina2')
    results = []
    for relative in selected:
        source = catalogue / relative
        git = lambda *a: subprocess.check_output(['git', *a], cwd=source, text=True)
        if Path(git('rev-parse', '--show-toplevel').strip()) != source:
            raise ValueError(f'Not its own repository: {source}')
        record = {'project': relative, 'commit': git('rev-parse', 'HEAD').strip(),
                  'status_before': git('status', '--short')}
        target = Path(scratch) / source.name
        # COPY, never hardlink: currency checks deliberately restamp artifacts.
        shutil.copytree(source, target, symlinks=True,
                        ignore=shutil.ignore_patterns('.git', '__pycache__', '.env',
                            '.pytest_cache', '.venv', 'node_modules', '*.pyc'))
        # Do not let a project symlink make benchmark writes escape its copy.
        for path in target.rglob('*'):
            if path.is_symlink() and not path.resolve().is_relative_to(target):
                raise ValueError(f'External symlink in snapshot: {path}')
        source_files = {}
        for path in target.rglob('*'):
            if path.is_file() and '_build' not in path.parts and path.suffix in (
                    '.py', '.toml', '.scad', '.js', '.step', '.stp', '.stl'):
                source_files[str(path.relative_to(target))] = hashlib.sha256(path.read_bytes()).hexdigest()
        record['source_sha256'] = source_files
        print('project:', relative, 'settle copied artifacts', flush=True)
        record['copied_artifacts_before'] = artifact_record(target)
        record['settle'] = invoke('cli', target, argv=['build'], timeout=420)
        if record['settle']['status'] == 0:
            record['artifacts'] = artifact_record(target)
            if detail:
                before = artifact_files(target)
                record['detail'] = invoke('detail', target, timeout=420)
                after = artifact_files(target)
                record['file_churn'] = artifact_churn(before, after)
            else:
                record['warm'] = [invoke('cli', target, argv=['build']) for _ in range(3)]
                record['manifest_unchanged'] = record['artifacts'] == artifact_record(target)
                print('project:', relative, 'profile current builder', flush=True)
                record['builder_profile'] = invoke('builder', target, profile=True)
        record['status_after'] = git('status', '--short')
        results.append(record)
    return results


def artifact_files(project):
    return {str(p.relative_to(project)): (p.stat().st_ino, p.stat().st_ctime_ns,
            hashlib.sha256(p.read_bytes()).hexdigest())
            for p in (Path(project) / '_build').rglob('*') if p.is_file()}


def artifact_churn(before, after):
    result = {}
    for name in before.keys() & after.keys():
        if before[name][:2] != after[name][:2]:
            extension = Path(name).suffix
            counts = result.setdefault(extension, {'replaced_or_restamped': 0,
                                                   'identical_bytes': 0})
            counts['replaced_or_restamped'] += 1
            counts['identical_bytes'] += before[name][2] == after[name][2]
    return result


def project_detail():
    import numpy as np
    from unittest.mock import patch
    from solid_node.core.builder import Builder
    from solid_node.core.loader import load_node, select_model
    from solid_node.core import pieces
    from solid_node.node import base
    from solid_node.node.base import _topmost_rigid_nodes, _compose_world_matrix
    import solid_node.test as checks

    result = {}
    selection = select_model(None)
    selection.anchor()
    start = time.perf_counter()
    node = load_node(selection.reference)
    result['load_node_s'] = time.perf_counter() - start
    before = artifact_files(Path.cwd())
    start = time.perf_counter()
    with patch.object(base, '_atomic_write_text', wraps=base._atomic_write_text) as writes:
        node.assemble()
    result['assemble_scad_writes'] = writes.call_count
    result['assemble_s'] = time.perf_counter() - start
    result['assemble_file_churn'] = artifact_churn(before, artifact_files(Path.cwd()))
    builder = Builder(selection.reference, watch=False)
    builder.node = node
    result['freshness_checks'] = measure(builder._artifacts_are_current)
    nodes = []

    def walk(n):
        nodes.append(n)
        for child in n.children:
            walk(child)

    walk(node)
    solids = list(_topmost_rigid_nodes(node))
    result.update(nodes=len(nodes), selected_solids=len(solids),
                  distinct_selected_artifacts=len({s.stl_file for s in solids}),
                  source_closure_entries=sum(len(n.files) for n in nodes),
                  distinct_sources=len(set().union(*(n.files for n in nodes))))
    # Measure the unmodified publication method with direct phase timers.
    result['snapshot_cold_process_cache'] = measure(builder._write_viewer_snapshot, 1)
    result['snapshot_warm_process_cache'] = measure(builder._write_viewer_snapshot)
    result['loaded_meshes'] = len(base._base_mesh_cache)
    result['loaded_triangles'] = sum(len(m.faces) for m in base._base_mesh_cache.values())
    # Isolated counterfactual: published geometry facts reused for the SAME
    # artifact. Does not weaken currency checks; performed only after those
    # checks passed and verifies that the output manifest stays byte-identical.
    document_path = Path('_build/viewer.json')
    original_document = document_path.read_bytes()
    document = json.loads(original_document)
    facts = {}
    for entry in document['pieces']:
        for model in entry['models']:
            path = str((Path('_build') / model).resolve())
            facts[(path, os.stat(path).st_mtime_ns)] = (
                entry['size'], entry['volume'], entry['watertight'])
    real_facts = pieces._geometry_facts

    def reuse(path):
        key = (os.path.realpath(path), os.stat(path).st_mtime_ns)
        return facts[key] if key in facts else real_facts(path)

    base._base_mesh_cache.clear()
    pieces._fingerprint_cache.clear()
    with patch.object(pieces, '_geometry_facts', reuse):
        result['snapshot_reuse_published_facts'] = measure(builder._write_viewer_snapshot, 1)
    result['reuse_manifest_identical'] = document_path.read_bytes() == original_document
    # A stable source-mtime census is scoped to this assembled snapshot, not
    # proposed as a long-lived replacement for source-change detection.
    all_sources = set().union(*(n.files for n in nodes))
    saved_stamps = {p: os.stat(p).st_mtime_ns for p in all_sources}
    result['mtime_all_nodes'] = measure(lambda: sum(n.mtime_ns for n in nodes))
    result['mtime_snapshot_census'] = measure(
        lambda: sum(max(saved_stamps[p] for p in n.files) for n in nodes))
    node.set_keyframe(0)
    bounds = [checks._world_bounds(checks._cached_local_bounds(s.stl_file),
                                  _compose_world_matrix(s)) for s in solids]
    candidate_sets = []
    result['real_sweep_axes'] = []
    for axis in (0, 1, 2):
        axes = [axis] + [i for i in range(3) if i != axis]
        reordered = [(lo[axes], hi[axes]) for lo, hi in bounds]
        candidates = set(checks._bounds_candidates(reordered))
        candidate_sets.append(candidates)
        result['real_sweep_axes'].append(dict(axis=axis,
            **measure(lambda: len(list(checks._bounds_candidates(reordered))))))
    result['sweep_candidate_sets_identical'] = candidate_sets[0] == candidate_sets[1] == candidate_sets[2]
    if any(type(n).__name__ == 'ValveSpring' for n in nodes):
        result['flexible'] = flexible_detail(node, nodes)
    return result


def flexible_detail(root, nodes):
    from unittest.mock import patch
    from solid_node.node.base import binding_hash
    import solid_node.test as checks
    springs = [n for n in nodes if type(n).__name__ == 'ValveSpring']
    valve = next(n for n in nodes if type(n).__name__ == 'Valve')
    spring = springs[0]
    result = {'spring_count': len(springs), 'pair': [spring.name, valve.name],
              'instants': []}
    for t in (0, 0.1, 0.2, 0.3):
        root.set_keyframe(t)
        checks.set_comparison_policy(checks.resolve_comparison_policy('exact'))
        exact = measure(lambda: tuple(checks._intersection_stats(spring, valve)))
        checks.set_comparison_policy(checks.resolve_comparison_policy('faceted'))
        faceted = measure(lambda: tuple(checks._intersection_stats(spring, valve)))
        result['instants'].append({'t': t, 'exact': exact, 'faceted': faceted})
    checks.set_comparison_policy(checks.resolve_comparison_policy('faceted'))
    root.set_keyframe(0.1)
    keys = [(s.uniq_id, binding_hash(s.bound_values())) for s in springs]
    result['distinct_bindings_at_t_01'] = len(set(keys))
    checks._flexible_manifold_cache.clear()

    def sequence(evaluate):
        return [float(evaluate(s)[0].volume()) for _ in range(5) for s in springs]

    with patch.object(checks, '_admitted', wraps=checks._admitted) as counted:
        result['interleaved_actual_cache'] = measure(lambda: sequence(checks._flexible_manifold), 1)
        result['interleaved_actual_builds'] = counted.call_count
    checks._flexible_manifold_cache.clear()
    local = {}

    def request_local(s):
        key = (s.uniq_id, binding_hash(s.bound_values()))
        if key not in local:
            local[key] = checks._flexible_manifold(s)
        return local[key]

    with patch.object(checks, '_admitted', wraps=checks._admitted) as counted:
        result['interleaved_request_local_cache'] = measure(lambda: sequence(request_local), 1)
        result['interleaved_request_local_builds'] = counted.call_count
    result['interleaved_volumes_identical'] = (
        result['interleaved_actual_cache']['result'] == result['interleaved_request_local_cache']['result'])
    return result


def algorithm_probes():
    sys.path.insert(0, os.getcwd())
    import numpy as np
    import solid_node.test as framework
    from solid_node.node.operations import Translation
    from solid_node.node.base import AbstractBaseNode
    from solid_node.simulation import Sim
    from bench.solid import Driven

    result = {'sweep': [], 'tree': []}
    for count in (128, 256, 512, 1024):
        for axis in (0, 1, 2):
            bounds = []
            for i in range(count):
                low = np.zeros(3)
                low[axis] = 3 * i
                bounds.append((low, low + 1))
            result['sweep'].append({'count': count, 'axis': axis,
                **measure(lambda: len(list(framework._bounds_candidates(bounds))))})
    for count in (128, 512, 2048):
        for explicit in (False, True):
            node = Driven(count=count, distinct=False, explicit=explicit)
            node.set_state(position=0)
            linking = measure(lambda: [node._link_child(c) for c in node.parts] and len(node.parts))
            sim = Sim(node, dt=0.01)
            stepping = measure(lambda: sim.run(0.2))
            result['tree'].append({'count': count, 'explicit_names': explicit,
                                   'link_all': linking, '20_ticks': stepping,
                                   'names': [node.parts[0].name, node.parts[-1].name]})
    # Real artifact-backed intersection, so both memo hits and misses use core code.
    from trimesh.creation import icosphere
    mesh = icosphere(subdivisions=3)
    path = Path('_pair.stl').resolve()
    mesh.export(path)

    class Part:
        exact = False
        flexible = False
        rigid = True
        _parent = None
        as_number = lambda self, x: float(x)

        def __init__(self, name, x):
            self.name = name
            self.stl_file = str(path)
            self.operations = [Translation([x, 0, 0], self)]

    first, second = Part('first', 0), Part('second', 1.5)
    framework._verdict_cache.clear()
    result['intersection_first'] = measure(lambda: tuple(framework._intersection_stats(first, second)), 1)
    result['intersection_1000_memo_hits'] = measure(lambda: [tuple(framework._intersection_stats(first, second)) for _ in range(1000)][-1])
    result['intersection_triangles'] = len(mesh.faces)
    return result


def memory_probe():
    import cadquery as cq
    import numpy as np
    from solid_node import exact
    shape = cq.Workplane('XY').box(10, 10, 10).val()
    path = Path('_memory.brep').resolve()
    shape.exportBrep(str(path))
    loaded = exact.cached_shape(str(path))
    data = {'placements': [], 'baseline_rss_kib': rss_kib()}
    start = time.perf_counter()
    for i in range(4000):
        matrix = np.eye(4)
        matrix[0, 3] = i / 100
        exact.placed_shape(loaded, matrix)
        if i + 1 in (100, 1000, 2000, 4000):
            data['placements'].append({'count': i + 1,
                'cache_entries': len(exact._placement_cache), 'rss_kib': rss_kib(),
                'elapsed_s': time.perf_counter() - start})
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--section', choices=('startup', 'build', 'batch', 'projects', 'empirical', 'algorithms', 'memory'))
    parser.add_argument('--catalogue', type=Path)
    parser.add_argument('--worker')
    parser.add_argument('--snippet', default='')
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('argv', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.argv[:1] == ['--']:
        args.argv = args.argv[1:]
    if args.worker:
        return worker(args)
    if not args.section:
        parser.error('--section is required')
    record = {'environment': environment(), 'section': args.section}
    with tempfile.TemporaryDirectory(prefix='solid-performance-') as scratch:
        if args.section in ('projects', 'empirical'):
            if args.catalogue is None:
                parser.error('--catalogue is required for projects')
            record['measurements'] = project_probes(scratch, args.catalogue.resolve(),
                                                  detail=args.section == 'empirical')
        elif args.section == 'build':
            record['measurements'] = build_probes(scratch)
        elif args.section == 'batch':
            record['measurements'] = batch_probes(scratch)
        else:
            project = Path(scratch) / 'fixture'
            shutil.copytree(HERE / 'fixtures', project)
            if args.section == 'startup':
                record['measurements'] = startup_probes(project)
            else:
                record['measurements'] = invoke(args.section, project)
    output = HERE / f'{args.section}.json'
    output.write_text(json.dumps(record, indent=2) + '\n')
    print(output, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
