from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Appointment, Patient, Trainee, User


class Command(BaseCommand):
    help = "Popula o banco com pacientes, estagiarios e consultas demo para testes e relatorios."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-demo",
            action="store_true",
            help="Remove os dados demo conhecidos antes de recriar.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset_demo"]:
            self._reset_demo_data()

        patients = self._seed_patients()
        trainees = self._seed_trainees()
        appointments_count = self._seed_appointments(patients, trainees)

        self.stdout.write(
            self.style.SUCCESS(
                f"Demo seed concluido: {len(patients)} pacientes, "
                f"{len(trainees)} estagiarios, {appointments_count} consultas."
            )
        )

    def _reset_demo_data(self):
        demo_patients = Patient.objects.filter(cpf__startswith="900000000")
        demo_trainees = Trainee.objects.filter(registration_number__startswith="DEMO")

        Appointment.objects.filter(patient__in=demo_patients).delete()
        Appointment.objects.filter(trainee__in=demo_trainees).delete()

        trainee_user_ids = list(demo_trainees.values_list("user_id", flat=True))
        demo_trainees.delete()
        get_user_model().objects.filter(id__in=trainee_user_ids).delete()
        demo_patients.delete()

    def _seed_patients(self):
        data = [
            ("Ana Beatriz Costa", "90000000001", "ana.costa@example.com", "35991000001", date(1998, 3, 12)),
            ("Bruno Henrique Lima", "90000000002", "bruno.lima@example.com", "35991000002", date(1992, 7, 24)),
            ("Camila Rocha Martins", "90000000003", "camila.martins@example.com", "35991000003", date(2001, 1, 5)),
            ("Daniel Souza Vieira", "90000000004", "daniel.vieira@example.com", "35991000004", date(1988, 11, 18)),
            ("Eduarda Alves Pinto", "90000000005", "eduarda.pinto@example.com", "35991000005", date(1996, 5, 30)),
            ("Felipe Gomes Reis", "90000000006", "felipe.reis@example.com", "35991000006", date(1990, 9, 9)),
            ("Gabriela Nunes Castro", "90000000007", "gabriela.castro@example.com", "35991000007", date(1999, 12, 2)),
            ("Henrique Matos Silva", "90000000008", "henrique.silva@example.com", "35991000008", date(1985, 4, 21)),
            ("Isabela Ferreira Dias", "90000000009", "isabela.dias@example.com", "35991000009", date(2003, 8, 14)),
            ("Joao Pedro Moreira", "90000000010", "joao.moreira@example.com", "35991000010", date(1994, 2, 27)),
            ("Larissa Teixeira Melo", "90000000011", "larissa.melo@example.com", "35991000011", date(1997, 6, 6)),
            ("Marcos Vinicius Barros", "90000000012", "marcos.barros@example.com", "35991000012", date(1989, 10, 16)),
        ]
        patients = []
        for name, cpf, email, phone, birth_date in data:
            patient, _created = Patient.objects.update_or_create(
                cpf=cpf,
                defaults={
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "birth_date": birth_date,
                    "active": True,
                },
            )
            patients.append(patient)
        return patients

    def _seed_trainees(self):
        data = [
            ("DEMO2026001", "Alice", "Mendes", "alice.mendes@example.com", "35992000001", "Dra. Helena Prado"),
            ("DEMO2026002", "Caio", "Ribeiro", "caio.ribeiro@example.com", "35992000002", "Dr. Roberto Naves"),
            ("DEMO2026003", "Marina", "Lopes", "marina.lopes@example.com", "35992000003", "Dra. Silvia Campos"),
            ("DEMO2026004", "Rafael", "Andrade", "rafael.andrade@example.com", "35992000004", "Dra. Helena Prado"),
            ("DEMO2026005", "Sofia", "Cardoso", "sofia.cardoso@example.com", "35992000005", "Dr. Roberto Naves"),
        ]
        trainees = []
        UserModel = get_user_model()

        for registration, first_name, last_name, email, phone, supervisor_name in data:
            user, created = UserModel.objects.update_or_create(
                username=registration,
                defaults={
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "role": User.Role.TRAINEE,
                    "is_active": True,
                },
            )
            if created:
                user.set_password("Demo123456")
                user.save(update_fields=["password"])

            trainee, _created = Trainee.objects.update_or_create(
                registration_number=registration,
                defaults={
                    "user": user,
                    "phone": phone,
                    "supervisor_name": supervisor_name,
                    "active": True,
                },
            )
            trainees.append(trainee)
        return trainees

    def _seed_appointments(self, patients, trainees):
        base_day = timezone.localdate()
        statuses = [
            Appointment.Status.COMPLETED,
            Appointment.Status.COMPLETED,
            Appointment.Status.SCHEDULED,
            Appointment.Status.SCHEDULED,
            Appointment.Status.CANCELED,
        ]
        cancellation_reasons = [
            Appointment.CancellationReason.PATIENT_REQUEST,
            Appointment.CancellationReason.TECHNICAL_ISSUE,
            Appointment.CancellationReason.RESCHEDULED,
            Appointment.CancellationReason.TRAINEE_ABSENCE,
        ]

        count = 0
        for index in range(60):
            trainee = trainees[index % len(trainees)]
            patient = patients[(index * 3) % len(patients)]
            status = statuses[index % len(statuses)]
            day_offset = index - 35
            hour = 8 + (index % 8)
            scheduled_date = base_day + timedelta(days=day_offset)
            naive_dt = datetime.combine(scheduled_date, time(hour=hour, minute=0))
            scheduled_at = timezone.make_aware(naive_dt, timezone.get_current_timezone())

            defaults = {
                "status": status,
                "active": status != Appointment.Status.CANCELED,
                "call_link": f"https://meet.example.com/psiline-demo-{index + 1:02d}",
                "cancellation_reason": "",
            }
            if status == Appointment.Status.CANCELED:
                defaults["cancellation_reason"] = cancellation_reasons[index % len(cancellation_reasons)]

            Appointment.objects.update_or_create(
                trainee=trainee,
                patient=patient,
                scheduled_at=scheduled_at,
                defaults=defaults,
            )
            count += 1

        return count
