from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from shortener.views import AdminStatsView, RegisterView, URLViewSet, redirect_view

router = DefaultRouter()
router.register("urls", URLViewSet, basename="urls")

urlpatterns = [
    path("", TemplateView.as_view(template_name="index.html")),
    path("admin/", admin.site.urls),
    path("api/auth/register/", RegisterView.as_view()),
    path("api/auth/login/", TokenObtainPairView.as_view()),
    path("api/auth/refresh/", TokenRefreshView.as_view()),
    path("api/admin/stats/", AdminStatsView.as_view()),
    path("api/", include(router.urls)),
    path("<str:code>", redirect_view),  # MUST stay last
]
