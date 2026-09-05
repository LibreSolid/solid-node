"""Spike: cost of the EXACT (OCCT B-rep) intersection path.

`_intersection_stats`'s exact branch runs, per pair per animation step:
  shape() -> BoundingBox() -> placed_shape() x2 -> BRepAlgoAPI_Common
            -> Solids() -> Volume()
None of it is cached across steps. This measures each stage on the real
v8-engine BREP artifacts.
"""
import glob
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.environ.get('BENCH', '.'))
from solid_node.exact import (cached_shape, placed_shape, intersect_shapes,
                              solid_count, solid_volume)

BUILD = ('/home/asa/devel/libresolid-studio/solid-node/'
         'docs/examples/v8-engine/_build')


def timed(function, repeats=1):
    best, result = float('inf'), None
    for _ in range(repeats):
        start = time.perf_counter()
        result = function()
        best = min(best, time.perf_counter() - start)
    return best, result


def main():
    files = sorted(glob.glob(os.path.join(BUILD, '**', '*.brep'),
                             recursive=True),
                   key=os.path.getsize, reverse=True)[:int(sys.argv[1])]
    shapes = []
    print(f"{'part':22} {'MB':>7} {'import ms':>10} {'bbox ms':>9} "
          f"{'placed ms':>10}")
    for path in files:
        name = os.path.basename(path).split('-')[0]
        size = os.path.getsize(path) / 1e6
        import_ms, shape = timed(lambda p=path: cached_shape(p))
        # second call is the cache hit; measure the cold one above
        bbox_ms, _ = timed(lambda s=shape: s.BoundingBox(), 3)
        matrix = np.eye(4)
        matrix[0, 3] = 3.0
        placed_ms, placed = timed(lambda s=shape: placed_shape(s, matrix), 3)
        print(f"{name:22} {size:7.1f} {import_ms*1e3:10.1f} "
              f"{bbox_ms*1e3:9.2f} {placed_ms*1e3:10.1f}")
        shapes.append((name, shape, placed))

    print()
    print(f"{'pair':40} {'common ms':>10} {'solids ms':>10} {'verdict':>12}")
    for i in range(len(shapes)):
        for j in range(i + 1, len(shapes)):
            name1, shape1, placed1 = shapes[i]
            name2, shape2, placed2 = shapes[j]
            common_ms, result = timed(
                lambda: intersect_shapes(placed1, placed2, name1, name2))
            read_ms, count = timed(lambda r=result: solid_count(r))
            volume = solid_volume(result) if count else 0.0
            verdict = 'empty' if count == 0 else f'{volume:.1f}mm3'
            print(f"{name1[:19]+'/'+name2[:19]:40} {common_ms*1e3:10.1f} "
                  f"{read_ms*1e3:10.1f} {verdict:>12}")


if __name__ == '__main__':
    main()
