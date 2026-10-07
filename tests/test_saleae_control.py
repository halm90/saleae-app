import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from saleae_control import SaleaeControl


class RecordingHandler(BaseHTTPRequestHandler):
    requests = []
    logic_running = False

    def do_GET(self):
        self.requests.append((self.command, self.path))
        if self.path == "/api/logic/status":
            body = json.dumps({"connected": self.logic_running}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/capture/capture-1/download?format=csv":
            body = b"timestamp,channel_0\n1,2.5\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        self.requests.append((self.command, self.path, body))
        if self.path == "/api/logic/start":
            self.logic_running = True
            response = json.dumps({"status": "started", "service": "logic2"}).encode()
        elif self.path == "/api/capture/run":
            response = json.dumps(
                {"capture_id": "capture-1", "status": "completed"}
            ).encode()
        elif self.path == "/api/acquisition/stop":
            response = json.dumps({"status": "idle"}).encode()
        elif self.path == "/api/logic/stop":
            self.logic_running = False
            response = json.dumps({"status": "stopped", "service": "logic2"}).encode()
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        return


def test_remote_client_preserves_saleae_control_interface(tmp_path: Path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), RecordingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    output_path = tmp_path / "reference.csv"

    try:
        control = SaleaeControl(
            remote_url=f"http://127.0.0.1:{server.server_port}",
            timeout=2,
        )
        control.start_up()
        control.gather_data_saleae(
            5,
            str(output_path),
            channels=[0, 1, 2],
            sample_rate=50,
        )
        control.stop_capture()
        control.cleanup()

        assert output_path.read_text() == "timestamp,channel_0\n1,2.5\n"
        requests = RecordingHandler.requests
        assert any(
            request[0] == "POST"
            and request[1] == "/api/logic/start"
            and request[2] == b'{"application_path":null}'
            for request in requests
        )
        assert any(
            request[0] == "POST" and request[1] == "/api/capture/run"
            for request in requests
        )
        assert any(
            request[0] == "POST" and request[1] == "/api/acquisition/stop"
            for request in requests
        )
        assert any(
            request[0] == "POST" and request[1] == "/api/logic/stop"
            for request in requests
        )
        assert any(
            request[0] == "GET"
            and request[1] == "/api/capture/capture-1/download?format=csv"
            for request in requests
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
