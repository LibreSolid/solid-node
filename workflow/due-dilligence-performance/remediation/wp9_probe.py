# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Measure sparse statics construction without running the LP solver."""

import json
import resource
from types import SimpleNamespace
import tracemalloc
from unittest.mock import patch

import numpy as np
from scipy import sparse

import solid_node.test as test_module


def body(index, anchored=False):
    return test_module._Body(
        f'body-{index}', None, None, 1.0, np.zeros(3), 1.0, anchored)


def main():
    free_count = 1000
    rows = 6 * free_count
    bodies = [body(index) for index in range(free_count)]
    bodies.append(body(free_count, anchored=True))
    contacts = [
        test_module._Contact(np.zeros(3), np.array([0.0, 0.0, 1.0]),
                             index, free_count)
        for index in range(free_count)
    ]
    captured = {}

    def solver(objective, **keywords):
        captured.update(objective=objective, **keywords)
        return SimpleNamespace(success=True, message='construction only',
                               x=np.zeros(len(objective)))

    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    tracemalloc.start()
    with patch.object(test_module, 'linprog', side_effect=solver):
        test_module._unbalanced_bodies(
            bodies, contacts, (), np.array([0.0, 0.0, -1.0]))
    _, traced_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    equality = captured['A_eq'].tocsr()
    assert sparse.issparse(equality)
    assert equality.shape == (rows, free_count + 2 * rows)
    assert equality.nnz == free_count + 2 * rows
    matrix_bytes = (equality.data.nbytes + equality.indices.nbytes
                    + equality.indptr.nbytes)
    vector_bytes = (captured['objective'].nbytes
                    + captured['b_eq'].nbytes)
    dense_coefficients = rows * free_count * np.dtype(float).itemsize
    dense_slack = 2 * rows * rows * np.dtype(float).itemsize
    print(json.dumps({
        'free_bodies': free_count,
        'rows': rows,
        'contact_variables': free_count,
        'equality_shape': list(equality.shape),
        'equality_nnz': equality.nnz,
        'csr_storage_bytes': matrix_bytes,
        'one_dimensional_vector_bytes': vector_bytes,
        'tracemalloc_peak_bytes': traced_peak,
        'maxrss_before_kib': rss_before,
        'maxrss_after_kib': rss_after,
        'historical_dense_coefficient_bytes': dense_coefficients,
        'historical_dense_slack_identity_bytes': dense_slack,
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
