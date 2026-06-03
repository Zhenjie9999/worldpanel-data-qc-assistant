import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from worldpanel_qc.llm.client import LlmClient


class _Handler(BaseHTTPRequestHandler):
    response_content = '{"status":"ok"}'
    requests = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8"))
        self.__class__.requests.append({"headers": dict(self.headers), "body": body})
        response = {
            "model": "synthetic-model",
            "choices": [{"message": {"content": self.__class__.response_content}}],
        }
        encoded = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, *args):
        return


class LlmClientTests(unittest.TestCase):
    def setUp(self):
        _Handler.response_content = '{"status":"ok"}'
        _Handler.requests = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_port}/chat/completions"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_connection_returns_structured_success(self):
        client = LlmClient(self.endpoint, "synthetic-model", "secret", timeout_seconds=3)

        result = client.test_connection()

        self.assertTrue(result["ok"])
        self.assertEqual(_Handler.requests[0]["headers"]["Authorization"], "Bearer secret")

    def test_review_candidates_parses_fenced_json(self):
        _Handler.response_content = '```json\n{"issues":[{"severity":"Medium","title":"Share total","description":"Total is 90%","evidence":"90%","recommendation":"Review","confidence":0.9}]}\n```'
        client = LlmClient(self.endpoint, "synthetic-model", "secret", timeout_seconds=3)

        result = client.review_candidates([{"type": "share_total", "total": 90}])

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["issues"][0]["title"], "Share total")

    def test_invalid_json_is_reported_without_raising(self):
        _Handler.response_content = "not-json"
        client = LlmClient(self.endpoint, "synthetic-model", "secret", timeout_seconds=3)

        result = client.review_candidates([{"type": "share_total", "total": 90}])

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "invalid_response")

    def test_review_document_chunk_requests_comprehensive_qc(self):
        _Handler.response_content = '{"issues":[]}'
        client = LlmClient(self.endpoint, "synthetic-model", "secret", timeout_seconds=3)

        result = client.review_document_chunk(
            {"file_name": "price.xlsx", "records": [{"kind": "number", "location": "Sheet1!B4", "value": 8000}]}
        )

        self.assertTrue(result["ok"])
        prompt = _Handler.requests[0]["body"]["messages"][0]["content"]
        self.assertIn("complete parsed document batch", prompt)
        self.assertIn("market-common-sense concerns", prompt)
        self.assertIn("buyers = households * penetration", prompt)
        self.assertIn("Selected category template: general_fmcg", prompt)
        self.assertIn("peer consistency", prompt)
        self.assertIn("Sheet1!B4", prompt)

    def test_review_document_chunk_uses_selected_category_guidance(self):
        _Handler.response_content = '{"issues":[]}'
        client = LlmClient(self.endpoint, "synthetic-model", "secret", timeout_seconds=3)

        client.review_document_chunk(
            {
                "file_name": "juice.xlsx",
                "category_template": "beverages",
                "category_guidance": "Check pack-size mix, promotions, and price-per-volume consistency.",
                "records": [],
            }
        )

        prompt = _Handler.requests[0]["body"]["messages"][0]["content"]
        self.assertIn("Selected category template: beverages", prompt)
        self.assertIn("Check pack-size mix, promotions, and price-per-volume consistency.", prompt)

    def test_ocr_image_uses_data_url_payload(self):
        _Handler.response_content = '{"lines":["Share 73.19%"],"issues":[]}'
        client = LlmClient(self.endpoint, "synthetic-model", "secret", timeout_seconds=3)

        result = client.ocr_image(b"png-bytes", "deck.pptx", 4)

        self.assertTrue(result["ok"])
        content = _Handler.requests[0]["body"]["messages"][0]["content"]
        self.assertEqual(content[1]["type"], "image_url")
        self.assertTrue(content[1]["image_url"]["url"].startswith("data:image/png;base64,"))


if __name__ == "__main__":
    unittest.main()
