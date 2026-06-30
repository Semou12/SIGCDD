from __future__ import absolute_import
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def async_add(x,y):
    logger.info("res:{}".format(x+y))
    return x+y



from django.db.models.signals import post_delete
from django.dispatch import receiver
from allauth.mfa.models import Authenticator


@receiver(post_delete, sender=Authenticator)
def invalidate_sessions_on_authenticator_delete(sender, instance, **kwargs):
    """
    Quand un Authenticator TOTP est supprimé (via l'admin ou le code),
    on invalide TOUTES les sessions Django actives de cet utilisateur.
    Cela casse la boucle /2fa/authenticate/ ↔ /login/ causée par
    une session MFA pendante sans device valide.
    """
    from django.contrib.sessions.models import Session
    from django.utils import timezone

    user = instance.user
    user_pk_str = str(user.pk)

    # On ne parcourt que les sessions non expirées
    active_sessions = Session.objects.filter(expire_date__gte=timezone.now())

    to_delete = []
    for session in active_sessions:
        try:
            data = session.get_decoded()
            if data.get("_auth_user_id") == user_pk_str:
                to_delete.append(session.pk)
        except Exception:
            continue

    if to_delete:
        Session.objects.filter(pk__in=to_delete).delete()
