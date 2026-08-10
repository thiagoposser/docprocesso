from django.urls import path
from .views import AdminSettingsView, PublicSettingsView, dashboard, health_check

app_name = "core"
urlpatterns = [
    path("health/", health_check, name="health"),
    path("dashboard/", dashboard, name="dashboard"),
    path("settings/public/", PublicSettingsView.as_view(), name="settings-public"),
    path("settings/", AdminSettingsView.as_view(), name="settings-admin"),
]
