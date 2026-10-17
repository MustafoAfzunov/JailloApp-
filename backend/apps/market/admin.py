from django.contrib import admin

from .models import Category, ChatThread, Listing, ListingImage, Message, Order, Review


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("slug", "name_ru", "name_ky", "name_en", "is_animal", "order")


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "seller", "village", "price_kgs", "unit", "quantity", "status", "created_at")
    list_filter = ("status", "category", "village")
    search_fields = ("title", "description", "breed")
    inlines = [ListingImageInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "buyer", "quantity", "status", "created_at")
    list_filter = ("status",)


admin.site.register(Review)
admin.site.register(ChatThread)
admin.site.register(Message)
