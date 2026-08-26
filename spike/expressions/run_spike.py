"""ADR-056 expression-spike runner: one section per SCOPE sub-question.

Run from the framework worktree root:

    PYTHONPATH="$PWD" <venv>/bin/python spike/expressions/run_spike.py

Prints a VERDICT line per sub-question and a summary. Artifacts land in
spike/expressions/_build/ (gitignored). NON-SHIPPING.
"""

import contextlib
import json
import logging
import math
import os
import subprocess
import sys

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from solid_node.node.assembly import AssemblyNode                # noqa: E402
from solid_node.node.base import _compose_world_matrix           # noqa: E402
from solid_node.simulation import Sim                            # noqa: E402
from solid_node.simulation.driver import DriverState, driver_states  # noqa: E402

from machine_model import Axis, Machine                          # noqa: E402
from symbolic import (bind_numeric, bind_symbolic, collect_ops,  # noqa: E402
                      driver_id, instance_path, qualified_drivers)

BUILD = os.path.join(HERE, '_build')
NODE = 'node'
OPENSCAD = '/usr/bin/openscad'

# Seven sampled snapshots: distinct per-axis driver values (so the two
# instances can never agree by accident) and distinct times.
SNAPSHOTS = [
    {'x_axis.motor': 0,    'y_axis.motor': 8000, 'time': 0.0},
    {'x_axis.motor': 1234, 'y_axis.motor': 6543, 'time': 0.125},
    {'x_axis.motor': 4000, 'y_axis.motor': 400,  'time': 0.25},
    {'x_axis.motor': 8000, 'y_axis.motor': 3200, 'time': 0.37},
    {'x_axis.motor': -400, 'y_axis.motor': 111,  'time': 0.5},
    {'x_axis.motor': 6543, 'y_axis.motor': 1234, 'time': 0.75},
    {'x_axis.motor': 3200, 'y_axis.motor': 8000, 'time': 0.9},
]

VERDICTS = []


def verdict(key, outcome, detail):
    VERDICTS.append((key, outcome, detail))
    print(f'  VERDICT {key}: {outcome} -- {detail}')


def section(title):
    print(f'\n== {title} ==')


def driver_context(snapshot):
    """The snapshot as the client would hold it: a nested map, because
    the qualified id `x_axis.motor` parses as a member access."""
    context = {'$t': snapshot['time']}
    for key, value in snapshot.items():
        if key == 'time':
            continue
        instance, name = key.rsplit('.', 1)
        context.setdefault(instance, {})[name] = value
    return context


# --------------------------------------------------------------------
# Sub-question 1: symbolic driver reads
# --------------------------------------------------------------------

def sub_question_1():
    section('Sub-question 1: symbolic driver reads')
    findings = []

    machine = Machine()
    try:
        machine.x_axis.state['motor']
        findings.append('unbound read did NOT raise')
        loud = False
    except KeyError as error:
        loud = True
        print(f'  unbound read raises, as designed: KeyError({error})')

    from symbolic import DriverToken
    token = DriverToken(machine.x_axis, 'motor')
    try:
        machine.set_state(motor=token)
        rejected = False
        findings.append('set_state accepted a symbolic value')
    except TypeError as error:
        rejected = True
        print(f'  set_state rejects a symbolic value: TypeError({error})')

    # The shim: bind tokens directly into the state dicts.
    machine = Machine()
    bind_symbolic(machine)
    values, chain, nodes = collect_ops(machine)
    for key in sorted(values):
        print(f'    {key} = {values[key]}')

    wire = values['Machine/x_axis/cover#0.angle']
    expected = 'asin((0.25 * sin((x_axis.motor * 0.1125))))'
    well_formed = wire == expected
    if not well_formed:
        findings.append(f'cover angle was {wire!r}, expected {expected!r}')

    ok = loud and rejected and well_formed
    verdict('1-symbolic-reads',
            'validated (behind a shim; seam named)' if ok else 'INVALIDATED',
            'unbound reads stay loud, set_state still refuses non-numbers, '
            'and tokens bound past it flow through project arithmetic and '
            f'degree trig into well-formed wire strings'
            if ok else '; '.join(findings))
    return values, chain, nodes


# --------------------------------------------------------------------
# Sub-question 2: qualification
# --------------------------------------------------------------------

class ProbeAxis(Axis):
    """Records what the node knows about its own identity at the exact
    moment render() builds its expressions."""

    trace = []

    def render(self):
        ProbeAxis.trace.append(
            (self.label, self.name, instance_path(self),
             getattr(self, '_parent', None) is not None))
        return super().render()


class ProbeMachine(Machine):
    axis_class = ProbeAxis


class ListMachine(Machine):
    """Holds its axes in a LIST instead of named attributes, which is
    how _attr_name_for produces `<attr>-<index>` names."""

    def __init__(self, *args, **kwargs):
        AssemblyNode.__init__(self, *args, **kwargs)
        self.axes = [Axis('x'), Axis('y')]

    def render(self):
        return list(self.axes)


def sub_question_2(sym_values):
    section('Sub-question 2: qualification, local names -> global ids')

    fresh = Machine()
    print(f'  before any linking: x_axis.name={fresh.x_axis.name!r} '
          f'y_axis.name={fresh.y_axis.name!r} '
          f'(both the CLASS name -- names are derived by the parent)')
    fresh.render()
    print(f'  after machine.render() alone: x_axis.name='
          f'{fresh.x_axis.name!r} (render does NOT link)')

    ProbeAxis.trace = []
    probe = ProbeMachine()
    bind_symbolic(probe)
    print('  render-time identity, in binding/serialization order:')
    for label, name, path, linked in ProbeAxis.trace:
        print(f'    Axis({label!r}): name={name!r} path={path} '
              f'linked={linked}')
    known_at_render = all(linked and len(path) == 1
                          for _, _, path, linked in ProbeAxis.trace)

    # The hazard: set_state's own propagation renders children WITHOUT
    # linking them first.
    hazard = Machine()
    hazard._states.update({})
    for axis in (hazard.x_axis, hazard.y_axis):
        axis._states['motor'] = 0
    hazard.set_state(time=0.0)
    unlinked_names = {hazard.x_axis.name, hazard.y_axis.name}
    print(f'  after set_state() on a never-assembled tree: names='
          f'{sorted(unlinked_names)} -- set_state renders children '
          f'without linking them (assembly.py _rendered_children)')

    x_id = driver_id(Machine().x_axis, 'motor')  # unlinked -> collides
    print(f'    an unlinked instance qualifies to {x_id!r}')

    # Two instances, distinct ids, distinct bound values.
    distinct_ids = (
        sym_values['Machine/x_axis/pulley#0.angle'] ==
        '(x_axis.motor * 0.1125)' and
        sym_values['Machine/y_axis/pulley#0.angle'] ==
        '(y_axis.motor * 0.1125)')
    print(f"  x pulley angle: {sym_values['Machine/x_axis/pulley#0.angle']}")
    print(f"  y pulley angle: {sym_values['Machine/y_axis/pulley#0.angle']}")

    numeric = Machine()
    bind_numeric(numeric, {'x_axis.motor': 8000, 'y_axis.motor': 2000})
    numeric.set_state(time=0.0)
    num_values, _, _ = collect_ops(numeric)
    x_num = float(num_values['Machine/x_axis/carriage#0.t0'])
    y_num = float(num_values['Machine/y_axis/carriage#0.t0'])
    print(f'  same two instances bound numerically: x carriage={x_num} mm, '
          f'y carriage={y_num} mm')
    distinct_values = abs(x_num - 100.0) < 1e-9 and abs(y_num - 25.0) < 1e-9

    # A child held in a LIST gets the name `<attr>-<index>`
    # (base.py _attr_name_for), which is not a legal identifier in
    # either target runtime -- the id would parse as a subtraction.
    listed = ListMachine()
    bind_symbolic(listed)
    list_values, _, _ = collect_ops(listed)
    bad_key = next(key for key in list_values
                   if 'pulley' in key and '-' in key)
    bad_id = list_values[bad_key]
    print(f'  identifier hazard: a child held in a LIST is named '
          f'{bad_key.split("/")[1]!r}, so its driver serializes as '
          f'{bad_id!r} -- a subtraction, not a name')

    flat_id = driver_id(probe.x_axis, 'motor', sep='__')
    print(f"  flat-identifier variant (sep='__'): {flat_id!r} -- also "
          'well-formed, and legal in OpenSCAD as well')

    ok = known_at_render and distinct_ids and distinct_values
    verdict('2-qualification',
            'validated (eager qualification viable)' if ok
            else 'INVALIDATED',
            'a node knows its parent and derived name at the moment its '
            'own render() runs, in every pass that links before it '
            'recurses; two instances of one class serialize x_axis.motor '
            'vs y_axis.motor and bind 100 mm vs 25 mm'
            if ok else 'path not knowable at render time')
    return known_at_render


# --------------------------------------------------------------------
# Sub-question 3: client parity
# --------------------------------------------------------------------

def world_matrix(path, chain, value_of):
    """The node's world matrix, composed exactly as
    base.py _compose_matrix does: own operations first, then each
    ancestor's, each premultiplied onto the running total."""
    matrix = np.eye(4)
    current = path
    while current is not None:
        parent, ops = chain[current]
        for kind, axis, keys in ops:
            if kind == 'r':
                step = trimesh.transformations.rotation_matrix(
                    math.radians(value_of(keys[0])), axis)
            else:
                step = trimesh.transformations.translation_matrix(
                    [value_of(key) for key in keys])
            matrix = step @ matrix
        current = parent
    return matrix


def sub_question_3(sym_values, sym_chain):
    section('Sub-question 3: client parity')

    numeric = Machine()
    python_values = {}
    for index, snapshot in enumerate(SNAPSHOTS):
        bind_numeric(numeric, {k: v for k, v in snapshot.items()
                               if k != 'time'})
        numeric.set_state(time=snapshot['time'])
        values, chain, nodes = collect_ops(numeric)
        python_values[index] = {k: float(v) for k, v in values.items()}
        if index == 0:
            # Self-check: the composer above must reproduce the
            # framework's own world matrix for a driven leaf.
            path = 'Machine/y_axis/cover'
            mine = world_matrix(path, chain,
                                lambda k: python_values[0][k])
            theirs = _compose_world_matrix(nodes[path])
            drift = float(np.max(np.abs(mine - theirs)))
            print(f'  composer self-check vs _compose_world_matrix: '
                  f'max |delta| = {drift:.3e}')
            assert drift < 1e-12, drift

    cases = {}
    for index, snapshot in enumerate(SNAPSHOTS):
        context = driver_context(snapshot)
        for key, expression in sym_values.items():
            cases[f'{index}|{key}'] = {'expression': expression,
                                       'context': context}
    request = os.path.join(BUILD, 'parity_input.json')
    response = os.path.join(BUILD, 'parity_output.json')
    with open(request, 'w') as handle:
        json.dump({'cases': cases}, handle)
    print(f'  {subprocess.run([NODE, os.path.join(HERE, "parity_harness.js"), request, response], capture_output=True, text=True, check=True).stdout.strip()}'
          f' ({len(SNAPSHOTS)} snapshots x {len(sym_values)} expressions)')
    with open(response) as handle:
        client = json.load(handle)

    errors = [result['error'] for result in client.values()
              if result['error']]
    worst_scalar = 0.0
    worst_key = None
    for case_key, result in client.items():
        index, key = case_key.split('|', 1)
        delta = abs(result['value'] - python_values[int(index)][key])
        if delta > worst_scalar:
            worst_scalar, worst_key = delta, case_key

    worst_matrix = 0.0
    for index in range(len(SNAPSHOTS)):
        for path in sym_chain:
            py = world_matrix(path, sym_chain,
                              lambda k: python_values[index][k])
            js = world_matrix(path, sym_chain,
                              lambda k: client[f'{index}|{k}']['value'])
            worst_matrix = max(worst_matrix,
                               float(np.max(np.abs(py - js))))

    pow_cases = {key: result for key, result in client.items()
                 if result['rawPow'] is not None}
    pow_gap = max((abs(result['rawPow'] - result['value'])
                   for result in pow_cases.values()), default=0.0)
    print(f'  max |python - client| over scalars: {worst_scalar:.3e} '
          f'(worst case {worst_key})')
    print(f'  `^` rewrite is load-bearing: {len(pow_cases)} expressions '
          f'contain `^`; without powify they diverge by up to {pow_gap:.3f}')
    print(f'  max |python - client| over composed 4x4 world matrices: '
          f'{worst_matrix:.3e}')

    # The isAnimated replacement.
    static_key = '0|Machine/y_axis#0.angle'
    trig_key = '0|Machine/x_axis/cover#0.angle'
    mixed_key = '0|Machine/x_axis/cover#1.t0'
    print(f'  free variables from the parsed tree (isAnimated candidate):')
    for key in (static_key, trig_key, mixed_key):
        print(f'    {key.split("|", 1)[1]:34s} -> '
              f'{client[key]["freeVars"] or "[] (static)"}')
    static_is_static = client[static_key]['freeVars'] == []
    trig_reads_driver = client[trig_key]['freeVars'] == ['x_axis.motor']
    mixed_reads_both = client[mixed_key]['freeVars'] == ['$t', 'x_axis.motor']

    ok = (not errors and worst_scalar < 1e-9 and worst_matrix < 1e-9
          and static_is_static and trig_reads_driver and mixed_reads_both)
    verdict('3-client-parity',
            'validated' if ok else 'INVALIDATED',
            f'{len(client)} evaluations, max scalar deviation '
            f'{worst_scalar:.3e}, max world-matrix deviation '
            f'{worst_matrix:.3e}; free-variable analysis separates static, '
            'driver-only and mixed expressions'
            if ok else f'errors={errors[:3]} scalar={worst_scalar:.3e} '
                       f'matrix={worst_matrix:.3e}')
    return worst_scalar, worst_matrix


# --------------------------------------------------------------------
# Sub-question 4: scad snapshot substitution
# --------------------------------------------------------------------

@contextlib.contextmanager
def quiet():
    """Silence the STL build: OpenSCAD is spawned with this process's
    own stdout/stderr, and the spike's transcript is the deliverable."""
    saved = os.dup(1), os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    sys.stdout.flush()
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    try:
        yield
    finally:
        os.dup2(saved[0], 1)
        os.dup2(saved[1], 2)
        for descriptor in (*saved, devnull):
            os.close(descriptor)


def openscad(arguments):
    """OpenSCAD PNG export needs a GL context; this box is headless, so
    the call is wrapped in xvfb-run when no DISPLAY is set."""
    prefix = [] if os.environ.get('DISPLAY') else ['xvfb-run', '-a']
    return subprocess.run(prefix + [OPENSCAD] + arguments,
                          capture_output=True, text=True)


def emit_scad(snapshot, filename):
    """A fresh tree bound to `snapshot`, with time left UNBOUND so it
    stays solid2's symbolic $t, assembled and written as .scad."""
    machine = Machine()
    bind_numeric(machine, snapshot)
    with quiet():
        machine.build_stls()
    code = machine.scad_code
    path = os.path.join(machine.build_dir, filename)
    with open(path, 'w') as handle:
        handle.write(code)
    return path, code


def sub_question_4():
    section('Sub-question 4: scad snapshot substitution')

    # Warm the leaf STLs first. On a cold tree `import_optimized`
    # inlines each leaf's geometry because its artifact is not current
    # yet, so the first .scad differs in SIZE (not in driver or $t
    # content) from every later one; emitting both snapshots against a
    # current build keeps the transcript comparable.
    emit_scad({'x_axis.motor': 0, 'y_axis.motor': 0}, 'warmup.scad')

    a_path, a_code = emit_scad({'x_axis.motor': 8000, 'y_axis.motor': 2000},
                               'snapshot_a.scad')
    b_path, b_code = emit_scad({'x_axis.motor': 1600, 'y_axis.motor': 6400},
                               'snapshot_b.scad')

    def formulas(code):
        return sorted({line.strip() for line in code.splitlines()
                       if '$t' in line})

    print(f'  {os.path.relpath(a_path, HERE)}: {len(a_code)} bytes')
    for line in formulas(a_code):
        print(f'    mixed: {line}')
    print(f'  {os.path.relpath(b_path, HERE)}: {len(b_code)} bytes')
    for line in formulas(b_code):
        print(f'    mixed: {line}')

    time_symbolic = '$t' in a_code and '$t' in b_code
    no_driver_names = ('motor' not in a_code and 'motor' not in b_code)
    differ = a_code != b_code
    mixed_survived = any('cos' in line and '+' in line
                         for line in formulas(a_code))

    png = os.path.join(os.path.dirname(a_path), 'snapshot_a.png')
    result = openscad(['-o', png, '--imgsize=900,700', '--autocenter',
                       '--viewall', '--colorscheme=Tomorrow', a_path])
    rendered = os.path.exists(png) and os.path.getsize(png) > 5000
    detail = ''
    if rendered:
        with open(png, 'rb') as handle:
            data = handle.read()
        detail = (f'{os.path.getsize(png)} bytes, '
                  f'{len(set(data))} distinct byte values')
        print(f'  openscad rendered {os.path.relpath(png, HERE)}: {detail}')
    else:
        print(f'  openscad failed: {result.stderr.strip()[:400]}')

    # OpenSCAD sweeps $t itself over an --animate run. Frames that
    # differ are direct proof the emitted .scad still animates on the
    # time term while every driver term is frozen at its bound value.
    frames_prefix = os.path.join(os.path.dirname(a_path), 'anim')
    openscad(['-o', frames_prefix + '.png', '--imgsize=400,300',
              '--autocenter', '--viewall', '--render', '--animate', '4',
              a_path])
    frames = sorted(name for name in os.listdir(os.path.dirname(a_path))
                    if name.startswith('anim') and name.endswith('.png'))
    frame_bytes = {name: open(os.path.join(os.path.dirname(a_path), name),
                              'rb').read() for name in frames}
    animated = len(set(frame_bytes.values())) > 1
    print(f'  --animate 4 over the same file: {len(frames)} frames, '
          f'{len(set(frame_bytes.values()))} distinct -- $t is still live')

    ok = (time_symbolic and no_driver_names and differ and mixed_survived
          and rendered and animated)
    verdict('4-scad-substitution',
            'validated' if ok else 'INVALIDATED',
            'two snapshots of one model emit different .scad, every driver '
            'term already numeric and $t still symbolic; the mixed formula '
            'survived partial substitution; OpenSCAD rendered it, and '
            '--animate frames still differ'
            if ok else f'time_symbolic={time_symbolic} '
                       f'no_driver_names={no_driver_names} differ={differ} '
                       f'mixed={mixed_survived} rendered={rendered}')
    return png


# --------------------------------------------------------------------
# Sub-question 5: state-bank qualification
# --------------------------------------------------------------------

def sub_question_5():
    section('Sub-question 5: state-bank qualification')

    print(f'  driver_states(Machine) = {driver_states(Machine)} '
          '-- Sim enumerates the ROOT class only, and the root declares '
          'no driver')

    unbound = Machine()
    try:
        Sim(unbound, 0.02)
        sim_blocked = False
        print('  Sim(machine, dt) constructed (unexpected)')
    except KeyError as error:
        sim_blocked = True
        print(f'  Sim(machine, dt) fails at its first render: KeyError'
              f'({str(error)[:90]}...)')

    flat = Machine()
    for axis in (flat.x_axis, flat.y_axis):
        axis._states['motor'] = 0
    flat.set_state(motor=1234, time=0.0)
    collided = (flat.x_axis.state['motor'] == flat.y_axis.state['motor']
                == 1234)
    print(f'  set_state(motor=1234) -> x_axis.motor='
          f'{flat.x_axis.state["motor"]}, y_axis.motor='
          f'{flat.y_axis.state["motor"]} -- one flat dict reaches every '
          'descendant, so the two instances CANNOT differ')

    # The shim: a state bank keyed by qualified id, stepped per instance.
    machine = Machine()
    bind_numeric(machine, {'x_axis.motor': 8000, 'y_axis.motor': 0})
    machine.set_state(time=0.0)
    bank = {key: DriverState(key, declaration)
            for key, (_, _, declaration) in
            qualified_drivers(machine).items()}
    for key, state in bank.items():
        state.value = {'x_axis.motor': 8000, 'y_axis.motor': 0}[key]
    print(f'  qualified bank: {sorted(bank)}')

    bank['x_axis.motor'].ramp_to(0, 10, 0)        # x homes
    bank['y_axis.motor'].ramp_to(6400, 10, 0)     # y advances to 80 mm
    trajectory = []
    for tick in range(1, 11):
        snapshot = {key: state.advance(tick) for key, state in bank.items()}
        bind_numeric(machine, snapshot)
        machine.set_state(time=tick / 10)
        values, _, _ = collect_ops(machine)
        trajectory.append((
            tick,
            float(values['Machine/x_axis/carriage#0.t0']),
            float(values['Machine/y_axis/carriage#0.t0']),
        ))
    for tick, x, y in trajectory[:3] + trajectory[-2:]:
        print(f'    tick {tick:2d}: x carriage = {x:7.3f} mm, '
              f'y carriage = {y:7.3f} mm')
    independent = (abs(trajectory[-1][1] - 0.0) < 1e-9 and
                   abs(trajectory[-1][2] - 80.0) < 1e-9 and
                   all(abs(x - y) > 1e-9 for _, x, y in trajectory[:-1]))

    ok = sim_blocked and collided and independent
    verdict('5-state-bank',
            'invalidated for the shipped API; validated behind the shim'
            if ok else 'INVALIDATED',
            "today's flat propagation and root-only driver enumeration make "
            'independent addressing structurally impossible; a bank keyed by '
            'the same qualified id sub-question 2 lands on drives the two '
            'axes to 0 mm and 80 mm independently'
            if ok else f'sim_blocked={sim_blocked} collided={collided} '
                       f'independent={independent}')


# --------------------------------------------------------------------

def main():
    os.makedirs(BUILD, exist_ok=True)
    logging.getLogger('node.base').setLevel(logging.WARNING)
    print('== Environment ==')
    print(f'  python: {sys.executable}')
    print(f'  worktree: {os.path.dirname(os.path.dirname(HERE))}')
    print(f'  node: {subprocess.run([NODE, "--version"], capture_output=True, text=True).stdout.strip()}')
    print(f'  openscad: {subprocess.run([OPENSCAD, "--version"], capture_output=True, text=True).stderr.strip()}')

    sym_values, sym_chain, _ = sub_question_1()
    sub_question_2(sym_values)
    sub_question_3(sym_values, sym_chain)
    sub_question_4()
    sub_question_5()

    print('\n== Summary ==')
    for key, outcome, _ in VERDICTS:
        print(f'  {key}: {outcome}')
    return 0 if all('INVALIDATED' not in outcome
                    for _, outcome, _ in VERDICTS) else 1


if __name__ == '__main__':
    raise SystemExit(main())
