from datetime import timedelta

from celery import shared_task
from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone

from .models import ClickEvent, DailyAnalytics, ShortURL
from .utils import hash_ip, parse_user_agent


@shared_task
def record_click(url_id, ip, referrer, user_agent):
    device, browser = parse_user_agent(user_agent)
    ClickEvent.objects.create(
        url_id=url_id,
        referrer=(referrer or "")[:500],
        device=device,
        browser=browser,
        ip_hash=hash_ip(ip or ""),
    )


@shared_task
def expire_links():
    due = ShortURL.objects.filter(status="active", expires_at__lte=timezone.now())
    keys = []
    for u in due:
        keys += [f"url:{u.short_code}", f"url:{u.custom_alias}"]
    due.update(status="expired")
    if keys:
        cache.delete_many(keys)


@shared_task
def aggregate_analytics():
    today = timezone.localdate()
    for day in (today - timedelta(days=1), today):
        rows = (
            ClickEvent.objects.filter(timestamp__date=day)
            .values("url_id")
            .annotate(c=Count("id"), u=Count("ip_hash", distinct=True))
        )
        for r in rows:
            DailyAnalytics.objects.update_or_create(
                url_id=r["url_id"], date=day,
                defaults={"clicks": r["c"], "unique_visitors": r["u"]},
            )