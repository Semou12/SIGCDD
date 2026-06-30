from django.db import models
from helpers.models import Role

class CommandeQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                if user.role == Role.AGENT_DAP:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
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


class CommandeManager(models.Manager):
    def get_queryset(self, ):
        return CommandeQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)

class ChequierQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                if user.role == Role.AGENT_DAP:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(compte__poste_id=user.agent_postecomptable.poste_id)
                    else :return self.filter(compte__poste_id=user.agent_postecomptable.poste_id,compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(compte_id__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.none()

                else:
                    return self.none()
            except Exception:
                return self.none()

class ChequierManager(models.Manager):
    def get_queryset(self, ):
        return ChequierQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)



class ChequeQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                if user.role == Role.AGENT_DAP:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(chequier__compte__poste_id=user.agent_postecomptable.poste_id)
                    else:return self.filter(chequier__compte__poste_id=user.agent_postecomptable.poste_id,chequier__compte__secrete=False)

                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(chequier__compte_id__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.none()

                else:
                    return self.none()
            except Exception:
                return self.none()

class ChequeManager(models.Manager):
    def get_queryset(self, ):
        return ChequeQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)



class CompenseChequeQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                if user.role == Role.AGENT_DAP:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(cheque__chequier__compte__poste_id=user.agent_postecomptable.poste_id)
                    else:return self.filter(cheque__chequier__compte__poste_id=user.agent_postecomptable.poste_id,cheque__chequier__compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(cheque__chequier__compte_id__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.none()

                else:
                    return self.none()
            except Exception:
                return self.none()

class CompenseChequeManager(models.Manager):
    def get_queryset(self, ):
        return CompenseChequeQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)




class MiseEnOppositionQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                if user.role == Role.AGENT_DAP:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(cheque__chequier__compte__poste_id=user.agent_postecomptable.poste_id)
                    else:return self.filter(cheque__chequier__compte__poste_id=user.agent_postecomptable.poste_id,cheque__chequier__compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(cheque__chequier__compte_id__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.none()

                else:
                    return self.none()
            except Exception:
                return self.none()

class MiseEnOppositionManager(models.Manager):
    def get_queryset(self, ):
        return MiseEnOppositionQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)



class AnnulationChequeQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                if user.role == Role.AGENT_DAP:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(cheque__chequier__compte__poste_id=user.agent_postecomptable.poste_id)
                    else : return self.filter(cheque__chequier__compte__poste_id=user.agent_postecomptable.poste_id,cheque__chequier__compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(cheque__chequier__compte_id__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.none()

                else:
                    return self.none()
            except Exception:
                return self.none()

class AnnulationChequeManager(models.Manager):
    def get_queryset(self, ):
        return AnnulationChequeQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)




class RejetChequeQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                if user.role == Role.AGENT_DAP:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(cheque__chequier__compte__poste_id=user.agent_postecomptable.poste_id)
                    else: return self.filter(cheque__chequier__compte__poste_id=user.agent_postecomptable.poste_id,cheque__chequier__compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte_id", flat=True)
                    return self.filter(cheque__chequier__compte_id__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.none()

                else:
                    return self.none()
            except Exception:
                return self.none()

class RejetChequeManager(models.Manager):
    def get_queryset(self, ):
        return RejetChequeQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)




class ChequeScanneQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role == Role.ADMIN:
                    return self.all()
                if user.role == Role.AGENT_DAP:
                    return self.all()
                elif user.role == Role.AGENT_DCP:
                    return self.none()
                elif user.role == Role.AGENT_PC:
                    if user.agent_postecomptable.is_master:
                        return self.filter(poste_id=user.agent_postecomptable.poste_id)
                    else:return self.filter(poste_id=user.agent_postecomptable.poste_id,cheque__chequier__compte__secrete=False)
                elif user.role == Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte__short_compte", flat=True)
                    return self.filter(compte_aster__in=ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    return self.none()

                else:
                    return self.none()
            except Exception:
                return self.none()

class ChequeScanneManager(models.Manager):
    def get_queryset(self, ):
        return ChequeScanneQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)



class ComptableMatiereQuerySet(models.QuerySet):
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
                    if user.agent_postecomptable.is_master:
                        return  self.filter(poste_id=user.agent_postecomptable.poste_id)
                    else: return self.filter(poste_id=user.agent_postecomptable.poste_id)
                elif user.role == Role.GERANT:
                    compte_ids=user.gerant_cd.mes_compte_depots.filter(actif=True,compte__secrete=False).values_list("compte__poste_id", flat=True)
                    return self.filter(poste_id__in=compte_ids)
                elif user.role == Role.AGENT_SAISIE_CD:
                    compte_ids=user.agent_saisie_cd.comptes.filter(actif=True,compte__secrete=False).values_list("compte__poste_id", flat=True)
                    return self.filter(poste_id__in=compte_ids)

                else:
                    return self.none()
            except Exception:
                return self.none()



class ComptableMatiereManager(models.Manager):
    def get_queryset(self, ):
        return ComptableMatiereQuerySet(self.model, using=self._db)  # Important!

    def by_agent(self, user):
        return self.get_queryset().by_agent(user)