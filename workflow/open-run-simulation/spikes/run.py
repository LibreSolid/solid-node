"""Reproduce native tests, shared JSON corpus, Node parity and bounded-memory probe.

Every generated file stays in ../evidence. Browser evidence is browser_probe.py.
"""
import copy
import argparse
import gc
import hashlib
import json
import platform
import subprocess
import sys
import time
import tracemalloc
from pathlib import Path

from kernel import Engine
from programs import HERE, CURTA, WORKSPACE, all_programs, profiles, seal, event

EVIDENCE = HERE.parent / 'evidence'


def write(name, content):
    EVIDENCE.mkdir(exist_ok=True)
    path = EVIDENCE / name
    path.write_text(content if isinstance(content, str) else json.dumps(content, indent=2) + '\n')


def cases(programs):
    result = []
    def add(name, program, dt, commands):
        result.append(dict(name=name, program=program, dt=dt, commands=commands))
    add('couple-open-close-reverse', 'clutch', 1, [
        ['rate', 'shaft', 10], ['advance', 1], ['rate', 'shaft', 0],
        ['rate', 'sleeve', -1], ['advance', 1], ['rate', 'sleeve', 0],
        ['rate', 'shaft', 10], ['advance', 1], ['rate', 'shaft', 0], ['mark'],
        ['rate', 'sleeve', 1], ['advance', 1], ['rate', 'sleeve', 0],
        ['rate', 'wheel', -10], ['advance', 1], ['rate', 'wheel', 0], ['advance', 10]])
    add('refuse-misaligned-engagement', 'clutch', 1, [
        ['rate', 'sleeve', -1], ['advance', 1], ['rate', 'sleeve', 0],
        ['rate', 'shaft', 1], ['advance', 1], ['rate', 'shaft', 0],
        ['rate', 'sleeve', 1], ['expect-error', 'advance', 1]])
    add('ratchet-reverse-lift-reseat', 'ratchet', 1, [
        ['rate', 'disc', 25], ['advance', 1], ['rate', 'disc', -15], ['advance', 1], ['mark'],
        ['rate', 'disc', 0], ['rate', 'lift', 1], ['advance', 1], ['rate', 'lift', 0],
        ['rate', 'disc', -15], ['advance', 1], ['rate', 'disc', 0],
        ['rate', 'lift', -1], ['advance', 1], ['rate', 'lift', 0],
        ['rate', 'disc', -10], ['advance', 1]])
    for n in (1, 7, 240, 997):
        add(f'curta-dt-{n}', 'curta', 1 / n, [['rate', 'crank', 1080], ['advance', n]])
    # Exact entry/exit, adjacent floating point values, reset spanning wrap.
    for angle in (113.5 - 1e-6, 113.5, 113.5 + 1e-6, 124.75, 157.625, 177.625, 360, 380):
        add(f'curta-boundary-{angle}', 'curta', 1, [['rate', 'crank', angle], ['advance', 1]])
    add('curta-checkpoint-replay', 'curta', 1 / 240, [
        ['rate', 'crank', 360], ['advance', 81], ['save', 'mid-contact'],
        ['advance', 399], ['mark'], ['restore', 'mid-contact'], ['advance', 399]])
    add('concurrent-pause-replay', 'concurrent', .01, [
        ['rate', 'motor', 720], ['rate', 'steering', 10],
        ['move', 'print', {'x_motor': 1800, 'y_motor': 900}, 100], ['advance', 40],
        ['pause', 'print'], ['save', 'paused'], ['advance', 50], ['mark'],
        ['pause', 'print', False], ['advance', 60], ['mark'], ['restore', 'paused'],
        ['advance', 50], ['pause', 'print', False], ['advance', 60]])
    add('incompatible-drives', 'clutch', 1, [
        ['rate', 'shaft', 10], ['rate', 'wheel', 10], ['expect-error', 'advance', 1]])
    p = copy.deepcopy(programs['concurrent'])
    p['m'] = dict(a=False, b=False)
    p['events'] = [event('a', 'motor', 10, {'a': True}),
        event('b', 'motor', 10, {'b': True}, when=['m', 'a'])]
    programs['settle'] = seal(p)
    add('same-instant', 'settle', 1, [['rate', 'motor', 20], ['advance', 1]])
    p = copy.deepcopy(p)
    p['events'][1] = event('b', 'motor', 10, {'a': False})
    programs['conflict'] = seal(p)
    add('event-write-conflict', 'conflict', 1, [['rate', 'motor', 20], ['expect-error', 'advance', 1]])
    return result


def execute(programs, test):
    e, marks, saved = Engine(programs[test['program']], test['dt']), [], {}
    for op, *args in test['commands']:
        if op == 'save':
            saved[args[0]] = e.snapshot()
        elif op == 'restore':
            e.restore(saved[args[0]])
        elif op == 'expect-error':
            try:
                getattr(e, args[0])(*args[1:])
            except ValueError as err:
                marks.append(dict(error=str(err)))
            else:
                raise AssertionError('expected refusal did not occur')
        elif op == 'mark':
            marks.append(e.snapshot())
        else:
            getattr(e, op)(*args)
    marks.append(e.snapshot())
    return marks


def compare(a, b, path='root'):
    if isinstance(a, dict):
        assert a.keys() == b.keys(), path
        return max((compare(v, b[k], f'{path}.{k}') for k, v in a.items()), default=0)
    if isinstance(a, list):
        assert len(a) == len(b), path
        return max((compare(x, y, f'{path}[{i}]') for i, (x, y) in enumerate(zip(a, b))), default=0)
    if isinstance(a, bool):
        assert isinstance(b, bool) and a == b, (path, a, b)
        return 0
    if isinstance(a, (str, int)):
        assert a == b, (path, a, b)
        return 0
    if isinstance(a, float):
        error = abs(a-b)
        assert error <= 1e-7, (path, a, b)
        return error
    assert a == b, (path, a, b)
    return 0


def source_evidence():
    paths = ['simulation/carry_profiles.py', 'simulation/carry_motion.py',
        'simulation/cycle.py', 'simulation/selectors.py', 'simulation/pawl.py',
        'simulation/tools/compile_carry_motion.py',
        '_build_evidence/carry-half-trigger-assembled.jsonl',
        '_build_evidence/carry-full-trigger-final-tip.jsonl',
        '_build_evidence/carry-reset-profile.jsonl']
    record = dict(project=str(CURTA.relative_to(WORKSPACE)),
        commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=CURTA, text=True).strip(),
        license='Source Curta project identifies Marcus Wu, CC BY-NC-SA 4.0. No CAD assets copied.',
        files={p: hashlib.sha256((CURTA / p).read_bytes()).hexdigest() for p in paths})
    def rows(name):
        return [json.loads(l) for l in (CURTA / '_build_evidence' / name).read_text().splitlines() if l.startswith('{')]
    def lerp(points, x):
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            if x0 <= x <= x1:
                return y0 + (y1-y0) * (x-x0) / (x1-x0)
        raise ValueError(x)
    data = profiles()
    margins, compress = [], []
    half, full = rows('carry-half-trigger-assembled.jsonl'), rows('carry-full-trigger-final-tip.jsonl')
    assert [r['digit'] for r in half] == [r['digit'] for r in full]
    for h, f in zip(half, full):
        original = max(h['minimum_drop_mm'], f['minimum_drop_mm'])
        predicted = lerp(data['PIN_DROP'], h['digit'])
        margins.append(predicted-original)
        compress.append(abs(predicted-(original+.05)))
    resets = []
    for r in rows('carry-reset-profile.jsonl'):
        if r['bank'] == 'result' and (r['angle'] >= 330 or r['angle'] <= 3):
            x = r['angle'] + (360 if r['angle'] < 30 else 0)
            resets.append(abs(lerp(data['RESET_LIFT'], x) - (r['required_lift_mm'] + .05)))
    assert max(compress) <= .001001
    assert max(resets) <= .001001
    assert min(margins) > 0
    record['profile_revalidation'] = dict(pin_samples=len(half),
        min_sample_clearance_margin_mm=min(margins), max_pin_compaction_error_mm=max(compress),
        reset_samples=len(resets), max_reset_compaction_error_mm=max(resets),
        limit='Revalidated existing sampled gauge data, NOT a new CAD sweep or exact continuous-contact proof.')
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-memory', action='store_true', help='rerun fast conformance without replacing long-run memory evidence')
    args = parser.parse_args()
    tests = subprocess.run([sys.executable, '-m', 'unittest', 'test_mechanics', '-v'], cwd=HERE, capture_output=True, text=True)
    write('native-tests.txt', tests.stdout + tests.stderr)
    assert tests.returncode == 0, tests.stderr
    programs = all_programs()
    corpus = dict(programs=programs, cases=cases(programs))
    write('corpus.json', corpus)
    expected = {c['name']: execute(programs, c) for c in corpus['cases']}
    write('python-results.json', expected)
    print(f'Native tests passed; {len(corpus["cases"])} conformance cases', flush=True)
    node = subprocess.run(['node', '--expose-gc', str(HERE / 'node_probe.mjs'), str(EVIDENCE / 'corpus.json')], capture_output=True, text=True, check=True)
    observed = json.loads(node.stdout)
    max_error = compare(expected, observed.pop('results'))
    observed['conformance_cases'] = len(corpus['cases'])
    observed['max_python_node_coordinate_error'] = max_error
    write('node-results.json', observed)
    write('provenance.json', source_evidence())
    scale = subprocess.run(['node', str(HERE / 'scale_probe.mjs')], capture_output=True, text=True, check=True)
    write('scale-results.json', json.loads(scale.stdout))
    if args.skip_memory:
        return
    print('Node parity passed; measuring Python retained allocations', flush=True)
    tracemalloc.start()
    e = Engine(programs['curta'])
    e.rate('crank', 360)
    started, previous, memory = time.perf_counter(), 0, []
    for n in (2000, 20000, 100000):
        e.advance(n-previous)
        previous = n
        gc.collect()
        current, peak = tracemalloc.get_traced_memory()
        memory.append(dict(ticks=n, retained_traced_bytes=current, peak_traced_bytes=peak,
            snapshot_bytes=len(json.dumps(e.snapshot())), trace_length=len(e.trace),
            event_count_slots=len(e.counts)))
        print(f'Python: {n} ticks, {current} retained traced bytes', flush=True)
    write('python-memory.json', dict(runtime=platform.python_version(),
        tracemalloc_enabled=True, seconds_for_100000_ticks=time.perf_counter()-started, samples=memory))
    print('Evidence written to', EVIDENCE, flush=True)


if __name__ == '__main__':
    main()
