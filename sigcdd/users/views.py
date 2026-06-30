from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView

from users.forms import ProfileForm

User = get_user_model()

from django.http import Http404

class UserDetailView(LoginRequiredMixin, DetailView):

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_success_url(self):
        return reverse("users:home_view")


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = User
    #fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self):
        assert (
            self.request.user.is_authenticated
        )  # for mypy to know that the user is authenticated
        return self.request.user.get_absolute_url()

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        #return reverse("users:detail", kwargs={"username": self.request.user.username})
        return reverse("users:home_view")



user_redirect_view = UserRedirectView.as_view()


from helpers.models import Role
@login_required
def home_view(request):
    user = request.user
    if user.last_login is None:
        #change password
        url = redirect(reverse("account_change_password"))
        return url

    if request.user.is_superuser:
        raise Http404

    elif user.role == Role.ADMIN:
        url_path = reverse('core:dcp_list')
        url = redirect(url_path)
        return url

    elif user.role == Role.AGENT_TG:
        url_path = reverse('core:dash_tg_view')
        url = redirect(url_path)
        return url

    elif user.role == Role.AGENT_DS:
        url_path = reverse('core:dash_ds_view')
        url = redirect(url_path)
        return url

    elif user.role == Role.SIMPLE:
        url_path = reverse('users:user_simple_view')
        url = redirect(url_path)
        return url


    elif hasattr(user, "agent_dcp") == True:
        poste_id = user.agent_dcp
        url_path = reverse('cddaccount:comptedepot_list')
        url = redirect(url_path)
        return url

    elif hasattr(user, "agent_dap") == True:
        poste_id = user.agent_dap
        url_path = reverse('bankcheck:dap_list')
        url = redirect(url_path)
        return url

    elif hasattr(user, "agent_postecomptable") == True:
        poste_id = user.agent_postecomptable.poste_id
        url_path = reverse('core:dash_postcomptable_view',kwargs={"poste_id":poste_id})
        url = redirect(url_path)
        return url

    elif hasattr(user, "gerant_cd") == True:
        url_path = user.gerant_cd.get_absolute_url()
        url = redirect(url_path)
        return url

    elif hasattr(user, Role.AGENT_SAISIE_CD.lower()) == True:
        url_path = user.agent_saisie_cd.get_absolute_url()
        url = redirect(url_path)
        return url

    else:
        raise Http404


from allauth.account.views import PasswordChangeView
class SigcddPasswordChangeView(LoginRequiredMixin,PasswordChangeView):

    def get_success_url(self):
        """
        Return the URL to redirect to after processing a valid form.

        Using this instead of just defining the success_url attribute
        because our url has a dynamic element.
        """
        #success_url = reverse("users:detail", kwargs={"username": self.request.user.username})
        success_url = reverse("users:home_view")

        return success_url


from django.shortcuts import render, redirect
from django.contrib import messages


@login_required
def profile_view(request):
    template = "users/profile.html"
    user = request.user
    initial = {"email":user.email,"first_name":user.first_name,"last_name":user.last_name}
    if request.method == 'POST':
        form = ProfileForm(request.POST, )
        if form.is_valid():
            user.first_name=form.cleaned_data["first_name"]
            user.last_name = form.cleaned_data["last_name"]
            user.email = form.cleaned_data["email"]
            user.save()
        else:
            for field in form:
                if field.errors:
                    for error in field.errors:
                        meg = '{}({})'.format(error, field.html_name)
                        messages.error(request, meg, extra_tags="danger")

    else:
        form = ProfileForm(initial=initial)

    context = {"form": form, }
    return render(request, template, context)


@login_required
def user_simple_view(request):
    template="users/simple.html"
    return render(request, template, {})