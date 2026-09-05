"""Spike: a mid-phase between the AABB broad phase and the boolean.

Question: after fixes 1-3 (docs/performance-improvement.md), what does a
pair that SURVIVES the AABB broad phase but is still empty actually cost,
and can a cheaper exact-negative filter reject it before the boolean?

The filter under test: two parts can only share volume inside the
intersection of their world AABBs (the "overlap box"). Pull that box back
into each part's LOCAL frame (rigid inverse, 8 corners), and keep only the
triangles whose local AABB meets it. If either survivor set is empty the
parts cannot share a boundary there; a single containment probe then rules
out the one remaining case (one part wholly inside the other).

Everything here is measurement only. No framework file is modified.
"""
import glob
import os
import sys
import time

import numpy as np
import trimesh
from manifold3d import Manifold, Mesh

BUILD = ('/home/asa/devel/libresolid-studio/solid-node/'
         'docs/examples/v8-engine/_build')


def load_parts(limit):
    """(name, trimesh, Manifold, local tri AABBs) for the biggest parts."""
    files = sorted(glob.glob(os.path.join(BUILD, '**', '*.stl'), recursive=True),
                   key=os.path.getsize, reverse=True)[:limit]
    parts = []
    for path in files:
        mesh = trimesh.load(path, file_type='stl', process=False)
        mesh.merge_vertices()
        manifold = Manifold(Mesh(
            vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
            tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))
        tris = mesh.vertices[mesh.faces]              # (F, 3, 3)
        lo = tris.min(axis=1)
        hi = tris.max(axis=1)
        parts.append((os.path.basename(path).split('-')[0], mesh, manifold,
                      lo, hi))
    return parts


def world_bounds(mesh, matrix):
    lo, hi = mesh.bounds
    corners = np.array([[x, y, z, 1.0]
                        for x in (lo[0], hi[0])
                        for y in (lo[1], hi[1])
                        for z in (lo[2], hi[2])])
    world = (matrix @ corners.T).T[:, :3]
    return world.min(axis=0), world.max(axis=0)


def overlap_box(box1, box2):
    lo = np.maximum(box1[0], box2[0])
    hi = np.minimum(box1[1], box2[1])
    return None if np.any(hi < lo) else (lo, hi)


def to_local_box(box, matrix):
    """Conservative local-frame AABB of a world box under a rigid matrix."""
    inverse = np.linalg.inv(matrix)
    lo, hi = box
    corners = np.array([[x, y, z, 1.0]
                        for x in (lo[0], hi[0])
                        for y in (lo[1], hi[1])
                        for z in (lo[2], hi[2])])
    local = (inverse @ corners.T).T[:, :3]
    return local.min(axis=0), local.max(axis=0)


def survivors(lo, hi, box):
    """Count triangles whose local AABB meets `box` (vectorized)."""
    blo, bhi = box
    keep = ~(np.any(hi < blo, axis=1) | np.any(lo > bhi, axis=1))
    return int(keep.sum())


def timed(function, repeats=3):
    best = float('inf')
    result = None
    for _ in range(repeats):
        start = time.perf_counter()
        result = function()
        best = min(best, time.perf_counter() - start)
    return best, result


def main():
    parts = load_parts(int(sys.argv[1]) if len(sys.argv) > 1 else 6)
    print(f"{'part':22} {'faces':>8}")
    for name, mesh, _, _, _ in parts:
        print(f"{name:22} {len(mesh.faces):>8}")
    print()

    # Place each pair so their AABBs overlap by a thin margin but the solids
    # stay apart: the exact case the broad phase cannot cull and the suite
    # spends its time on (a passing assembly is mostly near-misses).
    print(f"{'pair':40} {'boolean ms':>11} {'midphase ms':>12} "
          f"{'kept A':>8} {'kept B':>8} {'verdict':>9}")
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            name1, mesh1, man1, lo1, hi1 = parts[i]
            name2, mesh2, man2, lo2, hi2 = parts[j]
            # shift part 2 along +X so the boxes overlap by 15% of part 2's span
            span = mesh2.bounds[1][0] - mesh2.bounds[0][0]
            shift = (mesh1.bounds[1][0] - mesh2.bounds[0][0]) - 0.15 * span
            matrix1 = np.eye(4)
            matrix2 = np.eye(4)
            matrix2[0, 3] = shift
            box1 = world_bounds(mesh1, matrix1)
            box2 = world_bounds(mesh2, matrix2)
            shared = overlap_box(box1, box2)
            if shared is None:
                continue

            def boolean():
                result = man1.transform(matrix1[:3, :4]) ^ \
                    man2.transform(matrix2[:3, :4])
                empty = result.is_empty()
                return empty, 0.0 if empty else result.volume()

            def midphase():
                local1 = to_local_box(shared, matrix1)
                local2 = to_local_box(shared, matrix2)
                return (survivors(lo1, hi1, local1),
                        survivors(lo2, hi2, local2))

            bool_ms, (empty, volume) = timed(boolean)
            mid_ms, (kept1, kept2) = timed(midphase)
            verdict = 'empty' if empty else f'{volume:.1f}mm3'
            print(f"{name1[:19]+'/'+name2[:19]:40} {bool_ms*1e3:11.2f} "
                  f"{mid_ms*1e3:12.3f} {kept1:8} {kept2:8} {verdict:>9}")


if __name__ == '__main__':
    main()
