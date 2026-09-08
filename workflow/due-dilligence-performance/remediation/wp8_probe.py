#!/usr/bin/env python3
"""Measure P07 exact-placement retention without retaining test call history.

Run from the framework worktree with ``PYTHONPATH="$PWD"``.  The probe
creates and deletes only a temporary BREP; it does not write a project or the
historical audit area.  Each invocation is one process so bounded and
uncached observations begin from the same empty process-local exact caches.
"""

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time

import cadquery as cq
import numpy as np

import solid_node.exact as exact


def resident_kib():
    with open('/proc/self/status') as status:
        for line in status:
            if line.startswith('VmRSS:'):
                return int(line.split()[1])
    raise RuntimeError('VmRSS was not present in /proc/self/status')


def matrix(offset):
    result = np.eye(4)
    result[0, 3] = float(offset)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('bounded', 'uncached'), required=True)
    parser.add_argument('--counts', type=int, nargs='+',
                        default=(1000, 4000, 8000))
    args = parser.parse_args()
    counts = tuple(sorted(set(args.counts)))
    if not counts or counts[0] < 1:
        parser.error('--counts must contain positive values')

    exact._shape_cache.clear()
    exact._shape_keys.clear()
    exact._bounds_cache.clear()
    exact._reset_placement_cache()
    original_place = exact._place
    constructions = 0

    def counted_place(shape, values):
        nonlocal constructions
        constructions += 1
        return original_place(shape, values)

    exact._place = counted_place
    try:
        with tempfile.TemporaryDirectory(prefix='solid-wp8-probe-') as directory:
            path = os.path.join(directory, 'trajectory.brep')
            exact.write_brep(cq.Workplane('XY').box(2, 2, 2).val(), path,
                             1 * 10 ** 9)
            stable_shape = exact.cached_shape(path)
            shape = (stable_shape if args.mode == 'bounded'
                     else cq.Workplane('XY').box(2, 2, 2).val())
            samples = []
            next_sample = iter(counts)
            target = next(next_sample)
            started = time.perf_counter()
            for offset in range(counts[-1]):
                placed = exact.placed_shape(shape, matrix(offset))
                del placed
                if offset + 1 == target:
                    gc.collect()
                    samples.append({
                        'count': target,
                        'cache_entries': len(exact._placement_cache),
                        'rss_kib': resident_kib(),
                        'placement_constructions': constructions,
                    })
                    target = next(next_sample, None)
            working_set = (matrix(0), matrix(1), matrix(2))
            before_working_set = constructions
            for _ in range(4):
                for transform in working_set:
                    placed = exact.placed_shape(shape, transform)
                    del placed
            gc.collect()
            elapsed = time.perf_counter() - started
    finally:
        exact._place = original_place

    probe = Path(__file__)
    with probe.open('rb') as stream:
        probe_sha256 = hashlib.file_digest(stream, 'sha256').hexdigest()
    print(json.dumps({
        'mode': args.mode,
        'cache_limit': exact._PLACEMENT_CACHE_LIMIT,
        'counts': counts,
        'samples': samples,
        'working_set': {
            'requests': 12,
            'placement_constructions': constructions - before_working_set,
            'hits': 12 - (constructions - before_working_set),
            'cache_entries_after': len(exact._placement_cache),
            'rss_kib_after': resident_kib(),
        },
        'elapsed_s': elapsed,
        'probe_sha256': probe_sha256,
    }, indent=2))


if __name__ == '__main__':
    main()
