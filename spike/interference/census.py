"""Spike: census of intersection work in a REAL animated suite run.

Wraps solid_node.test._intersection_stats and solid_node.exact's kernel
entry points, then runs the v8-engine test suite. Reports, per call site:
total calls, wall time, and how many calls repeat a key already seen --
where the key is (part identities, RELATIVE placement), which is what a
memoized verdict would be valid for.
"""
import collections
import os
import sys
import time

import numpy as np

BENCH = os.environ['BENCH']
sys.path.insert(0, BENCH)

import solid_node.test as test_module
import solid_node.exact as exact_module

STATS = collections.Counter()
TIME = collections.defaultdict(float)
KEYS = collections.defaultdict(set)


def _key(node1, node2):
    """(names, relative world placement) rounded -- the memoizable identity."""
    try:
        matrix1 = test_module._compose_world_matrix(node1)
        matrix2 = test_module._compose_world_matrix(node2)
        relative = np.linalg.inv(matrix1) @ matrix2
        return (getattr(node1, 'name', '?'), getattr(node2, 'name', '?'),
                np.round(relative, 9).tobytes())
    except Exception:
        return None


def wrap_stats(original):
    def wrapper(node1, node2, *args, **kwargs):
        key = _key(node1, node2)
        exact = (getattr(node1, 'exact', False) and
                 getattr(node2, 'exact', False))
        label = 'exact' if exact else 'faceted'
        start = time.perf_counter()
        try:
            return original(node1, node2, *args, **kwargs)
        finally:
            elapsed = time.perf_counter() - start
            STATS[f'{label}:calls'] += 1
            TIME[f'{label}:seconds'] += elapsed
            if key is not None:
                if key in KEYS[label]:
                    STATS[f'{label}:repeat'] += 1
                    TIME[f'{label}:repeat_seconds'] += elapsed
                KEYS[label].add(key)
    return wrapper


def wrap_named(module, name, label):
    original = getattr(module, name)

    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            STATS[f'{label}:calls'] += 1
            TIME[f'{label}:seconds'] += time.perf_counter() - start
    setattr(module, name, wrapper)


test_module._intersection_stats = wrap_stats(test_module._intersection_stats)
wrap_named(test_module, '_placed_intersection', 'placed_intersection')
wrap_named(exact_module, 'intersect_shapes', 'occt_common')
wrap_named(exact_module, 'placed_shape', 'occt_placed')
wrap_named(exact_module, 'cached_shape', 'occt_import')
wrap_named(test_module, '_cached_manifold', 'manifold_cache')

from solid_node.cli import manage

sys.argv = ['solid', 'test'] + sys.argv[1:]
start = time.perf_counter()
code = 0
try:
    manage()
except SystemExit as exit_code:
    code = exit_code.code
total = time.perf_counter() - start

print(f"\n=== census (suite wall {total:.1f}s, exit {code}) ===")
for label in ('faceted', 'exact'):
    calls = STATS[f'{label}:calls']
    if not calls:
        continue
    print(f"{label:10} calls={calls:6}  {TIME[f'{label}:seconds']:8.2f}s   "
          f"repeats={STATS[f'{label}:repeat']:6} "
          f"({TIME[f'{label}:repeat_seconds']:.2f}s recoverable by memo, "
          f"{100*STATS[f'{label}:repeat']/calls:.0f}% of calls)")
for label in ('placed_intersection', 'occt_common', 'occt_placed',
              'occt_import', 'manifold_cache'):
    if STATS[f'{label}:calls']:
        print(f"{label:20} calls={STATS[f'{label}:calls']:6}  "
              f"{TIME[f'{label}:seconds']:8.2f}s")
