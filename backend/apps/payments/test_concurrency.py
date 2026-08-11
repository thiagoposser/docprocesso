from decimal import Decimal
from queue import Queue
from threading import Barrier, Thread

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from django.utils import timezone

from apps.processes.models import AdministrativeProcess, ProcessEvent, ProcessType
from apps.sectors.models import Sector, UserSectorMembership

from .models import Payment, PaymentMethod, PaymentStatus, Supplier
from .services import PaymentConflictError, confirm_payment


class PaymentConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="payment_concurrent")
        self.sector = Sector.objects.create(name="Concorrência pagamentos", code="CON-F")
        UserSectorMembership.objects.create(user=self.user, sector=self.sector, is_primary=True)
        self.user.user_permissions.add(*Permission.objects.filter(codename__in={
            "confirm_payment", "view_financial_data", "view_administrativeprocess",
        }))
        process_type = ProcessType.objects.create(name="Financeiro concorrente", code="financeiro-concorrente")
        self.process = AdministrativeProcess.objects.create(
            title="Pagamento simultâneo", process_type=process_type, created_by=self.user,
            origin_sector=self.sector,
        )
        supplier = Supplier.objects.create(name="Fornecedor concorrente", tax_id="12345678901")
        self.payment = Payment.objects.create(
            process=self.process, sector=self.sector, supplier=supplier, created_by=self.user,
            description="Confirmação única", amount=Decimal("75.00"), due_date=timezone.localdate(),
        )

    def test_only_one_simultaneous_confirmation_commits(self):
        barrier, results = Barrier(2), Queue()

        def execute():
            close_old_connections()
            actor = get_user_model().objects.get(pk=self.user.pk)
            barrier.wait()
            try:
                confirm_payment(
                    payment_id=self.payment.pk, actor=actor, paid_at=timezone.now(),
                    paid_amount=Decimal("75.00"), payment_method=PaymentMethod.PIX,
                )
                results.put("ok")
            except Exception as error:  # captured in the main test thread
                results.put(type(error))
            finally:
                connections.close_all()

        threads = [Thread(target=execute) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        outcomes = [results.get_nowait(), results.get_nowait()]
        self.assertEqual(outcomes.count("ok"), 1)
        self.assertEqual(outcomes.count(PaymentConflictError), 1)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, PaymentStatus.PAID)
        self.assertEqual(self.payment.paid_amount, Decimal("75.00"))
        self.assertEqual(ProcessEvent.objects.filter(process=self.process, title="Pagamento confirmado").count(), 1)
