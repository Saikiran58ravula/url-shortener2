from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.core.cache import cache

from .models import ClickEvent, DailyAnalytics, ShortURL, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Role", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_staff", "date_joined")


@admin.register(ShortURL)
class ShortURLAdmin(admin.ModelAdmin):
    list_display = ("short_code", "custom_alias", "user", "status", "expires_at", "created_at")
    list_filter = ("status",)
    search_fields = ("short_code", "custom_alias", "original_url", "user__username")
    actions = ["disable_links", "mark_reported", "activate_links"]

    def _set(self, request, queryset, status):
        keys = []
        for u in queryset:
            keys += [f"url:{u.short_code}", f"url:{u.custom_alias}"]
        queryset.update(status=status)
        cache.delete_many(keys)

    @admin.action(description="Disable selected links")
    def disable_links(self, request, queryset):
        self._set(request, queryset, "disabled")

    @admin.action(description="Mark selected links as reported")
    def mark_reported(self, request, queryset):
        self._set(request, queryset, "reported")

    @admin.action(description="Activate selected links")
    def activate_links(self, request, queryset):
        self._set(request, queryset, "active")


@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    list_display = ("url", "timestamp", "device", "browser", "referrer")
    list_filter = ("device", "browser")


@admin.register(DailyAnalytics)
class DailyAnalyticsAdmin(admin.ModelAdmin):
    list_display = ("url", "date", "clicks", "unique_visitors")
    list_filter = ("date",)
