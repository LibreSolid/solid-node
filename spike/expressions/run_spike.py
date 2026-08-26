"""ADR-056 expression-spike runner: one section per SCOPE sub-question.

Run from the framework worktree root:

    PYTHONPATH="$PWD" <venv>/bin/python spike/expressions/run_spike.py

Prints a VERDICT line per sub-question and a summary. Artifacts land in
spike/expressions/_build/ (gitignored). NON-SHIPPING.

Since the `instance-qualified-drivers` change landed, this is CALLER
VALIDATION rather than a spike behind shims: every sub-question is now
answered by the shipped API -- `AssemblyNode.set_state` by qualified
id, `core.serializer.symbolic_drivers`,
`simulation.enumeration.qualified_drivers`, and `Sim` over a driverless
root. The two hazards the spike found (an unlinked walk qualifying to
the bare name, a list-held child's illegal id segment) are now loud
failures, and this runner asserts the noise.
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

from solid_node.core.serializer import symbolic_drivers           # noqa: E402
from solid_node.node.assembly import AssemblyNode                # noqa: E402
from solid_node.node.base import _compose_world_matrix           # noqa: E402
from solid_node.node.qualified import (DriverIdError, DriverToken,  # noqa: E402
                                       driver_id, instance_path)
from solid_node.simulation import Sim                            # noqa: E402
from solid_node.simulation.driver import declared_drivers        # noqa: E402
from solid_node.simulation.enumeration import qualified_drivers  # noqa: E402

from machine_model import Axis, Machine                          # noqa: E402
from symbolic import collect_ops                                 # noqa: E402

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

    token = DriverToken('x_axis.motor')
    try:
        machine.set_state(**{'x_axis.motor': token})
        rejected = False
        findings.append('set_state accepted a symbolic value')
    except TypeError as error:
        rejected = True
        print(f'  set_state still rejects a symbolic value: '
              f'TypeError({error})')

    # Seam 1 closed: the shipped symbolic serialization MODE binds every
    # declared driver to its token through an internal path, so
    # _validate_state's numbers-only contract never had to be relaxed.
    machine = Machine()
    with symbolic_drivers(machine) as declarations:
        values, chain, nodes = collect_ops(machine)
    print(f'  symbolic_drivers bound {sorted(declarations)}')
    for key in sorted(values):
        print(f'    {key} = {values[key]}')

    wire = values['Machine/x_axis/cover#0.angle']
    expected = 'asin((0.25 * sin((x_axis.motor * 0.1125))))'
    well_formed = wire == expected
    if not well_formed:
        findings.append(f'cover angle was {wire!r}, expected {expected!r}')

    ok = loud and rejected and well_formed
    verdict('1-symbolic-reads',
            'validated on the shipped API' if ok else 'INVALIDATED',
            'unbound reads stay loud, set_state still refuses non-numbers, '
            'and the shipped symbolic serialization mode binds every '
            'declared driver to its token through a separate internal door, '
            'flowing through project arithmetic and degree trig into '
            'well-formed wire strings'
            if ok else '; '.join(findings))
    return values, chain, nodes


# --------------------------------------------------------------------
# Sub-question 2: qualification
# --------------------------------------------------------------------

def _root_of(node):
    """The topmost linked ancestor: the spike's own convenience, since
    the shipped `instance_path(node, root)` addresses a path RELATIVE to
    a stated root (there is no global namespace to walk to)."""
    current = node
    while getattr(current, '_parent', None) is not None:
        current = current._parent
    return current


class ProbeAxis(Axis):
    """Records what the node knows about its own identity at the exact
    moment render() builds its expressions."""

    trace = []

    def render(self):
        linked = getattr(self, '_parent', None) is not None
        path = instance_path(self, _root_of(self)) if linked else None
        ProbeAxis.trace.append((self.label, self.name, path, linked))
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
    with symbolic_drivers(probe):
        pass
    print('  render-time identity, in binding/serialization order:')
    for label, name, path, linked in ProbeAxis.trace:
        print(f'    Axis({label!r}): name={name!r} path={path} '
              f'linked={linked}')
    known_at_render = all(linked and len(path) == 1
                          for _, _, path, linked in ProbeAxis.trace)

    # SEAM 3 CLOSED: set_state's own propagation now links each child
    # before recursing, exactly as the scad and serializer passes do, so
    # a never-assembled tree is qualified correctly instead of silently
    # collapsing both instances onto the bare name.
    hazard = Machine()
    hazard.set_state(**{'x_axis.motor': 0, 'y_axis.motor': 0, 'time': 0.0})
    linked_names = sorted({hazard.x_axis.name, hazard.y_axis.name})
    print(f'  after set_state() on a never-assembled tree: names='
          f'{linked_names} -- the propagation walk links before it '
          f'recurses (assembly.py _rendered_children)')
    walk_links = linked_names == ['x_axis', 'y_axis']

    try:
        instance_path(Machine().x_axis, Machine())
        unlinked_loud = False
        print('    an unlinked instance qualified silently (unexpected)')
    except DriverIdError as error:
        unlinked_loud = True
        print(f'    an unlinked instance refuses to qualify: '
              f'DriverIdError({str(error)[:88]}...)')

    # Two instances, distinct ids, distinct bound values.
    distinct_ids = (
        sym_values['Machine/x_axis/pulley#0.angle'] ==
        '(x_axis.motor * 0.1125)' and
        sym_values['Machine/y_axis/pulley#0.angle'] ==
        '(y_axis.motor * 0.1125)')
    print(f"  x pulley angle: {sym_values['Machine/x_axis/pulley#0.angle']}")
    print(f"  y pulley angle: {sym_values['Machine/y_axis/pulley#0.angle']}")

    numeric = Machine()
    numeric.set_state(**{'x_axis.motor': 8000, 'y_axis.motor': 2000,
                         'time': 0.0})
    num_values, _, _ = collect_ops(numeric)
    x_num = float(num_values['Machine/x_axis/carriage#0.t0'])
    y_num = float(num_values['Machine/y_axis/carriage#0.t0'])
    print(f'  same two instances bound numerically: x carriage={x_num} mm, '
          f'y carriage={y_num} mm')
    distinct_values = abs(x_num - 100.0) < 1e-9 and abs(y_num - 25.0) < 1e-9

    # SEAM 4 CLOSED: a child held in a LIST is named `<attr>-<index>`
    # (base.py _attr_name_for), which is not a legal identifier in
    # either target runtime. v1 forbids it loudly rather than emitting
    # an id that parses as a subtraction.
    try:
        with symbolic_drivers(ListMachine()):
            pass
        segment_loud = False
        print('  a list-held driver serialized silently (unexpected)')
    except DriverIdError as error:
        segment_loud = True
        print(f'  identifier rule: a driver behind a list-held child '
              f'refuses to qualify: DriverIdError({str(error)[:96]}...)')

    print(f"  id syntax as shipped: {driver_id(('x_axis',), 'motor')!r}")

    ok = (known_at_render and distinct_ids and distinct_values
          and walk_links and unlinked_loud and segment_loud)
    verdict('2-qualification',
            'validated on the shipped API' if ok
            else 'INVALIDATED',
            'a node knows its parent and derived name at the moment its '
            'own render() runs, in every pass that links before it '
            'recurses -- including set_state, which now links; two '
            'instances of one class serialize x_axis.motor vs '
            'y_axis.motor and bind 100 mm vs 25 mm, and both hazards the '
            'spike found are loud failures'
            if ok else f'known_at_render={known_at_render} '
                       f'walk_links={walk_links} '
                       f'unlinked_loud={unlinked_loud} '
                       f'segment_loud={segment_loud}')
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
        numeric.set_state(**snapshot)
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
    machine.set_state(**snapshot)
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

    print(f'  declared_drivers(Machine) = {declared_drivers(Machine)} '
          '-- the single-class scan still sees nothing, because the root '
          'declares no driver')
    print(f'  qualified_drivers(Machine()) = '
          f'{sorted(qualified_drivers(Machine()))} -- SEAM 5 CLOSED: the '
          'shipped enumeration walks the whole linked tree')

    # SEAM 2 CLOSED: an ambiguous BARE bind no longer shares one value
    # between two instances -- it refuses, naming the qualified cure.
    flat = Machine()
    try:
        flat.set_state(motor=1234, time=0.0)
        refuses_ambiguity = False
        print(f'  set_state(motor=1234) -> x_axis.motor='
              f'{flat.x_axis.state["motor"]}, y_axis.motor='
              f'{flat.y_axis.state["motor"]} (unexpected: silently shared)')
    except ValueError as error:
        refuses_ambiguity = True
        print(f'  set_state(motor=1234) refuses rather than sharing one '
              f'value: ValueError({str(error)[:104]}...)')

    # The whole machine now steps through the shipped Sim, over a root
    # that declares nothing: the bank is keyed by the same qualified ids
    # the serialized document publishes.
    machine = Machine()
    sim = Sim(machine, 0.1)
    print(f'  Sim(machine, dt) constructs; qualified bank: '
          f'{sorted(sim.drivers)}')
    sim.drivers['x_axis.motor'].value = 8000
    sim.drivers['y_axis.motor'].value = 0
    sim.drivers['x_axis.motor'].ramp_to(0, 10, 0)        # x homes
    sim.drivers['y_axis.motor'].ramp_to(6400, 10, 0)     # y to 80 mm

    trajectory = []
    for _ in range(10):
        sim.run(0.1)
        values, _, _ = collect_ops(machine)
        trajectory.append((
            sim.tick,
            float(values['Machine/x_axis/carriage#0.t0']),
            float(values['Machine/y_axis/carriage#0.t0']),
        ))
    for tick, x, y in trajectory[:3] + trajectory[-2:]:
        print(f'    tick {tick:2d}: x carriage = {x:7.3f} mm, '
              f'y carriage = {y:7.3f} mm')
    independent = (abs(trajectory[-1][1] - 0.0) < 1e-9 and
                   abs(trajectory[-1][2] - 80.0) < 1e-9 and
                   all(abs(x - y) > 1e-9 for _, x, y in trajectory[:-1]))

    # `time` is one driver among the rest, and under a Sim it is the
    # stepped clock in seconds rather than the normalized 0..1 $t.
    clock = abs(machine.time - 1.0) < 1e-12
    print(f'  self.time under the Sim after 10 ticks of dt=0.1: '
          f'{machine.time} s (the stepped clock, not $t)')

    # A child's instruction homes only that child.
    homing = Sim(Machine(), 0.1)
    homing.at(0.0).trigger('x_axis.Home')
    homing.run(2.0)
    per_instance = (homing.state['x_axis.motor'] == 0 and
                    homing.state['y_axis.motor'] == 8000)
    print(f"  trigger('x_axis.Home') -> {homing.state} -- SEAM 6 CLOSED: "
          'only the addressed instance ramps')

    ok = refuses_ambiguity and independent and clock and per_instance
    verdict('5-state-bank',
            'validated on the shipped API' if ok else 'INVALIDATED',
            'the shipped Sim enumerates a driverless root\'s whole tree, '
            'keys its bank by the same qualified ids the document '
            'publishes, drives the two axes to 0 mm and 80 mm '
            'independently, binds `time` as the stepped clock in seconds, '
            'and homes one instance without touching its sibling'
            if ok else f'refuses_ambiguity={refuses_ambiguity} '
                       f'independent={independent} clock={clock} '
                       f'per_instance={per_instance}')


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
