from .config import ROOT

SECRET_KEY = "local-demo-no-auth-no-persisted-server-sessions"
DEBUG = False
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
ROOT_URLCONF = "lens.urls"
INSTALLED_APPS = ["django.contrib.staticfiles"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.middleware.csrf.CsrfViewMiddleware",
              "django.middleware.clickjacking.XFrameOptionsMiddleware"]
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [ROOT / "templates"], "APP_DIRS": True}]
STATIC_URL = "/static/"
STATICFILES_DIRS = [ROOT / "static"]
DATA_UPLOAD_MAX_MEMORY_SIZE = 2_200_000
FILE_UPLOAD_MAX_MEMORY_SIZE = 2_000_000
CSRF_COOKIE_SAMESITE = "Strict"
CSRF_FAILURE_VIEW = "lens.views.csrf_failure"
USE_TZ = True
X_FRAME_OPTIONS = "DENY"
