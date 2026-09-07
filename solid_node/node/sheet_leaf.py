# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

from solid_node.node.exact_leaf import ExactLeafNode


class SheetLeafNode(ExactLeafNode):
    """Base for the leaf adapters whose part is cut from sheet stock.

    A sheet part is authored as a two-dimensional profile plus a declared
    `thickness`, and its solid is that profile extruded from the XY plane
    along +Z. The extension point is therefore `profile()`, never
    `render()`: `render()` is owned here so that the solid in the tree and
    the cut file on disk cannot describe different parts. A leaf that
    authored the solid separately from the profile would be free to drift,
    and a laser cutter would happily cut the drift.

    The direction matters. Authoring 2D and deriving 3D is a projection --
    one extrusion, no choices. Recovering 2D from an authored solid is an
    inverse problem: which plane to slice on, whether the thickness is even
    constant, how to reconstruct a curve from a slice. So the profile is the
    source and the solid is derived, not the other way round.

    A subclass supplies what genuinely differs between backends: how a
    profile result is reduced to one planar face, how a face is extruded,
    and how a face is written as a cut file. The *rules* -- one planar face,
    one part per leaf, on the XY plane, a positive thickness -- are here, so
    every sheet backend rejects the same authoring mistakes with the same
    wording.

    Like ExactLeafNode this is a framework-internal base: projects subclass
    a concrete sheet adapter, not this.
    """

    #: Stock thickness, declared per node as a class attribute or passed as
    #: a `thickness=` constructor argument. Passed as an argument it reaches
    #: uniq_id like any other parameter (ADR-026), so two thicknesses of one
    #: panel are two artifacts; declared as a class attribute, a change edits
    #: the source file, which the source-set freshness path already rebuilds
    #: on (ADR-033).
    thickness = None

    def __init__(self, *args, **kwargs):
        # Taken from kwargs rather than captured as a named parameter, so it
        # still travels into AbstractBaseNode's uniq_id: a node keyed
        # without its thickness would serve a 3 mm panel's artifacts for a
        # 6 mm one.
        if 'thickness' in kwargs:
            self.thickness = kwargs['thickness']

        super().__init__(*args, **kwargs)

        # The cut file joins the STL and the BREP in this node's artifact
        # set, under the same basename and the same freshness rules.
        self.dxf_file = f'{self.basepath}.dxf'

        # The validated profile of this render, kept because as_scad() needs
        # the very face render() extruded -- deriving the cut file from a
        # second, independent call to profile() is exactly the divergence
        # this class exists to prevent.
        self._profile_face = None

        self._validate_thickness()

    ##############################################
    # The extension point

    def profile(self):
        """The part's 2D profile, in the backend's own terms.

        This is what a sheet part's subclass writes. It must produce one
        planar face -- a single outer boundary with any holes strictly
        inside it -- lying on the XY plane.
        """
        raise NotImplementedError(
            f"{self.__class__} is a sheet leaf and must implement profile(), "
            "returning its 2D cut profile")

    ##############################################
    # The derived solid

    def render(self):
        """The extrusion of the validated profile.

        Not an extension point: overriding it would let the solid and the
        cut file describe different parts.
        """
        return self._extrude(self.validated_profile())

    def validated_profile(self):
        """The one planar face this part's solid and cut file both come
        from, validated once per node."""
        if self._profile_face is None:
            self._profile_face = self._validate_profile(self.profile())
        return self._profile_face

    def _validate_profile(self, profile):
        """Reduce a backend profile result to the single planar face the
        contract demands, naming this node and the offending type when it
        cannot.

        Raised before anything is written: an unmanufacturable profile must
        not leave an artifact behind for a cutter to find.
        """
        faces = self._profile_faces(profile)

        if not faces:
            raise ValueError(
                f"{self.name} is a sheet part and its profile() must produce "
                f"one planar face on the XY plane -- an outer boundary with "
                f"its holes inside -- not {type(profile).__name__}")

        if len(faces) > 1:
            raise ValueError(
                f"{self.name} is a sheet part and one sheet part is one "
                f"piece, but its profile() produced {len(faces)} disjoint "
                f"faces from {type(profile).__name__}; author each piece as "
                f"its own sheet leaf")

        face = faces[0]

        if not self._lies_on_xy_plane(face):
            raise ValueError(
                f"{self.name} is a sheet part and its profile() must lie on "
                f"the XY plane, since the solid is the profile extruded from "
                f"there along +Z by thickness; this "
                f"{type(profile).__name__} does not")

        return face

    def _validate_thickness(self):
        """Fail at construction, not at render: a panel with no declared
        stock is a modelling mistake, and the earliest legible place to say
        so is where the node is written down."""
        if self.thickness is None:
            raise ValueError(
                f"{self.name} is a sheet part and must declare a positive "
                f"thickness, as a class attribute or a thickness= "
                f"constructor argument")

        try:
            thickness = self.as_number(self.thickness)
        except TypeError:
            raise TypeError(
                f"{self.name} is a sheet part and its thickness must be a "
                f"number, not {type(self.thickness).__name__}") from None

        if thickness <= 0:
            raise ValueError(
                f"{self.name} is a sheet part and its thickness must be "
                f"positive, not {thickness}")

    ##############################################
    # The cut file, in the artifact lifecycle

    def _render_can_be_skipped(self):
        """The cut file is an artifact of this node like the STL and the
        BREP, so the build's work is only skippable while it too is
        current -- otherwise a lost DXF would never come back."""
        return (
            super()._render_can_be_skipped()
            and self._up_to_date(self.dxf_file)
        )

    def as_scad(self, rendered):
        """The exact adapter's STL and BREP, plus this part's cut file.

        Same guard as the other artifacts: produced only when it is not
        already the file these sources would produce, and the returned SCAD
        is the same either way.
        """
        scad = super().as_scad(rendered)
        if not self._up_to_date(self.dxf_file):
            self._write_dxf(self.validated_profile(), self.dxf_file,
                            self.mtime_ns, self.source_digest,
                            self.source_fingerprint)
        return scad

    ##############################################
    # Backend hooks

    def _profile_faces(self, profile):
        """The planar faces of a backend profile result, or an empty list
        when it is not a two-dimensional object at all."""
        raise NotImplementedError

    def _lies_on_xy_plane(self, face):
        """Whether a validated face lies on the plane the extrusion starts
        from."""
        raise NotImplementedError

    def _extrude(self, face):
        """The face extruded along +Z by this node's thickness, in the
        backend's own terms."""
        raise NotImplementedError

    def _write_dxf(self, face, path, mtime_ns, digest=None,
                   fingerprint=None):
        """Write the nominal cut file for a validated face."""
        raise NotImplementedError
