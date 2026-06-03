import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import worldpanel_qc.web as web
from worldpanel_qc.auth import PasswordAuth


class WebAuthTests(unittest.TestCase):
    def setUp(self):
        self.original_auth = web.auth
        self.original_max_request_bytes = web.MAX_REQUEST_BYTES
        self.original_llm_settings_editable = web.LLM_SETTINGS_EDITABLE
        web.auth = PasswordAuth(password="shared-secret", secret=b"test-secret")
        web.MAX_REQUEST_BYTES = 1024
        web.LLM_SETTINGS_EDITABLE = False
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), web.AppHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        web.auth = self.original_auth
        web.MAX_REQUEST_BYTES = self.original_max_request_bytes
        web.LLM_SETTINGS_EDITABLE = self.original_llm_settings_editable

    def request(self, path, data=None, cookie=None, headers=None):
        headers = dict(headers or {})
        if data is not None:
            headers["Content-Type"] = "application/json"
        if cookie:
            headers["Cookie"] = cookie
        return urllib.request.urlopen(
            urllib.request.Request(
                self.base_url + path,
                data=json.dumps(data).encode("utf-8") if data is not None else None,
                headers=headers,
                method="POST" if data is not None else "GET",
            ),
            timeout=3,
        )

    def test_health_and_login_page_are_public_but_api_requires_login(self):
        with self.request("/api/health") as response:
            self.assertEqual(response.status, 200)
        with self.request("/login") as response:
            self.assertEqual(response.status, 200)
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/projects")
        self.assertEqual(error.exception.code, 401)

    def test_login_cookie_unlocks_business_api(self):
        with self.request("/api/auth/login", {"password": "shared-secret"}) as response:
            cookie = response.headers["Set-Cookie"].split(";", 1)[0]

        with self.request("/api/projects", cookie=cookie) as response:
            self.assertEqual(response.status, 200)

    def test_oversized_json_request_is_rejected(self):
        web.MAX_REQUEST_BYTES = 10

        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/auth/login", {"password": "shared-secret"})

        self.assertEqual(error.exception.code, 413)

    def test_authenticated_shared_user_cannot_edit_llm_settings(self):
        with self.request("/api/auth/login", {"password": "shared-secret"}) as response:
            cookie = response.headers["Set-Cookie"].split(";", 1)[0]

        with self.request("/api/runtime", cookie=cookie) as response:
            runtime = json.load(response)
        self.assertFalse(runtime["llm_settings_editable"])

        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/llm/settings", {"enabled": False}, cookie=cookie)

        self.assertEqual(error.exception.code, 403)

    def test_cloudflare_visitor_ip_is_used_for_login_rate_limit(self):
        web.auth = PasswordAuth(password="shared-secret", secret=b"test-secret", max_attempts=1)
        with self.assertRaises(urllib.error.HTTPError):
            self.request("/api/auth/login", {"password": "wrong"}, headers={"CF-Connecting-IP": "198.51.100.10"})

        with self.request(
            "/api/auth/login",
            {"password": "shared-secret"},
            headers={"CF-Connecting-IP": "198.51.100.11"},
        ) as response:
            self.assertEqual(response.status, 200)


if __name__ == "__main__":
    unittest.main()
