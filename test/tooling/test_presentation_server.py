"""Public-file isolation and correct media seeking for the local deck server."""

import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread

from scripts.serve_presentation import ROOT, Handler, byte_range


class PresentationServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.worker = Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=2)

    def request(self, method, path, headers=None):
        connection = HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_only_allowlisted_files_are_served(self):
        for path in ('/not-public.txt', '/../backend/app/main.py', '/%2e%2e/backend/app/main.py'):
            with self.subTest(path=path):
                self.assertEqual(self.request('GET', path)[0], 404)

    def test_root_redirect_preserves_relative_asset_resolution(self):
        status, headers, body = self.request('GET', '/')
        self.assertEqual((status, body), (302, b''))
        self.assertEqual(headers['Location'], '/presentation/kou-presentation.html')

    def test_head_has_length_and_no_body(self):
        status, headers, body = self.request('HEAD', '/presentation/presentation-content.js')
        self.assertEqual(status, 200)
        self.assertEqual(int(headers['Content-Length']), (ROOT / 'presentation/presentation-content.js').stat().st_size)
        self.assertEqual(body, b'')

    def test_video_range_returns_exact_bytes(self):
        status, headers, body = self.request('GET', '/outputs/kou-revisit-intro-v13.mp4', {'Range': 'bytes=32-63'})
        self.assertEqual(status, 206)
        self.assertEqual(headers['Content-Length'], '32')
        self.assertEqual(body, (ROOT / 'outputs/kou-revisit-intro-v13.mp4').read_bytes()[32:64])

    def test_invalid_range_is_rejected(self):
        status, headers, body = self.request('GET', '/outputs/kou-revisit-intro-v13.mp4', {'Range': 'bytes=999999999-1000000000'})
        self.assertEqual((status, body), (416, b''))
        self.assertTrue(headers['Content-Range'].startswith('bytes */'))

    def test_range_boundaries(self):
        self.assertEqual(byte_range('bytes=-3', 10), (7, 9))
        self.assertEqual(byte_range('bytes=7-', 10), (7, 9))
        self.assertEqual(byte_range('bytes=0-999', 10), (0, 9))
        for value in ('bytes=-0', 'bytes=-', 'bytes=4-2', 'bytes=0-1,3-4'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                byte_range(value, 10)


if __name__ == '__main__':
    unittest.main()
