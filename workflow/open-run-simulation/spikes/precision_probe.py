"""Stress the unwrapped-float representation, not elapsed-time endurance.

Equivalent periodic configurations are initialized at enormous winding counts.
The second experiment subtracts a whole-turn origin before stepping; production
would need explicit winding/phase coordinates and transformation of local memory.
"""
import json
from kernel import Engine
from programs import curta, seal
from run import write


def main():
    samples = []
    for turns in (0, 10**6, 10**9, 10**12):
        p = curta()
        p['q']['crank'] = turns * 360.
        e = Engine(seal(p), dt=1)
        e.rate('crank', 180)
        error = None
        try:
            e.advance(1)
        except ValueError as exc:
            error = str(exc)
        actual = [e.q[f'wheel{i}'] for i in range(3)]
        # A phase-local coordinate plus a separately retained integer winding.
        local = Engine(curta(), dt=1)
        local.rate('crank', 180)
        local.advance(1)
        phase_actual = [local.q[f'wheel{i}'] for i in range(3)]
        assert all(abs(x-y) < 1e-8 for x, y in zip(phase_actual, (360, 360, 36)))
        samples.append(dict(initial_whole_turns=str(turns),
            unwrapped_float_wheels=actual, unwrapped_float_error=error,
            max_unwrapped_wheel_error=max(abs(x-y) for x, y in zip(actual, (360, 360, 36))),
            phase_local_wheels=phase_actual,
            phase_local_winding_after=str(turns), phase_local_degrees_after=local.q['crank']))
    record = dict(samples=samples, scope='large-origin representation stress; NOT a trillion-turn runtime test',
        conclusion='Use bounded local phases and separate integer winding for periodic coordinates; the baseline spike kernel stores plain floats.')
    write('precision-results.json', record)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
