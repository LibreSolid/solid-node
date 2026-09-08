# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import tempfile
import time
from solid2 import import_stl
from subprocess import CalledProcessError, Popen
from solid_node import currency
from solid_node.node.leaf import LeafNode
from solid_node.source_generation import current_phase


class JScadNode(LeafNode):
    """
    A JScad node. You just need to declare the property "jscad_source" with
    the path of your JScad source code. It must be placed in the same directory
    of the python file containing this node.

    You need to have jscad cli tool installed in $PATH, and node dependencies
    installed in the directory you are running solid from.
    """

    jscad_source = None

    def __init__(self, name=None):
        if not self.jscad_source:
            raise Exception('OpenJScadNode subclass must declare "jscad_source" '
                            'property with path with a valid OpenJScad js file')
        module = sys.modules[self.__class__.__module__]
        basedir = os.path.dirname(module.__file__)
        source_path = os.path.join(basedir, self.jscad_source)
        self.jscad_source = os.path.realpath(source_path)

        super().__init__(name=name)

    def get_source_file(self):
        return self.jscad_source

    def render(self):
        return self

    def as_scad(self, _):
        # An STL already produced from this jscad source needs no
        # second run of the external renderer.
        if self._up_to_date(self.stl_file):
            return import_stl(self.local_stl)

        directory = os.path.dirname(self.stl_file) or '.'
        os.makedirs(directory, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f'.{os.path.basename(self.stl_file)}.',
            suffix='.tmp', dir=directory)
        os.close(descriptor)
        # A zero-byte placeholder is not successful renderer output.  The
        # random name remains private under the project build lock.
        os.remove(temporary)
        try:
            cmd = [
                'jscad',
                self.jscad_source,
                '-o', temporary,
            ]
            print('\n' + ' '.join(cmd))
            proc = Popen(cmd)
            proc.communicate()
            if proc.returncode:
                raise CalledProcessError(proc.returncode, cmd)
            if not os.path.exists(temporary):
                return import_stl(self.local_stl)

            phase = current_phase()
            if phase is not None:
                # The foreign renderer consumed the JavaScript asynchronously
                # with respect to Python.  Certify its source epoch after it
                # completes and before its output replaces the prior artifact.
                phase.checkpoint(
                    (self.jscad_source,), label='jscad_render_post')
            os.utime(temporary, ns=(time.time_ns(), self.mtime_ns))
            currency.publish(temporary, self.stl_file, self.source_digest,
                             self.source_fingerprint)
        finally:
            try:
                os.remove(temporary)
            except FileNotFoundError:
                pass
        return import_stl(self.local_stl)
