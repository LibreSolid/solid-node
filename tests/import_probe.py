# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Report which modules a snippet actually imports, in a fresh interpreter.

What a command costs at startup is decided by what it imports, and that is
only observable in a process that has not already imported it. Asserting on
`sys.modules` inside the test runner would prove nothing: pytest has already
loaded the whole framework by the time a test body runs.

So the snippet runs in a subprocess, and the probe records `sys.modules`
before and after it. `added` is the honest answer to "what did this cost",
and it is deterministic -- unlike wall-clock time, which is why the specs
assert on module sets and leave the timings in the proposal as motivation.

The report travels through its own file rather than a marker on stderr, so a
snippet is free to write whatever it likes to stdout and stderr and the
caller still sees both streams unchanged.
"""

import json
import os
import subprocess
import sys
import tempfile


BASEDIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(BASEDIR)

_PROBE = r'''
import json
import os
import sys

import traceback

_before = set(sys.modules)
_report = os.environ['SOLID_IMPORT_PROBE_REPORT']
_snippet = os.environ['SOLID_IMPORT_PROBE_SNIPPET']
_status = 0
_error = None

with open(_snippet) as _handle:
    _code = compile(_handle.read(), '<probe-snippet>', 'exec')

# A snippet that dies partway through has imported less than one that ran,
# so a crash must never be reported as a clean run: it would satisfy an
# assertion like "cadquery was absent" for entirely the wrong reason.
# Every exit path therefore sets _status before the report is written.
try:
    exec(_code, {'__name__': '__main__'})
except SystemExit as stop:
    if stop.code is None:
        _status = 0
    elif isinstance(stop.code, int):
        _status = stop.code
    else:
        sys.stderr.write(f'{stop.code}\n')
        _status = 1
except BaseException:
    _error = traceback.format_exc()
    sys.stderr.write(_error)
    _status = 1
finally:
    _after = set(sys.modules)
    with open(_report, 'w') as _handle:
        json.dump({'status': _status,
                   'error': _error,
                   'added': sorted(_after - _before),
                   'modules': sorted(_after)}, _handle)

sys.exit(_status)
'''


class ProbeResult:
    """One probed run: its streams, its status, and what it imported."""

    def __init__(self, status, added, modules, stdout, stderr, error=None):
        self.status = status
        self.error = error
        self.added = frozenset(added)
        self.modules = frozenset(modules)
        self.stdout = stdout
        self.stderr = stderr

    def check(self):
        """Assert the snippet ran to completion, and return self.

        A test asserting that some module was NOT imported should call this
        first: a snippet that raised before reaching the import under test
        would otherwise pass.
        """
        assert self.status == 0, (
            f'the probed snippet exited {self.status}\n'
            f'{self.error or ""}stdout:\n{self.stdout}\nstderr:\n{self.stderr}')
        return self

    def imported(self, name):
        """Whether `name` -- or anything inside it -- was imported."""
        prefix = f'{name}.'
        return any(module == name or module.startswith(prefix)
                   for module in self.modules)

    def imported_under(self, package):
        """Every imported module inside `package`, the package included."""
        prefix = f'{package}.'
        return {module for module in self.modules
                if module == package or module.startswith(prefix)}

    def __repr__(self):
        return (f'ProbeResult(status={self.status}, '
                f'added={len(self.added)} modules)')


def probe(snippet, argv=(), env=None, cwd=None, timeout=300):
    """Run `snippet` in a fresh interpreter and report what it imported.

    `argv` becomes the child's `sys.argv[1:]`, so a snippet may call
    `solid_node.cli.manage()` and be dispatched exactly as the real command
    line dispatches it.
    """
    with tempfile.TemporaryDirectory(prefix='solid-import-probe-') as scratch:
        snippet_path = os.path.join(scratch, 'snippet.py')
        report_path = os.path.join(scratch, 'report.json')
        with open(snippet_path, 'w') as handle:
            handle.write(snippet)

        environment = dict(os.environ, PYTHONPATH=REPO_DIR,
                           SOLID_IMPORT_PROBE_SNIPPET=snippet_path,
                           SOLID_IMPORT_PROBE_REPORT=report_path)
        environment.update(env or {})

        completed = subprocess.run(
            [sys.executable, '-c', _PROBE, *argv],
            cwd=cwd or REPO_DIR, env=environment,
            capture_output=True, text=True, timeout=timeout,
        )

        try:
            with open(report_path) as handle:
                report = json.load(handle)
        except (OSError, ValueError):
            raise AssertionError(
                'the import probe produced no report; the child likely died '
                f'before running.\nstdout:\n{completed.stdout}\n'
                f'stderr:\n{completed.stderr}')

    return ProbeResult(report['status'], report['added'], report['modules'],
                       completed.stdout, completed.stderr,
                       report.get('error'))


def probe_import(module):
    """What importing `module` alone costs in a fresh interpreter."""
    return probe(f'import {module}\n')
