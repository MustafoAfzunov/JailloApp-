from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.alerts.models import Alert, AlertDelivery, SirenCommand
from apps.common.testing import make_node, make_user, make_village
from apps.risk.engine import evaluate_village
from apps.sensors.classifier import classify, features_from_samples
from apps.sensors.models import Reading, VibrationEvent


class ClassifierTests(APITestCase):
    def test_quiet_is_noise(self):
        self.assertEqual(classify(0.01, 30.0, []).label, "noise")

    def test_single_blip_is_vehicle(self):
        self.assertEqual(classify(0.5, 40.0, []).label, "vehicle")

    def test_sustained_rumble_is_mudflow(self):
        self.assertEqual(classify(0.8, 25.0, [0.45, 0.6]).label, "mudflow")

    def test_low_frequency_is_earthquake(self):
        self.assertEqual(classify(0.4, 3.0, []).label, "earthquake")

    def test_trusted_edge_model_is_accepted(self):
        c = classify(0.5, 25.0, [], edge_label="mudflow", edge_conf=0.95)
        self.assertEqual(c.label, "mudflow")

    def test_fft_finds_dominant_frequency(self):
        import numpy as np

        t = np.arange(0, 2, 1 / 200)
        samples = (0.8 * np.sin(2 * np.pi * 25 * t)).tolist()
        rms, freq = features_from_samples(samples, 200)
        self.assertAlmostEqual(freq, 25.0, delta=1.0)
        self.assertGreater(rms, 0.4)


class IngestAndAlertChainTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.village = make_village()
        self.n1, self.k1 = make_node(self.village, "t-n1", 0.050, 0.030, 0)
        self.n2, self.k2 = make_node(self.village, "t-n2", 0.030, 0.018, 1)
        self.villager = make_user("+996700000021", village=self.village, chat_id=101)
        self.rescuer = make_user("+996700000022", role=User.RESCUER, chat_id=102)

    def _post(self, key, payload):
        return self.client.post("/api/sensors/ingest/", payload, format="json", HTTP_X_DEVICE_KEY=key)

    def _shake(self, key):
        last = None
        for rms in (0.45, 0.80, 1.20):
            last = self._post(key, {"vibration_rms": rms, "dominant_freq_hz": 25.0})
            self.assertEqual(last.status_code, 201, last.data)
        return last

    def test_ingest_requires_valid_key(self):
        self.assertIn(self.client.post("/api/sensors/ingest/", {}, format="json").status_code, (401, 403))
        self.assertIn(self._post("jk_wrong", {}).status_code, (401, 403))

    def test_ingest_validates_ranges(self):
        self.assertEqual(self._post(self.k1, {"water_level_cm": -5}).status_code, 400)

    def test_ingest_updates_node_health(self):
        self.assertEqual(self._post(self.k1, {"battery_v": 3.7}).status_code, 201)
        self.n1.refresh_from_db()
        self.assertEqual(self.n1.battery_v, 3.7)
        self.assertEqual(self.n1.status, "online")

    @mock.patch("apps.common.telegram.safe_send", return_value=(True, ""))
    def test_one_node_is_high_two_nodes_is_critical_with_siren(self, send):
        r = self._shake(self.k1)
        self.assertEqual(r.data["classification"], "mudflow")
        alert = Alert.objects.get(hazard="mudflow", status="active")
        self.assertEqual(alert.level, "high")  # single node: not yet confirmed
        self.assertFalse(SirenCommand.objects.exists())

        self._shake(self.k2)
        alert.refresh_from_db()
        self.assertEqual(alert.level, "critical")
        self.assertTrue(SirenCommand.objects.filter(alert=alert, action="on").exists())
        # one delivery per recipient per level
        self.assertEqual(AlertDelivery.objects.filter(alert=alert, level="critical", status="sent").count(), 2)
        chats = {c.args[0] for c in send.call_args_list}
        self.assertEqual(chats, {101, 102})
        self.assertIn("title", alert.texts["ru"])
        self.assertIsNotNone(alert.eta_at)

    def test_eta_uses_measured_speed_between_nodes(self):
        now = timezone.now()
        for node, minutes_ago in ((self.n1, 10), (self.n2, 4)):
            VibrationEvent.objects.create(
                node=node, classification="mudflow", confidence=0.9, rms=1.0, dominant_freq_hz=25,
                created_at=now - timedelta(minutes=minutes_ago),
            )
        result = next(r for r in evaluate_village(self.village, now=now, notify=False) if r.hazard == "mudflow")
        eta = result.inputs["eta"]
        self.assertFalse(eta["speed_assumed"])
        self.assertAlmostEqual(eta["speed_kmh"], 31.6, delta=3)
        self.assertTrue(240 <= result.eta_seconds <= 360, result.eta_seconds)

    def test_eta_with_one_node_is_flagged_as_assumed(self):
        now = timezone.now()
        VibrationEvent.objects.create(
            node=self.n1, classification="mudflow", confidence=0.9, rms=1.0, created_at=now - timedelta(minutes=1)
        )
        result = next(r for r in evaluate_village(self.village, now=now, notify=False) if r.hazard == "mudflow")
        self.assertTrue(result.inputs["eta"]["speed_assumed"])

    @mock.patch("apps.common.telegram.safe_send", return_value=(True, ""))
    def test_alert_clears_itself_after_quiet_period(self, send):
        self._shake(self.k1)
        alert = Alert.objects.get(status="active")
        VibrationEvent.objects.all().delete()
        later = timezone.now() + timedelta(minutes=45)
        evaluate_village(self.village, now=later)
        alert.refresh_from_db()
        self.assertEqual(alert.status, "resolved")

    def test_node_list_hides_secrets(self):
        data = self.client.get("/api/sensors/nodes/").data
        self.assertEqual(len(data), 2)
        self.assertNotIn("api_key_hash", data[0])
        self.assertNotIn("key", " ".join(data[0].keys()))
