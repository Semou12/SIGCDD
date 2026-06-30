from django.test import TestCase

from cddaccount import ETAPE_ORDRE_PAYMENT
from cddaccount.models import AnneeComptable, JourneeComptable, ReservationFond

def update_rsv_th_mean():
	obx= ReservationFond.objects.filter(payment_mean=None, close=False, reliquat__gt=0,ordre__annulation_op=None,ordre__etape=ETAPE_ORDRE_PAYMENT.PRISE_EN_CHARGE)
	for o in obx:
		o.payment_mean=o.ordre.payment_mean
		o.save()
