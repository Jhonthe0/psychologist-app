from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from core.models import Appointment, Patient, Trainee
from core.permissions import IsAdminRole, IsTraineeRole
from core.serializers import (
    AppointmentSerializer,
    PatientSerializer,
    ReportQuerySerializer,
    RoleTokenObtainPairSerializer,
    TraineeSerializer,
)


class HomeView(TemplateView):
    template_name = "home.html"


class LoginView(TemplateView):
    template_name = "login.html"


class AdminDashboardView(TemplateView):
    template_name = "app/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointments = Appointment.objects.select_related("patient", "trainee", "trainee__user")
        context.update(
            {
                "active_patients_count": Patient.objects.filter(active=True).count(),
                "active_trainees_count": Trainee.objects.filter(active=True).count(),
                "scheduled_appointments_count": appointments.filter(
                    active=True,
                    status=Appointment.Status.SCHEDULED,
                ).count(),
                "upcoming_appointments": appointments.filter(
                    active=True,
                    status=Appointment.Status.SCHEDULED,
                    scheduled_at__gte=timezone.now(),
                ).order_by("scheduled_at")[:5],
            }
        )
        return context


class AdminPatientsPageView(TemplateView):
    template_name = "app/patients.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["patients"] = Patient.objects.order_by("name")
        return context


class AdminTraineesPageView(TemplateView):
    template_name = "app/trainees.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["trainees"] = Trainee.objects.select_related("user").order_by("user__first_name", "user__last_name")
        return context


class AdminAppointmentsPageView(TemplateView):
    template_name = "app/appointments.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["appointments"] = Appointment.objects.select_related("patient", "trainee", "trainee__user").order_by(
            "scheduled_at"
        )
        return context


class TraineeAgendaPageView(TemplateView):
    template_name = "app/agenda.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointments = Appointment.objects.select_related("patient", "trainee", "trainee__user").filter(
            scheduled_at__gte=timezone.now(),
            status=Appointment.Status.SCHEDULED,
            active=True,
        )
        if self.request.user.is_authenticated:
            appointments = appointments.filter(trainee__user=self.request.user)
        context["appointments"] = appointments
        return context


class RoleTokenObtainPairView(TokenObtainPairView):
    serializer_class = RoleTokenObtainPairSerializer


class AdminPatientViewSet(viewsets.ModelViewSet):
    serializer_class = PatientSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        queryset = Patient.objects.all()
        include_inactive = self.request.query_params.get("include_inactive") == "true"
        if not include_inactive:
            queryset = queryset.filter(active=True)
        return queryset

    def perform_destroy(self, instance):
        if instance.has_future_appointments():
            return Response(
                {"detail": "Paciente possui consultas futuras agendadas."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.active = False
        instance.save(update_fields=["active", "updated_at"])

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.has_future_appointments():
            return Response(
                {"detail": "Paciente possui consultas futuras agendadas."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.active = False
        instance.save(update_fields=["active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminTraineeViewSet(viewsets.ModelViewSet):
    serializer_class = TraineeSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        queryset = Trainee.objects.select_related("user")
        include_inactive = self.request.query_params.get("include_inactive") == "true"
        if not include_inactive:
            queryset = queryset.filter(active=True)
        return queryset

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.has_future_appointments():
            return Response(
                {"detail": "Estagiario possui consultas futuras agendadas."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.active = False
        instance.user.is_active = False
        instance.user.save(update_fields=["is_active"])
        instance.save(update_fields=["active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminAppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        queryset = Appointment.objects.select_related("patient", "trainee", "trainee__user")
        include_inactive = self.request.query_params.get("include_inactive") == "true"
        if not include_inactive:
            queryset = queryset.filter(active=True).exclude(status=Appointment.Status.CANCELED)
        return queryset

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        if appointment.status != Appointment.Status.SCHEDULED:
            return Response(
                {"detail": "Somente consultas agendadas podem ser canceladas."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cancellation_reason = request.data.get("cancellation_reason", "")
        if cancellation_reason and cancellation_reason not in Appointment.CancellationReason.values:
            return Response(
                {"cancellation_reason": "Motivo de cancelamento invalido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        appointment.status = Appointment.Status.CANCELED
        appointment.cancellation_reason = cancellation_reason
        appointment.active = False
        appointment.save(update_fields=["status", "cancellation_reason", "active", "updated_at"])
        return Response(self.get_serializer(appointment).data)


class AdminReportsViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminRole]

    def _appointments(self):
        return Appointment.objects.select_related("patient", "trainee", "trainee__user")

    @action(detail=False, methods=["get"], url_path="by-trainee")
    def by_trainee(self, request):
        serializer = ReportQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        trainee_id = serializer.validated_data.get("trainee_id")
        if not trainee_id:
            return Response({"detail": "Informe trainee_id."}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self._appointments().filter(trainee_id=trainee_id)
        return Response(AppointmentSerializer(queryset, many=True).data)

    @action(detail=False, methods=["get"], url_path="by-patient")
    def by_patient(self, request):
        serializer = ReportQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        patient_id = serializer.validated_data.get("patient_id")
        if not patient_id:
            return Response({"detail": "Informe patient_id."}, status=status.HTTP_400_BAD_REQUEST)
        queryset = self._appointments().filter(patient_id=patient_id)
        return Response(AppointmentSerializer(queryset, many=True).data)

    @action(detail=False, methods=["get"], url_path="by-period")
    def by_period(self, request):
        serializer = ReportQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        start_date = serializer.validated_data.get("start_date")
        end_date = serializer.validated_data.get("end_date")
        if not start_date or not end_date:
            return Response(
                {"detail": "Informe start_date e end_date."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        queryset = self._appointments().filter(scheduled_at__range=(start_date, end_date))
        return Response(AppointmentSerializer(queryset, many=True).data)


class TraineeAgendaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsTraineeRole]

    def get_queryset(self):
        return Appointment.objects.select_related("patient", "trainee", "trainee__user").filter(
            trainee__user=self.request.user,
            scheduled_at__gte=timezone.now(),
            status=Appointment.Status.SCHEDULED,
            active=True,
        )

    @action(detail=True, methods=["patch"], url_path="meeting-link")
    def meeting_link(self, request, pk=None):
        appointment = self.get_object()
        call_link = request.data.get("call_link")
        if not call_link:
            return Response({"detail": "Informe call_link."}, status=status.HTTP_400_BAD_REQUEST)
        appointment.call_link = call_link
        appointment.save(update_fields=["call_link", "updated_at"])
        return Response(self.get_serializer(appointment).data)
