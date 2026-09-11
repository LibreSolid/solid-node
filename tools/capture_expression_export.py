"""Mount an existing export unchanged, drive it and photograph carry springs."""
import argparse
import functools
import json
from pathlib import Path
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import sync_playwright


PAGE = b'''<!doctype html><html><head><style>
html,body,#host{margin:0;width:100%;height:100%;overflow:hidden;background:#eee}
</style></head><body><div id="host"></div><script src="solid-widget.js"></script>
<script>SolidNodeWidget.mount('#host','manifest.json',{
animation:'external',driverControls:'none',autoplay:false}).then(h=>window.probe=h)
.catch(e=>window.failure=String(e));</script></body></html>'''


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/probe.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(PAGE)
        else:
            super().do_GET()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('export', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1', 0),
                                functools.partial(Handler, directory=str(args.export)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(args=['--use-gl=angle',
                '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
            page = browser.new_page(viewport=dict(width=1400, height=1000))
            page.set_default_timeout(300000)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{server.server_port}/probe.html')
            page.wait_for_function('window.probe || window.failure')
            assert not page.evaluate('window.failure'), page.evaluate('window.failure')
            assembly = page.evaluate('window.probe.assembly()')
            (args.output/'assembly.json').write_text(json.dumps(assembly, indent=2))
            page.evaluate('() => new Promise(r => requestAnimationFrame(()=>requestAnimationFrame(r)))')
            page.screenshot(path=str(args.output/'whole-rest.png'))
            # Focus a result-carry spring using the viewer's own assembly path.
            def springs(node):
                if 'spring' in node['name'].lower():
                    yield node
                for child in node['children']:
                    yield from springs(child)
            candidates = list(springs(assembly))
            chosen = next(n for n in candidates if 'results_tens_lever_assembly_1' in n['path'])
            page.evaluate('path => window.probe.setRoot(path)', chosen['path'])
            states = []
            for turn in (0, .3, .7, .99, 1):
                state = dict(operand=1, initial_result=9, crank_turns=turn)
                page.evaluate('s => {for(const [k,v] of Object.entries(s)) window.probe.setDriver(k,v)}', state)
                page.evaluate('() => new Promise(r => requestAnimationFrame(()=>requestAnimationFrame(r)))')
                actual = page.evaluate('keys => Object.fromEntries(keys.map(k=>[k,window.probe.driver(k)]))', list(state))
                assert actual == state
                name = f'spring-carry-{turn}.png'
                page.screenshot(path=str(args.output/name))
                states.append(dict(state=state, screenshot=name))
            assert not errors, errors
            report = dict(browser=browser.version, api=page.evaluate('window.probe.apiVersion'),
                          spring=chosen, states=states, page_errors=errors)
            (args.output/'browser.json').write_text(json.dumps(report, indent=2)+'\n')
            print(json.dumps(report, indent=2))
            page.evaluate('window.probe.dispose()')
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == '__main__':
    main()
