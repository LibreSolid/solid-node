# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""End-to-end tests for the export widget: export the spinner_project
fixture, serve the output directory over HTTP, render it in headless
chromium and assert on the pixels -- models load with their colors,
and the ?t= URL parameter actually poses the $t animation.

The mount-interface tests below them drive a real page with playwright
instead, because a screenshot cannot click a control or read an
attribute.

These tests need artifacts a plain python environment may not have,
and skip when missing:
- the widget bundle (dist/solid-widget.js, built by npm)
- a headless chromium (playwright's cache, $SOLID_HEADLESS_CHROME,
  or a chromium/chrome on PATH)
- Pillow, for pixel assertions
- playwright, for the mount-interface tests
"""

import glob
import os
import shutil
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from subprocess import run

from solid_node.core.export import export_node
from solid_node.viewers.bundle import bundle_path

from .base import BaseNodeTest
from . import spinner_project

try:
    from PIL import Image, ImageChops
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def find_headless_chrome():
    """A chromium able to take --headless --screenshot shots.
    Prefers an explicit $SOLID_HEADLESS_CHROME, then playwright's
    cached headless shell, then a browser on PATH."""
    explicit = os.environ.get('SOLID_HEADLESS_CHROME')
    if explicit:
        return explicit

    cached = sorted(glob.glob(os.path.expanduser(
        '~/.cache/ms-playwright/chromium_headless_shell-*/'
        'chrome-headless-shell-*/chrome-headless-shell'
    )))
    if cached:
        return cached[-1]

    for name in ('chromium', 'chromium-browser', 'google-chrome',
                 'chrome'):
        path = shutil.which(name)
        if path:
            return path


CHROME = find_headless_chrome()


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@unittest.skipUnless(os.path.exists(bundle_path()),
                     'widget bundle not built (npm run build)')
@unittest.skipUnless(CHROME, 'no headless chromium available')
@unittest.skipUnless(HAS_PIL, 'Pillow not installed')
class WidgetE2ETest(BaseNodeTest):

    def setUp(self):
        super().setUp()
        self.out_dir = os.path.join(self.build_dir, 'export_out')
        export_node(spinner_project.Spinner(), self.out_dir)

        handler = partial(QuietHandler, directory=self.out_dir)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=self.server.serve_forever,
                         daemon=True).start()
        self.addCleanup(self.server.shutdown)
        port = self.server.server_address[1]
        self.base_url = f'http://127.0.0.1:{port}/index.html'

    def screenshot(self, query):
        path = os.path.join(self.build_dir, 'shot.png')
        result = run(
            [
                CHROME,
                '--headless',
                '--no-sandbox',
                '--disable-gpu',
                '--use-angle=swiftshader',
                '--window-size=800,600',
                # Generous budget so STL fetches + first render complete
                '--virtual-time-budget=4000',
                f'--screenshot={path}',
                f'{self.base_url}?{query}',
            ],
            capture_output=True, timeout=120,
        )
        self.assertEqual(
            result.returncode, 0,
            f'chromium failed: {result.stderr.decode()[-500:]}',
        )
        image = Image.open(path).convert('RGB')
        os.remove(path)
        # Crop off the bottom control bar: the play button and the
        # slider thumb (whose position tracks ?t=) are UI, and pixel
        # assertions here are about the rendered model
        return image.crop((0, 0, image.width, image.height - 40))

    def count_pixels(self, image, predicate):
        return sum(1 for pixel in image.getdata() if predicate(*pixel))

    def test_models_render_with_their_colors(self):
        image = self.screenshot('t=0&autoplay=0')

        # The red hub (#cc4444) and blue blades (#4477cc) must both
        # cover a meaningful area; lighting shifts the exact shades,
        # so only the dominant channel is asserted.
        red = self.count_pixels(
            image, lambda r, g, b: r > 100 and r > 1.4 * g and r > 1.4 * b)
        blue = self.count_pixels(
            image, lambda r, g, b: b > 100 and b > 1.4 * r and b > 1.4 * g)

        self.assertGreater(red, 500, 'red hub not visible')
        self.assertGreater(blue, 2000, 'blue blades not visible')

    def test_time_parameter_poses_the_animation(self):
        # A 45 degree turn is asymmetric for the 3-fold symmetric
        # spinner, so the two poses must differ substantially
        at_zero = self.screenshot('t=0&autoplay=0')
        at_eighth = self.screenshot('t=0.125&autoplay=0')

        difference = ImageChops.difference(at_zero, at_eighth)
        changed = self.count_pixels(
            difference, lambda r, g, b: r + g + b > 30)

        self.assertGreater(changed, 2000,
                           'pose did not change with ?t=')

    def test_full_cycle_returns_to_start(self):
        # $t is periodic: t=0 and t=1 are the same pose (modulo
        # antialiasing noise), proving the expression is evaluated
        # rather than the frames drifting
        at_zero = self.screenshot('t=0&autoplay=0')
        at_one = self.screenshot('t=1&autoplay=0')

        difference = ImageChops.difference(at_zero, at_one)
        changed = self.count_pixels(
            difference, lambda r, g, b: r + g + b > 30)

        self.assertLess(changed, 500,
                        't=0 and t=1 should render the same pose')


HARNESS_PAGE = """<!doctype html>
<html>
  <head>
    <meta charset="utf-8">
    <style>
      html, body { margin: 0; }
      #host { width: 800px; height: 600px; position: relative; }
    </style>
  </head>
  <body>
    <div id="host"></div>
    <script src="solid-widget.js"></script>
  </body>
</html>
"""


@unittest.skipUnless(os.path.exists(bundle_path()),
                     'widget bundle not built (npm run build)')
@unittest.skipUnless(HAS_PLAYWRIGHT, 'playwright not installed')
class ViewerMountApiTest(BaseNodeTest):
    """The mount interface hosts other than an export page need.

    The pixel tests above render one URL and compare images, which
    cannot click a control, read an attribute, or see that a container
    was emptied. These drive a real page instead: they load the bundle
    with nothing to auto-mount, call mount() themselves, and assert on
    the live DOM.
    """

    def setUp(self):
        super().setUp()
        self.out_dir = os.path.join(self.build_dir, 'export_out')
        export_node(spinner_project.Spinner(), self.out_dir)
        with open(os.path.join(self.out_dir, 'harness.html'), 'w') as page:
            page.write(HARNESS_PAGE)

        handler = partial(QuietHandler, directory=self.out_dir)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=self.server.serve_forever,
                         daemon=True).start()
        self.addCleanup(self.server.shutdown)
        port = self.server.server_address[1]
        self.harness_url = f'http://127.0.0.1:{port}/harness.html'

    def in_page(self, script):
        """Run one script in a page that has the bundle but nothing
        auto-mounted, and fail on any uncaught page error."""
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(args=[
                '--no-sandbox',
                '--disable-gpu',
                '--use-angle=swiftshader',
            ])
            try:
                page = browser.new_page(
                    viewport={'width': 800, 'height': 600})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(self.harness_url)
                page.wait_for_function(
                    'typeof SolidNodeWidget !== "undefined"')
                result = page.evaluate(script)
                self.assertEqual(errors, [], f'uncaught page errors: {errors}')
                return result
            finally:
                browser.close()

    def test_dispose_leaves_the_container_empty(self):
        result = self.in_page("""async () => {
          const host = document.getElementById('host');
          const viewer = await SolidNodeWidget.mount(
            host, 'manifest.json', {});
          const mounted = host.children.length;
          viewer.dispose();
          return { mounted, after: host.children.length };
        }""")

        self.assertGreater(result['mounted'], 0, 'nothing was mounted')
        self.assertEqual(result['after'], 0,
                         'dispose() left elements in the container')

    def test_the_bundle_and_mount_handle_report_one_api_version(self):
        result = self.in_page("""async () => {
          const host = document.getElementById('host');
          const viewer = await SolidNodeWidget.mount(
            host, 'manifest.json', {});
          return {
            bundle: SolidNodeWidget.apiVersion,
            handle: viewer.apiVersion,
          };
        }""")

        self.assertIsInstance(result['bundle'], int)
        self.assertEqual(result['bundle'], result['handle'])

    def test_a_captured_view_survives_a_remount(self):
        result = self.in_page("""async () => {
          const host = document.getElementById('host');
          const first = await SolidNodeWidget.mount(
            host, 'manifest.json', {});
          // Move away from the fitted camera, so restoring is
          // distinguishable from fitting again
          const moved = {
            camera: first.view().camera.clone().multiplyScalar(2),
            target: first.view().target.clone(),
          };
          first.dispose();

          const second = await SolidNodeWidget.mount(
            host, 'manifest.json', { view: moved });
          const got = second.view();
          return {
            want: [moved.camera.x, moved.camera.y, moved.camera.z],
            got: [got.camera.x, got.camera.y, got.camera.z],
          };
        }""")

        for want, got in zip(result['want'], result['got']):
            self.assertAlmostEqual(want, got, places=4,
                                   msg='remount did not restore the view')

    def test_reload_keeps_the_maker_looking_where_they_were(self):
        result = self.in_page("""async () => {
          const host = document.getElementById('host');
          const viewer = await SolidNodeWidget.mount(
            host, 'manifest.json', {});
          const before = viewer.view();
          const want = [before.camera.x, before.camera.y, before.camera.z];
          await viewer.reload();
          const after = viewer.view();
          return {
            want,
            got: [after.camera.x, after.camera.y, after.camera.z],
          };
        }""")

        for want, got in zip(result['want'], result['got']):
            self.assertAlmostEqual(want, got, places=4,
                                   msg='reload() moved the camera')

    def test_the_host_names_the_canvas(self):
        result = self.in_page("""async () => {
          const host = document.getElementById('host');
          await SolidNodeWidget.mount(host, 'manifest.json', {
            className: 'functional-model',
            role: 'img',
            ariaLabel: 'Functional model',
          });
          const canvas = host.querySelector('canvas');
          return {
            className: canvas.className,
            role: canvas.getAttribute('role'),
            label: canvas.getAttribute('aria-label'),
          };
        }""")

        self.assertEqual(result['className'], 'functional-model')
        self.assertEqual(result['role'], 'img')
        self.assertEqual(result['label'], 'Functional model')

    def test_the_toggle_presentation_starts_collapsed(self):
        result = self.in_page("""async () => {
          const host = document.getElementById('host');
          await SolidNodeWidget.mount(host, 'manifest.json', {
            animation: 'toggle',
          });
          const toggle = host.querySelector('.timeline-toggle');
          const bar = host.querySelector('.animation-controls');
          const collapsed = {
            expanded: toggle.getAttribute('aria-expanded'),
            barVisible: bar.offsetParent !== null,
          };
          toggle.click();
          return {
            collapsed,
            expanded: toggle.getAttribute('aria-expanded'),
            barVisible: bar.offsetParent !== null,
          };
        }""")

        self.assertEqual(result['collapsed']['expanded'], 'false')
        self.assertFalse(result['collapsed']['barVisible'],
                         'the timeline was visible before it was asked for')
        self.assertEqual(result['expanded'], 'true')
        self.assertTrue(result['barVisible'],
                        'the timeline stayed hidden after the toggle')
