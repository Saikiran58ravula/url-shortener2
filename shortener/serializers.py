import re
import uuid

from django.utils import timezone
from rest_framework import serializers

from .models import ShortURL, User
from .utils import base62_encode

RESERVED = {"api", "admin", "static", "login", "register", "favicon.ico"}
ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]{3,30}$")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)  # hashes the password


class ShortURLSerializer(serializers.ModelSerializer):
    short_url = serializers.SerializerMethodField()
    click_count = serializers.SerializerMethodField()

    class Meta:
        model = ShortURL
        fields = [
            "id", "original_url", "short_code", "custom_alias",
            "expires_at", "status", "short_url", "click_count", "created_at",
        ]
        read_only_fields = ["short_code", "created_at"]

    def get_short_url(self, obj):
        base = self.context["request"].build_absolute_uri("/")
        return f"{base}{obj.custom_alias or obj.short_code}"

    def get_click_count(self, obj):
        return getattr(obj, "click_count", 0)

    def validate_original_url(self, value):
        if not value.lower().startswith(("http://", "https://")):
            raise serializers.ValidationError("Only http:// and https:// URLs are allowed.")
        return value

    def validate_custom_alias(self, value):
        if not value:
            return None
        if not ALIAS_RE.match(value):
            raise serializers.ValidationError("Alias: 3-30 characters, letters, numbers, - or _ only.")
        if value.lower() in RESERVED:
            raise serializers.ValidationError("This alias is reserved.")
        clash = ShortURL.objects.filter(short_code=value)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError("This alias is already taken.")
        return value

    def validate_expires_at(self, value):
        if value and value <= timezone.now():
            raise serializers.ValidationError("Expiry must be in the future.")
        return value

    def create(self, validated_data):
        # temporary unique code, then replace with Base62 of the row id
        obj = ShortURL.objects.create(**validated_data, short_code=uuid.uuid4().hex[:20])
        code = base62_encode(obj.id + 100000)
        while ShortURL.objects.filter(custom_alias=code).exists():
            code += "x"
        obj.short_code = code
        obj.save(update_fields=["short_code"])
        return obj