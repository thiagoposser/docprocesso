from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from datetime import timedelta
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken
from django.core.exceptions import ValidationError

from .models import SystemSettings
from apps.payments.models import Payment, Supplier
from apps.processes.models import AdministrativeProcess, ProcessStatus, ProcessType
from apps.sectors.models import Sector, UserSectorMembership


class SystemSettingsApiTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.admin = users.objects.create_user(username="settings_admin", password="safe-password", is_staff=True)
        self.user = users.objects.create_user(username="settings_user", password="safe-password")
        self.user.groups.add(Group.objects.get(name="Usuário"))
        self.settings = SystemSettings.load()

    def test_public_endpoint_has_only_allowlisted_fields(self):
        response = self.client.get(reverse("core:settings-public"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data), {"system_name", "system_short_name", "logo_url", "primary_color", "language_code", "timezone", "version"})
        self.assertNotIn("maintenance_mode", response.data)
        self.assertNotIn("support_email", response.data)

    def test_only_administrator_reads_and_updates_admin_settings(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(reverse("core:settings-admin")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.patch(reverse("core:settings-admin"), {"system_name": "Negado"}).status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.admin)
        response = self.client.patch(reverse("core:settings-admin"), {"system_name": "Novo Sistema", "primary_color": "#123ABC"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.system_name, "Novo Sistema")
        self.assertEqual(self.settings.primary_color, "#123abc")

    def test_maintenance_blocks_regular_user_but_not_admin_or_login(self):
        self.settings.maintenance_mode = True
        self.settings.save()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.user)}")
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.json()["code"], "maintenance_mode")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(self.admin)}")
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, status.HTTP_200_OK)
        self.client.credentials()
        self.assertNotEqual(self.client.post(reverse("auth-login"), {"username": "invalid", "password": "invalid"}).status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_singleton_cannot_be_duplicated(self):
        second = SystemSettings(system_name="Outro")
        with self.assertRaises(ValidationError):
            second.save()
        self.assertEqual(SystemSettings.objects.count(), 1)


class DomainDashboardApiTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.user = users.objects.create_user(username="dashboard_domain")
        self.denied = users.objects.create_user(username="dashboard_denied")
        self.sector = Sector.objects.create(name="Dashboard", code="DASH")
        self.other_sector = Sector.objects.create(name="Outro dashboard", code="DASH-X")
        UserSectorMembership.objects.create(user=self.user, sector=self.sector, is_primary=True)
        process_type = ProcessType.objects.create(name="Dashboard", code="dashboard")
        self.process = AdministrativeProcess.objects.create(
            title="Visível", process_type=process_type, created_by=self.user,
            origin_sector=self.sector, current_sector=self.sector,
            status=ProcessStatus.IN_PROGRESS,
        )
        AdministrativeProcess.objects.create(
            title="Oculto", process_type=process_type, created_by=self.user,
            origin_sector=self.other_sector, current_sector=self.other_sector,
            status=ProcessStatus.COMPLETED, completed_at=timezone.now(),
        )
        supplier = Supplier.objects.create(name="Dashboard", tax_id="12345678901")
        Payment.objects.create(
            process=self.process, sector=self.sector, supplier=supplier,
            description="Vencido", amount=Decimal("100.50"),
            due_date=timezone.localdate() - timedelta(days=1), created_by=self.user,
        )
        self.user.user_permissions.add(*Permission.objects.filter(codename__in={
            "view_administrativeprocess", "view_payment", "view_financial_data", "generate_reports",
        }))

    def test_domain_summaries_are_sector_scoped_and_financial_is_protected(self):
        self.client.force_authenticate(self.user)
        processes = self.client.get(reverse("core:dashboard-processes"))
        financial = self.client.get(reverse("core:dashboard-financial"))
        self.assertEqual(processes.data, {"in_progress": 1, "completed": 0, "total": 1})
        self.assertEqual(financial.data["pending"], 1)
        self.assertEqual(financial.data["overdue"], 1)
        self.assertEqual(Decimal(financial.data["pending_total"]), Decimal("100.50"))

        self.client.force_authenticate(self.denied)
        self.assertEqual(self.client.get(reverse("core:dashboard-processes")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(reverse("core:dashboard-financial")).status_code, status.HTTP_403_FORBIDDEN)

    def test_report_endpoints_aggregate_filters_and_protect_financial_data(self):
        self.client.force_authenticate(self.user)
        process_summary = self.client.get(reverse("core:reports-process-summary"), {"status": ProcessStatus.IN_PROGRESS})
        payment_summary = self.client.get(reverse("core:reports-payment-summary"), {"min_amount": "100", "purpose": "Vencido"})
        by_sector = self.client.get(reverse("core:reports-payments-by-sector"))
        by_supplier = self.client.get(reverse("core:reports-payments-by-supplier"))
        time_report = self.client.get(reverse("core:reports-process-time-by-sector"))
        self.assertEqual(process_summary.status_code, status.HTTP_200_OK)
        self.assertEqual(process_summary.data["total"], 1)
        self.assertEqual(payment_summary.data["count"], 1)
        self.assertEqual(Decimal(payment_summary.data["total"]), Decimal("100.50"))
        self.assertEqual(by_sector.data[0]["sector"], self.sector.pk)
        self.assertEqual(by_supplier.data[0]["count"], 1)
        self.assertEqual(time_report.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(reverse("core:reports-process-summary"), {"date_from": "invalid"}).status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(self.denied)
        self.assertEqual(self.client.get(reverse("core:reports-process-summary")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(reverse("core:reports-payment-summary")).status_code, status.HTTP_403_FORBIDDEN)
