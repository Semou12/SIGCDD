from django.utils.translation import pgettext_lazy

class STATUS_COMMANDE:
    NOUVEAU = 'NOUVEAU'
    ACCEPTE = 'ACCEPTE'
    REJETE = 'REJETE'
    TRAITE = 'TRAITE'

    CHOICES = [
        (NOUVEAU, pgettext_lazy("NOUVEAU", "NOUVEAU")),
        (ACCEPTE, pgettext_lazy("ACCEPTE", "ACCEPTE")),
        (REJETE, pgettext_lazy("REJETE", "REJETE")),
	    (TRAITE, pgettext_lazy("TRAITE", "TRAITE")),
    ]


class STATUS_CHEQUE:
    VISE = 'VISE'
    INCONNU = 'INCONNU'
    MISE_EN_OPPOSITION = 'MISE_EN_OPPOSITION'
    NON_VISE = 'NON_VISE'
    REJET = 'REJET'
    RECEPTIONNE = 'RECEPTIONNE'

    CHOICES = [
        (VISE, pgettext_lazy("VISE", "VISE")),
        (INCONNU, pgettext_lazy("INCONNU", "INCONNU")),
        (MISE_EN_OPPOSITION, pgettext_lazy("MISE_EN_OPPOSITION", "MISE EN OPPOSITION")),
	    (NON_VISE, pgettext_lazy("NON_VISE", "NON VISE")),
        (REJET, pgettext_lazy("REJET", "REJET")),
        (RECEPTIONNE, pgettext_lazy("RECEPTIONNE", "RECEPTIONNE")),
    ]
