import os
import django

BASE_DIR = os.path.dirname(__file__)
DEBUG = True

django_version = django.VERSION

# Make this unique, and don't share it with anybody.
SECRET_KEY = "cookies"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

middleware = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)
if django_version[:2] >= (1, 10):
    MIDDLEWARE = middleware
else:
    MIDDLEWARE_CLASSES = middleware

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = ()

# For Django 1.10 compatibility because TEMPLATE_DIRS is deprecated
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': TEMPLATE_DIRS,
    }
]

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
)