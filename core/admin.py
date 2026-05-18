from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from core.models import Appointment, Patient, Trainee, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Perfil PsiLine", {"fields": ("role",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Perfil PsiLine", {"fields": ("email", "role")}),
    )
    list_display = ("username", "email", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("name", "cpf", "email", "phone", "active")
    list_filter = ("active",)
    search_fields = ("name", "cpf", "email")


@admin.register(Trainee)
class TraineeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "registration_number", "email", "phone", "active")
    list_filter = ("active",)
    search_fields = ("user__first_name", "user__last_name", "user__email", "registration_number")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("scheduled_at", "patient", "trainee", "status", "active")
    list_filter = ("status", "active", "scheduled_at")
    search_fields = ("patient__name", "trainee__user__first_name", "trainee__user__last_name")
