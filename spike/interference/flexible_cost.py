"""Spike: what a flexible-part comparison actually costs.

The after-run left 6120 uncacheable evaluations carrying the bulk of the
v8 suite. The probe showed what they are: comparisons involving flexible
leaves (valve springs), whose geometry is a function of the driver
binding and therefore genuinely different at every animation instant.

That makes them uncacheable BY CONSTRUCTION. The open question is what
the 245 ms each is spent on -- evaluating the spring's shape, or the
boolean against it.
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
print(f'springs={len(springs)} valves/retainers={len(valves)}')
if not springs or not valves:
    sys.exit('fixture not found')

spring, valve = springs[0], valves[0]

for instant in (0.0, 0.1, 0.2):
    node.set_keyframe(instant)
    start = time.perf_counter()
    shape = spring.shape()
    evaluated = time.perf_counter() - start

    start = time.perf_counter()
    stats = test_module._intersection_stats(spring, valve)
    compared = time.perf_counter() - start

    print(f't={instant}: spring.shape() {evaluated * 1e3:7.1f} ms | '
          f'full comparison {compared * 1e3:7.1f} ms | '
          f'empty={stats.is_empty} exact={stats.exact}')
