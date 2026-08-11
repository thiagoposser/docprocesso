from django.urls import path
from .views import AdminSettingsView, PublicSettingsView, dashboard, financial_dashboard, health_check, process_dashboard

app_name = "core"
urlpatterns = [
    path("health/", health_check, name="health"),
    path("dashboard/", dashboard, name="dashboard"),
    path("dashboard/processes/", process_dashboard, name="dashboard-processes"),
    path("dashboard/financial/", financial_dashboard, name="dashboard-financial"),
    path("settings/public/", PublicSettingsView.as_view(), name="settings-public"),
    path("settings/", AdminSettingsView.as_view(), name="settings-admin"),
]
