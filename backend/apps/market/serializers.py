from decimal import Decimal

from rest_framework import serializers

from apps.common.constants import pick_lang
from apps.geo.models import Village

from .models import Category, ChatThread, Listing, ListingImage, Message, Order, Review


class CategorySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    hint = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["slug", "name", "hint", "name_ru", "name_ky", "name_en", "icon", "is_animal"]

    def _lang(self):
        request = self.context.get("request")
        return pick_lang(request.query_params.get("lang") if request else None)

    def get_name(self, obj):
        return obj.name_for(self._lang())

    def get_hint(self, obj):
        return (obj.hint_ky if self._lang() == "ky" else obj.hint_ru) or obj.hint_ru


class SellerSerializer(serializers.Serializer):
    """Public seller card. The phone number is added by ListingSerializer when allowed."""

    id = serializers.IntegerField()
    name = serializers.SerializerMethodField()
    village = serializers.CharField(source="village.name", default=None)
    is_verified = serializers.BooleanField()
    rating = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()

    def get_name(self, obj):
        return obj.name or "—"

    def _stats(self, obj):
        if not hasattr(obj, "_rating_cache"):
            from django.db.models import Avg, Count

            agg = obj.reviews_received.aggregate(avg=Avg("rating"), n=Count("id"))
            obj._rating_cache = (round(agg["avg"], 2) if agg["avg"] else None, agg["n"])
        return obj._rating_cache

    def get_rating(self, obj):
        return self._stats(obj)[0]

    def get_reviews(self, obj):
        return self._stats(obj)[1]


class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = ["id", "image", "order"]


class ListingSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="slug", queryset=Category.objects.all())
    category_name = serializers.SerializerMethodField()
    village = serializers.PrimaryKeyRelatedField(queryset=Village.objects.all(), required=False)
    village_name = serializers.CharField(source="village.name", read_only=True)
    images = ListingImageSerializer(many=True, read_only=True)
    seller = serializers.SerializerMethodField()
    vet_certificate_uploaded = serializers.SerializerMethodField()
    village_alert = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id", "title", "description", "category", "category_name", "price_kgs", "unit", "quantity",
            "village", "village_name", "lat", "lon", "status", "views", "tag", "place_note",
            "species", "breed", "sex", "age_months", "weight_kg", "vet_certificate",
            "vet_certificate_uploaded", "images", "seller", "village_alert", "distance_km",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "views", "created_at", "updated_at"]
        extra_kwargs = {"vet_certificate": {"write_only": True}}

    def get_category_name(self, obj):
        request = self.context.get("request")
        return obj.category.name_for(pick_lang(request.query_params.get("lang") if request else None))

    def get_vet_certificate_uploaded(self, obj):
        return bool(obj.vet_certificate)

    def get_village_alert(self, obj):
        """Highest active alert level at the seller's village (buyers see delays coming)."""
        return self.context.get("alert_levels", {}).get(obj.village_id)

    def get_distance_km(self, obj):
        return self.context.get("distances", {}).get(obj.pk)

    def get_seller(self, obj):
        data = SellerSerializer(obj.seller).data
        request = self.context.get("request")
        user = getattr(request, "user", None)
        allowed = bool(
            user and user.is_authenticated
            and (user.pk == obj.seller_id or obj.pk in self.context.get("accepted_listing_ids", set()))
        )
        data["phone"] = obj.seller.phone if allowed else None
        return data

    def validate(self, attrs):
        category = attrs.get("category") or getattr(self.instance, "category", None)
        if category and not category.is_animal:
            for field in ("species", "breed", "sex", "age_months", "weight_kg", "vet_certificate"):
                if attrs.get(field):
                    raise serializers.ValidationError({field: "Animal details only apply to livestock."})
        return attrs

    def create(self, validated_data):
        seller = validated_data["seller"]
        validated_data.setdefault("village", seller.village)
        if validated_data["village"] is None:
            raise serializers.ValidationError({"village": "Set a village on the listing or in your profile."})
        return super().create(validated_data)


class OrderSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    listing_unit = serializers.CharField(source="listing.unit", read_only=True)
    buyer = serializers.SerializerMethodField()
    seller = serializers.SerializerMethodField()
    reviewed = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "listing", "listing_title", "listing_unit", "quantity", "delivery", "note",
            "status", "buyer", "seller", "reviewed", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def _reveal(self, order):
        return order.status in (Order.ACCEPTED, Order.COMPLETED)

    def get_buyer(self, obj):
        return {"id": obj.buyer_id, "name": obj.buyer.name, "phone": obj.buyer.phone if self._reveal(obj) else None}

    def get_seller(self, obj):
        s = obj.listing.seller
        return {"id": s.pk, "name": s.name, "phone": s.phone if self._reveal(obj) else None}

    def get_reviewed(self, obj):
        return hasattr(obj, "review")

    def validate_quantity(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Quantity must be positive.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        listing = attrs["listing"]
        if listing.status != Listing.ACTIVE:
            raise serializers.ValidationError({"listing": "This listing is not available."})
        if listing.seller_id == request.user.pk:
            raise serializers.ValidationError({"listing": "You cannot order your own listing."})
        if attrs["quantity"] > listing.quantity:
            raise serializers.ValidationError({"quantity": f"Only {listing.quantity} available."})
        return attrs


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "order", "rating", "comment", "created_at"]
        read_only_fields = ["id", "order", "created_at"]


class MessageSerializer(serializers.ModelSerializer):
    mine = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "body", "mine", "created_at"]
        read_only_fields = ["id", "created_at"]

    def get_mine(self, obj):
        return obj.sender_id == self.context["request"].user.pk


class ThreadSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = ["id", "listing", "listing_title", "other_user", "last_message", "created_at"]

    def get_other_user(self, obj):
        me = self.context["request"].user
        other = obj.seller if obj.buyer_id == me.pk else obj.buyer
        return {"id": other.pk, "name": other.name or "—"}

    def get_last_message(self, obj):
        m = obj.messages.last()
        return {"body": m.body[:120], "created_at": m.created_at} if m else None
