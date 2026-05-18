from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.views import (
    AdminAppointmentViewSet,
    AdminPatientViewSet,
    AdminReportsViewSet,
    AdminTraineeViewSet,
    TraineeAgendaViewSet,
)

router = DefaultRouter()
router.register("admin/patients", AdminPatientViewSet, basename="admin-patients")
router.register("admin/trainees", AdminTraineeViewSet, basename="admin-trainees")
router.register("admin/appointments", AdminAppointmentViewSet, basename="admin-appointments")
router.register("admin/reports", AdminReportsViewSet, basename="admin-reports")
router.register("trainee/agenda", TraineeAgendaViewSet, basename="trainee-agenda")

urlpatterns = [
    path("", include(router.urls)),
]
