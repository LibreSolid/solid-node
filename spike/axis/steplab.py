"""Spike harness for ADR-056 stepped driver simulation. NON-SHIPPING.

Everything here shims the framework from outside — no framework source
is modified. The one framework seam used is AssemblyNode.set_keyframe,
the only public trigger for the idempotent re-render sweep; see
spike/SCOPE.md sub-question 1.
"""

import time

from solid_node.node import AssemblyNode


class Port:
    """Minimal port shim: a named, unit-tagged value slot the owning
    assembly re-binds on every render. Enough surface to exercise
    per-tick binding inside render() (SCOPE sub-question 4)."""

    def __init__(self, unit=None):
        self.unit = unit
        self.value = None


class Instruction:
    """v1 semantics per ADR-056: driver targets plus a duration,
    ramped linearly. No sequencing, no easing."""

    def __init__(self, targets, duration):
        self.targets = dict(targets)
        self.duration = duration


class StepperDriver:
    """Integer-state driver: state is whole microsteps, forever an int.

    A program distributes a delta over n ticks by integer accumulation:
    state_k = start + (delta * k) // n. At k == n the state is exactly
    start + delta — no float ever enters the state trajectory, which is
    what makes the determinism sub-question decidable by exact
    comparison (the ADR-050 reasoning applied to simulation state).

    Spike smell, recorded for FINDINGS: instances live as class
    attributes on the assembly (declaration and state are conflated),
    so Sim must reset() them. The real API must separate driver
    declaration from per-simulation driver state.
    """

    def __init__(self, default, unit='ustep'):
        self.default = int(default)
        self.unit = unit
        self.reset()

    def reset(self):
        self.state = self.default
        self._program = None

    def start_program(self, target, n_ticks, start_tick):
        self._program = (self.state, int(target) - self.state,
                         n_ticks, start_tick)

    def advance(self, tick):
        if self._program is not None:
            start, delta, n, t0 = self._program
            k = tick - t0
            if k >= n:
                self.state = start + delta
                self._program = None
            else:
                self.state = start + (delta * k) // n
        return self.state


class DrivenAssembly(AssemblyNode):
    """Declaration carrier for the spike's drivers and instructions.

    Originally this class shimmed multi-driver state binding over the
    framework's time-only set_keyframe seam. The multi-driver-state-seam
    change (ADR-056 stage 1) absorbed exactly that shim into the
    framework: AssemblyNode now provides set_state/clear_state/state
    natively, so the override is gone and only the spike-local
    declarations remain. Sim binds the initial snapshot explicitly
    (the framework, by design, invents no defaults — that is stage 2's
    Driver declaration job).
    """

    drivers = {}
    instructions = {}


class _At:
    def __init__(self, sim, tick):
        self._sim = sim
        self._tick = tick

    def trigger(self, name):
        self._add(lambda sim: sim.trigger(name))

    def run(self, fn):
        """Register a DEFERRED callable(sim). Ergonomics finding: the
        ADR's sketch `sim.at(2.5).assertEqual(sim.state.x, 0)` cannot
        work — arguments would evaluate at registration time. The real
        interface needs deferred callables, as here."""
        self._add(fn)

    def _add(self, action):
        self._sim._at.setdefault(self._tick, []).append(action)


class Sim:
    """Fixed-dt stepping loop. Instants are integer tick counts, never
    accumulated floats. Per tick: advance drivers -> bind snapshot ->
    at-actions -> cadence actions."""

    def __init__(self, node, dt):
        self.node = node
        self.dt = dt
        self.tick = 0
        self._at = {}
        self._every = []          # [cadence, fn, args, seconds, calls]
        self.trajectory = []
        for driver in node.drivers.values():
            driver.reset()
        node.set_state(**{name: driver.state
                          for name, driver in node.drivers.items()})
        node.assemble()
        node.build_stls()

    def _ticks(self, value, what):
        k = round(value / self.dt)
        if abs(k * self.dt - value) > 1e-9:
            raise ValueError(
                f'{what} {value} is not a whole number of dt={self.dt} ticks')
        return k

    def at(self, t):
        return _At(self, self._ticks(t, 'instant'))

    def every(self, period, fn, *args):
        self._every.append([self._ticks(period, 'period'), fn, args, 0.0, 0])

    def trigger(self, name):
        instruction = self.node.instructions[name]
        n = self._ticks(instruction.duration, 'duration')
        for dname, target in instruction.targets.items():
            self.node.drivers[dname].start_program(target, n, self.tick)

    def run(self, duration):
        end = self.tick + self._ticks(duration, 'duration')
        for action in self._at.pop(self.tick, []):
            action(self)
        while self.tick < end:
            self.tick += 1
            states = {name: driver.advance(self.tick)
                      for name, driver in sorted(self.node.drivers.items())}
            self.node.set_state(**states)
            self.trajectory.append(
                (self.tick, tuple(sorted(states.items()))))
            for action in self._at.pop(self.tick, []):
                action(self)
            for slot in self._every:
                if self.tick % slot[0] == 0:
                    t0 = time.perf_counter()
                    slot[1](*slot[2])
                    slot[3] += time.perf_counter() - t0
                    slot[4] += 1

    @property
    def assertion_stats(self):
        """(calls, mean seconds per call) across all cadence slots."""
        calls = sum(slot[4] for slot in self._every)
        seconds = sum(slot[3] for slot in self._every)
        return calls, (seconds / calls if calls else 0.0)
