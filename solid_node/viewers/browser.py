# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""Browser-backed transparent PNG rendering."""

import json
import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from solid_node.core.builder import get_build_dir, project_build_lock
from solid_node.core.camera import parse_camera
from solid_node.core.pieces import PieceInventory
from solid_node.core.serializer import (
    DOCUMENT_FORMAT, DOCUMENT_VERSION, serialize_node,
)
from solid_node.viewers import bundle as viewer_bundle

PLAYWRIGHT_REMEDY = (
    "Install the browser renderer with `pip install solid-node[web-snapshot]` "
    "and then download Chromium with `playwright install chromium`."
)


class BrowserSnapshotError(Exception):
    pass


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class BrowserRenderer:
    def render(self, node, args, output):
        self.assert_not_root()
        build_dir = self.build_dir(node, args)
        staging = None
        try:
            with project_build_lock(build_dir):
                node.build_stls()
                staging = self.stage(node, build_dir)
            self.write_mount_page(staging, args)
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
        if not viewer_bundle.has_bundle():
            raise BrowserSnapshotError(viewer_bundle.missing_bundle_remedy())

        artifacts = {}
        inventory = PieceInventory()
        root = serialize_node(
            node,
            lambda rigid_node: artifacts.setdefault(
                rigid_node.stl_file,
                self.artifact_path(rigid_node.stl_file, build_dir),
            ),
            inventory.register,
        )
        document = {
            "format": DOCUMENT_FORMAT,
            "version": DOCUMENT_VERSION,
            "animation": {"fps": 30, "frames": 360},
            "root": root,
            "pieces": inventory.pieces(),
        }

        staging = tempfile.mkdtemp(
            prefix=f"{os.path.basename(build_dir)}.web-snapshot.",
            dir=os.path.dirname(build_dir),
        )
        try:
            with open(os.path.join(staging, "viewer.json"), "w") as output:
                json.dump(document, output)
            for source, relative in artifacts.items():
                if not os.path.isfile(source):
                    raise BrowserSnapshotError(
                        f"Build artifact is missing: {relative}"
                    )
                target = os.path.join(staging, relative)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                os.link(source, target)
            shutil.copy2(
                viewer_bundle.bundle_path(),
                os.path.join(staging, viewer_bundle.BUNDLE_NAME),
            )
            return staging
        except Exception:
            self.remove_stage(staging)
            raise

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

    def write_mount_page(self, staging, args):
        options = {"animation": "external", "time": args.time}
        if args.camera:
            camera = parse_camera(args.camera)
            options.update(
                {
                    "view": {"camera": camera.eye, "target": camera.target},
                    "up": camera.up,
                    "fov": camera.fov,
                }
            )
        payload = json.dumps(options)
        page = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body,#host{{margin:0;width:100%;height:100%;overflow:hidden;
background:transparent}}
canvas{{background:transparent}}
</style></head><body><div id="host"></div>
<script src="{viewer_bundle.BUNDLE_NAME}"></script><script>
SolidNodeWidget.mount('#host', 'viewer.json', {payload}).then(() => {{
  requestAnimationFrame(() => requestAnimationFrame(() => {{
    document.body.dataset.ready = '1';
  }}));
}}).catch((error) => {{ document.body.dataset.error = String(error); }});
</script></body></html>"""
        with open(os.path.join(staging, "index.html"), "w") as output:
            output.write(page)

    @contextmanager
    def serve(self, staging):
        handler = partial(_QuietHandler, directory=staging)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_address[1]}"
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def capture(self, staging, args, output):
        dimensions = args.imgsize.lower().split("x")
        width, height = (int(value) for value in dimensions)
        playwright = self.playwright()
        with self.serve(staging) as base_url, playwright() as runtime:
            browser = self.launch(runtime.chromium)
            try:
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=1,
                )
                page = context.new_page()
                page.goto(f"{base_url}/index.html")
                page.wait_for_function(
                    "document.body.dataset.ready || " "document.body.dataset.error"
                )
                error = page.locator("body").get_attribute("data-error")
                if error:
                    raise BrowserSnapshotError(
                        f"Browser viewer failed to mount: {error}"
                    )
                output_dir = os.path.dirname(os.path.abspath(output))
                os.makedirs(output_dir, exist_ok=True)
                page.locator("canvas").screenshot(
                    path=output,
                    omit_background=True,
                )
                context.close()
            finally:
                browser.close()

    def playwright(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise BrowserSnapshotError(PLAYWRIGHT_REMEDY) from error
        return sync_playwright

    def launch(self, browser_type):
        try:
            return browser_type.launch(
                args=[
                    "--use-gl=angle",
                    "--use-angle=swiftshader",
                    "--enable-unsafe-swiftshader",
                ]
            )
        except Exception as error:
            if "Executable doesn't exist" in str(error):
                raise BrowserSnapshotError(PLAYWRIGHT_REMEDY) from error
            raise

    def assert_not_root(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            raise BrowserSnapshotError(
                "The web renderer cannot run as root because Chromium cannot "
                "use its sandbox. Run the command as an unprivileged user."
            )
