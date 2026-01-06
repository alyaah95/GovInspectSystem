"""
Django settings for GovInspectSystem project.
Final Production Version for Vercel.
"""

from pathlib import Path
import dj_database_url
import os
from email.utils import formataddr
# في الإنتاج على Vercel، لا نحتاج لـ load_dotenv لأن القيم تُقرأ من إعدادات الموقع مباشرة
# لكن سنبقي عليها للمساعدة في التشغيل المحلي إذا لزم الأمر
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

# قراءة السرية من متغيرات البيئة
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key')

# يجب أن يكون False في Vercel إلا لو كنتِ تقومين بعمل تصحيح أخطاء
DEBUG = True

# السماح لروابط فيرسل
ALLOWED_HOSTS = ['.vercel.app', '.now.sh', 'localhost', '127.0.0.1']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'auditlog',
    'inspectors',
    'crispy_forms',
    'crispy_bootstrap5',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # الترتيب مهم: تحت Security مباشرة
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'auditlog.middleware.AuditlogMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
]

ROOT_URLCONF = 'GovInspectSystem.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], # تأكدي من إضافة هذا المسار
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug', # أضيفي هذا للضرورة
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'inspectors.context_processors.unread_notifications',
            ],
        },
    },
]

WSGI_APPLICATION = 'GovInspectSystem.wsgi.application'

# إعداد قاعدة البيانات Neon
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'db.sqlite3')}"),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Asia/Qatar'
USE_I18N = True
USE_TZ = True

# --- تعديل الملفات الثابتة لـ Vercel ---
STATIC_URL = '/static/'

# هذا المسار هو ما ينتظره Vercel عند عمل Deploy
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_build', 'static')

# تأكدي أن هذا المجلد موجود في مشروعك ويحتوي على ملفات CSS/JS الخاصة بك
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

# استخدام WhiteNoise لضغط الملفات وخدمتها
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# إعدادات البريد الإلكتروني
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

# تأكدي من وجود قيمة للإيميل قبل التنسيق لتجنب الأخطاء
if EMAIL_HOST_USER:
    DEFAULT_FROM_EMAIL = formataddr(('نظام التفتيش الحكومي', EMAIL_HOST_USER))

AUTHENTICATION_BACKENDS = [
    'inspectors.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

CSRF_FAILURE_VIEW = 'inspectors.views.csrf_failure'

# لا يفضل تخزين الميديا على Vercel لأنها تُحذف عند كل Deploy جديد
# ولكن للتشغيل الأولي سنتركها هكذا
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

AUTH_USER_MODEL = 'inspectors.User'