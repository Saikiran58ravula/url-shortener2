from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import ShortURL, User
from .utils import base62_encode

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@override_settings(CACHES=LOCMEM)
class BaseTest(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("sunny", password="pass12345")
        self.other = User.objects.create_user("other", password="pass12345")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def make(self, **kw):
        data = {"original_url": "https://example.com/very/long/path"}
        data.update(kw)
        return self.client.post("/api/urls/", data, format="json")


class Base62Tests(TestCase):
    def test_encode(self):
        self.assertEqual(base62_encode(0), "0")
        self.assertEqual(base62_encode(61), "Z")
        self.assertEqual(base62_encode(62), "10")


class APITests(BaseTest):
    def test_create_and_list(self):
        r = self.make()
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.data["short_code"])
        self.assertEqual(self.client.get("/api/urls/").data["count"], 1)

    def test_unauthenticated_gets_401(self):
        self.assertEqual(APIClient().get("/api/urls/").status_code, 401)

    def test_cannot_touch_other_users_url(self):
        r = self.make()
        other = APIClient()
        other.force_authenticate(self.other)
        self.assertEqual(other.get(f"/api/urls/{r.data['id']}/").status_code, 404)
        self.assertEqual(other.delete(f"/api/urls/{r.data['id']}/").status_code, 404)

    def test_update_and_delete(self):
        r = self.make()
        u = f"/api/urls/{r.data['id']}/"
        self.assertEqual(self.client.patch(u, {"status": "disabled"}, format="json").status_code, 200)
        self.assertEqual(self.client.delete(u).status_code, 204)

    def test_custom_alias(self):
        self.assertEqual(self.make(custom_alias="my-link").data["short_url"].endswith("/my-link"), True)
        self.assertEqual(self.make(custom_alias="my-link").status_code, 400)  # duplicate

    def test_analytics_endpoint(self):
        r = self.make()
        res = self.client.get(f"/api/urls/{r.data['id']}/analytics/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["total_clicks"], 0)


class SecurityTests(BaseTest):
    def test_malformed_url_rejected(self):
        self.assertEqual(self.make(original_url="not a url").status_code, 400)
        self.assertEqual(self.make(original_url="javascript:alert(1)").status_code, 400)

    def test_reserved_alias_rejected(self):
        self.assertEqual(self.make(custom_alias="admin").status_code, 400)

    def test_past_expiry_rejected(self):
        past = (timezone.now() - timedelta(days=1)).isoformat()
        self.assertEqual(self.make(expires_at=past).status_code, 400)

    def test_rate_limit(self):
        anon = APIClient()
        codes = [
            anon.post("/api/auth/login/", {"username": "x", "password": "y"}, format="json").status_code
            for _ in range(25)
        ]
        self.assertIn(429, codes)


@patch("shortener.views.record_click")
class RedirectTests(BaseTest):
    def test_valid_code_redirects(self, _mock):
        code = self.make().data["short_code"]
        r = APIClient().get(f"/{code}")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], "https://example.com/very/long/path")

    def test_missing_code_404(self, _mock):
        self.assertEqual(APIClient().get("/nope123").status_code, 404)

    def test_expired_link_404(self, _mock):
        ShortURL.objects.create(
            user=self.user, original_url="https://example.com", short_code="exp1",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertEqual(APIClient().get("/exp1").status_code, 404)

    def test_disabled_link_404(self, _mock):
        r = self.make()
        self.client.patch(f"/api/urls/{r.data['id']}/", {"status": "disabled"}, format="json")
        self.assertEqual(APIClient().get(f"/{r.data['short_code']}").status_code, 404)

    def test_cache_hit_uses_no_queries(self, _mock):
        code = self.make().data["short_code"]
        c = APIClient()
        c.get(f"/{code}")  # first hit fills the cache
        with self.assertNumQueries(0):
            self.assertEqual(c.get(f"/{code}").status_code, 302)

    def test_cache_invalidated_on_disable(self, _mock):
        r = self.make()
        code = r.data["short_code"]
        APIClient().get(f"/{code}")  # cached
        self.client.patch(f"/api/urls/{r.data['id']}/", {"status": "disabled"}, format="json")
        self.assertEqual(APIClient().get(f"/{code}").status_code, 404)
