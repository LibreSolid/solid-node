"""Spike: which exact solids can be keyed, and which cannot.

The after-run showed 6120 of 30227 evaluations uncacheable -- no geometry
identity -- and the time unaccounted for by the cacheable branch is the
same order as the whole suite. This asks the model directly: for every
exact node, does `shape()` come back with a cache identity?
"""
import os
import sys

BENCH = os.environ['BENCH']
sys.path.insert(0, BENCH)

from solid_node.core.loader import load_node
from solid_node.exact import shape_identity
from solid_node.node.base import AbstractBaseNode

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

keyed, unkeyed = [], []
for solid in seen.values():
    try:
        if not solid.exact:
            continue
    except Exception:
        continue
    try:
        shape = solid.shape()
    except Exception as error:
        unkeyed.append((type(solid).__name__, solid.name,
                        f'{type(error).__name__}: {error}'))
        continue
    identity = shape_identity(shape)
    if identity is None:
        current = None
        brep = getattr(solid, 'brep_file', None)
        if brep is not None:
            current = solid._up_to_date(brep)
        unkeyed.append((type(solid).__name__, solid.name,
                        f'brep current={current}'))
    else:
        keyed.append((type(solid).__name__, solid.name))

print(f'exact solids keyed  : {len(keyed)}')
print(f'exact solids UNKEYED: {len(unkeyed)}')
for kind, name, why in unkeyed[:25]:
    print(f'  {kind:22} {name:32} {why}')
