"""Spike: the memo's real hit rate, keyed on EXACT matrix bytes.

`census.py` measured the repeat rate with the relative matrix rounded at
1e-9, which is an upper bound. The change keys on the exact bytes -- a
tolerance would be the one thing this work refuses to add -- so the rate
that matters is this one. Design open question; the answer belongs to the
pilot if it falls materially short of the rounded 54%.
"""
import collections
import os
import sys
import time

BENCH = os.environ['BENCH']
sys.path.insert(0, BENCH)

import solid_node.test as test_module

COUNTS = collections.Counter()
TIME = collections.defaultdict(float)

_memoized = test_module._memoized


def counting_memoized(key, compute):
    if key is None:
        COUNTS['uncacheable'] += 1
        return compute()
    if key in test_module._verdict_cache:
        COUNTS['hit'] += 1
        return _memoized(key, compute)
    COUNTS['miss'] += 1
    start = time.perf_counter()
    try:
        return _memoized(key, compute)
    finally:
        TIME['computed'] += time.perf_counter() - start


test_module._memoized = counting_memoized

_stats = test_module._intersection_stats


def counting_stats(*arguments, **keywords):
    COUNTS['comparisons'] += 1
    start = time.perf_counter()
    try:
        return _stats(*arguments, **keywords)
    finally:
        TIME['comparisons'] += time.perf_counter() - start


test_module._intersection_stats = counting_stats

_placed = test_module._placed_intersection


def counting_placed(*arguments, **keywords):
    COUNTS['assembly_pairs'] += 1
    start = time.perf_counter()
    try:
        return _placed(*arguments, **keywords)
    finally:
        TIME['assembly_pairs'] += time.perf_counter() - start


test_module._placed_intersection = counting_placed

from solid_node.cli import manage

sys.argv = ['solid', 'test'] + sys.argv[1:]
start = time.perf_counter()
code = 0
try:
    manage()
except SystemExit as stop:
    code = stop.code
total = time.perf_counter() - start

served = COUNTS['hit']
keyed = COUNTS['hit'] + COUNTS['miss']
print(f"\n=== after (suite wall {total:.1f}s, exit {code}) ===")
print(f"comparisons via _intersection_stats : {COUNTS['comparisons']:6} "
      f"({TIME['comparisons']:.1f}s)")
print(f"pairs via _placed_intersection      : {COUNTS['assembly_pairs']:6} "
      f"({TIME['assembly_pairs']:.1f}s)")
print(f"keyed evaluations                   : {keyed:6}")
print(f"  served from cache (EXACT bytes)   : {served:6} "
      f"({100 * served / keyed:.0f}%)" if keyed else "  none")
print(f"  computed                          : {COUNTS['miss']:6} "
      f"({TIME['computed']:.1f}s)")
print(f"uncacheable (no geometry identity)  : {COUNTS['uncacheable']:6}")
