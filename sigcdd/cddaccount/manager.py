import traceback

from django.db import models
from helpers.models import Role
class CompteDepotQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role==Role.ADMIN:#ASSANE
                    return self.all()
                elif user.role==Role.AGENT_DCP:
                    return self.all()
                elif user.role==Role.AGENT_TG:
                    return self.all()
                elif user.role==Role.AGENT_DS:
                    return self.filter(secrete=False)
                elif user.role==Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(poste_id=user.agent_postecomptable.poste_id).exclude(
                            validation_cd=None)

                    else:return self.filter(poste_id=user.agent_postecomptable.poste_id,secrete=False).exclude(validation_cd=None)

                elif user.role==Role.AGENT_SAISIE_CD:
                    return user.agent_saisie_cd.comptes.filter(actif=True,secrete=False).exclude(validation_cd=None)
                elif user.role==Role.GERANT:
                    ids=user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return  self.filter(id__in=ids)
                else:
                    return self.none()
            except Exception:
                return self.none()

class CompteDepotManager(models.Manager):
    def get_queryset(self, ):
        return CompteDepotQuerySet(self.model, using=self._db)  # Important!
    def by_agent(self, user):
        return self.get_queryset().by_agent(user)


class GestionCompteDepotQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role==Role.ADMIN:
                    return self.all()
                elif user.role==Role.AGENT_DCP:
                    return self.none()
                elif user.role==Role.AGENT_TG:
                    return self.all()
                elif user.role==Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(compte__poste_id=user.agent_postecomptable.poste_id)

                    else :return self.filter(compte__poste_id=user.agent_postecomptable.poste_id,compte__secrete=False)

                elif user.role==Role.AGENT_SAISIE_CD:
                    return user.agent_saisie_cd.comptescd_agentsaisiecd.filter(actif=True,compte__secrete=False)
                elif user.role==Role.GERANT:
                    return self.filter(gerant_id=user.gerant_dc.id,compte__secrete=False)
                else:
                    return self.none()
            except Exception:
                return self.none()

class GestionCompteDepotManager(models.Manager):
    def get_queryset(self, ):
        return GestionCompteDepotQuerySet(self.model, using=self._db)  # Important!
    def by_agent(self, user):
        return self.get_queryset().by_agent(user)


class GerantCDQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_PC:
                    return self.filter(poste_id=user.agent_postecomptable.poste_id)
                elif user.role == Role.GERANT:
                    return self.filter(id=user.gerant_cd.id)
                else:
                    return self.none()
            except Exception:
                return self.none()


class GerantCDManager(models.Manager):
    def get_queryset(self, ):
        return GerantCDQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)


#GerantCDManager



class AgentSaisieCDQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_PC:
                    return self.filter(gerant__poste_id=user.agent_postecomptable.poste_id)
                elif user.role == Role.GERANT:
                    return self.filter(gerant_id=user.gerant_cd.id)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.filter(id=user.agent_saisie_cd.id)

                else:
                    return self.none()
            except Exception:
                return self.none()


class AgentSaisieCDManager(models.Manager):
    def get_queryset(self, ):
        return AgentSaisieCDQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)





class OrdrePaymentQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_DS:
                    return self.filter( compte__secrete=False)
                elif user.role==Role.AGENT_TG:
                    return self.all()

                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(compte__poste_id=user.agent_postecomptable.poste_id)
                    else:return self.filter(compte__poste_id=user.agent_postecomptable.poste_id,compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True).values_list("compte_id", flat=True)
                    return self.filter(compte_id__in=ids,compte__secrete=False)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.filter(creator_id=user.id,compte__secrete=False)

                else:
                    return self.none()
            except Exception:
                return self.none()


class OrdrePaymentManager(models.Manager):
    def get_queryset(self, ):
        return OrdrePaymentQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)



class DepositaireQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_TG:
                    return self.all()
                elif user.role == Role.AGENT_DS:
                    return self.filter(compte__secrete=False)
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return  self.filter(comptes__poste_id=user.agent_postecomptable.poste_id)
                    else: return self.filter(comptes__poste_id=user.agent_postecomptable.poste_id,comptes__secrete=False)
                elif user.role == Role.GERANT:
                    compte_ids=user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(comptes__id__in=compte_ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    compte_ids=user.agent_saisie_cd.comptes.filter(actif=True).values_list("compte_id", flat=True)
                    return self.filter(comptes__id__in=compte_ids)

                else:
                    return self.none()
            except Exception:
                return self.none()


class DepositaireManager(models.Manager):
    def get_queryset(self, ):
        return DepositaireQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)





class AvisDeCreditQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_TG:
                    return self.all()
                elif user.role == Role.AGENT_DS:
                    return  self.filter( compte__secrete=False)
                elif user.role == Role.AGENT_PC:

                    if user.agent_postecomptable.is_master:

                        return self.filter(compte__poste_id=user.agent_postecomptable.poste_id)
                    else:
                        return  self.filter(compte__poste_id=user.agent_postecomptable.poste_id,compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(compte_id__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.none()
                else:
                    return self.none()
            except Exception:
                traceback.print_exc()
                return self.none()


class AvisDeCreditManager(models.Manager):
    def get_queryset(self, ):
        return AvisDeCreditQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)


class AvisDeDebitQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_TG:
                    return  self.all()
                elif user.role == Role.AGENT_DS:
                    return  self.filter( compte__secrete=False)
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(compte__poste_id=user.agent_postecomptable.poste_id)
                    else:return self.filter(compte__poste_id=user.agent_postecomptable.poste_id,compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(compte_id__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.none()

                else:
                    return self.none()
            except Exception:
                return self.none()


class AvisDeDebitManager(models.Manager):
    def get_queryset(self, ):
        return AvisDeDebitQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)


class BlocageFondQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_TG:
                   return self.all()
                elif user.role == Role.AGENT_DS:
                    return  self.filter( compte__secrete=False)
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(compte__poste_id=user.agent_postecomptable.poste_id)
                    else : return self.filter(compte__poste_id=user.agent_postecomptable.poste_id,compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(compte_id__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.none()

                else:
                    return self.none()
            except Exception:
                return self.none()


class BlocageFondManager(models.Manager):
    def get_queryset(self, ):
        return BlocageFondQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)



class ProjetQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_TG:
                    return self.all()
                elif user.role == Role.AGENT_DS:
                    return self.filter( compte__secrete=False)
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(compte__poste_id=user.agent_postecomptable.poste_id,demande_blocage=True)
                    else: return self.filter(compte__poste_id=user.agent_postecomptable.poste_id,demande_blocage=True,compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(compte_id__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.none()

                else:
                    return self.none()
            except Exception:
                return self.none()


class ProjetManager(models.Manager):
    def get_queryset(self, ):
        return ProjetQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)




class AnnulationBlocageFondQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_TG:
                    return self.all()
                elif user.role == Role.AGENT_DS:
                    return  self.filter( blocage__compte__secrete=False)
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(blocage__compte__poste_id=user.agent_postecomptable.poste_id)
                    else:
                        return self.filter(blocage__compte__poste_id=user.agent_postecomptable.poste_id,blocage__compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,blocage__compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(blocage__compte_id__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.none()

                else:
                    return self.none()
            except Exception:
                return self.none()


class AnnulationBlocageFondManager(models.Manager):
    def get_queryset(self, ):
        return AnnulationBlocageFondQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)


class ReportQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_TG:
                    return self.all()
                elif user.role == Role.AGENT_DS:
                    return self.filter( compte__secrete=False)
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(compte__poste_id=user.agent_postecomptable.poste_id)
                    else:return self.filter(compte__poste_id=user.agent_postecomptable.poste_id,compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(compte_id__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.none()

                else:
                    return self.none()
            except Exception:
                return self.none()


class ReportManager(models.Manager):
    def get_queryset(self, ):
        return ReportQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)



class BalanceQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role==Role.ADMIN:
                    return self.all()
                elif user.role==Role.AGENT_DCP:
                    return self.all()
                elif user.role == Role.AGENT_TG:
                    return self.all()
                elif user.role == Role.AGENT_DS:
                    return  self.filter( compte__secrete=False)
                elif user.role==Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(compte__poste_id=user.agent_postecomptable.poste_id)
                    else:return self.filter(compte__poste_id=user.agent_postecomptable.poste_id,compte__secrete=False)

                elif user.role==Role.AGENT_SAISIE_CD:
                    ids = user.agent_saisie_cd.comptes.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return  self.filter(compte__id__in=ids)
                elif user.role==Role.GERANT:
                    ids=user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return  self.filter(compte__id__in=ids)
                else:
                    return self.none()
            except Exception:
                return self.none()

class BalanceManager(models.Manager):
    def get_queryset(self, ):
        return BalanceQuerySet(self.model, using=self._db)  # Important!
    def by_agent(self, user):
        return self.get_queryset().by_agent(user)





class OPTransationQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_TG:
                    return self.all()
                elif user.role == Role.AGENT_DS:
                    return  self.filter( reservation__ordre__compte__secrete=False)
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(poste_comptable=user.agent_postecomptable.poste.reference)
                    else:
                        return self.filter(poste_comptable=user.agent_postecomptable.poste.reference,reservation__ordre__compte__secrete=False)
                else:
                    return self.none()
            except Exception:
                return self.none()


class OPTransationManager(models.Manager):
    def get_queryset(self, ):
        return OPTransationQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)




class VirementDetailsQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_TG:
                    return self.all()

                elif user.role == Role.AGENT_DS:
                    return  self.filter( virement__compte__secrete=False)
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(virement__compte__poste_id=user.agent_postecomptable.poste_id)
                    else:
                        return self.filter(virement__compte__poste_id=user.agent_postecomptable.poste_id,virement__compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(virement__compte_id__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.filter(virement__creator_id=user.id,virement__compte__secrete=False)

                else:
                    return self.none()
            except Exception:
                return self.none()


class VirementDetailsManager(models.Manager):
    def get_queryset(self, ):
        return VirementDetailsQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)




class PrisEnchageOrdrePaymentQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_TG:
                    return self.all()
                elif user.role == Role.AGENT_DS:
                    return self.filter( ordre__compte__secrete=False)
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(ordre__compte__poste_id=user.agent_postecomptable.poste_id)
                    else:return self.filter(ordre__compte__poste_id=user.agent_postecomptable.poste_id,ordre__compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(ordre__compte_id__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.filter(ordre__creator_id=user.id,ordre__compte__secrete=False)

                else:
                    return self.none()
            except Exception:
                return self.none()


class PrisEnchageOrdrePaymentManager(models.Manager):
    def get_queryset(self, ):
        return PrisEnchageOrdrePaymentQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)



class ReservationFondQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_TG:
                    return self.all()
                elif user.role == Role.AGENT_DS:
                    return self.filter( ordre__compte__secrete=False)
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(ordre__compte__poste_id=user.agent_postecomptable.poste_id)
                    else:return self.filter(ordre__compte__poste_id=user.agent_postecomptable.poste_id,ordre__compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(ordre__compte_id__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.filter(ordre__creator_id=user.id,ordre__compte__secrete=False)

                else:
                    return self.none()
            except Exception:
                return self.none()


class ReservationFondManager(models.Manager):
    def get_queryset(self, ):
        return ReservationFondQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)


class MandataireQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_PC:
                    return self.filter(gerant__poste_id=user.agent_postecomptable.poste_id)
                elif user.role == Role.GERANT:
                    return self.filter(gerant_id=user.gerant_cd.id)
                elif user.role == Role.AGENT_SAISIE_CD:
                    # compte_ids=user.agent_saisie_cd.comptes.filter(actif=True).values_list("compte_id", flat=True)
                    return self.none()

                else:
                    return self.none()
            except Exception:
                return self.none()


class MandataireManager(models.Manager):
    def get_queryset(self, ):
        return MandataireQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)
