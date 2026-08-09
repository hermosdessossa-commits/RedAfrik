"""
Signaux de l'app votes.

À chaque changement de vote (création, modification, suppression), le score
dénormalisé du post ou du commentaire est ajusté par delta (mise à jour
atomique via F), ainsi que le karma de l'auteur du contenu. Cette approche
par delta évite de resommer la table entière des votes à chaque événement
(problématique en cas de suppression en cascade d'un contenu très voté).

À la suppression d'un post ou d'un commentaire, le karma de son auteur est
recalculé intégralement pour rester exact dans tous les cas de figure
(suppression isolée, suppression en cascade d'une communauté, etc.).
"""

from django.db.models import F, Sum
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.comments.models import Commentaire
from apps.posts.models import Post
from apps.users.models import User

from .models import VoteCommentaire, VotePost


def calculer_score(votes):
    """Somme des valeurs d'un queryset de votes (0 si aucun vote)."""
    return votes.aggregate(total=Sum("valeur"))["total"] or 0


def mettre_a_jour_karma(auteur_id):
    """
    Recalcule le karma d'un utilisateur : somme des scores de ses posts
    et de ses commentaires.
    """
    karma_posts = (
        Post.objects.filter(auteur_id=auteur_id).aggregate(total=Sum("score"))["total"]
        or 0
    )
    karma_commentaires = (
        Commentaire.objects.filter(auteur_id=auteur_id).aggregate(
            total=Sum("score")
        )["total"]
        or 0
    )
    User.objects.filter(pk=auteur_id).update(
        karma=karma_posts + karma_commentaires
    )


# --- Utilitaires --------------------------------------------------------------


def _valeur_precedente(instance):
    """Valeur du vote avant sa modification (mémorisée en pre_save)."""
    return getattr(instance, "_valeur_precedente", 0)


def _delta_du_vote(instance):
    """
    Delta du vote si sa valeur était purement remplacée par la précédente :
    nouveau - ancien. Un vote qui n'existait pas encore a une ancienne
    valeur nulle.
    """
    return instance.valeur - _valeur_precedente(instance)


def _enregistrer_vote_post(instance, delta):
    """
    Applique le delta du vote au score du post et au karma de son auteur.

    Si le post n'existe plus (suppression en cascade d'une communauté), le
    score disparaît avec lui et le karma sera recalculé par le signal
    post_delete du Post : on ne fait rien ici.
    """
    if not delta:
        return
    auteur_id = (
        Post.objects.filter(pk=instance.post_id)
        .values_list("auteur_id", flat=True)
        .first()
    )
    if auteur_id is None:
        return
    Post.objects.filter(pk=instance.post_id).update(
        score=F("score") + delta
    )
    User.objects.filter(pk=auteur_id).update(karma=F("karma") + delta)


def _enregistrer_vote_commentaire(instance, delta):
    """Idem pour un commentaire."""
    if not delta:
        return
    auteur_id = (
        Commentaire.objects.filter(pk=instance.commentaire_id)
        .values_list("auteur_id", flat=True)
        .first()
    )
    if auteur_id is None:
        return
    Commentaire.objects.filter(pk=instance.commentaire_id).update(
        score=F("score") + delta
    )
    User.objects.filter(pk=auteur_id).update(karma=F("karma") + delta)


@receiver(pre_save, sender=VotePost)
def _vote_post_avant_sauvegarde(sender, instance, **kwargs):
    """Mémorise la valeur du vote avant son écrasement (calcul du delta)."""
    if instance.pk:
        instance._valeur_precedente = (
            VotePost.objects.filter(pk=instance.pk)
            .values_list("valeur", flat=True)
            .first()
            or 0
        )


@receiver(post_save, sender=VotePost)
def _vote_post_enregistre(sender, instance, **kwargs):
    _enregistrer_vote_post(instance, _delta_du_vote(instance))


@receiver(post_delete, sender=VotePost)
def _vote_post_supprime(sender, instance, **kwargs):
    # Le vote disparaît : son apport est retiré du score et du karma.
    _enregistrer_vote_post(instance, -instance.valeur)


@receiver(pre_save, sender=VoteCommentaire)
def _vote_commentaire_avant_sauvegarde(sender, instance, **kwargs):
    if instance.pk:
        instance._valeur_precedente = (
            VoteCommentaire.objects.filter(pk=instance.pk)
            .values_list("valeur", flat=True)
            .first()
            or 0
        )


@receiver(post_save, sender=VoteCommentaire)
def _vote_commentaire_enregistre(sender, instance, **kwargs):
    _enregistrer_vote_commentaire(instance, _delta_du_vote(instance))


@receiver(post_delete, sender=VoteCommentaire)
def _vote_commentaire_supprime(sender, instance, **kwargs):
    _enregistrer_vote_commentaire(instance, -instance.valeur)


# --- Karma après suppression de contenu --------------------------------------


@receiver(post_delete, sender=Post)
def _post_supprime(sender, instance, **kwargs):
    # Le post n'existe plus : son score ne doit plus contribuer au karma
    # de son auteur (la somme des scores des posts restants le reflète).
    mettre_a_jour_karma(instance.auteur_id)


@receiver(post_delete, sender=Commentaire)
def _commentaire_supprime(sender, instance, **kwargs):
    mettre_a_jour_karma(instance.auteur_id)