"""Experimental piecewise-affine mechanical interpreter. No machine dispatch.

Coordinates are unwrapped. Relations constrain velocities, events change local
contact memory, and unilateral stops constrain admitted motion. SI is not
assumed: fixture units are explicit. This is NOT a general contact/force solver.
"""
import copy
import math

EPS = 1e-8
TIME_EPS = 1e-12


def value(expr, q, m):
    if not isinstance(expr, list):
        return expr
    op, *args = expr
    if op == 'q':
        return q[args[0]]
    if op == 'm':
        return m[args[0]]
    args = [value(x, q, m) for x in args]
    if op == 'and':
        return all(args)
    if op == 'not':
        return not args[0]
    if op == '+':
        return args[0] + args[1]
    if op == '-':
        return args[0] - args[1]
    if op == '*':
        return args[0] * args[1]
    if op == 'floor':
        return math.floor(args[0])
    if op == 'phase-aligned':
        return abs(args[0] - round(args[0] / args[1]) * args[1]) <= EPS
    if op == '==':
        return abs(args[0] - args[1]) <= EPS
    raise ValueError(f'unsupported expression: {op}')


class Engine:
    def __init__(self, program, dt=1 / 240):
        if program['version'] != 'open-run-spike/1':
            raise ValueError('unsupported program version')
        if not math.isfinite(dt) or dt <= 0:
            raise ValueError('positive finite dt required')
        self.p = copy.deepcopy(program)
        self.dt, self.tick = dt, 0
        self.q, self.m = copy.deepcopy(program['q']), copy.deepcopy(program['m'])
        self.rates, self.moves = {}, {}
        self.blocked, self.counts, self.trace = [], {}, []
        self._check_initial()

    def ev(self, expr):
        return value(expr, self.q, self.m)

    def _check_initial(self):
        ids = [r['id'] for field in ('relations', 'events', 'stops')
               for r in self.p[field]]
        if len(set(ids)) != len(ids):
            raise ValueError('duplicate mechanism identity')
        for r in self.p['relations']:
            if not math.isfinite(r['ratio']) or r['ratio'] == 0:
                raise ValueError('nonzero finite affine ratio required')
            for k in ('a', 'b'):
                if r[k] not in self.q:
                    raise ValueError('unknown coordinate')
            self.ev(r.get('when', True))
        for e in self.p['events']:
            if e['coord'] not in self.q or e['direction'] not in (-1, 1):
                raise ValueError('invalid event surface')
            if e.get('period', 0) < 0:
                raise ValueError('negative event period')
            self.ev(e.get('when', True))
            self.ev(e.get('require', True))
            for k, v in e['writes'].items():
                if k not in self.m:
                    raise ValueError('unknown state slot')
                self.ev(v)
        for s in self.p['stops']:
            if self.ev(s.get('when', True)):
                if self.q[s['coord']] < self.ev(s.get('lo', -math.inf)) - EPS:
                    raise ValueError('initial state below stop')
                if self.q[s['coord']] > self.ev(s.get('hi', math.inf)) + EPS:
                    raise ValueError('initial state above stop')

    def rate(self, coord, rate):
        if coord not in self.p['inputs'] or not math.isfinite(rate):
            raise ValueError('finite rate on declared input required')
        if any(coord in g['rates'] for g in self.moves.values() if g['remaining']):
            raise ValueError('actuator already owned by motion group')
        if rate == 0:
            self.rates.pop(coord, None)
        else:
            self.rates[coord] = rate

    def move(self, group, deltas, ticks):
        active = {k: g for k, g in self.moves.items() if g['remaining']}
        if not deltas or not isinstance(ticks, int) or ticks <= 0 or group in active:
            raise ValueError('new group and positive integer duration required')
        owned = set(self.rates)
        for g in self.moves.values():
            if g['remaining']:
                owned.update(g['rates'])
        if owned.intersection(deltas) or not set(deltas).issubset(self.p['inputs']):
            raise ValueError('actuator ownership conflict')
        if not all(math.isfinite(v) for v in deltas.values()):
            raise ValueError('finite travel required')
        self.moves = active
        self.moves[group] = dict(rates={k: v / (ticks * self.dt) for k, v in deltas.items()},
                                 remaining=ticks, paused=False, status='running')

    def pause(self, group, paused=True):
        if not paused and self.moves[group]['status'] == 'blocked':
            raise ValueError('blocked move needs explicit replan in this spike')
        self.moves[group]['paused'] = paused

    def snapshot(self):
        return copy.deepcopy(dict(program=self.p['id'], dt=self.dt, tick=self.tick,
            q=self.q, m=self.m, rates=self.rates, moves=self.moves,
            blocked=self.blocked, counts=self.counts, trace=self.trace))

    def restore(self, snap):
        if snap['program'] != self.p['id'] or snap['dt'] != self.dt:
            raise ValueError('incompatible checkpoint')
        for k in ('tick', 'q', 'm', 'rates', 'moves', 'blocked', 'counts', 'trace'):
            setattr(self, k, copy.deepcopy(snap[k]))

    def _velocities(self):
        adj = {k: [] for k in self.q}
        for r in self.p['relations']:
            if self.ev(r.get('when', True)):
                adj[r['a']].append((r['b'], r['ratio']))
                adj[r['b']].append((r['a'], 1 / r['ratio']))
        requested = dict(self.rates)
        for g in self.moves.values():
            if g['remaining'] and not g['paused']:
                requested.update(g['rates'])
        v, components = {}, []
        for start in sorted(self.q):
            if start in v:
                continue
            members, stack = set(), [start]
            while stack:
                x = stack.pop()
                if x not in members:
                    members.add(x)
                    stack.extend(y for y, _ in adj[x])
            seeds = sorted(members.intersection(requested))
            root = seeds[0] if seeds else start
            v[root] = requested.get(root, 0)
            stack = [root]
            while stack:
                x = stack.pop()
                for y, ratio in adj[x]:
                    expected = v[x] * ratio
                    if y in v:
                        if abs(v[y] - expected) > EPS:
                            raise ValueError(f'inconsistent closed relation at {y}')
                    else:
                        v[y] = expected
                        stack.append(y)
            for x in seeds:
                if abs(v[x] - requested[x]) > EPS:
                    raise ValueError(f'incompatible prescribed motion at {x}')
            components.append((members, seeds))
        blocked_members = set()
        for s in self.p['stops']:
            if not self.ev(s.get('when', True)):
                continue
            c = s['coord']
            lo, hi = self.ev(s.get('lo', -math.inf)), self.ev(s.get('hi', math.inf))
            if (v[c] < 0 and self.q[c] <= lo + EPS or
                    v[c] > 0 and self.q[c] >= hi - EPS):
                blocked_members.add(c)
        for members, seeds in components:
            if members.intersection(blocked_members):
                self.blocked.extend(x for x in seeds if x not in self.blocked)
                for x in members:
                    v[x] = 0
        return v

    def _event_distance(self, e, v):
        speed = v[e['coord']]
        if speed * e['direction'] <= 0:
            return math.inf
        x, phase, period = self.q[e['coord']], e['phase'], e.get('period', 0)
        if period:
            if speed > 0:
                level = phase + (math.floor((x - phase + EPS) / period) + 1) * period
            else:
                level = phase + (math.ceil((x - phase - EPS) / period) - 1) * period
        else:
            level = phase
        t = (level - x) / speed
        return t if t > TIME_EPS else math.inf

    def _on_surface(self, e):
        d = self.q[e['coord']] - e['phase']
        if e.get('period', 0):
            d -= round(d / e['period']) * e['period']
        return abs(d) <= EPS

    def _settle(self, arrival_velocity):
        fired = set()
        for _ in range(64):
            batch = [e for e in self.p['events'] if e['id'] not in fired
                     and arrival_velocity[e['coord']] * e['direction'] > 0
                     and self._on_surface(e) and self.ev(e.get('when', True))]
            if not batch:
                return
            writes = {}
            for e in sorted(batch, key=lambda x: x['id']):
                if not self.ev(e.get('require', True)):
                    raise ValueError(f'inadmissible engagement: {e["id"]}')
                for k, expr in e['writes'].items():
                    new = self.ev(expr)
                    if k in writes and writes[k] != new:
                        raise ValueError(f'conflicting event writes: {k}')
                    writes[k] = new
                fired.add(e['id'])
            self.m.update(writes)
            for e in sorted(batch, key=lambda x: x['id']):
                self.counts[e['id']] = self.counts.get(e['id'], 0) + 1
                self.trace.append(dict(id=e['id'], at=self.q[e['coord']]))
            self.trace = self.trace[-64:]
        raise ValueError('same-instant event settlement limit')

    def _step(self):
        remaining, self.blocked = self.dt, []
        for _ in range(1000):
            if remaining <= TIME_EPS:
                break
            v = self._velocities()
            interval = remaining
            for e in self.p['events']:
                # Disabled surfaces are still visited: another event can enable
                # their transition at exactly the same instant.
                interval = min(interval, self._event_distance(e, v))
            for s in self.p['stops']:
                if not self.ev(s.get('when', True)):
                    continue
                c = s['coord']
                if v[c]:
                    edge = self.ev(s.get('hi', math.inf) if v[c] > 0 else s.get('lo', -math.inf))
                    t = (edge - self.q[c]) / v[c]
                    if t > TIME_EPS:
                        interval = min(interval, t)
            for c in self.q:
                self.q[c] += v[c] * interval
            self._settle(v)
            remaining -= interval
        else:
            raise ValueError('event subdivision limit')
        # Evaluate the final boundary too, so landing exactly on a stop reports it.
        self._velocities()
        self.blocked.sort()
        for g in self.moves.values():
            if g['remaining'] and not g['paused']:
                if set(g['rates']).intersection(self.blocked):
                    g['paused'], g['status'] = True, 'blocked'
                else:
                    g['remaining'] -= 1
                    if not g['remaining']:
                        g['status'] = 'completed'
        self.tick += 1

    def advance(self, ticks):
        if not isinstance(ticks, int) or ticks < 0:
            raise ValueError('nonnegative integer ticks required')
        for _ in range(ticks):
            before = self.snapshot()
            try:
                self._step()
            except Exception:
                self.restore(before)
                raise
        return self.snapshot()
