import copy
import unittest

from kernel import Engine
from programs import clutch, ratchet, concurrent, curta, event, relation, seal


def travel(e, c, by, ticks=1):
    e.rate(c, by / (ticks * e.dt))
    e.advance(ticks)
    e.rate(c, 0)


class Mechanics(unittest.TestCase):
    def test_coupling_hold_reengage_and_reverse_solve(self):
        e = Engine(clutch(), dt=1)
        travel(e, 'shaft', 10)
        self.assertEqual(e.q['wheel'], -20)
        travel(e, 'sleeve', -1)
        travel(e, 'shaft', 10)
        self.assertEqual(e.q['wheel'], -20)
        travel(e, 'sleeve', 1)
        self.assertEqual(e.q['wheel'], -20)
        travel(e, 'wheel', -10)
        self.assertEqual(e.q['shaft'], 25)
        e.advance(50)
        self.assertEqual(e.q['wheel'], -30)

    def test_rates_integrate_history(self):
        e = Engine(clutch(), dt=1)
        travel(e, 'shaft', 10)
        travel(e, 'shaft', 20)
        self.assertEqual(e.q['shaft'], 30)

    def test_misaligned_reengagement_is_refused_without_teleporting(self):
        e = Engine(clutch(), dt=1)
        travel(e, 'sleeve', -1)
        travel(e, 'shaft', 1)
        e.rate('sleeve', 1)
        before = e.snapshot()
        with self.assertRaisesRegex(ValueError, 'inadmissible engagement'):
            e.advance(1)
        self.assertEqual(e.snapshot(), before)

    def test_ratchet_has_backlash_blocks_reverse_and_can_lift(self):
        e = Engine(ratchet(), dt=1)
        travel(e, 'disc', 25)
        self.assertEqual(e.m['detent'], 20)
        travel(e, 'disc', -15)
        self.assertEqual(e.q['disc'], 20)
        self.assertEqual(e.blocked, ['disc'])
        travel(e, 'lift', 1)
        travel(e, 'disc', -15)
        self.assertEqual(e.q['disc'], 5)
        travel(e, 'lift', -1)
        travel(e, 'disc', -10)
        self.assertEqual(e.q['disc'], 0)

    def test_completed_commands_do_not_accumulate(self):
        e = Engine(concurrent(), dt=1)
        for n in range(100):
            e.move(str(n), {'motor': 10}, 1)
            e.advance(1)
        self.assertLessEqual(len(e.moves), 1)

    def test_swept_stop_not_only_endpoint_and_independent_drive_continues(self):
        p = concurrent()
        p['stops'] = [dict(id='rack-stop', coord='rack', hi=1)]
        e = Engine(seal(p), dt=1)
        e.rate('steering', 100)
        e.rate('motor', 720)
        e.advance(1)
        self.assertAlmostEqual(e.q['rack'], 1)
        self.assertEqual(e.blocked, ['steering'])
        self.assertAlmostEqual(e.q['cam'], 360)

    def test_incompatible_drives_rollback_entire_tick(self):
        e = Engine(clutch(), dt=1)
        e.rate('shaft', 10)
        e.rate('wheel', 10)
        before = e.snapshot()
        with self.assertRaisesRegex(ValueError, 'incompatible'):
            e.advance(1)
        self.assertEqual(e.snapshot(), before)

    def test_consistent_loop_supported_inconsistent_loop_refused(self):
        p = concurrent()
        p['relations'].append(relation('return', 'cam', 'motor', 2))
        e = Engine(seal(p), dt=1)
        travel(e, 'motor', 10)
        self.assertEqual(e.q['cam'], 5)
        p['relations'][-1]['ratio'] = 3
        e = Engine(seal(p), dt=1)
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            travel(e, 'motor', 10)

    def test_simultaneous_events_settle_without_declaration_order(self):
        p = concurrent()
        p['m'] = dict(a=False, b=False)
        p['events'] = [event('a', 'motor', 10, {'a': True}),
            event('b', 'motor', 10, {'b': True}, when=['m', 'a'])]
        for reverse in (False, True):
            if reverse:
                p['events'].reverse()
            e = Engine(seal(p), dt=1)
            travel(e, 'motor', 20)
            self.assertEqual(e.m, dict(a=True, b=True))
            self.assertEqual(e.counts, dict(a=1, b=1))

    def test_event_write_conflict_rolls_back(self):
        p = concurrent()
        p['m'] = dict(latch=False)
        p['events'] = [event('a', 'motor', 10, {'latch': True}),
                       event('b', 'motor', 10, {'latch': False})]
        e = Engine(seal(p), dt=1)
        e.rate('motor', 20)
        before = e.snapshot()
        with self.assertRaisesRegex(ValueError, 'conflicting event'):
            e.advance(1)
        self.assertEqual(e.snapshot(), before)

    def test_curta_two_successive_physical_carries_in_one_tick(self):
        e = Engine(curta(), dt=1)
        travel(e, 'crank', 180)
        for i, expected in enumerate((360, 360, 36)):
            self.assertAlmostEqual(e.q[f'wheel{i}'], expected)
        self.assertTrue(e.m['latched1'])
        self.assertTrue(e.m['latched2'])
        ids = [x['id'] for x in e.trace]
        self.assertLess(ids.index('pin-trips-lever1'), ids.index('carry-tooth-enter1'))
        self.assertLess(ids.index('pin-trips-lever2'), ids.index('carry-tooth-enter2'))

    def test_curta_reset_after_wrap_and_no_arithmetic_repose(self):
        e = Engine(curta(), dt=1)
        travel(e, 'crank', 360)
        self.assertFalse(e.m['latched1'])
        self.assertTrue(e.m['latched2'])
        travel(e, 'crank', 20)
        self.assertFalse(e.m['latched2'])
        travel(e, 'crank', 340)
        self.assertAlmostEqual(e.q['wheel0'], 396)
        self.assertAlmostEqual(e.q['wheel1'], 360)
        self.assertAlmostEqual(e.q['wheel2'], 36)

    def test_selector_disengages_input_without_changing_wheel(self):
        e = Engine(curta(), dt=1)
        travel(e, 'selector', -1)
        before = [e.q[f'wheel{i}'] for i in range(3)]
        travel(e, 'crank', 720)
        self.assertEqual([e.q[f'wheel{i}'] for i in range(3)], before)

    def test_small_steps_match_many_contacts_inside_one_step(self):
        states = []
        for ticks in (1, 7, 240, 997):
            e = Engine(curta(), dt=1 / ticks)
            travel(e, 'crank', 1080, ticks)
            states.append(e.snapshot())
        for s in states[1:]:
            self.assertEqual(s['m'], states[0]['m'])
            self.assertEqual(s['counts'], states[0]['counts'])
            for k in s['q']:
                self.assertAlmostEqual(s['q'][k], states[0]['q'][k], places=7)

    def test_motor_steering_and_printer_group_pause_checkpoint_resume(self):
        e = Engine(concurrent(), dt=.01)
        e.rate('motor', 720)
        e.rate('steering', 10)
        e.move('print', {'x_motor': 1800, 'y_motor': 900}, 100)
        e.advance(40)
        self.assertAlmostEqual(e.q['x'], 4)
        e.pause('print')
        snap = e.snapshot()
        e.advance(50)
        self.assertAlmostEqual(e.q['x'], 4)
        self.assertAlmostEqual(e.q['cam'], 324)
        self.assertAlmostEqual(e.q['rack'], .9)
        e.pause('print', False)
        e.advance(60)
        final = e.snapshot()
        self.assertAlmostEqual(e.q['x'], 10)
        self.assertAlmostEqual(e.q['y'], 5)
        self.assertEqual(e.moves['print']['status'], 'completed')
        e.restore(snap)
        e.advance(50)
        e.pause('print', False)
        e.advance(60)
        self.assertEqual(e.snapshot(), final)

    def test_ownership_version_and_checkpoint_boundary(self):
        e = Engine(concurrent())
        e.move('print', {'x_motor': 10}, 50)
        with self.assertRaisesRegex(ValueError, 'owned'):
            e.rate('x_motor', 1)
        before = e.snapshot()
        bad = copy.deepcopy(before)
        bad['program'] = 'other-model'
        with self.assertRaisesRegex(ValueError, 'incompatible checkpoint'):
            e.restore(bad)
        self.assertEqual(e.snapshot(), before)
        p = concurrent()
        p['version'] = 'future/99'
        with self.assertRaisesRegex(ValueError, 'unsupported program'):
            Engine(p)

    def test_broken_mechanisms_are_detected(self):
        def observed(p):
            e = Engine(seal(p), dt=1)
            travel(e, 'crank', 180)
            return [round(e.q[f'wheel{i}'], 7) for i in range(3)]
        p = curta()
        self.assertEqual(observed(p), [360, 360, 36])
        for mutation in ('missing-pin', 'wrong-ratio', 'missed-contact'):
            p = curta()
            if mutation == 'missing-pin':
                p['events'] = [x for x in p['events'] if x['id'] != 'pin-trips-lever2']
            elif mutation == 'wrong-ratio':
                p['relations'][0]['ratio'] *= -1
            else:
                p['events'] = [x for x in p['events'] if x['id'] != 'input-tooth-enter']
            with self.subTest(mutation=mutation):
                self.assertNotEqual(observed(p), [360, 360, 36])


if __name__ == '__main__':
    unittest.main(verbosity=2)
