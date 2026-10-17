from decimal import Decimal

from django.db import transaction
from django.db.models import F, Q
from django_filters import rest_framework as filters
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import SAFE_METHODS, AllowAny, BasePermission, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.alerts.models import Alert
from apps.common.constants import LEVEL_RANK
from apps.common.geo import haversine_km
from apps.common.notify import notify_user

from .models import Category, ChatThread, Listing, ListingImage, Message, Order, Review
from .serializers import (
    CategorySerializer,
    ListingImageSerializer,
    ListingSerializer,
    MessageSerializer,
    OrderSerializer,
    ReviewSerializer,
    ThreadSerializer,
)

MAX_IMAGES = 6


class IsSellerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or obj.seller_id == request.user.pk


class ListingFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category__slug")
    region = filters.CharFilter(field_name="village__region", lookup_expr="iexact")
    min_price = filters.NumberFilter(field_name="price_kgs", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price_kgs", lookup_expr="lte")

    class Meta:
        model = Listing
        fields = ["category", "village", "region", "species", "status", "seller", "min_price", "max_price"]


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None
    lookup_field = "slug"


class ListingViewSet(viewsets.ModelViewSet):
    """Village marketplace. Public to browse; sign in to sell or order.

    Useful query params: category, village, region, species, min_price, max_price, search,
    ordering (price_kgs, -created_at, views, distance), lat+lon (adds distance_km),
    radius_km (with lat+lon), mine=1, lang.
    """

    serializer_class = ListingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsSellerOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_class = ListingFilter
    search_fields = ["title", "description", "breed"]
    ordering_fields = ["price_kgs", "created_at", "views"]

    def get_queryset(self):
        qs = Listing.objects.select_related("seller", "seller__village", "category", "village").prefetch_related("images")
        params = self.request.query_params
        user = self.request.user
        if params.get("mine") and user.is_authenticated:
            return qs.filter(seller=user)
        if self.action == "list" and "status" not in params:
            qs = qs.filter(status=Listing.ACTIVE)
        return qs

    # -- context: alert levels per village, phone visibility, distances
    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        levels = {}
        for village_id, level in Alert.objects.filter(status=Alert.ACTIVE).values_list("village_id", "level"):
            if village_id not in levels or LEVEL_RANK[level] > LEVEL_RANK[levels[village_id]]:
                levels[village_id] = level
        ctx["alert_levels"] = levels
        user = self.request.user
        if user.is_authenticated:
            ctx["accepted_listing_ids"] = set(
                Order.objects.filter(buyer=user, status__in=[Order.ACCEPTED, Order.COMPLETED]).values_list("listing_id", flat=True)
            )
        return ctx

    def _origin(self):
        try:
            return float(self.request.query_params["lat"]), float(self.request.query_params["lon"])
        except (KeyError, ValueError):
            return None

    def _distance(self, obj, origin):
        lat = obj.lat if obj.lat is not None else obj.village.lat
        lon = obj.lon if obj.lon is not None else obj.village.lon
        return haversine_km(origin[0], origin[1], lat, lon)

    def list(self, request, *args, **kwargs):
        origin = self._origin()
        if origin is None:
            return super().list(request, *args, **kwargs)

        items = list(self.filter_queryset(self.get_queryset())[:500])
        distances = {o.pk: round(self._distance(o, origin), 1) for o in items}
        try:
            radius = float(request.query_params["radius_km"])
            items = [o for o in items if distances[o.pk] <= radius]
        except (KeyError, ValueError):
            pass
        if request.query_params.get("ordering") == "distance":
            items.sort(key=lambda o: distances[o.pk])
        page = self.paginate_queryset(items)
        ctx = self.get_serializer_context()
        ctx["distances"] = distances
        serializer = self.get_serializer(page if page is not None else items, many=True, context=ctx)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.seller_id != getattr(request.user, "pk", None):
            Listing.objects.filter(pk=obj.pk).update(views=F("views") + 1)
            obj.views += 1
        return Response(self.get_serializer(obj).data)

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)

    def perform_destroy(self, instance):
        # keep history when orders exist; otherwise really delete
        if instance.orders.exists():
            instance.status = Listing.CLOSED
            instance.save(update_fields=["status"])
        else:
            instance.delete()

    @action(detail=True, methods=["post"], url_path="images", permission_classes=[IsAuthenticated, IsSellerOrReadOnly])
    def add_image(self, request, pk=None):
        """Upload a photo (multipart field `image`). Max 6 per listing."""
        listing = self.get_object()
        if listing.images.count() >= MAX_IMAGES:
            raise ValidationError({"image": f"At most {MAX_IMAGES} photos per listing."})
        s = ListingImageSerializer(data={"image": request.data.get("image"), "order": listing.images.count()})
        s.is_valid(raise_exception=True)
        if s.validated_data["image"].size > 8 * 1024 * 1024:
            raise ValidationError({"image": "Photo must be under 8 MB."})
        s.save(listing=listing)
        return Response(s.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"images/(?P<image_id>\d+)", permission_classes=[IsAuthenticated, IsSellerOrReadOnly])
    def delete_image(self, request, pk=None, image_id=None):
        listing = self.get_object()
        deleted, _ = listing.images.filter(pk=image_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT if deleted else status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def chat(self, request, pk=None):
        """Start (or open) a chat with the seller about this listing."""
        listing = self.get_object()
        if listing.seller_id == request.user.pk:
            raise ValidationError("You cannot chat with yourself.")
        thread, _ = ChatThread.objects.get_or_create(
            listing=listing, buyer=request.user, defaults={"seller": listing.seller}
        )
        return Response(ThreadSerializer(thread, context={"request": request}).data)


class OrderViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Order requests. No online payment: buyer and seller agree on payment when they meet.
    Phone numbers are shared only after the seller accepts."""

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "listing"]

    def get_queryset(self):
        user = self.request.user
        qs = Order.objects.select_related("listing", "listing__seller", "buyer")
        role = self.request.query_params.get("role")
        if role == "buyer":
            return qs.filter(buyer=user)
        if role == "seller":
            return qs.filter(listing__seller=user)
        return qs.filter(Q(buyer=user) | Q(listing__seller=user))

    def perform_create(self, serializer):
        order = serializer.save(buyer=self.request.user)
        listing = order.listing
        notify_user(
            listing.seller,
            f"🛒 New order for «{listing.title}»: {order.quantity} {listing.unit} "
            f"from {self.request.user.name or self.request.user.phone}. Open Jailo to accept or decline.",
        )

    def _seller_only(self, order):
        if order.listing.seller_id != self.request.user.pk:
            raise PermissionDenied("Only the seller can do this.")

    def _set(self, order, new_status):
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        order = self.get_object()
        self._seller_only(order)
        with transaction.atomic():
            listing = Listing.objects.select_for_update().get(pk=order.listing_id)
            if order.status != Order.PENDING:
                raise ValidationError("Only pending orders can be accepted.")
            if order.quantity > listing.quantity:
                raise ValidationError(f"Only {listing.quantity} left in stock.")
            listing.quantity -= order.quantity
            if listing.quantity <= Decimal("0"):
                listing.status = Listing.SOLD
            listing.save(update_fields=["quantity", "status", "updated_at"])
            resp = self._set(order, Order.ACCEPTED)
        notify_user(order.buyer, f"✅ Your order for «{order.listing.title}» was accepted. Open Jailo for the seller's phone number.")
        return resp

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        order = self.get_object()
        self._seller_only(order)
        if order.status != Order.PENDING:
            raise ValidationError("Only pending orders can be declined.")
        resp = self._set(order, Order.DECLINED)
        notify_user(order.buyer, f"❌ Your order for «{order.listing.title}» was declined.")
        return resp

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        order = self.get_object()
        self._seller_only(order)
        if order.status != Order.ACCEPTED:
            raise ValidationError("Only accepted orders can be completed.")
        return self._set(order, Order.COMPLETED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        if order.buyer_id != request.user.pk:
            raise PermissionDenied("Only the buyer can cancel.")
        if order.status not in (Order.PENDING, Order.ACCEPTED):
            raise ValidationError("This order can no longer be cancelled.")
        with transaction.atomic():
            if order.status == Order.ACCEPTED:  # give the stock back
                listing = Listing.objects.select_for_update().get(pk=order.listing_id)
                listing.quantity += order.quantity
                if listing.status == Listing.SOLD:
                    listing.status = Listing.ACTIVE
                listing.save(update_fields=["quantity", "status", "updated_at"])
            resp = self._set(order, Order.CANCELLED)
        notify_user(order.listing.seller, f"Order for «{order.listing.title}» was cancelled by the buyer.")
        return resp

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        """Buyer rates the seller after a completed order. Body: rating (1-5), comment?"""
        order = self.get_object()
        if order.buyer_id != request.user.pk:
            raise PermissionDenied("Only the buyer can review.")
        if order.status != Order.COMPLETED:
            raise ValidationError("You can review after the order is completed.")
        if hasattr(order, "review"):
            raise ValidationError("You already reviewed this order.")
        s = ReviewSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(order=order, reviewer=request.user, seller=order.listing.seller)
        return Response(s.data, status=status.HTTP_201_CREATED)


class ThreadViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """My chats. Poll `messages?after=<last id>` for new messages."""

    serializer_class = ThreadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ChatThread.objects.filter(Q(buyer=user) | Q(seller=user)).select_related("listing", "buyer", "seller")

    @action(detail=True, methods=["get", "post"], pagination_class=None)
    def messages(self, request, pk=None):
        thread = self.get_object()
        if request.method == "GET":
            qs = thread.messages.all()
            after = request.query_params.get("after")
            if after and after.isdigit():
                qs = qs.filter(id__gt=int(after))
            return Response(MessageSerializer(qs[:200], many=True, context={"request": request}).data)

        s = MessageSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        msg = s.save(thread=thread, sender=request.user)
        recipient = thread.seller if thread.buyer_id == request.user.pk else thread.buyer
        # Telegram nudge only for the first message of a conversation, to avoid spamming
        if thread.messages.count() == 1:
            notify_user(recipient, f"💬 New message about «{thread.listing.title}» from {request.user.name or 'a user'}.")
        return Response(MessageSerializer(msg, context={"request": request}).data, status=status.HTTP_201_CREATED)
