from unittest import mock

from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.alerts.models import Alert
from apps.common.testing import make_user, make_village
from apps.reports.models import HazardReport


@mock.patch("apps.common.telegram.safe_send", return_value=(True, ""))
class ReportTests(APITestCase):
    def setUp(self):
        self.village = make_village()
        self.rescuer = make_user("+996700000041", role=User.RESCUER, chat_id=900)
        self.users = [make_user(f"+99670000005{i}") for i in range(3)]

    def _report(self, user, type="smoke", dlat=0.0):
        self.client.force_authenticate(user)
        return self.client.post(
            "/api/reports/", {"type": type, "lat": self.village.lat + dlat, "lon": self.village.lon, "description": "x"},
            format="json",
        )

    def test_report_gets_village_and_notifies_rescuers(self, send):
        r = self._report(self.users[0])
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["village"], self.village.pk)
        self.assertIsNone(r.data["reporter"])  # reporter identity hidden from non-rescuers
        self.assertEqual(send.call_args_list[0].args[0], 900)
        self.assertFalse(Alert.objects.exists())

    def test_three_distinct_reporters_raise_high_alert(self, send):
        for i, u in enumerate(self.users):
            self._report(u, dlat=0.002 * i)
        alert = Alert.objects.get(hazard="fire")
        self.assertEqual((alert.level, alert.source), ("high", "report"))
        self.assertEqual(HazardReport.objects.filter(crowd_confirmed=True).count(), 3)

    def test_same_person_repeating_does_not_count(self, send):
        for _ in range(4):
            self._report(self.users[0])
        self.assertFalse(Alert.objects.exists())

    def test_rescuer_confirm_and_permission(self, send):
        rid = self._report(self.users[0]).data["id"]
        self.client.force_authenticate(self.users[1])
        self.assertEqual(self.client.post(f"/api/reports/{rid}/confirm/").status_code, 403)
        self.client.force_authenticate(self.rescuer)
        self.assertEqual(self.client.post(f"/api/reports/{rid}/confirm/").status_code, 200)
        self.assertTrue(Alert.objects.filter(hazard="fire", status="active").exists())

    def test_dismiss_does_not_alert(self, send):
        rid = self._report(self.users[0]).data["id"]
        self.client.force_authenticate(self.rescuer)
        self.assertEqual(self.client.post(f"/api/reports/{rid}/dismiss/").status_code, 200)
        self.assertFalse(Alert.objects.exists())

    def test_rejects_bad_coordinates(self, send):
        self.client.force_authenticate(self.users[0])
        r = self.client.post("/api/reports/", {"type": "smoke", "lat": 99, "lon": 0}, format="json")
        self.assertEqual(r.status_code, 400)
