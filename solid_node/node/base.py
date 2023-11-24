import os
import sys
import time
import inspect
import logging
import importlib
import pyinotify
import trimesh
import numpy as np
from decimal import Decimal
from subprocess import Popen
from solid2 import (scad_render, import_scad, import_stl,
                    translate, rotate, union, color,
                    get_animation_time)
from .operations import Rotation, Translation


logger = logging.getLogger('node.base')


MESH_CACHE = {}

def _build_uniq_id(args, kwargs):
    all_args = list(args) + list(kwargs.values())
    return ','.join(str(a) for a in all_args)

class AbstractBaseNode:

    fn = None

    # The rendering colors
    color = None

    # This determines if stl can be generated for this Node
    rigid = True

    # All children nodes, initialized as tuple for compliance
    children = tuple()

    def __init__(self, *args, name=None, **kwargs):
        # self.uniq_id uniquely identifies a set of parameters of an instance.
        # self.name is used to refer to nodes in tests
        if not name:
            self.uniq_id = _build_uniq_id(args, kwargs)
            self.name = self.__class__.__name__
        else:
            self.name = name
            self.uniq_id = name

        # A list of rotations and translations to be applied to object
        # after rendering. Operations done this way will be applied after
        # optimization.
        self.operations = []

        # An index on self.operations to which the state can be restored to
        self.checkpoint = None

        # The source file for this Node is stored and used as
        # a base for scad and stl file paths
        self.src = self.get_source_file()

        build_dir = os.environ.get('SOLID_BUILD_DIR', "_build")

        self.basedir = os.path.dirname(self.src)

        self.build_dir = os.path.join(
            os.path.relpath(build_dir),
            os.path.relpath(self.basedir),
        )

        script = self.src.split('/')[-1]
        script = '.'.join(script.split('.')[:-1])  # remove extension
        basename = f'{script}-{self.uniq_id}' if self.uniq_id else script
        basepath = os.path.join(self.build_dir, basename)

        # The base scad file, and respective rendered stl,
        # without transformations, used for building and assembling
        # on parent node
        self.scad_file = f'{basepath}.scad'
        self.stl_file = f'{basepath}.stl'

        # A scad file and mesh with transformations applied,
        # used for mesh generation for spatial calculations, specially tests
        self.mesh_scad_file = f'{basepath}.mesh.scad'
        self.mesh_stl_file = f'{basepath}.mesh.stl'

        # Lock file for stl, for concurrency management (not implemented yet)
        self.lock_file = f'{basepath}.stl.lock'

        # Used to build a local path for importing relative stls
        self.local_stl = f'{basename}.stl'
        self.basepath = basepath

        # Track source of this node and all children
        self.files = set([self.src])

        # Holds the result of render()
        self.model = None

        self.root = self.basedir

        # Assembled is done only once
        self._assembled = False

        self._make_build_dirs()

    def get_source_file(self):
        return inspect.getfile(self.__class__)

    @property
    def time(self):
        raise NotImplementedError

    def assemble(self, root=None):
        """Renders this node and returns an optimized version
        with all operations applied"""
        if self._assembled:
            return self._assembled

        if root:
            self.root = root

        rendered = self.render()

        self.validate(rendered)
        self.model = self.as_scad(rendered)
        self.generate_scad()

        assembled = self.import_optimized()

        for operation in self.operations:
            # Apply scad operation
            assembled = operation.scad(assembled)

        self._assembled = assembled

        return assembled

    def import_optimized(self):
        if self.rigid and self._up_to_date(self.stl_file):
            basedir = os.path.relpath(self.basedir, self.root)
            local_stl = os.path.join(basedir, self.local_stl)
            return import_stl(local_stl)
        return self.model

    @property
    def stl(self):
        if not self.rigid:
            raise Exception(f'{self.name} is not rigid, cannot generate stl')
        if not self._up_to_date(self.stl_file):
            return
        return self.stl_file

    @property
    def mtime(self):
        """Maximum mtime in source file of all nodes rendered inside this one"""
        return max([
            os.path.getmtime(path)
            for path in self.files
        ])

    def render(self):
        raise NotImplementedError

    def as_scad(self, rendered):
        """Converts the output of render() to solid2 object"""
        raise NotImplementedError

    def as_number(self, n):
        if type(n) not in (int, float, Decimal):
            raise TypeError(f'{n} is not a number')
        return n

    @property
    def scad_code(self):
        code = scad_render(self.model)
        if self.fn:
            code = f'$fn = {self.fn};\n\n{code}'
        return code

    def generate_scad(self):
        open(self.scad_file, 'w').write(self.scad_code)
        os.utime(self.scad_file, (time.time(), self.mtime))
        logger.info(f"{self.scad_file} generated with {self.mtime}!")

    def trigger_stl(self):
        self.assemble()
        for child in self.children:
            child.trigger_stl()
        self.generate_stl()

    @property
    def _stl_generation_locked(self):
        try:
            fh = open(self.lock_file)
        except FileNotFoundError:
            return False

        try:
            pid = int(fh.read())
        except ValueError:
            return False

        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False

    def generate_stl(self):
        if self._up_to_date(self.stl_file) or \
           not self.rigid or \
           self._stl_generation_locked:
            return

        fh = open(self.lock_file, 'w')

        try:
            os.remove(self.stl_file)
        except FileNotFoundError:
            pass

        proc = Popen(self.stl_builder_command)

        fh.write(f'{proc.pid}')
        fh.close()

        raise StlRenderStart(proc, self.stl_file, self.mtime, self.lock_file)

    @property
    def stl_builder_command(self):
        return [
            'openscad', self.scad_file,
            '-o', self.stl_file,
            '--export-format', 'binstl',
        ]

    def generate_mesh(self):
        basedir = os.path.relpath(self.basedir, self.root)
        local_stl = os.path.join(basedir, self.local_stl)
        return import_stl(local_stl)

        return trimesh.load(self.stl_file)

    ##############################################
    # Transformations that can be applied to Node
    # model or mesh
    def rotate(self, angle, axis):
        self.operations.append(Rotation(angle, axis))
        return self

    def translate(self, translation):
        self.operations.append(Translation(self, translation))
        return self

    @property
    def mesh(self):
        mesh = trimesh.load(self.stl_file)
        for operation in self.operations:
            operation.mesh(mesh)
        return mesh

    def build_stls(node):
        while True:
            try:
                node.trigger_stl()
                return
            except StlRenderStart as job:
                job.wait()

    def save_checkpoint(self):
        """Sets a checkpoint on self.operations, so that state can
        be restored to that point"""
        self.checkpoint = len(self.operations)

    def restore_checkpoint(self):
        """Restore the state of self.operations, and return the
        discarded operations, in reverse order"""
        to_revert = self.operations[self.checkpoint:]
        self.operations = self.operations[:self.checkpoint]
        return reversed(to_revert)


    def _up_to_date(self, path):
        return (
            os.path.exists(path) and
            os.path.getmtime(path) == self.mtime
        )

    def _make_build_dirs(self):
        path = self.build_dir.split('/')
        build_dirs = []
        while path:
            build_dirs.append(path.pop(0))
            build_dir = '/'.join(build_dirs)
            if not os.path.exists(build_dir):
                os.mkdir(build_dir)


class StlRenderStart(Exception):

    def __init__(self, proc, stl_file, mtime, lock_file):
        super().__init__()
        self.proc = proc
        self.stl_file = stl_file
        self.mtime = mtime
        self.lock_file = lock_file

    def finish(self):
        os.utime(self.stl_file, (time.time(), self.mtime))
        logger.info(f"{self.stl_file} generated with {self.mtime}!")
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)

    def wait(self):
        logger.info(f"{self.scad_file} -> {self.stl_file} ...")
        self.proc.wait()
        self.finish()
