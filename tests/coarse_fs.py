# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""A filesystem that stores timestamps at millisecond resolution.

Emscripten's MEMFS does, and under it solid-node's mtime-equality
freshness contract failed 13 of 25 generations -- a project whose sources
carry sub-second mtimes got no artifact caching at all. Reproduction:
browser-engine, change `prove-solid-node-runs-in-browser`, upstream
finding 1, `evidence/groundwork.md` task 1.4 (solid-node 0.5.1 at commit
1c03e337 vendored unmodified, Pyodide 314.0.5 / Emscripten 5.0.3,
headless Chromium 149).

Only `os.utime` is patched here. Reads are left to the real filesystem,
which stores faithfully whatever this wrapper computed, so a test using
this emulator watches genuine `stat` calls against genuine files. What is
simulated is exactly one thing -- that a write cannot record finer than a
millisecond -- which keeps the framework's own choice of timestamp API,
the thing under test, entirely in the framework.
"""

import math
import os
import time
from contextlib import contextmanager
from unittest import mock


MILLISECOND_NS = 10 ** 6
SECOND_NS = 10 ** 9

# Pinned, not chosen freshly: half of all whole-millisecond stamps survive
# the float path, so a stamp picked at random would make these tests flaky
# at 50%. This is the evidence's own generation-0 value. Its nearest double
# is 1787402869.5399999619..., which floors to ...539999961 ns, which a
# millisecond-resolution filesystem stores as ...539 -- one millisecond
# below the value that was asked for.
PINNED_STAMP_NS = 1787402869 * SECOND_NS + 540 * MILLISECOND_NS


def float_to_ns(value):
    """How CPython converts a float timestamp to (sec, nsec): it floors.

    That floor is the whole defect. It lands a nanosecond or two below the
    value that was read, which a nanosecond-resolution filesystem stores
    harmlessly and a coarser one truncates across a quantum boundary.
    """
    seconds = math.floor(value)
    return seconds * SECOND_NS + math.floor((value - seconds) * 1e9)


def truncate_to_ms(value_ns):
    return value_ns - value_ns % MILLISECOND_NS


def stamp(path, mtime_ns):
    """Give a file a timestamp the emulated filesystem could hold.

    Uses the real `os.utime`, because this models a file arriving already
    quantised -- written by the host, unpacked from a zip -- not the
    framework stamping an artifact.
    """
    _real_utime(path, ns=(mtime_ns, mtime_ns))


_real_utime = os.utime


def _coarse_utime(path, times=None, *, ns=None, **kwargs):
    if ns is not None:
        atime_ns, mtime_ns = ns
    elif times is None:
        now = float_to_ns(time.time())
        atime_ns = mtime_ns = now
    else:
        atime_ns, mtime_ns = (float_to_ns(value) for value in times)
    _real_utime(path,
                ns=(truncate_to_ms(atime_ns), truncate_to_ms(mtime_ns)),
                **kwargs)


@contextmanager
def millisecond_filesystem():
    """Every `os.utime` inside this block records only to the millisecond."""
    with mock.patch('os.utime', _coarse_utime):
        yield
