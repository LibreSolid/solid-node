"""Build numeric mechanical fixtures, never import the Curta calculator model.

Curta data below are a reduced measured-contact model, NOT a full-machine
conversion or an exact runtime CAD contact solver. See evidence/provenance.json.
"""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
CURTA = WORKSPACE / 'projects/Calculators/Curta-Type-I-3x'


def seal(p):
    p.pop('id', None)
    p['id'] = hashlib.sha256(json.dumps(p, sort_keys=True).encode()).hexdigest()
    return p


def base(q, m, inputs):
    return dict(version='open-run-spike/1', q=q, m=m, inputs=inputs,
                relations=[], events=[], stops=[])


def relation(id, a, b, ratio, when=True):
    return dict(id=id, a=a, b=b, ratio=ratio, when=when)


def event(id, coord, phase, writes, period=0, direction=1, when=True):
    return dict(id=id, coord=coord, phase=phase, period=period,
                direction=direction, when=when, writes=writes)


def clutch():
    p = base(dict(shaft=0., wheel=0., sleeve=1.), dict(mesh=True),
             ['shaft', 'wheel', 'sleeve'])
    p['relations'] = [relation('teeth', 'shaft', 'wheel', -2, ['m', 'mesh'])]
    p['events'] = [event('open', 'sleeve', .5, {'mesh': False}, direction=-1),
                   event('close', 'sleeve', .5, {'mesh': True})]
    # Ideal keyed/toothed phase compatibility, not an arbitrary clutch switch.
    p['events'][1]['require'] = ['phase-aligned',
        ['+', ['q', 'wheel'], ['*', 2, ['q', 'shaft']]], 20]
    p['stops'] = [dict(id='sleeve-travel', coord='sleeve', lo=0, hi=1)]
    return seal(p)


def ratchet():
    p = base(dict(disc=0., lift=0.), dict(detent=0., down=True), ['disc', 'lift'])
    p['events'] = [event('tooth-seat', 'disc', 0, {'detent': ['q', 'disc']}, period=10),
        event('lift-pawl', 'lift', .5, {'down': False}),
        event('lower-pawl', 'lift', .5, {'down': True,
            'detent': ['*', 10, ['floor', ['*', .1, ['q', 'disc']]]]}, direction=-1)]
    p['stops'] = [dict(id='pawl-flank', coord='disc', lo=['m', 'detent'], when=['m', 'down']),
                  dict(id='lift-travel', coord='lift', lo=0, hi=1)]
    return seal(p)


def concurrent():
    p = base(dict(motor=0., cam=0., steering=0., rack=0.,
                  x_motor=0., x=0., y_motor=0., y=0.), {},
             ['motor', 'steering', 'x_motor', 'y_motor'])
    p['relations'] = [relation('timing', 'motor', 'cam', .5),
        relation('steering-rack', 'steering', 'rack', .1),
        relation('x-screw', 'x_motor', 'x', 2 / 360),
        relation('y-screw', 'y_motor', 'y', 2 / 360)]
    return seal(p)


def profiles():
    source = CURTA / 'simulation/carry_profiles.py'
    tree = ast.parse(source.read_text())
    return {n.targets[0].id: ast.literal_eval(n.value)
            for n in tree.body if isinstance(n, ast.Assign)}


def first_crossing(profile, height):
    for (x0, y0), (x1, y1) in zip(profile, profile[1:]):
        if y0 < height <= y1:
            return x0 + (x1 - x0) * (height - y0) / (y1 - y0)
    raise ValueError('profile never crosses contact height')


def curta():
    data = profiles()
    # Measured over-centre crest; an ideal instantaneous detent transition.
    trip = 36 * first_crossing(data['PIN_DROP'], .61 * 4.2)
    reset = first_crossing(data['RESET_LIFT'], 1.85)
    q = dict(crank=0., selector=1.)
    # Positions are initialization of marked physical wheels, not operands.
    for i, angle in enumerate((324., 324., 0.)):
        q[f'wheel{i}'] = angle
        q[f'shaft{i}'] = angle * 2
    m = dict(input_contact=False, selected=True)
    for i in (1, 2):
        m[f'latched{i}'], m[f'carry_contact{i}'] = False, False
    p = base(q, m, ['crank', 'selector'])
    # The selector here has normalized travel 0..1 for rows with zero or one
    # tooth. It is NOT the finished nine-row physical selector-height model.
    p['events'] = [event('select-one-row', 'selector', .5, {'selected': True}),
        event('select-zero-row', 'selector', .5, {'selected': False}, direction=-1),
        event('input-tooth-enter', 'crank', 113.5, {'input_contact': True}, period=360),
        event('input-tooth-leave', 'crank', 124.75, {'input_contact': False}, period=360)]
    p['relations'] = [relation('drum-input-tooth', 'crank', 'shaft0', 72 / 11.25,
                             ['and', ['m', 'input_contact'], ['m', 'selected']])]
    for i in range(3):
        p['relations'].append(relation(f'bevel{i}', f'shaft{i}', f'wheel{i}', .5))
    for i in (1, 2):
        p['events'].extend([
            event(f'pin-trips-lever{i}', f'wheel{i-1}', trip, {f'latched{i}': True}, period=360),
            event(f'carry-tooth-enter{i}', 'crank', 137.625 + 20 * i - 11.25,
                  {f'carry_contact{i}': True}, period=360),
            event(f'carry-tooth-leave{i}', 'crank', 137.625 + 20 * i,
                  {f'carry_contact{i}': False}, period=360),
            event(f'cam-resets-lever{i}', 'crank', reset + 20 * (i-1),
                  {f'latched{i}': False}, period=360)])
        p['relations'].append(relation(f'carry-tooth{i}', 'crank', f'shaft{i}', 72 / 11.25,
            ['and', ['m', f'latched{i}'], ['m', f'carry_contact{i}']]))
    # Reduced rig is forward-only; complete Curta ratchet profile is NOT used.
    p['stops'] = [dict(id='selector-travel', coord='selector', lo=0, hi=1)]
    p['metadata'] = dict(units='angles deg; selector normalized',
        wheel_trip_degrees=trip, first_cam_reset_degrees=reset,
        scope='three-wheel reduced Curta measured-contact rig; forward crank only')
    return seal(p)


def all_programs():
    return {name: factory() for name, factory in
            [('clutch', clutch), ('ratchet', ratchet), ('concurrent', concurrent), ('curta', curta)]}


if __name__ == '__main__':
    print(json.dumps(all_programs(), indent=2))
