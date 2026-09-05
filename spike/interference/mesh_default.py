"""Spike: what a flexible-part comparison would cost through meshes.

Finding 5 located the v8 suite's remaining cost in 6120 uncacheable
comparisons involving flexible ValveSpring leaves, ~440 ms each, of
which ~300 ms is the exact kernel returning EMPTY.

The pilot's question is whether the default should be the mesh path,
with exact comparison an explicit developer opt-in. That turns on two
numbers this probe measures, per instant and per pair:

  * evaluating the spring: molejo -> OCCT solid vs molejo -> mesh
  * the boolean itself: OCCT common vs manifold3d intersection

Both verdicts are printed so any disagreement between the two paths is
visible rather than assumed away.
"""
import os
import sys
import time

BENCH = os.environ['BENCH']
sys.path.insert(0, BENCH)

from solid_node.core.loader import load_node
import solid_node.test as test_module

node = load_node(sys.argv[1])
node.assemble()

seen = {}


def walk(current):
    if id(current) in seen:
        return
    seen[id(current)] = current
    for child in getattr(current, 'children', []) or []:
        walk(child)


walk(node)

springs = [solid for solid in seen.values()
           if type(solid).__name__ == 'ValveSpring']
valves = [solid for solid in seen.values()
          if type(solid).__name__ in ('Valve', 'Retainer')]
if not springs or not valves:
    sys.exit('fixture not found')

spring, valve = springs[0], valves[0]
print(f'spring={spring.name} valve={valve.name}')


def timed(call):
    start = time.perf_counter()
    result = call()
    return result, (time.perf_counter() - start) * 1e3


for instant in (0.0, 0.1, 0.2, 0.3):
    node.set_keyframe(instant)

    _, exact_eval = timed(spring.shape)
    _, mesh_eval = timed(lambda: test_module._flexible_manifold(spring))

    # Second reads, to separate evaluation from the memo both paths keep.
    _, exact_again = timed(spring.shape)
    _, mesh_again = timed(lambda: test_module._flexible_manifold(spring))

    shape1 = spring.shape()
    shape2 = valve.shape()
    matrix1 = test_module._compose_world_matrix(spring)
    matrix2 = test_module._compose_world_matrix(valve)
    exact_stats, exact_boolean = timed(
        lambda: test_module._exact_verdict(shape1, matrix1, shape2, matrix2,
                                           spring.name, valve.name))

    fast1 = test_module._fast_geometry(spring)
    fast2 = test_module._fast_geometry(valve)
    faceted_stats, faceted_boolean = timed(
        lambda: test_module._faceted_verdict(fast1[0], fast1[1], fast1[2],
                                             fast2[0], fast2[1], fast2[2]))

    print(f't={instant}: '
          f'eval exact {exact_eval:7.1f} ms (memo {exact_again:5.1f}) | '
          f'eval mesh {mesh_eval:7.1f} ms (memo {mesh_again:5.1f}) | '
          f'boolean exact {exact_boolean:7.1f} ms -> '
          f'empty={exact_stats.is_empty} vol={exact_stats.volume:.4f} | '
          f'boolean mesh {faceted_boolean:7.1f} ms -> '
          f'empty={faceted_stats.is_empty} vol={faceted_stats.volume:.4f}')
