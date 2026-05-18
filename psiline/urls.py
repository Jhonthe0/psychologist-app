from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from core.views import RoleTokenObtainPairView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", RoleTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("core.urls")),
]
