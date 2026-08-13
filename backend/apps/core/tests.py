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
from django.db import connection
from django.test.utils import CaptureQueriesContext

from .models import SystemSettings
from apps.payments.models import Payment, PaymentStatus, Supplier
from apps.processes.models import AdministrativeProcess, ProcessStatus, ProcessType, WorkflowStage, WorkflowTransition
from apps.processes.workflow_services import create_workflow
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
        self.assertEqual(processes.data["in_progress"], 1)
        self.assertEqual(processes.data["completed"], 0)
        self.assertEqual(processes.data["total"], 1)
        self.assertEqual(processes.data["my_sector"], 1)
        self.assertEqual(processes.data["my_action"], 0)
        self.assertEqual(processes.data["stalled_days"], 7)
        self.assertEqual(processes.data["by_stage"], [])
        self.assertIn("as_of", processes.data)
        self.assertEqual(financial.data["pending"], 1)
        self.assertEqual(financial.data["overdue"], 1)
        self.assertEqual(financial.data["scheduled"], 0)
        self.assertIn("due_next_7_days", financial.data)
        self.assertEqual(Decimal(financial.data["pending_total"]), Decimal("100.50"))

        self.client.force_authenticate(self.denied)
        self.assertEqual(self.client.get(reverse("core:dashboard-processes")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(reverse("core:dashboard-financial")).status_code, status.HTTP_403_FORBIDDEN)

    def test_operational_counts_match_workbox_across_multiple_memberships(self):
        second_sector = Sector.objects.create(name="Dashboard adicional", code="DASH-A")
        UserSectorMembership.objects.create(user=self.user, sector=second_sector)
        workflow = create_workflow(code="dashboard-actions", name="Dashboard actions")
        stage = WorkflowStage.objects.create(
            workflow_version=workflow.current_version, order=1, name="Aprovação", is_initial=True,
            responsible_sector=second_sector,
        )
        final = WorkflowStage.objects.create(
            workflow_version=workflow.current_version, order=2, name="Final", is_final=True,
            responsible_sector=second_sector,
        )
        WorkflowTransition.objects.create(
            source_stage=stage, destination_stage=final, code="aprovar", name="Aprovar",
            authorized_sector=second_sector,
        )
        process_type = ProcessType.objects.create(name="Dashboard action", code="dashboard-action", workflow=workflow)
        AdministrativeProcess.objects.create(
            title="Aguardando aprovação", process_type=process_type, created_by=self.user,
            origin_sector=second_sector, current_sector=second_sector, responsible_sector=second_sector,
            workflow_version=workflow.current_version, current_stage=stage, status=ProcessStatus.OPEN,
        )
        self.user.user_permissions.add(Permission.objects.get(codename="forward_administrativeprocess"))
        self.client.force_authenticate(self.user)
        dashboard = self.client.get(reverse("core:dashboard-processes"))
        workbox = self.client.get(reverse("process-workbox"), {"scope": "my-action"})
        self.assertEqual(dashboard.data["my_action"], workbox.data["count"])
        self.assertEqual(dashboard.data["awaiting_approval"], 1)
        self.assertEqual(dashboard.data["my_sector"], 2)
        self.assertEqual(dashboard.data["by_stage"][0]["current_stage__name"], "Aprovação")

    def test_dashboard_query_budgets_are_bounded(self):
        self.client.force_authenticate(self.user)
        with CaptureQueriesContext(connection) as process_queries:
            process_response = self.client.get(reverse("core:dashboard-processes"))
        with CaptureQueriesContext(connection) as financial_queries:
            financial_response = self.client.get(reverse("core:dashboard-financial"))
        self.assertEqual(process_response.status_code, status.HTTP_200_OK)
        self.assertEqual(financial_response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(process_queries), 12)
        self.assertLessEqual(len(financial_queries), 5)

    def test_stalled_and_financial_periods_use_documented_dates(self):
        AdministrativeProcess.objects.filter(pk=self.process.pk).update(
            updated_at=timezone.now() - timedelta(days=8)
        )
        supplier = Supplier.objects.get(name="Dashboard")
        Payment.objects.create(
            process=self.process, sector=self.sector, supplier=supplier,
            description="Próxima semana", amount=Decimal("25.00"),
            due_date=timezone.localdate() + timedelta(days=5), status=PaymentStatus.SCHEDULED,
            scheduled_at=timezone.now() + timedelta(hours=1), created_by=self.user,
        )
        self.client.force_authenticate(self.user)
        processes = self.client.get(reverse("core:dashboard-processes"))
        financial = self.client.get(reverse("core:dashboard-financial"))
        stalled_workbox = self.client.get(
            reverse("process-workbox"), {"scope": "my-sector", "stalled": "true"}
        )
        self.assertEqual(processes.data["stalled"], 1)
        self.assertEqual(processes.data["stalled"], stalled_workbox.data["count"])
        self.assertEqual(processes.data["stalled_days"], 7)
        self.assertEqual(financial.data["scheduled"], 1)
        self.assertEqual(financial.data["due_next_7_days"], 1)

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

    def test_report_query_budgets_are_bounded(self):
        self.client.force_authenticate(self.user)
        self.client.get(reverse("core:dashboard"))
        with CaptureQueriesContext(connection) as process_queries:
            process_response = self.client.get(reverse("core:reports-process-summary"))
        with CaptureQueriesContext(connection) as payment_queries:
            payment_response = self.client.get(reverse("core:reports-payments-by-supplier"))
        self.assertEqual(process_response.status_code, status.HTTP_200_OK)
        self.assertEqual(payment_response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(process_queries), 6)
        self.assertLessEqual(len(payment_queries), 4)
