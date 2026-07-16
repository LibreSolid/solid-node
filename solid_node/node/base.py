# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import re
import time
import inspect
import hashlib
import logging
import trimesh
from decimal import Decimal
from subprocess import Popen
from solid2 import scad_render, import_stl, color
from .operations import Rotation, Translation


logger = logging.getLogger('node.base')


# While an AssemblyNode render() runs it sits on this stack; every
# operation applied through rotate()/translate() in that window is
# kinematic, and gets tagged with the assembly driving it (operation
# ._driver) plus registered on that assembly's persistent
# _driven_nodes set. Before its next render, the assembly sweeps each
# driven node's operations, dropping only the ones IT tagged, so
# re-renders (one per test instant, assemble, the viewer) express
# absolute kinematics instead of accumulating -- even when a SECOND,
# independent assembly also drives the same node instance (e.g. a
# wheel spun by its axle and steered by the steering assembly): each
# driver only ever touches its own tagged operations, never the
# other's.
_render_stack = []


def _tag_driver(node, operation):
    if not _render_stack:
        # Not applied during a render (static placement in __init__,
        # a test perturbation poked directly into node.operations):
        # leave it untagged, so it is never swept.
        return
    assembly = _render_stack[-1]
    operation._driver = assembly
    if not hasattr(assembly, '_driven_nodes'):
        assembly._driven_nodes = set()
    assembly._driven_nodes.add(node)


# Filesystem-safe charset for the readable prefix: anything outside this
# set (spaces, brackets, quotes -- whatever str() on a list/dict produces)
# is replaced, so the prefix can never itself break a path component.
_UNSAFE_PREFIX_CHARS = re.compile(r'[^A-Za-z0-9_,=.-]')

# How much of the canonical serialization to keep in the readable prefix.
# Purely decorative (a glance-friendly hint); identity lives in the hash,
# so this bound is what keeps the basename length independent of
# parameter size (e.g. a 200-element float list kwarg).
_PREFIX_LEN = 60

# Hex digits of the sha256 kept in the artifact key. Short enough to stay
# out of the way, long enough that accidental collisions are not a
# practical concern for a single project's build tree.
_HASH_LEN = 12


def _canonical_serialization(args, kwargs):
    """The full, order-stable string identifying a call's parameters:
    positional args in call order, then kwargs sorted by key (so kwarg
    order never affects it), comma-joined. This is the string that is
    HASHED for identity; unlike the readable prefix derived from it,
    it is never truncated, so it still distinguishes calls that only
    differ deep inside a long value.
    """
    parts = [str(a) for a in args]
    parts += [f'{k}={v}' for k, v in sorted(kwargs.items())]
    return ','.join(parts)


def _build_uniq_id(args, kwargs):
    """The artifact key for a node instance: ALWAYS derived from its
    constructor parameters, never from name= (name only addresses the
    node in the tree/tests -- see AbstractBaseNode.__init__). A node
    built with no args/kwargs gets '' (the basename is then the bare
    script name, unchanged from before).

    Otherwise the key is:

        <readable-prefix>-<shorthash>

    where <shorthash> is the first _HASH_LEN hex digits of the sha256
    of _canonical_serialization(args, kwargs) -- the FULL serialization,
    so any parameter change (including one buried in a long value)
    changes the id -- and <readable-prefix> is that same serialization,
    sanitized to filesystem-safe characters and truncated to
    _PREFIX_LEN chars. The prefix is decoration only; identity lives
    entirely in the hash, so the total basename length is bounded
    regardless of parameter values (fixes the OSError: File name too
    long a long list-valued kwarg used to cause when it serialized
    verbatim into the filename).
    """
    canonical = _canonical_serialization(args, kwargs)
    if not canonical:
        return ''
    digest = hashlib.sha256(canonical.encode()).hexdigest()[:_HASH_LEN]
    prefix = _UNSAFE_PREFIX_CHARS.sub('_', canonical)[:_PREFIX_LEN]
    return f'{prefix}-{digest}'

class AbstractBaseNode:
    """A mechanical project in solid-node is represented by a
    tree, and this is the abstract base class for all nodes.
    Above this class, there are two other base classes:
    LeafNode and InternalNode.
    """

    fn = None

    # The rendering colors
    color = None

    # This determines if stl can be generated for this Node
    rigid = True

    # All children nodes, initialized as tuple for compliance
    children = tuple()

    # The internal node this node was assembled under, set by the
    # parent's as_scad(). Used to compose ancestor operations into
    # this node's mesh.
    _parent = None

    # Set to false to render scad directly instead of stls
    # Only works in openscad viewer
    optimize = True

    def __init__(self, *args, name=None, **kwargs):
        # self.uniq_id is the artifact key: always derived from this
        # instance's constructor parameters via _build_uniq_id, so a
        # parameter change always produces a new artifact. self.name is
        # purely for tree/test addressing and never influences uniq_id --
        # naming a node used to REPLACE its parameter-based key, so two
        # same-named instances with different parameters collided on one
        # stl file and one of them served the other's stale geometry.
        #
        # self._explicit_name records whether name= was actually passed,
        # so the parent-attribute-derived name (see _link_child below,
        # skill-repo improvements.md #16) only ever overrides the
        # class-name default -- never an explicit name=, which always
        # wins.
        self._explicit_name = name is not None
        self.name = name or self.__class__.__name__
        self.uniq_id = _build_uniq_id(args, kwargs)

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
        """Finds the source file of this node"""
        return inspect.getfile(self.__class__)

    @property
    def time(self):
        raise NotImplementedError

    def set_keyframe(self, time):
        """Set a fixed time for keyframes and tests.
        No-op for non-animated nodes; overridden by AssemblyNode."""
        pass

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
        if not self.optimize:
            self.model = self._colorize(self.model)
        self.generate_scad()

        if self.optimize:
            assembled = self.import_optimized()
        else:
            assembled = self.model

        for operation in self.operations:
            # Apply scad operation
            assembled = operation.scad(assembled)

        self._assembled = assembled

        return assembled

    def import_optimized(self):
        if self.rigid and self._up_to_date(self.stl_file):
            basedir = os.path.relpath(self.basedir, self.root)
            local_stl = os.path.join(basedir, self.local_stl)
            imported_stl = import_stl(local_stl)
            return self._colorize(imported_stl)
        return self._colorize(self.model)

    def _colorize(self, scad_code):
        if self.color is None:
            return scad_code
        hex_code = self.color.lstrip('#')
        if len(hex_code) != 6:
            raise ValueError(f"Invalid self.color at {self}. "
                             "It should be in the format #RRGGBB")
        colors = [int(hex_code[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        return color(colors, 1)(scad_code)

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
        logger.info('Triggering children')
        for child in self.children:
            child.trigger_stl()
        logger.info('Generating stl')
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
        except PermissionError:
            # No permission to signal the process, but it does exist.
            return True

    def generate_stl(self):
        if self._up_to_date(self.stl_file):
            return logger.info('STL up to date')
        if not self.rigid:
            return logger.info('Non rigid node, no STL to generate')
        if self._stl_generation_locked:
            return logger.info('Cannot generate, locked')

        fh = open(self.lock_file, 'w')

        try:
            os.remove(self.stl_file)
        except FileNotFoundError:
            pass

        proc = Popen(self.stl_builder_command)

        fh.write(f'{proc.pid}')
        fh.close()
        logger.info(f'Job started with pid {proc.pid}')
        raise StlRenderStart(proc, self.stl_file, self.mtime, self.lock_file)

    @property
    def stl_builder_command(self):
        return [
            'openscad', self.scad_file,
            '-o', self.stl_file,
            '--export-format', 'binstl',
        ]

    ##############################################
    # Child naming (skill-repo improvements.md #16)
    #
    # Two children of the same class under one parent used to collide
    # in the viewer's name-addressed tree, because node.name defaulted
    # to the class name for every instance. The fix: a child's name is
    # derived from the attribute name the PARENT instance holds it
    # under -- introspected off the parent's __dict__ -- unless an
    # explicit name= was given (that always wins) or the child cannot
    # be found in the parent's __dict__ at all (then it just keeps its
    # current name, the class-name default).
    def _link_child(self, child):
        """Link `child` to this node as its parent, and derive its
        name from the attribute holding it. Called from the same spot
        the tree links parent/child today (InternalNode.as_scad) and
        from the web viewer's NodeAPI, which walks render() output
        directly without a full assemble(). Idempotent: re-deriving
        the same attribute mapping twice (e.g. a second assemble())
        always recomputes the identical name -- it overwrites rather
        than appends, so nothing stacks."""
        child._parent = self
        if child._explicit_name:
            return
        found = self._attr_name_for(child)
        if found is not None:
            child.name = found

    def _attr_name_for(self, child):
        """The attribute name (or `<attr>-<index>` for a list/tuple
        member) under which `self.__dict__` holds `child`, scanned in
        definition order. A plain attribute is always preferred over a
        list/tuple membership, even if the list hit comes first in
        definition order (two passes, not one). Private attributes
        (leading underscore) are skipped. Returns None if `child`
        isn't referenced by any (non-private) attribute at all."""
        for attr, value in self.__dict__.items():
            if attr.startswith('_'):
                continue
            if value is child:
                return attr
        for attr, value in self.__dict__.items():
            if attr.startswith('_'):
                continue
            if isinstance(value, (list, tuple)):
                for index, item in enumerate(value):
                    if item is child:
                        return f'{attr}-{index}'
        return None

    ##############################################
    # Transformations that can be applied to Node
    # model or mesh
    def rotate(self, angle, axis):
        operation = Rotation(angle, axis, self)
        self.operations.append(operation)
        _tag_driver(self, operation)
        return self

    def translate(self, translation):
        operation = Translation(translation, self)
        self.operations.append(operation)
        _tag_driver(self, operation)
        return self

    @property
    def mesh(self):
        """The node's mesh in WORLD coordinates: its own operations
        applied first, then each ancestor's, up the assembled tree —
        the same composition the viewer renders."""
        mesh = trimesh.load(self.stl_file)
        node = self
        while node is not None:
            for operation in node.operations:
                operation.mesh(mesh)
            node = getattr(node, '_parent', None)
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
                try:
                    os.mkdir(build_dir)
                except FileExistsError:
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
        logger.info(f"{self.stl_file} generated with {self.mtime}!")
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)

    def wait(self):
        logger.info(f"waiting for {self.stl_file} ...")
        self.proc.wait()
        logger.info(f"{self.stl_file} done!")
        self.finish()
