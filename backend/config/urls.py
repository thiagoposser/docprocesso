"""Root URL configuration."""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.documents.urls")),
    path("api/", include("apps.audit.urls")),
    path("api/", include("apps.notifications.urls")),
]

# Em desenvolvimento, o Django serve uploads locais. Em produção, use o
# proxy/armazenamento de mídia da infraestrutura escolhida.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
