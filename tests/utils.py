# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import re


def edit_source(test, path):
    """Give a tracked source genuinely different content, and put it back.

    A test that means "this file was edited" has to change bytes. Moving
    the timestamp alone stopped being an edit when build-pipeline gained
    its content-verified fallback: a source whose mtime moved and whose
    content did not is exactly the case the fallback exists to spare, so
    a guard written that way would assert the defect rather than the
    rule.

    The probe is a trailing comment, so the file stays valid whatever
    happens to it, and both the original bytes and the original
    timestamps are restored on cleanup -- these are the suite's own
    fixtures, not scratch files.
    """
    with open(path, 'rb') as source:
        original = source.read()
    stat = os.stat(path)

    def restore():
        with open(path, 'wb') as source:
            source.write(original)
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))

    test.addCleanup(restore)
    with open(path, 'ab') as source:
        source.write(b'\n# content-verified currency probe\n')


def format_codes(generated, expected):
    generated = re.sub(r'//.+?\n', '', generated)
    generated = generated.strip()
    generated = generated.replace('\t', '    ').strip()
    first_line = expected.split('\n')[1]
    spaces = len(first_line) - len(first_line.strip())
    column = '\n' + ' ' * spaces

    expected = expected.replace(column, '\n').strip()

    return generated, expected
