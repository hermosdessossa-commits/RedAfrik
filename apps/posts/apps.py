"""App des publications : posts dans les communautés."""

from django.apps import AppConfig


class PostsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.posts"
    verbose_name = "Publications"
