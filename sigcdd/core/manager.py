from django.db import models
from helpers.models import Role
class DCPQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role==Role.ADMIN:
                    return self.all()
                else:
                    return self.none()
            except Exception:
                return self.none()

class DCPManager(models.Manager):
    def get_queryset(self, ):
        return DCPQuerySet(self.model, using=self._db)  # Important!
    def by_agent(self, user):
        return self.get_queryset().by_agent(user)


class PosteComptableSet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role==Role.ADMIN:
                    return self.all()
                elif user.role==Role.AGENT_DCP:
                    return self.all()
                elif user.role==Role.AGENT_PC:
                    return self.filter(id=user.agent_postecomptable.poste_id)

                elif user.role==Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.filter(actif=True).values_list("compte__poste_id", flat=True)
                    return self.filter(id__in=ids)
                else:
                    return self.none()
            except Exception:
                return self.none()

class PosteComptableManager(models.Manager):
    def get_queryset(self, ):
        return PosteComptableSet(self.model, using=self._db)  # Important!
    def by_agent(self, user):
        return self.get_queryset().by_agent(user)





class ProfilePCQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role==Role.ADMIN:
                    return self.all()
                elif user.role==Role.AGENT_DCP:
                    return self.none()
                elif user.role==Role.AGENT_PC:
                    return self.filter(id=user.agent_postecomptable.id)
                else:
                    return self.none()
            except Exception:
                return self.none()

class ProfilePCManager(models.Manager):
    def get_queryset(self, ):
        return ProfilePCQuerySet(self.model, using=self._db)  # Important!
    def by_agent(self, user):
        return self.get_queryset().by_agent(user)



class ProfileDCPQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role==Role.ADMIN:
                    return self.all()
                elif user.role==Role.AGENT_DCP:
                    return self.filter(id=user.agent_dcp.id)

                else:
                    return self.none()
            except Exception:
                return self.none()

class ProfileDCPManager(models.Manager):
    def get_queryset(self, ):
        return ProfileDCPQuerySet(self.model, using=self._db)  # Important!
    def by_agent(self, user):
        return self.get_queryset().by_agent(user)

class AffectationAgentQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role==Role.ADMIN:
                    return self.all()
                elif user.role==Role.AGENT_DCP:
                    return self.none()
                elif user.role==Role.AGENT_PC:
                    return self.filter(agent_id=user.agent_postecomptable.id)
                else:
                    return self.none()
            except Exception:
                return self.none()

class AffectationAgentManager(models.Manager):
    def get_queryset(self, ):
        return AffectationAgentQuerySet(self.model, using=self._db)  # Important!
    def by_agent(self, user):
        return self.get_queryset().by_agent(user)



class StructureQuerySet(models.QuerySet):
    def by_agent(self, user, *args, **kwargs):
        if user.is_superuser:
            return self.all()
        else:
            try:
                if user.role==Role.ADMIN:
                    return self.all()
                elif user.role==Role.AGENT_DCP:
                    return self.none()
                elif user.role==Role.GERANT:
                    ids = user.gerant_cd.mes_compte_depots.all().values_list("structure_id", flat=True)
                    return self.filter(id__in=ids)
                else:
                    return self.none()
            except Exception:
                return self.none()

class StructureManager(models.Manager):
    def get_queryset(self, ):
        return StructureQuerySet(self.model, using=self._db)  # Important!
    def by_agent(self, user):
        return self.get_queryset().by_agent(user)