# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""How a build command starts a subprocess.

Not the platform default. On Linux that default is `fork`, and a build
command forks late: `solid build` resolves the model in its own process to
tell a missing model from a failed build, and resolving it imports and runs
the model's geometry. That leaves OCCT's OpenMP worker team live -- in a
real project, one thread becomes forty-six.

`fork()` copies the address space but not the threads. The child inherits
libgomp's record of a worker team none of whose threads exist in it, and the
first parallel OCCT call -- tessellation during STL export -- waits on that
team's barrier and never wakes. Not a slow build: a permanent stop, at no
CPU, with nothing in flight. It hides whenever the build directory is already
current, because the child then reports CURRENT without tessellating
anything.

So build subprocesses start from a fresh interpreter, which inherits no
thread pool, worker team, or lock from whatever the parent happened to
import. A child is handed its target instead of inheriting it, which is why
every target here is a module-level function taking plain values.
"""

import multiprocessing

_CONTEXT = multiprocessing.get_context('spawn')

Process = _CONTEXT.Process

__all__ = ['Process']
