"""Task 1.4: every fixture of `tests/running_project/` poses untimed on
the UNCHANGED tree, and the rest-pose numbers scenario "The initial bank
is the rest pose" compares against.

Neither `Time.running()` nor `Instruction(by=)` exists at the base, so
the module cannot be imported as written. The two shims below give the
declarations a base spelling -- a one-second LOOP for the running base,
and a `by=` keyword an instruction stores and nothing reads -- so the
fixture's RELATIONS can be posed. The numbers below are properties of
those relations and of the rest render, not of the time base: the point
of the probe is that this machine is a machine before this cycle
touches anything.
"""

from solid_node.motion.ports import Time
from solid_node.simulation.instruction import Instruction

Time.running = classmethod(lambda cls: cls(loop=1.0))

_original = Instruction.__init__


def _with_by(self, targets=None, duration=None, *, by=None):
    _original(self, targets if targets is not None else dict(by), duration)
    self.by = by


Instruction.__init__ = _with_by

from tests.running_project import machine as m  # noqa: E402
from solid_node.motion.ports import get_coordinate  # noqa: E402


def coordinates(node, names):
    return {name: get_coordinate(node, name)._value for name, node in names}


def show(label, node, reads):
    values = []
    for written, owner, name in reads:
        values.append(f'{written}={get_coordinate(owner(node), name)._value!r}')
    print(f'{label}: ' + ', '.join(values))


body = m.TrainBody()
body.set_state(crank=10.0, lever=100.0)
show('TrainBody at crank=10, lever=100 (default)', body, [
    ('first.turn', lambda n: n.first, 'turn'),
    ('second.turn', lambda n: n.second, 'turn'),
    ('slide.travel', lambda n: n.slide, 'travel'),
    ('spindle', lambda n: n, 'spindle'),
    ('wheel.turn (plain port)', lambda n: n.wheel, 'turn'),
])

backwards = m.Backwards()
backwards.set_state(crank=10.0)
show('Backwards at crank=10', backwards, [
    ('first.turn', lambda n: n.first, 'turn'),
    ('second.turn', lambda n: n.second, 'turn'),
])

differential = m.Differential()
differential.set_state(wrist_in=10.0, sum_in=30.0)
show('Differential at wrist_in=10, sum_in=30', differential, [
    ('wrist', lambda n: n, 'wrist'),
    ('tool', lambda n: n, 'tool'),
    ('left', lambda n: n, 'left'),
])

guarded = m.Guarded()
guarded.set_state(crank=10.0)
show('Guarded at crank=10', guarded, [
    ('first.turn', lambda n: n.first, 'turn'),
    ('slide.travel', lambda n: n.slide, 'travel'),
])

opaque = m.OpaqueBody()
opaque.set_state(crank=10.0)
show('OpaqueBody at crank=10', opaque, [
    ('relay', lambda n: n, 'relay'),
    ('first.turn', lambda n: n.first, 'turn'),
])

stepped = m.SteppedBody()
stepped.set_state(crank=470.0)
show('SteppedBody at crank=470 (one turn past the window)', stepped, [
    ('first.turn', lambda n: n.first, 'turn'),
])

stdlib = m.StdlibBody()
stdlib.set_state(crank=30.0)
show('StdlibBody at crank=30', stdlib, [
    ('first.turn', lambda n: n.first, 'turn'),
])

ranged = m.Ranged()
ranged.set_state(crank=10.0)
show('Ranged at crank=10', ranged, [
    ('first.turn', lambda n: n.first, 'turn'),
])

unbound = m.Unbound()
unbound.set_state(crank=10.0)
show('Unbound at crank=10', unbound, [
    ('first.turn', lambda n: n.first, 'turn'),
    ('idle.turn', lambda n: n.idle, 'turn'),
])

sixfree = m.Sixfree()
sixfree.set_state(lift=5.0, surge=1.0, sway=2.0, heading=30.0)
show('Sixfree at lift=5, surge=1, sway=2, heading=30', sixfree.chassis, [
    ('pose.x', lambda n: n, 'pose.x'),
    ('pose.y', lambda n: n, 'pose.y'),
    ('pose.z', lambda n: n, 'pose.z'),
    ('pose.yaw', lambda n: n, 'pose.yaw'),
    ('pose.roll', lambda n: n, 'pose.roll'),
    ('pose.pitch', lambda n: n, 'pose.pitch'),
])

follower = m.Follower()
follower.set_state(crank=10.0)
show('Follower at crank=10', follower, [
    ('first.turn', lambda n: n.first, 'turn'),
    ('gauge.turn', lambda n: n.gauge, 'turn'),
    ('gauge.readout', lambda n: n.gauge, 'readout'),
])

hand = m.HandBound()
hand.set_state(crank=10.0)
show('HandBound at crank=10', hand, [
    ('first.turn', lambda n: n.first, 'turn'),
])

print('every fixture posed untimed on the unchanged tree')
