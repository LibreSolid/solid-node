import os
import sys
import time
import inspect
import importlib
import pyinotify
from subprocess import Popen
from solid2 import (scad_render, import_scad, import_stl,
                    translate, rotate, union, color,
                    get_animation_time)


class AbstractBaseNode:

    # The rendering colors
    color = None

    # All children nodes, initialized as tuple for compliance
    children = tuple()

    def __init__(self, *args, name=None):
        # Name uniquely identifies a set of parameters of an instance.
        if not name:
            name = ','.join([str(arg) for arg in args])

        # A list of rotations and translations to be applied to object
        # after rendering. Operations done this way will be applied after
        # optimization.
        self.operations = []

        # The source file for this Node is stored and used as
        # a base for scad and stl file paths
        self.src = inspect.getfile(self.__class__)

        build_dir = os.environ.get('SOLID_BUILD_DIR', "_build")

        self.basedir = os.path.dirname(self.src)

        self.build_dir = os.path.join(
            os.path.relpath(build_dir),
            os.path.relpath(self.basedir),
        )

        script = self.src.split('/')[-1][:-3]
        basename = f'{script}-{name}' if name else script
        basepath = os.path.join(self.build_dir, basename)

        self.scad_file = f'{basepath}.scad'
        self.stl_file = f'{basepath}.stl'
        self.lock_file = f'{basepath}.stl.lock'
        self.local_stl = f'{basename}.stl'

        # Track source of this node and all children
        self.files = set([self.src])


        # This determines if stl can be generated for this Node
        self.rigid = True

        # Holds the result of render()
        self.model = None

        self.root = self.basedir

        # Assembled is done only once
        self._assembled = False

        self._make_build_dirs()

    @property
    def time(self):
        raise NotImplementedError

    #####################################################
    # Transformations that can be applied to Node after
    # optimization
    def rotate(self, angle, axis):
        return self.transform(rotate(angle, axis))

    def translate(self, *argz):
        return self.transform(translate(*argz))

    def transform(self, operation):
        self.operations.append(operation)
        return self

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
            assembled = operation(assembled)

        self._assembled = assembled

        return assembled

    def import_optimized(self):
        if self.rigid and self._up_to_date(self.stl_file):
            basedir = os.path.relpath(self.basedir, self.root)
            local_stl = os.path.join(basedir, self.local_stl)
            return import_stl(local_stl)
        return self.model

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

    @property
    def scad_code(self):
        code = scad_render(self.model)
        return code

    def generate_scad(self):
        open(self.scad_file, 'w').write(self.scad_code)
        os.utime(self.scad_file, (time.time(), self.mtime))
        print(f"{self.scad_file} generated with {self.mtime}!")

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

        proc = Popen(['openscad', self.scad_file, '-o', self.stl_file])

        fh.write(f'{proc.pid}')
        fh.close()

        raise StlRenderStart(proc, self.stl_file, self.mtime, self.lock_file)

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
                try:
                    os.mkdir(build_dir)
                except:
                    import ipdb; ipdb.set_trace()
                    pass


class StlRenderStart(Exception):

    def __init__(self, proc, stl_file, mtime, lock_file):
        super().__init__()
        self.proc = proc
        self.stl_file = stl_file
        self.mtime = mtime
        self.lock_file = lock_file

    def finish(self):
        os.utime(self.stl_file, (time.time(), self.mtime))
        print(f"{self.stl_file} generated with {self.mtime}!")
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)

    def wait(self):
        print(f"{self.stl_file}")
        self.proc.wait()
        self.finish()
