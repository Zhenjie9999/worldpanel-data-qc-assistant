import tempfile
import unittest
import base64
from pathlib import Path
from unittest.mock import patch

from worldpanel_qc.llm.settings import LlmSettingsStore


class LlmSettingsTests(unittest.TestCase):
    def test_round_trips_token_without_exposing_it_publicly(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LlmSettingsStore(
                Path(tmp) / "settings.json",
                protect=lambda value: base64.b64encode(value.encode("utf-8")).decode("ascii"),
                unprotect=lambda value: base64.b64decode(value).decode("utf-8"),
            )

            store.save(
                {
                    "endpoint": "http://llm.internal/chat/completions",
                    "model": "gpt-5.4",
                    "token": "secret-token",
                    "timeout_seconds": 30,
                    "enabled": True,
                    "ocr_enabled": True,
                }
            )

            self.assertEqual(store.load()["token"], "secret-token")
            self.assertNotIn("secret-token", (Path(tmp) / "settings.json").read_text(encoding="utf-8"))
            public = store.public_settings()
            self.assertNotIn("token", public)
            self.assertTrue(public["token_configured"])

    def test_warns_when_endpoint_is_plain_http(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LlmSettingsStore(
                Path(tmp) / "settings.json",
                protect=lambda value: value,
                unprotect=lambda value: value,
            )
            store.save({"endpoint": "http://llm.internal/chat/completions", "model": "gpt-5.4", "token": "x"})

            self.assertIn("trusted intranet", store.public_settings()["warning"].lower())

    def test_environment_configuration_overrides_file_without_exposing_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LlmSettingsStore(
                Path(tmp) / "settings.json",
                protect=lambda value: value,
                unprotect=lambda value: value,
            )
            store.save({"endpoint": "https://old.example/chat/completions", "model": "old", "token": "old-token"})

            with patch.dict(
                "os.environ",
                {
                    "WORLDPANEL_QC_LLM_ENDPOINT": "http://218.241.201.171:28180/jdgpt/v1/chat/completions",
                    "WORLDPANEL_QC_LLM_MODEL": "gpt-5.4",
                    "WORLDPANEL_QC_LLM_TOKEN": "env-token",
                    "WORLDPANEL_QC_LLM_TIMEOUT_SECONDS": "90",
                    "WORLDPANEL_QC_LLM_ENABLED": "1",
                    "WORLDPANEL_QC_LLM_OCR_ENABLED": "1",
                },
                clear=False,
            ):
                loaded = store.load()
                public = store.public_settings()

            self.assertEqual(loaded["endpoint"], "http://218.241.201.171:28180/jdgpt/v1/chat/completions")
            self.assertEqual(loaded["model"], "gpt-5.4")
            self.assertEqual(loaded["token"], "env-token")
            self.assertEqual(loaded["timeout_seconds"], 90)
            self.assertTrue(loaded["enabled"])
            self.assertTrue(loaded["ocr_enabled"])
            self.assertTrue(public["token_configured"])
            self.assertNotIn("token", public)
            self.assertIn("trusted intranet", public["warning"].lower())


if __name__ == "__main__":
    unittest.main()
