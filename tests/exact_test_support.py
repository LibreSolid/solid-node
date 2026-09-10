# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Test-only isolation seams for process-local exact geometry caches."""

from solid_node import exact


def clear_exact_shape_caches():
    """Drop coherent exact-cache state between fixtures.

    ``_shape_keys`` maps object ids to entries retained by ``_shape_cache``;
    the bounds and placement caches depend on those same keys.  Clear every
    dependent registry while the fixture still owns any shapes, then release
    the shape cache so a future object-id reuse cannot acquire stale identity.
    """
    exact._shape_keys.clear()
    exact._bounds_cache.clear()
    exact._face_box_cache.clear()
    exact._placement_cache.clear()
    exact._shape_cache.clear()
