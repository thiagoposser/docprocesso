from queue import Queue
from threading import Barrier, Thread

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import close_old_connections, connections
from django.test import TransactionTestCase

from apps.sectors.models import Sector, UserSectorMembership

from .models import AdministrativeProcess, ProcessMovement, ProcessStatus, ProcessType
from .services import ProcessConflictError, open_process


class ProcessConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="process_concurrent")
        self.sector = Sector.objects.create(name="Concorrência processos", code="CON-P")
        UserSectorMembership.objects.create(user=self.user, sector=self.sector, is_primary=True)
        self.user.user_permissions.add(Permission.objects.get(codename="open_administrativeprocess"))
        process_type = ProcessType.objects.create(name="Concorrência", code="concorrencia")
        self.process = AdministrativeProcess.objects.create(
            title="Abertura simultânea", process_type=process_type, created_by=self.user,
            origin_sector=self.sector,
        )

    def test_only_one_action_wins_for_the_same_process_version(self):
        barrier, results = Barrier(2), Queue()

        def execute():
            close_old_connections()
            actor = get_user_model().objects.get(pk=self.user.pk)
            barrier.wait()
            try:
                open_process(process_id=self.process.pk, actor=actor, expected_version=1)
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
        self.assertEqual(outcomes.count(ProcessConflictError), 1)
        self.process.refresh_from_db()
        self.assertEqual(self.process.status, ProcessStatus.OPEN)
        self.assertEqual(self.process.version, 2)
        self.assertEqual(ProcessMovement.objects.filter(process=self.process).count(), 1)
