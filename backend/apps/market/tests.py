from decimal import Decimal

from rest_framework.test import APITestCase

from apps.common.testing import make_user, make_village
from apps.market.models import Category, Listing


class MarketFlowTests(APITestCase):
    def setUp(self):
        self.village = make_village()
        self.cat = Category.objects.create(slug="dairy", name_ru="Молочное", name_en="Dairy")
        self.seller = make_user("+996700000031", name="Seller")
        self.buyer = make_user("+996700000032", name="Buyer")
        self.other = make_user("+996700000033", name="Other")
        self.listing = Listing.objects.create(
            seller=self.seller, category=self.cat, title="Kymyz", price_kgs=Decimal("200"),
            unit="l", quantity=Decimal("10"), village=self.village, lat=self.village.lat, lon=self.village.lon,
        )

    def _order(self, user, qty="4"):
        self.client.force_authenticate(user)
        return self.client.post("/api/market/orders/", {"listing": self.listing.pk, "quantity": qty}, format="json")

    def test_anonymous_can_browse_but_not_see_phone(self):
        self.client.force_authenticate(None)
        r = self.client.get(f"/api/market/listings/{self.listing.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(self.seller.phone, str(r.data))

    def test_must_login_to_post_listing(self):
        r = self.client.post("/api/market/listings/", {}, format="json")
        self.assertIn(r.status_code, (401, 403))

    def test_full_order_flow_reveals_phones_only_after_accept(self):
        r = self._order(self.buyer)
        self.assertEqual(r.status_code, 201, r.data)
        oid = r.data["id"]
        self.assertIsNone(r.data["seller"]["phone"])
        self.assertIsNone(r.data["buyer"]["phone"])

        # listing phone hidden for the buyer before acceptance
        self.assertNotIn(self.seller.phone, str(self.client.get(f"/api/market/listings/{self.listing.pk}/").data))

        # a stranger can neither see nor accept it
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/market/orders/{oid}/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/market/orders/{oid}/accept/").status_code, 404)

        # buyer cannot accept their own order
        self.client.force_authenticate(self.buyer)
        self.assertEqual(self.client.post(f"/api/market/orders/{oid}/accept/").status_code, 403)

        self.client.force_authenticate(self.seller)
        r = self.client.post(f"/api/market/orders/{oid}/accept/")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["buyer"]["phone"], self.buyer.phone)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.quantity, Decimal("6.00"))

        self.client.force_authenticate(self.buyer)
        self.assertEqual(self.client.get(f"/api/market/orders/{oid}/").data["seller"]["phone"], self.seller.phone)

        # review only after completion
        self.assertEqual(self.client.post(f"/api/market/orders/{oid}/review/", {"rating": 5}, format="json").status_code, 400)
        self.client.force_authenticate(self.seller)
        self.assertEqual(self.client.post(f"/api/market/orders/{oid}/complete/").status_code, 200)
        self.client.force_authenticate(self.buyer)
        self.assertEqual(self.client.post(f"/api/market/orders/{oid}/review/", {"rating": 5, "comment": "Good"}, format="json").status_code, 201)
        self.assertEqual(self.client.post(f"/api/market/orders/{oid}/review/", {"rating": 4}, format="json").status_code, 400)

    def test_cannot_order_more_than_stock_or_own_listing(self):
        self.assertEqual(self._order(self.buyer, "99").status_code, 400)
        self.assertEqual(self._order(self.seller, "1").status_code, 400)

    def test_selling_out_marks_sold_and_cancel_restocks(self):
        oid = self._order(self.buyer, "10").data["id"]
        self.client.force_authenticate(self.seller)
        self.client.post(f"/api/market/orders/{oid}/accept/")
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.SOLD)
        self.client.force_authenticate(self.buyer)
        self.assertEqual(self.client.post(f"/api/market/orders/{oid}/cancel/").status_code, 200)
        self.listing.refresh_from_db()
        self.assertEqual((self.listing.status, self.listing.quantity), (Listing.ACTIVE, Decimal("10.00")))

    def test_decline(self):
        oid = self._order(self.buyer).data["id"]
        self.client.force_authenticate(self.seller)
        self.assertEqual(self.client.post(f"/api/market/orders/{oid}/decline/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/market/orders/{oid}/accept/").status_code, 400)

    def test_only_seller_can_edit_listing(self):
        self.client.force_authenticate(self.buyer)
        r = self.client.patch(f"/api/market/listings/{self.listing.pk}/", {"title": "x"}, format="json")
        self.assertIn(r.status_code, (403, 404))
        self.client.force_authenticate(self.seller)
        self.assertEqual(self.client.patch(f"/api/market/listings/{self.listing.pk}/", {"title": "Fresh kymyz"}, format="json").status_code, 200)
