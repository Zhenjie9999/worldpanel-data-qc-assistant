from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from collections import defaultdict
from http.cookies import SimpleCookie


COOKIE_NAME = "worldpanel_qc_session"


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


class PasswordAuth:
    def __init__(
        self,
        password: str,
        secret: bytes | None = None,
        now=time.time,
        session_seconds: int = 12 * 60 * 60,
        max_attempts: int = 5,
        block_seconds: int = 5 * 60,
        secure_cookie: bool = False,
    ):
        self.password = str(password or "")
        self.secret = secret or os.urandom(32)
        self.now = now
        self.session_seconds = session_seconds
        self.max_attempts = max_attempts
        self.block_seconds = block_seconds
        self.secure_cookie = secure_cookie
        self.failures = defaultdict(list)

    @property
    def enabled(self) -> bool:
        return bool(self.password)

    def is_authenticated(self, cookie_header: str) -> bool:
        if not self.enabled:
            return True
        cookie = SimpleCookie()
        cookie.load(cookie_header or "")
        morsel = cookie.get(COOKIE_NAME)
        if not morsel:
            return False
        try:
            expires_text, signature = morsel.value.split(".", 1)
            expires = int(expires_text)
        except ValueError:
            return False
        expected = self._signature(expires_text)
        return expires >= int(self.now()) and hmac.compare_digest(signature, expected)

    def login(self, supplied_password: str, remote_address: str) -> dict:
        if not self.enabled:
            return {"ok": True, "status": "disabled", "cookie": self.session_cookie()}
        address = remote_address or "unknown"
        failures = self._active_failures(address)
        if len(failures) >= self.max_attempts:
            return {"ok": False, "status": "rate_limited"}
        if not hmac.compare_digest(str(supplied_password or ""), self.password):
            failures.append(self.now())
            return {"ok": False, "status": "invalid_password"}
        self.failures.pop(address, None)
        return {"ok": True, "status": "authenticated", "cookie": self.session_cookie()}

    def session_cookie(self) -> str:
        expires = str(int(self.now()) + self.session_seconds)
        value = f"{expires}.{self._signature(expires)}"
        secure = "; Secure" if self.secure_cookie else ""
        return f"{COOKIE_NAME}={value}; Path=/; HttpOnly; SameSite=Lax; Max-Age={self.session_seconds}{secure}"

    def logout_cookie(self) -> str:
        secure = "; Secure" if self.secure_cookie else ""
        return f"{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0{secure}"

    def _signature(self, expires: str) -> str:
        return _encode(hmac.new(self.secret, expires.encode("ascii"), hashlib.sha256).digest())

    def _active_failures(self, address: str) -> list[float]:
        threshold = self.now() - self.block_seconds
        self.failures[address] = [failure for failure in self.failures[address] if failure >= threshold]
        return self.failures[address]
