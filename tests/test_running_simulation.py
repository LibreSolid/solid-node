# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The running simulation: the run owns the coordinates.

OpenSpec change ``run-owns-the-coordinates``, cycle 1 of the open-run
campaign. A root declaring ``time = Time.running()`` gets a simulation
that owns a BANK of every driver and every joint coordinate of the
linked tree, initialized from the untimed rest pose, bound by the run on
every tick, and advanced by INCREMENTS: over one tick a continuous law
contributes exactly ``f(end) - f(start)`` to its driven coordinate, from
where it stood.

Originating projects: the Curta ``InputMesh`` bench, whose transmission
pinion could only say where it IS and never where it WAS, and the
Pascaline module, whose dials must accumulate without register re-entry.

Everything here is new behaviour; nothing in it changes what an untimed
or looping root does, which the untouched suites pin.
"""

import gc
import tracemalloc
from unittest import TestCase

from solid_node.core.serializer import instructions_table
from solid_node.motion.couplings import DoublyBound
from solid_node.motion.ports import get_coordinate
from solid_node.simulation import Instruction, RunConflict, Sim, UnsupportedLaw

from .base import BaseNodeTest
from .running_project.machine import (Backwards, Differential, Follower,
                                      Guarded, HandBound, LoopingTrain,
                                      Opaque, Ranged, RangedExact, Sixfree,
                                      Stdlib, Stepped, SteppedBody, Stepper,
                                      Train, TrainBody, Unbound)


def reads(node, name):
    """The value a coordinate of `node` holds, by the name the port
    enumeration reports it under."""
    return get_coordinate(node, name)._value


def turned(node):
    """The angle the joint placed `node` at, off its own operations --
    pixels for a kinematic model: the body moved, not only the number."""
    for operation in node.operations:
        if getattr(operation, '_motion', False) and hasattr(operation, 'angle'):
            return operation.angle
    return None


def slid(node):
    for operation in node.operations:
        if (getattr(operation, '_motion', False)
                and hasattr(operation, 'translation')):
            return operation.translation
    return None


class BankTest(BaseNodeTest):
    """(2) The bank is every driver and every joint coordinate of the
    linked tree, by qualified id, and its initial values are the untimed
    rest pose."""

    def test_the_bank_lists_drivers_and_joint_coordinates_only(self):
        sim = Sim(Train(), 0.1)
        self.assertEqual(sorted(sim.state), [
            'crank', 'first.turn', 'lever', 'second.turn', 'slide.travel',
            'spindle'])

    def test_the_initial_bank_is_the_untimed_rest_pose(self):
        sim = Sim(Train(), 0.1, state={'crank': 10.0})
        self.assertEqual(sim.state, {
            'crank': 10.0,
            'lever': 100.0,
            'first.turn': 20.0,
            'second.turn': -30.0,
            'slide.travel': 4.0,
            'spindle': 10.0,
        })
        self.assertEqual(sim.tick, 0)
        self.assertEqual(sim.time, 0.0)
        self.assertTrue(sim.running)

    def test_a_plain_port_is_computed_by_the_enumeration_not_banked(self):
        node = Train()
        sim = Sim(node, 0.1, state={'crank': 10.0})
        self.assertNotIn('wheel.turn', sim.state)
        self.assertEqual(reads(node.wheel, 'turn'), 10.0)

    def test_a_joint_on_a_leaf_is_owned_like_any_other(self):
        node = Train()
        Sim(node, 0.1, state={'crank': 10.0})
        self.assertEqual(reads(node.first, 'turn'), 20.0)
        self.assertEqual(turned(node.first), 20.0)

    def test_state_refuses_a_coordinate_id(self):
        with self.assertRaises(ValueError) as caught:
            Sim(Train(), 0.1, state={'first.turn': 12.0})
        self.assertIn('first.turn', str(caught.exception))

    def test_the_running_surface_is_refused_under_a_looping_root(self):
        sim = Sim(LoopingTrain(), 0.1)
        self.assertFalse(sim.running)
        for call in (lambda: sim.move('crank', by=1.0, duration=1.0),
                     lambda: sim.rate('crank', 1.0),
                     lambda: sim.snapshot(),
                     lambda: sim.restore(None),
                     lambda: sim.reset(),
                     lambda: sim.commands,
                     lambda: sim.program,
                     lambda: sim.initial):
            with self.subTest(call=call):
                with self.assertRaises(TypeError) as caught:
                    call()
                self.assertIn('Time.running()', str(caught.exception))


class IntegrationTest(BaseNodeTest):
    """(3) Moves accumulate; an affine chain follows; a law with a kink
    integrates exactly."""

    def test_two_moves_accumulate_through_the_train(self):
        node = Train()
        sim = Sim(node, 0.1)
        first = sim.move('crank', by=10.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(first.status, 'completed')
        self.assertEqual(first.admitted, 10.0)
        second = sim.move('crank', by=10.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(second.status, 'completed')
        self.assertEqual(second.admitted, 10.0)
        self.assertEqual(sim.state['crank'], 20.0)
        self.assertEqual(sim.state['first.turn'], 40.0)
        self.assertEqual(sim.state['second.turn'], -60.0)
        self.assertEqual(turned(node.first), 40.0)
        self.assertEqual(turned(node.second), -60.0)

    def test_a_law_with_a_kink_integrates_exactly(self):
        sim = Sim(Train(), 0.1)
        sim.move('lever', by=40.0, duration=0.8)
        sim.run(0.3)
        self.assertEqual(sim.state['slide.travel'], 13.6)
        sim.run(0.1)
        # The same arithmetic the law performs: 4 + 72*clamp01(6.5/11.25).
        self.assertEqual(sim.state['slide.travel'], 45.599999999999994)
        sim.run(0.1)
        self.assertEqual(sim.state['slide.travel'], 76.0)
        sim.run(0.3)
        self.assertEqual(sim.state['slide.travel'], 76.0)
        self.assertEqual(sim.state['lever'], 140.0)

    def test_backward_propagation_through_an_invertible_law(self):
        sim = Sim(Backwards(), 0.1)
        sim.move('crank', by=10.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(sim.state['first.turn'], 20.0)
        self.assertEqual(sim.state['second.turn'], 5.0)

    def test_an_undriven_joint_holds_on_every_tick(self):
        sim = Sim(Train(), 0.1)
        seen = []
        sim.every(0.1, lambda: seen.append(
            (sim.state['lever'], sim.state['slide.travel'])))
        sim.move('crank', by=10.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(len(seen), 10)
        self.assertEqual(set(seen), {(100.0, 4.0)})


class ConflictTest(BaseNodeTest):
    """(6) Two inputs prescribing one rigid group."""

    def test_a_disagreeing_tick_is_refused_and_commits_nothing(self):
        node = Differential()
        sim = Sim(node, 0.1)
        before = dict(sim.state)
        handle = sim.move('wrist_in', by=10.0, duration=1.0)
        with self.assertRaises(RunConflict) as caught:
            sim.run(0.1)
        message = str(caught.exception)
        self.assertIn('left', message)
        self.assertIn('wrist', message)
        self.assertIn('tool', message)
        self.assertIn('sum_in', message)
        self.assertEqual(sim.state, before)
        self.assertEqual(sim.tick, 0)
        self.assertEqual(reads(node, 'wrist'), before['wrist'])
        self.assertEqual(handle.status, 'refused')
        self.assertEqual(handle.admitted, 0.0)
        self.assertEqual(sim.commands, ())

    def test_the_refused_increments_are_named(self):
        sim = Sim(Differential(), 0.1)
        sim.move('wrist_in', by=10.0, duration=0.1)
        with self.assertRaises(RunConflict) as caught:
            sim.run(0.1)
        message = str(caught.exception)
        self.assertIn('30', message)
        self.assertIn('0', message)

    def test_the_same_group_moved_consistently_is_admitted(self):
        node = Differential()
        sim = Sim(node, 0.1)
        sim.move('wrist_in', by=10.0, duration=1.0)
        sim.move('sum_in', by=30.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(sim.state['wrist'], 10.0)
        self.assertEqual(sim.state['tool'], 10.0)
        self.assertEqual(reads(node, 'left'), 30.0)


class AuthorBindingTest(BaseNodeTest):
    """(7) A law stated imperatively is refused; a guarded rest default
    keeps working."""

    def test_an_unconditional_author_binding_is_refused(self):
        with self.assertRaises(DoublyBound) as caught:
            Sim(HandBound(), 0.1)
        message = str(caught.exception)
        self.assertIn('HandBound', message)
        self.assertIn('first.turn', message)
        self.assertIn('running simulation', message)

    def test_a_guarded_rest_default_keeps_working(self):
        node = Guarded()
        sim = Sim(node, 0.1)
        self.assertEqual(sim.state['slide.travel'], 4.0)
        sim.move('crank', by=10.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(sim.state['slide.travel'], 4.0)
        self.assertEqual(reads(node.slide, 'travel'), 4.0)


class SnapshotTest(BaseNodeTest):
    """(8), (9) Snapshot, restore and reset act on the run's bank."""

    def test_a_snapshot_restores_mid_run(self):
        node = Train()
        sim = Sim(node, 0.1)
        sim.move('crank', by=10.0, duration=1.0)
        sim.run(0.5)
        saved = sim.snapshot()
        self.assertEqual(saved, sim.snapshot())
        sim.run(0.5)
        completed = dict(sim.state)
        sim.restore(saved)
        self.assertEqual(sim.state, dict(saved.bank))
        self.assertEqual(sim.tick, saved.tick)
        self.assertEqual(reads(node.first, 'turn'), sim.state['first.turn'])
        sim.run(0.5)
        self.assertEqual(sim.state, completed)

    def test_a_mismatched_program_is_refused_before_anything_changes(self):
        sim = Sim(Train(), 0.1)
        other = Sim(Backwards(), 0.1)
        alien = other.snapshot()
        before = dict(sim.state)
        with self.assertRaises(ValueError) as caught:
            sim.restore(alien)
        message = str(caught.exception)
        self.assertIn(sim.program.identity, message)
        self.assertIn(alien.program, message)
        self.assertEqual(sim.state, before)
        self.assertEqual(sim.tick, 0)

    def test_a_mismatched_dt_is_refused(self):
        fine = Sim(Train(), 0.05)
        coarse = Sim(Train(), 0.1)
        with self.assertRaises(ValueError) as caught:
            coarse.restore(fine.snapshot())
        message = str(caught.exception)
        self.assertIn('0.05', message)
        self.assertIn('0.1', message)

    def test_reset_returns_to_the_initial_snapshot(self):
        sim = Sim(Train(), 0.1, record=8)
        sim.move('crank', by=10.0, duration=1.0)
        sim.run(1.0)
        sim.reset()
        self.assertEqual(sim.snapshot(), sim.initial)
        self.assertEqual(sim.tick, 0)
        self.assertEqual(sim.state['crank'], 0.0)
        self.assertEqual(sim.state['first.turn'], 0.0)
        self.assertEqual(sim.commands, ())
        self.assertEqual(sim.trajectory, [])

    def test_a_handle_issued_before_a_restore_is_cancelled(self):
        sim = Sim(Train(), 0.1)
        saved = sim.snapshot()
        handle = sim.move('crank', by=10.0, duration=1.0)
        sim.run(0.5)
        sim.restore(saved)
        self.assertEqual(handle.status, 'cancelled')
        self.assertEqual(handle.admitted, 5.0)


class InstructionTest(BaseNodeTest):
    """(10) Instructions under a running root are moves; `by=` is
    relative everywhere."""

    def test_a_relative_instruction_accumulates(self):
        sim = Sim(Train(), 0.1)
        sim.trigger('Advance')
        sim.run(0.5)
        self.assertEqual(sim.state['crank'], 10.0)
        sim.trigger('Advance')
        sim.run(0.5)
        self.assertEqual(sim.state['crank'], 20.0)

    def test_an_absolute_instruction_moves_to_its_target(self):
        sim = Sim(Train(), 0.1)
        sim.trigger('Advance')
        sim.run(0.5)
        sim.trigger('Advance')
        sim.run(0.5)
        sim.trigger('Park')
        sim.run(0.5)
        self.assertEqual(sim.state['crank'], 40.0)

    def test_a_relative_instruction_ramps_under_a_looping_root(self):
        sim = Sim(LoopingTrain(), 0.1)
        sim.trigger('Advance')
        sim.run(0.5)
        self.assertEqual(sim.state['crank'], 10.0)
        sim.trigger('Advance')
        sim.run(0.5)
        self.assertEqual(sim.state['crank'], 20.0)

    def test_the_declaration_reads_back_one_of_the_two(self):
        relative = Instruction(by={'crank': 10.0}, duration=0.5)
        absolute = Instruction({'crank': 40.0}, duration=0.5)
        self.assertEqual(relative.by, {'crank': 10.0})
        self.assertIsNone(relative.targets)
        self.assertEqual(absolute.targets, {'crank': 40.0})
        self.assertIsNone(absolute.by)

    def test_exactly_one_of_targets_and_by(self):
        with self.assertRaises(TypeError):
            Instruction({'crank': 0.0}, duration=1.0, by={'crank': 1.0})
        with self.assertRaises(TypeError):
            Instruction(duration=1.0)

    def test_an_instruction_whose_input_is_owned_starts_nothing(self):
        sim = Sim(Train(), 0.1)
        rate = sim.rate('crank', 90.0)
        with self.assertRaises(ValueError) as caught:
            sim.trigger('Wind')
        self.assertIn('crank', str(caught.exception))
        # 'Wind' names `lever` too, and nothing was started on it.
        self.assertEqual(sim.commands, (rate,))


class CommandTest(BaseNodeTest):
    """(11) One owner per input, an outcome handle, retirement."""

    def test_a_rate_and_a_move_on_one_input_conflict(self):
        sim = Sim(Train(), 0.1)
        rate = sim.rate('crank', 90.0)
        with self.assertRaises(ValueError) as caught:
            sim.move('crank', by=10.0, duration=1.0)
        message = str(caught.exception)
        self.assertIn('crank', message)
        self.assertIn('rate', message)
        self.assertEqual(rate.status, 'active')

    def test_two_moves_on_one_input_conflict(self):
        sim = Sim(Train(), 0.1)
        sim.move('crank', by=10.0, duration=1.0)
        with self.assertRaises(ValueError) as caught:
            sim.move('crank', by=10.0, duration=1.0)
        self.assertIn('crank', str(caught.exception))

    def test_a_rate_accumulates_until_released(self):
        sim = Sim(Train(), 0.1)
        handle = sim.rate('crank', 90.0)
        sim.run(2.0)
        sim.rate('crank', 0)
        self.assertEqual(sim.state['crank'], 180.0)
        self.assertEqual(sim.state['first.turn'], 360.0)
        self.assertEqual(handle.status, 'completed')
        self.assertEqual(handle.admitted, 180.0)
        self.assertEqual(sim.commands, ())

    def test_releasing_an_unowned_input_is_a_no_op(self):
        sim = Sim(Train(), 0.1)
        self.assertIsNone(sim.rate('crank', 0))
        self.assertEqual(sim.commands, ())

    def test_a_reverse_request_runs(self):
        """Cycle 3: a reverse move meets a stop exactly as a forward one
        does, and a crank that meets none runs backwards through the same
        laws."""
        for kind, call, landed in (
                ('by', lambda sim: sim.move('crank', by=-10.0, duration=1.0),
                 10.0),
                ('to', lambda sim: sim.move('crank', to=5.0, duration=1.0),
                 5.0),
                ('rate', lambda sim: sim.rate('crank', -90.0), -70.0)):
            with self.subTest(kind=kind):
                node = Train()
                sim = Sim(node, 0.1)
                sim.move('crank', by=20.0, duration=1.0)
                sim.run(1.0)
                handle = call(sim)
                sim.run(1.0)
                if kind == 'rate':
                    sim.rate('crank', 0)
                self.assertEqual(sim.state['crank'], landed)
                self.assertEqual(sim.state['first.turn'], landed * 2)
                self.assertEqual(sim.state['second.turn'], landed * -3.0)
                self.assertEqual(reads(node.first, 'turn'), landed * 2)
                self.assertEqual(handle.status, 'completed')
                self.assertEqual(handle.admitted, landed - 20.0)

    def test_a_reverse_rate_on_an_integer_input_truncates_toward_zero(self):
        """A negative rate rounds the way a positive one does: `trunc`,
        not `floor`, so the state neither leads nor lags by a whole
        native unit depending on direction."""
        for rate, expected in ((-1.5, [-1, -3, -4, -6]),
                               (1.5, [1, 3, 4, 6])):
            with self.subTest(rate=rate):
                sim = Sim(Stepper(), 1.0)
                sim.rate('step', rate)
                trace = []
                for _ in range(4):
                    sim.run(1.0)
                    trace.append(sim.state['step'])
                self.assertEqual(trace, expected)
                self.assertEqual(sim.state['carriage.travel'], expected[-1])

    def test_only_a_declared_input_can_be_moved(self):
        sim = Sim(Train(), 0.1)
        with self.assertRaises(ValueError) as caught:
            sim.move('first.turn', by=10.0, duration=1.0)
        message = str(caught.exception)
        self.assertIn('first.turn', message)
        self.assertIn('crank', message)
        self.assertIn('lever', message)

    def test_completed_commands_are_retired(self):
        sim = Sim(Train(), 0.1)
        handles = []
        for _ in range(100):
            handles.append(sim.move('crank', by=1.0, duration=0.1))
            sim.run(0.1)
            self.assertLessEqual(len(sim.commands), 1)
        self.assertEqual(sim.state['crank'], 100.0)
        self.assertTrue(all(handle.status == 'completed'
                            for handle in handles))

    def test_a_zero_duration_move_integrates_now(self):
        node = Train()
        sim = Sim(node, 0.1)
        sim.run(2.0)
        self.assertEqual(sim.tick, 20)
        handle = sim.move('crank', by=10.0, duration=0)
        self.assertEqual(sim.tick, 20)
        self.assertEqual(sim.state['crank'], 10.0)
        self.assertEqual(sim.state['first.turn'], 20.0)
        self.assertEqual(reads(node.first, 'turn'), 20.0)
        self.assertEqual(handle.status, 'completed')
        self.assertEqual(sim.commands, ())


class PurityTest(BaseNodeTest):
    """(12) Rendering and rebinding advance nothing."""

    def test_rendering_and_rebinding_change_nothing(self):
        node = Train()
        sim = Sim(node, 0.1)
        sim.move('crank', by=10.0, duration=1.0)
        sim.run(1.0)
        before = dict(sim.state)
        tick = sim.tick
        node.render()
        self.assertEqual(reads(node.first, 'turn'), before['first.turn'])
        self.assertEqual(reads(node.second, 'turn'), before['second.turn'])
        node.set_state(**dict(sim.state, time=sim.time))
        self.assertEqual(sim.state, before)
        self.assertEqual(sim.tick, tick)
        self.assertEqual(reads(node.first, 'turn'), before['first.turn'])
        sim.move('crank', by=10.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(sim.state['crank'], 20.0)
        self.assertEqual(sim.state['first.turn'], 40.0)


class CompileRefusalTest(BaseNodeTest):
    """(13) A law is inspected as the expression it builds."""

    def test_a_jump_compiles(self):
        # Cycle 1 refused this law by name; cycle 2 compiles it into a
        # JUMP PLAN and integrates it over the tick's pieces
        # (`test_running_jumps.py`). What has not changed is the untimed
        # reading, which `SteppedBody` still poses absolutely.
        sim = Sim(Stepped(), 0.1)
        edge, = [edge for edge in sim.program.edges if edge.kind == 'law']
        plan, = edge.plans
        jump, = plan.jumps
        self.assertEqual(jump.primitive, 'floor')
        self.assertTrue(jump.affine)
        self.assertEqual(jump.argument.evaluate({'crank': 720.0}), 2.0)
        self.assertNotIn('floor', str(plan.skeleton))
        body = Sim(SteppedBody(), 0.1, state={'crank': 115.0})
        self.assertEqual(reads(body.node.first, 'turn'), 13.6)

    def test_a_stdlib_law_is_refused_as_non_symbolic(self):
        with self.assertRaises(UnsupportedLaw) as caught:
            Sim(Stdlib(), 0.1)
        self.assertIn('symbol', str(caught.exception))

    def test_an_opaque_source_is_refused(self):
        with self.assertRaises(UnsupportedLaw) as caught:
            Sim(Opaque(), 0.1)
        message = str(caught.exception)
        self.assertIn('relay', message)
        self.assertIn('first.turn', message)

    def test_a_law_with_a_kink_compiles(self):
        sim = Sim(Train(), 0.1)
        text = sim.program.described()
        self.assertIn('lever', text)
        self.assertIn('max', text)
        self.assertIn('min', text)
        self.assertNotIn('floor', text)


class RangeTest(BaseNodeTest):
    """A joint's range STOPS the tick's motion rather than failing it
    (cycle 3). Cycle 1 refused the whole tick here and left the bank at
    the last admitted one; the declaration has not changed, only what the
    run reads it as."""

    def test_the_crossing_tick_commits_at_the_bound(self):
        node = Ranged()
        sim = Sim(node, 0.1, record=8)
        handle = sim.move('crank', by=50.0, duration=0.5)
        sim.run(0.5)
        self.assertEqual(sim.state['first.turn'], 90.0)
        self.assertEqual(sim.state['crank'], 45.0)
        self.assertEqual(reads(node.first, 'turn'), 90.0)
        self.assertEqual(sim.tick, 5)
        self.assertEqual(handle.status, 'blocked')
        self.assertEqual(handle.admitted, 45.0)
        self.assertEqual(handle.requested, 50.0)
        stop, = sim.stops
        self.assertEqual(stop.coordinate, 'first.turn')
        self.assertEqual(stop.bound, 'high')
        self.assertEqual(stop.value, 90.0)
        self.assertEqual(stop.t, 0.5)
        self.assertEqual(stop.inputs, ('crank',))

    def test_a_move_landing_exactly_on_the_bound_completes(self):
        sim = Sim(RangedExact(), 0.1, record=8)
        handle = sim.move('crank', by=5.0, duration=0.1)
        sim.run(0.1)
        self.assertEqual(sim.state['first.turn'], 90.0)
        self.assertEqual(handle.status, 'completed')
        self.assertEqual(handle.admitted, 5.0)
        self.assertEqual(sim.stops, [])
        self.assertEqual(sim.tick, 1)


class UnboundCoordinateTest(BaseNodeTest):
    """An unbound joint coordinate is refused at construction."""

    def test_a_coordinate_nothing_binds_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            Sim(Unbound(), 0.1)
        message = str(caught.exception)
        self.assertIn('idle.turn', message)
        self.assertIn('rest value', message)

    def test_a_partly_bound_free_joint_names_both_coordinates(self):
        with self.assertRaises(ValueError) as caught:
            Sim(Sixfree(), 0.1)
        message = str(caught.exception)
        self.assertIn('chassis.pose.roll', message)
        self.assertIn('chassis.pose.pitch', message)


class RecordingTest(BaseNodeTest):
    """Recording is explicit and bounded."""

    def test_nothing_is_recorded_by_default(self):
        sim = Sim(Train(), 0.1)
        sim.rate('crank', 1.0)
        sim.run(100.0)
        gc.collect()
        tracemalloc.start()
        sim.run(100.0)
        _current, first = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        sim.run(900.0)
        _current, later = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.assertEqual(sim.trajectory, [])
        self.assertLess(later - first, 64 * 1024)

    def test_a_ring_keeps_the_most_recent_ticks(self):
        sim = Sim(Train(), 0.1, record=64)
        sim.rate('crank', 1.0)
        sim.run(10.0)
        self.assertEqual(len(sim.trajectory), 64)
        self.assertEqual([tick for tick, _bank in sim.trajectory],
                         list(range(37, 101)))

    def test_an_invalid_recording_option_is_refused(self):
        for value in (0, -1, True, 'all'):
            with self.subTest(record=value):
                with self.assertRaises(ValueError) as caught:
                    Sim(Train(), 0.1, record=value)
                self.assertIn('record', str(caught.exception))


class SetStateCoordinateTest(BaseNodeTest):
    """(2.19) `set_state` accepts a qualified joint-coordinate id under a
    running root, and only there."""

    def test_a_coordinate_id_binds_and_places_under_a_running_root(self):
        node = Unbound()
        node.set_state(crank=0.0)
        node.set_state(**{'idle.turn': 12.0})
        self.assertEqual(reads(node.idle, 'turn'), 12.0)
        self.assertEqual(turned(node.idle), 12.0)

    def test_a_coordinate_a_relation_drives_is_still_the_relations(self):
        """A hand binding is not a run: outside one, a coordinate a
        relation drives is cleared and re-solved by the enumeration
        `set_state` runs, exactly as a hand assignment always was. What
        makes the bank stick is the RUN as the binder, and nothing
        else."""
        node = Train()
        node.set_state(crank=0.0, lever=100.0)
        node.set_state(**{'first.turn': 12.0})
        self.assertEqual(reads(node.first, 'turn'), 0.0)

    def test_a_dotted_coordinate_of_a_multi_coordinate_joint_binds(self):
        node = Sixfree()
        node.set_state(lift=0.0, surge=0.0, sway=0.0, heading=0.0)
        node.set_state(**{'chassis.pose.roll': 3.0})
        self.assertEqual(reads(node.chassis, 'pose.roll'), 3.0)
        self.assertNotIn('pose.roll', vars(node.chassis))

    def test_a_coordinate_id_is_refused_under_any_other_root(self):
        for factory in (LoopingTrain, TrainBody):
            with self.subTest(root=factory.__name__):
                node = factory()
                node.set_state(crank=0.0, lever=100.0)
                with self.assertRaises(ValueError) as caught:
                    node.set_state(**{'first.turn': 12.0})
                message = str(caught.exception)
                self.assertIn('first.turn', message)
                self.assertIn('crank', message)

    def test_a_refused_binding_restores_coordinates_too(self):
        node = Unbound()
        node.set_state(crank=0.0)
        node.set_state(**{'idle.turn': 12.0})
        with self.assertRaises(ValueError) as caught:
            node.set_state(**{'idle.turn': 99.0, 'nobody.turn': 1.0})
        self.assertIn('nobody.turn', str(caught.exception))
        self.assertEqual(reads(node.idle, 'turn'), 12.0)
        self.assertEqual(turned(node.idle), 12.0)


class FollowerTest(BaseNodeTest):
    """(2.24) An author-bound plain port follows a run-owned coordinate,
    and is never marked as the run's."""

    def test_the_port_follows_and_keeps_the_author_as_its_binder(self):
        from solid_node.motion.ports import RunBinder

        node = Follower()
        sim = Sim(node, 0.1)
        seen = []

        def check():
            slot = get_coordinate(node.gauge, 'readout')
            seen.append((slot._value, sim.state['gauge.turn'],
                         sim.state['first.turn'],
                         isinstance(slot.binder, RunBinder)))

        sim.every(0.1, check)
        sim.move('crank', by=10.0, duration=1.0)
        sim.run(1.0)
        self.assertEqual(len(seen), 10)
        for readout, turn, first, run_bound in seen:
            self.assertEqual(readout, turn)
            self.assertEqual(readout, first)
            self.assertFalse(run_bound)
        self.assertEqual(seen[-1][0], 20.0)
        self.assertEqual(seen[0][0], 2.0)


class RelativeInstructionDocumentTest(BaseNodeTest):
    """(2.25) A relative instruction is not yet published."""

    def test_the_table_carries_the_absolute_entry_only(self):
        from solid_node.core.serializer import symbolic_document

        node = Train()
        with symbolic_document(node) as (_declarations, instructions):
            table = instructions_table(instructions)
        self.assertEqual(sorted(table), ['Park'])
        self.assertEqual(table['Park']['targets'], {'crank': 40.0})
        self.assertEqual(table['Park']['duration'], 0.5)
