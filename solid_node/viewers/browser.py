# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Transparent PNG rendering through the installed browser viewer.

This side knows what a node is: it brings the artifacts up to date under
the build lock, serializes the photographed node into a staging directory of
its own and links the models it names there. The photograph itself is the
viewer's -- `solid-node-viewer capture`, run on that directory as a separate
process with the image size, the animation instant and the camera this side
resolved from OpenSCAD's syntax. Nothing of the viewer is imported here.
"""

import json
import os
import shutil
import tempfile
from subprocess import run

from solid_node._artifact import ArtifactChanged
from solid_node.core.builder import get_build_dir, project_build_lock
from solid_node.core.camera import parse_camera
from solid_node.core.pieces import PieceInventory
from solid_node.core.serializer import (
    compiled_program, document_body, drivers_table, serialize_node,
)
from solid_node.viewers import bundle as viewer_bundle


class BrowserSnapshotError(Exception):
    pass


class BrowserRenderer:
    def render(self, node, args, output):
        build_dir = self.build_dir(node, args)
        staging = None
        try:
            with project_build_lock(build_dir):
                node.build_stls()
                staging = self.stage(node, build_dir)
            self.capture(staging, args, output)
        finally:
            if staging is not None:
                self.remove_stage(staging)

    def build_dir(self, node, args=None):
        origin = getattr(args, "path", None) or getattr(node, "file", None)
        return os.path.abspath(get_build_dir(origin))

    def stage(self, node, build_dir):
        """Describe `node` in a private directory beside the build.

        The document is serialized here rather than republished into the
        build, because the build's own document and artifacts belong to
        whatever produced them -- usually a running `solid develop` serving
        the project's root. Writing this node's tree there would replace
        that model, sweep the artifacts it still references, and discard any
        recorded build error. A snapshot only reads.
        """
        for attempt in range(3):
            try:
                return self._stage(node, build_dir)
            except ArtifactChanged:
                if attempt == 2:
                    raise

    def _stage(self, node, build_dir):
        """Perform one coherent read-only staging attempt."""
        if not viewer_bundle.has_bundle():
            raise BrowserSnapshotError(viewer_bundle.missing_bundle_remedy())

        artifacts = {}
        # A capture BAKES one instant: the node arrives keyframed and
        # posed at whatever `--drive` asked for, and its operations hold
        # the numbers that pose produced. So this document is not the
        # machine's own -- there is nothing symbolic in it to bind -- and
        # the drivers table it carries under a running root is the
        # declaration beside the program, not a scope for expressions.
        program, initial = compiled_program(node)
        with PieceInventory(publish_facts=False) as inventory:
            root = serialize_node(
                node,
                lambda rigid_node: artifacts.setdefault(
                    rigid_node.stl_file,
                    self.artifact_path(rigid_node.stl_file, build_dir),
                ),
                inventory.register,
                graph_values=True,
            )
            drivers = ({} if program is None
                       else drivers_table(dict(program.inputs)))
            document = document_body(node, root, drivers, {},
                                     program, initial)
            self.refuse_unreadable(document['version'])
            document["root"] = root
            document["pieces"] = inventory.pieces()

            staging = tempfile.mkdtemp(
                prefix=f"{os.path.basename(build_dir)}.web-snapshot.",
                dir=os.path.dirname(build_dir),
            )
            try:
                for source, relative in artifacts.items():
                    if not os.path.isfile(source):
                        raise BrowserSnapshotError(
                            f"Build artifact is missing: {relative}")
                    target = os.path.join(staging, relative)
                    inventory.copy_artifact(source, target)
                inventory.validate()
                # Document last: a successful staged directory never names a
                # missing or incoherent model.
                with open(os.path.join(staging, "viewer.json"), "w") as output:
                    json.dump(document, output)
                return staging
            except Exception:
                self.remove_stage(staging)
                raise

    def refuse_unreadable(self, version):
        """Refuse a document the installed viewer cannot read, BEFORE the
        browser starts and before a staging directory exists.

        A capture is a one-shot: the viewer's own refusal would reach the
        caller as an opaque non-zero exit from a headless page, and this
        capability's standing rule is to fail with what is missing rather
        than substitute. It never falls back to OpenSCAD, which is the
        same rule stated for a missing viewer package and a missing
        browser.
        """
        message = viewer_bundle.unreadable_document(version)
        if message is not None:
            raise BrowserSnapshotError(
                f'{message}. A capture is a one-shot, so it is refused '
                f'here rather than failing inside a headless page: no '
                f'browser was started and no image was written. Install a '
                f'viewer that renders it, or photograph the model with '
                f'--renderer openscad.')

    def artifact_path(self, stl_file, build_dir):
        """The staged, build-relative location of one artifact."""
        source = os.path.abspath(stl_file)
        if os.path.commonpath((source, build_dir)) != build_dir:
            raise BrowserSnapshotError(
                f"Node artifact lies outside the build: {stl_file}"
            )
        return os.path.relpath(source, build_dir)

    def remove_stage(self, staging):
        shutil.rmtree(staging, ignore_errors=True)

    def capture_command(self, staging, args, output):
        """The viewer's capture, told what to photograph and how to frame it."""
        command = viewer_bundle.viewer_command() + [
            "capture", staging, "-o", output,
            "--imgsize", args.imgsize, "--time", str(args.time),
        ]
        if args.camera:
            camera = parse_camera(args.camera)
            command += [
                "--view", ",".join(str(v) for v in (*camera.eye, *camera.target)),
                "--up", ",".join(str(v) for v in camera.up),
                "--fov", str(camera.fov),
            ]
        return command

    def capture(self, staging, args, output):
        """Photograph the staged document through the viewer's own process."""
        result = run(
            self.capture_command(staging, args, output),
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip() or (
                f"the viewer's capture exited with status {result.returncode}"
            )
            raise BrowserSnapshotError(message)
