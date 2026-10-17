from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.accounts.models import User


class PortalTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_home_calm_in_both_languages(self):
        for lang, word in (("ky", "тынч"), ("ru", "спокойно")):
            r = self.client.get(f"/api/portal/home/?village=ak-tash&lang={lang}")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.data["status"]["tone"], "calm")
            self.assertIn(word, r.data["status"]["headline"])
            self.assertEqual(r.data["village"]["elevation_m"], 2240)
            self.assertEqual(r.data["shelters"]["count"], 4)
            self.assertEqual(r.data["weather"]["condition"], "clear")
            self.assertEqual(r.data["roads"]["summary_status"], "open")
            self.assertTrue(r.data["speech"])
            self.assertEqual(len(r.data["contacts"]["community"]), 3)
            self.assertEqual(len(r.data["contacts"]["strip"]), 3)
            self.assertIsNotNone(r.data["announcement"])

    def test_home_defaults_to_ak_tash(self):
        self.assertEqual(self.client.get("/api/portal/home/").data["village"]["slug"], "ak-tash")

    def test_map_has_geometry_and_shelter_distance(self):
        self.client.force_authenticate(User.objects.get(phone="+996700000003"))
        d = self.client.get("/api/portal/map/?lang=ky").data
        self.assertEqual({z["kind"] for z in d["zones"]}, {"safe", "danger"})
        self.assertEqual(len(d["routes"][0]["path"]), 5)
        school = d["shelters"][0]
        self.assertTrue(school["is_primary"] and school["has_clinic"] and school["has_water"])
        self.assertTrue(400 <= school["distance_m"] <= 700, school["distance_m"])
        self.assertTrue(5 <= school["walk_minutes"] <= 12)
        self.assertEqual(d["home"]["label"], "№14")
        b = d["bounds"]
        self.assertTrue(b["south"] < d["home"]["lat"] < b["north"] and b["west"] < d["home"]["lon"] < b["east"])

    def test_anonymous_map_has_no_home(self):
        self.assertIsNone(self.client.get("/api/portal/map/").data["home"])

    def test_active_alert_switches_home_to_danger_with_countdown(self):
        rescuer = User.objects.get(phone="+996700000002")
        self.client.force_authenticate(rescuer)
        self.client.post("/api/alerts/create/", {"village": rescuer.village_id, "hazard": "mudflow", "level": "critical", "eta_seconds": 600}, format="json")
        self.client.force_authenticate(None)
        d = self.client.get("/api/portal/home/?village=ak-tash&lang=ru").data
        self.assertEqual(d["status"]["tone"], "danger")
        self.assertEqual(d["status"]["primary_alert"]["hazard"], "mudflow")
        self.assertTrue(500 <= d["status"]["primary_alert"]["eta_seconds_remaining"] <= 600)
        self.assertIn("Внимание", d["speech"])

    def test_config_exposes_bot_username(self):
        d = self.client.get("/api/portal/config/").data
        self.assertEqual(d["bot_username"], "JailoAppBot")
        self.assertTrue(any(v["slug"] == "ak-tash" for v in d["villages"]))


class SeededMarketTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_cards_have_badge_verified_seller_and_image_but_no_phone(self):
        r = self.client.get("/api/market/listings/?lang=ky")
        results = r.data["results"] if isinstance(r.data, dict) else r.data
        self.assertEqual(len(results), 4)
        honey = next(x for x in results if x["category"] == "honey")
        self.assertEqual(honey["tag"], "100% Табигый тоо балы")
        self.assertTrue(honey["seller"]["is_verified"])
        self.assertIsNone(honey["seller"]["phone"])
        self.assertTrue(honey["images"][0]["image"].endswith(".svg"))

    def test_four_categories_with_hints(self):
        cats = self.client.get("/api/market/categories/?lang=ky").data
        self.assertEqual([c["slug"] for c in cats], ["dairy", "meat", "honey", "livestock"])
        self.assertEqual(cats[0]["hint"], "Кымыз, сүт, май")

    def test_sell_flow_name_amount_unit_price_category(self):
        user = User.objects.get(phone="+996700000003")
        self.client.force_authenticate(user)
        r = self.client.post("/api/market/listings/", {
            "title": "Кой эти", "category": "meat", "price_kgs": "700", "unit": "kg", "quantity": "10"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["village_name"], "Ак-Таш")

    def test_livestock_listing_without_species_is_accepted(self):
        self.client.force_authenticate(User.objects.get(phone="+996700000003"))
        r = self.client.post("/api/market/listings/", {
            "title": "Тай", "category": "livestock", "price_kgs": "30000", "unit": "head", "quantity": "1"}, format="json")
        self.assertEqual(r.status_code, 201, r.data)

    def test_rockfall_report_is_accepted_and_does_not_raise_alert(self):
        self.client.force_authenticate(User.objects.get(phone="+996700000003"))
        r = self.client.post("/api/reports/", {"type": "rockfall", "lat": 42.2, "lon": 73.5}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
