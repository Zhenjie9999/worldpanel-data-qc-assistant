import unittest

from worldpanel_qc.auth import PasswordAuth


class PasswordAuthTests(unittest.TestCase):
    def test_disabled_auth_allows_requests_without_cookie(self):
        auth = PasswordAuth(password="")

        self.assertTrue(auth.is_authenticated(""))

    def test_login_returns_signed_cookie_and_accepts_it(self):
        auth = PasswordAuth(password="shared-secret", secret=b"test-secret", now=lambda: 1000)

        result = auth.login("shared-secret", "192.168.1.20")

        self.assertTrue(result["ok"])
        self.assertTrue(auth.is_authenticated(result["cookie"]))

    def test_wrong_password_is_rejected_and_rate_limited(self):
        auth = PasswordAuth(password="shared-secret", secret=b"test-secret", now=lambda: 1000, max_attempts=2)

        first = auth.login("wrong", "192.168.1.20")
        second = auth.login("wrong", "192.168.1.20")
        blocked = auth.login("shared-secret", "192.168.1.20")

        self.assertEqual(first["status"], "invalid_password")
        self.assertEqual(second["status"], "invalid_password")
        self.assertEqual(blocked["status"], "rate_limited")

    def test_logout_cookie_expires_session(self):
        auth = PasswordAuth(password="shared-secret")

        self.assertIn("Max-Age=0", auth.logout_cookie())


if __name__ == "__main__":
    unittest.main()
