"""Administration Django de l'app votes (site RedAfrik)."""

from django.contrib.admin import ModelAdmin

from core.admin import site
from .models import VoteCommentaire, VotePost


class VotePostAdmin(ModelAdmin):
    list_display = ("utilisateur", "post", "valeur", "date_vote")
    list_filter = ("valeur",)


class VoteCommentaireAdmin(ModelAdmin):
    list_display = ("utilisateur", "commentaire", "valeur", "date_vote")
    list_filter = ("valeur",)


site.register(VotePost, VotePostAdmin)
site.register(VoteCommentaire, VoteCommentaireAdmin)