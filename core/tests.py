from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Appointment, Patient, Trainee, User


class FrontendPageTests(APITestCase):
    def test_home_page_renders_public_hospital_interface(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "PsiLine")
        self.assertContains(response, "Atendimento psicologico remoto")
        self.assertContains(response, 'href="/app/"')

    def test_login_page_renders_entry_interface(self):
        response = self.client.get("/login/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Acesso PsiLine")
        self.assertContains(response, "Entrar")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertNotContains(response, "Registrar estudante")
        self.assertNotContains(response, 'name="registration_number"')
        self.assertNotContains(response, 'name="phone"')

    def test_login_redirects_admin_and_trainee_to_their_workspaces(self):
        admin_user = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password="StrongPass123!",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        trainee_user = get_user_model().objects.create_user(
            username="20250001",
            email="joao@example.com",
            password="StrongPass123!",
            role=User.Role.TRAINEE,
        )

        admin_response = self.client.post(
            "/login/",
            {"username": admin_user.username, "password": "StrongPass123!", "role_hint": "admin"},
        )
        self.assertRedirects(admin_response, "/app/")

        self.client.logout()
        trainee_response = self.client.post(
            "/login/",
            {"username": trainee_user.username, "password": "StrongPass123!", "role_hint": "trainee"},
        )
        self.assertRedirects(trainee_response, "/app/agenda/")

    def test_app_pages_redirect_anonymous_users_to_login(self):
        response = self.client.get("/app/")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("/login/", response["Location"])

    def test_admin_dashboard_renders_operational_metrics(self):
        admin_user = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password="StrongPass123!",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        patient = Patient.objects.create(
            name="Maria Silva",
            cpf="12345678900",
            email="maria@example.com",
            phone="35999999999",
        )
        trainee_user = get_user_model().objects.create_user(
            username="20250001",
            email="joao@example.com",
            password="StrongPass123!",
            role=User.Role.TRAINEE,
            first_name="Joao",
            last_name="Pereira",
        )
        trainee = Trainee.objects.create(
            user=trainee_user,
            registration_number="20250001",
            phone="35988888888",
        )
        Appointment.objects.create(
            patient=patient,
            trainee=trainee,
            scheduled_at=timezone.now() + timedelta(days=1),
        )

        self.client.force_login(admin_user)
        response = self.client.get("/app/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Painel clinico")
        self.assertContains(response, "Pacientes ativos")
        self.assertContains(response, "Maria Silva")
        self.assertContains(response, "admin")
        self.assertContains(response, "Sair")
        self.assertContains(response, "Consultas no periodo")
        self.assertContains(response, "chart-pie")
        self.assertContains(response, 'name="start_date"')
        self.assertContains(response, 'name="end_date"')

    def test_admin_dashboard_filters_metrics_by_date_range(self):
        admin_user = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password="StrongPass123!",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        patient = Patient.objects.create(
            name="Maria Silva",
            cpf="12345678900",
            email="maria@example.com",
            phone="35999999999",
        )
        trainee_user = get_user_model().objects.create_user(
            username="20250001",
            email="joao@example.com",
            password="StrongPass123!",
            role=User.Role.TRAINEE,
            first_name="Joao",
            last_name="Pereira",
        )
        trainee = Trainee.objects.create(
            user=trainee_user,
            registration_number="20250001",
            phone="35988888888",
        )
        Appointment.objects.create(
            patient=patient,
            trainee=trainee,
            scheduled_at=timezone.datetime(2026, 6, 10, 10, tzinfo=timezone.get_current_timezone()),
            status=Appointment.Status.SCHEDULED,
        )
        Appointment.objects.create(
            patient=patient,
            trainee=trainee,
            scheduled_at=timezone.datetime(2026, 6, 11, 10, tzinfo=timezone.get_current_timezone()),
            status=Appointment.Status.COMPLETED,
        )
        Appointment.objects.create(
            patient=patient,
            trainee=trainee,
            scheduled_at=timezone.datetime(2026, 7, 1, 10, tzinfo=timezone.get_current_timezone()),
            status=Appointment.Status.CANCELED,
        )

        self.client.force_login(admin_user)
        response = self.client.get("/app/?start_date=2026-06-10&end_date=2026-06-30")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "2")
        self.assertContains(response, "Agendadas")
        self.assertContains(response, "Realizadas")
        self.assertContains(response, "Canceladas")
        self.assertNotContains(response, "01/07/2026 10:00")

    def test_logged_user_can_logout_from_app_shell(self):
        admin_user = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password="StrongPass123!",
            role=User.Role.ADMIN,
            is_staff=True,
        )

        self.client.force_login(admin_user)
        response = self.client.post("/logout/")

        self.assertRedirects(response, "/login/")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_list_pages_render_registered_records(self):
        admin_user = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password="StrongPass123!",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        patient = Patient.objects.create(
            name="Maria Silva",
            cpf="12345678900",
            email="maria@example.com",
            phone="35999999999",
        )
        trainee_user = get_user_model().objects.create_user(
            username="20250001",
            email="joao@example.com",
            password="StrongPass123!",
            role=User.Role.TRAINEE,
            first_name="Joao",
            last_name="Pereira",
        )
        trainee = Trainee.objects.create(
            user=trainee_user,
            registration_number="20250001",
            phone="35988888888",
        )
        Appointment.objects.create(
            patient=patient,
            trainee=trainee,
            scheduled_at=timezone.now() + timedelta(days=1),
        )

        self.client.force_login(admin_user)
        patient_response = self.client.get("/app/patients/")
        trainee_response = self.client.get("/app/trainees/")
        appointment_response = self.client.get("/app/appointments/")

        self.assertContains(patient_response, "Maria Silva")
        self.assertContains(trainee_response, "Joao")
        self.assertContains(appointment_response, "Agendada")

    def test_patients_page_filters_by_identity_fields_and_status(self):
        admin_user = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password="StrongPass123!",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        Patient.objects.create(
            name="Maria Silva",
            cpf="12345678900",
            email="maria@example.com",
            phone="35999999999",
            active=True,
        )
        Patient.objects.create(
            name="Ana Costa",
            cpf="98765432100",
            email="ana@example.com",
            phone="35988888888",
            active=False,
        )

        self.client.force_login(admin_user)
        response = self.client.get("/app/patients/?name=Maria&status=active")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Maria Silva")
        self.assertNotContains(response, "Ana Costa")
        self.assertContains(response, 'name="cpf"')
        self.assertContains(response, 'name="phone"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="status"')

        masked_response = self.client.get(
            "/app/patients/?cpf=123.456.789-00&phone=(35) 99999-9999&status=active"
        )
        self.assertContains(masked_response, "Maria Silva")
        self.assertContains(masked_response, "123.456.789-00")
        self.assertContains(masked_response, "(35) 99999-9999")
        self.assertNotContains(masked_response, "12345678900")

    def test_trainees_page_filters_by_name_registration_email_phone_and_status(self):
        admin_user = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password="StrongPass123!",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        active_user = get_user_model().objects.create_user(
            username="20250001",
            email="joao@example.com",
            password="StrongPass123!",
            role=User.Role.TRAINEE,
            first_name="Joao",
            last_name="Pereira",
        )
        inactive_user = get_user_model().objects.create_user(
            username="20250002",
            email="ana@example.com",
            password="StrongPass123!",
            role=User.Role.TRAINEE,
            first_name="Ana",
            last_name="Costa",
        )
        Trainee.objects.create(
            user=active_user,
            registration_number="20250001",
            phone="35999999999",
            active=True,
        )
        Trainee.objects.create(
            user=inactive_user,
            registration_number="20250002",
            phone="35988888888",
            active=False,
        )

        self.client.force_login(admin_user)
        response = self.client.get("/app/trainees/?name=Joao&phone=(35) 99999-9999&status=active")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Joao Pereira")
        self.assertContains(response, "(35) 99999-9999")
        self.assertNotContains(response, "Ana Costa")
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="registration_number"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="phone"')
        self.assertContains(response, 'name="status"')

    def test_appointments_page_filters_by_date_patient_trainee_and_status(self):
        admin_user = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password="StrongPass123!",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        patient = Patient.objects.create(
            name="Maria Silva",
            cpf="12345678900",
            email="maria@example.com",
            phone="35999999999",
        )
        other_patient = Patient.objects.create(
            name="Ana Costa",
            cpf="98765432100",
            email="ana@example.com",
            phone="35988888888",
        )
        trainee_user = get_user_model().objects.create_user(
            username="20250001",
            email="joao@example.com",
            password="StrongPass123!",
            role=User.Role.TRAINEE,
            first_name="Joao",
            last_name="Pereira",
        )
        other_trainee_user = get_user_model().objects.create_user(
            username="20250002",
            email="clara@example.com",
            password="StrongPass123!",
            role=User.Role.TRAINEE,
            first_name="Clara",
            last_name="Mendes",
        )
        trainee = Trainee.objects.create(
            user=trainee_user,
            registration_number="20250001",
            phone="35977777777",
        )
        other_trainee = Trainee.objects.create(
            user=other_trainee_user,
            registration_number="20250002",
            phone="35966666666",
        )
        Appointment.objects.create(
            patient=patient,
            trainee=trainee,
            scheduled_at=timezone.datetime(2026, 6, 10, 10, tzinfo=timezone.get_current_timezone()),
            status=Appointment.Status.SCHEDULED,
        )
        Appointment.objects.create(
            patient=other_patient,
            trainee=other_trainee,
            scheduled_at=timezone.datetime(2026, 7, 1, 10, tzinfo=timezone.get_current_timezone()),
            status=Appointment.Status.COMPLETED,
        )

        self.client.force_login(admin_user)
        response = self.client.get(
            "/app/appointments/?start_date=2026-06-01&end_date=2026-06-30"
            "&patient=Maria&trainee=Joao&status=scheduled"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Maria Silva")
        self.assertContains(response, "Joao Pereira")
        self.assertContains(response, "Agendada")
        self.assertNotContains(response, "Ana Costa")
        self.assertContains(response, 'name="start_date"')
        self.assertContains(response, 'name="end_date"')
        self.assertContains(response, 'name="patient"')
        self.assertContains(response, 'name="trainee"')
        self.assertContains(response, 'name="status"')

    def test_trainee_agenda_page_renders_only_authenticated_user_appointments(self):
        patient = Patient.objects.create(
            name="Maria Silva",
            cpf="12345678900",
            email="maria@example.com",
            phone="35999999999",
        )
        other_patient = Patient.objects.create(
            name="Ana Costa",
            cpf="98765432100",
            email="ana@example.com",
            phone="35977777777",
        )
        trainee_user = get_user_model().objects.create_user(
            username="20250001",
            email="joao@example.com",
            password="StrongPass123!",
            role=User.Role.TRAINEE,
            first_name="Joao",
            last_name="Pereira",
        )
        trainee = Trainee.objects.create(
            user=trainee_user,
            registration_number="20250001",
            phone="35988888888",
        )
        other_user = get_user_model().objects.create_user(
            username="20250002",
            email="clara@example.com",
            password="StrongPass123!",
            role=User.Role.TRAINEE,
        )
        other_trainee = Trainee.objects.create(
            user=other_user,
            registration_number="20250002",
            phone="35966666666",
        )
        Appointment.objects.create(
            patient=patient,
            trainee=trainee,
            scheduled_at=timezone.now() + timedelta(days=1),
        )
        Appointment.objects.create(
            patient=other_patient,
            trainee=other_trainee,
            scheduled_at=timezone.now() + timedelta(days=1),
        )

        self.client.force_login(trainee_user)
        response = self.client.get("/app/agenda/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Minha agenda")
        self.assertContains(response, "Maria Silva")
        self.assertContains(response, "(35) 99999-9999")
        self.assertNotContains(response, "Ana Costa")


class AdminApiTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password="StrongPass123!",
            role=User.Role.ADMIN,
            is_staff=True,
        )
        self.client.force_authenticate(self.admin)

    def test_admin_can_create_patient_trainee_and_appointment(self):
        patient_response = self.client.post(
            "/api/admin/patients/",
            {
                "name": "Maria Silva",
                "cpf": "12345678900",
                "email": "maria@example.com",
                "phone": "35999999999",
            },
            format="json",
        )
        self.assertEqual(patient_response.status_code, status.HTTP_201_CREATED)

        trainee_response = self.client.post(
            "/api/admin/trainees/",
            {
                "name": "Joao Pereira",
                "email": "joao@example.com",
                "registration_number": "20250001",
                "phone": "35988888888",
                "password": "StrongPass123!",
            },
            format="json",
        )
        self.assertEqual(trainee_response.status_code, status.HTTP_201_CREATED)

        scheduled_at = timezone.now() + timedelta(days=1)
        appointment_response = self.client.post(
            "/api/admin/appointments/",
            {
                "patient": patient_response.data["id"],
                "trainee": trainee_response.data["id"],
                "scheduled_at": scheduled_at.isoformat(),
                "call_link": "https://meet.example.com/abc",
                "status": Appointment.Status.SCHEDULED,
            },
            format="json",
        )
        self.assertEqual(appointment_response.status_code, status.HTTP_201_CREATED)

    def test_appointment_conflict_is_rejected(self):
        patient = Patient.objects.create(
            name="Maria Silva",
            cpf="12345678900",
            email="maria@example.com",
            phone="35999999999",
        )
        trainee_user = get_user_model().objects.create_user(
            username="20250001",
            email="joao@example.com",
            password="StrongPass123!",
            role=User.Role.TRAINEE,
        )
        trainee = Trainee.objects.create(
            user=trainee_user,
            registration_number="20250001",
            phone="35988888888",
        )
        scheduled_at = timezone.now() + timedelta(days=1)
        Appointment.objects.create(patient=patient, trainee=trainee, scheduled_at=scheduled_at)

        response = self.client.post(
            "/api/admin/appointments/",
            {
                "patient": patient.id,
                "trainee": trainee.id,
                "scheduled_at": scheduled_at.isoformat(),
                "status": Appointment.Status.SCHEDULED,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TraineeApiTests(APITestCase):
    def test_trainee_can_view_own_agenda_and_update_meeting_link(self):
        patient = Patient.objects.create(
            name="Maria Silva",
            cpf="12345678900",
            email="maria@example.com",
            phone="35999999999",
        )
        trainee_user = get_user_model().objects.create_user(
            username="20250001",
            email="joao@example.com",
            password="StrongPass123!",
            role=User.Role.TRAINEE,
        )
        trainee = Trainee.objects.create(
            user=trainee_user,
            registration_number="20250001",
            phone="35988888888",
        )
        appointment = Appointment.objects.create(
            patient=patient,
            trainee=trainee,
            scheduled_at=timezone.now() + timedelta(days=1),
        )

        self.client.force_authenticate(trainee_user)
        list_response = self.client.get("/api/trainee/agenda/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        link_response = self.client.patch(
            f"/api/trainee/agenda/{appointment.id}/meeting-link/",
            {"call_link": "https://meet.example.com/new"},
            format="json",
        )

        self.assertEqual(link_response.status_code, status.HTTP_200_OK)
        appointment.refresh_from_db()
        self.assertEqual(appointment.call_link, "https://meet.example.com/new")


class SeedDemoDataCommandTests(APITestCase):
    def test_seed_demo_data_creates_reportable_records_and_is_idempotent(self):
        call_command("seed_demo_data")
        call_command("seed_demo_data")

        self.assertEqual(Patient.objects.filter(cpf__startswith="900000000").count(), 12)
        self.assertEqual(Trainee.objects.filter(registration_number__startswith="DEMO").count(), 5)
        self.assertEqual(Appointment.objects.count(), 60)
        self.assertTrue(Appointment.objects.filter(status=Appointment.Status.COMPLETED).exists())
        self.assertTrue(Appointment.objects.filter(status=Appointment.Status.SCHEDULED).exists())
        self.assertTrue(Appointment.objects.filter(status=Appointment.Status.CANCELED).exists())
        self.assertTrue(Appointment.objects.exclude(cancellation_reason="").exists())
