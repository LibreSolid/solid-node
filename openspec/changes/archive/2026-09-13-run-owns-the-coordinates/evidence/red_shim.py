"""A pytest plugin that installs the DECLARATIONS this cycle adds, and
none of its behaviour, so every red of section 2 can be seen for its own
reason rather than as one collection error.

Run as `python -m pytest -p red_shim ...` with this directory on
PYTHONPATH. It gives `Time` a `running()` spelling and a `mode`, exports
a `RunBinder` marker and the two new error kinds, and lets an
`Instruction` carry `by=`. Nothing here owns a coordinate, compiles a
law, integrates a tick or binds anything: every case that fails below
fails because the framework does not do the thing, not because a name is
missing.
"""

import solid_node.motion.ports as ports
import solid_node.simulation as simulation
import solid_node.simulation.instruction as instruction_module
from solid_node.motion.ports import Time


def _running(cls):
    base = object.__new__(cls)
    object.__setattr__(base, 'loop', None)
    return base


Time.running = classmethod(_running)
Time.mode = property(lambda self: 'loop' if self.loop is not None
                     else 'running')


class RunBinder:
    def described(self):
        return 'the running simulation'


class RunConflict(ValueError):
    pass


class UnsupportedLaw(ValueError):
    pass


ports.RunBinder = RunBinder
simulation.RunConflict = RunConflict
simulation.UnsupportedLaw = UnsupportedLaw

_original = instruction_module.Instruction.__init__


def _init(self, targets=None, duration=None, *, by=None):
    _original(self, targets if targets is not None else (by or {}), duration)
    self.by = by
    if by is not None:
        self.targets = None


instruction_module.Instruction.__init__ = _init
