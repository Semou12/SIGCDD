# -*- coding: utf-8 -*-
"""
Django settings for bcore project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""
from __future__ import absolute_import, unicode_literals
from .base import *





# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases



DATABASES['default']['ATOMIC_REQUESTS'] = True


# django-debug-toolbar
# ------------------------------------------------------------------------------
MIDDLEWARE += ('debug_toolbar.middleware.DebugToolbarMiddleware',)
INSTALLED_APPS += ('debug_toolbar','werkzeug',)

DEBUG_TOOLBAR_CONFIG = {
    'DISABLE_PANELS': [
        'debug_toolbar.panels.redirects.RedirectsPanel',
    ],
    'SHOW_TEMPLATE_CONTEXT': True,
}



# TESTING
# ------------------------------------------------------------------------------
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Your local stuff: Below this line define 3rd party library settings


MEDIA_ROOT = os.path.normpath(os.path.join(SITE_ROOT, 'media'))
STATIC_ROOT = os.path.normpath(os.path.join(SITE_ROOT, 'assets'))

FORCE_2FA_ENABLED=True

ACCOUNT_SIGNUP_ENABLED = False
ACCOUNT_ALLOW_REGISTRATION = False
SOCIALACCOUNT_AUTO_SIGNUP = False