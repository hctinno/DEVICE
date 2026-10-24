"""Loopback-only intake and control-source UI. No equipment or mutation endpoints."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import json
from pathlib import Path
import re
import threading
from urllib.parse import parse_qsl, unquote, urlsplit

from .ui_read_model import IntakeReadModel, ReadModelError

ASSETS = {
    '/': ('index.html', 'text/html; charset=utf-8'),
    '/styles.css': ('styles.css', 'text/css; charset=utf-8'),
    '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
    '/model.mjs': ('model.mjs', 'text/javascript; charset=utf-8'),
    '/intake_flow_model.mjs': ('intake_flow_model.mjs', 'text/javascript; charset=utf-8'),
    '/virtual_fleet/harness_model.mjs': ('virtual_fleet/harness_model.mjs', 'text/javascript; charset=utf-8'),
    '/control-sources': ('control_sources/index.html', 'text/html; charset=utf-8'),
    '/control-sources/': ('control_sources/index.html', 'text/html; charset=utf-8'),
    '/control-sources/styles.css': ('control_sources/styles.css', 'text/css; charset=utf-8'),
    '/control-sources/app.js': ('control_sources/app.js', 'text/javascript; charset=utf-8'),
    '/control-sources/model.mjs': ('control_sources/model.mjs', 'text/javascript; charset=utf-8'),
}
FRONTEND = Path(__file__).resolve().parents[1] / 'frontend'
_ID = re.compile(r'[A-Za-z0-9_.-]{1,150}', re.ASCII)
_SCOPES = {'included', 'excluded_passive', 'identity_unresolved', 'needs_scope_review'}


def _catalog_query(raw):
    # BaseHTTPRequestHandler decodes request-target bytes as ISO-8859-1.
    raw_bytes = raw.encode('latin-1')
    if len(raw_bytes) > 4096:
        raise ValueError('catalog_invalid_query')
    raw = raw_bytes.decode('utf-8', errors='strict')
    if re.search(r'%(?![0-9A-Fa-f]{2})', raw):
        raise ValueError('catalog_invalid_query')
    pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True,
                      encoding='utf-8', errors='strict', max_num_fields=8)
    result = {}
    for key, value in pairs:
        if key in result or key not in {'query', 'scope', 'model_id', 'equipment_id', 'profile_id', 'offset', 'limit'}:
            raise ValueError('catalog_invalid_query')
        if key in {'offset', 'limit'}:
            if not re.fullmatch(r'[0-9]+', value, re.ASCII):
                raise ValueError('catalog_invalid_query')
            value = int(value)
            if (key == 'offset' and not 0 <= value <= 1000000) or (key == 'limit' and not 1 <= value <= 100):
                raise ValueError('catalog_invalid_query')
        elif key == 'query':
            if len(value) > 200:
                raise ValueError('catalog_invalid_query')
        elif key == 'scope':
            if value not in _SCOPES:
                raise ValueError('catalog_invalid_query')
        elif not _ID.fullmatch(value):
            raise ValueError('catalog_invalid_query')
        result[key] = value
    return result


def create_server(workspace, host='127.0.0.1', port=8765):
    if host != '127.0.0.1':
        raise ValueError('The UI server only accepts the loopback host 127.0.0.1')
    model = IntakeReadModel(workspace)
    catalog_instance = None
    catalog_lock = threading.Lock()

    def catalog():
        nonlocal catalog_instance
        with catalog_lock:
            if catalog_instance is None:
                module = importlib.import_module('.control_source_catalog', __package__)
                # Publish only a successfully constructed immutable snapshot.
                catalog_instance = module.ControlSourceCatalog()
            return catalog_instance

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # No document names or source text in the web-server log.
            pass

        def send_payload(self, status, content, content_type='application/json; charset=utf-8'):
            if not isinstance(content, bytes):
                content = json.dumps(content, ensure_ascii=False, allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy',
                             "default-src 'none'; script-src 'self'; style-src 'self'; "
                             "connect-src 'self'; img-src 'self'; font-src 'self'; "
                             "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(content)

        def error(self, status, code):
            self.send_payload(status, {'error': {'code': code}})

        def allowed_request(self):
            server_port = self.server.server_port
            hosts = {f'127.0.0.1:{server_port}', f'localhost:{server_port}'}
            if server_port == 80:
                hosts.update({'127.0.0.1', 'localhost'})
            return (self.headers.get('Host') in hosts
                    and self.headers.get('Origin') in {None, *(f'http://{name}' for name in hosts)}
                    and self.headers.get('Sec-Fetch-Site') != 'cross-site')

        def do_GET(self):
            if not self.allowed_request():
                return self.error(403, 'local_origin_required')
            try:
                parsed = urlsplit(self.path)
                if re.search(r'%(?![0-9A-Fa-f]{2})', parsed.path):
                    raise ValueError('invalid_path')
                path = unquote(parsed.path, encoding='utf-8', errors='strict')
            except ValueError:
                return self.error(404, 'route_not_found')
            if parsed.fragment or parsed.scheme or parsed.netloc or ('?' in self.path and path != '/api/control-sources'):
                return self.error(404, 'route_not_found')
            if path == '/api/control-sources':
                try:
                    filters = _catalog_query(parsed.query)
                except (ValueError, UnicodeError):
                    return self.error(400, 'catalog_invalid_query')
                return self.read_catalog('find_items', **filters)
            if path == '/api/control-sources/summary':
                return self.read_catalog('summary')
            if path.startswith('/api/control-sources/'):
                item_id = path[len('/api/control-sources/'):]
                if not _ID.fullmatch(item_id):
                    return self.error(400, 'catalog_invalid_query')
                return self.read_catalog('detail', item_id)
            if path in ASSETS:
                filename, content_type = ASSETS[path]
                try:
                    return self.send_payload(200, (FRONTEND / filename).read_bytes(), content_type)
                except OSError:
                    return self.error(503, 'asset_unavailable')
            if path == '/api/intakes':
                intake_id = None
                fixture_runs = False
            else:
                match = re.fullmatch(r'/api/intakes/([A-Za-z0-9][A-Za-z0-9_.-]{0,149})(/fixture-runs)?', path)
                if match is None:
                    return self.error(404, 'route_not_found')
                intake_id = match[1]
                fixture_runs = bool(match[2])
            try:
                self.send_payload(200, model.fixture_runs(intake_id) if fixture_runs else model.snapshot(intake_id))
            except ReadModelError as exc:
                self.error(404 if exc.code == 'intake_not_found' else 503, exc.code)
            except (OSError, ValueError):
                self.error(503, 'store_unavailable')

        def read_catalog(self, method, *args, **kwargs):
            try:
                payload = getattr(catalog(), method)(*args, **kwargs)
                return self.send_payload(200, payload)
            except Exception as exc:
                try:
                    code = getattr(exc, 'code', None) if isinstance(exc, ValueError) else None
                except Exception:
                    code = None
                if type(code) is not str:
                    code = None
                if code == 'catalog_item_not_found':
                    return self.error(404, code)
                if code == 'catalog_invalid_query':
                    return self.error(400, code)
                return self.error(503, 'catalog_unavailable')

        do_HEAD = do_GET

        def reject_write(self):
            self.error(405, 'read_only')

        do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = reject_write

    return ThreadingHTTPServer((host, port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, help='Existing labflow state directory')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('port must be between 0 and 65535')
    server = create_server(args.workspace, port=args.port)
    print(f'DGM AutoLab intake UI: http://127.0.0.1:{server.server_port} (read only)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
