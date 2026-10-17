from unittest import mock

from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.alerts.models import Alert, SafeCheckin, SirenCommand
from apps.common.testing import make_node, make_user, make_village


@mock.patch("apps.common.telegram.safe_send", return_value=(True, ""))
class AlertApiTests(APITestCase):
    def setUp(self):
        self.v1, self.v2 = make_village(), make_village("other", "Other", 42.0, 74.0)
        self.rescuer = make_user("+996700000061", role=User.RESCUER)
        self.villager = make_user("+996700000062", village=self.v1, chat_id=61)
        self.far = make_user("+996700000063", village=self.v2, chat_id=62)
        self.gw, self.gw_key = make_node(self.v1, "t-gw", 0.0, 0.0, 0, kind="gateway")
        self.body = {"village": self.v1.pk, "hazard": "flood", "level": "critical"}

    def test_only_rescuers_create(self, send):
        self.client.force_authenticate(self.villager)
        self.assertEqual(self.client.post("/api/alerts/create/", self.body, format="json").status_code, 403)

    def test_critical_notifies_only_nearby_users_and_queues_siren(self, send):
        self.client.force_authenticate(self.rescuer)
        r = self.client.post("/api/alerts/create/", self.body, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        chats = {c.args[0] for c in send.call_args_list}
        self.assertIn(61, chats)
        self.assertNotIn(62, chats)
        self.assertTrue(SirenCommand.objects.filter(village=self.v1, action="on").exists())

    def test_simulated_alert_is_flagged(self, send):
        self.client.force_authenticate(self.rescuer)
        r = self.client.post("/api/alerts/simulate/", self.body, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Alert.objects.get().source, "simulated")

    def test_public_active_list_resolve_and_safe_checkin(self, send):
        self.client.force_authenticate(self.rescuer)
        aid = self.client.post("/api/alerts/create/", self.body, format="json").data["id"]
        self.client.force_authenticate(None)
        self.assertEqual(len(self.client.get("/api/alerts/active/").data), 1)
        self.client.force_authenticate(self.villager)
        self.assertEqual(self.client.post(f"/api/alerts/{aid}/safe/", {}, format="json").status_code, 200)
        self.assertEqual(SafeCheckin.objects.count(), 1)
        self.assertEqual(self.client.post(f"/api/alerts/{aid}/resolve/").status_code, 403)
        self.client.force_authenticate(self.rescuer)
        self.assertEqual(self.client.post(f"/api/alerts/{aid}/resolve/").status_code, 200)
        self.client.force_authenticate(None)
        self.assertEqual(len(self.client.get("/api/alerts/active/").data), 0)
        # resolving switches the siren off
        self.assertTrue(SirenCommand.objects.filter(action="off").exists())

    def test_repeat_create_updates_instead_of_duplicating(self, send):
        self.client.force_authenticate(self.rescuer)
        self.client.post("/api/alerts/create/", self.body, format="json")
        self.client.post("/api/alerts/create/", self.body, format="json")
        self.assertEqual(Alert.objects.filter(status="active").count(), 1)
        # and nobody is messaged twice for the same level
        self.assertEqual(sum(1 for c in send.call_args_list if c.args[0] == 61), 1)

    def test_gateway_polls_and_acks_its_own_village_only(self, send):
        self.client.force_authenticate(self.rescuer)
        self.client.post("/api/alerts/create/", self.body, format="json")
        self.client.force_authenticate(None)
        self.assertIn(self.client.get("/api/alerts/siren/pending/").status_code, (401, 403))
        r = self.client.get("/api/alerts/siren/pending/", HTTP_X_DEVICE_KEY=self.gw_key)
        self.assertEqual(r.status_code, 200)
        self.assertEqual([c["action"] for c in r.data], ["on"])
        cid = r.data[0]["id"]
        self.assertTrue(self.client.post(f"/api/alerts/siren/{cid}/ack/", HTTP_X_DEVICE_KEY=self.gw_key).data["acked"])
        self.assertEqual(self.client.get("/api/alerts/siren/pending/", HTTP_X_DEVICE_KEY=self.gw_key).data, [])
