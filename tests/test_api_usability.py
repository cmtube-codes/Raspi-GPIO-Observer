import unittest

from fastapi.testclient import TestClient

from main import app
from rpi_observer import IOs


class ApiUsabilityTests(unittest.TestCase):
    def setUp(self):
        IOs.clear()
        self.client = TestClient(app)

    def test_root_serves_web_app(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("Konfiguration ansehen", response.text)

    def test_api_lists_meaningful_endpoints(self):
        response = self.client.get("/api")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("endpoints", data)
        self.assertIn("POST /input", data["endpoints"])
        self.assertIn("POST /output", data["endpoints"])

    def test_post_config_accepts_user_friendly_payload(self):
        response = self.client.post(
            "/config",
            json={"gpio": 17, "pull_down": True, "edge": "rising"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("configured", response.json()["message"].lower())

    def test_invalid_edge_is_rejected_cleanly(self):
        response = self.client.post(
            "/config",
            json={"gpio": 17, "pull_down": True, "edge": "invalid"},
        )
        self.assertEqual(response.status_code, 422)

    def test_output_gpio_can_be_configured_and_set(self):
        response = self.client.post(
            "/output",
            json={"gpio": 18, "state": "high"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("GPIO 18", response.json()["message"])
        self.assertEqual(response.json()["state"], "high")

    def test_dashboard_is_available_as_html(self):
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("Raspi GPIO Observer", response.text)

    def test_get_config_returns_configuration_list(self):
        self.client.post("/config", json={"gpio": 11, "pull_down": True, "edge": "rising"})
        response = self.client.get("/config")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("configurations", data)
        self.assertTrue(any(entry["gpio"] == 11 for entry in data["configurations"]))


if __name__ == "__main__":
    unittest.main()
