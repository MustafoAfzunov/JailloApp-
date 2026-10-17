from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

User = settings.AUTH_USER_MODEL


class Category(models.Model):
    slug = models.SlugField(unique=True)
    name_ru = models.CharField(max_length=80)
    name_ky = models.CharField(max_length=80, blank=True)
    name_en = models.CharField(max_length=80)
    icon = models.CharField(max_length=40, blank=True)
    hint_ru = models.CharField(max_length=80, blank=True)
    hint_ky = models.CharField(max_length=80, blank=True)
    is_animal = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "slug"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name_en

    def name_for(self, lang):
        return {"ky": self.name_ky, "en": self.name_en}.get(lang) or self.name_ru


class Listing(models.Model):
    ACTIVE, RESERVED, SOLD, CLOSED = "active", "reserved", "sold", "closed"
    STATUS_CHOICES = [(ACTIVE, "Active"), (RESERVED, "Reserved"), (SOLD, "Sold"), (CLOSED, "Closed")]
    UNIT_CHOICES = [
        ("kg", "kg"), ("l", "litre"), ("piece", "piece"), ("head", "head"), ("bottle", "bottle"), ("jar", "jar"), ("other", "other"),
    ]
    SPECIES_CHOICES = [
        ("sheep", "Sheep"), ("goat", "Goat"), ("cow", "Cow"), ("horse", "Horse"),
        ("yak", "Yak"), ("camel", "Camel"), ("other", "Other"),
    ]
    SEX_CHOICES = [("m", "Male"), ("f", "Female")]

    seller = models.ForeignKey(User, related_name="listings", on_delete=models.CASCADE)
    category = models.ForeignKey(Category, related_name="listings", on_delete=models.PROTECT)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True, max_length=3000)
    price_kgs = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    unit = models.CharField(max_length=8, choices=UNIT_CHOICES, default="kg")
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("1"), validators=[MinValueValidator(Decimal("0"))],
        help_text="Quantity still available",
    )
    village = models.ForeignKey("geo.Village", related_name="listings", on_delete=models.PROTECT)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE, db_index=True)
    views = models.PositiveIntegerField(default=0)
    tag = models.CharField(max_length=60, blank=True, help_text="Short badge, e.g. 100% natural honey")
    place_note = models.CharField(max_length=120, blank=True, help_text="Where exactly, e.g. Central street")

    # livestock details
    species = models.CharField(max_length=8, choices=SPECIES_CHOICES, blank=True)
    breed = models.CharField(max_length=80, blank=True)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES, blank=True)
    age_months = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MaxValueValidator(600)])
    weight_kg = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True)
    vet_certificate = models.ImageField(upload_to="vet/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "category"])]

    def __str__(self):
        return self.title


class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="listings/")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class Order(models.Model):
    PENDING, ACCEPTED, DECLINED, COMPLETED, CANCELLED = (
        "pending", "accepted", "declined", "completed", "cancelled",
    )
    STATUS_CHOICES = [
        (PENDING, "Pending"), (ACCEPTED, "Accepted"), (DECLINED, "Declined"),
        (COMPLETED, "Completed"), (CANCELLED, "Cancelled"),
    ]
    DELIVERY_CHOICES = [("pickup", "Pickup"), ("delivery", "Delivery")]

    listing = models.ForeignKey(Listing, related_name="orders", on_delete=models.CASCADE)
    buyer = models.ForeignKey(User, related_name="orders", on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    delivery = models.CharField(max_length=10, choices=DELIVERY_CHOICES, default="pickup")
    note = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class Review(models.Model):
    order = models.OneToOneField(Order, related_name="review", on_delete=models.CASCADE)
    reviewer = models.ForeignKey(User, related_name="reviews_written", on_delete=models.CASCADE)
    seller = models.ForeignKey(User, related_name="reviews_received", on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ChatThread(models.Model):
    listing = models.ForeignKey(Listing, related_name="threads", on_delete=models.CASCADE)
    buyer = models.ForeignKey(User, related_name="threads_as_buyer", on_delete=models.CASCADE)
    seller = models.ForeignKey(User, related_name="threads_as_seller", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["listing", "buyer"], name="uniq_thread_listing_buyer")]
        ordering = ["-created_at"]


class Message(models.Model):
    thread = models.ForeignKey(ChatThread, related_name="messages", on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name="messages_sent", on_delete=models.CASCADE)
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
