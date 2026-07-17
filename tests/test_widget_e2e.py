# Solid Node - A framework for mechanical CAD projects
# Copyright (C) 2023-2026 Luis Henrique Cassis Fagundes
# SPDX-License-Identifier: Apache-2.0

"""End-to-end tests for the export widget: export the spinner_project
fixture, serve the output directory over HTTP, render it in headless
chromium and assert on the pixels -- models load with their colors,
and the ?t= URL parameter actually poses the $t animation.

These tests need artifacts a plain python environment may not have,
and skip when missing:
- the widget bundle (dist/solid-widget.js, built by npm)
- a headless chromium (playwright's cache, $SOLID_HEADLESS_CHROME,
  or a chromium/chrome on PATH)
- Pillow, for pixel assertions
"""

import glob
import os
import shutil
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from subprocess import run

from solid_node.core.export import export_node, WIDGET_BUNDLE

from .base import BaseNodeTest
from . import spinner_project

try:
    from PIL import Image, ImageChops
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


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


@unittest.skipUnless(os.path.exists(WIDGET_BUNDLE),
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
