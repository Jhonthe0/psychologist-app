from datetime import timedelta

from django.contrib.auth import get_user_model
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

    def test_login_page_renders_entry_interface(self):
        response = self.client.get("/login/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Acessar o sistema")
        self.assertContains(response, "Django Admin")

    def test_admin_dashboard_renders_operational_metrics(self):
        admin = get_user_model().objects.create_user(
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

        self.client.force_login(admin)
        response = self.client.get("/app/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Painel clinico")
        self.assertContains(response, "Pacientes ativos")
        self.assertContains(response, "Maria Silva")

    def test_admin_list_pages_render_registered_records(self):
        admin = get_user_model().objects.create_user(
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

        self.client.force_login(admin)

        patient_response = self.client.get("/app/patients/")
        trainee_response = self.client.get("/app/trainees/")
        appointment_response = self.client.get("/app/appointments/")

        self.assertContains(patient_response, "Maria Silva")
        self.assertContains(trainee_response, "Joao")
        self.assertContains(appointment_response, "Agendada")

    def test_trainee_agenda_page_only_renders_own_future_appointments(self):
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
