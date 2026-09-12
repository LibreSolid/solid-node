"""Actual Chromium module-worker parity, frame batching, UI responsiveness, pixels.

Temporary server exposes only this experiment and installed three.js assets.
It does not serve the workspace or change the viewer repository.
"""
import argparse
import functools
import http.server
import json
import threading
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.sync_api import sync_playwright
from programs import HERE, WORKSPACE
from run import EVIDENCE, compare, write

THREE = WORKSPACE / 'solid-node-viewer/solid_node_viewer/widget/node_modules/three'


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = unquote(urlsplit(path).path)
        if path.startswith('/three/'):
            candidate = (THREE / path[len('/three/'):]).resolve()
            if candidate.is_relative_to(THREE.resolve()):
                return str(candidate)
            return str(HERE / 'not-found')
        return super().translate_path(path)

    def log_message(self, *args):
        pass


def server(port=0):
    if not THREE.is_dir():
        raise RuntimeError(f'Expected installed viewer dependency absent: {THREE}')
    return http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(Handler, directory=HERE.parent))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--serve', action='store_true', help='leave the experimental page available for manual use')
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    httpd = server(args.port)
    url = f'http://127.0.0.1:{httpd.server_port}/spikes/index.html'
    print(url, flush=True)
    if args.serve:
        try:
            httpd.serve_forever()
        finally:
            httpd.server_close()
        return
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
            page = browser.new_page(viewport=dict(width=1160, height=850))
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(url)
            page.wait_for_function('window.ready === true')
            expected = json.loads((EVIDENCE / 'python-results.json').read_text())
            results = page.evaluate('() => probe.suite()')
            error = compare(expected, results)
            write('browser-gcode.json', page.evaluate('() => probe.gcode()'))
            page.screenshot(path=EVIDENCE / 'browser-initial.png')
            page.evaluate('() => probe.advance(240)')
            page.screenshot(path=EVIDENCE / 'browser-two-carries.png')
            whole = page.evaluate('() => probe.snapshot()')
            page.evaluate('() => { for (let i=0; i<100; i++) probe.renderOnly(); }')
            compare(whole, page.evaluate('() => probe.snapshot()'))
            page.evaluate('() => probe.reset()')
            # Irregular display cadence changes only publication batching.
            page.evaluate('async () => { for (const n of [1, 17, 3, 79, 2, 91, 47]) await probe.advance(n); }')
            compare(whole, page.evaluate('() => probe.snapshot()'))
            responsive = page.evaluate('''async () => {
                let beats=0; const interval=setInterval(() => beats++, 10);
                const start=performance.now(); await probe.longRun(30000);
                clearInterval(interval); return {beats, elapsed_ms:performance.now()-start};
            }''')
            assert responsive['beats'] >= 2, responsive
            assert not errors, errors
            write('browser-results.json', dict(browser=browser.version,
                three_revision=page.evaluate('probe.revision'), conformance_cases=len(results),
                max_python_browser_error=error, irregular_batches=[1, 17, 3, 79, 2, 91, 47],
                render_only_did_not_advance=True, responsive_during_worker_30000_ticks=responsive,
                page_errors=errors, renderer='headless Chromium / SwiftShader'))
            browser.close()
    finally:
        httpd.shutdown(); httpd.server_close(); thread.join()
    print('Browser parity, frame batching and render purity passed; screenshots captured.', flush=True)


if __name__ == '__main__':
    main()
