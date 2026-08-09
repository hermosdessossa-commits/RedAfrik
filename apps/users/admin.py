"""Administration Django de l'app users (site RedAfrik)."""

from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from core.admin import site

from .models import User


class UserAdmin(DjangoUserAdmin):
    """Admin des utilisateurs : profil communautaire visible dans le formulaire."""

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Profil communautaire", {"fields": ("bio", "avatar_url", "karma")}),
    )
    list_display = ("username", "email", "karma", "date_creation", "is_staff")
    list_filter = ("is_staff", "is_superuser", "is_active")
    ordering = ("-karma", "username")


site.register(User, UserAdmin)