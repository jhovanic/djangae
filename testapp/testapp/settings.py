"""
Django settings for testapp project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""
import sys
import django
from djangae.settings_base import *

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '&x$ts1u)tx#5zsi84555$(@mydbz06&q23p8=c6fs1!d4%1a^u'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'djangae',
    'django.contrib.admin',
    'django.contrib.auth',
    'djangae.contrib.gauth_datastore',
    'djangae.contrib.security',
    'djangae.contrib.consistency',
    'django.contrib.contenttypes',
    'djangae.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'djangae.contrib.locking',
    'djangae.contrib.processing.mapreduce',
    'djangae.contrib.pagination',
    'djangae.contrib.uniquetool',
    'testapp'
]

TO_TEST = []

if "test" in sys.argv:
    import sys
    import tempfile
    import django

    tests_dir = os.path.join(BASE_DIR, "libs", "django-stable-{}.{}.x/tests".format(*django.VERSION[:2]))
    if not os.path.exists(tests_dir):
        tests_dir = os.path.join(BASE_DIR, "libs", "django-{}/tests".format(django.get_version()))
        if not os.path.exists(tests_dir):
            tests_dir = os.path.join(BASE_DIR, "libs", "django-master/tests")

    sys.path.insert(0, tests_dir)

    TEMP_DIR = tempfile.mkdtemp(prefix='django_')
    os.environ['DJANGO_TEST_TEMP_DIR'] = TEMP_DIR

    TO_TEST = [
        "basic",
        "bulk_create",
        "custom_managers",
        "custom_pk",
        "dates",
        "datetimes",
        "defer",
        "delete",
        "empty",
        "force_insert_update",
        "get_or_create",
        "lookup",
        "many_to_one",
        "many_to_one_null",
        "max_lengths",
        "model_forms",
        "model_inheritance",
        "null_queries",
        "one_to_one",
        "or_lookups",
        "ordering",
        "proxy_models",
        "update",
    ]

    ADDITIONAL_INSTALLED_APPS = ["file_uploads"]

    for folder in TO_TEST + ADDITIONAL_INSTALLED_APPS:
        if os.path.exists(os.path.join(tests_dir, folder, "tests.py")):
            INSTALLED_APPS.append(folder)

INSTALLED_APPS = tuple(INSTALLED_APPS)

MIDDLEWARE = (
    'djangae.contrib.security.middleware.AppEngineSecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'djangae.contrib.gauth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'session_csrf.CsrfMiddleware'
)

if tuple(django.VERSION[:2]) < (1, 10):
    MIDDLEWARE_CLASSES = MIDDLEWARE



ROOT_URLCONF = 'testapp.urls'
SITE_ID = 1
WSGI_APPLICATION = 'testapp.wsgi.application'


# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'djangae.db.backends.appengine',
        'NAMESPACE': 'customdefaultnamespace',
    },
    "ns1": {
        'ENGINE': 'djangae.db.backends.appengine',
        'NAMESPACE': 'ns1namespace',
    },
    "nonamespace": {
        'ENGINE': 'djangae.db.backends.appengine',
    },
}

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/

STATIC_ROOT = BASE_DIR + 'static'
STATIC_URL = '/static/'

AUTH_USER_MODEL = 'gauth_datastore.GaeDatastoreUser'
GENERATE_SPECIAL_INDEXES_DURING_TESTING = True
COMPLETE_FLUSH_WHILE_TESTING = True
DJANGAE_SEQUENTIAL_IDS_IN_TESTS = True

TEST_RUNNER = 'djangae.test_runner.SkipUnsupportedRunner'
DJANGAE_ADDITIONAL_TEST_APPS = ["djangae"] + TO_TEST

DJANGAE_ADDITIONAL_MODULES = [os.path.join(BASE_DIR, "module.yaml")]

# Here because of "You haven't defined a TEMPLATES setting" deprecation message
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth'
            ],
            'debug': True
        }
    },
]

from djangae.contrib.gauth.settings import *
