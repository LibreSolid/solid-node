# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A joint's range is a physical stop located inside the tick.

OpenSpec change ``ranges-are-stops``, cycle 3 of the open-run campaign.
Cycles 1 and 2 failed the whole tick when a banked joint coordinate would
leave its declared range. Here the range is read as the mechanical limit
it states: the run locates the fraction ``t*`` of the tick at which the
coordinate reaches its bound, commits it AT that bound, stops every input
whose movement pushes it, lets everything else run its full tick, and
retires the pushing commands ``blocked`` with the travel they actually
admitted.

The two originating mechanisms are here with their own numbers: the
Pascaline module's ratchet, whose lower bound is an expression over its
own coordinate -- the last seated tooth -- and the spike's swept stop,
where a rack stops at its limit while an unrelated motor runs on.

Nothing here changes what an untimed or looping root does, which
``UntimedControlTest`` pins directly and the untouched suites pin at
large: there a range still REFUSES a binding outside it and never clamps
or stops.
"""

from unittest import skip

from pytest import approx

from solid_node.motion.joints import JointRangeError
from solid_node.motion.ports import get_coordinate
from solid_node.simulation import RunConflict, Sim, Stop

from .base import BaseNodeTest
from .running_project.machine import (Curved, CurvedBody, ImpossibleBoundBody,
                                      LoopingTrain, OpenGate, OpenGateBody,
                                      OpenLowBody, Ratchet, RatchetBody,
                                      Shared, SharedBody, StopAndJump,
                                      StopAndJumpBody, StoppedDifferential,
                                      Swept, SweptBody, SweptWide, TwoStops,
                                      TwoStopsBody)


def reads(node, qualified):
    """The value a coordinate holds, by the qualified id the run banks it
    under -- pixels' own source, since the joint places the body off
    exactly this number."""
    *path, name = qualified.split('.')
    for step in path:
        node = getattr(node, step)
    return get_coordinate(node, name)._value


def key_of(program, name):
    """The program node key of a coordinate, by its qualified id."""
    for key, node in program.nodes.items():
        if node.name == name:
            return key
    raise AssertionError(f'no program node called {name}')


def sources_of(sim, name):
    """The CANDIDATE inputs the compiled program says reach `name`."""
    return sim.program.sources[key_of(sim.program, name)]


class RatchetTest(BaseNodeTest):
    """(2) The worked example of design.md section 11, with its numbers.

    Forward rotation from the seated tooth is free; the reverse that
    follows blocks at the same tooth, admitting exactly what it had
    gained. That is retention.
    """

    def test_forward_from_the_seated_tooth_is_free(self):
        node = Ratchet()
        sim = Sim(node, 0.1, record=8)
        handle = sim.move('arbor', by=20.0, duration=0.1)
        sim.run(0.1)
        self.assertEqual(sim.state['wheel.turn'], 60.0)
        self.assertEqual(reads(node, 'wheel.turn'), 60.0)
        self.assertEqual(handle.status, 'completed')
        self.assertEqual(handle.admitted, 20.0)
        self.assertEqual(sim.stops, [])

    def test_a_reverse_blocks_at_the_last_seated_tooth(self):
        node = Ratchet()
        sim = Sim(node, 0.1, record=8)
        handle = sim.move('arbor', by=-10.0, duration=0.1)
        sim.run(0.1)
        self.assertEqual(sim.state['wheel.turn'], 36.0)
        self.assertEqual(sim.state['arbor'], 36.0)
        self.assertEqual(reads(node, 'wheel.turn'), 36.0)
        self.assertEqual(handle.status, 'blocked')
        self.assertEqual(handle.admitted, -4.0)
        self.assertEqual(handle.requested, -10.0)
        self.assertEqual(sim.tick, 1)
        self.assertEqual(sim.commands, ())
        stop, = sim.stops
        self.assertEqual(stop.coordinate, 'wheel.turn')
        self.assertEqual(stop.t, 0.4)

    def test_the_retention_sequence(self):
        """The last three rows of the table, read down: blocked at the
        tooth, free forward off it, blocked at it again."""
        sim = Sim(Ratchet(), 0.1, record=8)
        first = sim.move('arbor', by=-10.0, duration=0.1)
        sim.run(0.1)
        self.assertEqual((first.status, first.admitted), ('blocked', -4.0))

        again = sim.move('arbor', by=-10.0, duration=0.1)
        sim.run(0.1)
        self.assertEqual(sim.state['wheel.turn'], 36.0)
        self.assertEqual((again.status, again.admitted), ('blocked', 0.0))

        forward = sim.move('arbor', by=4.0, duration=0.1)
        sim.run(0.1)
        self.assertEqual(sim.state['wheel.turn'], 40.0)
        self.assertEqual((forward.status, forward.admitted),
                         ('completed', 4.0))

        back = sim.move('arbor', by=-10.0, duration=0.1)
        sim.run(0.1)
        self.assertEqual(sim.state['wheel.turn'], 36.0)
        self.assertEqual((back.status, back.admitted), ('blocked', -4.0))

    def test_a_push_from_the_stop_is_accepted_and_retires_at_once(self):
        """(5) A new command on a stopped input is accepted at once, and
        blocked in the tick it was issued with nothing admitted."""
        sim = Sim(Ratchet(), 0.1, record=8, state={'arbor': 36.0})
        handle = sim.move('arbor', by=-10.0, duration=0.1)
        self.assertEqual(handle.status, 'active')
        sim.run(0.1)
        self.assertEqual(handle.status, 'blocked')
        self.assertEqual(handle.admitted, 0.0)
        self.assertEqual(sim.state['wheel.turn'], 36.0)
        self.assertEqual(sim.commands, ())
        stop, = sim.stops
        self.assertEqual(stop.t, 0.0)
        # And the input is free at once: no ownership error.
        after = sim.move('arbor', by=4.0, duration=0.1)
        sim.run(0.1)
        self.assertEqual((after.status, after.admitted), ('completed', 4.0))

    def test_the_tooth_advances_with_the_arbor(self):
        sim = Sim(Ratchet(), 0.1, record=8, state={'arbor': 75.0})
        handle = sim.move('arbor', by=-10.0, duration=0.1)
        sim.run(0.1)
        self.assertEqual(sim.state['wheel.turn'], 72.0)
        self.assertEqual((handle.status, handle.admitted), ('blocked', -3.0))

    def test_a_blocked_command_never_resumes(self):
        sim = Sim(Ratchet(), 0.1, record=8)
        handle = sim.move('arbor', by=-10.0, duration=0.1)
        sim.run(0.1)
        sim.run(1.0)
        self.assertEqual(sim.state['wheel.turn'], 36.0)
        self.assertEqual(handle.status, 'blocked')
        self.assertEqual(handle.admitted, -4.0)
        self.assertEqual(sim.commands, ())
        self.assertEqual(len(sim.stops), 1)

    def test_a_reverse_rate_blocks_too(self):
        """A rate is not a promise of a total, but it is a command, and
        the run will not let a machine push silently against a stop for
        ever. (At -40 deg/s the first tick lands on exactly 36, which is
        INSIDE the inclusive bound and no stop at all; -50 overshoots
        it.)"""
        sim = Sim(Ratchet(), 0.1, record=8)
        steady = Sim(Ratchet(), 0.1, record=8)
        landing = steady.rate('arbor', -40.0)
        steady.run(0.1)
        self.assertEqual(steady.state['wheel.turn'], 36.0)
        self.assertEqual(landing.status, 'active')
        self.assertEqual(steady.stops, [])

        handle = sim.rate('arbor', -50.0)
        sim.run(0.1)
        self.assertEqual(sim.state['wheel.turn'], 36.0)
        self.assertEqual(handle.status, 'blocked')
        self.assertEqual(handle.admitted, -4.0)
        self.assertEqual(sim.commands, ())


class CadenceTest(BaseNodeTest):
    """(12) A stop admits the same travel at any cadence."""

    def test_the_same_reverse_move_at_three_cadences(self):
        for duration, ticks, blocking, fraction in ((0.1, 1, 1, 0.4),
                                                    (0.4, 4, 2, 0.6),
                                                    (4.0, 40, 17, 0.0)):
            with self.subTest(ticks=ticks):
                sim = Sim(Ratchet(), 0.1, record=64)
                handle = sim.move('arbor', by=-10.0, duration=duration)
                sim.run(duration)
                self.assertEqual(sim.state['wheel.turn'], 36.0)
                self.assertEqual(handle.status, 'blocked')
                self.assertEqual(handle.admitted, -4.0)
                stop, = sim.stops
                self.assertEqual(stop.tick, blocking)
                self.assertEqual(stop.t, fraction)

    def test_the_tick_that_lands_on_the_bound_is_ordinary(self):
        """Tick 16 of the forty-tick run lands on exactly 36, which is
        INSIDE the inclusive bound: no stop, and the command still
        active."""
        sim = Sim(Ratchet(), 0.1, record=64)
        handle = sim.move('arbor', by=-10.0, duration=4.0)
        sim.run(1.6)
        self.assertEqual(sim.tick, 16)
        self.assertEqual(sim.state['wheel.turn'], 36.0)
        self.assertEqual(handle.status, 'active')
        self.assertEqual(sim.stops, [])
        sim.run(0.1)
        self.assertEqual(handle.status, 'blocked')
        self.assertEqual(len(sim.stops), 1)


class SweptStopTest(BaseNodeTest):
    """(3) The spike's swept stop: the rack stops at its bound inside the
    tick while an independent motor runs its full tick."""

    def test_the_rack_stops_and_the_motor_continues(self):
        node = Swept()
        sim = Sim(node, 0.1, record=8)
        motor = sim.rate('motor', 90.0)
        steer = sim.move('steer', by=10.0, duration=0.1)
        sim.run(0.1)
        self.assertEqual(sim.state['rack.travel'], 50.0)
        self.assertEqual(reads(node, 'rack.travel'), 50.0)
        self.assertEqual(sim.state['wheel.turn'], 27.0)
        self.assertEqual((steer.status, steer.admitted), ('blocked', 5.0))
        self.assertEqual(motor.status, 'active')
        self.assertEqual(sim.commands, (motor,))
        stop, = sim.stops
        self.assertEqual(stop.coordinate, 'rack.travel')
        self.assertEqual(stop.t, 0.5)
        self.assertEqual(stop.inputs, ('steer',))

    def test_the_rack_holds_while_the_wheel_goes_on_turning(self):
        sim = Sim(Swept(), 0.1, record=8)
        sim.rate('motor', 90.0)
        sim.move('steer', by=10.0, duration=0.1)
        sim.run(0.1)
        sim.run(1.0)
        self.assertEqual(sim.state['rack.travel'], 50.0)
        self.assertEqual(sim.state['wheel.turn'], 297.0)
        self.assertEqual(len(sim.stops), 1)

    def test_an_instruction_reports_each_input_for_itself(self):
        sim = Sim(Swept(), 0.1, record=8)
        blocked, free = sim.trigger('Sweep')
        sim.run(0.1)
        self.assertEqual(blocked.input, 'steer')
        self.assertEqual((blocked.status, blocked.admitted), ('blocked', 5.0))
        self.assertEqual((free.status, free.admitted), ('completed', 9.0))
        self.assertEqual(sim.state['wheel.turn'], 27.0)


class SharedCoordinateTest(BaseNodeTest):
    """(6) A coordinate determined by a stopped input and a free one
    keeps moving on what the free one contributes."""

    def test_the_free_input_goes_on_contributing(self):
        sim = Sim(Shared(), 1.0, record=8)
        a_handle = sim.move('a_in', by=4.0, duration=1.0)
        b_handle = sim.move('b_in', by=6.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(sim.state['c.turn'], 10.0)
        self.assertEqual((a_handle.status, a_handle.admitted),
                         ('blocked', 2.0))
        self.assertEqual((b_handle.status, b_handle.admitted),
                         ('completed', 6.0))
        # 2*2 + 3*3 over segment A, then 3*3 over segment B: 22, not the
        # 26 an unstopped tick gives and not the 13 of segment A alone.
        self.assertEqual(sim.state['d.turn'] - 16.0, 22.0)
        stop, = sim.stops
        self.assertEqual(stop.inputs, ('a_in',))


class TwoStopsTest(BaseNodeTest):
    """(7) Two stops in one tick, taken earliest first."""

    def test_both_groups_stop_at_their_own_fraction(self):
        for order in ('lever first', 'rack first'):
            with self.subTest(order=order):
                sim = Sim(TwoStops(), 1.0, record=8)
                if order == 'lever first':
                    lever = sim.move('lever_in', by=8.0, duration=1.0)
                    rack = sim.move('steer', by=10.0, duration=1.0)
                else:
                    rack = sim.move('steer', by=10.0, duration=1.0)
                    lever = sim.move('lever_in', by=8.0, duration=1.0)
                sim.run(1.0)
                self.assertEqual(sim.state['lever.turn'], 20.0)
                self.assertEqual(sim.state['rack.travel'], 50.0)
                self.assertEqual((lever.status, lever.admitted),
                                 ('blocked', 2.0))
                self.assertEqual((rack.status, rack.admitted),
                                 ('blocked', 5.0))
                self.assertEqual([(stop.coordinate, stop.t)
                                  for stop in sim.stops],
                                 [('lever.turn', 0.25), ('rack.travel', 0.5)])


class StopAndJumpTest(BaseNodeTest):
    """(8) A stop and a jump crossing in one tick: the crossing is
    recorded at its fraction OF THE TICK, not of the segment."""

    def test_the_crossing_is_rescaled_to_the_tick(self):
        node = StopAndJump()
        sim = Sim(node, 1.0, record=8)
        handle = sim.move('crank', by=20.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(sim.state['first.turn'], 145.0)
        self.assertEqual(sim.state['folder.turn'] - 80.0, 30.0)
        self.assertEqual((handle.status, handle.admitted), ('blocked', 15.0))
        crossing, = sim.crossings
        self.assertEqual(crossing.primitive, 'ceil')
        self.assertEqual(crossing.t, approx(0.25, abs=1e-12))
        stop, = sim.stops
        self.assertEqual(stop.t, 0.75)


class CurvedStopTest(BaseNodeTest):
    """(6b) A stop on a chain that is NOT affine is found by search."""

    def test_the_searched_fraction_matches_the_computed_root(self):
        sim = Sim(Curved(), 1.0, record=8)
        handle = sim.move('crank', by=40.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(sim.state['dial.turn'], 20.0)
        # 40*sin(x) reaches 20 at x == 30 degrees, which is 30/40 of
        # the way along a tick that travels 40 degrees -- a root the
        # search has to find, because the law is not affine in x.
        stop, = sim.stops
        self.assertEqual(stop.t, approx(30.0 / 40.0, abs=1e-9))
        self.assertEqual(handle.admitted, approx(30.0, abs=1e-8))
        self.assertEqual(handle.status, 'blocked')

    def test_the_classification_is_read_off_the_edge(self):
        curved = Sim(Curved(), 1.0)
        edge = next(edge for edge in curved.program.edges
                    if edge.kind == 'law')
        self.assertEqual(edge.affine, (False,))
        affine = Sim(Swept(), 0.1)
        for edge in affine.program.edges:
            with self.subTest(edge=edge.description):
                self.assertTrue(all(edge.affine))


class GroupTest(BaseNodeTest):
    """(13) The group is the program's candidates, filtered by who
    actually pushes."""

    def test_the_candidate_table_names_the_reaching_inputs(self):
        swept = Sim(Swept(), 0.1)
        self.assertEqual(sources_of(swept, 'rack.travel'),
                         frozenset({'steer'}))
        self.assertEqual(sources_of(swept, 'wheel.turn'), frozenset({'motor'}))
        shared = Sim(Shared(), 1.0)
        self.assertEqual(sources_of(shared, 'c.turn'), frozenset({'a_in'}))
        self.assertEqual(sources_of(shared, 'd.turn'),
                         frozenset({'a_in', 'b_in'}))

    def test_a_check_edge_contributes_nothing_to_the_table(self):
        sim = Sim(StoppedDifferential(), 1.0)
        self.assertEqual(sources_of(sim, 'wrist'), frozenset({'wrist_in'}))
        self.assertEqual(sources_of(sim, 'tool'), frozenset({'wrist_in'}))

    def test_an_open_gate_does_not_stop_its_crank(self):
        node = OpenGate()
        sim = Sim(node, 1.0, record=8)
        push = sim.move('push', by=10.0, duration=1.0)
        crank = sim.move('crank', by=30.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(sim.state['wheel.turn'], 20.0)
        self.assertEqual((push.status, push.admitted), ('blocked', 5.0))
        self.assertEqual((crank.status, crank.admitted), ('completed', 30.0))
        self.assertEqual(sim.state['flywheel.turn'], 30.0)
        stop, = sim.stops
        self.assertEqual(stop.inputs, ('push',))

    def test_a_closed_gate_stops_both(self):
        sim = Sim(OpenGate(), 1.0, record=8, state={'gate': 1.0})
        push = sim.move('push', by=10.0, duration=1.0)
        crank = sim.move('crank', by=30.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(sim.state['wheel.turn'], 20.0)
        self.assertEqual((push.status, push.admitted), ('blocked', 1.25))
        self.assertEqual((crank.status, crank.admitted), ('blocked', 3.75))
        self.assertEqual(sim.state['flywheel.turn'], 3.75)
        stop, = sim.stops
        self.assertEqual(sorted(stop.inputs), ['crank', 'push'])


class AtomicTickTest(BaseNodeTest):
    """(A tick that fails after a stop commits nothing.)"""

    def test_a_conflict_in_the_second_segment_refuses_the_whole_tick(self):
        node = StoppedDifferential()
        sim = Sim(node, 1.0, record=8)
        wrist = sim.move('wrist_in', by=10.0, duration=1.0)
        total = sim.move('sum_in', by=30.0, duration=1.0)
        with self.assertRaises(RunConflict) as caught:
            sim.run(1.0)
        self.assertIn('left', str(caught.exception))
        self.assertEqual(sim.state['wrist'], 0.0)
        self.assertEqual(sim.state['tool'], 0.0)
        self.assertEqual(sim.tick, 0)
        self.assertEqual(reads(node, 'wrist'), 0.0)
        self.assertEqual(sim.stops, [])
        self.assertEqual(sim.crossings, [])
        self.assertEqual(wrist.status, 'refused')
        self.assertEqual(total.status, 'refused')


class SnapshotAcrossBlockTest(BaseNodeTest):
    """(9) A block replays identically from a snapshot."""

    def test_a_snapshot_before_the_block_replays_it(self):
        sim = Sim(Ratchet(), 0.1, record=8)
        before = sim.snapshot()
        first = sim.move('arbor', by=-10.0, duration=0.1)
        sim.run(0.1)
        recorded = list(sim.stops)

        sim.restore(before)
        again = sim.move('arbor', by=-10.0, duration=0.1)
        sim.run(0.1)
        self.assertEqual(sim.state['wheel.turn'], 36.0)
        self.assertEqual(again.admitted, first.admitted)
        self.assertEqual(again.status, 'blocked')
        self.assertEqual([(stop.coordinate, stop.t) for stop in sim.stops],
                         [(stop.coordinate, stop.t) for stop in recorded])

    def test_a_snapshot_after_the_block_carries_no_command(self):
        sim = Sim(Ratchet(), 0.1, record=8)
        handle = sim.move('arbor', by=-10.0, duration=0.1)
        sim.run(0.1)
        after = sim.snapshot()
        sim.move('arbor', by=20.0, duration=0.1)
        sim.run(0.1)

        sim.restore(after)
        self.assertEqual(sim.commands, ())
        self.assertEqual(sim.state['wheel.turn'], 36.0)
        self.assertEqual(handle.status, 'blocked')
        self.assertEqual(handle.admitted, -4.0)

    def test_reset_returns_to_the_rest_pose_and_clears_every_ring(self):
        sim = Sim(Ratchet(), 0.1, record=8)
        sim.move('arbor', by=-10.0, duration=0.1)
        sim.run(0.1)
        self.assertEqual(len(sim.stops), 1)
        sim.reset()
        self.assertEqual(sim.state['wheel.turn'], 40.0)
        self.assertEqual(sim.trajectory, [])
        self.assertEqual(sim.crossings, [])
        self.assertEqual(sim.stops, [])


class StopRecordTest(BaseNodeTest):
    """(11) The stop ring: bounded, explicit, and built only when asked."""

    def test_the_ring_keeps_the_most_recent_stops(self):
        sim = Sim(Ratchet(), 0.1, record=4)
        for _ in range(6):
            sim.move('arbor', by=-10.0, duration=0.1)
            sim.run(0.1)
        self.assertEqual(len(sim.stops), 4)
        for stop in sim.stops:
            with self.subTest(stop=stop):
                self.assertIsInstance(stop, Stop)
                self.assertEqual(stop.coordinate, 'wheel.turn')
                self.assertEqual(stop.bound, 'low')
                self.assertEqual(stop.value, 36.0)
                self.assertEqual(stop.inputs, ('arbor',))
                self.assertTrue(0.0 <= stop.t <= 1.0)
        self.assertEqual([stop.tick for stop in sim.stops], [3, 4, 5, 6])

    def test_nothing_is_recorded_without_the_option(self):
        sim = Sim(Ratchet(), 0.1)
        sim.move('arbor', by=-10.0, duration=0.1)
        sim.run(0.1)
        self.assertEqual(sim.state['wheel.turn'], 36.0)
        self.assertEqual(sim.stops, [])
        self.assertEqual(sim.trajectory, [])

    def test_a_refused_tick_records_no_stop(self):
        sim = Sim(StoppedDifferential(), 1.0, record=8)
        sim.move('wrist_in', by=10.0, duration=1.0)
        sim.move('sum_in', by=30.0, duration=1.0)
        with self.assertRaises(RunConflict):
            sim.run(1.0)
        self.assertEqual(sim.stops, [])

    def test_stops_belong_to_a_running_root(self):
        sim = Sim(LoopingTrain(), 0.1)
        with self.assertRaises(TypeError) as caught:
            sim.stops
        self.assertIn('Time.running()', str(caught.exception))


class ProgramIdentityTest(BaseNodeTest):
    """(3.5) A changed range changes the program identity a snapshot is
    checked against."""

    def test_the_span_table_is_named_in_the_identity(self):
        sim = Sim(Swept(), 0.1)
        self.assertIn('span rack.travel unbounded to 50.0 mm',
                      sim.program.described())
        ratchet = Sim(Ratchet(), 0.1)
        self.assertIn('span wheel.turn (36 * floor((wheel.turn / 36))) to '
                      'unbounded deg', ratchet.program.described())
        self.assertNotEqual(sim.program.identity, ratchet.program.identity)

    def test_a_snapshot_does_not_restore_into_moved_stops(self):
        """`SweptWide` is `Swept` with the rack's bound moved and nothing
        else: a snapshot of one must not restore into the other."""
        swept = Sim(Swept(), 0.1)
        wide = Sim(SweptWide(), 0.1)
        self.assertNotEqual(wide.program.identity, swept.program.identity)
        with self.assertRaises(ValueError) as caught:
            wide.restore(swept.snapshot())
        self.assertIn('snapshot', str(caught.exception))


class UntimedControlTest(BaseNodeTest):
    """(10) The untimed reading of every new declaration, unchanged: a
    range refuses a binding outside it and never clamps or stops."""

    def test_an_expression_bound_poses_untimed_at_any_angle(self):
        for value in (0.0, 36.0, 40.0, 359.0, -720.0):
            with self.subTest(value=value):
                node = RatchetBody()
                node.set_state(arbor=value)
                self.assertEqual(reads(node, 'wheel.turn'), value)

    def test_a_bound_no_value_satisfies_is_refused_by_name(self):
        for value in (0.0, 40.0, -5.0):
            with self.subTest(value=value):
                with self.assertRaises(JointRangeError) as caught:
                    ImpossibleBoundBody().set_state(arbor=value)
                message = str(caught.exception)
                self.assertIn('turn', message)
                self.assertIn(repr(value), message)
                self.assertIn(repr(value + 1), message)

    def test_an_open_bound_accepts_anything_on_its_side(self):
        node = OpenLowBody()
        node.set_state(arbor=10_000.0)
        self.assertEqual(reads(node, 'wheel.turn'), 10_000.0)
        with self.assertRaises(JointRangeError) as caught:
            OpenLowBody().set_state(arbor=-1.0)
        self.assertIn('-1', str(caught.exception))

    def test_the_running_fixtures_pose_untimed(self):
        cases = {
            SweptBody: ({'steer': 48.0, 'motor': 2.0}, 'rack.travel', 48.0),
            SharedBody: ({'a_in': 9.0, 'b_in': 1.0}, 'c.turn', 9.0),
            TwoStopsBody: ({'lever_in': 19.0, 'steer': 46.0},
                           'lever.turn', 19.0),
            OpenGateBody: ({'push': 12.0, 'crank': 5.0, 'gate': 0.0},
                           'wheel.turn', 12.0),
            StopAndJumpBody: ({'crank': 140.0}, 'first.turn', 140.0),
            CurvedBody: ({'crank': 10.0}, 'dial.turn', 6.945927106677224),
        }
        for cls, (state, coordinate, expected) in cases.items():
            with self.subTest(cls=cls.__name__):
                node = cls()
                node.set_state(**state)
                self.assertEqual(reads(node, coordinate), approx(expected))

    def test_an_untimed_binding_outside_a_numeric_bound_is_still_refused(self):
        with self.assertRaises(JointRangeError) as caught:
            SweptBody().set_state(steer=60.0, motor=0.0)
        message = str(caught.exception)
        self.assertIn('travel', message)
        self.assertIn('60', message)


class DeferredBoundTest(BaseNodeTest):
    """Design.md section 10: a bound naming a SECOND coordinate is not in
    this cycle."""

    @skip('design.md section 10: a bound over a second coordinate needs a '
          'declaration object that names what it reads, resolved against '
          'the declarer subtree at Sim construction. Deferred; a '
          'one-argument callable keeps meaning what it means here.')
    def test_a_bound_may_name_a_second_coordinate(self):
        raise AssertionError('not in this cycle')
