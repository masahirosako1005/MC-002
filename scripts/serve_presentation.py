"""Serve only public presentation files on loopback, including video seeking."""

import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = {
    '/': 'presentation/kou-presentation.html',
    '/presentation/kou-presentation.html': 'presentation/kou-presentation.html',
    '/presentation/presentation-content.js': 'presentation/presentation-content.js',
    '/presentation/speaker-script.txt': 'presentation/speaker-script.txt',
    '/outputs/kou-revisit-intro-v13.mp4': 'outputs/kou-revisit-intro-v13.mp4',
    '/outputs/kou-revisit-intro-v13-ja.vtt': 'outputs/kou-revisit-intro-v13-ja.vtt',
    '/frontend/public/art/wa/washi-paper-v1.webp': 'frontend/public/art/wa/washi-paper-v1.webp',
    '/frontend/public/art/wa/travel-woodcut-v1-960.webp': 'frontend/public/art/wa/travel-woodcut-v1-960.webp',
    '/frontend/public/fonts/yujimai/YujiMai-Regular.woff2': 'frontend/public/fonts/yujimai/YujiMai-Regular.woff2',
    '/artifacts/video-revisit/v13/final/decoded-01-login_before.png': 'artifacts/video-revisit/v13/final/decoded-01-login_before.png',
}
for name in ('program-progress.jpg', 'rank-phone.jpg', 'zone-coupon.jpg',
             'city-dashboard.jpg', 'washi-paper.png', 'travel-woodcut.png'):
    PUBLIC_FILES[f'/presentation/assets/current/{name}'] = f'presentation/assets/current/{name}'
for name in ('planning-friction-v1.png', 'shared-journey-v1.png'):
    PUBLIC_FILES[f'/presentation/assets/opening/{name}'] = f'presentation/assets/opening/{name}'
for name in ('DESIGN.md', 'docs/COMMUNITY-UX-RATIONALE.md',
             'docs/JOURNEY-PROGRAMS-CONTRACT.md', 'docs/DAYTRIP-ROUTES.md',
             'docs/CITY-DASHBOARD-ACCEPTANCE.md', 'docs/contracts/REFLECTIONS-CONTRACT.md',
             'docs/evaluation-frameworks/EV02-REPORT.md', 'docs/REVISIT-VIDEO.md',
             'artifacts/survey-content-summary.json'):
    PUBLIC_FILES['/' + name] = name


def byte_range(value, size):
    """Return a valid inclusive single range; reject malformed/empty ranges."""
    match = re.fullmatch(r'bytes=(\d{0,20})-(\d{0,20})', value)
    if not match or size <= 0:
        raise ValueError('Invalid range')
    first, last = match.groups()
    if not first:
        if not last or int(last) <= 0:
            raise ValueError('Invalid suffix')
        return max(0, size - int(last)), size - 1
    start = int(first)
    end = min(int(last), size - 1) if last else size - 1
    if start >= size or start > end:
        raise ValueError('Unsatisfiable range')
    return start, end


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_file(False)

    def do_HEAD(self):
        self.send_file(True)

    def send_file(self, head_only):
        requested_path = unquote(urlsplit(self.path).path)
        if requested_path == '/':
            self.send_response(302)
            self.send_header('Location', '/presentation/kou-presentation.html')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        name = PUBLIC_FILES.get(requested_path)
        if name is None:
            self.send_error(404)
            return
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            self.send_error(404)
            return
        size = path.stat().st_size
        start, end, status = 0, size - 1, 200
        requested = self.headers.get('Range')
        if requested:
            try:
                start, end = byte_range(requested, size)
                status = 206
            except ValueError:
                self.send_response(416)
                self.send_header('Content-Range', f'bytes */{size}')
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
        self.send_response(status)
        self.send_header('Content-Type', mimetypes.guess_type(path)[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(max(0, end - start + 1)))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if status == 206:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        if head_only:
            return
        self.stream_file(path, start, end)

    def stream_file(self, path, start, end):
        try:
            with path.open('rb') as source:
                source.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = source.read(min(remaining, 65536))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # Navigation or seeking may cancel an in-flight video request.

    def log_message(self, *_args):
        pass  # Do not record requested paths or browser identifiers.


if __name__ == '__main__':
    mimetypes.add_type('text/javascript', '.js')
    mimetypes.add_type('text/vtt', '.vtt')
    mimetypes.add_type('font/woff2', '.woff2')
    print('http://127.0.0.1:8093/presentation/kou-presentation.html', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8093), Handler).serve_forever()
