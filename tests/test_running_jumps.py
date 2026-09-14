# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A jump is located inside the tick and subtracted.

OpenSpec change ``integrate-jumps``, cycle 2 of the open-run campaign.
Cycle 1 refused every law whose expression contained ``floor``, ``ceil``,
``sign``, ``%`` or a comparison. Here those laws compile: a tick's path
is cut at every crossing of every jump surface it meets, each piece
carries one BRANCH per jump node -- read at the piece's midpoint -- and
the increment is the sum of the branch-substituted law's change over the
pieces. No jump ever moves a part.

The two originating laws are the Curta bench's periodic tooth window and
the Pascaline module's carry; both are here, with the fixture's own round
constants, and both are answerable to the worked numbers of the change's
``design.md`` sections 6, 7 and 11.

Nothing here changes what an untimed or looping root does, which
``UntimedControlTest`` pins directly and the untouched suites pin at
large.
"""

import gc
import math
import tracemalloc

from pytest import approx

from solid_node.motion.ports import get_coordinate
from solid_node.simulation import Sim, TooManyCrossings, UnsupportedLaw

from .base import BaseNodeTest
from .running_project.machine import (Alternating, AlternatingBody,
                                      BackwardJump, Carry, CarryLead,
                                      Clutch, Crowded, Divisor, Kinked,
                                      NonAffine, OnlyJumps, PortDriven,
                                      PortDrivenJoint, PortDrivenSmooth,
                                      LoopingTrain, Remainder, Reverser,
                                      Settled, SteppedBody, Throwing, Window,
                                      WindowBody, Wrapped)


def reads(node, qualified):
    """The value a coordinate holds, by the qualified id the run banks
    it under -- pixels' own source, since the joint places the body off
    exactly this number."""
    *path, name = qualified.split('.')
    for step in path:
        node = getattr(node, step)
    return get_coordinate(node, name)._value


def law_edge(sim, coordinate):
    """The compiled law edge driving `coordinate`."""
    for edge in sim.program.edges:
        if edge.kind != 'law':
            continue
        if coordinate in [sim.program.nodes[key].name for key in edge.gives]:
            return edge
    raise AssertionError(f'no law edge drives {coordinate}')


def stepped(cls, driver, travel, ticks, dt, coordinate, state=None):
    """`travel` taken in `ticks` ticks, and what `coordinate` read after
    each of them."""
    sim = Sim(cls(), dt, state=state)
    sim.move(driver, by=travel, duration=ticks * dt)
    trace = []
    for _ in range(ticks):
        sim.run(dt)
        trace.append(sim.state[coordinate])
    return sim, trace


class CompilePlanTest(BaseNodeTest):
    """(2.17) A jump-carrying law compiles into a JUMP PLAN: its jump
    nodes in postorder, each with the level quantity whose surfaces it
    crosses and whether that quantity is affine, and a skeleton with
    every jump node replaced."""

    def test_a_periodic_window_compiles_one_affine_floor(self):
        sim = Sim(Window(), 0.1)
        edge = law_edge(sim, 'pinion.turn')
        plan = edge.plans[0]
        self.assertEqual(len(plan.jumps), 1)
        jump = plan.jumps[0]
        self.assertEqual(jump.primitive, 'floor')
        self.assertTrue(jump.affine)
        # The level quantity is the source's qualified id over 360.
        self.assertEqual(jump.argument.evaluate({'crank': 720.0}), 2.0)
        self.assertEqual(jump.argument.evaluate({'crank': -180.0}), -0.5)
        self.assertNotIn('floor', str(jump.argument))
        # The skeleton is the law with the jump node replaced, so it
        # carries no jump at all.
        self.assertNotIn('floor', str(plan.skeleton))
        self.assertIn('crank', str(plan.skeleton))

    def test_a_nested_jump_compiles_two_nodes_in_postorder(self):
        sim = Sim(Alternating(), 0.1)
        plan = law_edge(sim, 'pinion.turn').plans[0]
        self.assertEqual(len(plan.jumps), 2)
        inner, outer = plan.jumps
        self.assertEqual([jump.primitive for jump in plan.jumps],
                         ['floor', 'floor'])
        # The inner node's level quantity is the winding, over the source.
        self.assertEqual(inner.argument.evaluate({'crank': 720.0}), 2.0)
        # The OUTER node's level quantity names no source at all: with
        # the inner branch fixed it is constant on every piece, so it
        # contributes no crossing of its own.
        self.assertNotIn('crank', str(outer.argument))
        self.assertEqual(outer.argument.evaluate({inner.placeholder: 3.0}),
                         1.5)

    def test_a_continuous_law_carries_no_plan(self):
        sim = Sim(Kinked(), 0.1)
        self.assertEqual(law_edge(sim, 'pinion.turn').plans, ())

    def test_a_remainder_is_a_jump_node_over_its_quotient(self):
        sim = Sim(Remainder(), 0.1)
        plan = law_edge(sim, 'pinion.turn').plans[0]
        self.assertEqual([jump.primitive for jump in plan.jumps], ['%'])
        self.assertTrue(plan.jumps[0].affine)
        self.assertEqual(plan.jumps[0].argument.evaluate({'crank': 720.0}),
                         2.0)

    def test_a_gate_is_a_jump_node_over_its_difference(self):
        sim = Sim(Clutch(), 1.0)
        plan = law_edge(sim, 'wheel.turn').plans[0]
        self.assertEqual([jump.primitive for jump in plan.jumps], ['>'])
        self.assertTrue(plan.jumps[0].affine)
        self.assertEqual(plan.jumps[0].argument.evaluate({'sleeve': 1.0}), 0.5)


class UntimedControlTest(BaseNodeTest):
    """(2.2) The untimed reading is untouched. A jump law posed without a
    time base is the absolute reading it always was, at every angle,
    including either side of a window boundary."""

    WINDOW = ((100.0, 4.0), (113.5, 4.0), (115.0, 13.6), (124.0, 71.2),
              (125.5, 76.0), (359.9, 76.0), (360.0, 4.0), (360.1, 4.0),
              (460.0, 4.0), (820.0, 4.0))
    STEPPED = ((0.0, 4.0), (113.5, 4.0), (115.0, 13.6), (124.0, 71.2),
               (125.5, 76.0), (359.9, 76.0), (360.0, 4.0), (360.1, 4.0),
               (480.0, 45.599999999999994), (820.0, 4.0))

    def test_the_window_body_poses_exactly_as_before(self):
        for angle, expected in self.WINDOW:
            with self.subTest(crank=angle):
                sim = Sim(WindowBody(), 0.1, state={'crank': angle})
                self.assertEqual(reads(sim.node, 'pinion.turn'), expected)

    def test_the_stepped_body_poses_exactly_as_before(self):
        for angle, expected in self.STEPPED:
            with self.subTest(crank=angle):
                sim = Sim(SteppedBody(), 0.1, state={'crank': angle})
                self.assertEqual(reads(sim.node, 'first.turn'), expected)

    def test_the_nested_body_poses_exactly_as_before(self):
        for angle, expected in ((100.0, 0.0), (460.0, 0.0), (475.0, 0.0),
                                (835.0, 9.6), (820.0, 0.0)):
            with self.subTest(crank=angle):
                sim = Sim(AlternatingBody(), 0.1, state={'crank': angle})
                self.assertEqual(reads(sim.node, 'pinion.turn'), expected)


class PeriodicWindowTest(BaseNodeTest):
    """(2.1) The pilot's illustration: the pinion stands at 4 at rest, at
    76 after one crank turn and at 148 after two -- and the tick in which
    the crank passes 360 contributes exactly zero."""

    def test_the_window_advances_once_per_revolution(self):
        sim = Sim(Window(), 1 / 240)
        self.assertEqual(sim.state['pinion.turn'], 4.0)
        self.assertEqual(reads(sim.node, 'pinion.turn'), 4.0)

        sim.move('crank', by=360, duration=1.0)
        trace = []
        for _ in range(240):
            sim.run(1 / 240)
            trace.append(sim.state['pinion.turn'])

        # design.md section 6, exactly: inside the ramp the law's slope
        # is 72 * 1.5 / 11.25 = 9.6 per tick, and outside it is zero.
        self.assertEqual(trace[8], 4.0)      # tick 9: the window opens
        self.assertEqual(trace[9], 13.6)     # tick 10: in the ramp
        self.assertEqual(trace[15], 71.2)    # tick 16: last ramping tick
        self.assertEqual(trace[16], 76.0)    # tick 17: clamp01 saturates
        self.assertEqual(trace[172], 76.0)   # tick 173: holding
        self.assertEqual(trace[173], 76.0)   # tick 174: the CROSSING tick
        self.assertEqual(sim.state['crank'], 460.0)
        self.assertEqual(sim.state['pinion.turn'],
                         approx(76.0, rel=1e-12))

        sim.move('crank', by=360, duration=1.0)
        sim.run(1.0)
        self.assertEqual(sim.state['crank'], 820.0)
        self.assertEqual(sim.state['pinion.turn'],
                         approx(148.0, rel=1e-12))
        self.assertEqual(reads(sim.node, 'pinion.turn'),
                         approx(148.0, rel=1e-12))

    def test_the_crossing_tick_contributes_exactly_zero(self):
        sim = Sim(Window(), 1 / 240, record=8)
        sim.move('crank', by=360, duration=1.0)
        sim.run(173 / 240)
        before = sim.state['pinion.turn']
        sim.run(1 / 240)
        self.assertEqual(sim.state['pinion.turn'] - before, 0.0)
        self.assertEqual(sim.state['crank'], 361.0)
        crossing, = sim.crossings
        self.assertEqual(crossing.primitive, 'floor')
        self.assertEqual(crossing.level, 1.0)
        self.assertEqual(crossing.t,
                         approx(1 / 3, rel=1e-12))

    def test_a_tick_that_passes_three_windows_adds_three_throws(self):
        sim = Sim(Window(), 1 / 240, record=8)
        sim.move('crank', by=1080, duration=0)
        self.assertEqual(sim.state['pinion.turn'],
                         approx(220.0, rel=1e-12))
        self.assertEqual(sim.state['crank'], 1180.0)
        self.assertEqual([crossing.level for crossing in sim.crossings],
                         [1.0, 2.0, 3.0])
        for crossing, expected in zip(sim.crossings,
                                      (260 / 1080, 620 / 1080, 980 / 1080)):
            self.assertEqual(crossing.t,
                             approx(expected, rel=1e-12))

    def test_the_answer_does_not_depend_on_the_display_cadence(self):
        answers = {}
        for ticks in (1, 12, 40, 240):
            sim = Sim(Window(), 1 / 240)
            sim.move('crank', by=360, duration=ticks / 240)
            sim.run(ticks / 240)
            answers[ticks] = sim.state['pinion.turn']
        for ticks, answer in answers.items():
            with self.subTest(ticks=ticks):
                self.assertEqual(answer,
                                 approx(76.0, rel=1e-12))

        one = Sim(Window(), 1 / 240)
        one.move('crank', by=720, duration=2.0)
        one.run(2.0)
        two = Sim(Window(), 1 / 240)
        for _ in range(2):
            two.move('crank', by=360, duration=1.0)
            two.run(1.0)
        self.assertEqual(one.state['pinion.turn'],
                         approx(two.state['pinion.turn'], rel=1e-12))
        self.assertEqual(one.state['pinion.turn'],
                         approx(148.0, rel=1e-12))


class ClutchTest(BaseNodeTest):
    """(2.3) A gate holds open, drives closed, and re-engages without a
    jump: the travel after engagement only."""

    def _moved(self, sim, **moves):
        before = sim.state['wheel.turn']
        for name, travel in moves.items():
            sim.move(name, by=travel, duration=1.0)
        sim.run(1.0)
        return sim.state['wheel.turn'] - before

    def test_an_open_gate_holds_the_wheel(self):
        sim = Sim(Clutch(), 1.0)
        self.assertEqual(self._moved(sim, shaft=4.0), 0.0)

    def test_a_closed_gate_drives_the_pair(self):
        sim = Sim(Clutch(), 1.0, state={'sleeve': 1.0})
        self.assertEqual(self._moved(sim, shaft=4.0), -8.0)

    def test_a_gate_closing_inside_the_tick_takes_the_travel_after_it(self):
        sim = Sim(Clutch(), 1.0)
        # The absolute reading would apply -2 * shaft = -24 at the
        # instant of engagement. That jump never moves the wheel.
        self.assertEqual(self._moved(sim, shaft=4.0, sleeve=1.0), -4.0)


class NestedJumpTest(BaseNodeTest):
    """(2.5) A jump node whose argument contains another: the engagement
    happens on alternate revolutions."""

    def test_the_law_engages_on_alternate_revolutions(self):
        sim = Sim(Alternating(), 1 / 240, record=16)
        reached = []
        for _ in range(4):
            sim.move('crank', by=360, duration=1.0)
            sim.run(1.0)
            reached.append(sim.state['pinion.turn'])
        for value, expected in zip(reached, (72.0, 72.0, 144.0, 144.0)):
            self.assertEqual(value,
                             approx(expected, rel=1e-12))

    def test_only_the_inner_node_ever_crosses(self):
        sim = Sim(Alternating(), 1 / 240, record=16)
        for _ in range(4):
            sim.move('crank', by=360, duration=1.0)
            sim.run(1.0)
        # Four revolutions from 100 pass 360, 720, 1080 and 1440: the
        # inner floor crosses four surfaces and the outer none, because
        # its level quantity is constant between the inner's crossings.
        self.assertEqual([crossing.level for crossing in sim.crossings],
                         [1.0, 2.0, 3.0, 4.0])


class PrimitiveTest(BaseNodeTest):
    """(2.6, 2.7, 2.8) One case per primitive, each against a reading
    that does not need the primitive at all."""

    def test_a_remainder_window_and_a_floor_window_agree(self):
        _floor_sim, by_floor = stepped(Window, 'crank', 360, 240, 1 / 240,
                                       'pinion.turn')
        _mod_sim, by_mod = stepped(Remainder, 'crank', 360, 240, 1 / 240,
                                   'pinion.turn')
        for tick, (left, right) in enumerate(zip(by_floor, by_mod), start=1):
            with self.subTest(tick=tick):
                self.assertEqual(left, right)
        self.assertEqual(by_mod[-1],
                         approx(76.0, rel=1e-12))

    def test_a_sign_that_does_not_jump_reads_as_its_continuous_twin(self):
        for start in (40.0, 40.5):
            _a, by_sign = stepped(Reverser, 'crank', 20, 20, 1.0,
                                  'pinion.turn', state={'crank': start})
            _b, by_abs = stepped(Kinked, 'crank', 20, 20, 1.0,
                                 'pinion.turn', state={'crank': start})
            for tick, (left, right) in enumerate(zip(by_sign, by_abs), 1):
                with self.subTest(start=start, tick=tick):
                    self.assertEqual(left, right)

    def test_a_sign_that_jumps_contributes_its_segments_and_not_its_jump(self):
        sim = Sim(Throwing(), 1.0)
        before = sim.state['pinion.turn']
        sim.move('crank', by=20, duration=1.0)
        sim.run(1.0)
        # design.md section 6: the two segments give -50 and +50; the
        # jump of 500 at the crossing moves nothing.
        self.assertEqual(sim.state['pinion.turn'] - before, 0.0)

        halves = Sim(Throwing(), 1.0)
        start = halves.state['pinion.turn']
        halves.move('crank', by=10, duration=1.0)
        halves.run(1.0)
        first = halves.state['pinion.turn']
        self.assertEqual(first - start, -50.0)
        halves.move('crank', by=10, duration=1.0)
        halves.run(1.0)
        self.assertEqual(halves.state['pinion.turn'] - first, 50.0)

    def test_a_wrapped_law_integrates_to_the_unwrapped_travel(self):
        sim = Sim(Wrapped(), 1.0, record=8)
        before = sim.state['pinion.turn']
        self.assertEqual(before, 200.0)
        sim.move('crank', by=500, duration=1.0)
        sim.run(1.0)
        self.assertEqual(sim.state['pinion.turn'] - before, 1000.0)
        self.assertEqual([crossing.primitive for crossing in sim.crossings],
                         ['ceil', 'ceil'])
        for crossing, expected in zip(sim.crossings, (0.16, 0.88)):
            self.assertEqual(crossing.t,
                             approx(expected, rel=1e-12))


class OnlyJumpsRefusalTest(BaseNodeTest):
    """(2.9) A law that can move its coordinate only by jumping is
    refused as arithmetic, and a jump beside a sloped term is not."""

    def test_a_step_counter_is_refused(self):
        with self.assertRaises(UnsupportedLaw) as caught:
            Sim(OnlyJumps(), 0.1)
        message = str(caught.exception)
        self.assertIn('turns', message)
        self.assertIn('dial.turn', message)
        self.assertIn('OnlyJumps', message)
        self.assertIn('only', message)
        self.assertIn('jump', message)
        self.assertIn('arithmetic', message)

    def test_a_jump_beside_a_sloped_term_compiles(self):
        sim = Sim(Settled(), 0.1)
        before = sim.state['dial.turn']
        sim.move('turns', by=2.0, duration=0.1)
        sim.run(0.1)
        self.assertEqual(sim.state['dial.turn'], before)
        sim.move('enabled', by=1.0, duration=0.1)
        sim.run(0.1)
        self.assertEqual(sim.state['dial.turn'] - before, 9.0)

    def test_a_periodic_window_is_not_a_law_that_only_jumps(self):
        sim = Sim(Window(), 0.1)
        self.assertEqual(sim.state['pinion.turn'], 4.0)


class HistoryRefusalTest(BaseNodeTest):
    """(2.9a) A subtracted jump implies a history, and only a coordinate
    the run owns keeps one."""

    def test_a_jumping_law_into_a_plain_port_is_refused(self):
        with self.assertRaises(UnsupportedLaw) as caught:
            Sim(PortDriven(), 0.1)
        message = str(caught.exception)
        self.assertIn('register', message)
        self.assertIn('crank', message)
        self.assertIn('PortDriven', message)
        self.assertIn('joint', message)
        self.assertIn('history', message)

    def test_the_same_relation_into_the_joint_compiles(self):
        sim = Sim(PortDrivenJoint(), 0.1)
        self.assertEqual(sim.state['first.turn'], 4.0)

    def test_a_continuous_law_into_the_same_port_still_compiles(self):
        sim = Sim(PortDrivenSmooth(), 0.1)
        self.assertEqual(sim.state['first.turn'], 4.0)


class CrossingRecordTest(BaseNodeTest):
    """(2.10) The crossing record is bounded, optional, and says what
    crossed."""

    def test_the_ring_keeps_the_most_recent_crossings(self):
        # 1.5 degrees a tick, so every boundary falls strictly INSIDE a
        # tick rather than on one of its ends.
        sim = Sim(Window(), 1 / 240, record=4)
        sim.move('crank', by=2160, duration=6.0)
        sim.run(6.0)
        self.assertEqual(len(sim.crossings), 4)
        self.assertEqual([crossing.level for crossing in sim.crossings],
                         [3.0, 4.0, 5.0, 6.0])
        for crossing in sim.crossings:
            self.assertEqual(crossing.coordinate, 'pinion.turn')
            self.assertEqual(crossing.primitive, 'floor')
            self.assertIn('crank', crossing.relation)
            self.assertIn('pinion.turn', crossing.relation)
            self.assertTrue(0.0 <= crossing.t <= 1.0)
            self.assertGreater(crossing.tick, 0)

    def test_nothing_is_recorded_by_default(self):
        sim = Sim(Window(), 1 / 240)
        sim.rate('crank', 360.0)
        sim.run(10.0)
        gc.collect()
        tracemalloc.start()
        sim.run(10.0)
        _current, first = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        sim.run(20.0)
        _current, later = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.assertEqual(sim.crossings, [])
        self.assertLess(later - first, 64 * 1024)

    def test_reset_clears_the_crossing_ring(self):
        sim = Sim(Window(), 1 / 240, record=8)
        sim.move('crank', by=720, duration=2.0)
        sim.run(2.0)
        self.assertEqual(len(sim.crossings), 2)
        sim.reset()
        self.assertEqual(sim.crossings, [])

    def test_a_refused_tick_records_no_crossing(self):
        sim = Sim(Crowded(), 1.0, record=8)
        sim.move('a', by=2000, duration=1.0)
        with self.assertRaises(TooManyCrossings):
            sim.run(1.0)
        self.assertEqual(sim.crossings, [])

    def test_crossings_belong_to_a_running_root(self):
        sim = Sim(LoopingTrain(), 0.1)
        with self.assertRaises(TypeError) as caught:
            sim.crossings
        self.assertIn('Time.running()', str(caught.exception))


class LargeOriginTest(BaseNodeTest):
    """(2.12) Locating a crossing adds no error of its own; what
    degrades is the bank's own resolution."""

    WINDINGS = (0.0, 1e3, 1e6, 1e9, 1e12, 1e13)

    def _two_turns(self, winding):
        sim = Sim(Window(), 1 / 240, state={'crank': winding * 360.0 + 100.0})
        sim.move('crank', by=720, duration=2.0)
        trace = []
        for _ in range(480):
            sim.run(1 / 240)
            trace.append(sim.state['pinion.turn'])
        return trace

    def test_the_answer_is_bit_identical_across_six_orders_of_winding(self):
        reference = self._two_turns(0.0)
        self.assertEqual(reference[-1],
                         approx(148.0, rel=1e-12))
        for winding in self.WINDINGS[1:]:
            with self.subTest(winding=winding):
                trace = self._two_turns(winding)
                deviation = max(math.fabs(x - y)
                                for x, y in zip(reference, trace))
                self.assertEqual(deviation, 0.0)
                self.assertEqual(trace[-1], reference[-1])

    def test_the_boundary_is_the_banks_resolution_and_not_the_search(self):
        # At 1e13 turns the tick's own travel still clears the bank's
        # ulp, and the answer is exact to the last bit (above).
        self.assertLess(math.ulp(1e13 * 360.0), 1.5)
        # At 1e14 it does not: a 1.5 degree step is below half an ulp of
        # the crank's own magnitude, so a crank asked to advance by 1.5
        # degrees a tick does not move at all, and the pinion stands
        # where the rest pose put it.
        self.assertGreater(math.ulp(1e14 * 360.0), 1.5)
        sim = Sim(Window(), 1 / 240, state={'crank': 1e14 * 360.0 + 100.0})
        origin = sim.state['crank']
        for _ in range(480):
            sim.move('crank', by=1.5, duration=1 / 240)
            sim.run(1 / 240)
        self.assertEqual(sim.state['crank'], origin)
        self.assertEqual(sim.state['pinion.turn'], 4.0)


class CarryTest(BaseNodeTest):
    """(2.13) The Pascaline-shaped carry: one driver and one joint
    coordinate as the two sources of a column's law."""

    def test_a_column_hands_on_one_throw_per_revolution(self):
        sim = Sim(Carry(), 1.0)
        rest = sim.state['tens.turn']
        self.assertEqual(rest, 0.0)
        sim.move('column', by=720, duration=72.0)
        sim.run(72.0)
        self.assertEqual(sim.state['column'], 820.0)
        self.assertEqual(sim.state['tens.turn'] - rest,
                         approx(120.0, rel=1e-12))
        self.assertEqual(sim.state['tens_entry'], 0.0)

        sim.move('tens_entry', by=1.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(sim.state['tens.turn'] - rest,
                         approx(156.0, rel=1e-12))

    def test_a_lead_makes_the_law_jump_and_the_jump_is_subtracted(self):
        # The fixture's lead of 0.5 makes handed_on discontinuous at the
        # window boundary by first_rise * lead / first_width =
        # 20 * 0.5 / 10 = 1.0, so each throw integrates to 59 rather than
        # 60. The committed module's own constants do the same with
        # 4.10 * 0.10 / 3 = 0.136666..., which takes its CARRY_THROW of
        # 65.54 to 65.403333... -- a finding for the module's migration,
        # not a framework question.
        sim = Sim(CarryLead(), 1.0)
        rest = sim.state['tens.turn']
        self.assertEqual(rest, 1.0)
        sim.move('column', by=720, duration=72.0)
        sim.run(72.0)
        self.assertEqual(sim.state['tens.turn'] - rest,
                         approx(118.0, rel=1e-12))


class SearchPathTest(BaseNodeTest):
    """(2.18) A level quantity that is not affine in the sources is
    bracketed by subdivision and bisected."""

    def test_a_product_of_two_sources_is_located_by_search(self):
        sim = Sim(NonAffine(), 1.0)
        plan = law_edge(sim, 'dial.turn').plans[0]
        self.assertEqual(plan.jumps[0].primitive, 'floor')
        self.assertFalse(plan.jumps[0].affine)
        before = sim.state['dial.turn']
        self.assertEqual(before, 0.0)
        sim.move('a', by=20.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(sim.state['dial.turn'] - before, 10.0)


class PerTickRefusalTest(BaseNodeTest):
    """(2.19) Two refusals belong to the tick rather than to
    construction, and both commit nothing."""

    def test_too_many_crossings_refuses_the_tick(self):
        sim = Sim(Crowded(), 1.0)
        handle = sim.move('a', by=2000.0, duration=1.0)
        with self.assertRaises(TooManyCrossings) as caught:
            sim.run(1.0)
        message = str(caught.exception)
        self.assertIn('dial.turn', message)
        self.assertIn('floor', message)
        self.assertIn('1000', message)
        self.assertIn('1999', message)
        self.assertEqual(sim.state['a'], 0.0)
        self.assertEqual(sim.state['dial.turn'], 0.0)
        self.assertEqual(sim.tick, 0)
        self.assertEqual(reads(sim.node, 'dial.turn'), 0.0)
        self.assertEqual(handle.status, 'refused')

    def test_a_zero_divisor_refuses_the_tick(self):
        sim = Sim(Divisor(), 1.0)
        before = sim.state['dial.turn']
        handle = sim.move('b', by=4.0, duration=1.0)
        with self.assertRaises(UnsupportedLaw) as caught:
            sim.run(1.0)
        message = str(caught.exception)
        self.assertIn('dial.turn', message)
        self.assertIn('divisor', message)
        self.assertEqual(sim.state['b'], -2.0)
        self.assertEqual(sim.state['dial.turn'], before)
        self.assertEqual(sim.tick, 0)
        self.assertEqual(handle.status, 'refused')


class SnapshotAcrossCrossingTest(BaseNodeTest):
    """(2.20) A tick is a pure function of the bank and the commands,
    crossings included."""

    def test_a_snapshot_restored_over_a_crossing_replays_exactly(self):
        sim = Sim(Window(), 1 / 240, record=8)
        sim.move('crank', by=360, duration=1.0)
        sim.run(173 / 240)
        taken = sim.snapshot()

        sim.run(2 / 240)
        bank = dict(sim.state)
        crossings = list(sim.crossings)
        self.assertEqual(len(crossings), 1)

        sim.restore(taken)
        self.assertEqual(sim.crossings, [])
        sim.run(2 / 240)
        self.assertEqual(dict(sim.state), bank)
        self.assertEqual(list(sim.crossings), crossings)


class BackwardJumpTest(BaseNodeTest):
    """(2.21) A jump in the face the rest render solved BACKWARD
    integrates through the same machinery, over the driven end's id."""

    def test_an_inverse_that_jumps_integrates_over_the_driven_id(self):
        sim = Sim(BackwardJump(), 1.0, record=8)
        self.assertEqual(sim.state['first.turn'], 200.0)
        self.assertEqual(sim.state['second.turn'], -160.0)
        plan = law_edge(sim, 'second.turn').plans[0]
        self.assertEqual(plan.jumps[0].primitive, 'ceil')
        level = plan.jumps[0].argument
        self.assertEqual(level.evaluate({'first.turn': 540.0}), 1.0)
        sim.move('crank', by=200.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(sim.state['first.turn'], 600.0)
        self.assertEqual(sim.state['second.turn'] - (-160.0), 400.0)
        crossing, = sim.crossings
        self.assertEqual(crossing.coordinate, 'second.turn')
        self.assertEqual(crossing.t,
                         approx(0.85, rel=1e-12))
