from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.models import OTPCode, User
from apps.accounts.phone import normalize_phone
from apps.common.testing import make_user
from apps.telegrambot.handlers import handle_update


class PhoneTests(APITestCase):
    def test_normalize(self):
        self.assertEqual(normalize_phone("0700 123 456"), "+996700123456")
        self.assertEqual(normalize_phone("700123456"), "+996700123456")
        self.assertEqual(normalize_phone("+996 (700) 123-456"), "+996700123456")
        with self.assertRaises(ValueError):
            normalize_phone("123")


@override_settings(OTP_RESEND_SECONDS=0, DEBUG=True, OTP_EXPOSE_IN_DEBUG=True)
class OTPFlowTests(APITestCase):
    def setUp(self):
        cache.clear()

    def _request(self, phone="0700123456"):
        return self.client.post("/api/auth/otp/request/", {"phone": phone}, format="json")

    def test_login_creates_user_and_returns_tokens(self):
        r = self._request()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["channel"], "dev")
        r = self.client.post(
            "/api/auth/otp/verify/",
            {"phone": "+996700123456", "code": r.data["dev_code"], "name": "Aibek"},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(r.data["is_new"])
        self.assertEqual(r.data["user"]["phone"], "+996700123456")
        me = self.client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["name"], "Aibek")

    def test_code_is_single_use(self):
        code = self._request().data["dev_code"]
        body = {"phone": "+996700123456", "code": code}
        self.assertEqual(self.client.post("/api/auth/otp/verify/", body, format="json").status_code, 200)
        self.assertEqual(self.client.post("/api/auth/otp/verify/", body, format="json").status_code, 400)

    def test_wrong_code_and_attempt_limit(self):
        self._request()
        for _ in range(5):
            r = self.client.post("/api/auth/otp/verify/", {"phone": "+996700123456", "code": "000000"}, format="json")
            self.assertEqual(r.status_code, 400)
        self.assertEqual(OTPCode.objects.get().attempts, 5)
        r = self.client.post("/api/auth/otp/verify/", {"phone": "+996700123456", "code": "000000"}, format="json")
        self.assertIn("Too many", str(r.data))

    def test_invalid_phone_rejected(self):
        self.assertEqual(self._request("12").status_code, 400)

    @override_settings(OTP_RESEND_SECONDS=60)
    def test_resend_is_rate_limited(self):
        self.assertEqual(self._request().status_code, 200)
        self.assertEqual(self._request().status_code, 429)

    @override_settings(DEBUG=False)
    def test_code_goes_to_telegram_when_linked_and_is_never_returned(self):
        make_user("+996700123456", chat_id=777)
        with mock.patch("apps.common.telegram.safe_send", return_value=(True, "")) as send:
            r = self._request()
        self.assertEqual(r.data["channel"], "telegram")
        self.assertNotIn("dev_code", r.data)
        self.assertEqual(send.call_args[0][0], 777)

    @override_settings(DEBUG=False)
    def test_unlinked_user_without_dev_echo_gets_no_code_in_response(self):
        r = self._request()
        self.assertEqual(r.data["channel"], "none")
        self.assertFalse(r.data["sent"])
        self.assertNotIn("dev_code", r.data)


class WatchedLocationTests(APITestCase):
    def test_crud_and_isolation(self):
        a, b = make_user("+996700000010"), make_user("+996700000011")
        self.client.force_authenticate(a)
        r = self.client.post("/api/auth/watched-locations/", {"name": "Pasture", "lat": 41.3, "lon": 72.9, "radius_km": 12}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.client.force_authenticate(b)
        self.assertEqual(len(self.client.get("/api/auth/watched-locations/").data), 0)


class BotLinkingTests(APITestCase):
    def _contact(self, chat_id, user_id, phone="996700555111"):
        return {
            "message": {
                "chat": {"id": chat_id, "type": "private"},
                "from": {"id": chat_id, "language_code": "ru"},
                "contact": {"phone_number": phone, "user_id": user_id, "first_name": "Test"},
            }
        }

    def test_sharing_own_number_links_account(self):
        with mock.patch("apps.common.telegram.safe_send", return_value=(True, "")):
            handle_update(self._contact(555, 555))
        user = User.objects.get(phone="+996700555111")
        self.assertEqual(user.telegram_chat_id, 555)

    def test_forwarded_contact_is_rejected(self):
        with mock.patch("apps.common.telegram.safe_send", return_value=(True, "")):
            handle_update(self._contact(555, 999))
        self.assertFalse(User.objects.filter(phone="+996700555111").exists())
