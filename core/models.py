from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador"
        TRAINEE = "trainee", "Estagiario"
        PATIENT = "patient", "Paciente"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.TRAINEE)
    REQUIRED_FIELDS = ["email"]

    def save(self, *args, **kwargs):
        if self.is_superuser or self.is_staff:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)


class Patient(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="patient_profile",
    )
    name = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14, unique=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def has_future_appointments(self):
        return self.appointments.filter(
            scheduled_at__gt=timezone.now(),
            status=Appointment.Status.SCHEDULED,
            active=True,
        ).exists()


class Trainee(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        related_name="trainee_profile",
    )
    registration_number = models.CharField(max_length=50, unique=True)
    phone = models.CharField(max_length=20)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__first_name", "user__last_name"]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def email(self):
        return self.user.email

    def has_future_appointments(self):
        return self.appointments.filter(
            scheduled_at__gt=timezone.now(),
            status=Appointment.Status.SCHEDULED,
            active=True,
        ).exists()


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Agendada"
        COMPLETED = "completed", "Realizada"
        CANCELED = "canceled", "Cancelada"

    trainee = models.ForeignKey(
        Trainee,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    scheduled_at = models.DateTimeField()
    call_link = models.URLField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_at"]
        indexes = [
            models.Index(fields=["scheduled_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.patient} com {self.trainee} em {self.scheduled_at:%d/%m/%Y %H:%M}"

    def clean(self):
        if not self.patient.active:
            raise ValidationError({"patient": "Paciente inativo nao pode receber consulta."})
        if not self.trainee.active:
            raise ValidationError({"trainee": "Estagiario inativo nao pode receber consulta."})
        conflict = Appointment.objects.filter(
            trainee=self.trainee,
            scheduled_at=self.scheduled_at,
            status=self.Status.SCHEDULED,
            active=True,
        )
        if self.pk:
            conflict = conflict.exclude(pk=self.pk)
        if self.status == self.Status.SCHEDULED and conflict.exists():
            raise ValidationError({"scheduled_at": "Ja existe consulta agendada para este estagiario neste horario."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
