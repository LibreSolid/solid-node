# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""The flexible leaf: a part whose shape follows the machine's state.

A valve spring, a timing belt, a cable loom: parts whose GEOMETRY, not
just whose placement, is a function of where the machine is. Every other
leaf promises a time-invariant solid, which is what lets its STL be
cached and its body be fused into a printed piece. A flexible part makes
no such promise, so it is the one non-rigid leaf kind -- the exception
ADR-003 and ADR-008 anticipated when they deferred time-dependent leaf
geometry.

The consequences compose with the existing rules rather than fighting
them. A `FusionNode` already rejects a non-rigid child, so a flexible
part cannot be fused, which is mechanically right: you cannot union a
deforming spring into one printed solid. Non-rigid nodes already produce
no cached rigid STL, so the mtime-caching precondition is untouched --
this leaf simply is not in the cached set. It is never a topmost rigid
node, so it is not a printed piece. And `time` still raises, because its
shape is a pure function of its bound ports and of nothing else.

Parameters arrive through ports, never through the constructor. Every
constructor parameter enters `uniq_id` (ADR-026), so a continuously
varying value would mint a new artifact identity per frame; a port
binding keeps identity structural -- two `ValveSpring()` instances share
one -- while the values flow through the seam drivers already use::

    class ValveSpring(MolejoNode):
        height = TranslationalPort(unit='mm')

        def render(self):
            return Shape(profile=Circle(radius=2.0),
                         path=[Helix(radius=14.0, turns=6.5,
                                     height=P.height)],
                         path_samples=240, profile_samples=16)

    class Valvetrain(AssemblyNode):
        lift = Driver(default=0.0, range=(0.0, 12.0), unit='mm')

        def render(self):
            self.connect(FREE_HEIGHT - self.lift, self.spring.height)
            return [self.spring]

The port name IS the parameter name, and the two name sets must agree
exactly: a shape parameter with no port would be fed by nothing, and a
port naming no parameter would bind a value no geometry follows. Both
fail loudly, naming the node, the offending name and both sets. A
missing binding fails too -- never a silent default, matching the driver
read discipline.

This is a framework-internal base, like `ExactLeafNode` and
`SheetLeafNode`: it holds everything the framework needs regardless of
which technology evaluates the sweep, and a concrete adapter (today
`MolejoNode`) supplies the three backend hooks at the bottom of this
module. Sharing the base never makes two adapters interchangeable to a
type test.
"""

import os

from solid2 import import_stl, union
from solid2.core.object_base import OpenSCADConstant
from solid2.extensions.greedy_scad_interface import get_animation_time

from solid_node.node.base import _atomic_write_bytes, binding_hash
from solid_node.node.leaf import LeafNode
from solid_node.node.ports import declared_ports


def _names(names):
    return ', '.join(sorted(names)) or 'none'


class FlexibleNode(LeafNode):
    """Base for the leaf adapters whose part deforms with machine state.

    A subclass declares one port per shape parameter, returns its
    backend's shape object from `render()`, and implements the three
    backend hooks. Everything else -- rigidity, the parameter-surface
    check, the resolved binding, the per-binding snapshot artifact and
    the mesh seam -- is here, so a correction to the contract lands once.
    """

    #: The one non-rigid leaf kind. Its geometry is a function of bound
    #: state, so it makes no time-invariance promise and never joins the
    #: cached-STL or printed-piece sets.
    rigid = False

    #: The third node shape the serialized document knows, beside a
    #: model reference and a list of children. Read by the serializer
    #: exactly as `rigid` is, so the document's shape follows the node's
    #: kind rather than a type test in the producer.
    flexible = True

    #: The technology that evaluates this leaf's shape, published in the
    #: document so a consumer knows which evaluator the spec belongs to
    #: -- and can refuse one it cannot evaluate, naming it. Declared by
    #: the concrete adapter, like `namespace`.
    tech = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #: The snapshot artifact this node's last `as_scad()` imported,
        #: or None before one ran. Public because the build's post-build
        #: sweep has to know which per-binding artifact is still
        #: referenced: the published document is serialized symbolically
        #: and so cannot name one, while the assembled tree can.
        self.snapshot_file = None

        #: The last binding whose exact solid was built, and the result.
        #: An assertion asks a pair the same question twice -- once for
        #: emptiness, once for connectivity -- and an exact leaf answers
        #: the second from its cached `.brep`; this leaf has none to read
        #: (see `shape`), so the memo is where that saving lives instead.
        self._exact_binding = None
        self._exact_result = None

    ##############################################
    # The parameter surface

    def bound_values(self):
        """The resolved numeric value of every declared port.

        The snapshot evaluation entry point: what the backend is handed,
        and what the snapshot artifact is keyed on. Both failures here
        are the same refusal to guess -- an unbound port is a wiring
        mistake to be seen, and a port carrying a driver expression means
        the caller reached a numeric path in symbolic mode, where no
        single mesh exists to evaluate.
        """
        values = {}
        for name in sorted(declared_ports(type(self))):
            value = getattr(self, name).value
            if value is None:
                raise ValueError(
                    f"{self.name} cannot be evaluated: its port '{name}' is "
                    f"unbound, and a flexible part's shape is a function of "
                    f"its ports. Connect it where the parent assembly "
                    f"renders this node, with "
                    f"connect(<source>, <node>.{name}).")
            try:
                values[name] = float(self.as_number(value))
            except TypeError:
                raise TypeError(
                    f"{self.name} cannot be evaluated: its port '{name}' is "
                    f"bound to the expression '{value}', not to a number. A "
                    f"flexible part evaluates one instant at a time, so this "
                    f"path needs a numeric binding; bind the drivers the "
                    f"expression names with set_state() first.") from None
        return values

    def bound_expressions(self):
        """The bound expression of every declared port, as a string.

        The symbolic counterpart of `bound_values()`, and the document's
        parameter surface. Under symbolic serialization the parent's
        `connect()` has already bound each port to ordinary solid2
        arithmetic over driver tokens, so the wire expression is finished
        before this reads it and `str` is the whole serialization -- the
        same `str(value)` an operation publishes, carrying the same
        verbatim guarantee. Under a numeric binding it is the number, for
        the same reason and by the same rule: what the port carries.
        """
        expressions = {}
        for name in sorted(declared_ports(type(self))):
            value = getattr(self, name).value
            if value is None:
                raise ValueError(
                    f"{self.name} cannot be serialized: its port '{name}' is "
                    f"unbound, and a flexible part publishes one expression "
                    f"per port. Connect it where the parent assembly renders "
                    f"this node, with connect(<source>, <node>.{name}).")
            expressions[name] = str(value)
        return expressions

    def flexible_document(self):
        """This leaf as the document's `flexible` object.

        The whole of what travels: which technology evaluates the shape,
        the shape spec verbatim as the adapter serialized it, and one
        expression per parameter. No geometry -- a flexible part's viewer
        representation IS its spec, so there is no mesh to publish,
        nothing to deduplicate into an export's `models/`, and no piece.
        """
        return {
            'tech': self.tech,
            'spec': self._shape_spec(self.current_shape()),
            'params': self.bound_expressions(),
        }

    def validate(self, rendered):
        """The backend's namespace check, then the parameter surface.

        Checked in both directions and immediately after `render()`, so a
        mismatch is reported where the shape was authored rather than
        much later as a missing value inside the backend.
        """
        super().validate(rendered)

        parameters = set(self._shape_parameters(rendered))
        ports = set(declared_ports(type(self)))

        unfed = sorted(parameters - ports)
        if unfed:
            raise ValueError(
                f"{self.name} renders a shape whose parameter '{unfed[0]}' "
                f"has no declared port: a flexible part's parameters are fed "
                f"by its ports, one port per parameter, and the port's "
                f"attribute name is the parameter's name. Shape parameters: "
                f"{_names(parameters)}; declared ports: {_names(ports)}.")

        unread = sorted(ports - parameters)
        if unread:
            raise ValueError(
                f"{self.name} declares the port '{unread[0]}', which its "
                f"rendered shape names no parameter for: a flexible part's "
                f"declared ports are its whole parameter surface, so a port "
                f"nothing reads would bind a value no geometry follows. "
                f"Shape parameters: {_names(parameters)}; declared ports: "
                f"{_names(ports)}.")

    ##############################################
    # The per-binding snapshot artifact

    def snapshot_stl_file(self, values):
        """This node's snapshot artifact for one binding.

        `<script>-<uniq_id>-<binding-hash>.stl`: the node's own artifact
        key, so two flexible parts never collide, plus the binding, so a
        changed state selects a different file. Mtime equality then
        decides SOURCE currency within one binding exactly as it does for
        any adapter-owned artifact, and never has to decide binding
        currency -- which it could not.
        """
        return f'{self.basepath}-{binding_hash(values)}.stl'

    def local_snapshot_stl(self, values):
        """`snapshot_stl_file` as the SCAD document imports it, beside
        the scad -- the local form `local_stl` is for a rigid leaf."""
        return f'{os.path.basename(self.basepath)}-{binding_hash(values)}.stl'

    def _unbound_ports(self):
        """The declared ports nothing has connected."""
        return sorted(name for name in declared_ports(type(self))
                      if getattr(self, name).value is None)

    def _time_fed_ports(self):
        """The declared ports bound to an expression over animation
        time, which the build path keeps symbolic (`solid_node.math`).

        Narrower than "symbolic" on purpose. Time is the ONE thing
        nothing can bind here -- `AssemblyNode.time` falls back to
        solid2's `$t` precisely so the build and viewer paths animate --
        so a time-fed port is a part with no instant, not a mistake.
        Every other symbolic value IS a mistake: the loader binds
        declared driver defaults, so a port still carrying a raw driver
        token means something skipped that, and it goes on failing
        loudly through `bound_values()`.
        """
        token = str(get_animation_time())
        return sorted(
            name for name in declared_ports(type(self))
            if isinstance(getattr(self, name).value, OpenSCADConstant)
            and token in str(getattr(self, name).value))

    def as_scad(self, rendered):
        """Evaluate this instant and import it, so the assembled SCAD
        document stays as complete as it honestly can for the OpenSCAD
        GUI.

        A snapshot camera, never animation: OpenSCAD gets the geometry of
        the bound state, the same treatment drivers already get. Produced
        only when the artifact for THIS binding is not already the file
        these sources would produce, and the returned SCAD is the same
        either way.

        A port fed by animation time has no instant to photograph. The
        loader binds declared driver defaults, so a driver-fed port
        always resolves; time is deliberately symbolic here, so a part
        whose geometry follows the crank arrives holding an expression.
        Substituting a value for it would be this module guessing which
        moment of the cycle matters, and failing would stop the build
        before it published the document -- which is where a flexible
        part is actually delivered and where the full expression travels
        intact. So the camera declines: no artifact, no geometry, and
        assembly carries on. An UNBOUND port is a different thing, a
        wiring mistake with no expression behind it, and still fails
        loudly through `bound_values()` below.
        """
        if not self._unbound_ports() and self._time_fed_ports():
            self.snapshot_file = None
            return union()

        values = self.bound_values()
        snapshot = self.snapshot_stl_file(values)
        if not self._up_to_date(snapshot):
            _atomic_write_bytes(snapshot, self._snapshot_stl(rendered, values),
                                self.mtime_ns)
        self.snapshot_file = snapshot
        return import_stl(self.local_snapshot_stl(values))

    ##############################################
    # Geometry for tests and assertions

    def base_mesh(self):
        """This instant's geometry, evaluated rather than read.

        A flexible part has no cached rigid artifact to load, and its
        shape is not time-invariant, so the mesh has to come from the
        current binding. Overriding this one seam gives every framed view
        -- `mesh` in world coordinates, `_mesh_in_frame` in the solid
        frame -- the same geometry it would have had from an artifact.
        """
        return self._snapshot_mesh(self.current_shape(), self.bound_values())

    def current_shape(self):
        """The validated render result for this instant."""
        rendered = self.render()
        self.validate(rendered)
        return rendered

    ##############################################
    # Exact geometry

    def shape(self):
        """This instant's exact solid, computed rather than loaded.

        An exact leaf reads its `.brep` back when the artifact on disk is
        the one its sources would produce, and that shortcut is exactly
        what a flexible part cannot have: mtime answers whether the
        SOURCE changed, never whether the BINDING did, and a part whose
        shape follows the machine has one solid per instant rather than
        one per source. Persistence is structurally about rigid nodes
        anyway -- the build requires a `.brep` only where a node is both
        rigid and exact, the exact composition path fuses the shapes its
        children RETURN rather than files they wrote, and a fusion
        refuses a flexible child outright -- so nothing downstream is
        waiting for a file, and a per-binding one would be swept by
        nothing (the sweep spares every `.brep` unconditionally). The
        binding memo below is the whole of the caching this needs.
        """
        return self._exact_solid()[0]

    @property
    def shape_tolerance(self):
        """The approximation tolerance `shape()` was built to, at the
        current binding: zero when every surface of the solid is
        analytic, and the backend's declared approximation where some
        part of the sweep has no closed form the kernel can hold. Carried
        rather than hidden -- a swept helix is honestly tolerant, and a
        caller reading an exact answer deserves to know how exact.
        """
        return self._exact_solid()[1]

    def _exact_solid(self):
        """`(shape, tolerance)` for the current binding, built once."""
        values = self.bound_values()
        key = binding_hash(values)
        if key != self._exact_binding:
            self._exact_result = self._snapshot_shape(
                self.current_shape(), values)
            self._exact_binding = key
        return self._exact_result

    ##############################################
    # Backend hooks

    def _shape_parameters(self, rendered):
        """The parameter names the rendered shape references."""
        raise NotImplementedError

    def _shape_spec(self, rendered):
        """The rendered shape as the document the framework embeds."""
        raise NotImplementedError

    def _snapshot_mesh(self, rendered, values):
        """The backend's evaluation of `rendered` at `values`, as a
        trimesh in the node's own frame."""
        raise NotImplementedError

    def _snapshot_stl(self, rendered, values):
        """The same evaluation as binary STL bytes."""
        raise NotImplementedError

    def _snapshot_shape(self, rendered, values):
        """The same evaluation as `(exact shape, tolerance)`, in the
        shared boundary representation every exact node trades in."""
        raise NotImplementedError
