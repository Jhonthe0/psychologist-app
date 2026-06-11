from django.contrib import admin
from django.urls import include, path
from django.contrib.auth.views import LogoutView
from rest_framework_simplejwt.views import TokenRefreshView

from core.views import (
    AdminAppointmentsPageView,
    AdminDashboardView,
    AdminPatientsPageView,
    AdminTraineesPageView,
    HomeView,
    LoginView,
    RoleTokenObtainPairView,
    TraineeAgendaPageView,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("login/", LoginView.as_view(), name="frontend-login"),
    path("logout/", LogoutView.as_view(next_page="frontend-login"), name="frontend-logout"),
    path("app/", AdminDashboardView.as_view(), name="app-dashboard"),
    path("app/patients/", AdminPatientsPageView.as_view(), name="app-patients"),
    path("app/trainees/", AdminTraineesPageView.as_view(), name="app-trainees"),
    path("app/appointments/", AdminAppointmentsPageView.as_view(), name="app-appointments"),
    path("app/agenda/", TraineeAgendaPageView.as_view(), name="app-agenda"),
    path("admin/", admin.site.urls),
    path("api/auth/token/", RoleTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("core.urls")),
]
