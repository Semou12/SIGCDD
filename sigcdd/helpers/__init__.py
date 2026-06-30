from django.conf import settings
from django.utils.translation import pgettext_lazy

class TypePiece:
    CNI = 'CNI'
    PASSEPORT = 'PASSEPORT'
    PERMIS = 'PERMIS'
    EXTRAIT= "EXTRAIT"
    CHOICES = [
        (CNI, pgettext_lazy('CNI', 'CNI')),
        (PERMIS, pgettext_lazy('PERMIS', 'PERMIS')),
        (EXTRAIT, pgettext_lazy('EXTRAIT', 'EXTRAIT')),
        (PASSEPORT, pgettext_lazy('PASSEPORT', 'PASSEPORT')),
    ]


class SexeType:
    H = 'H'
    F = 'F'
    CHOICES = [
        (F, pgettext_lazy('Health cover type', "Femme")),
        (H, pgettext_lazy('Health cover', 'Homme')),
    ]
