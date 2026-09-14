# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

import os
import io
import re
import time
import inspect
import hashlib
import logging
import tempfile
import numpy as np
from decimal import Decimal
from subprocess import CalledProcessError, Popen
from solid2 import scad_render, import_stl, color
from solid_node import currency
from solid_node._artifact import (ArtifactChanged, ArtifactSnapshot,
                                  artifact_cache_key)
from solid_node.openscad import require_openscad
from solid_node.source_generation import (
    current_census, current_generation, current_phase, track_sources,
)
from .sources import source_closure, source_scope
from . import phase as _phase
from .declarative import (ChildDeclaration, NodeMeta, StructureError,
                          identity_values, in_class_body, is_declarative,
                          realize_children, resolve_parameters)


logger = logging.getLogger('node.base')


def _seconds(mtime_ns):
    """Integer nanoseconds as the float `os.stat().st_mtime` would report.

    Not `mtime_ns / 1e9`: at the current epoch that integer is past 2**53,
    so converting it to a double before dividing rounds to a different
    last bit than the OS does for 27% of timestamps. CPython builds
    st_mtime as `sec + 1e-9 * nsec`, and the published viewer document
    records this value -- so it is computed the same way here, and stays
    bit-identical to what every existing reader has always seen.
    """
    seconds, nanoseconds = divmod(mtime_ns, 10 ** 9)
    return seconds + nanoseconds * 1e-9


def _atomic_write_text(path, content, mtime_ns, digest=None, fingerprint=None):
    desired = content.encode()
    try:
        with ArtifactSnapshot(path) as existing:
            unchanged = existing.read_bytes() == desired
            existing_mtime_ns = existing.observation.mtime_ns
    except (ArtifactChanged, OSError):
        unchanged = False
        existing_mtime_ns = None

    if unchanged:
        if existing_mtime_ns != mtime_ns:
            currency.restamp(path, mtime_ns)
        currency.record(path, digest, fingerprint)
        return

    directory = os.path.dirname(path) or '.'
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f'.{os.path.basename(path)}.', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(desired)
        os.utime(temporary, ns=(time.time_ns(), mtime_ns))
        currency.publish(temporary, path, digest, fingerprint)
    except Exception:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise


def _publish_scad(path, content, mtime_ns, digest, fingerprint):
    """Publish one captured SCAD state and update process-local currentness."""
    _atomic_write_text(path, content, mtime_ns, digest, fingerprint)
    generation = current_generation()
    if generation is not None:
        generation.remember_scad_artifact(
            path, (mtime_ns, digest, fingerprint))
    logger.info('%s generated with %s!', path, _seconds(mtime_ns))


def _atomic_write_bytes(path, content, mtime_ns, digest=None,
                        fingerprint=None, recipe=None):
    """`_atomic_write_text` for a binary artifact.

    Same contract, and it matters for the same reason: the stamp is
    applied before the rename, so the file at `path` is never a
    half-written mesh and never carries a build-time mtime that would
    make it look newer than the source it came from.
    """
    directory = os.path.dirname(path) or '.'
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f'.{os.path.basename(path)}.', suffix='.tmp', dir=directory)
    try:
        with os.fdopen(descriptor, 'wb') as output:
            output.write(content)
        os.utime(temporary, ns=(time.time_ns(), mtime_ns))
        currency.publish(temporary, path, digest, fingerprint, recipe)
    except Exception:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise


# Module-level cache of loaded base meshes (no operations applied),
# keyed on the STL's complete observable filesystem identity --
# skill-repo docs/performance-improvement.md
# fix 1. Before this cache, AbstractBaseNode.mesh called trimesh.load()
# on EVERY access; a single real STL can take over a second to load
# (the v8-engine camshaft, 660k faces), and a test suite hits `.mesh`
# thousands of times. Keying on mtime (not just path) means a rebuilt
# STL is picked up automatically -- and any stale entry under the
# file's old strong observation is evicted on the next access under its new
# one, so even same-size content replacement with a restored mtime cannot
# reuse stale geometry and a rebuild loop cannot accumulate stale entries.
_base_mesh_cache = {}


# trimesh costs 0.64 s to import and cached_base_mesh below is the only
# thing in this module that reads a mesh, so the library is imported on
# first use rather than at module scope: every command that merely
# touches a node module used to pay for a mesh library it never asked a
# question of. It stays a REQUIRED dependency -- a missing one raises
# ImportError here, uncaught and unsubstituted, at the point of use.
#
# The resolution is published into globals() so the name behaves exactly
# as the module-scope import made it behave: one shared binding, readable
# as `solid_node.node.base.trimesh`, which is the target
# tests/test_node_mesh_cache.py patches to count disk loads. Reading the
# global first (rather than re-importing) is what preserves that -- a
# caller that replaces the binding keeps its replacement.
def _mesh_library():
    """The mesh library, imported on first use and shared thereafter."""
    try:
        return globals()['trimesh']
    except KeyError:
        import trimesh
        globals()['trimesh'] = trimesh
        return trimesh


def __getattr__(name):
    """Resolve the deferred `trimesh` binding on attribute access (PEP
    562), so reading `solid_node.node.base.trimesh` works in a process
    that has not yet loaded a mesh. Without it the deferral would break
    every by-name reference to the module's mesh library, patching
    included, in exactly the runs that never call cached_base_mesh
    first."""
    if name == 'trimesh':
        return _mesh_library()
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def cached_base_mesh(stl_file, observation=None):
    """The node's immutable base mesh (STL geometry, no operations
    applied), loaded once per strong artifact observation and shared across
    every caller. Returns the cached object itself -- callers that need a
    mutable copy (AbstractBaseNode.mesh) must .copy() it; callers that
    only read it (e.g. the AABB broad-phase's local .bounds) can use it
    directly. ``observation`` lets a higher cache require the decode to come
    from exactly the identity that keyed its own miss; a mismatch raises
    rather than storing mixed geometry under the earlier identity."""
    key = (os.fspath(stl_file), observation) if observation is not None \
        else artifact_cache_key(stl_file)
    cached = _base_mesh_cache.get(key)
    if cached is None:
        for stale_key in [k for k in _base_mesh_cache if k[0] == stl_file]:
            del _base_mesh_cache[stale_key]
        # The cache identity and decoded geometry must describe one open file,
        # not two resolutions of a path an atomic publisher can replace.
        with ArtifactSnapshot(stl_file) as snapshot:
            if snapshot.observation != key[1]:
                raise ArtifactChanged(
                    f'Artifact changed before mesh decode: {stl_file}')
            cached = _mesh_library().load(
                io.BytesIO(snapshot.read_bytes()), file_type='stl')
            snapshot.validate()
        _base_mesh_cache[key] = cached
    return cached


def _compose_matrix(node, stop_before):
    """Compose operations until ``stop_before(current)`` is true.

    Computed fresh on EVERY call, never cached: operation values can be
    solid2 animated expressions that change with the keyframe
    (Rotation/Translation.matrix() resolves them via as_number() at
    access time), and node.operations can be mutated in place (the
    perturbation assertions in solid_node/test.py insert an operation
    and remove it in a finally) -- a cached matrix would silently miss
    both.
    """
    matrix = np.eye(4)
    current = node
    while current is not None and not stop_before(current):
        for operation in current.operations:
            matrix = operation.matrix() @ matrix
        current = getattr(current, '_parent', None)
    return matrix


def _compose_world_matrix(node):
    """The node's placement in WORLD coordinates: its own operations
    then each ancestor's, walking node -> parent -> ... -- the same
    composition the shared viewer applies, so mesh and viewer placement
    share one semantics (ADR-028). Later operations are outermost (each
    op's matrix is premultiplied onto the running total).

    This is the right frame for COLLISION: whether two separately
    placed parts clash is a world-framed, time-dependent question. It
    is the wrong frame for connectivity -- see _compose_solid_matrix.
    """
    return _compose_matrix(node, lambda current: False)


def _topmost_rigid_ancestor(node):
    """Return the rigid root of the solid containing ``node``: walk up
    while the parent is rigid, so the result is the node whose STL is
    the whole printed part. A node directly under an assembly is its
    own solid."""
    current = node
    while True:
        parent = getattr(current, '_parent', None)
        if parent is None or not parent.rigid:
            return current
        current = parent


def _topmost_rigid_nodes(node):
    """Yield each printed solid below ``node``.

    A rigid node is already the complete printed solid for its branch, so the
    walk stops there rather than inspecting its rigid ingredients.
    """
    if node.rigid:
        yield node
        return
    for child in node.children:
        yield from _topmost_rigid_nodes(child)


def _enclosing_solid(node):
    """The topmost rigid ancestor of an ASSEMBLED node, or None when
    the node is not linked into a tree at all.

    The distinction matters for the same-solid guard in assertJoined:
    two unlinked nodes (mesh-only test doubles, or geometry examined
    before assemble()) are not evidence of two different parts, while
    two linked nodes resolving to different solids are.
    """
    if getattr(node, '_parent', None) is None:
        return None
    return _topmost_rigid_ancestor(node)


def _compose_solid_matrix(node):
    """The node's placement WITHIN its enclosing solid: operations
    below the topmost rigid ancestor only, stopping before that node's
    own operations, which are pose of the whole body.

    This is the right frame for CONNECTIVITY: whether two features of
    one part meet is local and timeless, invariant under the rigid
    placement an assembly applies to the part as a whole. Composing no
    further also means no animated ancestor operation is ever resolved,
    so the question has the same answer at every instant.
    """
    solid = _topmost_rigid_ancestor(node)
    return _compose_matrix(node, lambda current: current is solid)


# While an AssemblyNode lifecycle method runs, the phase stack
# (solid_node.node.phase) says which one. An operation applied through
# rotate()/translate() during simulate() is MOTION: it goes at the head
# of the node's operations, before every rest placement, so the part
# moves in its own frame and is then carried by its placement; it is
# tagged with the assembly simulating it (operation._animator) and that
# assembly is registered on the node in its persistent _animated_nodes
# set, so before its next simulate() the assembly sweeps each animated
# node's operations, dropping only the ones IT tagged. Poses are
# absolute per instant instead of accumulating -- even when a SECOND,
# independent assembly also simulates the same node instance (a wheel
# spun by its axle and steered by the steering assembly): each animator
# only ever touches its own tagged operations, never the other's.
#
# The motion block itself has TWO parts, and they are ordered by what
# the class says rather than by what ran first (ADR-093):
#
#     [ joint 1 ][ joint 2 ] ... [ hand-written, in call order ][ rest ]
#
# innermost on the left. Joint n is the n-th joint DECLARED on the
# node's class -- `declared_joints` order, base classes before the
# subclass, a redeclaration keeping the base's position -- and it goes
# in at its own slot through `apply_joint_motion`, as one contiguous
# run, however many operations its placement produced and whatever
# order the coordinates were bound in. Hand-written motion goes to the
# end of the whole motion block through `_insert_motion`, so it lands
# outside every joint and keeps its call order among itself.
#
# Why: when both joints of a body are bound by relations, the order
# they were APPLIED in is the couplings solver's pass order, a property
# of where the relations were written and not of the class carrying the
# joints. A reader of the class body could not see it, a derived
# coordinate could silently change it, and a sweep and re-bind could
# reverse it between two runs. Declaration order is visible, stable
# across runs, and independent of which assembly animates which joint.
#
# An operation applied during render() is appended and tagged too, and
# the lifecycle wrapper decides what it was once the render returns: a
# render that read no driver is rest placement, run once, and its
# operations are untagged so they persist; a render that read one is a
# legacy render, re-run and swept per binding as it always was. An
# operation applied outside any phase (placement in __init__, a test
# perturbation poked into node.operations) is untagged and never swept.
#
# The tag is named for ANIMATION, not for driving: ADR-056 reserves
# "driver" for a simulation input bound through set_state, and one word
# cannot mean both without misleading every later reader.
_render_stack = _phase._stack


def _insert_motion(node, operation):
    """Put `operation` at the end of the node's motion block: after the
    motion already applied, before every rest operation, so the part
    moves in its own frame and is then carried by its placement, and so
    successive calls keep their call order at the head of the list.

    This is the HAND-WRITTEN motion path. Joints have their own seam --
    `apply_joint_motion`, which inserts by declaration slot at the head
    of the motion block -- so a hand-written rotate()/translate() lands
    at the end of the whole motion block and therefore OUTSIDE the joint
    block, whichever was applied first."""
    operation._motion = True
    index = 0
    for existing in node.operations:
        if not getattr(existing, '_motion', False):
            break
        index += 1
    node.operations.insert(index, operation)


def _tag_operation(node, operation, phase):
    assembly = phase.assembly
    operation._animator = assembly
    if not hasattr(assembly, '_animated_nodes'):
        assembly._animated_nodes = set()
    assembly._animated_nodes.add(node)
    phase.applied.append(operation)


def _place_operation(node, operation):
    phase = _phase.current()
    if phase is None:
        node.operations.append(operation)
        return
    if phase.kind == _phase.SIMULATE:
        _insert_motion(node, operation)
    else:
        node.operations.append(operation)
    _tag_operation(node, operation, phase)


def apply_joint_motion(node, operations, slot):
    """Place a joint's `operations` on `node` as one contiguous run of
    MOTION at the position its declaration `slot` dictates, whatever
    phase is current, and return them. The joint seam, and nothing
    else's.

    `_place_operation` appends when no lifecycle phase is running, which
    is right for a placement stated in the parent's frame and wrong for
    a joint: a joint's axis and anchor were carried into the node's own
    frame, so an operation appended after the rest placement would be
    read in the parent's frame instead -- a body turned about the wrong
    line, silently. A joint therefore never goes through the plain
    rotate()/translate() path.

    `slot` is the joint's index in `declared_joints(type(node))`, and it
    is what decides WHERE the run goes: the insertion index is the
    length of the prefix of `node.operations` whose entries are motion,
    carry a `_joint_slot`, and whose slot is <= this one. Equivalently:
    after every joint of an earlier-or-equal slot, before the first
    joint of a later slot, before every hand-written motion, before
    every rest operation. So the composition a reader sees is the
    DECLARATION order of the class -- first declared innermost -- and
    not the order the coordinates happened to be bound in, which for a
    relation-bound joint is the couplings solver's pass order and is
    invisible in the class body (ADR-093).

    The run is inserted at ONE index rather than one operation at a
    time, so contiguity is an invariant this seam enforces instead of
    one every caller has to preserve: a `Revolute` at an off-origin
    anchor emits three operations and they are one unit at one slot.

    The scan is tolerant of a missing operation in exactly the way
    `Joint.clear` is: an operation a sweep or a checkpoint restore has
    dropped is simply not there.

    Under a simulate phase nothing else changes: each operation is
    tagged with the simulating assembly and swept before its next run,
    exactly as a hand-written rotation there is. Outside any phase they
    are marked as motion but untagged, so no sweep touches them and
    re-binding the joint is what keeps it absolute.
    """
    index = 0
    for existing in node.operations:
        if not getattr(existing, '_motion', False):
            break
        existing_slot = getattr(existing, '_joint_slot', None)
        if existing_slot is None or existing_slot > slot:
            break
        index += 1
    phase = _phase.current()
    for offset, operation in enumerate(operations):
        operation._motion = True
        operation._joint_slot = slot
        node.operations.insert(index + offset, operation)
        if phase is not None:
            _tag_operation(node, operation, phase)
    return operations


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


def _canonical_serialization(klass, args, kwargs):
    """The full, order-stable string identifying a call's identity:
    the node class's __qualname__ (skill-repo improvements.md #22),
    then positional args in call order, then kwargs sorted by key (so
    kwarg order never affects it), comma-joined. This is the string
    that is HASHED for identity; unlike the readable prefix derived
    from it, it is never truncated, so it still distinguishes calls
    that only differ deep inside a long value.

    Leading with the class is what makes two DIFFERENT node classes,
    called with identical (possibly empty) args/kwargs, get distinct
    ids -- before #22 identity was args/kwargs only, so two different
    no-arg classes defined in the same file both got the empty
    canonical serialization and silently shared the bare-script-name
    artifact (one served the other's stale geometry).
    """
    parts = [klass.__qualname__]
    parts += [str(a) for a in args]
    parts += [f'{k}={v}' for k, v in sorted(kwargs.items())]
    return ','.join(parts)


def _build_uniq_id(klass, args, kwargs):
    """The artifact key for a node instance: ALWAYS derived from its
    class plus its constructor parameters, never from name= (name
    only addresses the node in the tree/tests -- see
    AbstractBaseNode.__init__). The class is always present in the
    canonical serialization (see _canonical_serialization), so the
    key is never empty -- even a no-arg node gets one, keyed off its
    class.

    The key is:

        <readable-prefix>-<shorthash>

    where <shorthash> is the first _HASH_LEN hex digits of the sha256
    of _canonical_serialization(klass, args, kwargs) -- the FULL
    serialization, so any parameter change (including one buried in a
    long value) or a different class changes the id -- and
    <readable-prefix> is that same serialization, sanitized to
    filesystem-safe characters and truncated to _PREFIX_LEN chars. The
    prefix is decoration only; identity lives entirely in the hash, so
    the total basename length is bounded regardless of parameter
    values (fixes the OSError: File name too long a long list-valued
    kwarg used to cause when it serialized verbatim into the
    filename).
    """
    canonical = _canonical_serialization(klass, args, kwargs)
    digest = hashlib.sha256(canonical.encode()).hexdigest()[:_HASH_LEN]
    prefix = _UNSAFE_PREFIX_CHARS.sub('_', canonical)[:_PREFIX_LEN]
    return f'{prefix}-{digest}'


def binding_hash(values):
    """The artifact key of one parameter binding, beside `_build_uniq_id`.

    A flexible leaf's geometry is a function of its bound ports, so a
    snapshot of it is addressed by those values as well as by the node
    that rendered it. `uniq_id` stays structural -- a continuously
    varying value must never mint a new node identity (ADR-026) -- and
    this key is what makes a changed binding a DIFFERENT file rather
    than a rewrite of one whose mtime already says it is current.

    Names are sorted and values serialized through repr, so the key
    depends on the binding and not on the order it was collected in, and
    two floats that print alike but are not equal still key apart.
    """
    canonical = ','.join(f'{name}={value!r}'
                         for name, value in sorted(values.items()))
    return hashlib.sha256(canonical.encode()).hexdigest()[:_HASH_LEN]


class AbstractBaseNode(metaclass=NodeMeta):
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

    # Whether this node's geometry is a function of its bound ports
    # rather than a solid it can hand over. Fixed by type beside `rigid`,
    # and for the same reason: it says what KIND of thing the node is,
    # which is what the serialized document publishes it as. Only
    # `FlexibleNode` sets it (see solid_node/node/flexible.py).
    flexible = False

    # All children nodes, initialized as tuple for compliance
    children = tuple()

    # The internal node this node was assembled under, set by the
    # parent's as_scad(). Used to compose ancestor operations into
    # this node's mesh.
    _parent = None

    # Set to false to present this node's SCAD directly instead of importing
    # its optimized STL.
    optimize = True

    # Whether the render in progress left this node out of the machine.
    # Set by omit(), cleared by the parent's render before it runs.
    _omitted = False

    def __new__(cls, *args, **kwargs):
        # A call in a node class body is a declaration, never an
        # instance: a class attribute is one object shared by every
        # parent instance, so building the node here would give eight
        # cylinder units one piston. Returning something that is not an
        # instance of `cls` also makes Python skip __init__, which is
        # exactly right -- the declaration is realized, per parent, when
        # the parent is constructed (see declarative.realize_children).
        if in_class_body():
            return ChildDeclaration(cls, args, kwargs)
        return super().__new__(cls)

    def __init__(self, *args, name=None, **kwargs):
        # self.uniq_id is the artifact key: always derived from this
        # instance's CLASS plus its constructor parameters via
        # _build_uniq_id (skill-repo improvements.md #22 adds the
        # class; #3/#13 established parameters), so a parameter change
        # -- or building a different class -- always produces a new
        # artifact. self.name is purely for tree/test addressing and
        # never influences uniq_id -- naming a node used to REPLACE its
        # parameter-based key, so two same-named instances with
        # different parameters collided on one stl file and one of
        # them served the other's stale geometry.
        #
        # self._explicit_name records whether name= was actually passed,
        # so the parent-attribute-derived name (see _link_child below,
        # skill-repo improvements.md #16) only ever overrides the
        # class-name default -- never an explicit name=, which always
        # wins.
        self._explicit_name = name is not None
        self.name = name or self.__class__.__name__
        declarative = is_declarative(type(self))
        if declarative:
            # Declaration order is a reading order, not a call order.
            if args:
                raise TypeError(
                    f'{type(self).__name__} takes no positional arguments: '
                    f'its parameters are declared, pass them by name')
            # Every declared parameter resolved -- coerced, checked,
            # derived -- before anything else reads one. The private key
            # keeps _attr_name_for's scan of __dict__ seeing what it saw.
            self.__dict__['_parameters'] = resolve_parameters(
                type(self), kwargs)
            # The author's guards over several parameters at once, now
            # that each reads as a plain value and before anything is
            # built or realized on their strength.
            self.check()
            # Identity is the class plus the resolved declared values:
            # the same function and the same serialization the
            # constructor form hashes, fed the COMPLETE map rather than
            # whatever an author remembered to forward.
            self.uniq_id = _build_uniq_id(
                self.__class__, (),
                identity_values(type(self), self.__dict__['_parameters']))
        else:
            self.uniq_id = _build_uniq_id(self.__class__, args, kwargs)

        # Where this node may move, resolved against this instance:
        # after its parameters and its check(), and before any child is
        # realized (below), so a joint argument that cannot resolve
        # names the class, the joint and the argument at the earliest
        # point a value could be wrong and a refused instance has built
        # nothing. Imported here rather than at module scope:
        # solid_node.motion.joints imports solid_node.motion.ports,
        # which imports this package.
        from solid_node.motion.joints import resolve_declared_joints
        resolve_declared_joints(self)

        # A list of rotations and translations to be applied to object
        # after rendering. Operations done this way will be applied after
        # optimization.
        self.operations = []

        # An index on self.operations to which the state can be restored to
        self.checkpoint = None

        # The source file for this Node is stored and used as
        # a base for scad and stl file paths
        self.src = self.get_source_file()

        # Local import avoids the loader -> node.base import cycle, the same
        # way sources.py reaches project discovery.
        from solid_node.core.builder import get_build_dir
        from solid_node.core.loader import project_root

        self.basedir = os.path.dirname(self.src)

        # Artifacts mirror the project's source tree inside the one project
        # build directory. Both halves anchor on the project root, never on
        # the working directory: a node's artifact path must not depend on
        # the directory the command happened to run from, or a build from a
        # subdirectory publishes a second, private tree.
        root = self._project_root = project_root(self.src)
        self.build_dir = os.path.normpath(os.path.join(
            get_build_dir(self.src),
            os.path.relpath(self.basedir, root),
        ))

        script = self.src.split('/')[-1]
        script = '.'.join(script.split('.')[:-1])  # remove extension
        # uniq_id is never empty (it always includes the class -- see
        # _build_uniq_id), so basename always carries it.
        basename = f'{script}-{self.uniq_id}'
        basepath = os.path.join(self.build_dir, basename)

        # The base scad file, and respective rendered stl,
        # without transformations, used for building and assembling
        # on parent node
        self.scad_file = f'{basepath}.scad'
        self.stl_file = f'{basepath}.stl'
        self.brep_file = f'{basepath}.brep'

        # A scad file and mesh with transformations applied,
        # used for mesh generation for spatial calculations, specially tests
        self.mesh_scad_file = f'{basepath}.mesh.scad'
        self.mesh_stl_file = f'{basepath}.mesh.stl'

        # Lock file for stl, for concurrency management (not implemented yet)
        self.lock_file = f'{basepath}.stl.lock'

        # Used to build a local path for importing relative stls
        self.local_stl = f'{basename}.stl'
        self.basepath = basepath

        # Track source of this node and all children. The node's own
        # source is not the whole story: a module it imports for its
        # dimensions decides its geometry just as much, so the set is
        # the project-local import closure (see sources.py). Internal
        # nodes union in their children's sets while assembling.
        self.files = source_closure(self.src)

        # What this node can see of its own file, for the content-verified
        # digest: its own class, so siblings defined in the same file do
        # not invalidate it when they change. Internal nodes union in
        # their children's scopes beside their files.
        self.scope = source_scope(self.src, self.__class__)

        # Holds the result of render()
        self.model = None

        # Native preparation is independent of SCAD presentation.  The
        # rendered value belongs to this instance only; artifact currency is
        # still on disk and no prepared tree is shared globally.
        self._prepared = False
        self._prepared_rendered = None

        self.root = self.basedir

        # Assembled is done only once
        self._assembled = False

        self._make_build_dirs()

        # Last, so a child is constructed by a parent that already knows
        # its own name, source and artifact paths -- the reverse of the
        # constructor form, where children are built before super().
        if declarative:
            realize_children(self)

        # Every relation this class states, resolved against this
        # instance, and every law= callable called once -- at the END of
        # construction, after the children are realized, because an end
        # may be a child or a descendant of one. Imported here for the
        # reason the joints import is: solid_node.motion.couplings
        # imports solid_node.motion.ports, which imports this package.
        from solid_node.motion.couplings import resolve_declared_relations
        resolve_declared_relations(self)

    def check(self):
        """Refuse this instance by raising.

        Called by the framework on a declarative node once its
        parameters are resolved and before any child is realized, so a
        guard over several parameters at once -- `stop` must exceed
        `stem` -- has one place to live and a refused root builds no
        subtree. The base does nothing, so `super().check()` chains.
        A class that declares nothing is not called: its attributes do
        not exist yet when this constructor runs.
        """

    def omit(self):
        """Leave this node out of the machine.

        Called from the parent's render() on a declared child: the part
        is not linked, built, exported, fused or serialized -- a
        different mass, a different BOM, absent from a fused solid.
        Structure is decided at rest: a once-only render() decides it
        for the instance, a legacy render clears the mark before it
        runs and records what was omitted, and simulate() -- which only
        moves -- may not call this at all. Structure may vary with
        parameters, never with time.
        """
        phase = _phase.current()
        if phase is not None and phase.kind == _phase.SIMULATE:
            owner = phase.assembly
            raise StructureError(
                f"{type(owner).__name__} '{owner.name}' called omit() on "
                f"'{self.name}' in simulate(): structure is decided at "
                f"rest, in render(); simulate() only moves.")
        self._omitted = True

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

    def clear_keyframe(self):
        """Drop a fixed time, returning to symbolic animation time.
        No-op for non-animated nodes; overridden by AssemblyNode."""
        pass

    def set_state(self, **states):
        """Bind named driver values for this instant.
        No-op for non-animated nodes; overridden by AssemblyNode.

        The no-op is what lets an assembly propagate a snapshot into
        whatever its render() returned without asking what each child
        is -- the same tolerance set_keyframe has always had."""
        pass

    def clear_state(self, *names):
        """Drop bound driver values, all of them when given no names.
        No-op for non-animated nodes; overridden by AssemblyNode."""
        pass

    def _receive_state(self, entries, path, declared, saved,
                       coordinates=None):
        """This node's share of a set_state propagation.
        No-op for non-animated nodes; overridden by AssemblyNode --
        except that under a RUNNING root an entry addressed to a leaf's
        own joint coordinate binds it, because a joint may be declared
        on a leaf and the run owns every joint coordinate of the tree
        (OpenSpec change ``run-owns-the-coordinates``). The delivery
        object is the assembly layer's; this node only hands itself to
        it, so nothing about the motion layer is imported here."""
        if coordinates is not None:
            coordinates.deliver(self, entries, path, declared)

    def _receive_clear(self, names):
        """This node's share of a clear_state propagation.
        No-op for non-animated nodes; overridden by AssemblyNode."""
        pass

    def assemble(self, root=None):
        """Renders this node and returns an optimized version
        with all operations applied"""
        if self._assembled:
            return self._assembled

        self._prepare(root)

        if self.optimize and self.rigid and self._up_to_date(self.stl_file):
            # Everything below would recompute an artifact that is
            # already on disk and already current. import_optimized()
            # imports it instead; self.model stays unset and is
            # rendered lazily if something actually asks for the scad.
            if self.model is None:
                self.model = import_stl(self.local_stl)
            self.generate_scad()
            assembled = self.import_optimized()
        else:
            rendered = self._require_rendered()
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

    def _prepare(self, root=None):
        """Prepare native structure and geometry without presenting SCAD."""
        track_sources(self.files)
        if root:
            self.root = root
        if self._prepared:
            return self
        if not self._prepare_can_be_skipped():
            rendered = self.render()
            self.validate(rendered)
            self._prepared_rendered = rendered
            if self._uses_legacy_scad_materialization():
                # A project adapter that overrides the established SCAD hook
                # is an explicit request to keep using that artifact path.
                # Preserve it without making SCAD the path for native leaves.
                self.model = self.as_scad(rendered)
                self.generate_scad()
            else:
                self.materialize(rendered)
        self._prepared = True
        return self

    def _require_rendered(self):
        if self._prepared_rendered is None:
            rendered = self.render()
            self.validate(rendered)
            self._prepared_rendered = rendered
        return self._prepared_rendered

    def materialize(self, rendered):
        """Produce backend-owned artifacts from one validated render."""

    def _prepare_can_be_skipped(self):
        return False

    def _uses_legacy_scad_materialization(self):
        return False

    def _render_can_be_skipped(self):
        """Whether assemble() can import this node's artifact instead of
        producing it. False here: an internal node's file set is the
        union of its children's, and it only learns that by walking them
        (see InternalNode.as_scad), so it cannot know whether it is
        current without doing the very work the answer would skip. A
        leaf can -- its set is known at construction. LeafNode overrides.
        """
        return False

    def _require_model(self):
        """This node's own geometry as scad.

        A leaf whose artifact was already current never rendered, so
        self.model is unset. Nothing in the build path needs it -- the
        parent imports the STL -- but a caller that genuinely wants the
        scad gets it rendered on demand rather than getting None.
        """
        if self.model is None:
            self._prepare()
            rendered = self._require_rendered()
            self.model = self.as_scad(rendered)
            if not self.optimize:
                self.model = self._colorize(self.model)
        return self.model

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
    def mtime_ns(self):
        """Maximum mtime in source file of all nodes rendered inside this
        one, as integer nanoseconds.

        This is the value the build stamps onto artifacts and compares
        them against. It is an int, not a float, and that is the whole
        point: a float timestamp cannot survive the round trip through
        os.utime, which floors it to a timespec a nanosecond or two low.
        A nanosecond filesystem stores those low bits harmlessly, but a
        coarser one truncates them across a quantum boundary about half
        the time and a whole quantum disappears -- so the artifact lands
        below the stamp it was given and never reports current again
        (ADR-006). An integer read from the filesystem and written back
        unchanged is a fixed point at any resolution.
        """
        census = current_census()
        if census is not None:
            return max(census[path].mtime_ns for path in self.files)
        return max(os.stat(path).st_mtime_ns for path in self.files)

    @property
    def source_digest(self):
        """What this node's tracked sources say, as one digest.

        Computed over exactly the set `mtime_ns` is the maximum of, so it
        answers precisely the question the timestamp was standing in for:
        would re-deriving this artifact reproduce it? Recorded beside an
        artifact when it is written and consulted when either the artifact
        timestamp or source-set fingerprint differs (see `_up_to_date`).

        Scoped to this node: a file in the set that defines other node
        classes contributes only the text this node can depend on, so an
        edit to a sibling class sharing the file does not change the
        answer here (see `currency.source_digest`).

        None when any tracked source cannot be read -- an answer, not an
        error: nothing can be vouched for, so nothing is current.
        """
        return currency.source_digest(self.files, self._project_root,
                                      self.scope)

    @property
    def source_fingerprint(self):
        """Observable metadata state of every tracked source.

        This never opens source contents. It guards the settled path against
        a changed contributor hidden beneath the same maximum mtime; any
        disagreement falls through to the content digest.
        """
        return currency.source_fingerprint(self.files, self._project_root)

    @property
    def mtime(self):
        """Maximum mtime in source file of all nodes rendered inside this one.

        Public and float, as it has always been: the published viewer
        document records it per node. Derived from mtime_ns rather than
        computed beside it, so the two can never disagree about which
        source file won. Nothing in the build path decides currency from
        this value.
        """
        return _seconds(self.mtime_ns)

    def render(self):
        raise NotImplementedError

    @property
    def exact(self):
        """Whether this node exposes exact boundary-representation geometry."""
        return False

    def shape(self):
        raise RuntimeError(f'{self.name} does not expose exact geometry')

    def as_scad(self, rendered):
        """Converts the output of render() to solid2 object"""
        raise NotImplementedError

    def as_number(self, n):
        if type(n) not in (int, float, Decimal):
            raise TypeError(f'{n!r} is not a number')
        return n

    @property
    def scad_code(self):
        code = scad_render(self._require_model())
        if self.fn:
            code = f'$fn = {self.fn};\n\n{code}'
        return code

    def generate_scad(self):
        mtime_ns = self.mtime_ns
        digest = self.source_digest
        fingerprint = self.source_fingerprint
        identity = (mtime_ns, digest, fingerprint)
        generation = current_generation()
        shareable = self.rigid and generation is not None
        if (shareable
                and generation.has_scad_artifact(self.scad_file, identity)):
            logger.info('%s reused in this source generation', self.scad_file)
            return

        content = self.scad_code
        phase = current_phase()
        if (not self.rigid and not self.flexible and phase is not None
                and phase.coalesces_scad):
            phase.defer_scad(
                self.scad_file, content, mtime_ns, digest, fingerprint,
                _publish_scad)
            return

        _publish_scad(
            self.scad_file, content, mtime_ns, digest, fingerprint)

    def trigger_stl(self):
        self._prepare()
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

        backend = next(
            (cls.__name__ for cls in type(self).__mro__
             if cls.__name__ in ('Solid2Node', 'OpenScadNode', 'FusionNode')),
            type(self).__name__)
        node_name = getattr(self, 'name', type(self).__name__)
        openscad = require_openscad(
            f'node {node_name} ({backend} backend)',
            'its backend renders this STL through OpenSCAD')

        fh = open(self.lock_file, 'w')

        os.makedirs(os.path.dirname(self.stl_file) or '.', exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f'.{os.path.basename(self.stl_file)}.', suffix='.tmp',
            dir=os.path.dirname(self.stl_file) or '.')
        os.close(descriptor)
        command = self.stl_builder_command_for(temporary)
        command[0] = openscad
        proc = Popen(command)

        fh.write(f'{proc.pid}')
        fh.close()
        logger.info(f'Job started with pid {proc.pid}')
        raise StlRenderStart(proc, self.stl_file, temporary, self.mtime_ns,
                             self.lock_file, self.source_digest,
                             self.source_fingerprint)

    @property
    def stl_builder_command(self):
        return self.stl_builder_command_for(self.stl_file)

    def stl_builder_command_for(self, output):
        return [
            'openscad', self.scad_file,
            '-o', output,
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
    # be found in the parent's __dict__ at all (then it receives its
    # class-name fallback afresh).
    def _link_child(self, child, name_index=None):
        """Link `child` to this node as its parent, and derive its
        name from the attribute holding it. Called from the same spot
        the tree links parent/child today (InternalNode.as_scad) and
        from the shared viewer serializer, which walks render() output
        directly without a full assemble(). Idempotent: re-deriving
        the same attribute mapping twice (e.g. a second assemble())
        always recomputes the identical name -- it overwrites rather
        than appends, so nothing stacks."""
        child._parent = self
        if child._explicit_name:
            return
        found = (self._attr_name_for(child) if name_index is None
                 else name_index.get(id(child)))
        child.name = found if found is not None else type(child).__name__

    def _link_children(self, children):
        """Link one sibling batch from one parent-attribute snapshot."""
        if not children:
            return
        name_index = self._child_name_index()
        for child in children:
            self._link_child(child, name_index)

    def _child_name_index(self):
        """Map child identity to its name from one attribute snapshot.

        Public direct attributes are indexed first, in insertion order, so
        they beat every sequence alias.  Public list/tuple contents are
        copied while taking the snapshot and indexed second, also first-win.
        The copy fixes the naming observation for the whole sibling batch if
        recursive user code later mutates the live sequence.
        """
        attributes = []
        for attr, value in self.__dict__.items():
            if attr.startswith('_') or attr == 'children':
                continue
            members = tuple(value) if isinstance(value, (list, tuple)) else ()
            attributes.append((attr, value, members))

        found = {}
        for attr, value, _ in attributes:
            found.setdefault(id(value), attr)
        for attr, _, members in attributes:
            for index, item in enumerate(members):
                found.setdefault(id(item), f'{attr}-{index}')
        return found

    def _attr_name_for(self, child):
        """The attribute name (or `<attr>-<index>` for a list/tuple
        member) under which `self.__dict__` holds `child`, scanned in
        definition order. A plain attribute is always preferred over a
        list/tuple membership, even if the list hit comes first in
        definition order (two passes, not one). Private attributes
        (leading underscore) are skipped, and so is `children`, the
        framework's own linked list (InternalNode.as_scad): an
        assembly's rest render is kept and returned again, so the
        same instances are in that list on every later link and would
        otherwise be renamed `children-<index>`. Returns None if
        `child` isn't referenced by any (non-private) attribute at
        all."""
        return self._child_name_index().get(id(child))

    ##############################################
    # Transformations that can be applied to Node
    # model or mesh
    def rotate(self, angle, axis):
        # Deferred for the same reason as trimesh in cached_base_mesh, and
        # to the same end: operations.py imports trimesh at ITS module
        # scope, so importing it from here at module scope would import the
        # mesh library through the back door and undo the deferral above.
        from .operations import Rotation
        _place_operation(self, Rotation(angle, axis, self))
        return self

    def translate(self, translation):
        from .operations import Translation
        _place_operation(self, Translation(translation, self))
        return self

    def base_mesh(self):
        """The node's geometry in its OWN frame, as a fresh mutable copy.

        The one seam every framed view goes through -- `mesh` here, and
        the test runner's `_mesh_in_frame`, which needs the same geometry
        in the solid frame instead. A node kind whose geometry is not a
        cached artifact overrides this single method rather than each
        framing separately: a flexible leaf (`FlexibleNode`) evaluates
        its current binding here, because it has no cached rigid STL to
        read and its shape is not time-invariant.
        """
        return cached_base_mesh(self.stl_file).copy()

    @property
    def mesh(self):
        """The node's mesh in WORLD coordinates: its own operations
        applied first, then each ancestor's, up the assembled tree —
        the same composition the viewer renders. The base geometry is
        loaded once per strong artifact observation (see
        ``cached_base_mesh``) and
        always returned as a fresh COPY with a single composed world
        matrix applied (see _compose_world_matrix) -- callers are free
        to mutate the result; the cached base mesh never is."""
        mesh = self.base_mesh()
        mesh.apply_transform(_compose_world_matrix(self))
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
        """Exact artifact equality guarded by every source's metadata.

        Equality and not tolerance: a window wide enough to absorb a
        filesystem's quantum is exactly a window in which a real edit
        becomes invisible, and ADR-033 ranks a stale model above a
        spurious rebuild for good reason.

        A matching maximum alone loses information about older contributors,
        so the settled path also requires the source-set fingerprint recorded
        when the artifact was written. This stats sources and reads one small
        sidecar, but does not open source contents. Any disagreement invokes
        the existing stronger content proof.
        """
        if not os.path.exists(path):
            return False
        expected_recipe = self._artifact_recipe(path)
        if (expected_recipe is not None
                and currency.recorded_recipe(path) != expected_recipe):
            return False
        artifact_mtime_ns = os.stat(path).st_mtime_ns
        node_mtime_ns = self.mtime_ns
        fingerprint = self.source_fingerprint
        if (fingerprint is not None
                and artifact_mtime_ns == node_mtime_ns
                and currency.recorded_fingerprint(path) == fingerprint):
            return True
        return self._content_verified(path, fingerprint)

    def _content_verified(self, path, fingerprint=None):
        """Whether `path` was produced from the sources that are here now.

        The timestamp or contributor fingerprint moved -- a clone, a branch
        switch, a stash pop, a copy, a formatter rewriting a file byte for
        byte, or an edit hidden below the maximum mtime. If the digest
        recorded when this artifact was written is the digest of the
        sources on disk, then re-deriving it would reproduce it, which is
        a strictly stronger claim than the equality that just failed.

        Anything less says no: no record, an unreadable source, or any
        disagreement at all. The artifact is then rebuilt exactly as it
        always was.

        The restamp is a deliberate side effect inside a predicate, and it
        is the same `os.utime` a build performs: it moves the artifact
        onto the fast path so no later build pays for this again. It is
        best effort, and the answer does not depend on it -- where the
        filesystem cannot store the exact stamp, the artifact is still
        current for this build on the strength of the digest, and the
        fallback is simply consulted again next time.
        """
        recorded = currency.recorded_digest(path)
        if recorded is None:
            return False
        digest = self.source_digest
        if digest is None or digest != recorded:
            return False
        currency.restamp(path, self.mtime_ns)
        if fingerprint is None:
            fingerprint = self.source_fingerprint
        currency.record(path, digest, fingerprint,
                        self._artifact_recipe(path))
        return True

    def _artifact_recipe(self, path):
        """Private producer revision expected for an affected artifact."""
        return None

    @property
    def geometry_recipe(self):
        """Stable ingredient revision used by enclosing fusion recipes."""
        return f'{type(self).__module__}.{type(self).__qualname__}:native-v1'

    def _make_build_dirs(self):
        # The build directory is absolute once anchored on the project root,
        # so create the whole chain at once rather than walking it.
        os.makedirs(self.build_dir, exist_ok=True)


class StlRenderStart(Exception):

    def __init__(self, proc, stl_file, temporary_file, mtime_ns, lock_file,
                 digest=None, fingerprint=None):
        super().__init__()
        self.proc = proc
        self.stl_file = stl_file
        self.temporary_file = temporary_file
        self.mtime_ns = mtime_ns
        self.lock_file = lock_file
        # The source record this render was started from, carried across the
        # subprocess so finish() can vouch for what it publishes. Read
        # when the render began, not when it ended: an edit that lands
        # mid-render must not be recorded as the thing that produced
        # this artifact.
        self.digest = digest
        self.fingerprint = fingerprint

    @property
    def mtime(self):
        return _seconds(self.mtime_ns)

    def finish(self):
        os.utime(self.temporary_file, ns=(time.time_ns(), self.mtime_ns))
        currency.publish(self.temporary_file, self.stl_file, self.digest,
                         self.fingerprint)
        logger.info(f"{self.stl_file} generated with {self.mtime}!")
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)

    def _discard(self):
        """Remove the private files of a render that cannot be published."""
        for path in (self.temporary_file, self.lock_file):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

    def wait(self, checkpoint=None):
        logger.info(f"waiting for {self.stl_file} ...")
        changed = None
        if checkpoint is not None:
            try:
                checkpoint(label='render_wait_pre')
            except Exception as error:
                # The subprocess is already running.  Reap it before carrying
                # the source-change outcome out, but never publish its output.
                changed = error
        returncode = self.proc.wait()
        if changed is not None:
            self._discard()
            raise changed
        if returncode:
            self._discard()
            raise CalledProcessError(returncode, self.proc.args)
        if checkpoint is not None:
            try:
                checkpoint(label='render_wait_post')
            except Exception:
                self._discard()
                raise
        logger.info(f"{self.stl_file} done!")
        self.finish()
