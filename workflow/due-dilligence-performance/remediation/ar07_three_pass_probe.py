#!/usr/bin/env python3
"""Finite AR-07 proof on disposable copies of the three audited projects."""

import json
import tempfile
from pathlib import Path

import run_current_performance_probe as probe


def main():
    catalogue = probe.EXPECTED_CATALOGUE
    before = probe.require_baseline_catalogue(catalogue)
    projects = []
    with tempfile.TemporaryDirectory(
            prefix='ar07-disposable-three-pass-') as directory:
        for name in probe.PROJECTS:
            project, copy_record = probe.copy_project(
                catalogue, name, Path(directory) / name.replace('/', '-'))
            workers = []
            states = []
            for pass_name in ('first', 'second', 'third'):
                worker = probe.invoke(
                    probe._worker_command('cli', '--', 'build'),
                    project, timeout=600)
                probe.validate_worker_tree(worker)
                workers.append({
                    'pass': pass_name,
                    'status': worker['status'],
                    'wall_s': worker['outer_wall_s'],
                })
                states.append(probe.artifact_state(project))
            projects.append({
                'project': name,
                'copy_input_maps_equal': copy_record['input_maps_equal'],
                'workers': workers,
                'first_to_second': probe.artifact_churn(
                    states[0], states[1]),
                'second_to_third': probe.artifact_churn(
                    states[1], states[2]),
                'stl_maps_equal': (
                    states[0]['stl_filename_sha256']
                    == states[1]['stl_filename_sha256']
                    == states[2]['stl_filename_sha256']
                ),
                'manifests_equal': (
                    states[0]['manifest']
                    == states[1]['manifest']
                    == states[2]['manifest']
                ),
            })
    after = probe.require_baseline_catalogue(catalogue)
    assert before == after
    assert all(
        not project['first_to_second']['changed']
        and not project['second_to_third']['changed']
        and project['stl_maps_equal']
        and project['manifests_equal']
        for project in projects
    )
    print(json.dumps({
        'label': 'ar07-disposable-three-pass',
        'formal_wp10': False,
        'original_catalogue_unchanged': True,
        'projects': projects,
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
