from django.urls import path
from .views import AdminSettingsView, PublicSettingsView, dashboard, financial_dashboard, health_check, process_dashboard, report_payment_summary, report_payments_by_sector, report_payments_by_supplier, report_process_summary, report_process_time_by_sector

app_name = "core"
urlpatterns = [
    path("health/", health_check, name="health"),
    path("dashboard/", dashboard, name="dashboard"),
    path("dashboard/processes/", process_dashboard, name="dashboard-processes"),
    path("dashboard/financial/", financial_dashboard, name="dashboard-financial"),
    path("reports/processes/summary/", report_process_summary, name="reports-process-summary"),
    path("reports/processes/time-by-sector/", report_process_time_by_sector, name="reports-process-time-by-sector"),
    path("reports/payments/summary/", report_payment_summary, name="reports-payment-summary"),
    path("reports/payments/by-sector/", report_payments_by_sector, name="reports-payments-by-sector"),
    path("reports/payments/by-supplier/", report_payments_by_supplier, name="reports-payments-by-supplier"),
    path("settings/public/", PublicSettingsView.as_view(), name="settings-public"),
    path("settings/", AdminSettingsView.as_view(), name="settings-admin"),
]
