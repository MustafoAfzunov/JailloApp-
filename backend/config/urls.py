from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import FileResponse, JsonResponse
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health(request):
    return JsonResponse({"status": "ok"})


def frontend(request, path=""):
    """Serve the built React app. Missing client routes fall back to index.html."""
    root = settings.FRONTEND_DIST.resolve()
    index = root / "index.html"
    if path:
        target = (root / path).resolve()
        if str(target).startswith(str(root)) and target.is_file():
            return FileResponse(target.open("rb"))
    return FileResponse(index.open("rb"))


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/geo/", include("apps.geo.urls")),
    path("api/sensors/", include("apps.sensors.urls")),
    path("api/risk/", include("apps.risk.urls")),
    path("api/alerts/", include("apps.alerts.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/market/", include("apps.market.urls")),
    path("api/portal/", include("apps.portal.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.FRONTEND_DIST.joinpath("index.html").is_file():
    urlpatterns += [re_path(r"^(?!api/|admin/|static/|media/).*$", frontend)]
