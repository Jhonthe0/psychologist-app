from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from core.models import Appointment, Patient, Trainee, User


class RoleTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "role": self.user.role,
        }
        return data


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            "id",
            "name",
            "cpf",
            "email",
            "phone",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TraineeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True, required=False)
    email = serializers.EmailField(source="user.email")
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Trainee
        fields = [
            "id",
            "name",
            "full_name",
            "email",
            "registration_number",
            "phone",
            "password",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "full_name", "created_at", "updated_at"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if self.instance is None:
            required_fields = {
                "name": attrs.get("name"),
                "password": attrs.get("password"),
                "email": attrs.get("user", {}).get("email"),
            }
            missing = [field for field, value in required_fields.items() if not value]
            if missing:
                raise serializers.ValidationError({field: "Campo obrigatorio." for field in missing})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop("user")
        name = validated_data.pop("name")
        password = validated_data.pop("password")
        first_name, last_name = self._split_name(name)
        username = validated_data["registration_number"]
        user = User.objects.create_user(
            username=username,
            email=user_data["email"],
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=User.Role.TRAINEE,
        )
        return Trainee.objects.create(user=user, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        name = validated_data.pop("name", None)
        password = validated_data.pop("password", None)

        if name:
            instance.user.first_name, instance.user.last_name = self._split_name(name)
        if "email" in user_data:
            instance.user.email = user_data["email"]
        if "registration_number" in validated_data:
            instance.user.username = validated_data["registration_number"]
        if password:
            instance.user.set_password(password)
        instance.user.save()

        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

    def _split_name(self, name):
        parts = name.strip().split(maxsplit=1)
        return parts[0], parts[1] if len(parts) > 1 else ""


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    patient_phone = serializers.CharField(source="patient.phone", read_only=True)
    trainee_name = serializers.CharField(source="trainee.full_name", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "trainee",
            "trainee_name",
            "patient",
            "patient_name",
            "patient_phone",
            "scheduled_at",
            "call_link",
            "status",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance
        patient = attrs.get("patient", getattr(instance, "patient", None))
        trainee = attrs.get("trainee", getattr(instance, "trainee", None))
        scheduled_at = attrs.get("scheduled_at", getattr(instance, "scheduled_at", None))
        status = attrs.get("status", getattr(instance, "status", Appointment.Status.SCHEDULED))

        if patient and not patient.active:
            raise serializers.ValidationError({"patient": "Paciente inativo nao pode receber consulta."})
        if trainee and not trainee.active:
            raise serializers.ValidationError({"trainee": "Estagiario inativo nao pode receber consulta."})
        if trainee and scheduled_at and status == Appointment.Status.SCHEDULED:
            conflict = Appointment.objects.filter(
                trainee=trainee,
                scheduled_at=scheduled_at,
                status=Appointment.Status.SCHEDULED,
                active=True,
            )
            if instance:
                conflict = conflict.exclude(pk=instance.pk)
            if conflict.exists():
                raise serializers.ValidationError(
                    {"scheduled_at": "Ja existe consulta agendada para este estagiario neste horario."}
                )
        return attrs


class ReportQuerySerializer(serializers.Serializer):
    trainee_id = serializers.IntegerField(required=False)
    patient_id = serializers.IntegerField(required=False)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if bool(start_date) != bool(end_date):
            raise serializers.ValidationError("Informe start_date e end_date juntos.")
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date deve ser anterior ou igual a end_date.")
        return attrs
