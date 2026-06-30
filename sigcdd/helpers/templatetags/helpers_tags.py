from django import template
from django.utils.safestring import mark_safe
from datetime import datetime
from django.contrib.humanize.templatetags.humanize import intcomma
register = template.Library()

VERSION = "1.0"

propulseur_site_url="https://sud-pay.com/"
propulseur_site_name ="Tresor"
propulseur_name ="SIGCDD"
propulseur_company="Tresor"
year  = datetime.today().year
st= f""" <span class="hidden-md-down fw-700">{year} © {propulseur_name}&nbsp;<a href='{propulseur_site_url}'
                                                                    class='text-primary fw-500' title='{propulseur_site_name}'
                                                                    target='_blank'>{propulseur_site_name}</a></span>"""

copyright=format(st)


APPLICATION_CONFIG = {
    "VERSION": VERSION,
    "APP_NAME": "SIGCDD",
    "APP_DESCRIPTION": "SYSTEME INNTEGRE DE GESTION DES COMPTES DE DEPOT",
    "COPYRIGHT_MSG": "SUDPAY SARL Unite 13, N 444, Parcelles Assainies  Tel: +221 33 835 24 25 / 77 422 45 77  site:",
    "PARTNER_SITE_URL": "http://www.transco-rdc.cd",
    "PARTNER_SITE_NAME": "TRESOR",
    "SAV": "+243 844 689 031",
    "YEAR": "2014-2015",
}


def get_config(param):
    return APPLICATION_CONFIG.get(param)


@register.filter(name="application_local_tag")
def application_local_tag(name):
    value = get_config(name)
    return mark_safe(value) if isinstance(value, str) else value


@register.filter(name="field_type")
def field_type(field):
    """
    Template filter that returns field class name (in lower case).
    E.g. if field is CharField then {{ field|field_type }} will
    return 'charfield'.
    """
    if hasattr(field, "field") and field.field:
        return field.field.__class__.__name__.lower()
    return ""


@register.filter(name="widget_type")
def widget_type(field):
    """
    Template filter that returns field widget class name (in lower case).
    E.g. if field's widget is TextInput then {{ field|widget_type }} will
    return 'textinput'.
    """
    if (
        hasattr(field, "field")
        and hasattr(field.field, "widget")
        and field.field.widget
    ):
        return field.field.widget.__class__.__name__.lower()
    return ""


@register.filter("has_group")
def has_group(user, group_name):
    """
    Verifica se este usuário pertence a um grupo
    """
    groups = user.groups.all().values_list("name", flat=True)
    return True if group_name in groups else False


from django.utils.html import format_html
from  helpers.models import Category
@register.simple_tag(takes_context=True)
def sigcdd_live_notify_badge(context, badge_class='live_notify_badge'):
    user = user_context(context)
    if not user:
        return ''
    category_name=badge_class #.split("_").pop()
    unread =0
    try:
        category=Category.objects.get(name=category_name)
        unread=user.notifications.unread().filter(target_object_id=category.id).count()
    except:pass

    badge_classf=f"""badge  badge-danger badge-pill  mr-2 {badge_class}"""

    html = "<span class='{badge_class}'>{unread}</span>".format(
        badge_class=badge_classf, unread=unread
    )
    return format_html(html)

def user_context(context):
    if 'user' not in context:
        return None

    request = context['request']
    user = request.user
    try:
        user_is_anonymous = user.is_anonymous()
    except TypeError:  # Django >= 1.11
        user_is_anonymous = user.is_anonymous

    if user_is_anonymous:
        return None
    return user



from django.urls import reverse
@register.simple_tag
def sigregister_notify_callbacks(badge_class='live_notify_badge',
                              menu_class='live_notify_list',
                              refresh_period=300,
                              callbacks='',
                              api_name='count',
                              fetch=5):
    refresh_period = int(refresh_period) * 1000

    if api_name == 'count':
        api_url = reverse('helpers:live_unread_notification_count')
    else:
        return ""


    definitions = """
        notify_badge_class='{badge_class}';
        notify_menu_class='{menu_class}';
        notify_api_url='{api_url}';
        notify_fetch_count='{fetch_count}';
        notify_unread_url='{unread_url}';
        notify_mark_all_unread_url='{mark_all_unread_url}';
        notify_refresh_period={refresh};
    """.format(
        badge_class=badge_class,
        menu_class=menu_class,
        refresh=refresh_period,
        api_url=api_url,
        unread_url=reverse('notifications:unread'),
        mark_all_unread_url=reverse('notifications:mark_all_as_read'),
        fetch_count=fetch
    )

    script = "<script>" + definitions
    for callback in callbacks.split(','):
        script += "register_notifier(" + callback + ");"
    script += "</script>"
    return format_html(script)

@register.filter()
def to_int(value):
    return intcomma(int(value))