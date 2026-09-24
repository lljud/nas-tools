from pathlib import Path
from unittest import TestCase


class JellyfinTest(TestCase):
    def test_api_requests_do_not_use_legacy_api_key_parameter(self):
        source_path = Path(__file__).resolve().parents[1] / "app/mediaserver/client/jellyfin.py"
        source = source_path.read_text(encoding="utf-8")

        self.assertNotIn("?api_key=", source)
        self.assertNotIn("&api_key=", source)
        self.assertIn("ApiKey=", source)
        self.assertIn("self._client_config.get('api_key')", source)
