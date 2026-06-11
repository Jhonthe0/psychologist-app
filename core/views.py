from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count
from django.db.models import Q
from django.db.models.functions import TruncDate
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import TemplateView, View
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from core.models import Appointment, Patient, Trainee
from core.permissions import IsAdminRole, IsTraineeRole
from core.formatters import only_digits
from core.serializers import (
    AppointmentSerializer,
    PatientSerializer,
    ReportQuerySerializer,
    RoleTokenObtainPairSerializer,
    TraineeSerializer,
)


class HomeView(TemplateView):
    template_name = "home.html"


class LoginView(View):
    template_name = "login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(self._redirect_for_user(request.user))
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        role_hint = request.POST.get("role_hint", "")
        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Usuario ou senha invalidos.")
            return render(request, self.template_name, status=401)

        if role_hint == "admin" and not (user.is_staff or user.role == "admin"):
            messages.error(request, "Esta conta nao possui acesso de professor.")
            return render(request, self.template_name, status=403)

        if role_hint == "trainee" and user.role != "trainee":
            messages.error(request, "Esta conta nao possui acesso de estudante.")
            return render(request, self.template_name, status=403)

        login(request, user)
        return redirect(self._redirect_for_user(user))

    def _redirect_for_user(self, user):
        if user.role == "trainee" and not user.is_staff:
            return "app-agenda"
        return "app-dashboard"


class AdminOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = "frontend-login"

    def test_func(self):
        user = self.request.user
        return user.is_staff or user.role == "admin"


class TraineeOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = "frontend-login"

    def test_func(self):
        return self.request.user.role == "trainee"


class AdminDashboardView(AdminOnlyMixin, TemplateView):
    template_name = "app/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointments = Appointment.objects.select_related("patient", "trainee", "trainee__user")
        today = timezone.localdate()
        start_date = self._parse_date(self.request.GET.get("start_date")) or today
        end_date = self._parse_date(self.request.GET.get("end_date")) or today + timedelta(days=30)
        if end_date < start_date:
            start_date, end_date = end_date, start_date

        period_appointments = appointments.filter(
            scheduled_at__date__gte=start_date,
            scheduled_at__date__lte=end_date,
        )
        status_counts = {
            row["status"]: row["total"]
            for row in period_appointments.values("status").annotate(total=Count("id"))
        }
        total_period_appointments = sum(status_counts.values())
        scheduled_count = status_counts.get(Appointment.Status.SCHEDULED, 0)
        completed_count = status_counts.get(Appointment.Status.COMPLETED, 0)
        canceled_count = status_counts.get(Appointment.Status.CANCELED, 0)
        status_chart = self._status_chart(total_period_appointments, scheduled_count, completed_count, canceled_count)
        daily_distribution = list(
            period_appointments.annotate(day=TruncDate("scheduled_at"))
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")[:10]
        )
        max_daily_total = max([item["total"] for item in daily_distribution] or [1])

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
                "start_date": start_date,
                "end_date": end_date,
                "total_period_appointments": total_period_appointments,
                "period_scheduled_count": scheduled_count,
                "period_completed_count": completed_count,
                "period_canceled_count": canceled_count,
                "cancellation_rate": round((canceled_count / total_period_appointments) * 100)
                if total_period_appointments
                else 0,
                "status_chart": status_chart,
                "daily_distribution": [
                    {
                        "day": item["day"],
                        "total": item["total"],
                        "percent": round((item["total"] / max_daily_total) * 100),
                    }
                    for item in daily_distribution
                ],
            }
        )
        return context

    def _parse_date(self, value):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    def _status_chart(self, total, scheduled, completed, canceled):
        if not total:
            return {
                "scheduled_percent": 0,
                "completed_percent": 0,
                "canceled_percent": 0,
                "gradient": "#d8e6ec 0 100%",
            }
        scheduled_percent = round((scheduled / total) * 100)
        completed_percent = round((completed / total) * 100)
        canceled_percent = max(0, 100 - scheduled_percent - completed_percent)
        scheduled_end = scheduled_percent
        completed_end = scheduled_end + completed_percent
        return {
            "scheduled_percent": scheduled_percent,
            "completed_percent": completed_percent,
            "canceled_percent": canceled_percent,
            "gradient": (
                f"#0f6b8f 0 {scheduled_end}%, "
                f"#1a9b8f {scheduled_end}% {completed_end}%, "
                f"#b42318 {completed_end}% 100%"
            ),
        }


class AdminPatientsPageView(AdminOnlyMixin, TemplateView):
    template_name = "app/patients.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {
            "name": self.request.GET.get("name", "").strip(),
            "cpf": self.request.GET.get("cpf", "").strip(),
            "phone": self.request.GET.get("phone", "").strip(),
            "email": self.request.GET.get("email", "").strip(),
            "status": self.request.GET.get("status", "").strip(),
        }
        patients = Patient.objects.order_by("name")
        if filters["name"]:
            patients = patients.filter(name__icontains=filters["name"])
        if filters["cpf"]:
            patients = patients.filter(cpf__icontains=only_digits(filters["cpf"]))
        if filters["phone"]:
            patients = patients.filter(phone__icontains=only_digits(filters["phone"]))
        if filters["email"]:
            patients = patients.filter(email__icontains=filters["email"])
        if filters["status"] == "active":
            patients = patients.filter(active=True)
        if filters["status"] == "inactive":
            patients = patients.filter(active=False)
        context["patients"] = patients
        context["patient_filters"] = filters
        return context


class AdminTraineesPageView(AdminOnlyMixin, TemplateView):
    template_name = "app/trainees.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {
            "name": self.request.GET.get("name", "").strip(),
            "registration_number": self.request.GET.get("registration_number", "").strip(),
            "email": self.request.GET.get("email", "").strip(),
            "phone": self.request.GET.get("phone", "").strip(),
            "status": self.request.GET.get("status", "").strip(),
        }
        trainees = Trainee.objects.select_related("user").order_by("user__first_name", "user__last_name")
        if filters["name"]:
            trainees = trainees.filter(
                Q(user__first_name__icontains=filters["name"])
                | Q(user__last_name__icontains=filters["name"])
                | Q(user__username__icontains=filters["name"])
            )
        if filters["registration_number"]:
            trainees = trainees.filter(registration_number__icontains=filters["registration_number"])
        if filters["email"]:
            trainees = trainees.filter(user__email__icontains=filters["email"])
        if filters["phone"]:
            trainees = trainees.filter(phone__icontains=only_digits(filters["phone"]))
        if filters["status"] == "active":
            trainees = trainees.filter(active=True)
        if filters["status"] == "inactive":
            trainees = trainees.filter(active=False)
        context["trainees"] = trainees
        context["trainee_filters"] = filters
        return context


class AdminAppointmentsPageView(AdminOnlyMixin, TemplateView):
    template_name = "app/appointments.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = {
            "start_date": self.request.GET.get("start_date", "").strip(),
            "end_date": self.request.GET.get("end_date", "").strip(),
            "patient": self.request.GET.get("patient", "").strip(),
            "trainee": self.request.GET.get("trainee", "").strip(),
            "status": self.request.GET.get("status", "").strip(),
        }
        appointments = Appointment.objects.select_related("patient", "trainee", "trainee__user").order_by(
            "scheduled_at"
        )
        start_date = self._parse_date(filters["start_date"])
        end_date = self._parse_date(filters["end_date"])
        if start_date:
            appointments = appointments.filter(scheduled_at__date__gte=start_date)
        if end_date:
            appointments = appointments.filter(scheduled_at__date__lte=end_date)
        if filters["patient"]:
            appointments = appointments.filter(patient__name__icontains=filters["patient"])
        if filters["trainee"]:
            appointments = appointments.filter(
                Q(trainee__user__first_name__icontains=filters["trainee"])
                | Q(trainee__user__last_name__icontains=filters["trainee"])
                | Q(trainee__registration_number__icontains=filters["trainee"])
            )
        if filters["status"] in Appointment.Status.values:
            appointments = appointments.filter(status=filters["status"])
        context["appointments"] = appointments
        context["appointment_filters"] = filters
        context["appointment_statuses"] = Appointment.Status.choices
        return context

    def _parse_date(self, value):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None


class TraineeAgendaPageView(TraineeOnlyMixin, TemplateView):
    template_name = "app/agenda.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointments = Appointment.objects.select_related("patient", "trainee", "trainee__user").filter(
            scheduled_at__gte=timezone.now(),
            status=Appointment.Status.SCHEDULED,
            active=True,
        )
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
