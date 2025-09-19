import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import TCPServer

from llamacpp_manager.health import check_endpoint


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b"{\n  \"object\": \"list\",\n  \"data\": [],\n  \"server\": \"llama.cpp test\",\n  \"version\": \"test-1\"\n}\n"
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(server):
    with server:
        server.serve_forever()


def test_health_check():
    # Start a local HTTP server on an ephemeral port
    TCPServer.allow_reuse_address = True
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_port
    t = threading.Thread(target=run_server, args=(httpd,), daemon=True)
    t.start()

    status = check_endpoint("127.0.0.1", port, timeout_ms=500)
    assert status["up"] is True
    assert status["http_status"] == 200
    assert status["latency_ms"] >= 0

