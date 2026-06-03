from __future__ import annotations

import base64
import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse


HTTP_WARNING = "Trusted intranet testing only. HTTP traffic is not encrypted; do not use this endpoint on a public network."


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes) -> tuple[_DataBlob, ctypes.Array]:
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def protect_token(value: str) -> str:
    if not value:
        return ""
    source, source_buffer = _blob(value.encode("utf-8"))
    output = _DataBlob()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(source), "Worldpanel QC LLM token", None, None, None, 0, ctypes.byref(output)
    ):
        raise OSError("Unable to protect LLM token with Windows DPAPI.")
    try:
        encrypted = ctypes.string_at(output.pbData, output.cbData)
        return base64.b64encode(encrypted).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)
        del source_buffer


def unprotect_token(value: str) -> str:
    if not value:
        return ""
    source, source_buffer = _blob(base64.b64decode(value))
    output = _DataBlob()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output)
    ):
        raise OSError("Unable to read the protected LLM token on this Windows account.")
    try:
        return ctypes.string_at(output.pbData, output.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)
        del source_buffer


class LlmSettingsStore:
    def __init__(
        self,
        path: Path,
        protect: Callable[[str], str] = protect_token,
        unprotect: Callable[[str], str] = unprotect_token,
    ):
        self.path = Path(path)
        self._protect = protect
        self._unprotect = unprotect

    def save(self, values: dict) -> dict:
        current = self._read_raw()
        token = values.get("token")
        protected_token = current.get("protected_token", "")
        if token:
            protected_token = self._protect(str(token))
        data = {
            "endpoint": str(values.get("endpoint", current.get("endpoint", ""))).strip(),
            "model": str(values.get("model", current.get("model", ""))).strip(),
            "protected_token": protected_token,
            "timeout_seconds": int(values.get("timeout_seconds", current.get("timeout_seconds", 60))),
            "enabled": bool(values.get("enabled", current.get("enabled", False))),
            "ocr_enabled": bool(values.get("ocr_enabled", current.get("ocr_enabled", False))),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return self.public_settings()

    def load(self) -> dict:
        data = self._read_raw()
        env_endpoint = os.environ.get("WORLDPANEL_QC_LLM_ENDPOINT", "").strip()
        env_model = os.environ.get("WORLDPANEL_QC_LLM_MODEL", "").strip()
        env_token = os.environ.get("WORLDPANEL_QC_LLM_TOKEN", "")
        if env_endpoint or env_model or env_token:
            return {
                "endpoint": env_endpoint or data.get("endpoint", ""),
                "model": env_model or data.get("model", ""),
                "token": env_token or self._unprotect(data.get("protected_token", "")),
                "timeout_seconds": _env_int("WORLDPANEL_QC_LLM_TIMEOUT_SECONDS", int(data.get("timeout_seconds", 60))),
                "enabled": _env_bool("WORLDPANEL_QC_LLM_ENABLED", bool(data.get("enabled", False))),
                "ocr_enabled": _env_bool("WORLDPANEL_QC_LLM_OCR_ENABLED", bool(data.get("ocr_enabled", False))),
            }
        return {
            "endpoint": data.get("endpoint", ""),
            "model": data.get("model", ""),
            "token": self._unprotect(data.get("protected_token", "")),
            "timeout_seconds": int(data.get("timeout_seconds", 60)),
            "enabled": bool(data.get("enabled", False)),
            "ocr_enabled": bool(data.get("ocr_enabled", False)),
        }

    def public_settings(self) -> dict:
        settings = self.load()
        data = self._read_raw()
        endpoint = settings.get("endpoint", "")
        return {
            "endpoint": endpoint,
            "model": settings.get("model", ""),
            "timeout_seconds": int(settings.get("timeout_seconds", 60)),
            "enabled": bool(settings.get("enabled", False)),
            "ocr_enabled": bool(settings.get("ocr_enabled", False)),
            "token_configured": bool(settings.get("token") or data.get("protected_token")),
            "warning": HTTP_WARNING if endpoint and urlparse(endpoint).scheme.lower() == "http" else "",
        }

    def configured(self) -> bool:
        settings = self.load()
        return bool(settings["endpoint"] and settings["model"] and settings["token"])

    def _read_raw(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))
