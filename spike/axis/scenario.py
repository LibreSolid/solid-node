"""ADR-056 spike runner: scenario, determinism, purity, teeth, timing.

Run from anywhere with the workspace venv and the worktree on
PYTHONPATH, e.g.:

    PYTHONPATH=<worktree> <venv>/bin/python spike/axis/scenario.py

Prints one section per SCOPE sub-question and a machine-readable
summary line per verdict. Since the stepped-simulation-layer change,
the harness under test is the shipped solid_node.simulation package
rather than the spike's own steplab.py: this runner is now caller
validation, revalidating every recorded verdict against the real API.
"""

import time

from solid_node.simulation import Sim
from solid_node.test import TestCase

from axis_model import HOME_USTEPS, MM_PER_USTEP, XAxis

DT = 0.02

VERDICTS = []


def verdict(key, ok, detail):
    VERDICTS.append((key, ok, detail))
    print(f'  VERDICT {key}: {"validated" if ok else "INVALIDATED"} — {detail}')


def fresh_sim():
    axis = XAxis()
    build_start = time.perf_counter()
    sim = Sim(axis, DT, meshes=True)
    return axis, sim, time.perf_counter() - build_start


def home_scenario(register_assertions=True):
    """The SCOPE scenario: Home X at t=0, interference every 0.1 s,
    terminal check at t=2.5, run 3.0 s."""
    axis, sim, build_seconds = fresh_sim()
    tc = TestCase('set_node')
    outcome = {}

    sim.at(0.0).trigger('Home X')
    if register_assertions:
        sim.every(0.1, tc.assertNoSolidInterference, axis)

    def final_check(s):
        outcome['motor'] = s.state['motor']
        outcome['x'] = axis.x_out.value

    sim.at(2.5).run(final_check)

    run_start = time.perf_counter()
    sim.run(3.0)
    outcome['run_seconds'] = time.perf_counter() - run_start
    outcome['build_seconds'] = build_seconds
    return axis, sim, outcome


def main():
    print('== Build + scenario (sub-questions 1, 3, 4; scenario itself) ==')
    axis, sim, outcome = home_scenario()
    calls, mean = sim.assertion_stats
    print(f'  first build+assemble: {outcome["build_seconds"]:.2f}s; '
          f'scenario 150 ticks: {outcome["run_seconds"]:.2f}s; '
          f'{calls} interference checks, mean {mean * 1000:.1f}ms')
    verdict('instruction-ramp',
            outcome['motor'] == 0 and outcome['x'] == 0.0,
            f'at t=2.5 motor={outcome["motor"]} usteps, x={outcome["x"]} mm '
            '(expected exactly 0, 0.0)')

    print('== Sub-question 1: purity across re-renders ==')
    # After 150 renders the carriage must hold exactly ONE driven
    # translation (the sweep replaced, never accumulated), and binding
    # an arbitrary snapshot must place it absolutely.
    axis.set_state(motor=4000)          # x = 50 mm
    ops = len(axis.carriage.operations)
    bounds_x = axis.carriage.mesh.bounds[:, 0]
    placed = (abs(bounds_x[0] - 50.0) < 1e-6 and
              abs(bounds_x[1] - 90.0) < 1e-6)
    verdict('purity',
            ops == 1 and placed,
            f'carriage operations={ops} (expected 1) after 151 renders; '
            f'mesh x-bounds {bounds_x[0]:.6f}..{bounds_x[1]:.6f} '
            '(expected 50..90)')

    print('== Sub-question 2: determinism ==')
    t1 = home_scenario(register_assertions=False)[1].trajectory
    t2 = home_scenario(register_assertions=False)[1].trajectory
    verdict('determinism',
            t1 == t2 and len(t1) == 150,
            f'two fresh runs, {len(t1)} ticks each, trajectories '
            f'{"exactly equal" if t1 == t2 else "DIFFER"} '
            '(integer states, exact comparison)')

    print('== Assertion teeth: overshoot must fail ==')
    axis3, sim3, _ = fresh_sim()
    tc3 = TestCase('set_node')
    sim3.at(0.0).trigger('Crash X')     # x -> -5 mm, past the mount at -2
    sim3.every(0.1, tc3.assertNoSolidInterference, axis3)
    try:
        sim3.run(3.0)
        verdict('teeth', False, 'overshoot to x=-5mm raised nothing')
    except AssertionError as error:
        verdict('teeth', True, f'overshoot failed as it must: {error}')

    print('== Sub-question 5: cost ==')
    axis4, sim4, _ = fresh_sim()
    sim4.at(0.0).trigger('Home X')
    start = time.perf_counter()
    sim4.run(3.0)                       # 150 ticks, no assertions
    bare = time.perf_counter() - start
    ticks_per_second = 150 / bare
    print(f'  bare stepping: 150 ticks in {bare:.3f}s '
          f'-> {ticks_per_second:.0f} ticks/s; '
          f'interference check mean {mean * 1000:.1f}ms '
          f'(~{1 / mean:.0f}/s)' if mean else '  (no assertion timing)')
    verdict('cost',
            ticks_per_second > 100,
            f'{ticks_per_second:.0f} bare ticks/s; one interference check '
            f'costs {mean * 1000:.1f}ms ~= {mean * ticks_per_second:.1f} '
            'bare ticks')

    print('== Summary ==')
    for key, ok, _ in VERDICTS:
        print(f'  {key}: {"validated" if ok else "INVALIDATED"}')
    return 0 if all(ok for _, ok, _ in VERDICTS) else 1


if __name__ == '__main__':
    raise SystemExit(main())
