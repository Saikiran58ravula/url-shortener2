from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    role = models.CharField(
        max_length=10,
        choices=[("user", "User"), ("admin", "Admin")],
        default="user",
    )


class ShortURL(models.Model):
    STATUS = [
        ("active", "Active"),
        ("disabled", "Disabled"),
        ("expired", "Expired"),
        ("reported", "Reported"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="urls")
    original_url = models.URLField(max_length=2000)
    short_code = models.CharField(max_length=20, unique=True, db_index=True)
    custom_alias = models.CharField(max_length=30, unique=True, null=True, blank=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.custom_alias or self.short_code


class ClickEvent(models.Model):
    url = models.ForeignKey(ShortURL, on_delete=models.CASCADE, related_name="clicks")
    timestamp = models.DateTimeField(auto_now_add=True)
    referrer = models.CharField(max_length=500, blank=True)
    device = models.CharField(max_length=30, blank=True)
    browser = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=2, blank=True)  # left blank: geo lookup not implemented
    ip_hash = models.CharField(max_length=64, blank=True)  # SHA-256 of IP, never the raw IP

    class Meta:
        indexes = [models.Index(fields=["url", "timestamp"])]


class DailyAnalytics(models.Model):
    url = models.ForeignKey(ShortURL, on_delete=models.CASCADE)
    date = models.DateField()
    clicks = models.PositiveIntegerField(default=0)
    unique_visitors = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("url", "date")
        indexes = [models.Index(fields=["url", "date"])]
