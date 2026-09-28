import logging

from django.core.cache import cache
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import generics, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ClickEvent, ShortURL, User
from .serializers import RegisterSerializer, ShortURLSerializer
from .tasks import record_click

logger = logging.getLogger(__name__)


def _bump(name):
    try:
        cache.incr(name)
    except ValueError:
        cache.set(name, 1, None)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class URLViewSet(viewsets.ModelViewSet):
    serializer_class = ShortURLSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # users can only see and edit their own URLs
        return (
            ShortURL.objects.filter(user=self.request.user)
            .annotate(click_count=Count("clicks"))
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @staticmethod
    def _invalidate(obj):
        cache.delete_many([f"url:{obj.short_code}", f"url:{obj.custom_alias}"])

    def perform_update(self, serializer):
        old = serializer.instance
        old_alias = old.custom_alias
        obj = serializer.save()
        self._invalidate(obj)
        if old_alias and old_alias != obj.custom_alias:
            cache.delete(f"url:{old_alias}")

    def perform_destroy(self, instance):
        self._invalidate(instance)
        instance.delete()

    @action(detail=True, methods=["get"])
    def analytics(self, request, pk=None):
        url = self.get_object()
        today = timezone.localdate()

        # past days come from the pre-aggregated table, today is computed live
        daily = list(
            url.dailyanalytics_set.filter(date__lt=today)
            .order_by("date").values("date", "clicks", "unique_visitors")
        )
        t = url.clicks.filter(timestamp__date=today).aggregate(
            c=Count("id"), u=Count("ip_hash", distinct=True)
        )
        daily.append({"date": today, "clicks": t["c"], "unique_visitors": t["u"]})

        def breakdown(field):
            return list(url.clicks.values(field).annotate(n=Count("id")).order_by("-n")[:5])

        referrers = [
            {"referrer": r["referrer"] or "Direct", "n": r["n"]} for r in breakdown("referrer")
        ]
        return Response({
            "total_clicks": url.clicks.count(),
            "unique_visitors": url.clicks.values("ip_hash").distinct().count(),
            "daily": daily,
            "referrers": referrers,
            "devices": breakdown("device"),
            "browsers": breakdown("browser"),
        })


class AdminStatsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        hits = cache.get("stats:cache_hit", 0)
        misses = cache.get("stats:cache_miss", 0)
        total = hits + misses
        return Response({
            "total_users": User.objects.count(),
            "total_urls": ShortURL.objects.count(),
            "active_urls": ShortURL.objects.filter(status="active").count(),
            "expired_urls": ShortURL.objects.filter(status="expired").count(),
            "reported_urls": ShortURL.objects.filter(status="reported").count(),
            "total_clicks": ClickEvent.objects.count(),
            "cache_hit_rate": round(hits / total * 100, 1) if total else None,
        })


def redirect_view(request, code):
    key = f"url:{code}"
    data = cache.get(key)
    if data is None:
        _bump("stats:cache_miss")
        try:
            u = ShortURL.objects.get(Q(short_code=code) | Q(custom_alias=code))
        except ShortURL.DoesNotExist:
            raise Http404("Short link not found")
        if u.status != "active" or (u.expires_at and u.expires_at <= timezone.now()):
            raise Http404("Link expired or disabled")
        data = {"id": u.id, "url": u.original_url}
        ttl = 3600
        if u.expires_at:
            ttl = max(1, min(ttl, int((u.expires_at - timezone.now()).total_seconds())))
        cache.set(key, data, ttl)
    else:
        _bump("stats:cache_hit")

    try:
        record_click.delay(
            data["id"],
            request.META.get("REMOTE_ADDR", ""),
            request.META.get("HTTP_REFERER", ""),
            request.META.get("HTTP_USER_AGENT", ""),
        )
    except Exception:
        # never block a redirect because analytics failed
        logger.exception("Could not queue click event")
    return redirect(data["url"])  # 302, so every click is counted
