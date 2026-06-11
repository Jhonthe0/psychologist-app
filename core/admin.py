from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from core.formatters import format_cpf, format_phone
from core.models import Appointment, Patient, Trainee, User


admin.site.site_header = "PsiLine Admin"
admin.site.site_title = "PsiLine"
admin.site.index_title = "Administracao clinica"


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
    search_fields = ("username", "email", "first_name", "last_name")
    list_per_page = 25


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("name", "formatted_cpf", "email", "formatted_phone", "birth_date", "active")
    list_filter = ("active",)
    search_fields = ("name", "cpf", "email")
    list_per_page = 25

    @admin.display(description="CPF", ordering="cpf")
    def formatted_cpf(self, obj):
        return format_cpf(obj.cpf)

    @admin.display(description="Telefone", ordering="phone")
    def formatted_phone(self, obj):
        return format_phone(obj.phone)


@admin.register(Trainee)
class TraineeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "registration_number", "email", "formatted_phone", "supervisor_name", "active")
    list_filter = ("active",)
    search_fields = ("user__first_name", "user__last_name", "user__email", "registration_number", "supervisor_name")
    list_per_page = 25

    @admin.display(description="Telefone", ordering="phone")
    def formatted_phone(self, obj):
        return format_phone(obj.phone)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("scheduled_at", "patient", "trainee", "status", "cancellation_reason", "active")
    list_filter = ("status", "cancellation_reason", "active", "scheduled_at")
    search_fields = ("patient__name", "trainee__user__first_name", "trainee__user__last_name")
    date_hierarchy = "scheduled_at"
    list_per_page = 25
